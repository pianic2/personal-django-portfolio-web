import pytest

from portfolio.settings import database_config


def test_database_config_uses_native_postgresql_backend(monkeypatch):
    monkeypatch.setenv(
        "DJANGO_DATABASE_URL", "postgresql://portfolio:secret@db.example:5433/portfolio"
    )

    assert database_config() == {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "portfolio",
        "USER": "portfolio",
        "PASSWORD": "secret",
        "HOST": "db.example",
        "PORT": 5433,
    }


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (None, "DJANGO_DATABASE_URL is required"),
        ("sqlite:///db.sqlite3", "must use the postgres or postgresql scheme"),
        ("postgresql:///portfolio", "must include a PostgreSQL host and database name"),
        ("postgresql://localhost:invalid/portfolio", "must contain a valid PostgreSQL port"),
    ],
)
def test_database_config_rejects_missing_or_invalid_postgresql_contract(
    monkeypatch, value, message
):
    if value is None:
        monkeypatch.delenv("DJANGO_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DJANGO_DATABASE_URL", value)

    with pytest.raises(RuntimeError, match=message):
        database_config()
