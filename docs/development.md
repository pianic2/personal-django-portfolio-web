# Development and configuration

## Prerequisites and bootstrap

Use Python `>=3.13,<3.14` and `uv`. From a clean clone:

```bash
uv sync --frozen
cp .env.example .env
docker compose up -d postgres
uv run python manage.py migrate
uv run python manage.py check
```

Start the development server with `uv run python manage.py runserver`.
Create an administrator with `uv run python manage.py createsuperuser`.

## Configuration

`portfolio.settings` loads an optional root `.env` without a dotenv dependency.
Do not commit secrets. The supported variables are:

| Variable | Behavior |
| --- | --- |
| `DJANGO_DEBUG` | Boolean; defaults to `true`. |
| `DJANGO_SECRET_KEY` | Required in production; must be strong. A development-only fallback exists only with debug enabled. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts; required when debug is false. |
| `DJANGO_DATABASE_URL` | Required PostgreSQL URL, for example `postgresql://portfolio:portfolio@localhost:5432/portfolio`. |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Comma-separated origins; defaults to local React and the GitHub Pages consumer. |
| `DJANGO_BASE_URL` | Wagtail admin base URL; defaults to `http://localhost:8000`. |
| `DJANGO_EMAIL_BACKEND`, `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`, `DJANGO_EMAIL_USE_TLS`, `DJANGO_DEFAULT_FROM_EMAIL` | Email transport settings. Console email is the local default. |
| `DJANGO_CONTACT_RECIPIENT_EMAIL` | Recipient required for successful contact delivery. |
| `DJANGO_CONTACT_FROM_EMAIL` | Optional contact sender; otherwise the default sender is used. |
| `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS` | Production HTTPS behavior. |
| `WAGTAIL_AGENT_API_URL` | Base URL used by the MCP server. |
| `WAGTAIL_AGENT_API_TOKEN` | Server-side bearer token used by the MCP server; never expose or commit it. |

PostgreSQL is the only supported database backend. The repository-owned
Compose service uses PostgreSQL 18.4, matching CI. The database URL parser
rejects missing, unsupported, and incomplete PostgreSQL URLs; it never falls
back to another database backend.

## Migrations and quality

Apply migrations with `uv run python manage.py migrate`. Check migration drift
with `uv run python manage.py makemigrations --check --dry-run`. The canonical
quality gate is:

```bash
bash scripts/quality.sh
```

It runs Ruff, Django checks, migration drift validation, and the complete
pytest suite. Do not use `pip` as the project workflow.

## Frontend and admin boundaries

The separate React consumer reads Wagtail v3 JSON and the contact endpoint.
Use `/admin/` for Wagtail pages, revisions, publication, images, documents,
and page permissions. Use `/django-admin/` for standalone `Capability` and
`CapabilityTranslation` records. The backend does not contain the React build.
