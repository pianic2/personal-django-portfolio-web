from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

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
