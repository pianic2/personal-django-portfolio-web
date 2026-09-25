# Personal Django Portfolio Web

Django 5.2.17 and Wagtail 8.0 backend for the separate React portfolio
consumer. The repository owns bilingual editorial content, its JSON API, the
contact endpoint, and a least-privilege MCP content editor.

## Requirements and bootstrap

Use Python `>=3.13,<3.14` and `uv`. PostgreSQL is the only supported database
backend for local development, tests, and production-oriented execution.

```bash
uv sync --frozen
cp .env.example .env
docker compose up -d postgres
uv run python manage.py migrate
uv run python manage.py check
uv run python manage.py runserver
```

Create an administrator with `uv run python manage.py createsuperuser`.
The canonical repository gate is `bash scripts/quality.sh`; it runs Ruff,
Django checks, migration drift validation, and the full pytest suite.

## Configuration and security

The optional root `.env` file is loaded locally and must not be committed.
`DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` are required when
`DJANGO_DEBUG=false`. `DJANGO_DATABASE_URL` must be an explicit PostgreSQL URL;
SQLite is not a supported runtime backend.
Email, CORS, production HTTPS, and MCP settings are documented in
[Development and configuration](docs/development.md). Never put API tokens or
other secrets in the repository, browser, logs, or agent-visible responses.

## Admin, content, and APIs

- `/admin/` is Wagtail administration for pages, revisions, publication,
  images, documents, and page permissions.
- `/django-admin/` is Django administration for standalone capability data.
- `/api/v3/openapi.json` and `/api/v3/docs/` expose the Wagtail API contract.
- `/api/contact/` accepts the validated public contact form.
- `uv run python manage.py import_portfolio` imports the repeatable bilingual
  canonical content snapshot.
- `uv run python manage.py configure_agent_account` provisions the scoped
  non-staff content account.
- The Render ASGI process serves the canonical remote MCP endpoint at
  `/mcp`; see [MCP integration](docs/api.md#mcp-integration) and
  [deployment operations](docs/operations.md#deploymentruntime-boundaries).

The MCP surface supports selected page drafts/revisions, localized-pair
creation, schemas, and image/document operations. It rejects publication
actions and does not expose delete operations. See [API and integration
contracts](docs/api.md) for routes, inputs, outputs, errors, and boundaries.

## Documentation map

- [Architecture and domain overview](docs/architecture.md)
- [Models and content model](docs/models.md)
- [API and integration contracts](docs/api.md)
- [Development and configuration](docs/development.md)
- [Testing and validation](docs/testing.md)
- [Operations and management commands](docs/operations.md)
- [Documentation inventory](docs/inventory.md)

The backend does not contain the React frontend or a deployment platform
configuration. Repository execution policy remains in `AGENTS.md`; project
governance remains in Jira/Confluence.
