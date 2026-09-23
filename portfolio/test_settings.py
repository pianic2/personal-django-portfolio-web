import importlib
from pathlib import Path

import pytest

from portfolio import settings


def test_debug_parser_defaults_to_false_when_unset(monkeypatch):
    monkeypatch.delenv("DJANGO_DEBUG", raising=False)
    monkeypatch.setenv(
        "DJANGO_SECRET_KEY",
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    )
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "localhost")
    original_exists = Path.exists
    monkeypatch.setattr(
        Path,
        "exists",
        lambda path: False if path.name == ".env" else original_exists(path),
    )

    reloaded = importlib.reload(settings)
    assert reloaded.DEBUG is False


def test_explicit_debug_mode_allows_development_fallback(monkeypatch):
    monkeypatch.setenv("DJANGO_DEBUG", "true")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "")

    reloaded = importlib.reload(settings)
    assert reloaded.DEBUG is True
    assert reloaded.SECRET_KEY == reloaded.DEVELOPMENT_SECRET_KEY
    assert reloaded.STORAGES["default"]["BACKEND"] == "django.core.files.storage.FileSystemStorage"
    assert reloaded.NUM_PROXIES == 0
    assert reloaded.CACHES["default"]["BACKEND"] == (
        "django.core.cache.backends.locmem.LocMemCache"
    )


@pytest.mark.parametrize(
    "debug,secret,error",
    [
        ("false", "", "DJANGO_SECRET_KEY is required"),
        (
            "false",
            "development-only-key-do-not-use-in-production",
            "must not use the development secret",
        ),
    ],
)
def test_production_rejects_missing_or_development_secret(monkeypatch, debug, secret, error):
    monkeypatch.setenv("DJANGO_DEBUG", debug)
    monkeypatch.setenv("DJANGO_SECRET_KEY", secret)

    with pytest.raises(RuntimeError, match=error):
        importlib.reload(settings)


def test_settings_default_is_fail_closed(monkeypatch):
    monkeypatch.setenv("DJANGO_DEBUG", "false")
    monkeypatch.setenv(
        "DJANGO_SECRET_KEY",
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    )
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "localhost")

    reloaded = importlib.reload(settings)
    assert reloaded.DEBUG is False
    assert reloaded.STORAGES["default"]["BACKEND"] == "storages.backends.s3.S3Storage"
    assert reloaded.STORAGES["staticfiles"]["BACKEND"] == (
        "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )


def test_production_uses_bounded_proxy_trust_and_shared_cache(monkeypatch):
    monkeypatch.setenv("DJANGO_DEBUG", "false")
    monkeypatch.setenv(
        "DJANGO_SECRET_KEY",
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    )
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "localhost")
    monkeypatch.delenv("DJANGO_NUM_PROXIES", raising=False)

    reloaded = importlib.reload(settings)

    assert reloaded.NUM_PROXIES == 1
    assert reloaded.CACHES["default"] == {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache_table",
    }


@pytest.mark.django_db
def test_database_cache_instances_share_values():
    from django.core.cache.backends.db import DatabaseCache
    from django.core.management import call_command

    call_command("createcachetable", "django_cache_table", verbosity=0)
    params = {"TIMEOUT": 60}
    first_worker = DatabaseCache("django_cache_table", params)
    second_worker = DatabaseCache("django_cache_table", params)

    first_worker.set("pdpw53-cache-boundary", "shared")

    assert second_worker.get("pdpw53-cache-boundary") == "shared"
