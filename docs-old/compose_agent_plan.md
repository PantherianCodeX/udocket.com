# Compose Agent LangGraph Plan

This plan captures the responsibilities, data contracts, and LangGraph orchestration strategy for the Compose agent. It reflects the current implementation in `packages/udocket_core/agents/compose_lib.py` and should stay in sync with the root [`AGENTS.md`](../AGENTS.md) guide and the operations service.

## Objectives
- Assemble client- and lawyer-facing deliverables from Analyze outputs without leaving Canadian Azure regions.
- Provide deterministic guard rails (structure, compliance, factuality, QA) that loop until documents meet release criteria.
- Emit rich telemetry (LLM usage, guard results, QA directives) for ops JSON and audit JSONL consumers.
- Render Markdown and DOCX artifacts using per-organization templates while retaining additive `_vN` versioning.

## Inputs & Context
- **Analyze artifacts**: latest approved summary Markdown and JSON (`analysis/<summary_job_id>__summary_v1.*`). Timeline seeds and entity hints are optional but improve factuality checks.
- **Case metadata**: intake payload, organization-scoped configuration, and resolved provider credentials via `LLMSettings`.
- **Transcript reference**: stored primarily for provenance; drafting relies on the Analyze outputs and claimable atoms.
- **Environment switches**: see `.env.example` for `COMPOSE_*` defaults (temperature, attempts, QA requirements, editor toggles, DOCX template path).

## Graph Architecture
Compose uses LangGraph 0.6 with explicit reducers. Nodes fan out into client and lawyer “lanes” that operate independently until a join syncs them for QA.

| Node | Stage names | Purpose | Notes |
| --- | --- | --- | --- |
| `ContextAssembler` | `compose.context` | Build shared `ComposeContext` from Analyze data, intake metadata, and staff report. | Deterministic; no LLM. |
| `ClientComposer` / `LawyerComposer` | `compose.client.draft`, `compose.client.revise`, `compose.lawyer.draft`, `compose.lawyer.revise` | Draft or revise Markdown using Azure models. | Attempts tracked per lane; revision briefs loaded when present. |
| `ClientStructureValidator` / `LawyerStructureValidator` | `compose.client.structure`, `compose.lawyer.structure` | Check headings, minimum word counts, readability. | Deterministic guard reports. |
| `ClientComplianceGuard` / `LawyerComplianceGuard` | `compose.client.compliance`, `compose.lawyer.compliance` | Flag disallowed content and missing sections. | Deterministic guard reports. |
| `ClientFactualityGate` / `LawyerFactualityGate` | `compose.client.factuality`, `compose.lawyer.factuality` | Validate timestamp references and reconcile with claimable atoms. | Records attempt history for ops logs. |
| `ClientRevision` / `LawyerRevision` | `compose.client.revision`, `compose.lawyer.revision` | Build revision briefs when guards fail and attempts remain. | Deterministic string assembly. |
| `ComposeJoin`, `WaitForClientLane`, `WaitForLawyerLane` | — | Ensure both lanes complete guard cycles before QA runs. | Pure control nodes. |
| `QAReviewer` | `compose.qa_reviewer` | LLM QA pass; emits status, alerts, recommendations, staff report, and lane directives (`revise`, `editor`, `none`). | Temperature forced low (`gpt-4o-mini` default). |
| `ClientQARevision` / `LawyerQARevision` | `compose.client.qa_revision`, `compose.lawyer.qa_revision` | Apply QA revision directives and clear lane outcomes to force reruns. | Deterministic. |
| `ClientQAEditor` / `LawyerQAEditor` | `compose.client.editor`, `compose.lawyer.editor` | Optional LLM “editor” pass for surgical edits when QA requests it. | Uses zero-temperature, JSON-formatted responses. |
| `ReleaseGate` | `compose.release_gate` | Final validation that both lanes passed guards and QA status is acceptable. | Raises descriptive failure messages when blocking. |

Reducers: `_latest_lane_state` ensures the most recent lane runtime state wins; `_merge_lane_outcomes` tracks released outcomes; `_merge_stage_usage` accumulates per-stage token usage.

## QA & Revision Loop
1. Lanes run draft → guard sequence. Failed guards generate revision briefs while attempts remain.
2. Successful guard passes store a `LaneOutcome`. Both outcomes are required before QA executes.
3. QA can: (a) approve (`status` in `ok`, `pass`, `approved`), (b) request lane revision (`lane_actions[lane].action == "revise"`), or (c) request the editor pass.
4. Revision/editor directives clear the lane outcome, allowing the graph to rerun the lane from the composer node. `COMPOSE_QA_MAX_ITERATIONS` caps QA cycles.
5. The release gate double-checks guard status and QA result before returning success.

## Artifacts & Telemetry
- Markdown: `docs/<job_id>__compose_client_v1.md`, `docs/<job_id>__compose_lawyer_v1.md`, plus a combined bundle Markdown.
- DOCX: client and lawyer deliverables rendered via docxtpl if `COMPOSE_DOCX_TEMPLATE` is defined, otherwise through basic Markdown conversion.
- QA deliverables: `docs/<job_id>__compose_staff_report_v1.md`, `docs/<job_id>__compose_qa_report_v1.md`.
- Ops metadata: `ops/<job_id>__compose_log.json` (includes stage usage, guard summaries, QA directives, artifact paths).
- Audit lines: appended to `ops/ops_compose.jsonl` for every emitted progress event plus a final job summary.
- Token usage: every LLM-producing node returns `{"stage_usage": {stage: usage_map}}` so totals aggregate cleanly.

## Model & Token Defaults
- Default provider chain: `["azure"]` (overrideable via `COMPOSE_PROVIDER_CHAIN` or `LLMConfiguration` records).
- Stage-to-model defaults live in `packages/udocket_core/agents/compose/llm_profiles.py` and `config/llm_assignments.json` (e.g., `compose.client.draft` → `gpt-4o`).
- Temperature: client drafts use `COMPOSE_TEMPERATURE` (0.6 default), lawyer drafts use `COMPOSE_LAWYER_TEMPERATURE` (0.4 default). Revisions and QA use cooler temperatures for determinism.
- Editors run at temperature `0.0` and must return JSON with `document` and `change_log`.

## Failure Handling
- Guard or QA failures after exhausting attempts raise `ComposeStageError` with stage, lane, provider, model, and attempt number.
- Missing inputs lead to deterministic placeholder artifacts (e.g., empty summary JSON) before LLM invocation to maintain predictable file sets.
- Hitting the QA iteration cap results in an explicit failure message specifying the iteration limit.
- Release gate errors include guard status summaries (structure/compliance/factuality per lane) to speed up debugging.

## Ops & Testing Expectations
- Every progress event is captured via `progress_callback`; services should stream them to real-time UI updates and ops JSONL.
- Add regression tests when introducing new nodes or reducers. Focus on: lane attempt accounting, QA loop routing, docx rendering, and audit log shape.
- Integration tests in the operations service should verify metadata updates (`compose_status`, artifact registration) and guardian triggers once compose succeeds.

Keeping this plan current ensures Compose remains reliable, observable, and consistent with the rest of the agent ecosystem that relies on LangGraph orchestration.
