# Compose Agent Guide

This guide documents the LangGraph-driven Compose agent that assembles client and lawyer deliverables from approved Analyze outputs. Read this alongside the root `AGENTS.md`, `docs/AGENTS_LANGGRAPH.md`, and the operations/UI area guides when touching Compose-related code.

## Purpose
- Consume approved Analyze artifacts (summary Markdown/JSON, timeline seeds, entity hints) plus intake metadata and case context.
- Draft client-facing and lawyer-facing Markdown deliverables, steer them through guard rails, and render DOCX versions.
- Produce deterministic, versioned files under `storage/media/cases/<CASE>/docs/` and append structured telemetry to `storage/media/cases/<CASE>/ops/`.
- Keep every LLM interaction in Canadian Azure regions; fail fast if credentials or provider assignments are missing.
- Prompt templates are versioned inside `packages/udocket_core/config/compose_prompts.yaml`. The agent loads that file by default and aborts if it is missing unless `COMPOSE_PROMPT_CONFIG` explicitly points elsewhere.

## LangGraph Overview
Compose uses LangGraph 0.6 with explicit reducers to avoid in-place mutation issues. The graph fan-outs client and lawyer work into dedicated “lanes” that loop until guard and QA checks succeed.

| Node | Stage name(s) | Role |
| --- | --- | --- |
| `ContextAssembler` | `compose.context` | Build the shared `ComposeContext` from Analyze outputs, intake metadata, and staff report. |
| `ClientComposer` / `LawyerComposer` | `compose.client.draft`, `compose.client.revise`, `compose.lawyer.draft`, `compose.lawyer.revise` | Draft (or revise) lane Markdown via Azure deployments. Attempts are capped per lane. |
| `ClientStructureValidator` / `LawyerStructureValidator` | `compose.client.structure`, `compose.lawyer.structure` | Deterministic guard reports on headings, word counts, readability. |
| `ClientComplianceGuard` / `LawyerComplianceGuard` | `compose.client.compliance`, `compose.lawyer.compliance` | Check for disallowed content and missing sections. |
| `ClientFactualityGate` / `LawyerFactualityGate` | `compose.client.factuality`, `compose.lawyer.factuality` | Validate timestamp coverage and factual accuracy; captures attempt history. |
| `ClientRevision` / `LawyerRevision` | `compose.client.revision`, `compose.lawyer.revision` | Deterministically build revision briefs when guards fail and retries remain. |
| `QAReviewer` | `compose.qa_reviewer` | Run the **lane-specific** QA pass immediately after guards, emitting status, alerts, recommendations, and directives (revise/editor/none). |
| `ClientQARevision` / `LawyerQARevision` | `compose.client.qa_revision`, `compose.lawyer.qa_revision` | Apply QA revision directives, then clear lane outcomes to force a re-run of the lane pipeline. |
| `ClientQAEditor` / `LawyerQAEditor` | `compose.client.editor`, `compose.lawyer.editor` | Optional editor passes that apply surgical edits when QA requests them; the lane re-enters QA afterwards. |
| `ComposeJoin`, `WaitForClientLane`, `WaitForLawyerLane` | — | Flow control nodes ensuring both lanes finish QA before the combined QA join and release gate execute. |
| `ReleaseGate` | `compose.release_gate` | Final guard: both lanes must pass all checks and QA status must be acceptable. |

Reducers (`_merge_stage_usage`, `_merge_lane_outcomes`, `_latest_lane_state`) guarantee that concurrent node writes remain conflict-free. All progress is reported via `_emit`, and the compose service streams those events into ops JSON / JSONL.

## Inputs
- Summary Markdown and JSON (`analysis/<summary_job_id>__summary_v1.*`) from the Analyze job metadata or fallback discovery.
- Optional timeline seeds and entity hints to enrich factual checks (`timeline_seeds_v1.json`, `entity_hints_v1.json`).
- Intake metadata and case metadata payloads supplied by the operations service.
- Organization-level LLM configuration (provider chain, stage models) resolved through `LLMSettings`.
- Optional DOCX template path (`COMPOSE_DOCX_TEMPLATE`) for rendering deliverables with organization branding.

## Outputs
Compose writes additive artifacts with `_vN` suffixing via `next_versioned`:

- `docs/<job_id>__compose_client_v1.md`
- `docs/<job_id>__compose_lawyer_v1.md`
- `docs/<job_id>__compose_client_v1.docx` (template-driven when configured, otherwise basic Markdown-to-DOCX)
- `docs/<job_id>__compose_lawyer_v1.docx`
- `docs/<job_id>__compose_bundle_v1.md` (combined excerpt of both briefs)
- `docs/<job_id>__compose_staff_report_v1.md` (QA reviewer staff narrative)
- `docs/<job_id>__compose_qa_report_v1.md` (structured QA summary)
- Ops metadata: `ops/<job_id>__compose_log.json`
- Audit trail: `ops/ops_compose.jsonl`

Case artifacts are registered from these files with deterministic titles; never overwrite existing artifacts—reruns append `_v2`, `_v3`, etc.

## Key Behaviours & Guardrails
- **Lane attempts**: Each lane tracks attempts, models, usage, and history. Revisions reset guard reports; if maximum attempts are reached, a `ComposeStageError` is raised.
- **QA loop**: QA increments `qa_iterations` and can route back to revision or editor nodes per lane. The release gate refuses to emit success until QA status is one of `ok|pass|approved`. `COMPOSE_QA_MAX_ITERATIONS` caps cycles.
- **LLM resilience**: Chat calls retry transient failures up to `COMPOSE_LLM_RETRY_ATTEMPTS` with exponential backoff starting at `COMPOSE_LLM_RETRY_DELAY_SECONDS`; configuration issues and other 4xx responses still fail immediately.
- **Event telemetry**: Graph nodes emit progress envelopes (`stage`, `event`, `lane`, `attempt`, etc.). The compose service writes these into both the per-run ops JSON and `ops_compose.jsonl`.
- **Snapshots & resume**: `ComposeRun` records every stage under `ops/<job_id>__compose_run/`. Calling `ComposeAgent.compose(..., resume=True)` rehydrates the latest snapshot so failed runs can restart without losing lane history.
- **Stage timing**: Each LangGraph node records elapsed seconds under `stage_durations` so ops metadata can surface per-stage latency trends.
- **Usage accounting**: Every LLM touch returns `{"stage_usage": {stage: token_usage}}`; reducers aggregate totals so ops metadata exposes full usage per stage.
- **Canadian regions only**: Provider selections must resolve to Canadian Azure deployments. The agent fails fast if assignments point elsewhere.
- **Docx rendering**: When `COMPOSE_DOCX_TEMPLATE` is set, the renderer injects Markdown via docxtpl subdocuments and exposes `*_plain` values for template fallbacks.

## Environment Configuration
See `.env.example` for the supported keys:

- `COMPOSE_PROVIDER_CHAIN`, `COMPOSE_TEMPERATURE`, `COMPOSE_LAWYER_TEMPERATURE`
- `COMPOSE_MAX_OUTPUT_TOKENS`, `COMPOSE_MAX_CLIENT_ATTEMPTS`, `COMPOSE_MAX_LAWYER_ATTEMPTS`
- `COMPOSE_MIN_TIMESTAMP_REFERENCES`, `COMPOSE_QA_ENFORCED`
- `COMPOSE_ENABLE_EDITOR`, `COMPOSE_QA_MAX_ITERATIONS`
- `COMPOSE_LLM_RETRY_ATTEMPTS`, `COMPOSE_LLM_RETRY_DELAY_SECONDS`
- `COMPOSE_ENABLE_ASYNC` (default off): when set to `1`, Compose runs client and lawyer lanes using LangGraph's async runner. The agent falls back to sync automatically if the runtime doesn't permit an event loop.
- Optional `COMPOSE_CLIENT_EDITOR_MODEL`, `COMPOSE_LAWYER_EDITOR_MODEL`, `COMPOSE_DOCX_TEMPLATE`
- `COMPOSE_PROMPT_CONFIG` (optional): absolute path to a YAML file following `packages/udocket_core/config/compose_prompts.yaml`. If unset, the agent requires that packaged default file; missing files raise immediately (no fallback).

Org-specific overrides are handled through `LLMConfiguration` records and `config/llm_assignments.json`.

## Failure Handling
- All user-visible failures raise `ComposeStageError` with the stage name, lane, provider/model, and attempt count to aid triage.
- Missing prerequisite artifacts are detected before LLM calls, with deterministic fallback placeholders written when possible (e.g., synthetic empty summary JSON).
- Hitting the QA iteration cap, guard failures after max attempts, or QA returning a blocking status will fail the job and annotate ops metadata.

## Testing Guidance
- Add unit coverage for helper utilities, reducers, and artifact writers under `tests/llm/` (mirror the patterns used by the Azure client tests).
- Extend operations/service integration tests whenever Compose service inputs or outputs change.
- When introducing new LangGraph nodes, add regression tests that exercise reducer behaviour and verify emitted events.

Maintaining these conventions keeps the Compose agent safe to rerun, easy to observe, and compatible with the broader LangGraph orchestration strategy shared across agents.
