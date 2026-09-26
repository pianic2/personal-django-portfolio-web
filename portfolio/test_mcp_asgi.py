from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import httpx
from django.test import SimpleTestCase

from .mcp_asgi import MCPBoundary, _DjangoASGIAuthorityAdapter, _valid_origin
from .mcp_server import _InboundTokenVerifier


class MCPASGISecurityConfigTests(SimpleTestCase):
    def test_oauth_boundary_routes_only_mcp_and_exact_oauth_paths_to_mcp_app(self):
        calls = []

        async def record(name):
            async def app(scope, receive, send):
                calls.append((name, scope["path"]))
                await send({"type": "http.response.start", "status": 200, "headers": []})
                await send({"type": "http.response.body", "body": b"ok"})

            return app

        async def run():
            calls.clear()

            async def send(message):
                return None

            class Verifier:
                async def verify_token(self, token):
                    return object() if token == "token" else None

            boundary = MCPBoundary(
                await record("django"),
                await record("mcp"),
                verifier=Verifier(),
                allowed_origins=set(),
                oauth_enabled=True,
                oauth_paths={
                    "/.well-known/oauth-authorization-server", "/authorize", "/token",
                    "/register", "/revoke", "/.well-known/oauth-protected-resource/mcp",
                    "/auth/callback", "/consent",
                },
            )
            await boundary(
                {
                    "type": "http",
                    "path": "/mcp",
                    "method": "POST",
                    "headers": [(b"authorization", b"Bearer token")],
                },
                None,
                send,
            )
            for path in (
                "/.well-known/oauth-authorization-server",
                "/authorize",
                "/token",
                "/register",
                "/revoke",
                "/.well-known/oauth-protected-resource/mcp",
                "/auth/callback", "/consent", "/admin/", "/api/v3/pages/",
                "/ordinary-django-path/",
            ):
                await boundary(
                    {"type": "http", "path": path, "method": "GET", "headers": []},
                    None,
                    send,
                )

        asyncio.run(run())
        self.assertEqual(
            calls,
            [
                ("mcp", "/mcp"),
                ("mcp", "/.well-known/oauth-authorization-server"),
                ("mcp", "/authorize"),
                ("mcp", "/token"),
                ("mcp", "/register"),
                ("mcp", "/revoke"),
                ("mcp", "/.well-known/oauth-protected-resource/mcp"),
                ("mcp", "/auth/callback"),
                ("mcp", "/consent"),
                ("django", "/admin/"),
                ("django", "/api/v3/pages/"),
                ("django", "/ordinary-django-path/"),
            ],
        )

    def test_internal_asgi_adapter_preserves_default_and_nondefault_ports(self):
        self.assertIsNone(httpx.URL("https://localhost").port)
        observed = []

        async def inspect_scope(scope, receive, send):
            observed.append((scope["scheme"], scope["server"][1]))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        async def exercise():
            adapter = _DjangoASGIAuthorityAdapter(inspect_scope)
            for base_url, expected_port in (
                ("https://localhost", 443),
                ("https://localhost:8443", 8443),
            ):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=adapter),
                    base_url=base_url,
                ) as client:
                    response = await client.get("/probe")
                    self.assertEqual(response.status_code, 200)
                self.assertEqual(observed[-1], ("https", expected_port))

        asyncio.run(exercise())

    def test_inbound_verifier_accepts_only_dedicated_token(self):
        async def verify(token):
            return await _InboundTokenVerifier().verify_token(token)

        with patch.dict(os.environ, {
            "PDPW_MCP_INBOUND_TOKEN": "inbound-secret",
            "WAGTAIL_AGENT_API_TOKEN": "wagtail-service-secret",
        }):
            self.assertIsNotNone(asyncio.run(verify("inbound-secret")))
            for token in ("", "invalid", " wagtail-service-secret",
                          "wagtail-service-secret", "inbound-secret "):
                with self.subTest(token=token):
                    self.assertIsNone(asyncio.run(verify(token)))

        with patch.dict(os.environ, {
            "PDPW_MCP_INBOUND_TOKEN": "",
            "WAGTAIL_AGENT_API_TOKEN": "wagtail-service-secret",
        }):
            self.assertIsNone(asyncio.run(verify("inbound-secret")))

    def test_origin_policy_requires_exact_well_formed_configured_origin(self):
        with patch.dict(os.environ, {
            "PDPW_MCP_ALLOWED_ORIGINS": "https://trusted.example,http://localhost:3000",
        }):
            self.assertTrue(_valid_origin("https://trusted.example"))
            self.assertTrue(_valid_origin("http://localhost:3000"))
            for origin in (
                "https://foreign.example",
                "null",
                "https://trusted.example/path",
                "https://trusted.example:invalid",
                " https://trusted.example",
            ):
                with self.subTest(origin=origin):
                    self.assertFalse(_valid_origin(origin))
