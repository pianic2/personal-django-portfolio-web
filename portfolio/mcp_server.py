"""Least-privilege FastMCP view of the project's Wagtail v3 API."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import urljoin

import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType, RouteMap


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


def create_server(openapi_spec: dict[str, Any], client: httpx.AsyncClient) -> FastMCP:
    """Build the MCP components from the supplied live Wagtail OpenAPI document."""
    if _reject_publication_bypass not in client.event_hooks["request"]:
        client.event_hooks["request"].append(_reject_publication_bypass)
    return FastMCP.from_openapi(
        openapi_spec=openapi_spec,
        client=client,
        name="Portfolio content editor",
        route_maps=_route_maps(),
        mcp_names={
            "pages_list": "list_pages",
            "pages_create": "create_page_draft",
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
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
        event_hooks={"request": [_reject_publication_bypass]},
    )
    return create_server(response.json(), client)


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
