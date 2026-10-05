<h1 align="center">
  <img
    src="docs/assets/readme-background.svg"
    alt="Personal Django Portfolio Web — Django and Wagtail backend for a separate React portfolio"
    width="100%"
  />
</h1>

<p align="center">
  <a href="#quick-start"><img src="https://img.shields.io/badge/Django%20%2B%20PostgreSQL-backend-111827?style=for-the-badge" alt="Django and PostgreSQL backend"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-facc15?style=for-the-badge" alt="MIT License"></a>
  <a href="https://github.com/pianic2/personal-django-portfolio-web/actions/workflows/quality.yml"><img src="https://github.com/pianic2/personal-django-portfolio-web/actions/workflows/quality.yml/badge.svg?branch=main&amp;style=for-the-badge" alt="Backend quality workflow"></a>
  <a href="docs/README.md"><img src="https://img.shields.io/badge/docs-guides-111827?style=for-the-badge" alt="Documentation guides"></a>
</p>

Django and Wagtail backend for a separately maintained React portfolio, with PostgreSQL-backed content and APIs.

## Quick start

Requires Python `>=3.13,<3.14`, [uv](https://docs.astral.sh/uv/), and Docker Compose.

```bash
uv sync --frozen
cp .env.example .env
docker compose up -d postgres
uv run python manage.py migrate
uv run python manage.py runserver
```

See [Development](docs/development/setup-and-configuration.md) for configuration and [Testing](docs/development/testing.md) for validation commands.
