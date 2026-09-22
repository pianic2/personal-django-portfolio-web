from __future__ import annotations

import asyncio
import json

import httpx
from django.test import SimpleTestCase
from fastmcp.server.openapi import MCPType

from .mcp_server import (
    _contains_publish_action,
    _reject_publication_bypass,
    _reject_publication_bypass_async,
    create_server,
)


class MCPServerTests(SimpleTestCase):
    def test_real_project_openapi_routes_build_deterministic_allowlisted_tools(self):
        from django.test import Client

        spec = Client().get("/api/v3/openapi.json").json()
        client = httpx.AsyncClient(base_url="https://wagtail.example", headers={
            "Authorization": "Bearer test-secret",
        })
        server = create_server(spec, client)

        tools = asyncio.run(server.get_tools())

        self.assertEqual(
            set(tools),
            {
                "list_pages", "create_localized_pair", "find_page", "get_page",
                "update_page_draft", "list_page_revisions", "get_page_revision",
                "list_content_types", "get_content_type_schema", "list_images",
                "create_image", "get_image", "update_image", "list_documents",
                "create_document", "get_document", "update_document",
            },
        )
        self.assertEqual(set(tools), set(asyncio.run(server.get_tools())))
        self.assertTrue(all(tool.description for tool in tools.values()))
        inventory = json.dumps(
            {name: tool.model_dump(mode="json") for name, tool in tools.items()},
            sort_keys=True,
        )
        self.assertNotIn("test-secret", inventory)
        self.assertNotIn("publish", " ".join(tools))
        self.assertNotIn("delete", " ".join(tools))
        self.assertIn("only creation path", tools["create_localized_pair"].description)
        self.assertNotIn("create_page_draft", tools["create_localized_pair"].description)
        list_schema = tools["list_pages"].parameters
        self.assertEqual(list_schema["properties"]["limit"].get("maximum"), 20)
        self.assertIn("pk, not id", list_schema["properties"]["order"]["description"])
        for schema in list_schema["properties"].values():
            self.assertNotIn("action", json.dumps(schema))
        asyncio.run(client.aclose())

    def test_final_route_rule_excludes_unmatched_and_forbidden_routes(self):
        from .mcp_server import _route_maps

        maps = _route_maps()
        self.assertEqual(maps[-1].mcp_type, MCPType.EXCLUDE)
        spec = {
            "openapi": "3.1.0",
            "info": {"title": "Future API", "version": "1"},
            "paths": {
                "/api/v3/pages/{page_id}/": {"delete": {"operationId": "delete_page"}},
                "/api/v3/pages/{page_id}/actions/publish/": {
                    "post": {"operationId": "publish_page"}
                },
                "/api/v3/unknown/": {"get": {"operationId": "future_route"}},
            },
        }
        client = httpx.AsyncClient(base_url="https://wagtail.example")
        server = create_server(spec, client)
        self.assertEqual(asyncio.run(server.get_tools()), {})
        asyncio.run(client.aclose())

    def test_publication_actions_are_detected_recursively_and_rejected_without_echo(self):
        self.assertTrue(_contains_publish_action({"meta": {"action": "publish"}}))
        self.assertTrue(_contains_publish_action({"nested": [{"action": "unpublish"}]}))
        self.assertFalse(_contains_publish_action({"meta": {"type": "portfolio.ProjectPage"}}))

        request = httpx.Request(
            "POST",
            "https://wagtail.example/api/v3/pages/",
            json={"meta": {"action": "publish"}},
        )
        with self.assertRaisesRegex(ValueError, "Publication actions are not available"):
            _reject_publication_bypass(request)
        query_request = httpx.Request(
            "POST", "https://wagtail.example/api/v3/pages/?action=publish"
        )
        with self.assertRaisesRegex(ValueError, "Publication actions are not available"):
            _reject_publication_bypass(query_request)

        async def check_configured_client():
            client = httpx.AsyncClient(
                base_url="https://wagtail.example",
                event_hooks={"request": [_reject_publication_bypass_async]},
            )
            try:
                with self.assertRaisesRegex(
                    ValueError, "Publication actions are not available"
                ):
                    await client.post("/api/v3/pages/", json={"meta": {"action": "publish"}})
            finally:
                await client.aclose()

        asyncio.run(check_configured_client())
