import asyncio
import base64
import hashlib
import re
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from asgiref.sync import sync_to_async
from authlib.integrations.httpx_client import AsyncOAuth2Client
from cryptography.fernet import Fernet
from django.core.management import call_command
from django.test import override_settings
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from starlette.applications import Starlette
from starlette.routing import Router

from .mcp_oauth import DatabaseCacheKeyValue, GoogleIdentityVerifier, create_oauth_proxy


def test_oauth_is_disabled_until_all_production_secrets_are_configured(monkeypatch):
    for name in (
        "PDPW_OAUTH_UPSTREAM_CLIENT_ID",
        "PDPW_OAUTH_UPSTREAM_CLIENT_SECRET",
        "PDPW_OAUTH_JWT_SIGNING_KEY",
        "PDPW_OAUTH_ALLOWED_IDENTITIES",
        "PDPW_OAUTH_STORAGE_ENCRYPTION_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    assert create_oauth_proxy() is None


def test_oauth_requires_a_complete_secret_set(monkeypatch):
    monkeypatch.setenv("PDPW_OAUTH_UPSTREAM_CLIENT_ID", "client")
    with pytest.raises(RuntimeError, match="PDPW_OAUTH_UPSTREAM_CLIENT_SECRET"):
        create_oauth_proxy()


def test_oauth_requires_a_separate_storage_encryption_key(monkeypatch):
    for name, value in {
        "PDPW_OAUTH_UPSTREAM_CLIENT_ID": "client",
        "PDPW_OAUTH_UPSTREAM_CLIENT_SECRET": "secret",
        "PDPW_OAUTH_JWT_SIGNING_KEY": "long-signing-key",
        "PDPW_OAUTH_ALLOWED_IDENTITIES": "nome@example.com",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("PDPW_OAUTH_STORAGE_ENCRYPTION_KEY", raising=False)
    with pytest.raises(RuntimeError, match="PDPW_OAUTH_STORAGE_ENCRYPTION_KEY"):
        create_oauth_proxy()


def test_oauth_rejects_reusing_jwt_signing_key_for_storage(monkeypatch):
    for name, value in {
        "PDPW_OAUTH_UPSTREAM_CLIENT_ID": "client",
        "PDPW_OAUTH_UPSTREAM_CLIENT_SECRET": "secret",
        "PDPW_OAUTH_JWT_SIGNING_KEY": "same-secret",
        "PDPW_OAUTH_ALLOWED_IDENTITIES": "nome@example.com",
        "PDPW_OAUTH_STORAGE_ENCRYPTION_KEY": "same-secret",
    }.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match="must differ"):
        create_oauth_proxy()


def test_oauth_proxy_allowlists_only_provider_redirects(monkeypatch):
    monkeypatch.setenv("PDPW_OAUTH_UPSTREAM_CLIENT_ID", "client")
    monkeypatch.setenv("PDPW_OAUTH_UPSTREAM_CLIENT_SECRET", "secret")
    monkeypatch.setenv("PDPW_OAUTH_JWT_SIGNING_KEY", "long-signing-key")
    monkeypatch.setenv("PDPW_OAUTH_ALLOWED_IDENTITIES", "nome@example.com")
    monkeypatch.setenv("PDPW_OAUTH_STORAGE_ENCRYPTION_KEY", Fernet.generate_key().decode())
    proxy = create_oauth_proxy()
    assert proxy is not None
    assert proxy._allowed_client_redirect_uris == [
        "https://chatgpt.com/connector_platform_oauth_redirect",
        "https://claude.ai/api/mcp/auth_callback",
    ]
    assert isinstance(proxy._client_storage, FernetEncryptionWrapper)


def test_oauth_proxy_exposes_metadata_dcr_and_pkce_routes(monkeypatch):
    for name, value in {
        "PDPW_OAUTH_UPSTREAM_CLIENT_ID": "client",
        "PDPW_OAUTH_UPSTREAM_CLIENT_SECRET": "secret",
        "PDPW_OAUTH_JWT_SIGNING_KEY": "long-signing-key",
        "PDPW_OAUTH_ALLOWED_IDENTITIES": "nome@example.com",
        "PDPW_OAUTH_STORAGE_ENCRYPTION_KEY": Fernet.generate_key().decode(),
    }.items():
        monkeypatch.setenv(name, value)
    proxy = create_oauth_proxy()
    assert proxy is not None
    routes = {route.path for route in proxy.get_routes("/mcp")}
    assert {
        "/.well-known/oauth-authorization-server",
        "/register",
        "/authorize",
        "/token",
        "/auth/callback",
    } <= routes
    assert str(proxy._resource_url) == "https://pdpw-production.onrender.com/mcp"
    assert proxy.required_scopes == ["mcp:read", "mcp:draft"]
    assert proxy._default_scope_str == "mcp:read mcp:draft"
    assert proxy.client_registration_options.valid_scopes == ["mcp:read", "mcp:draft"]


class OAuthTests(IsolatedAsyncioTestCase):
    async def test_claude_authorization_sends_google_only_scopes_and_keeps_mcp_scopes(self):
        proxy = create_oauth_proxy_for_test()
        app = Starlette(routes=proxy.get_routes("/mcp"))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://pdpw-production.onrender.com"
        ) as client:
            metadata = await client.get("/.well-known/oauth-authorization-server")
            assert {"mcp:read", "mcp:draft"} <= set(metadata.json()["scopes_supported"])

            registration = await client.post(
                "/register",
                json={
                    "client_name": "Claude",
                    "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
                    "grant_types": ["authorization_code", "refresh_token"],
                    "response_types": ["code"],
                    "token_endpoint_auth_method": "none",
                    "scope": "mcp:read mcp:draft",
                },
            )
            assert registration.status_code in {200, 201}
            assert registration.json()["scope"] == "mcp:read mcp:draft"
            client_id = registration.json()["client_id"]

            authorize = await client.get(
                "/authorize",
                params={
                    "client_id": client_id,
                    "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
                    "response_type": "code",
                    "scope": "mcp:read mcp:draft",
                    "state": "claude-state",
                    "code_challenge": base64.urlsafe_b64encode(
                        hashlib.sha256(b"claude-verifier").digest()
                    ).decode().rstrip("="),
                    "code_challenge_method": "S256",
                    "resource": "https://pdpw-production.onrender.com/mcp",
                },
            )
            assert authorize.status_code == 302
            consent = await client.get(authorize.headers["location"])
            assert consent.status_code == 200
            csrf_token = re.search(
                r'name="csrf_token" value="([^"]+)"', consent.text
            ).group(1)
            consent_txn = parse_qs(urlsplit(authorize.headers["location"]).query)[
                "txn_id"
            ][0]
            transaction = await proxy._transaction_store.get(key=consent_txn)
            assert transaction.scopes == ["mcp:read", "mcp:draft"]

            approved = await client.post(
                "/consent",
                data={
                    "txn_id": consent_txn,
                    "csrf_token": csrf_token,
                    "action": "approve",
                },
            )
            assert approved.status_code == 302
            google_authorize = parse_qs(urlsplit(approved.headers["location"]).query)
            assert google_authorize["scope"] == ["openid email profile"]
            assert not {"mcp:read", "mcp:draft"} & set(
                google_authorize["scope"][0].split()
            )

            google_client = MagicMock()
            google_client.fetch_token = AsyncMock(
                return_value={
                    "access_token": "google-access-token",
                    "refresh_token": "google-refresh-token",
                    "expires_in": 3600,
                }
            )
            with patch(
                "fastmcp.server.auth.oauth_proxy.AsyncOAuth2Client",
                return_value=google_client,
            ):
                callback = await client.get(
                    "/auth/callback",
                    params={"code": "google-code", "state": consent_txn},
                )
            assert callback.status_code == 302
            client_callback = parse_qs(urlsplit(callback.headers["location"]).query)
            downstream_code = client_callback["code"][0]
            stored_code = await proxy._code_store.get(key=downstream_code)
            assert stored_code.scopes == ["mcp:read", "mcp:draft"]

            token_response = await client.post(
                "/token",
                data={
                    "grant_type": "authorization_code",
                    "code": downstream_code,
                    "client_id": client_id,
                    "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
                    "code_verifier": "claude-verifier",
                },
            )
            assert token_response.status_code == 200
            assert token_response.json()["scope"] == "mcp:read mcp:draft"

    async def test_upstream_refresh_omits_downstream_mcp_scopes(self):
        proxy = create_oauth_proxy_for_test()
        proxy.get_routes("/mcp")
        proxy.jwt_issuer.verify_token = MagicMock(return_value={"jti": "refresh-jti"})
        upstream_token = MagicMock(
            upstream_token_id="upstream-id",
            refresh_token="google-refresh-token",
            refresh_token_expires_at=None,
            raw_token_data={},
        )
        proxy._jti_mapping_store = MagicMock()
        proxy._jti_mapping_store.get = AsyncMock(
            return_value=MagicMock(upstream_token_id="upstream-id")
        )
        proxy._jti_mapping_store.put = AsyncMock()
        proxy._jti_mapping_store.delete = AsyncMock()
        proxy._upstream_token_store = MagicMock()
        proxy._upstream_token_store.get = AsyncMock(return_value=upstream_token)
        proxy._upstream_token_store.put = AsyncMock()
        proxy._refresh_token_store = MagicMock()
        proxy._refresh_token_store.put = AsyncMock()
        proxy._refresh_token_store.delete = AsyncMock()
        requests = []

        async def respond(request):
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "access_token": "new-google-access-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )

        oauth_client = AsyncOAuth2Client(
            client_id="client",
            client_secret="secret",
            transport=httpx.MockTransport(respond),
        )
        with patch(
            "fastmcp.server.auth.oauth_proxy.AsyncOAuth2Client",
            return_value=oauth_client,
        ):
            result = await proxy.exchange_refresh_token(
                client=MagicMock(client_id="claude-client"),
                refresh_token=MagicMock(token="fastmcp-refresh-token"),
                scopes=["mcp:read", "mcp:draft"],
            )
        assert result.scope == "mcp:read mcp:draft"
        assert len(requests) == 1
        form = parse_qs(requests[0].content.decode())
        assert "scope" not in form
        assert not {"mcp:read", "mcp:draft"} & set(form.get("scope", []))
        await oauth_client.aclose()

    async def test_google_verifier_requires_verified_allowlisted_email_and_binds_subject(self):
        verifier = GoogleIdentityVerifier({"nome@example.com"}, "https://userinfo.example")
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "sub": "google-subject", "email": "nome@example.com", "email_verified": True
        }
        with patch("portfolio.mcp_oauth.httpx.AsyncClient.get", return_value=response):
            token = await verifier.verify_token("upstream-token")
        assert token is not None
        assert token.subject == "google-subject"
        assert token.client_id == "google:google-subject"
        assert token.scopes == ["mcp:read", "mcp:draft"]


    async def test_google_verifier_rejects_non_allowlisted_identity(self):
        verifier = GoogleIdentityVerifier({"nome@example.com"}, "https://userinfo.example")
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "sub": "other-subject", "email": "other@example.com", "email_verified": True
        }
        with patch("portfolio.mcp_oauth.httpx.AsyncClient.get", return_value=response):
            assert await verifier.verify_token("upstream-token") is None

    async def test_google_verifier_rejects_missing_or_unverified_claims(self):
        verifier = GoogleIdentityVerifier({"nome@example.com"}, "https://userinfo.example")
        for claims in (
            {"email": "nome@example.com", "email_verified": True},
            {"sub": "subject", "email": "nome@example.com", "email_verified": False},
            {"sub": "subject", "email": "nome@example.com", "email_verified": "true"},
            {"sub": "subject", "email": "nome@example.com"},
        ):
            response = MagicMock(status_code=200)
            response.json.return_value = claims
            with patch("portfolio.mcp_oauth.httpx.AsyncClient.get", return_value=response):
                assert await verifier.verify_token("upstream-token") is None


    async def test_database_cache_store_keeps_collections_separate(self):
        store = DatabaseCacheKeyValue()
        with patch("portfolio.mcp_oauth.cache.set") as set_cache, patch(
            "portfolio.mcp_oauth.cache.get", return_value={"value": "ok"}
        ):
            await store.put("key", {"value": "ok"}, collection="oauth")
            assert await store.get("key", collection="oauth") == {"value": "ok"}
        set_cache.assert_called_once()
        assert set_cache.call_args.args[0] == "pdpw-oauth:oauth:key"

    async def test_encrypted_store_persists_across_instances_and_deletes(self):
        key = Fernet.generate_key()
        raw = {}

        def cache_set(name, value, timeout):
            assert timeout == 30
            raw[name] = value

        def cache_get(name):
            return raw.get(name)

        with patch("portfolio.mcp_oauth.cache.set", side_effect=cache_set), patch(
            "portfolio.mcp_oauth.cache.get", side_effect=cache_get
        ), patch(
            "portfolio.mcp_oauth.cache.delete",
            side_effect=lambda name: raw.pop(name, None) is not None,
        ):
            first = FernetEncryptionWrapper(
                DatabaseCacheKeyValue(), fernet=Fernet(key)
            )
            await first.put("state", {"secret": "oauth-code"}, collection="transactions", ttl=30)
            stored = raw["pdpw-oauth:transactions:state"]
            assert stored["__encryption_version__"] == 1
            assert "oauth-code" not in repr(stored)
            second = FernetEncryptionWrapper(
                DatabaseCacheKeyValue(), fernet=Fernet(key)
            )
            assert await second.get("state", collection="transactions") == {
                "secret": "oauth-code"
            }
            assert await second.delete("state", collection="transactions")
            assert await second.get("state", collection="transactions") is None

    @pytest.mark.django_db
    async def test_encrypted_store_uses_database_cache_ttl_and_expiry(self):
        cache_settings = {
            "default": {
                "BACKEND": "django.core.cache.backends.db.DatabaseCache",
                "LOCATION": "django_cache_table",
            }
        }
        with override_settings(CACHES=cache_settings):
            from django.core.cache import cache, caches

            caches.close_all()
            if hasattr(caches._connections, "default"):
                del caches._connections.default
            await sync_to_async(call_command)(
                "createcachetable", "django_cache_table", verbosity=0
            )
            await sync_to_async(cache.clear)()
            key = Fernet.generate_key()
            store = FernetEncryptionWrapper(
                DatabaseCacheKeyValue(), fernet=Fernet(key)
            )
            await store.put(
                "state", {"secret": "oauth-code"}, collection="transactions", ttl=2
            )
            value, ttl = await store.ttl("state", collection="transactions")
            assert value == {"secret": "oauth-code"}
            assert ttl is not None and 0 < ttl <= 2
            await asyncio.sleep(2.1)
            assert await store.get("state", collection="transactions") is None
            await store.put(
                "state", {"secret": "oauth-code"}, collection="transactions", ttl=30
            )
            await store.delete("state", collection="transactions")
            assert await store.get("state", collection="transactions") is None
            from django.db import close_old_connections

            await sync_to_async(close_old_connections)()

    async def test_oauth_discovery_and_invalid_token_routes(self):
        proxy = create_oauth_proxy_for_test()
        app = Router(routes=proxy.get_routes("/mcp"))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="https://pdpw.example"
        ) as client:
            metadata = await client.get("/.well-known/oauth-authorization-server")
            assert metadata.status_code == 200
            assert metadata.json()["issuer"] == "https://pdpw-production.onrender.com/"
            assert metadata.json()["code_challenge_methods_supported"] == ["S256"]
            token = await client.post("/token", data={"grant_type": "authorization_code"})
            assert token.status_code == 401
            assert token.json()["error"] == "invalid_client"


def create_oauth_proxy_for_test():
    values = {
        "PDPW_OAUTH_UPSTREAM_CLIENT_ID": "client",
        "PDPW_OAUTH_UPSTREAM_CLIENT_SECRET": "secret",
        "PDPW_OAUTH_JWT_SIGNING_KEY": "a-long-signing-key",
        "PDPW_OAUTH_ALLOWED_IDENTITIES": "nome@example.com",
        "PDPW_OAUTH_STORAGE_ENCRYPTION_KEY": Fernet.generate_key().decode(),
    }
    with patch.dict("os.environ", values):
        return create_oauth_proxy()
