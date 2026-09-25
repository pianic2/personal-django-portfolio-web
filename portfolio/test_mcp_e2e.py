from __future__ import annotations

import asyncio
import base64
import inspect
import json
import logging
import os
from io import BytesIO
from unittest.mock import patch

import httpx
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import Client as DjangoClient
from django.test import TransactionTestCase
from PIL import Image as PILImage
from wagtail.images import get_image_model
from wagtail.models import APIToken, Collection, GroupPagePermission, Locale, Page, Site

from . import mcp_server
from .mcp_server import _BearerTokenAuth, create_server
from .models import BlogIndexPage, BlogPostPage, ProfilePage
from .test_support import ensure_localized_site_roots


class MCPAgentBoundaryTests(TransactionTestCase):
    def setUp(self):
        if not Site.objects.filter(is_default_site=True).exists():
            locale, _ = Locale.objects.get_or_create(language_code="it")
            content_type = ContentType.objects.get_for_model(Page)
            Page.objects.create(
                title="Root",
                slug="root",
                content_type=content_type,
                path="0001",
                depth=1,
                numchild=1,
                url_path="/",
                locale=locale,
            )
            homepage = Page.objects.create(
                title="Welcome to your new Wagtail site!",
                slug="home",
                content_type=content_type,
                path="00010001",
                depth=2,
                numchild=0,
                url_path="/home/",
                locale=locale,
            )
            Site.objects.create(
                hostname="localhost", root_page=homepage, is_default_site=True
            )
            Collection.add_root(instance=Collection(name="Root"))
        ensure_localized_site_roots()
        call_command("import_portfolio", verbosity=0)
        call_command("configure_agent_account", verbosity=0)
        user = get_user_model().objects.get(username="portfolio-agent")
        self.assertFalse(user.has_perm("wagtailcore.publish_page"))
        self.assertFalse(
            GroupPagePermission.objects.filter(
                group__user=user, permission__codename__startswith="publish_"
            ).exists()
        )
        _api_token, self.token = APIToken.create_token(user=user, name="MCP e2e test")
        self.profile = ProfilePage.objects.get(
            locale=Locale.objects.get(language_code="en"), stable_id="profile"
        )

        async def dispatch_to_wagtail(request):
            django_client = DjangoClient(HTTP_HOST="localhost")
            query = f"?{request.url.query}" if request.url.query else ""
            response = django_client.generic(
                request.method,
                f"{request.url.path}{query}",
                data=request.content,
                content_type=request.headers.get("content-type"),
                HTTP_AUTHORIZATION=request.headers.get("Authorization", ""),
            )
            return httpx.Response(
                response.status_code,
                headers=dict(response.headers),
                content=response.content,
                request=request,
            )

        self.client = httpx.AsyncClient(
            base_url="http://localhost",
            auth=_BearerTokenAuth(self.token),
            transport=httpx.MockTransport(dispatch_to_wagtail),
            timeout=10.0,
        )
        self.addCleanup(lambda: asyncio.run(self.client.aclose()))

    @staticmethod
    def _tool_result(result):
        if isinstance(result, tuple):
            _content, structured_content = result
            result = structured_content
        while isinstance(result, dict) and set(result) == {"result"}:
            result = result["result"]
        return result

    def _call_mcp_tool(self, server, name, arguments):
        async def call():
            return await server._call_tool_mcp(name, arguments)

        old_async_unsafe = os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE")
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        try:
            return self._tool_result(asyncio.run(call()))
        finally:
            if old_async_unsafe is None:
                os.environ.pop("DJANGO_ALLOW_ASYNC_UNSAFE", None)
            else:
                os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = old_async_unsafe

    def test_agent_mcp_flow_uses_authenticated_api_for_drafts_and_media(self):
        public_before = DjangoClient(HTTP_HOST="localhost").get(
            f"/api/v3/pages/{self.profile.pk}/"
        ).json()
        openapi = DjangoClient(HTTP_HOST="localhost").get("/api/v3/openapi.json").json()
        upstream_requests = []

        async def observe_request(request):
            upstream_requests.append(
                (
                    request.method,
                    request.url.path,
                    request.headers.get("Authorization") == f"Bearer {self.token}",
                )
            )

        self.client.event_hooks["request"].append(observe_request)
        server = create_server(openapi, self.client)
        inventory = asyncio.run(server.get_tools())
        resources = asyncio.run(server.get_resources())
        inventory_names = set(inventory)
        self.assertEqual(inventory_names, {
            "list_pages", "create_localized_pair", "find_page", "get_page",
            "update_page_draft", "list_page_revisions", "get_page_revision",
            "list_content_types", "get_content_type_schema", "list_images",
            "create_image", "get_image", "update_image", "list_documents",
            "create_document", "get_document", "update_document",
        })
        self.assertEqual(resources, {})
        self.assertIn(
            "base64 data URL",
            inventory["create_image"].parameters["properties"]["file"]["description"],
        )
        contract = json.dumps(
            [tool.to_mcp_tool().model_dump(mode="json") for tool in inventory.values()]
        )
        self.assertNotIn(self.token, contract)

        captured_logs = []
        discovery_calls = 1
        generation_calls = 0
        generated_payload = None

        def generate_bilingual_article():
            nonlocal generation_calls, generated_payload
            generation_calls += 1
            generated_payload = {
                "type": "portfolio.BlogPostPage",
                "stable_id": "mcp-draft-post",
                "parent_stable_id": "blog",
                "it": {
                    "title": "MCP draft post IT",
                    "slug": "mcp-draft-post-it",
                    "excerpt": "Estratto",
                    "body": "Corpo IT",
                },
                "en": {
                    "title": "MCP draft post EN",
                    "slug": "mcp-draft-post-en",
                    "excerpt": "Excerpt",
                    "body": "Body EN",
                },
            }
            return generated_payload

        class TokenCheckingHandler(logging.Handler):
            def emit(self, record):
                captured_logs.append(self.format(record))

        handler = TokenCheckingHandler()
        components_logger = logging.getLogger("fastmcp.server.openapi.components")
        previous_log_level = components_logger.level
        components_logger.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(handler)
        try:
            read_result = self._call_mcp_tool(
                server, "get_page", {"page_id": self.profile.pk}
            )
            self.assertIn("hero_description", json.dumps(read_result))

            create_result = self._call_mcp_tool(
                server,
                "create_localized_pair",
                generate_bilingual_article(),
            )
            created_id = next(
                page["id"] for page in create_result["pages"] if page["locale"] == "it"
            )
            created_en_id = next(
                page["id"] for page in create_result["pages"] if page["locale"] == "en"
            )
            update_result = self._call_mcp_tool(
                server,
                "update_page_draft",
                {"page_id": created_id, "data": {"title": "MCP revised draft index"}},
            )
            draft_result = self._call_mcp_tool(
                server, "get_page", {"page_id": created_id, "version": "draft"}
            )
            revision_result = self._call_mcp_tool(
                server, "list_page_revisions", {"page_id": created_id}
            )

            image_data = BytesIO()
            PILImage.new("RGB", (2, 2), color="white").save(image_data, format="PNG")
            image_result = self._call_mcp_tool(
                server,
                "create_image",
                {
                    "title": "MCP uploaded.png",
                    "file": (
                        "data:image/png;base64,"
                        + base64.b64encode(image_data.getvalue()).decode("ascii")
                    ),
                },
            )
            image_update_result = self._call_mcp_tool(
                server,
                "update_image",
                {
                    "image_id": image_result["id"],
                    "title": "MCP updated image",
                },
            )
        finally:
            logging.getLogger().removeHandler(handler)
            components_logger.setLevel(previous_log_level)

        results = (
            read_result,
            create_result,
            update_result,
            draft_result,
            revision_result,
            image_result,
            image_update_result,
        )
        self.assertTrue(all(self.token not in repr(result) for result in results))
        self.assertEqual(discovery_calls, 1)
        self.assertEqual(generation_calls, 1)
        self.assertEqual(
            sum(
                method == "GET" and path == "/api/v3/pages/"
                for method, path, _ in upstream_requests
            ),
            0,
        )
        self.assertNotIn("parent_id", json.dumps(generated_payload))
        self.assertEqual(
            sum(
                method == "POST" and path == "/api/v3/localized-pairs/"
                for method, path, _ in upstream_requests
            ),
            1,
        )
        self.assertEqual(
            sum(
                method == "POST" and path == "/api/v3/pages/"
                for method, path, _ in upstream_requests
            ),
            0,
        )
        self.assertTrue(all(self.token not in entry for entry in captured_logs))
        self.assertTrue(upstream_requests)
        self.assertTrue(all(path.startswith("/api/v3/") for _, path, _ in upstream_requests))
        self.assertTrue(all(authenticated for _, _, authenticated in upstream_requests))
        self.assertTrue(
            any(
                method == "POST" and path == "/api/v3/localized-pairs/"
                for method, path, _ in upstream_requests
            )
        )
        self.assertTrue(
            any(
                method == "PATCH" and path.endswith(f"/pages/{created_id}/")
                for method, path, _ in upstream_requests
            )
        )
        self.assertTrue(
            any(
                method == "POST" and path == "/api/v3/images/"
                for method, path, _ in upstream_requests
            )
        )

        self.profile.refresh_from_db()
        public_after = DjangoClient(HTTP_HOST="localhost").get(
            f"/api/v3/pages/{self.profile.pk}/"
        ).json()
        self.assertEqual(public_after, public_before)
        draft = BlogPostPage.objects.get(pk=created_id)
        english_draft = BlogPostPage.objects.get(pk=created_en_id)
        self.assertFalse(draft.live)
        self.assertFalse(english_draft.live)
        self.assertEqual(draft.title, "MCP revised draft index")
        self.assertEqual(draft.stable_id, english_draft.stable_id)
        self.assertEqual(draft.translation_key, english_draft.translation_key)
        self.assertEqual(draft.get_parent().specific_class, BlogIndexPage)
        self.assertEqual(english_draft.get_parent().specific_class, BlogIndexPage)
        self.assertEqual(draft.get_parent().locale_id, draft.locale_id)
        self.assertEqual(english_draft.get_parent().locale_id, english_draft.locale_id)
        self.assertGreater(draft.revisions.count(), 1)
        image = get_image_model().objects.get(title="MCP updated image")
        self.assertEqual(image.collection.name, "Portfolio agent content")
        self.addCleanup(lambda: image.file.delete(save=False))
        self.addCleanup(image.delete)

        source = inspect.getsource(mcp_server)
        self.assertNotIn("django.db", source)
        self.assertNotIn("portfolio.models", source)

    def test_publication_bypass_through_mcp_is_rejected_and_not_logged(self):
        openapi = DjangoClient(HTTP_HOST="localhost").get("/api/v3/openapi.json").json()
        create_server(openapi, self.client)
        public_before = DjangoClient(HTTP_HOST="localhost").get(
            f"/api/v3/pages/{self.profile.pk}/"
        ).json()
        root_id = Site.objects.get(is_default_site=True).root_page_id
        captured_logs = []

        class TokenCheckingHandler(logging.Handler):
            def emit(self, record):
                captured_logs.append(self.format(record))

        handler = TokenCheckingHandler()
        components_logger = logging.getLogger("fastmcp.server.openapi.components")
        previous_log_level = components_logger.level
        components_logger.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(handler)
        try:
            async def attempt_publication_bypass():
                await self.client.post(
                    "/api/v3/pages/",
                    json={
                        "meta": {
                            "type": "portfolio.BlogIndexPage",
                            "parent_id": root_id,
                            "action": "publish",
                        },
                        "title": "Must remain unpublished",
                        "slug": "mcp-publish-bypass",
                        "stable_id": "mcp-publish-bypass",
                    },
                )

            with self.assertRaisesRegex(
                ValueError, "Publication actions are not available"
            ):
                asyncio.run(attempt_publication_bypass())
        finally:
            logging.getLogger().removeHandler(handler)
            components_logger.setLevel(previous_log_level)

        self.assertTrue(all(self.token not in entry for entry in captured_logs))
        self.assertFalse(BlogIndexPage.objects.filter(slug="mcp-publish-bypass").exists())
        self.assertEqual(
            DjangoClient(HTTP_HOST="localhost").get(
                f"/api/v3/pages/{self.profile.pk}/"
            ).json(),
            public_before,
        )

    def test_composed_asgi_streamable_http_auth_and_bounded_draft(self):
        from django.core.asgi import get_asgi_application

        from .mcp_asgi import compose_asgi

        inbound = "separate-inbound-test-token"
        upstream = self.token
        expected_tools = {
            "list_pages", "create_localized_pair", "find_page", "get_page",
            "update_page_draft", "list_page_revisions", "get_page_revision",
            "list_content_types", "get_content_type_schema", "list_images",
            "create_image", "get_image", "update_image", "list_documents",
            "create_document", "get_document", "update_document",
        }
        with patch.dict(os.environ, {
            "PDPW_MCP_INBOUND_TOKEN": inbound,
            "WAGTAIL_AGENT_API_TOKEN": upstream,
            "PDPW_MCP_ALLOWED_ORIGINS": "https://trusted.example",
        }):
            app = compose_asgi(get_asgi_application())

        async def exercise():
            async with app.mcp_app.router.lifespan_context(app.mcp_app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://localhost",
                    follow_redirects=False,
                ) as client:
                    init_body = {
                        "jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26", "capabilities": {},
                            "clientInfo": {"name": "transport-test", "version": "1"},
                        },
                    }
                    missing = await client.post("/mcp", json=init_body)
                    self.assertEqual(missing.status_code, 401)
                    self.assertTrue(missing.headers["www-authenticate"].startswith("Bearer"))
                    for bad_token in ("wrong", upstream):
                        rejected = await client.post(
                            "/mcp", json=init_body,
                            headers={"Authorization": f"Bearer {bad_token}"},
                        )
                        self.assertEqual(rejected.status_code, 401)
                        self.assertIn("Bearer", rejected.headers["www-authenticate"])

                    headers = {
                        "Authorization": f"Bearer {inbound}",
                        "Accept": "application/json",
                    }
                    for path in ("/mcp", "/mcp/"):
                        response = await client.post(path, json=init_body, headers=headers)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json()["result"]["protocolVersion"], "2025-03-26")
                    for origin_headers, expected_status in (
                        ({}, 200),
                        ({"Origin": "https://trusted.example"}, 200),
                        ({"Origin": "https://foreign.example"}, 403),
                        ({"Origin": "null"}, 403),
                        (
                            [
                                ("Origin", "https://trusted.example"),
                                ("Origin", "https://trusted.example"),
                            ],
                            403,
                        ),
                    ):
                        response = await client.post(
                            "/mcp", json=init_body,
                            headers=[*headers.items(), *(
                                origin_headers.items() if isinstance(origin_headers, dict)
                                else origin_headers
                            )],
                        )
                        self.assertEqual(response.status_code, expected_status)

                    unauthenticated_get = await client.get("/mcp")
                    self.assertEqual(unauthenticated_get.status_code, 401)
                    self.assertIn(
                        "Bearer", unauthenticated_get.headers["www-authenticate"]
                    )
                    get_response = await client.get("/mcp", headers=headers)
                    self.assertEqual(get_response.status_code, 405)
                    self.assertNotIn(
                        "text/event-stream", get_response.headers.get("content-type", "")
                    )

                    tools_response = await client.post(
                        "/mcp",
                        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                        headers=headers,
                    )
                    self.assertEqual(
                        {tool["name"] for tool in tools_response.json()["result"]["tools"]},
                        expected_tools,
                    )
                    read_response = await client.post(
                        "/mcp",
                        json={
                            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                            "params": {
                                "name": "get_page",
                                "arguments": {"page_id": self.profile.pk},
                            },
                        },
                        headers=headers,
                    )
                    self.assertEqual(read_response.status_code, 200)
                    self.assertNotIn("error", read_response.json())
                    draft_response = await client.post(
                        "/mcp",
                        json={
                            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
                            "params": {
                                "name": "create_localized_pair",
                                "arguments": {
                                    "type": "portfolio.BlogPostPage",
                                    "stable_id": "pdpw-63-mcp-transport-test",
                                    "parent_stable_id": "blog",
                                    "it": {
                                        "title": "MCP transport IT draft",
                                        "slug": "pdpw-63-mcp-transport-it",
                                        "excerpt": "Bozza",
                                        "body": "Contenuto IT",
                                    },
                                    "en": {
                                        "title": "MCP transport EN draft",
                                        "slug": "pdpw-63-mcp-transport-en",
                                        "excerpt": "Draft",
                                        "body": "English content",
                                    },
                                },
                            },
                        },
                        headers=headers,
                    )
                    self.assertEqual(draft_response.status_code, 200, draft_response.text)
                    result = draft_response.json()["result"]
                    self.assertNotIn("isError", result)
                    page_ids = [page["id"] for page in result["structuredContent"]["pages"]]
                    for page_id in page_ids:
                        public_response = await client.get(
                            f"/api/v3/pages/{page_id}/", headers={"Host": "localhost"}
                        )
                        self.assertEqual(public_response.status_code, 404)
                    response_text = json.dumps(
                        [missing.text, tools_response.text, read_response.text, draft_response.text]
                    )
                    self.assertNotIn(inbound, response_text)
                    self.assertNotIn(upstream, response_text)

        asyncio.run(exercise())
