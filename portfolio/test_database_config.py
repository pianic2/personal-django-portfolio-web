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


def test_database_config_requires_explicit_database_url(monkeypatch):
    monkeypatch.delenv("DJANGO_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="must configure a PostgreSQL database"):
        database_config()


def test_database_config_rejects_sqlite_url(monkeypatch):
    monkeypatch.setenv("DJANGO_DATABASE_URL", "sqlite:///tmp/test.sqlite3")

    with pytest.raises(RuntimeError, match="must use postgres or postgresql"):
        database_config()


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("mysql://localhost/portfolio", "must use postgres or postgresql"),
        ("postgresql:///portfolio", "must include a PostgreSQL host and database name"),
        ("postgresql://localhost/", "must include a PostgreSQL host and database name"),
        ("postgresql://localhost:invalid/portfolio", "must contain a valid PostgreSQL port"),
    ],
)
def test_database_config_rejects_invalid_database_urls(
    monkeypatch, value, message
):
    monkeypatch.setenv("DJANGO_DATABASE_URL", value)

    with pytest.raises(RuntimeError, match=message):
        database_config()
