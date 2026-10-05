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
| `DJANGO_DEBUG` | Boolean; defaults to `false`. Set explicitly to `true` for local development. |
| `DJANGO_SECRET_KEY` | Required unless explicit debug mode is enabled; must be strong in production. A development-only fallback exists only with `DJANGO_DEBUG=true`. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts; required when debug is false. |
| `DJANGO_DATABASE_URL` | Required PostgreSQL URL, for example `postgresql://portfolio:portfolio@localhost:5432/portfolio`; SQLite is not supported. |
| `DJANGO_NUM_PROXIES` | Number of trusted proxy hops used by DRF throttling; defaults to `0` locally and `1` in production. |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Comma-separated origins; defaults to local React and the GitHub Pages consumer. |
| `DJANGO_BASE_URL` | Wagtail admin base URL; defaults to `http://localhost:8000`. |
| `DJANGO_EMAIL_BACKEND`, `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`, `DJANGO_EMAIL_USE_TLS`, `DJANGO_EMAIL_TIMEOUT`, `DJANGO_DEFAULT_FROM_EMAIL` | Email transport settings. SMTP has a 10-second timeout by default; `DJANGO_EMAIL_TIMEOUT` must be a positive integer number of seconds. Console email is the local default. |
| `DJANGO_CONTACT_RECIPIENT_EMAIL` | Recipient required for successful contact delivery. |
| `DJANGO_CONTACT_FROM_EMAIL` | Optional contact sender; otherwise the default sender is used. |
| `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS` | Production HTTPS behavior. |
| `WAGTAIL_AGENT_API_TOKEN` | Server-side bearer token used by the MCP server; never expose or commit it. |
| `PDPW_MCP_INBOUND_TOKEN` | Dedicated bearer token for inbound remote MCP clients; keep distinct from the Wagtail service token. |
| `PDPW_MCP_ALLOWED_ORIGINS` | Optional comma-separated exact browser origins allowed to call MCP; unset denies requests with an Origin. |
| `AWS_STORAGE_BUCKET_NAME` | Production S3-compatible media bucket; leave unset for local development. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Production object-storage credentials (or use the runtime's IAM credentials). |
| `AWS_S3_REGION_NAME` | Optional S3 region. |
| `AWS_S3_ENDPOINT_URL` | Optional S3-compatible endpoint URL. |
| `AWS_S3_CUSTOM_DOMAIN` | Optional public media hostname used when generating URLs. |
| `AWS_QUERYSTRING_AUTH` | Set `true` when media URLs must be signed; defaults to `false`. |

PostgreSQL URL query options are explicitly limited to `sslmode`,
`channel_binding`, `connect_timeout`, `application_name`, `target_session_attrs`,
and `pgbouncer`. Remote hosts default to `sslmode=require` and reject weaker
TLS modes; local hosts retain `sslmode=prefer` unless explicitly configured.
`pgbouncer=true` enables Django's `DISABLE_SERVER_SIDE_CURSORS` compatibility
setting. Unsupported options fail during settings initialization.

Production uses Django's PostgreSQL-backed cache (`django_cache_table`) so
contact throttles are shared by web workers. Create the cache table once after
database migrations with `uv run python manage.py createcachetable`.

Production media URLs require a public bucket or public media hostname when
`AWS_QUERYSTRING_AUTH=false`; use signed URLs for private buckets. Configure the
bucket and credentials in the deployment environment, never in this repository.

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
