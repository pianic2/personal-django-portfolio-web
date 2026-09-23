import json
import re

from django.http import JsonResponse
from wagtail.models import APIToken, Page

from .models import BlogIndexPage, BlogPostPage, ProfilePage, ProjectPage

AGENT_GROUP_NAME = "Portfolio content agent"
LOCALIZED_PAGE_TYPES = (BlogIndexPage, BlogPostPage, ProfilePage, ProjectPage)
PAGE_DETAIL_PATH = re.compile(r"^/api/v3/pages/(?P<page_id>\d+)/$")


def _is_content_agent(request):
    if not request.user.is_authenticated:
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        if scheme.casefold() == "bearer" and token:
            api_token = (
                APIToken.objects.select_related("user")
                .filter(
                    key_hash__in=APIToken.candidate_key_hashes(token),
                    revoked_at__isnull=True,
                )
                .first()
            )
            if api_token is not None and api_token.user.is_active:
                request.user = api_token.user
    return (
        request.user.is_authenticated
        and request.user.groups.filter(name=AGENT_GROUP_NAME).exists()
    )


def _deny_agent_localized_boundary(request):
    if not _is_content_agent(request):
        return None

    if request.method == "POST" and request.path == "/api/v3/pages/":
        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        page_type = payload.get("meta", {}).get("type") if isinstance(payload, dict) else None
        localized_types = {
            f"{model._meta.app_label}.{model.__name__}"
            for model in LOCALIZED_PAGE_TYPES
        }
        if page_type in localized_types:
            return JsonResponse(
                {"detail": "Use the localized pair endpoint for governed page types."},
                status=403,
            )

    if request.method == "DELETE":
        match = PAGE_DETAIL_PATH.fullmatch(request.path)
        if match:
            try:
                page = Page.objects.get(pk=match.group("page_id")).specific
            except Page.DoesNotExist:
                page = None
            if isinstance(page, LOCALIZED_PAGE_TYPES) and page.get_translations().exists():
                return JsonResponse(
                    {"detail": "Deleting one locale of a localized pair is not allowed."},
                    status=403,
                )
    return None


class ImmutableStableIDMiddleware:
    """Reject API page updates that attempt to change a page identity."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        boundary_response = _deny_agent_localized_boundary(request)
        if boundary_response is not None:
            return boundary_response
        if request.method == "PATCH" and request.path.startswith("/api/v3/pages/"):
            try:
                payload = json.loads(request.body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = None
            if isinstance(payload, dict) and "stable_id" in payload:
                return JsonResponse(
                    {"detail": "stable_id is immutable after page creation."},
                    status=400,
                )
        return self.get_response(request)
