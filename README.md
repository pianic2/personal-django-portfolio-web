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

Run the canonical backend quality command with `bash scripts/quality.sh`.
It is also executed by CI after restoring the locked environment with
`uv sync --frozen`.

The Wagtail administration is at `/admin/`. Create a local administrator with
`uv run python manage.py createsuperuser`.

## Agent API account

After migrations and the portfolio content import, provision the dedicated
non-staff account and its Wagtail page/media permissions with:

```bash
uv run python manage.py import_portfolio
uv run python manage.py configure_agent_account
```

The command is safe to rerun. It reconciles `portfolio-agent` to the
`Portfolio content agent` group, grants add/edit on the localized portfolio
page trees without publish permission, and grants image add/edit only in the
`Portfolio agent content` collection. Move any media the agent must maintain
into that collection through Wagtail administration. The service account has
no staff, superuser, model-admin, or API-token-management permissions and has
an unusable password.

Wagtail creates and stores only a digest of each API token. A site
administrator can create a token for `portfolio-agent` from **Settings → API
tokens** in Wagtail administration. Store the one-time plaintext token in the
server-side environment of the MCP process that calls this API (for example,
as `WAGTAIL_AGENT_API_TOKEN`); never put it in this repository, a browser, an
agent-visible tool response, or logs. Revoke it from the same admin view if it
is exposed.

The v3 OpenAPI document and interactive docs are available at
`/api/v3/openapi.json` and `/api/v3/docs/`. Wagtail's page add/edit boundary
also permits delete through some native operations; the MCP surface must
exclude delete operations when it is introduced.

`DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` are required when
`DJANGO_DEBUG=false`. Set `DJANGO_DATABASE_URL` to a PostgreSQL URL in deployed
environments, for example `postgresql://user:password@host:5432/database`.

The shared execution policy lives in the [PDPW — Luna Autonomous Execution
Runbook](https://niccolopiazzi01.atlassian.net/wiki/spaces/PDPW/pages/50855957/PDPW+Luna+Autonomous+Execution+Runbook); repository documentation only
records commands needed to reproduce this implementation.
