# Testing and validation

## Test organization

Tests use Django's `TestCase`, `TransactionTestCase`, and `SimpleTestCase`
through pytest-django. `pyproject.toml` discovers `test_*.py`, `*_test.py`,
and `tests.py`.

| Module | Coverage and test groups |
| --- | --- |
| `portfolio/tests.py` | `WagtailBootstrapTests` covers routes, admin access, media, CORS, and production/debug boundaries. `PortfolioDomainModelTests` covers blog/profile/project models, localization, revisions, API exposure, publication filtering, and cross-project evidence rules. `PortfolioImportTests` covers canonical import equality, bilingual repeatability, publication, and integrity failures. |
| `portfolio/test_api_contracts.py` | `PublicAPIContractTests` covers profile/project response shapes, locale/slug filters, invalid filters, CORS, draft exclusion, localized blog output, and media safety. |
| `portfolio/test_localization_api.py` | `LocalizedPairAPITests` covers atomic pair creation, shared translation identity, malformed payloads, duplicates, and second-locale failure rollback. |
| `portfolio/test_agent_api.py` | `PortfolioAgentAPITests` covers the non-admin scoped account, draft-only bearer page operations, and media collection boundaries. `png_file()` supplies the small upload fixture. |
| `portfolio/test_mcp_server.py` | `MCPServerTests` covers deterministic route allowlisting, unmatched-route exclusion, recursive publication rejection, and non-echoing errors. |
| `portfolio/test_mcp_e2e.py` | `MCPAgentBoundaryTests` exercises authenticated draft/media MCP flows and publication-bypass rejection against the running integration boundary. |
| `portfolio/test_contact.py` | `ContactEndpointTests` covers successful delivery, stable validation errors, payload limits, duplicate/IP throttles, CORS, and stable delivery failures. |
| `portfolio/test_admin.py` | `AdminBrandingAndOwnershipTests` covers admin identity/favicon and the ownership boundary for standalone capability data. |

The test and class names are the discoverable intent mechanism for the current
test suite. `setUp`/`setUpTestData` methods create the corresponding database,
API client, media, user, and cache fixtures; they are support code rather than
independent behavior contracts.

## Commands

Run one module while iterating:

```bash
uv run pytest portfolio/test_api_contracts.py -q
```

Run all tests with `uv run pytest -q`. Run the complete repository gate with
`bash scripts/quality.sh`; it also checks Ruff, Django configuration, and
migration drift. For a documentation-only change, additionally inspect the
final diff and run `git diff --check`.

## Validation principles

Tests are authoritative for the externally visible API and permission behavior.
The implemented models and settings are authoritative for fields, defaults,
configuration, and invariants. Documentation must not claim endpoints,
permissions, or runtime behavior that is not represented by those sources.
