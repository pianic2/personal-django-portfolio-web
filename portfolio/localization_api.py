from typing import Any, Literal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from ninja import Body, Router, Schema, Status
from ninja.errors import HttpError
from pydantic import Field
from wagtail.api.v3.auth import BearerTokenAuth
from wagtail.api.v3.permissions import require_any_permission
from wagtail.models import Locale, Page, Site

from .models import BlogIndexPage, BlogPostPage, ProfilePage, ProjectPage


class LocalizedPagePairCreate(Schema):
    type: Literal[
        "portfolio.BlogIndexPage",
        "portfolio.BlogPostPage",
        "portfolio.ProfilePage",
        "portfolio.ProjectPage",
    ]
    stable_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    parent_stable_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description=(
            "Stable editorial parent identity. Required for BlogPostPage; the "
            "server resolves the IT and EN BlogIndexPage parents by locale."
        ),
    )
    it: dict[str, Any]
    en: dict[str, Any]


class LocalizedPagePairResult(Schema):
    stable_id: str
    translation_key: str
    pages: list[dict[str, Any]]


router = Router(tags=["localized content"])
PAGE_TYPES = {
    "portfolio.BlogIndexPage": BlogIndexPage,
    "portfolio.BlogPostPage": BlogPostPage,
    "portfolio.ProfilePage": ProfilePage,
    "portfolio.ProjectPage": ProjectPage,
}
LOCALES = ("it", "en")
PROTECTED_FIELDS = {
    "id",
    "path",
    "depth",
    "numchild",
    "url_path",
    "locale",
    "translation_key",
    "live",
    "stable_id",
}


def _page_fields(model: type[Page]) -> set[str]:
    return {
        field.name
        for field in model._meta.concrete_fields
        if field.name not in PROTECTED_FIELDS
    }


def _create_variant(
    *,
    model: type[Page],
    locale: Locale,
    parent_id: int | None,
    parent_stable_id: str | None,
    stable_id: str,
    values: dict[str, Any],
    translation_key: Any | None,
    user,
) -> Page:
    if model is BlogPostPage:
        if parent_stable_id is None:
            raise ValidationError(
                {"parent_stable_id": "This stable parent identity is required for BlogPostPage."}
            )
        try:
            parent = BlogIndexPage.objects.get(
                stable_id=parent_stable_id,
                locale=locale,
            )
        except BlogIndexPage.DoesNotExist:
            raise ValidationError(
                {
                    "parent_stable_id": (
                        f"No BlogIndexPage with stable_id={parent_stable_id!r} "
                        f"exists for locale {locale.language_code}."
                    )
                }
            ) from None
        except BlogIndexPage.MultipleObjectsReturned:
            raise ValidationError(
                {
                    "parent_stable_id": (
                        f"Multiple BlogIndexPage parents use stable_id={parent_stable_id!r} "
                        f"for locale {locale.language_code}."
                    )
                }
            ) from None
    else:
        if not isinstance(parent_id, int) or parent_id <= 0:
            raise ValidationError({"parent_id": "A positive parent page ID is required."})
        parent = Page.objects.get(pk=parent_id).specific
    is_site_root = Site.objects.filter(root_page_id=parent.pk).exists()
    if parent.locale_id != locale.id and not is_site_root:
        raise ValidationError({"parent_id": f"Parent must use locale {locale.language_code}."})
    if not parent.permissions_for_user(user).can_add_subpage():
        raise PermissionDenied("The agent cannot add a page below this parent.")
    if model.objects.filter(locale=locale, stable_id=stable_id).exists():
        raise ValidationError(
            {"stable_id": f"A {locale.language_code} page already uses this stable ID."}
        )

    allowed_parent_fields = set() if model is BlogPostPage else {"parent_id"}
    unknown = set(values) - _page_fields(model) - allowed_parent_fields
    if unknown:
        raise ValidationError({"data": f"Unsupported fields: {', '.join(sorted(unknown))}."})
    if model is not BlogPostPage and "parent_id" not in values:
        raise ValidationError({"parent_id": "This field is required for each locale."})
    page = model(locale=locale, stable_id=stable_id)
    if translation_key is not None:
        page.translation_key = translation_key
    for field, value in values.items():
        if field != "parent_id":
            setattr(page, field, value)
    parent.add_child(instance=page)
    page.live = False
    page.save(update_fields=["live"])
    page.save_revision(user=user)
    return page


@router.post(
    "/",
    response={201: LocalizedPagePairResult},
    auth=BearerTokenAuth(),
    url_name="create_localized_pair",
    operation_id="localized_pairs_create",
    summary="Create an IT/EN localized page pair",
    description=(
        "Create exactly one Italian and one English draft with the same stable_id "
        "and Wagtail translation family. The operation is atomic: if either locale "
        "cannot be created, no pair is reported and the transaction is rolled back."
    ),
)
@require_any_permission(Page, ("add",))
def create_localized_pair(
    request: HttpRequest,
    data: LocalizedPagePairCreate = Body(...),
):
    model = PAGE_TYPES[data.type]
    try:
        locales = {code: Locale.objects.get(language_code=code) for code in LOCALES}
        with transaction.atomic():
            first = _create_variant(
                model=model,
                locale=locales["it"],
                parent_id=data.it.get("parent_id"),
                parent_stable_id=data.parent_stable_id,
                stable_id=data.stable_id,
                values=data.it,
                translation_key=None,
                user=request.user,
            )
            second = _create_variant(
                model=model,
                locale=locales["en"],
                parent_id=data.en.get("parent_id"),
                parent_stable_id=data.parent_stable_id,
                stable_id=data.stable_id,
                values=data.en,
                translation_key=first.translation_key,
                user=request.user,
            )
    except (Locale.DoesNotExist, Page.DoesNotExist, ValidationError, IntegrityError) as exc:
        if isinstance(exc, ValidationError):
            details = "; ".join(
                f"{field}: {', '.join(str(message) for message in messages)}"
                for field, messages in exc.message_dict.items()
            )
        elif isinstance(exc, Page.DoesNotExist):
            details = "parent_id: Parent page does not exist."
        else:
            details = str(exc)
        raise HttpError(
            400,
            f"Localized pair creation failed; no pages were created. {details}",
        ) from exc

    return Status(201, {
        "stable_id": data.stable_id,
        "translation_key": str(first.translation_key),
        "pages": [
            {"id": first.id, "locale": "it", "type": data.type},
            {"id": second.id, "locale": "en", "type": data.type},
        ],
    })
