Mission

Work on "personal-django-portfolio-web" as an autonomous engineering agent.

Deliver the smallest correct change that satisfies the active PDPW Jira task while minimizing scope and context usage and leaving reproducible validation evidence.

Do not redesign the project unless the active task requires it.

Portfolio content operations

Requests to create, add, or write a portfolio blog post or article are content
operations, not Jira or engineering tasks. Use the already-connected `portfolio`
MCP server directly: call `portfolio.create_localized_pair` with
`type="portfolio.BlogPostPage"`, `parent_stable_id="blog"`, IT and EN generated
in the same LLM pass, and one shared `stable_id`. Perform exactly one pair-create
mutation. Do not use `ALL_TOOLS`, MCP resource discovery, repository or Jira
discovery, local wrappers, or generic `create_page_draft` for this intent.
Investigate tooling only if the canonical MCP call is unavailable or fails.

Project

- Repository: "pianic2/personal-django-portfolio-web"
- Jira: "PDPW"
- Backend: Django 5.2 LTS + Wagtail 8
- Python: ">=3.13,<3.14"
- Production database: PostgreSQL
- Local bootstrap database: SQLite
- Python tooling: "uv"
- Tests: pytest / pytest-django
- Linting: Ruff
- Frontend is a separate consumer; this repository is backend-only.

Prefer maintained framework/community capabilities over custom infrastructure.

Execution

The active Jira issue defines the task scope.

Work on one Jira task at a time.

Acquire context according to the Context Budget below.

Before changing code, verify whether the requested behavior already exists. If already satisfied, validate it and report evidence instead of rewriting it.

Then:

1. implement the minimum coherent change;
2. add or update tests for changed behavior;
3. run targeted validation;
4. run broader gates only when required by impact or task;
5. inspect the final diff;
6. report concise evidence and stop.

Before transitioning Jira to Done, verify every applicable acceptance criterion individually against actual evidence.

Never stage or commit unrelated pre-existing changes. When the worktree is not clean, stage task-relevant paths or hunks explicitly.

Do not implement adjacent tasks, speculative features, unrelated fixes, cleanup, or refactors.

Context Budget

Context is a cost. Load it progressively.

For every task, acquire context in this order:

1. active Jira issue and acceptance criteria;
2. files, symbols, tests, configuration, or documentation explicitly referenced by the issue;
3. existing tests for the affected behavior;
4. direct dependencies and call paths, only when needed;
5. targeted repository search if the relevant implementation is still unknown;
6. Confluence/project documentation only if previous sources do not resolve a requirement or architectural question.

Stop expanding context as soon as the task can be implemented and validated safely.

Use targeted paths, symbols, diffs, and searches before broad exploration.

Do not acquire auxiliary memory, broad issue fields, whole-file content, or project-wide context when the active issue and targeted repository evidence are already sufficient.

Do not perform repository-wide, Jira-wide, Confluence-wide, or Git-history exploration unless the active task requires it.

Do not reread established context or investigate unrelated work.

Do not reconstruct missing requirements through broad project discovery. If information required by the task's Definition of Ready is missing, use targeted evidence first and escalate only if the task remains unsafe to execute.

Source of Truth

Use each source for its responsibility:

- Jira → requested work, scope, acceptance criteria.
- Repository → current technical state, implementation, tests, configuration, dependencies.
- Confluence/project docs → durable architecture, product decisions, runbooks.
- Official dependency documentation → exact behavior of installed external software.

Repository code and the active Jira task outrank assumptions from chat history.

If sources materially conflict, record the conflict instead of guessing or expanding scope.

Python / "uv"

Run all Python and project commands through "uv".

Never use "pip" directly or manually activate a virtual environment for normal project operations.

Use "uv add", "uv remove", "uv lock", "uv sync", and "uv run" as appropriate.

Do not use another Python environment or dependency manager unless the active task explicitly requires compatibility testing.

Canonical commands

Environment:

uv sync

Django checks:

uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run

Targeted tests:

uv run pytest path/to/test_file.py -q

Full test suite:

uv run pytest -q

Lint:

uv run ruff check .

Run targeted tests first.

Expand validation from targeted tests to relevant app/module tests when the change affects a broader surface.

Run the full suite only when required by change impact, the active task, or a completion/release gate.

Django / Wagtail

- Prefer Django/Wagtail conventions over custom abstractions.
- Avoid unnecessary signals, middleware, custom managers, and metaprogramming.
- Prevent obvious N+1 behavior on read/list paths.
- Preserve migration history.
- Never rewrite applied migrations unless explicitly required.
- Keep deployment-specific settings environment-driven.
- Never weaken security, validation, authentication, authorization, CORS/CSRF, or secret handling to make tests pass.

APIs

For consumer-facing contracts:

- preserve backward compatibility unless explicitly authorized otherwise;
- test status codes, validation, error behavior, and response shape;
- avoid new endpoints without a demonstrated consumer requirement.

Dependencies

Before adding a dependency:

1. verify existing Django/Wagtail/project capabilities are insufficient;
2. prefer a maintained package with a narrow purpose;
3. verify compatibility with the project's Python and framework versions;
4. manage dependency and lock state exclusively through "uv";
5. add only what the active task requires.

No speculative dependencies.

Validation

Prioritize validation of:

- acceptance criteria;
- changed behavior and regressions;
- validation and failure paths;
- permission/security boundaries;
- API contracts;
- migration/configuration safety when relevant.

Never report an unexecuted check as passing.

If validation fails, distinguish pre-existing failures from regressions introduced by the task using evidence.

Git / External Systems

Keep the final diff task-scoped.

Never overwrite unrelated user changes or include secrets, credentials, local databases, caches, virtual environments, or unrelated artifacts.

When the worktree is not clean, stage only explicit task-relevant paths.

Git execution contract

- Read the active Jira issue's exact Base branch, Working branch and commit convention/subject before changing code or documentation. A code-changing issue is not Ready without all three.
- Jira/Development-provided or recommended branch and commit metadata is authoritative. Use it verbatim; never invent, shorten, rename or substitute a branch name or commit subject.
- Before implementation and again before completion, verify `git branch --show-current`, `git status --short --branch`, the declared base and relevant remote refs, and required ancestry.
- Never implement an issue on `main`, an ancestor integration branch, a completed sibling branch, or a branch owned by another Jira issue. A technically correct diff on the wrong branch is not evidence for Done.
- One Epic owns one integration branch; each implementation Task owns one Task branch; each independently executed Subtask owns one Subtask branch. Child branches start from their current declared parent; consume predecessor work only after it is integrated into that parent unless the active issue explicitly declares another exact base.
- Use ordinary non-interactive `git` for repository operations, including fetch, branch/switch, status, diff, add, commit, integration and push. Never invoke shell `gh` during autonomous PDPW execution; use the connected GitHub capability/API only for GitHub-only inspection/actions when needed and available.
- Before Done, verify the final commit key/subject, branch ownership, push/remote equality, and exact-SHA CI where applicable. If a mandatory remote Git operation cannot complete non-interactively, report a blocker; do not substitute `gh` or ask the Project Owner to run it.

Jira defines work state. Confluence stores durable decisions/runbooks.

Do not continuously synchronize Jira or Confluence during implementation.

Update external systems only at meaningful state transitions or when explicitly required.

Do not transition an issue to Done when a mandatory completion action is blocked. Record the blocker and leave the issue in the appropriate non-Done state.

Stop / Escalation

Do not stop for ordinary implementation decisions.

Choose the simplest reversible solution consistent with the active task and existing architecture.

Stop and report a blocker only for:

- missing required access or credentials;
- irreconcilable acceptance criteria;
- unavailable mandatory external services;
- destructive actions requiring approval;
- unresolved security or data-loss risk;
- material Source-of-Truth conflicts;
- missing DoR information that cannot be resolved with targeted evidence.

Do not expand discovery merely because uncertainty exists.

Done

A task is technically complete when:

- acceptance criteria are satisfied;
- required validation passes;
- the final diff is task-scoped;
- evidence is concise and reproducible;
- residual risks or blockers are explicit.

A mandatory completion blocker is incompatible with `DONE`; report it and use the appropriate non-Done state.

Completion report:

PDPW-<id> — DONE | BLOCKED

Changed:
- <concise implementation summary>

Evidence:
- `<uv command>` -> PASS/FAIL
- `<uv command>` -> PASS/FAIL
- commit/PR: <ref if available>

Residual:
- none | <concise blocker/risk>

Do not append project-wide summaries or retrospectives unless explicitly request.
