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
    parent_id: int,
    stable_id: str,
    values: dict[str, Any],
    translation_key: Any | None,
    user,
) -> Page:
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

    unknown = set(values) - _page_fields(model) - {"parent_id", "parent_stable_id"}
    if unknown:
        raise ValidationError({"data": f"Unsupported fields: {', '.join(sorted(unknown))}."})
    if parent_id is None:
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


def _parent_id_for_values(*, locale: Locale, values: dict[str, Any]) -> Any:
    """Resolve the canonical stable parent while retaining numeric compatibility."""
    if "parent_id" in values:
        return values["parent_id"]
    stable_id = values.get("parent_stable_id")
    if stable_id is None:
        return None
    parent = BlogIndexPage.objects.filter(locale=locale, stable_id=stable_id).first()
    if parent is None:
        raise ValidationError({"parent_stable_id": "A matching blog parent is required."})
    return parent.pk


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
                parent_id=_parent_id_for_values(locale=locales["it"], values=data.it),
                stable_id=data.stable_id,
                values=data.it,
                translation_key=None,
                user=request.user,
            )
            second = _create_variant(
                model=model,
                locale=locales["en"],
                parent_id=_parent_id_for_values(locale=locales["en"], values=data.en),
                stable_id=data.stable_id,
                values=data.en,
                translation_key=first.translation_key,
                user=request.user,
            )
    except (Locale.DoesNotExist, Page.DoesNotExist, ValidationError, IntegrityError) as exc:
        raise HttpError(400, "Localized pair creation failed; no pages were created.") from exc

    return Status(201, {
        "stable_id": data.stable_id,
        "translation_key": str(first.translation_key),
        "pages": [
            {"id": first.id, "locale": "it", "type": data.type},
            {"id": second.id, "locale": "en", "type": data.type},
        ],
    })
