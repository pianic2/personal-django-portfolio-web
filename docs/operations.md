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
`portfolio/asgi.py`. Render runs the composed Django/FastMCP ASGI application
through the repository Procfile, with lifespan enabled:

```bash
uv run uvicorn portfolio.asgi:application --host 0.0.0.0 --port $PORT --lifespan on
```

Set `PDPW_MCP_INBOUND_TOKEN` to a strong secret distinct from
`WAGTAIL_AGENT_API_TOKEN`. An empty token disables successful MCP
authentication. `PDPW_MCP_ALLOWED_ORIGINS` is optional; unset means browser
Origins are denied. The canonical client endpoint is
`https://pdpw-production.onrender.com/mcp`.
Restart the Render service after changing either credential or the Origin list;
the ASGI application snapshots those values at startup.

## OAuth 2.1 provider connectors

When all four `PDPW_OAUTH_UPSTREAM_CLIENT_ID`,
`PDPW_OAUTH_UPSTREAM_CLIENT_SECRET`, `PDPW_OAUTH_JWT_SIGNING_KEY`, and
`PDPW_OAUTH_ALLOWED_IDENTITIES` values are set, the endpoint uses the single
FastMCP-native OAuth proxy with Google OIDC. The allowlist contains verified
Google email addresses (the owner supplied `nome@example.com`); the Google
`sub` claim is retained as the immutable authenticated subject. Wagtail and
inbound bearer credentials remain separate and are never forwarded to clients.

Register the upstream Google OAuth web client with this exact callback:
`https://pdpw-production.onrender.com/auth/callback`. ChatGPT uses the exact
redirect `https://chatgpt.com/connector_platform_oauth_redirect`; Claude uses
`https://claude.ai/api/mcp/auth_callback`. The proxy advertises OAuth metadata,
protected-resource metadata, DCR, authorization-code flow, PKCE S256, and the
resource audience `https://pdpw-production.onrender.com/mcp` at the canonical
endpoint. Both clients use the same `/mcp` URL.

OAuth client registrations, authorization transactions, codes, refresh metadata,
and token mappings use the existing PostgreSQL-backed Django cache table
`django_cache_table`; create it after migrations with
`uv run python manage.py createcachetable django_cache_table`. Do not use the
ephemeral disk store in production. Rotate the Google client secret and signing
key in Render, restart the service, and revoke upstream sessions/tokens in the
Google console. Remove an identity from `PDPW_OAUTH_ALLOWED_IDENTITIES` and
restart to revoke its access. G2/G3/G5 provider dashboard, secret provisioning,
and interactive smoke checks remain owner-gated.

After deployment, smoke-check that POST `/mcp` without authorization returns
401 with a Bearer challenge, then use the configured bearer token to initialize,
list tools, and make a safe read. Test a slash-appended `/mcp/` URL; it must not
redirect. Confirm GET does not establish SSE. If a bounded draft smoke write is
authorized, use the stable ID `pdpw-63-mcp-smoke`, verify it is absent from the
public pages API, record both locale IDs, and clean it up through Wagtail admin
after verification. Do not retry a write whose result is ambiguous.

Before deployment, an external unauthenticated POST `/mcp` with a valid
initialize request returned 404 with an HTML body and
`x-render-origin-server: gunicorn`. No credential was sent in that probe.

Run `uv run python manage.py collectstatic --noinput` during the image/build
step. WhiteNoise serves the resulting manifest-backed files at `/static/` when
`DEBUG=false`; media remains an external deployment concern.
