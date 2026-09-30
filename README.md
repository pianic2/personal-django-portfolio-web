<p align="center">
  <img src="docs/assets/readme-hero.svg" alt="Personal Django Portfolio Web — editorial backend for a bilingual portfolio" width="100%">
</p>

<p align="center">
  <img src="docs/assets/logo.svg" alt="" width="40" height="40"><br>
  <strong>Personal Django Portfolio Web</strong><br>
  Django and Wagtail backend for a separately maintained React portfolio.
</p>

<p align="center">
  <a href="https://github.com/pianic2/personal-django-portfolio-web/actions/workflows/quality.yml"><img src="https://github.com/pianic2/personal-django-portfolio-web/actions/workflows/quality.yml/badge.svg?branch=main" alt="Backend quality workflow"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-7a9b70.svg" alt="MIT License"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white" alt="Django 5.2">
  <img src="https://img.shields.io/badge/Wagtail-8.0-43B1B0?logo=wagtail&logoColor=white" alt="Wagtail 8.0">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white" alt="Python 3.13">
  <img src="https://img.shields.io/badge/PostgreSQL-required-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL">
</p>

## Quick start

Requires Python `>=3.13,<3.14`, [`uv`](https://docs.astral.sh/uv/), and Docker Compose. PostgreSQL is the supported database.

```bash
uv sync --frozen
cp .env.example .env
docker compose up -d postgres
uv run python manage.py migrate
uv run python manage.py runserver
```

## Interfaces

| Consumer | Backend interface | Purpose |
| --- | --- | --- |
| React portfolio | Wagtail v3 API, `/api/contact/` | Published portfolio content and contact form |
| MCP clients | `/mcp` | Allowlisted content editing and media operations |
| Editors | `/admin/`, `/django-admin/` | Wagtail editorial workflow and standalone capability records |

The backend owns bilingual Italian and English content. The React application is maintained separately and is not included here.

## Development

Run the canonical quality gate (Ruff, Django checks, migration drift, and the test suite):

```bash
bash scripts/quality.sh
```

For setup details and configuration, see [Development](docs/development.md). The [Testing guide](docs/testing.md) documents targeted and full test commands.

## Documentation

- [Architecture and domain overview](docs/architecture.md)
- [Models and content model](docs/models.md)
- [API and integration contracts](docs/api.md)
- [Development and configuration](docs/development.md)
- [Testing and validation](docs/testing.md)
- [Operations and management commands](docs/operations.md)

## License

[MIT](LICENSE)
