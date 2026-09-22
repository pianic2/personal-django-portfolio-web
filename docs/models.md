# Models and content model

All fields below are implemented in `portfolio/models.py`. Wagtail page
models are editorial content; `Orderable` models are owned by their parent
page; standalone Django models are not page content.

## Wagtail pages

| Model | Responsibility | Important contract |
| --- | --- | --- |
| `BlogIndexPage` | Locale-owned blog container | Accepts Wagtail pages as parents and only `BlogPostPage` children. |
| `BlogPostPage` | Minimal editable blog post | Owns `stable_id`, excerpt, publication date, body, and optional protected featured image. It has no children. |
| `ProfilePage` | Localized portfolio profile | Owns hero/closing copy and ordered `ProfileSection` and `ProfileUsefulLink` children. |
| `ProjectPage` | Localized project case study | Owns narrative, metadata, origin/visual choices, featured/order flags, and ordered capabilities, links, assets, evidence, and claims. |

`LocalizedPageMixin` supplies the shared `stable_id` and rejects duplicate
stable IDs within one locale. Its `save()` calls `full_clean()` by default.
The Wagtail API fields declared on each page and child model are writable by
the authenticated Wagtail API subject to Wagtail permissions.

## Standalone and child models

| Model | Ownership and constraints |
| --- | --- |
| `Capability` | Reusable categorized skill with globally unique `stable_id`; categories include frontend, backend, architecture, delivery, quality, security, product, and embedded. |
| `CapabilityTranslation` | Locale-specific label/description for a capability; one row per capability and locale. |
| `ProfileSection` | Ordered child of `ProfilePage`; stores number, headings, paragraph JSON, and highlight JSON. |
| `ProfileUsefulLink` | Ordered child of `ProfilePage`; stores label, description, URL, and CTA label. |
| `ProjectCapability` | Ordered protected link between a project and capability; duplicate pairs are rejected. |
| `ProjectLink` | Ordered external project link with repository/demo/documentation/Jira/other kind. |
| `ProjectAsset` | Ordered image asset with provenance, credit, alternative text, and decorative flag. Third-party assets require credit; informative assets require alt text; decorative assets must have empty alt text. |
| `ProjectEvidence` | Ordered evidence record backed by a URL or project asset. At least one reference is required. |
| `ProjectClaim` | Ordered claim with verified/demonstrated/declared/planned status. Verified and demonstrated claims require evidence; planned claims cannot have evidence. |
| `ClaimEvidence` | Through model connecting claims to evidence from the same project; duplicate pairs and cross-project links are rejected. |

`ProjectPage.origin` distinguishes personal long-term and ITS training work.
`ProjectPage.visual_variant` selects one of the implemented visual variants.
Projects are ordered by `display_order`, then `stable_id`.

## Integrity checks

`validate_portfolio_integrity()` verifies exactly one Italian and one English
profile/project variant per stable ID, shared translation families, the
required profile stable ID, at least one project, and claim/evidence rules.
`import_portfolio` calls this check after importing the canonical dataset.
