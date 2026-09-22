# Documentation inventory

This inventory is the AC1 coverage index. A surface is covered by the linked
technical page, by a precise existing symbol/test name, or is marked not
applicable with a reason.

| Surface | Implemented locations | Coverage |
| --- | --- | --- |
| Django/Wagtail models and invariants | `portfolio/models.py` | [Models](models.md) |
| URL routing and views | `portfolio/urls.py`, `portfolio/contact.py`, `portfolio/localization_api.py` | [API](api.md), [Architecture](architecture.md) |
| Wagtail v3 and localized-pair API | `portfolio/urls.py`, `portfolio/localization_api.py` | [API](api.md) |
| Contact serializer/throttles/delivery | `portfolio/contact.py` | [API](api.md) |
| MCP server and integration hooks | `portfolio/mcp_server.py` | [API](api.md), [Architecture](architecture.md) |
| Admin ownership and branding | `portfolio/admin.py`, templates | [Architecture](architecture.md), [Testing](testing.md) |
| Canonical content data | `portfolio/canonical_data.py` | [Operations](operations.md) |
| Management commands | `portfolio/management/commands/` | [Operations](operations.md) |
| Settings and environment | `portfolio/settings.py`, `.env.example` | [Development](development.md) |
| WSGI/ASGI runtime | `portfolio/wsgi.py`, `portfolio/asgi.py` | [Operations](operations.md) |
| Migrations | `portfolio/migrations/0001_initial.py`, `0002_blogindexpage_blogpostpage.py` | [Development](development.md) and quality gate |
| Quality script | `scripts/quality.sh` | [Development](development.md), [Testing](testing.md) |
| Test modules/classes/functions | `portfolio/tests.py`, `portfolio/test_*.py` | [Testing](testing.md); descriptive existing names are the accepted intent mechanism |
| Static branding asset | `portfolio/static/portfolio/portfolio-mark.svg` | Admin tests and repository asset; no separate runtime contract |
| HTML admin templates | `templates/admin/`, `templates/wagtailadmin/` | Admin behavior is covered by `test_admin.py`; templates are presentation overrides |
| Product frontend | Separate React repository | Not applicable: explicitly outside this backend repository |
| New deployment tooling | None present | Not applicable: no implemented platform contract to document |

The inventory was built from the repository file list plus targeted symbol
searches. It intentionally does not invent undocumented endpoints or claim
deployment behavior that is not implemented.
