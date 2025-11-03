# uDocket — Platform (Django) Agents Guide

Scope: this file governs contributions across `apps/platform/` (accounts, authorization, cases, artifacts, jobs, operations, UI). Deeper AGENTS.md files (e.g., `ui/AGENTS.md`) refine guidance for their subtree.

## Architecture
- ASGI‑first Django app with Channels, Celery, DRF, and HTMX UI.
- Multi‑tenant: organization scoping enforced by view helpers and selectors; do not bypass them.
- Storage: per‑tenant case roots under `MEDIA_ROOT/tenants/<ORG_ID>/cases/<case_id>/` created by `ensure_case_dirs` (apps/platform/operations/storage.py:20).
- Agents: implemented in `packages/udocket_core/agents/` and orchestrated via Celery tasks (apps/platform/operations/tasks.py:1). UI integrates through presenters + selectors.
 - Public API endpoints (DRF):
   - Jobs: `/api/v1/jobs/<id>/status/`, `/api/v1/jobs/<id>/detail/`, download endpoints
   - Cases: `/api/v1/cases/<id>/jobs/summary|detail/`, `/api/v1/cases/<id>/capabilities/`
 - Realtime: Channels groups `jobs_<id>` and `cases_<id>` with emitters `send_job_update` and `send_case_update` for live UI refresh.

## Core Conventions
- Keep view functions thin and typed; push formatting/aggregation to `views/presenters/*` and `views/selectors.py`.
- Always guard with `ensure_authenticated`, resolve organization and case via `get_case_and_org`, and scope querysets via `scope_jobs`/`scope_cases`.
- For writes, verify capabilities using `user_can_review_case` or `has_capability(user, case_id, ...)` (apps/platform/authorization/capabilities.py:1).
- Deterministic outputs and ops logging: align with root AGENTS.md — metadata JSON, human logs, and JSONL audit in `ops/`.

## Typing expectations
- Adhere to `docs/typing-roadmap.md` and `docs/typing_refactor_plan.md`. When you touch a module, raise its typing bar in the same PR.
- For `apps/platform/operations/*`, CI runs with `disallow_untyped_defs`; do not introduce new untyped defs or `Any` returns.
- Use `TypedDict`/`Protocol`/dataclasses for payloads instead of `dict[str, Any]`; avoid blanket ignores and casts to `Any`.
- Annotate pytest fixtures (see `tests/AGENTS.md`) before adding new tests; never suppress pyright warnings in the UI layer.

## URL Prefixes & Routing (Tenancy)
- UI, API, and websockets should be prefixed by organization slug: `/{org_slug}/...` and `/ws/{org_slug}/...`.
- Middleware resolves `org_slug` to the active organization and enforces cross‑org access denial.
- When adding new routes, ensure reverse() helpers accept/emit `org_slug` where appropriate so links remain tenant‑scoped.

## Background Work (Celery)
- Prefer explicit, argument‑only task signatures (no implicit DB state). See `transcribe_job` (apps/platform/operations/tasks.py:80).
- Tasks should:
  - Update `Job` status transitions deterministically
  - Emit websocket updates via `send_job_update`/`send_case_update`
  - Write meta and logs using `update_job_meta` and `append_job_log` (apps/platform/operations/utils.py:1)
  - Respect timeouts and avoid network calls outside Canada for PII

## Storage & Paths
- Use `tenant_case_root`/`ensure_case_dirs` to allocate per‑case subfolders: `audio/`, `transcript/`, `analysis/`, `ops/` (apps/platform/operations/storage.py:12).
- When regenerating artifacts, use versioned filenames (e.g., `_v2`) instead of overwriting (see `_next_versioned` in core agent).

## Jobs & Telemetry
- Use `jobs.telemetry` helpers to expose stable UI/API payloads and avoid re‑parsing ops files ad hoc (apps/platform/jobs/telemetry.py:1).
- Keep `Job` status enums and sort behavior consistent with UI constants (status pill styles). New statuses require a UI mapping.

## UI Integration
- Compose UI state with `views/contexts.py` and presenters; do not query DB directly in templates.
- For HTMX flows, return partials and set `HX-Trigger` headers for client refreshes where needed.

## Security & Tenancy
- Scope all queries via `scope_jobs`/`scope_cases` and check capabilities before writes or artifact access.
- Avoid leaking filesystem paths; use download endpoints with authorization checks for artifacts.
- Roadmap: migrate capability checks toward Oso/Polar policies with Postgres RLS backing (docs/ROADMAP.md). Keep current `has_capability` and membership checks until policy engine is integrated.

## Data Partitioning Options
- Current (Option A): single shared schema with strong org scoping via `organization_id` and Case membership. Recommended with Postgres RLS.
- Option: per‑organization Postgres schemas (e.g., `tenant_<org>`), maintained via migrations and `search_path` switching. Heavier ops cost but clearer data separation.
- Decide per environment; code should not assume a single schema when building raw SQL.

## Testing
- Start with focused unit tests for presenters/selectors and model utils, then integration tests for views and tasks.
- Tests avoid executing external services; mock Azure and blob uploads; exercise task code directly when feasible (see tests/test_platform_flow.py:18).

## Analysis & Compose
- Analyze task: writes outline/summary/staff report/timeline seeds/entity hints under `analysis/` with ops meta/audit.
- Compose task (target=`compose`): assembles final deliverables and owns timeline/graph generations internally (LLM-only). Artifacts:
  - `analysis/<job_id>__compose_client_v1.(md|docx)` and `analysis/<job_id>__compose_lawyer_v1.(md|docx)`
  - `analysis/<job_id>__timeline_v2.(json|html|png)` and `analysis/<job_id>__graph_v2.(json|html|png)`
  - Ops: `ops/<job_id>__compose_log.json`, audit `ops/ops_compose.jsonl`
- Existing timeline/graph tasks may temporarily wrap Compose sub-stages; prefer routing UI to Compose directly.
- Emit `send_case_update(..., event="artifact.created", kind=<type>, job_id=<id>)` after writing artifacts to notify UI modules.

## Parent/Child Job Actions & Approvals
- Parent rows represent a tool (Transcribe, Analyze, Compose). Child rows capture steps (Upload → Convert → Agent → Manual/Agent Edit).
- Parent status reflects the next blocking child action; cancelled children skip; pending edits keep parent pending.
- Manual Edit and Agent Edit create child tasks on save and require Reviewer approval to promote the version into the parent.
- Text artifact modal viewer must expose version history and comparison by default.

## LLM Tool Panels & Questionnaire
- All LLM tools share a common panel template with jobs history and Manual/Agent Edit actions.
- Intake panel adds “Generate Questionnaire” (LLM) using per‑org seeds/forms; saves Markdown for interview use; computes transcript completion score.

## Interview Page
- Add a per-case Interview page: live checklists (consent/content), notes, call start/end logging, questionnaire access; append minimal ops JSONL.

## Org & Reviewer Settings (file-driven defaults)
- Seed defaults for roles (ensure Reviewer exists), reviewer policies (required counts, allowed roles per page/tool), DOCX template selection, alert thresholds, retention windows, questionnaire seeds, branding/theme.
- Expose these in Org Settings; keep Canada-only region guard for now; TODO: design cross-provider region policy.
