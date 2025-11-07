# uDocket Platform Roadmap v2

This roadmap consolidates every planning artefact in `docs/`, the agents guides, and recent strategy updates. It provides a phased, end-to-end build sequence for a solo developer to deliver the full uDocket experience while maintaining strong typing, auditability, and region-specific data residency guarantees aligned to each organization’s policy.

## Guiding Principles
- **North star** (docs/AGENTS_LANGGRAPH.md): generate accurate, auditable legal artifacts from transcripts to accelerate court form preparation without sending PII outside approved regions.
- **Agent contract** (root `AGENTS.md`): deterministic outputs, versioned artifacts, per-run ops JSON, append-only audit JSONL, SHA-256 hashing, region-allowlisted Azure by default.
- **Typing discipline** (`docs/typing_refactor_plan.md` & `docs/typing_debt_assessment.md`): no regression in mypy/pyright counts, prioritize high-churn modules, define TypedDict/Protocol for shared payloads, track hotspots.
- **Architecture option 3** (docs/ROADMAP.md): single Django project with DRF, Channels, Celery, Postgres (RLS), OIDC (Keycloak), and Oso policies for authorization.
- **LLM execution**: provider-agnostic but fully compliant with tenant residency policies; never fall back to offline heuristics for content; expose configuration via stage maps and per-org policies.

## Current Baseline & Dependencies
1. **Repository preparation** (docs/ROADMAP.md §1)
   - Django project under `apps/platform`, maintain `manage.py`, settings package.
   - Ensure per-tenant storage layout under `MEDIA_ROOT/tenants/<org>/cases/<case_id>/`.
2. **Dependencies & tooling** (§2)
   - Django 5.2, DRF, Channels, Celery, django-environ, django-filter, drf-spectacular, pytest stack.
   - Policy/Audit: Oso, django-simple-history, django-auditlog.
   - IAM: Keycloak OIDC + JWT validation.
   - LLM SDKs: azure-openai, anthropic, openai-compatible variants; add stubs where missing.
3. **Settings & security** (§3) – enforce HTTPS defaults, ASGI configuration, env loading with `.env` for dev only.
4. **Database design** (§4) – Accounts, Organizations, Cases, CaseMembership, Jobs, CaseArtifact (generic, with metadata JSONB), AuditEvent; maintain referential integrity and history tracking.
5. **Auth & capabilities** (§5) – map Keycloak roles to capabilities, keep `has_capability` until Oso rollout complete.
6. **Operations & Channels** (§6) – structured Celery runtime, websocket event schema (`job.update`, `case.update`) with versioning.

## Phase Roadmap

### Phase 0 – Foundation & Typing Guardrails
- Finalise baseline items above, ensuring tests cover repo bootstrap.
- Integrate best-in-class LLM chat clients (docs/ROADMAP.md todo) for AWS Bedrock & Google Gemini; validate region guard rails.
- Seed file-driven defaults (see `AGENTS.md` standards): roles (Reviewer), reviewer policies, LLM stage maps per target (`summary`, `compose`, `guardian`, etc.), DOCX templates (uDocket default + per-org override), alert thresholds, data retention (default 90 days), questionnaire seeds, branding/theme.
- Clean typing hotspots (`docs/typing_debt_assessment.md`): begin annotating `apps/platform/operations/tasks.py`, `jobs/views.py`, `ui/views/*`, and remove legacy ignores where touched.
- Establish ToolDefinition schema (see Phase 1) with typed dataclasses/TypedDict to keep future pipeline typed.

### Phase 1 – Tool Platform Standardisation
- **ToolDefinition registry (done)**: backend dataclass describing key, label, permissions, LLM target, job endpoint, artifacts, editors, alerts support. Consumed by `build_tool_panels`/`analysis_modules_context` to avoid ad-hoc dictionaries. Implemented in `apps/platform/ui/views/presenters/tool_registry.py` with presenters updated to hydrate panels from the registry.
- **Shared panel layout (done)**: create `_tool_panel.html` for consistent header, controls, downloads, history, alerts, approvals; refactor Intake, Transcribe, Analyze, and Compose panels to extend it. Consolidate `_llm_controls.html`, status pills, job queue buttons, downloads menu across tools. Shared layout now lives at `apps/platform/ui/templates/platform_ui/tools/components/_tool_panel.html`; Timeline panel is being retired as compose absorbs that workflow.
- **ToolRun data model**: represent parent ToolRun (e.g., Transcribe) with child steps (Upload → Convert → Agent → Manual/Agent Edit) using consistent statuses; update presenters, tables, websocket payloads.
- **Modal upgrades**: extend `components/modals/text_modal.html` for version list, diff toggle, approval actions; reuse for transcripts, summary outputs, compose deliverables, Manual/Agent edits.
- **Manual Edit & Agent Edit tooling**: Manual Edit provides a textual editor saving proposed versions; Agent Edit offers chat-powered modifications. Both create child ToolRuns requiring approval per reviewer policy.
- **LLM tool panel pattern**: common data attributes (`data-llm-target`, provider chain JSON, stage cards) for all LLM-backed tools (summary, compose, questionnaire, guardian).

### Phase 2 – Core Deliverables & Staff Workflow
- **Compose Agent** (root `AGENTS.md`, docs/ROADMAP.md, AGENTS_LANGGRAPH): LLM-only pipeline producing client (grade-6 voice) and lawyer (professional) Markdown + DOCX deliverables, embedding timeline/graph assets (`timeline_v2.*`, `graph_v2.*`) with ops/audit logs.
- **Analyze Enhancements** (see `AGENTS.md` Analyze section): staff report artifact, discrepancy detector generating alerts, speaker mapping proposals with approval, removal of timeline/entity seeding (now Compose).
- **Questionnaire Tool & Interview Hub**: intake LLM tool with per-org question seeds, jobs history, Manual/Agent edits, Markdown artifact, transcript completion score; per-case interview page with live checklist, notes, call logging, questionnaire links, ops audit entries.
- **Alert Tool**: allow LLMs/staff to raise alerts (severity, category, message, action). Display on case banner & Alerts tab; audit everything. Acknowledgement deferred for future roadmap.
- **Parent/Child UI & Approvals**: parent rows show blocking child actions; pending edits set parent to waiting; cancelled children ignored. Reviewer-configurable approvals promote Manual/Agent edits; modal viewers expose version history & diffs.

### Phase 3 – Org Governance & Data Lifecycle
- **Org settings portal**: manage DOCX templates, reviewer policies, LLM configs per target, alert thresholds, data retention, questionnaire seeds, branding/theme, provider region policy. Defaults seeded via configuration files.
- **Data retention & deletion certificates**: default 90-day policy with overrides; two-party confirmation for early deletion; generate deletion certificates for all removals (routine, early, maintenance); purge backups per config; determine anonymisation vs deletion for metrics (TODO).
- **Audit log retention**: independent controls with deletion certificates.
- **Region policy design**: extend the current guard to per-org allowlists across providers with fail-fast behaviour.
- **Alert behaviour configuration**: thresholds and notification rules per org.
- **Artifact provenance**: ensure SHA-256 stored and metadata aligned for telemetry, approvals, retention.

### Phase 4 – Security, Observability, and Typing Expansion
- Continue eliminating `# type: ignore`, introduce TypedDict/dataclasses for presenters, runtime helpers, websocket payloads; record progress in typing docs.
- Implement universal logging system and automated auditing per docs/ROADMAP.md backlog.
- Complete Oso policy integration, harden Keycloak role mapping, enforce Postgres RLS everywhere.
- Expand Guardian agent coverage for Compose outputs and optional policy instructions.
- Optimise HTMX updates, caching, and failure messaging for LLM rate limits.

### Phase 5 – Extended Platform Features
- **Client portal**: authentication, forms/agreements, data deletion requests, estimated delivery times, profile/contact management, secure downloads.
- **Django admin improvements**: curated dashboards, read-only safeguards, bulk operations, typed admin forms.
- **Advanced reporting**: automated auditing, analytics dashboards, export tooling.
- **UI improvements**: responsive tweaks, theming, accessibility, interview/alert visualisations.
- **Future enhancements**: additional Compose variants, guardian policy wizards, pipeline health telemetry.

## Agents & LangGraph Alignment
- Maintain LangGraph personas and node design (docs/AGENTS_LANGGRAPH.md) for Analyze/Compose orchestration; optional dependency via `packages/core/agents/langgraph_orchestrator.py`.
- Shared state should capture all artifacts (summary, staff report, timeline, graph, compose outputs) plus intake, alerts, approvals.
- Prompts must enforce residency guardrails, schema compliance, and deterministic outputs; JSON stages leverage response-format schemas.
- Legacy LangGraph spec mentions offline summarisation fallback; per current policy we run LLM-only in production and reserve local fallback strictly for developer environments if ever enabled.

## Cross-Cutting Workstreams
- **Testing**: unit tests for agents (transcript parsing, version naming), presenters, tool registry, approval flows, retention engine; integration tests for task orchestration without external dependencies.
- **Documentation**: keep AGENTS guides, ROADMAPv2, and seed config docs synchronised.
- **Ops runbooks**: credential rotation, template updates, deletion certificates, alert configuration, Compose failure handling.
- **Regional compliance**: validate endpoints at runtime; fail fast with descriptive errors when region policies violated.
- **Metrics & observability**: track job runtimes, LLM token usage, approval latency, retention/deletion events.

## Immediate Next Steps
1. Finalise ToolDefinition schema and shared tool panel template (done).
2. Update Celery tasks to emit parent/child ToolRun payloads and leverage the registry.
3. Begin Compose agent implementation with timeline/graph migration; update AGENTS/ops docs as artifacts land.
4. Stand up Org Settings groundwork (template upload, reviewer policy seeds) to support approvals.
5. Schedule data retention and alert configuration work once Compose is functional.

By following this roadmap, uDocket will reach a production-ready, auditable legal assistance platform with clear phases, maintainable agents, rigorous typing, and a consistent UI/UX for staff and, ultimately, clients.
