from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

from django.test import SimpleTestCase

from .mcp_asgi import _valid_origin
from .mcp_server import _InboundTokenVerifier


class MCPASGISecurityConfigTests(SimpleTestCase):
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
