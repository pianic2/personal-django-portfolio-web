# Operations and management commands

## Canonical content import

Start the repository-owned PostgreSQL service before running Django commands:

```bash
docker compose up -d postgres
```

After migrations, run:

```bash
uv run python manage.py import_portfolio
```

The command synchronizes the backend-owned bilingual snapshot from
`portfolio.canonical_data`: locales, capabilities and translations, profile
variants, projects, ordered children, claims, evidence, and links. It is
transactional, repeatable, publishes the imported page revisions, runs
`validate_portfolio_integrity()`, and emits a JSON report. Add `--json` for a
machine-readable report without the `Imported ` prefix.

## Agent account provisioning

Run:

```bash
uv run python manage.py configure_agent_account
```

The command creates or reconciles the `portfolio-agent` user and
`Portfolio content agent` group. An optional `--username` selects another
service identity. The account is active, non-staff, non-superuser, has an
unusable password, and receives only page add/change permissions and image
add/change permissions in `Portfolio agent content`. The command refuses to
reuse the reserved group for another user and does not provision API tokens.

A site administrator creates the Wagtail API token in Wagtail administration.
Only its one-time plaintext value belongs in the server environment used by
the MCP process.

## Deployment/runtime boundaries

Production requires a strong `DJANGO_SECRET_KEY`, non-empty
`DJANGO_ALLOWED_HOSTS`, and a valid PostgreSQL URL. HTTPS redirect/HSTS and
secure cookies are enabled by the production settings defaults. Django serves
neither the root content route nor media files in production; use the Wagtail
and deployment infrastructure for those responsibilities.

The repository contains WSGI and ASGI entry points in `portfolio/wsgi.py` and
`portfolio/asgi.py`. The supported production web process is Gunicorn via the
repository Procfile:

```bash
gunicorn portfolio.wsgi:application
```

Run `uv run python manage.py collectstatic --noinput` during the image/build
step. WhiteNoise serves the resulting manifest-backed files at `/static/` when
`DEBUG=false`; media remains an external deployment concern.
