import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from asgiref.sync import sync_to_async
from cryptography.fernet import Fernet
from django.core.management import call_command
from django.test import override_settings
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
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
    assert proxy.required_scopes == ["openid", "email", "profile"]
    assert proxy._default_scope_str == "openid email profile"
    assert proxy.client_registration_options.valid_scopes == ["mcp:read", "mcp:draft"]
    upstream_url = proxy._build_upstream_authorize_url("transaction", {})
    assert parse_qs(urlsplit(upstream_url).query)["scope"] == ["openid email profile"]


class OAuthTests(IsolatedAsyncioTestCase):
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
