# Personal Django Portfolio Web

Django 5.2 LTS and Wagtail 8 backend for the existing React portfolio.

## Local bootstrap

Requires `uv`, Python 3.13 and PostgreSQL for the supported production configuration.
SQLite is the local default so a clean checkout can run the framework baseline
without external infrastructure.

```bash
uv sync --frozen
cp .env.example .env
uv run python manage.py migrate
uv run python manage.py check
uv run python manage.py runserver
```

The Wagtail administration is at `/admin/`. Create a local administrator with
`uv run python manage.py createsuperuser`.

`DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` are required when
`DJANGO_DEBUG=false`. Set `DJANGO_DATABASE_URL` to a PostgreSQL URL in deployed
environments, for example `postgresql://user:password@host:5432/database`.

The shared execution policy lives in the PDPW Confluence runbook; repository
documentation only records commands needed to reproduce this implementation.
