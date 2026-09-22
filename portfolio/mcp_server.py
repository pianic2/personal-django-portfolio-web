"""Least-privilege FastMCP view of the project's Wagtail v3 API."""

from __future__ import annotations

import base64
import binascii
import copy
import json
import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import urljoin

import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType, RouteMap

SUPPORTED_PAGE_ORDERING = (
    "random",
    "pk",
    "-pk",
    "title",
    "-title",
    "slug",
    "-slug",
    "first_published_at",
    "-first_published_at",
    "locale",
    "-locale",
)


class _BearerTokenAuth(httpx.Auth):
    """Add the service credential inside HTTPX after agent-facing request setup."""

    def __init__(self, token: str):
        self._token = token

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


def _reject_publication_bypass(request: httpx.Request) -> None:
    """Reject body-level Wagtail publication actions without logging request data."""
    if request.method not in {"POST", "PATCH", "PUT"}:
        return
    if any(
        value.casefold() in {"publish", "unpublish"}
        for value in request.url.params.get_list("action")
    ):
        raise ValueError("Publication actions are not available through this API.")
    if not request.content:
        return
    try:
        body = json.loads(request.content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return
    if _contains_publish_action(body):
        raise ValueError("Publication actions are not available through this API.")


async def _reject_publication_bypass_async(request: httpx.Request) -> None:
    """Apply the publication guard as an async HTTPX request hook."""
    _reject_publication_bypass(request)


async def _encode_media_upload(request: httpx.Request) -> None:
    """Translate the MCP base64 data URL into Wagtail's multipart upload shape."""
    if request.method != "POST" or request.url.path not in {
        "/api/v3/images/",
        "/api/v3/documents/",
    }:
        return
    try:
        body = json.loads(request.content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return
    if not isinstance(body, dict) or "file" not in body:
        return

    value = body["file"]
    if not isinstance(value, str) or not value.startswith("data:"):
        raise ValueError("Media file content must be supplied as a base64 data URL.")
    header, separator, encoded_file = value.partition(",")
    if not separator or ";base64" not in header:
        raise ValueError("Media file content must be supplied as a base64 data URL.")
    media_type = header[5:].split(";", 1)[0] or "application/octet-stream"
    try:
        file_content = base64.b64decode(encoded_file, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Media file content must be valid base64.") from None

    fields = {
        key: str(field_value)
        for key, field_value in body.items()
        if key != "file" and field_value is not None
    }
    filename = body.get("title") or "upload"
    multipart = httpx.Request(
        request.method,
        request.url,
        headers={
            key: field_value
            for key, field_value in request.headers.items()
            if key.casefold() not in {"content-type", "content-length"}
        },
        data=fields,
        files={"file": (filename, file_content, media_type)},
    )
    multipart.read()
    request.headers["Content-Type"] = multipart.headers["Content-Type"]
    request.headers["Content-Length"] = multipart.headers["Content-Length"]
    request.stream = multipart.stream
    request._content = multipart.content


def _contains_publish_action(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() == "action" and str(item).casefold() in {
                "publish",
                "unpublish",
            }:
                return True
            if _contains_publish_action(item):
                return True
    elif isinstance(value, list):
        return any(_contains_publish_action(item) for item in value)
    return False


def _route_maps() -> list[RouteMap]:
    allowed = [
        ("GET", r"^/api/v3/pages/$"),
        ("POST", r"^/api/v3/localized-pairs/$"),
        ("GET", r"^/api/v3/pages/find/$"),
        ("GET", r"^/api/v3/pages/\{page_id\}/$"),
        ("PATCH", r"^/api/v3/pages/\{page_id\}/$"),
        ("GET", r"^/api/v3/pages/\{page_id\}/revisions/$"),
        ("GET", r"^/api/v3/pages/\{page_id\}/revisions/\{revision_id\}/$"),
        ("GET", r"^/api/v3/schema/$"),
        ("GET", r"^/api/v3/schema/\{type_name\}/$"),
        ("GET", r"^/api/v3/(images|documents)/$"),
        ("POST", r"^/api/v3/(images|documents)/$"),
        ("GET", r"^/api/v3/images/\{image_id\}/$"),
        ("PATCH", r"^/api/v3/images/\{image_id\}/$"),
        ("GET", r"^/api/v3/documents/\{document_id\}/$"),
        ("PATCH", r"^/api/v3/documents/\{document_id\}/$"),
    ]
    return [
        *(RouteMap(methods=[method], pattern=path, mcp_type=MCPType.TOOL)
          for method, path in allowed),
        RouteMap(mcp_type=MCPType.EXCLUDE),
    ]


def _prepare_agent_openapi_spec(openapi_spec: dict[str, Any]) -> dict[str, Any]:
    """Expose only deterministic, agent-safe parts of the Wagtail contract."""
    spec = copy.deepcopy(openapi_spec)
    page_list = spec.get("paths", {}).get("/api/v3/pages/", {}).get("get", {})
    for parameter in page_list.get("parameters", []):
        if parameter.get("name") == "limit":
            schema = parameter.setdefault("schema", {})
            schema["maximum"] = 20
            schema["description"] = "Maximum 20 items per call."
        elif parameter.get("name") == "order":
            schema = parameter.setdefault("schema", {})
            schema.clear()
            schema.update({
                "default": [],
                "description": (
                    "Supported values: pk, title, slug, first_published_at, locale "
                    "and their '-' descending forms; use pk, not id."
                ),
                "items": {"enum": list(SUPPORTED_PAGE_ORDERING), "type": "string"},
                "type": "array",
            })

    for name, schema in spec.get("components", {}).get("schemas", {}).items():
        if name.endswith(("CreateMetaSchema", "PatchMetaSchema")):
            schema.get("properties", {}).pop("action", None)

    localized_create = (
        spec.get("paths", {}).get("/api/v3/localized-pairs/", {}).get("post", {})
    )
    localized_schema = (
        spec.get("components", {})
        .get("schemas", {})
        .get("LocalizedPagePairCreate", {})
    )
    parent_stable_schema = localized_schema.get("properties", {}).get("parent_stable_id")
    if parent_stable_schema is not None:
        parent_stable_schema["description"] = (
            "Required when type is portfolio.BlogPostPage. Use the stable editorial "
            "identity (for example 'blog'); the server resolves the IT and EN "
            "BlogIndexPage parents by locale. Never send numeric parent_id values."
        )
    for locale in ("it", "en"):
        locale_schema = localized_schema.get("properties", {}).get(locale)
        if locale_schema is not None:
            locale_schema["description"] = (
                "Locale-owned writable fields. For BlogPostPage do not include "
                "parent_id; parent_stable_id is resolved server-side."
            )
    localized_create.update({
        "summary": "CANONICAL: create one IT/EN localized page pair",
        "description": (
            "Use this as the only creation path for BlogIndexPage, BlogPostPage, "
            "ProfilePage and ProjectPage. Supply both locale payloads from the same "
            "article-generation result and make exactly one call. For BlogPostPage, "
            "call create_localized_pair(type='portfolio.BlogPostPage', "
            "stable_id=..., parent_stable_id='blog', it=..., en=...); numeric "
            "parent_id values are not part of the agent contract. The server resolves "
            "the localized BlogIndexPage parents and validates type, locale, and add "
            "permission. The operation is atomic and creates draft variants in one "
            "Wagtail translation family. Do not use generic page creation; it is "
            "intentionally unavailable."
        ),
    })
    return spec


def _customize_component(_route: Any, component: Any) -> None:
    """Keep Wagtail's heterogeneous page response valid across MCP clients."""
    if component.name == "get_page":
        component.output_schema = {"type": "object"}


def create_server(openapi_spec: dict[str, Any], client: httpx.AsyncClient) -> FastMCP:
    """Build the MCP components from the supplied live Wagtail OpenAPI document."""
    openapi_spec = _prepare_agent_openapi_spec(openapi_spec)
    for hook in (_reject_publication_bypass_async, _encode_media_upload):
        if hook not in client.event_hooks["request"]:
            client.event_hooks["request"].append(hook)
    for path in ("/api/v3/images/", "/api/v3/documents/"):
        upload = openapi_spec.get("paths", {}).get(path, {}).get("post", {})
        multipart = upload.get("requestBody", {}).get("content", {}).get(
            "multipart/form-data", {}
        )
        file_schema = multipart.get("schema", {}).get("properties", {}).get("file")
        if file_schema is not None:
            file_schema["description"] = (
                "File bytes as a base64 data URL, for example data:image/png;base64,..."
            )
    return FastMCP.from_openapi(
        openapi_spec=openapi_spec,
        client=client,
        name="Portfolio content editor",
        route_maps=_route_maps(),
        mcp_component_fn=_customize_component,
        mcp_names={
            "pages_list": "list_pages",
            "localized_pairs_create": "create_localized_pair",
            "pages_find": "find_page",
            "pages_detail": "get_page",
            "pages_update": "update_page_draft",
            "pages_revisions_list": "list_page_revisions",
            "pages_revisions_detail": "get_page_revision",
            "schema_list": "list_content_types",
            "schema_detail": "get_content_type_schema",
            "images_list": "list_images",
            "images_create": "create_image",
            "images_detail": "get_image",
            "images_update": "update_image",
            "documents_list": "list_documents",
            "documents_create": "create_document",
            "documents_detail": "get_document",
            "documents_update": "update_document",
        },
    )


def build_server() -> FastMCP:
    """Fetch this project's Wagtail schema and configure its server-side bearer client."""
    base_url = os.environ.get("WAGTAIL_AGENT_API_URL", "").rstrip("/")
    token = os.environ.get("WAGTAIL_AGENT_API_TOKEN", "")
    if not base_url or not token:
        raise RuntimeError("WAGTAIL_AGENT_API_URL and WAGTAIL_AGENT_API_TOKEN are required.")

    schema_url = urljoin(f"{base_url}/", "api/v3/openapi.json")
    response = httpx.get(schema_url, timeout=15.0)
    response.raise_for_status()
    client = httpx.AsyncClient(
        base_url=base_url,
        auth=_BearerTokenAuth(token),
        timeout=30.0,
        event_hooks={"request": [_reject_publication_bypass_async, _encode_media_upload]},
    )
    return create_server(response.json(), client)


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
