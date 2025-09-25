# uDocket — Platform UI Agents Guide

This guide documents how to contribute safely and consistently to the Django-based Platform UI under `apps/platform/ui`. It complements the root-level AGENTS.md (agents contract, storage, ops) with UI‑focused principles, structure, and patterns so both humans and LLMs can work productively.

Scope: everything beneath `apps/platform/ui/` (templates, views, presenters, selectors, templatetags, client scripts).


## Principles
- Prefer composition: inherit templates from the closest base, and reuse shared partials/components instead of rolling bespoke HTML/JS.
- Determinism and reproducibility: consistent element IDs, data attributes, and rendering paths so scripts can target reliably.
- Minimal surface area: push shared behavior into low‑level includes and helpers (presenters, selectors, scripts) to reduce drift.
- Server‑rendered first: use HTMX for partial updates; keep JS lightweight and colocated in shared component scripts.
- Accessibility: use the provided modal/popover systems with focus management and ARIA attributes.
- Small, typed view functions: Python 3.11, type hints, explicit error handling, and guardrails aligned with backend security rules.


## Directory Layout
- Templates root: `apps/platform/ui/templates/platform_ui/`
  - Base layout: `platform_ui/layouts/base.html` (apps/platform/ui/templates/platform_ui/layouts/base.html:1)
  - Components: `platform_ui/components/` (server-rendered fragments, modals, reusable HTML/JS assets)
  - Tools: `platform_ui/tools/` (case tools such as transcribe, summary, timeline)
  - Pages: dashboard, cases, jobs
- Views root: `apps/platform/ui/views/` (HTTP endpoints and context builders)
  - Presenters: `views/presenters/` (pure formatting/aggregation helpers for UI shape)
  - Selectors: `views/selectors.py` (reads telemetry, artifacts, etc.)
  - Contexts: `views/contexts.py` (composes case/job tool state)
  - Templatetags: `apps/platform/ui/templatetags/` (display filters)


## Template Inheritance & Structure
- Always inherit from `platform_ui/layouts/base.html` unless rendering an HTML partial for HTMX swaps.
  - Base injects Tailwind CDN config, global copy‑to‑clipboard, modal/popover scripts, and styles.
  - Do not duplicate those resources in child templates.
- Tools panel base (all tools share):
  - Create a shared analysis/tools base template (planned: `platform_ui/tools/_panel_base.html`).
  - Transcribe, Summary, Timeline, and Relationships should inherit this base.
  - The base defines: panel header (label/status/pill), left action area (form/buttons), right sidebar (latest artifact), and history section.
- For modals, inherit from `platform_ui/components/modals/modal_base.html` and only override the relevant blocks.
  - Example pattern: `platform_ui/components/modals/text_modal.html` (apps/platform/ui/templates/platform_ui/components/modals/text_modal.html:1) extends the base and defines header/body/actions.
  - Specialized modals (e.g., transcript) extend `text_modal.html` (apps/platform/ui/templates/platform_ui/components/modals/transcript_modal.html:1).
- Name fragments with a leading underscore when the file is intended for include‑only usage under `components/` and `tools/` (e.g., `_panel.html`, `_job_action_menu.html`).


## Styling & Design Tokens
- Tailwind via CDN is configured in base (primary color scale and utility overrides). Use utilities consistently.
- Status pills: use the presenter‑supplied classes or helpers instead of ad‑hoc styles.
  - Mapping lives in `views/constants.py` and helpers in `views/presenters/utils.py`.
- Use utility classes (rounded, border, bg, text, hover) already present in templates to ensure a cohesive look.


## Client‑Side Utilities (lowest level)
- Base layout provides global helpers:
  - Copy‑to‑clipboard via `[data-copy-text]` and `[data-copy-target]` with toast feedback (apps/platform/ui/templates/platform_ui/layouts/base.html:1).
  - Local time rendering via `[data-ts]` attributes.
  - Error reporting beacon to `/ui/log`.
- Modals: include `platform_ui/components/_modal_scripts.html` from base and use the `platformUI.modal` API for programmatic dialogs.
  - Server‑rendered modals should use `modal_base.html` to inherit focus/ARIA patterns.
- Popovers: use `platform_ui/components/_popover_scripts.html` and existing popover menu templates.


## HTMX & Partial Rendering
- Use HTMX for panel/body swaps on case views and forms:
  - Set `hx-get`/`hx-post` and `hx-target` to `#tool-workspace` or a nearby container.
  - Prefer returning a fragment that can be dropped in without reloading the whole layout.
- When a server action should notify the client, set the `HX-Trigger` header with a small JSON payload. See `case_job_update_title` (apps/platform/ui/views/jobs.py:248) for a pattern.
- For non‑HTMX fetches, include `HX-Request: true` so server views return the body fragment (several scripts do this in components).


## Realtime & APIs
- Subscribe to Channels websockets for jobs and cases:
  - Jobs: `/ws/jobs/<job_id>/` group `jobs_<id>`; messages have `{ "type":"job.update", "event": <phase>, "job_id": <id>, ... }` (apps/platform/operations/consumers.py:1).
  - Cases: `/ws/cases/<case_id>/` group `cases_<id>`; messages have `{ "type":"case.update", ... }`.
- Fallback polling endpoints (DRF):
  - `GET /api/v1/jobs/<id>/status/` for lightweight status
  - `GET /api/v1/jobs/<id>/detail/` for full telemetry
  - `GET /api/v1/cases/<id>/jobs/summary|detail/` for case dashboards
- Standard websocket emitters: `send_job_update(...)` and `send_case_update(...)` in operations.
- Client scripts: see `components/jobs/_jobs_scripts.html` and `components/cases/_case_detail_scripts.html` for socket + polling orchestration and DOM updates.


## Modals & Popovers (Usage)
- Server‑rendered modal pattern:
  - View prepares `modal_*` context keys, then `render(..., "platform_ui/components/modals/<modal>.html", ctx)`.
  - The modal template extends `modal_base.html` or `text_modal.html` and fills header/body/actions.
  - Example: Transcript modal (apps/platform/ui/views/jobs.py:34) renders `platform_ui/components/modals/transcript_modal.html`.
- Client-created modal pattern:
  - Use `platformUI.modal.create({ heading, title, bodyText|bodyHTML|bodyNode, actions })` and `platformUI.modal.open(...)` from `_modal_scripts.html`.
- Popovers: reuse `components/_popover_menu.html` and `components/_action_menu_popover.html`; wire triggers with `data-popover` attributes.


## Jobs, Tables & Presenters
- Build job rows with presenters to ensure consistent sorting/filtering labels:
  - `build_job_rows` returns `display_rows` and `flat_rows` dictionaries ready for templates (apps/platform/ui/views/presenters/jobs.py:124).
  - Add row actions via `build_job_action_entries` in `views/presenters/job_actions.py`.
- Use shared table configs via `table_config(...)` in `presenters/cases.py` to standardize columns/filters and row templates.
- When updating a single job row, render `platform_ui/components/jobs/job_row.html` and pass the same row shape used by tables.


## Adding a New Tool Panel (e.g., Entities/Graph)
1) Templates
   - Add `platform_ui/tools/<key>.html` for the panel body. Follow the patterns in `tools/transcribe.html`, `tools/summary.html`, and `tools/timeline.html`.
   - Standard tool panel scaffold: inherit from the shared base (planned `tools/_panel_base.html`) that defines slots for header, action area (left), and sidebar/history (right).

2) Presenter wiring
   - Extend `build_tool_panels(...)` in `views/presenters/cases.py` to register your panel under a unique `key`.
   - Provide:
     - `label`, `description`
     - `status_label`/`status_class` (use `status_payload` helper)
     - `updated_at` (artifact or job‑based)
     - `body_template` and `body_context`
     - `jobs` (filter using `jobs_by_agent(..., keywords=("<key>", ...))`)
     - `jobs_table` via `table_config(...)`
   - For inheritance: keep body context consistent across tools: `case`, `module` (latest/history), `transcripts` or `sources`, optional `artifact_options`, and `job_endpoint_template`.

3) Analysis module context (optional)
   - If you will surface artifact history in the right‑hand column, add your artifacts to `analysis_modules_context(...)` with a `key` matching the panel.

4) Backend trigger endpoints
   - Panels that queue work should POST to an API/Celery endpoint and on success refresh the tool body. The `transcribe` panel shows this with HTMX and with programmatic refresh hooks.

5) Realtime refresh hooks
   - Emit `send_case_update(case_id, event="artifact.created", kind="<key>", job_id=job_id)` when your agent writes artifacts so the UI can react without manual refresh.

6) Hashsums are mandatory
   - Ensure server tasks compute SHA‑256 for every artifact (text, JSON, HTML). Persist in both `CaseArtifact.checksum` and the per‑run ops JSON.


## View Patterns & Permissions
- Authentication guard: call `ensure_authenticated(request)` and return early if set.
- Case scoping: resolve org and case using `get_case_and_org(...)` (apps/platform/ui/views/contexts.py:242) and `scope_jobs(...)` for job queries.
- Permission checks: prefer `user_can_review_case(user, case)` or explicit capability checks before mutating artifacts/titles.
- Always set CSRF tokens in forms; base layout injects `csrf_token` and `{% csrf_token %}` usage is expected.
- Error handling: log exceptions with context; return a small, styled error fragment for partial views rather than a full page.


## Telemetry & Artifacts in UI
- Read job telemetry via `job_telemetry_payload(...)` and maps via `job_telemetry_map(...)` to avoid duplicating DB/API logic.
- For transcript artifacts:
  - Use helpers in `views/transcripts.py` to resolve candidate paths and titles (`ensure_transcript_artifact`, `default_transcript_title`, `unique_transcript_title`).
  - Promote/update artifacts with metadata that records provenance (`created_via`, timestamps, user IDs where available).
- Logs & metadata modals follow the same modal base; keep copy/download affordances wired via data‑attributes and reuse the styles.


## Roadmap Alignment
- Authorization is migrating toward policy‑based (Oso/Polar) plus Postgres RLS; continue to use `has_capability` and membership checks until policies land.
- UI should prefer server‑rendered fragments with HTMX swaps, real‑time updates via Channels, and DRF endpoints for summaries/detail (see docs/ROADMAP.md:1).
- Analysis panels (summary, timeline, relationships/graph) should follow artifact and ops logging conventions so the Admin UI can surface history consistently.


## Naming & Data Attributes
- IDs: prefer stable, descriptive IDs incorporating object IDs (e.g., `job-status-<job_id>`).
- Data attributes: use `data-*` hooks consistently so shared scripts can attach behavior (`data-case-view`, `data-job`, `data-job-detail`, `data-ts`, `data-copy-*`).
- Partials: prefix include‑only files with `_` under `components/` or `tools/` and keep them self‑contained.


## JS Conventions
- Do not inline large scripts in templates other than centralized includes under `components/`.
- Feature scripts live in:
  - `components/cases/_case_detail_scripts.html` for case view behaviors
  - `components/jobs/_jobs_scripts.html` for jobs list behaviors
  - Modal/Popover core in `_modal_scripts.html` and `_popover_scripts.html`
- Prefer progressive enhancement: templates render fully functional HTML; JS adds affordances.


## Python Conventions
- Python 3.11, type annotations on function signatures and key variables; avoid one‑letter names.
- Keep view functions small and explicit; push formatting/aggregation into presenters and selectors.
- Use `@require_http_methods` decorators and return appropriate fragments when `HX-Request` is present.
- Log with module logger `apps.platform.ui` and include identifiers in `extra` where useful.


## Testing & Local Dev
- Run with Docker: `docker compose up --build`. UI is at `http://localhost:8000`.
- Use the UI to create a case, upload audio, and watch the jobs table update. The scripts and HTMX flows in transcribe and case views are a good reference.
- When adding a new panel or modal, validate:
  - Keyboard navigation and focus restoration
  - Copy affordances (`data-copy-*`)
  - HTMX swaps and `HX-Trigger` events


## Do / Don’t
- Do
  - Inherit from `layouts/base.html` and `components/modals/modal_base.html` where applicable
  - Centralize repeated HTML/JS in `components/`
  - Use presenters/selectors for shaping data passed to templates
  - Reuse status helpers and table configs
  - Keep artifacts/telemetry provenance consistent with the root agents contract
- Don’t
  - Add bespoke modal/popover implementations
  - Inline large JS blobs in random templates
  - Query across cases or bypass `scope_jobs`/permission helpers
  - Hardcode styles inconsistent with existing utility patterns


## Quick References
- Base layout: `apps/platform/ui/templates/platform_ui/layouts/base.html:1`
- Modal base: `apps/platform/ui/templates/platform_ui/components/modals/modal_base.html:1`
- Transcript modal: `apps/platform/ui/templates/platform_ui/components/modals/transcript_modal.html:1`
- Tools panel include: `apps/platform/ui/templates/platform_ui/tools/_panel.html:1`
- Case tool state: `apps/platform/ui/views/contexts.py:70`
- Jobs presenters: `apps/platform/ui/views/presenters/jobs.py:1`
- Case presenters (tool panels): `apps/platform/ui/views/presenters/cases.py:1`
