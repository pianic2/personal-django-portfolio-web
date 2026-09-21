"""Least-privilege FastMCP view of the project's Wagtail v3 API."""

from __future__ import annotations

import base64
import binascii
import json
import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import urljoin

import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType, RouteMap


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
        ("POST", r"^/api/v3/pages/$"),
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


def _customize_component(_route: Any, component: Any) -> None:
    """Keep Wagtail's heterogeneous page response valid across MCP clients."""
    if component.name == "get_page":
        component.output_schema = {"type": "object"}


def create_server(openapi_spec: dict[str, Any], client: httpx.AsyncClient) -> FastMCP:
    """Build the MCP components from the supplied live Wagtail OpenAPI document."""
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
            "pages_create": "create_page_draft",
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
