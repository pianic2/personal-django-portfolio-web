import importlib

import pytest

from portfolio import settings


def test_debug_parser_defaults_to_false_when_unset(monkeypatch):
    monkeypatch.delenv("DJANGO_DEBUG", raising=False)

    assert settings.env_bool("DJANGO_DEBUG", default=False) is False


def test_explicit_debug_mode_allows_development_fallback(monkeypatch):
    monkeypatch.setenv("DJANGO_DEBUG", "true")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "")

    reloaded = importlib.reload(settings)
    assert reloaded.DEBUG is True
    assert reloaded.SECRET_KEY == reloaded.DEVELOPMENT_SECRET_KEY


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
