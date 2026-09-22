import pytest

from portfolio.settings import BASE_DIR, database_config


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


def test_database_config_defaults_to_local_sqlite(monkeypatch):
    monkeypatch.delenv("DJANGO_DATABASE_URL", raising=False)

    config = database_config()

    assert config["ENGINE"] == "django.db.backends.sqlite3"
    assert config["NAME"] == BASE_DIR / "db.sqlite3"


def test_database_config_accepts_explicit_sqlite_url(monkeypatch):
    monkeypatch.setenv("DJANGO_DATABASE_URL", "sqlite:///tmp/test.sqlite3")

    config = database_config()

    assert config == {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "tmp/test.sqlite3",
    }


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("mysql://localhost/portfolio", "must use sqlite, postgres, or postgresql"),
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
