"""Compose the authenticated, stateless MCP endpoint with Django ASGI."""

from __future__ import annotations

import json
import os
from urllib.parse import urlsplit

import httpx
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from wagtail.api.v3.urls import api as wagtail_api

from .mcp_server import (
    _BearerTokenAuth,
    _encode_media_upload,
    _InboundTokenVerifier,
    _reject_publication_bypass_async,
    create_server,
)


def _allowed_origins() -> set[str]:
    return {
        value.strip()
        for value in os.environ.get("PDPW_MCP_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    }


class MCPBoundary:
    """Route MCP requests and enforce the endpoint's narrow Origin policy."""

    def __init__(self, django_app, mcp_app, verifier, allowed_origins):
        self.django_app = django_app
        self.mcp_app = mcp_app
        self.verifier = verifier
        self.allowed_origins = allowed_origins

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await self.mcp_app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path not in {"/mcp", "/mcp/"}:
            await self.django_app(scope, receive, send)
            return

        headers = scope.get("headers", [])
        authorization_values = [
            value.decode("latin-1")
            for name, value in headers
            if name.lower() == b"authorization"
        ]
        if len(authorization_values) > 1:
            await _respond(
                send, 401, b"Unauthorized", [(b"www-authenticate", b"Bearer")]
            )
            return
        origins = [value.decode("latin-1") for name, value in headers if name.lower() == b"origin"]
        if len(origins) > 1 or (
            origins and not _valid_origin(origins[0], self.allowed_origins)
        ):
            await _respond(send, 403, b"Forbidden")
            return
        # This is a Streamable HTTP JSON endpoint. Never offer the SDK's GET/SSE route.
        if scope.get("method") == "GET":
            authorization = authorization_values[0] if authorization_values else ""
            scheme, separator, token = authorization.partition(" ")
            verified = (
                await self.verifier.verify_token(token)
                if separator and scheme.casefold() == "bearer"
                else None
            )
            if verified is None:
                await _respond(
                    send, 401, b"Unauthorized", [(b"www-authenticate", b"Bearer")]
                )
                return
            await _respond(
                send, 405, b"Method Not Allowed", [(b"allow", b"POST, DELETE")]
            )
            return
        normalized = dict(scope, path="/mcp")
        await self.mcp_app(normalized, receive, send)


def _valid_origin(value: str, allowed_origins: set[str] | None = None) -> bool:
    if value == "null" or value != value.strip():
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
        valid = (
            parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
            and (port is None or 1 <= port <= 65535)
            and parsed.username is None
            and parsed.password is None
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
        )
        return valid and value in (
            allowed_origins if allowed_origins is not None else _allowed_origins()
        )
    except ValueError:
        return False


async def _respond(send, status: int, body: bytes, extra_headers=()):
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"text/plain; charset=utf-8"), *extra_headers],
    })
    await send({"type": "http.response.body", "body": body})


def compose_asgi(django_app):
    """Create MCP routes without network calls during application construction."""
    # Ensure custom Wagtail/Ninja routers are registered before schema generation.
    from . import urls as _urls  # noqa: F401

    token = os.environ.get("WAGTAIL_AGENT_API_TOKEN", "")
    if not token:
        raise RuntimeError("WAGTAIL_AGENT_API_TOKEN is required for the MCP service.")
    allowed_hosts = [host for host in settings.ALLOWED_HOSTS if host != "*"]
    internal_host = allowed_hosts[0] if allowed_hosts else "localhost"
    client = httpx.AsyncClient(
        base_url=f"http://{internal_host}",
        transport=httpx.ASGITransport(app=django_app),
        auth=_BearerTokenAuth(token),
        timeout=30.0,
        event_hooks={"request": [_reject_publication_bypass_async, _encode_media_upload]},
    )
    schema = json.loads(json.dumps(
        wagtail_api.get_openapi_schema(path_prefix="/api/v3"),
        cls=DjangoJSONEncoder,
    ))
    verifier = _InboundTokenVerifier()
    server = create_server(schema, client, auth_verifier=verifier)
    mcp_app = server.http_app(
        path="/mcp",
        transport="streamable-http",
        stateless_http=True,
        json_response=True,
    )
    # FastMCP's lifespan owns server startup/shutdown; close its internal client
    # as part of the same ASGI lifecycle.
    original_lifespan = mcp_app.router.lifespan_context

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        try:
            async with original_lifespan(app):
                yield
        finally:
            await client.aclose()

    mcp_app.router.lifespan_context = lifespan
    return MCPBoundary(django_app, mcp_app, verifier, _allowed_origins())
