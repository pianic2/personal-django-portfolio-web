"""FastMCP OAuth 2.1 configuration for the provider-facing MCP endpoint."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, SupportsFloat

import httpx
from asgiref.sync import sync_to_async
from cryptography.fernet import Fernet
from django.core.cache import cache, caches
from django.db import connections, router
from django.utils import timezone
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper


class DatabaseCacheKeyValue:
    """Async key-value facade over the existing shared Django cache table."""

    def _key(self, collection: str | None, key: str) -> str:
        return f"pdpw-oauth:{collection or 'default'}:{key}"

    async def get(self, key: str, *, collection: str | None = None) -> dict[str, Any] | None:
        value = await sync_to_async(cache.get)(self._key(collection, key))
        return value if isinstance(value, dict) else None

    async def put(
        self,
        key: str,
        value: Mapping[str, Any],
        *,
        collection: str | None = None,
        ttl: SupportsFloat | None = None,
    ) -> None:
        timeout = None if ttl is None else max(1, int(float(ttl)))
        await sync_to_async(cache.set)(self._key(collection, key), dict(value), timeout)

    async def delete(self, key: str, *, collection: str | None = None) -> bool:
        return bool(await sync_to_async(cache.delete)(self._key(collection, key)))

    async def get_many(self, keys: Sequence[str], *, collection: str | None = None):
        return [await self.get(key, collection=collection) for key in keys]

    async def ttl(self, key: str, *, collection: str | None = None):
        value, expires = await sync_to_async(self._get_with_expiry)(
            key, collection=collection
        )
        if expires is None:
            return value, None
        remaining = (expires - timezone.now()).total_seconds()
        return value, max(0.0, remaining)

    async def ttl_many(self, keys: Sequence[str], *, collection: str | None = None):
        return [await self.ttl(key, collection=collection) for key in keys]

    async def put_many(
        self,
        keys: Sequence[str],
        values: Sequence[Mapping[str, Any]],
        *,
        collection: str | None = None,
        ttl: SupportsFloat | None = None,
    ) -> None:
        for key, value in zip(keys, values, strict=True):
            await self.put(key, value, collection=collection, ttl=ttl)

    async def delete_many(self, keys: Sequence[str], *, collection: str | None = None) -> int:
        return sum([await self.delete(key, collection=collection) for key in keys])

    def _get_with_expiry(
        self, key: str, *, collection: str | None = None
    ) -> tuple[dict[str, Any] | None, datetime | None]:
        """Read a database cache value and its expiry in one backend operation."""
        backend = caches["default"]
        table = getattr(backend, "_table", None)
        if table is None:
            return cache.get(self._key(collection, key)), None

        cache_key = backend.make_and_validate_key(self._key(collection, key))
        connection = connections[router.db_for_read(backend.cache_model_class)]
        quote_name = connection.ops.quote_name
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {quote_name('value')}, {quote_name('expires')} "
                f"FROM {quote_name(table)} WHERE {quote_name('cache_key')} = %s",
                [cache_key],
            )
            row = cursor.fetchone()
        if row is None:
            return None, None
        value = cache.get(self._key(collection, key))
        if value is None:
            return None, None
        expires = row[1]
        if timezone.is_naive(expires):
            expires = timezone.make_aware(expires)
        return value if isinstance(value, dict) else None, expires


class GoogleIdentityVerifier(TokenVerifier):
    """Validate Google userinfo and authorize only the configured identity."""

    def __init__(self, allowed_identities: set[str], userinfo_endpoint: str) -> None:
        super().__init__()
        self.allowed_identities = allowed_identities
        self.userinfo_endpoint = userinfo_endpoint

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or token != token.strip():
            return None
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    self.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {token}"},
                )
            if response.status_code != 200:
                return None
            claims = response.json()
        except (httpx.HTTPError, ValueError):
            return None
        subject = claims.get("sub")
        email = claims.get("email")
        if (
            not isinstance(subject, str)
            or not subject
            or not isinstance(email, str)
            or claims.get("email_verified") is not True
            or email.casefold() not in self.allowed_identities
        ):
            return None
        return AccessToken(
            token=token,
            client_id=f"google:{subject}",
            scopes=["mcp:read", "mcp:draft"],
            subject=subject,
            claims={"sub": subject, "email": email},
        )


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required when OAuth is configured.")
    return value


def create_oauth_proxy() -> OAuthProxy | None:
    """Build the single canonical OAuth proxy when its complete config is present."""
    names = (
        "PDPW_OAUTH_UPSTREAM_CLIENT_ID",
        "PDPW_OAUTH_UPSTREAM_CLIENT_SECRET",
        "PDPW_OAUTH_JWT_SIGNING_KEY",
        "PDPW_OAUTH_ALLOWED_IDENTITIES",
        "PDPW_OAUTH_STORAGE_ENCRYPTION_KEY",
    )
    configured = [bool(os.environ.get(name, "").strip()) for name in names]
    if not any(configured):
        return None
    values = {name: _required(name) for name in names}
    if values["PDPW_OAUTH_STORAGE_ENCRYPTION_KEY"] == values["PDPW_OAUTH_JWT_SIGNING_KEY"]:
        raise RuntimeError(
            "PDPW_OAUTH_STORAGE_ENCRYPTION_KEY must differ from "
            "PDPW_OAUTH_JWT_SIGNING_KEY."
        )
    allowed = {
        value.strip().casefold()
        for value in values["PDPW_OAUTH_ALLOWED_IDENTITIES"].split(",")
        if value.strip()
    }
    if not allowed:
        raise RuntimeError("PDPW_OAUTH_ALLOWED_IDENTITIES must contain an email address.")
    verifier = GoogleIdentityVerifier(
        allowed_identities=allowed,
        userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
    )
    return OAuthProxy(
        upstream_authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
        upstream_token_endpoint="https://oauth2.googleapis.com/token",
        upstream_revocation_endpoint="https://oauth2.googleapis.com/revoke",
        upstream_client_id=values["PDPW_OAUTH_UPSTREAM_CLIENT_ID"],
        upstream_client_secret=values["PDPW_OAUTH_UPSTREAM_CLIENT_SECRET"],
        token_verifier=verifier,
        base_url=os.environ.get("PDPW_OAUTH_BASE_URL", "https://pdpw-production.onrender.com"),
        redirect_path="/auth/callback",
        issuer_url=os.environ.get("PDPW_OAUTH_ISSUER_URL", "https://pdpw-production.onrender.com"),
        allowed_client_redirect_uris=[
            "https://chatgpt.com/connector_platform_oauth_redirect",
            "https://claude.ai/api/mcp/auth_callback",
        ],
        valid_scopes=["mcp:read", "mcp:draft"],
        forward_pkce=True,
        extra_authorize_params={"access_type": "offline", "prompt": "consent"},
        extra_token_params={"access_type": "offline"},
        client_storage=FernetEncryptionWrapper(
            DatabaseCacheKeyValue(),
            fernet=Fernet(values["PDPW_OAUTH_STORAGE_ENCRYPTION_KEY"].encode()),
        ),
        jwt_signing_key=values["PDPW_OAUTH_JWT_SIGNING_KEY"],
        require_authorization_consent=True,
    )
