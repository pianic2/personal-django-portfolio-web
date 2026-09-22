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
`ProjectPage`. `stable_id` is lowercase slug syntax. Both locale objects need
`parent_id`; protected fields such as `live`, `locale`, and `translation_key`
cannot be supplied. The caller needs Wagtail page-add permission below both
parents. Success returns `201` with the stable ID, shared translation key, and
the two created page IDs. Invalid locale, parent, duplicate, field, or
permission input returns `400`; the transaction rolls back both pages.

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

`uv run python -m portfolio.mcp_server` fetches the Wagtail OpenAPI document
from `WAGTAIL_AGENT_API_URL` and uses `WAGTAIL_AGENT_API_TOKEN` server-side.
The exposed tools cover page list/create/find/detail/update, localized-pair
creation, page revisions, content-type schemas, and image/document
list/create/detail/update. Unmatched Wagtail routes are excluded. Publish and
unpublish actions are rejected in query parameters and recursively in request
bodies. Image/document base64 data URLs are converted to multipart uploads.
