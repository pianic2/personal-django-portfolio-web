# API and integration contracts

## Mounted routes

| Method | Route | Contract |
| --- | --- | --- |
| `GET`/Wagtail methods | `/api/v3/` | Wagtail v3 page, image, document, schema, and revision API. Anonymous reads expose published content according to Wagtail rules. |
| `POST` | `/api/v3/localized-pairs/` | Authenticated Wagtail bearer user creates one Italian and one English draft page atomically. |
| `GET` | `/api/v3/openapi.json` | Wagtail-generated OpenAPI document used by the MCP adapter. |
| `GET` | `/api/v3/docs/` | Wagtail interactive API documentation. |
| `POST` | `/api/contact/` | Anonymous contact delivery endpoint described below. |
| Wagtail | `/admin/` | Editorial administration and publication workflow. |
| Django | `/django-admin/` | Standalone capability administration. |
| Wagtail documents | `/documents/` | Wagtail document serving route. |

In debug mode the Wagtail page route is also mounted at `/`; in production the
root returns 404. The exact Wagtail-generated resource paths are intentionally
not duplicated here: use the live OpenAPI document for the installed schema.

## Localized pair creation

`POST /api/v3/localized-pairs/` accepts a JSON object with:

```json
{
  "type": "portfolio.ProjectPage",
  "stable_id": "example-project",
  "it": {"parent_id": 1, "title": "Titolo"},
  "en": {"parent_id": 2, "title": "Title"}
}
```

Supported types are `BlogIndexPage`, `BlogPostPage`, `ProfilePage`, and
`ProjectPage`. `stable_id` is lowercase slug syntax. For `BlogIndexPage`,
`ProfilePage`, and `ProjectPage`, each locale object needs a numeric `parent_id`.
`BlogPostPage` instead requires the top-level `parent_stable_id`, which resolves
the matching Italian and English `BlogIndexPage`; locale-level `parent_id` is
rejected. Locale payloads accept only the public title, slug, and type-specific
editable fields; inherited Wagtail internals cannot be supplied. A blog post's
optional `featured_image` is an image ID or `null`, and the caller must have
Wagtail permission to choose that image. The caller needs Wagtail page-add
permission below both parents. Success returns `201` with the stable ID, shared
translation key, and the two created page IDs. Malformed framework-level request
shapes return `422`; invalid locale, parent, duplicate, or field input returns
`400`, and the transaction rolls back both pages. Missing authentication
returns `401`, and an authenticated caller without page-add permission below
either parent receives `403`.

For example, a localized blog post uses a stable identity for the translated
parent rather than locale-specific parent IDs:

```json
{
  "type": "portfolio.BlogPostPage",
  "stable_id": "example-post",
  "parent_stable_id": "blog",
  "it": {"title": "Articolo", "slug": "articolo", "excerpt": "Sintesi", "body": "Testo"},
  "en": {"title": "Article", "slug": "article", "excerpt": "Summary", "body": "Text"}
}
```

## Contact endpoint

`POST /api/contact/` is unauthenticated and accepts `name` (maximum 80),
`email`, `message` (20–2000 characters), and optional write-only `locale`
(`it` or `en`). A valid request sends server-side email and returns
`{"success": true}` with `200`. Validation errors return `400` with
`code=validation_error` and field errors. Missing recipient configuration or
mail delivery failure returns `503` with `code=delivery_failed` and no provider
details. The endpoint applies 3 requests/minute per client IP and one duplicate
message/minute per normalized client/message; throttling returns `429` and may
include `Retry-After`.

## MCP integration

The canonical remote MCP endpoint is
`https://pdpw-production.onrender.com/mcp`. It uses stateless Streamable HTTP
over POST with JSON responses and a bearer token. Configure
`PDPW_MCP_INBOUND_TOKEN` separately from `WAGTAIL_AGENT_API_TOKEN`; never put
either value in published documentation or source control. Supply the inbound
token only through the client's secret store; the Wagtail credential stays
server-side.

FastMCP runs inside Django's ASGI process. Its Wagtail OpenAPI schema is
generated in-process, and MCP calls use the internal ASGI application with the
Wagtail service credential. `/mcp` is canonical; `/mcp/` is accepted without
a redirect. Requests without an Origin are allowed. Browser origins are denied
unless an exact origin is configured in `PDPW_MCP_ALLOWED_ORIGINS`. GET is
rejected and SSE is unavailable.

Example client configuration (supply the token through the client's secret
store):

```json
{
  "url": "https://pdpw-production.onrender.com/mcp",
  "headers": { "Authorization": "Bearer <PDPW_MCP_INBOUND_TOKEN>" }
}
```

The exposed tools cover page list/find/detail/draft-update, localized-pair
creation as the only page-creation path, page revisions, content-type schemas,
and image/document list/create/detail/update. Generic page creation and
publish, unpublish, delete, and administrative tools are unavailable. Publish
and unpublish actions are rejected in query parameters and recursively in
request bodies. Image/document base64 data URLs are converted to multipart
uploads. Draft writes remain unpublished.

For local development, configure `PDPW_MCP_INBOUND_TOKEN` and
`WAGTAIL_AGENT_API_TOKEN`, then run
`uv run uvicorn portfolio.asgi:application --host 127.0.0.1 --port 8000 --lifespan on`.
