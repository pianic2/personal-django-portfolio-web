# Architecture and domain overview

## Responsibility

`personal-django-portfolio-web` is the backend for a separate React portfolio
consumer. It owns editable bilingual portfolio content, the public Wagtail v3
read API, a public contact endpoint, and a least-privilege MCP adapter for
authenticated content editing. The React application is not part of this
repository.

## Runtime shape

- `portfolio.settings` configures Django, Wagtail, REST Framework, CORS,
  PostgreSQL, email delivery, and security defaults.
- `portfolio.urls` mounts Django admin, Wagtail admin, documents, Wagtail API
  v3, the localized-pair API, and contact delivery.
- Wagtail `Page` models represent localized editorial content. Standalone
  Django models represent reusable capabilities and evidence relationships.
- `portfolio.canonical_data` is the backend-owned bilingual import snapshot.
- `portfolio.mcp_server` exposes an allowlisted view of the Wagtail OpenAPI
  contract through FastMCP. It carries the bearer token only server-side and
  rejects publication actions.

## Content ownership

Wagtail owns editorial pages, revisions, publication state, images, documents,
and page permissions. Django admin owns standalone capability records and
their translations. The dedicated `portfolio-agent` account receives page
add/change permission and image add/change permission in one collection; it is
not staff, a superuser, or an API-token administrator.

## Localization

The implemented portfolio content uses Italian (`it`) and English (`en`).
`stable_id` identifies the same logical record across locales. Profile and
project variants must form one Wagtail translation family per stable ID. The
localized-pair API creates both variants atomically as drafts.

## Request boundaries

In debug mode, the root route delegates to Wagtail and media files are served
locally. In production, the root route returns 404 and media is not served by
Django. Explicit admin, document, API, and contact routes remain available.

The MCP adapter is an integration boundary, not a second domain API. It
allowlists selected Wagtail routes, converts base64 data URLs to multipart
uploads, and blocks publish/unpublish actions at query and nested body levels.
