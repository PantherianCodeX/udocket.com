---
title: uDocket — LangGraph Agent Orchestration Specification
subtitle: Canonical pipelines for Transcribe, Analyze, Compose, Timeline, and Relationship agents
author:
  - Agent Platform Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Architecture
  - Applied AI Engineering
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - QA Engineering Lead
  - SRE Manager
approved_by:
approved_date:
header-includes:
  - |
    <style>
      table{font-size:8.5pt;}
      table td,table th{font-size:inherit;word-break:break-word;overflow-wrap:anywhere;}
      figure svg text,figure svg tspan{fill:#111!important;}
      figure svg text{font-family:"DejaVu Sans","Trebuchet MS",Arial,sans-serif!important;}
      figure.full-width-diagram img{width:100%;height:auto;display:block;}
    </style>
  - |
    <header class="page-header">uDocket — LangGraph Agent Orchestration Specification <br> Canonical pipelines for Transcribe, Analyze, Compose, Timeline, and Relationship agents</header>
  - |
    <footer class="page-footer">Confidential · Last updated 2025-10-29 · Page <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Agent Platform Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Architecture; Applied AI Engineering |
| Reviewers | QA Engineering Lead; SRE Manager |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Covers the shared LangGraph orchestration layer and the canonical pipelines for Transcribe, Analyze, Compose, Timeline, and Relationship agents. This spec also governs graph configuration, schema enforcement, QA gates, and shadow mode deployments.
- **Structure:** Sections follow the standard 0–10 layout with appendices for schema and error taxonomies. Per-agent responsibilities live in §2; pipeline contracts, tooling, and LangGraph runtime details live in §3; operational guardrails are in §§5–8.
- **Maintenance:** Run `python -m doc_tools.manage_docs --lint docs/automation/langgraph-agents.md` plus targeted lints (`python -m doc_tools.check.links --strict`) before shipping agent changes. Graph modifications require LangGraph contract tests (§3.2) and QA harness replays (§6.1) to pass in CI.
- **Change protocol:** Any change that alters agent outputs, pipeline structure, or QA gating must update this spec and include LangGraph acceptance test results in the PR description.
- **References:** This document intentionally scopes to LangGraph agents. Integration specifics live in their respective service documents.
- **Contacts:** Applied AI Engineering (primary owners), Platform Architecture (co-owners).

______________________________________________________________________

## 1) Purpose

**Purpose:** Define the canonical LangGraph-based agent pipelines, contracts, and guardrails that transform transcripts into downstream analyses and deliverables. **|**
**Contract:** This spec owns the agent interface, graph configuration model, QA gates, and operational controls that keep agents deterministic, observable, and compliant. Implementations must adhere to the shared manifests, artifact naming conventions, and error taxonomy defined here. **|**
**State:** Manifests persist per job under `storage/media/tenants/<ORG_ID>/cases/<case>/analysis|docs|ops`. **|**
**Failures & handling:** Graph activation rejects invalid schemas; runtime failures follow the taxonomy in §5. **|**
**Observability:** Metrics for pipeline/job/lane execution and ops JSONL streams (`ops_transcription.jsonl`, `ops_summary.jsonl`, `ops_compose.jsonl`) record pipeline versions, node usage, and retry history. **|**
**Breadcrumbs:** Orchestration runtime and graph builders live under `packages/core/agents/*`; acceptance tests under `tests/*`. **|**
**References:** TDD §5.5, Platform Runtime §3, Ops runbooks RB-AGENT-*.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Enumerate each agent’s charter, lane responsibilities, and artifact ownership. **|**
**Contract:** Agents must implement the shared runtime contracts, persist deterministic outputs, and expose audit-friendly manifests for every job. **|**
**State:** Each agent manages job manifests, derived artifact manifests, envelope hashes, QA logs, and Ops JSON per run; Analyze maintains an internal `AtomsIndex` leveraged by validation. **|**
**Failures & handling:** Runtime failures map to the taxonomy in §5. **|**
**Observability:** Metrics `agent_job_duration_seconds{agent=}`, `agent_retry_total`, `atoms_extracted_total`, QA issue density, and pipeline dashboards. **|**
**Breadcrumbs:** Transcription `packages/core/agents/transcribe_lib.py`, Analyze `packages/core/agents/analyze_lib.py` + stages `packages/core/agents/analyze/stages/`, Compose `packages/core/agents/compose_lib.py` + orchestrator `packages/core/agents/compose/orchestrator.py`, manifests `packages/core/agents/manifests.py`. **|**
**References:** Transcribe/Analyze/Compose specs, automation LangGraph diagrams, Ops runbooks RB-AGENT-*.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/diagrams/automation/langgraph-agents/pipeline-overview-v1.svg" alt="LangGraph pipeline overview">
  <figcaption style="font-size: 0.9em; color: #555;">Pipeline overview showing Transcribe → Analyze (Atoms) → Compose flow</figcaption>
</figure>

### 2.1 Transcription agent (binding)

- Modes: streaming (WebSocket) and batch (provider-hosted jobs). Diarisation is enabled for batch jobs only.
- Inputs: local filesystem path or HTTPS SAS URL, language, diarisation flag (batch only), optional transcription overrides.
- Outputs: transcript text `storage/media/tenants/<ORG_ID>/cases/<case>/transcript/<job_id>__transcript.txt`, structured transcript JSON `transcript/<job_id>__transcript_v1.json` (segments with deterministic UUIDs, speaker roster, hashes), per-run metadata JSON `ops/<job_id>__transcription_log.json`, human-readable log, and audit append `ops/ops_transcription.jsonl`.
- Header & manifest metadata: case/job identifiers, source hashes, language, duration, diarisation mode, settings snapshot SHA, provider version, conversion fingerprints (e.g., ffmpeg SHA-256).
- Retry semantics: streaming jobs resume from buffered offsets; batch jobs poll provider status and retry failed uploads with exponential backoff capped by settings budgets. Provider fallback is disabled unless Settings explicitly assigns alternates.
- Capability negotiation: `TranscriptionCapabilityMap` validates language/diarisation support before dispatch; unsupported combinations raise `E_INPUT_INVALID`.
- Cancellation: best-effort cancellation propagates through provider APIs; manifests mark `cancel_requested` and retain partial progress for audit.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/diagrams/automation/langgraph-agents/transcribe-pipeline-v1.svg" alt="Transcribe pipeline">
  <figcaption style="font-size: 0.9em; color: #555;">Transcribe pipeline with normalization, Azure health checks, retry loops, and artifact emission</figcaption>
</figure>

### 2.2 Analyze agent (binding)

- Inputs: structured transcript JSON (`transcript/<job_id>__transcript_v1.json`, text fallback only when JSON is unavailable), intake/questionnaire artifacts, DOCX outline template headers, case metadata, Settings overrides for prompts, lane concurrency ceilings, token budgets, and deterministic idempotency keys (`uuid5(job_id, stage_fingerprint)`).
- Parallel lanes: LangGraph fans out from `InputDiscovery` into outline, timeline, entities/relations, issues, gaps, and flags/alerts lanes. Lanes share the typed `AnalyzeState` mapping, emit deterministic UUIDs, and enforce JSON Schemas before merging into `SummaryDraft`, `StaffReport`, and `QAReview` nodes.
- Lane QA: every lane emits a `LaneResult` payload backed by `AnalyzeLaneResult` (Pydantic) with `status`, `artifacts[]`, `evidence_refs[]`, and `uuid_dirty_set[]`. The `LaneQA` node validates schema parity, atom coverage, questionnaire completeness, and intake alignment before deciding whether to advance, request a focused revision, or quarantine.
- Outputs: discrete artifacts under `analysis/` — `outline_v1.json`, `timeline_v1.json`, `entities_v1.json`, `issues_v1.json`, `gaps_v1.json`, `flags_v1.json`, `alerts_v1.json`, `summary_v1.json`, `staff_report_v1.md`, `qa_report_v1.json` — plus per-run metadata JSON and `ops/ops_summary.jsonl` audit entries. `_v{n}` suffixes apply on reruns without touching prior files.
- Finalize-only writes: only `Finalize` nodes persist artifacts to disk; lane nodes write to state or scratch space. Revisions never overwrite existing files; new versions use `_v{n}` suffixes.
- Summary lane: consumes all upstream JSON artifacts (not Analyze Markdown) to generate canonical `summary_v1.json`; Compose reads this JSON directly. Markdown render happens after JSON validation so staff edits always trace back to the canonical JSON.
- Revision directives: QA emits structured `AnalyzeRevisionDirective` objects that reference failing UUIDs, cite evidence gaps, and instruct the same LangGraph lane to revise only the affected slices. Directives preserve `preserve_spans[]` so passing artifacts stay frozen across retries, eliminate “good data” regeneration, and keep token churn predictable.
- Retry, cancellation, and resume: LangGraph checkpoints persist in Postgres via the shared checkpointer so retries reuse the last successful state. Cancellation halts active nodes, marks manifests with `cancel_requested`, and resumes only when checkpoint digests still match the pipeline definition and settings snapshot.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/diagrams/automation/langgraph-agents/analyze-pipeline-v1.svg" alt="Analyze pipeline">
  <figcaption style="font-size: 0.9em; color: #555;">Analyze LangGraph pipeline with atom-fed lanes, QA feedback loops, and artifact emission</figcaption>
</figure>

#### 2.2.1 Atom layer (binding)

- Purpose: derive internal “Atoms” — normalised, evidence-backed statements with deterministic UUIDs — from transcript segments. Atoms remain internal to Analyze and power validation, conflict detection, and QA scoring.
- Extraction flow: sentence heuristics plus (optional) LLM assists yield candidate claims; the pipeline canonicalises text, detects negation cues, attaches transcript evidence (`segment_id`, timestamps, speakers), assigns UUIDs, and merges corroborating statements into an `AtomsIndex`.
- Validation hooks: outline, timeline, entities, issues, gaps, flags, alerts, and summary lanes consult the shared `AtomsIndex` to attach citations, flag unsupported claims, and surface `SummaryCheck` verdicts (`CONFIRMED`, `CONFLICTED`, `UNSUPPORTED`, `AMBIGUOUS`) into `qa_report_v1.json`.
- Observability: per-run ops JSON records atom counts, conflict groups, extraction latency, and thresholds; optional debug dumps (`analysis/<job_id>__atoms_v1.json`) emit only when `ANALYZE_SAVE_ATOMS=1` for diagnostics.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/diagrams/automation/langgraph-agents/atoms-pipeline-v1.svg" alt="Atoms extraction pipeline">
  <figcaption style="font-size: 0.9em; color: #555;">Atoms extraction and validation overlay feeding Analyze quality gates</figcaption>
</figure>

<figure class="full-width-diagram">
  <img class="diagram" src="../build/diagrams/automation/langgraph-agents/analyze-feedback-loops-v1.svg" alt="Analyze lane feedback and revision directives">
  <figcaption style="font-size: 0.9em; color: #555;">Analyze lane feedback loop with targeted revision directives that preserve passing outputs</figcaption>
</figure>

#### 2.2.2 Lane QA & revision loops (binding)

- Node catalog: Analyze reuses the Compose-style LangGraph idioms — `LaneDraft`, `LaneQA`, `LaneRevision`, and `LaneFinalize` nodes per artifact lane — so Compose and Analyze share operational semantics, cost controls, and observability. Nodes register under `packages.core.agents.analyze.graph` and expose typed signatures (`AnalyzeState -> AnalyzeState`).
- Lane QA decisions: each `LaneQA` node executes schema validation, atom cross-checks, intake/questionnaire verification, and deterministic heuristics (e.g., minimum evidence count per issue). Outcomes map to `{"advance", "revise", "quarantine"}`; the node records a `LaneQAResult` payload plus structured findings for ops metadata.
- Revision directives: when `revise`, QA constructs an `AnalyzeRevisionDirective` describing failing UUIDs, acceptance criteria, prompts, and `preserve_spans[]`. LangGraph routes back to the same lane’s `LaneRevision` node, which swaps the instruction set, clamps temperature/length, and merges the new slice into the existing artifact while keeping preserved spans byte-identical.
- Freeze & merge rules: preserved spans enforce hash equality; revised spans carry deterministic UUIDv5 derived from `(job_id, lane_id, canonical_content)` so retries remain idempotent. If QA escalates to `quarantine`, the lane halts, emits `status="blocked"`, and records findings for review.
- QA fan-in: once all lane QA nodes report `advance`, a `QAJoin` node assembles `qa_report_v1.json` summarizing findings, completeness scores, and directives executed. Any lingering revisions block finalize until their dirty set clears, aligning Analyze with Compose’s QA gating discipline.

##### 2.2.2.1 Lane QA defaults (binding)

Default acceptance thresholds (tunable later via configuration, but binding here as engineering defaults):

- Timeline: minimum 1 evidence pointer per event; timestamp precision within ±1.0s; speaker attribution present for ≥95% of events.
- Entities: ≥1 evidence pointer per entity; alias clustering accuracy target ≥90% on golden sets; relations reference valid entity UUIDs.
- Issues/Gaps: ≥2 corroborating evidence pointers for issues rated high; at least 1 for medium; gaps must point to impacted sections.
- Summary: per-section citation density ≥1 citation per 200 words; prohibited patterns rejected (empty headings, speculative claims).
- Flags/Alerts: severity justification present; evidence pointer required; alert rate within configured bounds per job length.

Lane QA emits structured findings that include metric values, pass/fail checks, and remediation notes to guide revision directives.

### 2.3 Compose agent (binding)

- Inputs: canonical Analyze artifacts (`summary_v1.json|.md`, `timeline_v1.json`, `entities_v1.json`, `issues_v1.json`, `gaps_v1.json`, `flags_v1.json`, `alerts_v1.json`), intake data, deliverable templates (DOCX/Markdown), and lane concurrency budgets.
- Lanes: parallel client and lawyer deliverable pipelines (draft → editor passes → lane QA), optional bundle excerpt, followed by cross-lane QA review and final packaging. Lanes share shared context (summary JSON + structured artifacts) but render voice-specific outputs.
- Outputs: client and lawyer deliverables (`docs/<job_id>__compose_client_v1.md|.docx`, `docs/<job_id>__compose_lawyer_v1.md|.docx`), bundle excerpt Markdown (if enabled), compose staff report (`docs/<job_id>__compose_staff_report_v1.md`), compose QA report (`docs/<job_id>__compose_qa_report_v1.md` / `.json`), per-run metadata JSON, and `ops/ops_compose.jsonl` audit lines.
- Assembly nodes: each active lane includes a deterministic `*_ASSEMBLE` stage that programmatically embeds JSON context into Markdown/DOCX templates immediately after lane QA passes and before any cross-lane QA. Assemblies are pure functions and do not touch storage.
- Finalize-only writes: Finalize nodes read the already-assembled payloads, version artifacts (`_v1`, `_v2`, …), compute SHA-256 manifests, and write ops JSON/JSONL entries; no other node writes to disk.
- Safety: lane validators enforce forbidden patterns, required sections, link limits, and voice guidance; promotion requires QA PASS.
- Factuality guard: Compose relies on citations embedded in canonical Analyze artifacts (driven by Atoms) and enforces minimum citation thresholds per deliverable section before promotion.
- Revision directives: QA nodes emit structured `RevisionDirective` payloads that name the failing sections, preserve passing segments, and provide edit-specific prompts for the same drafting agent. Directives include citation expectations and acceptance criteria to minimise thrash.
- Retry & cancellation: SectionWriter nodes retry within configured budgets; revision directives are replayed until PASS, and successful sections are frozen between attempts. Cancellation stops graph execution, leaves partial artifacts versioned `_v{n}`, and records state in manifests.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/diagrams/automation/langgraph-agents/compose-overview-v1.svg" alt="Compose pipeline overview">
  <figcaption style="font-size: 0.9em; color: #555;">Compose pipeline overview with revision directives feeding the same agent instead of full rewrites</figcaption>
</figure>

<figure class="full-width-diagram">
  <img class="diagram" src="../build/diagrams/automation/langgraph-agents/compose-lanes-v1.svg" alt="Compose lanes with targeted revisions">
  <figcaption style="font-size: 0.9em; color: #555;">Client, lawyer, and bundle lanes share revision directives so only failing sections are redrafted</figcaption>
</figure>

### 2.4 Timeline & relationship agents (roadmap, informative)

- Roadmap agents will consume Analyze timeline/events and entities JSON to produce richer chronological visualisations and relationship graphs with deterministic UUID lineage.
- Responsibilities: maintain speaker attribution, event windows, entity linkage, and evidence references.
- Dependencies: reuse LangGraph pipelines with dedicated nodes for diarisation merge, event normalisation, entity clustering, and QA scoring. QA stages must emit focused revision directives (event-level or edge-level) so replays correct only failing segments while preserving accepted evidence.
- Current status: prototypes remain in shadow mode until QA metrics meet §6 targets; binding specification will follow once promoted.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/diagrams/automation/langgraph-agents/timeline-pipeline-v1.svg" alt="Timeline agent pipeline">
  <figcaption style="font-size: 0.9em; color: #555;">Future timeline agent pipeline with revision directives scoped to event corrections</figcaption>
</figure>

<figure class="full-width-diagram">
  <img class="diagram" src="../build/diagrams/automation/langgraph-agents/relationship-pipeline-v1.svg" alt="Relationship agent pipeline">
  <figcaption style="font-size: 0.9em; color: #555;">Future relationship agent pipeline with edge-level revision directives to prevent unnecessary rewrites</figcaption>
</figure>

### 2.5 Stage capability catalog (binding)

- Capability classes: LangGraph pipelines route provider work through capability-first `AgentTask` values instead of artifact-specific names.
  - `GENERATE` — long-form narrative generation (summary lanes, staff reports, Compose drafts).
  - `EXTRACT` — structured extraction/classification (outline/timeline/entities/issues/gaps/flags/alerts, bundle excerpt seeds).
  - `EVAL` — evaluation/QA/factuality scoring (lane QA, cross-lane QA, staff QA reports).
  - `EMBED` — embedding/vectorization (retrieval prep, future similarity search).
  - `ATOMS` — deterministic atomisation with optional LLM assists (input discovery + citations); falls back to `EXTRACT` if no provider call is required.
- Stage keys: every LangGraph node carries a typed `StageKey` (`StageKey` StrEnum) that records intent, schema, dependencies, and retries. A typed `StageMap` (exported in `packages/automation/pipelines/stage_map.py`) maps each `StageKey` to `{agent_task, llm_profile_id, model_hint, depends_on[], retry_budget, cost_ceiling}` so routing stays deterministic.
- Canonical Analyze stage keys (`AN_*`) map to capability classes as follows:

| StageKey | Capability (`AgentTask`) | Purpose |
| --- | --- | --- |
| `AN_INPUT_DISCOVERY` | — (pure) | Load transcript JSON, intake, questionnaire payloads. |
| `AN_ATOMS_EXTRACT` | `ATOMS` | Canonical atoms with citations + UUID5. |
| `AN_OUTLINE_DRAFT`, `AN_TIMELINE_BUILD`, `AN_ENTITIES_EXTRACT`, `AN_ISSUES_EXTRACT`, `AN_GAPS_EXTRACT`, `AN_FLAGS_EXTRACT` | `EXTRACT` | Structured JSON artifacts feeding summary + Compose. |
| `AN_SUMMARY_DRAFT`, `AN_STAFF_REPORT` | `GENERATE` | Narrative outputs assembled from upstream JSON (no raw transcript). |
| `AN_LANE_QA`, `AN_EVAL` | `EVAL` | Schema/citation/coverage QA with atom cross-checks. |
| `AN_FINALIZE_WRITE` | — (pure) | Versioned writes + SHA-256 manifests + ops JSON/JSONL. |

- Canonical Compose stage keys (`CO_*`) map similarly:

| StageKey | Capability (`AgentTask`) | Purpose |
| --- | --- | --- |
| `CO_CONTEXT_BUILD` | — (pure) | Assemble ComposeContext from Analyze artifacts + intake. |
| `CO_CLIENT_DRAFT`, `CO_LAWYER_DRAFT`, `CO_BUNDLE_DRAFT` | `GENERATE` | Role-specific drafting using structured summary JSON. |
| `CO_CLIENT_GUARDS`, `CO_LAWYER_GUARDS`, `CO_BUNDLE_GUARDS`, `CO_CLIENT_FACTUAL`, `CO_LAWYER_FACTUAL`, `CO_BUNDLE_FACTUAL`, `CO_LANE_QA` | `EVAL` | Lane-level structural, policy, and factuality gates. |
| `CO_CLIENT_ASSEMBLE`, `CO_LAWYER_ASSEMBLE`, `CO_BUNDLE_ASSEMBLE` | — (pure) | Programmatic template embedding once lane QA passes. |
| `CO_CROSS_QA`, `CO_QA_REVIEW` | `EVAL` | Cross-lane QA and staff QA reporting. |
| `CO_FINALIZE_WRITE` | — (pure) | Version deliverables, compute hashes, emit manifests/ops logs. |

- New stage keys must register in the StageMap, include JSON Schema references, and stay capability-aligned. Diagram callouts (see §2.2, §2.3) label StageKeys to keep engineers, QA, and ops in sync.

______________________________________________________________________

## 3) API Contract

**Purpose:** Govern the configurable LangGraph pipelines, tool catalog, concurrency rules, and agent interfaces that keep jobs deterministic and auditable. **|**
**Contract:** Pipelines are defined in Settings (`agents.pipeline.*`), tools in `agents.tools.*`, and assistant graphs follow the same activation rules. GraphRunner enforces schema hashes, stage ordering, deterministic manifests, and single-writer finalize semantics. **|**
**State:** Activation metadata captures `graph_version`, `graph_schema_sha256`, `settings_snapshot_sha256`, lane concurrency budgets, and idempotency keys; compiled graphs are cached for reuse alongside per-job checkpoints. Tool registry cache stores schema-validated bindings. **|**
**Failures & handling:** Invalid activations fail closed with actionable errors (`E_INPUT_INVALID`, `E_SCHEMA_MISMATCH`); runtime mismatches raise `E_INTEGRITY_MISMATCH`; missing tools block activation. **|**
**Observability:** Activation dashboards, CI contract tests, tool registry validation logs, prompts provenance, and ops manifests capture pipeline changes and drifting configurations. **|**
**Breadcrumbs:** Settings integration `apps/platform/settings/agents_pipeline.py`, pipeline catalog `packages/core/agents/pipeline_catalog.py`, LangGraph orchestrator `packages/core/agents/langgraph_orchestrator.py`, analyze stages `packages/core/agents/analyze/stages/`, compose orchestrator `packages/core/agents/compose/orchestrator.py`, activation tests `tests/agents/test_pipeline_catalog.py`. **|**
**References:** This section focuses on LangGraph contracts; platform activation specifics are covered elsewhere.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/diagrams/automation/langgraph-agents/agent-orchestration-classes-v1.svg" alt="Agent orchestration classes">
  <figcaption style="font-size: 0.9em; color: #555;">Agent orchestration classes</figcaption>
</figure>

### 3.1 External Interfaces (binding)

- External orchestration (out of scope here) invokes LangGraph pipelines and publishes progress. Task payloads carry manifest references and idempotency keys for replay. Activation/validation of configuration and any UI concerns are documented elsewhere.

### 3.2 Internal Interfaces (binding)

- Pipeline catalog, tool registry, and LangGraph orchestrator form the internal contract that manages stage ordering, lane concurrency, retries, and checkpoint management.
- Analyze stage implementations (`packages/core/agents/analyze/stages/*`) expose typed callables that operate on transcript JSON, intake data, and lane-specific context, returning structured payloads that comply with exported JSON Schemas.
- Compose orchestrator merges shared context (summary JSON + analysis artifacts) into role-specific lanes, ensuring that only finalize nodes write deliverables.

- Pipelines enumerate `{pipeline_id, graph_version, graph_schema_sha256, runner, stages[]}` with per-stage metadata `{stage_id, langgraph_node_id, llm_profile_id, prompt_template_id, tool_ids[], enabled, retry_budget, cost_ceiling, depends_on[]}`. Revision directives are structured `{stage_id, target_uuid[], failing_checks[], instructions, preserve_spans[]}` and attach to checkpoints for focused replays. Versioning is additive; prior versions remain callable for queued jobs & replays until archived.

### 3.3 API Error Codes (binding)

**Purpose:** Enumerate LangGraph agent `ApiError.code` values so service clients, worker orchestration, and UI flows respond deterministically. **|**
**Contract:** Agent launch and management endpoints reuse the platform catalog in [`Platform Runtime §3.3`](../platform/runtime.md#33-api-error-codes-binding); the scenarios below capture how those codes manifest for LangGraph pipelines. **|**
**State:** Runtime emits error codes as part of agent responses; schema parity is enforced by `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail lint and trigger `agent_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards chart `agent_api_error_total{code}`; synthetic launches follow pause/resume flows. **|**
**Breadcrumbs:** Error catalog lives in `docs/overview/tdd/appendices/api_error_codes.md`, enforcement in `packages/core/agents/api_errors.py`, tests `tests/agents/test_error_codes.py`. **|**
**References:** Platform Runtime §3.3, Ops runbooks RB-AGENT-ACTIVATION/RB-AGENT-QA.

> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#langgraph-agent-orchestration)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Idempotency key replay with a different payload or stale manifest version. | Read the latest manifest, regenerate the payload, and retry with a fresh Idempotency-Key. |
| `POLICY_BLOCK` | Guardian or residency guard rejected a pipeline launch or artifact promotion. | Present Guardian reason codes, remediate policy inputs, or seek waiver approval before retrying. |
| `PROVIDER_DEGRADED` | LLM provider or speech service unavailable and fallback chain exhausted. | Record degraded status, halt automatic retries, and resume once health probes report recovery. |
| `QUARANTINED` | Generated artifact or intermediate output quarantined pending Guardian review. | Route to reviewer workflow, capture remediation notes, and relaunch only after clearance. |
| `RATE_LIMIT` | Org or agent exceeded concurrency or FinOps budgets. | Honour Retry-After, shed background runs, and reschedule once the budget resets. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | No | agent_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | agent_guardian_block_total<br>agent_api_error_total |
| `PROVIDER_DEGRADED` | 503 | Yes | agent_api_error_total |
| `QUARANTINED` | 423 | Yes | agent_guardian_block_total |
| `RATE_LIMIT` | 429 | No | agent_api_error_total<br>agent_rate_limit_total |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

### 3.4 LangGraph runtime & checkpointing (binding)

- Runtime floor & ceiling: agents pin `langgraph>=0.2,<0.3` so we stay on the current major until we plan for breaking API changes. Compose and Analyze share the same runtime feature set, enabling consistent debugging/tools.
- GraphRunner + StateGraph: pipelines compile into `StateGraph` objects with named nodes per lane. `packages.core.agents.langgraph_runtime` hosts the orchestrator, `AnalyzeGraph`, and `ComposeGraph` builders plus shared middlewares (telemetry, tool dispatch).
- Checkpointer backend: the canonical LangGraph checkpointer runs against Postgres (`agents_graph_checkpoint` table) in the primary application database. Every node write stores `{job_id, pipeline_id, graph_version, node_id, state_jsonb, input_hash, output_hash, created_at}`; RLS + future OPA policies ensure per-tenant isolation without duplicating storage engines.
- Retention & pruning: checkpoints retain for 30 days or until job artefacts graduate to Deliverable status, whichever is longer. A nightly task prunes expired checkpoints after verifying manifests reference the final digests.
- Resume semantics: resumable jobs must present the original settings snapshot SHA and manifest hash. GraphRunner loads the latest checkpoint, verifies `input_hash` parity, and replays pending nodes only. Divergent definitions raise `E_INTEGRITY_MISMATCH` and require a fresh run.
- Idempotency keys: every node invocation derives `idempotency_key = sha256(job_id || pipeline_id || node_id || graph_version || input_hash)` and records it in the manifest + checkpoint row. Upstream services can safely retry nodes because Postgres enforces uniqueness on `{node_id, idempotency_key}`.
- Policy readiness: the checkpoint schema reserves `policy_tags[]` for future policy evaluation and caching at the node level.

### 3.5 LangGraph Tool Registry & Onboarding (binding)

- Catalog stored in `agents.tools.catalog[]` with each entry describing `{tool_id, description, input_schema, output_schema, binding, timeout_seconds, cost_profile_id, idempotent?, tool_idempotency_key}`.
- Validators ensure JSON Schema compliance, unique IDs, deterministic idempotency keys, and safe retry budgets. Non-idempotent tools require `max_attempts=1`.
- Tool bindings map to Python adapters, gRPC services, or HTTP endpoints resolved via `ToolFactory`.
- Activation runs schema validation, dry-run LangGraph graphs using the tool, and telemetry registration checks (`tool_invocation_total`, `tool_cost_estimate_total`).
- Audit: tool changes recorded in ops manifests with `{tool_id, version, schema_sha256}`.
- Initial wave ships with the built-in “no external tool” set (Analyze + Compose lanes depend only on LLM calls and storage writes). The empty registry plus scaffolding keeps the catalog deterministic until we introduce specialised tools.

### 3.6 Conversational Assistant Pipelines (binding)

- Assistant pipelines (`assistant.staff`, `assistant.client`, future variants) share the same activation flow as task agents. Nodes include retrieval, guardrails, responder lanes, moderation, and post-processing writers.
- Settings overrides: `assistant.retrieval.sources[]`, `assistant.voice.*`, `assistant.moderation.*` allow org-level tuning within validator limits; lane structure changes remain SYSTEM-only.
- QA: conversational replay harness replays standardized transcripts and portal conversations; acceptance tests assert retrieval scope, guardrail triggers, and moderation escalations.
- Safety: assistant lanes use the same QA gating patterns; replays ensure disclaimers + audit logs cover instructions/responses.

### 3.7 LangGraph Runtime Contracts (normative)

- GraphRunner compiles LangGraph graphs to Python callables, stores compiled graphs keyed by `{pipeline_id, graph_version}`, and enforces deterministic node execution with replayable checkpoints.
- Nodes record checkpoint digests (input + output hashes); retries compare digests to avoid duplicate work; concurrency locks ensure stage-level OCC.
- Deterministic identity: nodes/stages generate reproducible `uuid5` identifiers from `{pipeline_id, node_id, graph_version}`; manifests reference these IDs for audit alignment.
- Adoption guardrails: fallback plan keeps linear pipelines available; feature toggles `agents.runtime.langgraph_enabled` guard release; shadow mode (§8.2) and acceptance tests required before toggling default.

#### 3.7.1 Out-of-band edits (normative)

- Human and assistant edits to artifacts happen outside LangGraph pipelines. Pipelines never overwrite externally edited files; they produce new versions (`_v{n}`) and record provenance in manifests.
- QA within LangGraph may recommend revisions via directives, but these do not override external edits. Editors can accept or reject those revisions in their own workflows.

______________________________________________________________________

## 4) State Management

**Purpose:** Describe how agents persist manifests, artifacts, and lineage to provide forensic traceability. **|**
**Contract:** Every agent job produces manifests capturing input hashes, settings snapshot, pipeline + graph versions, tool usage, and resulting artifact paths. **|**
**State:** Manifests stored under `storage/media/tenants/<ORG_ID>/cases/<case>/ops/<job_id>__<agent>_manifest.json`; audit JSONL streams append to `ops/ops_<agent>.jsonl`; QA logs and acceptance verdicts live alongside artifacts. **|**
**Failures & handling:** Missing or corrupt manifests trigger `E_INTEGRITY_MISMATCH` and quarantine outputs; pipeline activation blocks if manifests fail schema validation. **|**
**Observability:** Manifests feed lineage diagrams, QA dashboards, and FinOps metrics. `python -m doc_tools.manage_docs --lint --check-manifests` ensures schema parity during CI. **|**
**Breadcrumbs:** Manifest models `packages/core/agents/manifests.py`, ops logging `packages/core/agents/logging.py`, lineage tooling `packages/core/agents/lineage.py`, QA harness `tests/agents/test_manifest_compliance.py`. **|**
**References:** This document.

- Filesystem layout: transcripts (text + JSON) under `transcript/`; analysis artifacts (`outline_v1.json`, `timeline_v1.json`, `entities_v1.json`, `issues_v1.json`, `gaps_v1.json`, `flags_v1.json`, `alerts_v1.json`, `summary_v1.json`, `staff_report_v1.md`, `qa_report_v1.json`) under `analysis/`; compose deliverables and QA/staff artifacts under `docs/`; ops metadata/logs under `ops/`.
- Naming convention: `<job_id>__<artifact>[_v{n}]<extension>` ensures sorted history; manual or agent edits create new versions requiring reviewer approval.
- Hashing: manifests include SHA-256 of outputs, pipeline manifest version, tool versions, provider/model versions, and settings snapshot hash.
- Lineage: manifests link `source_transcript`, `case_id`, `job_id`, upstream artifact IDs, and template IDs. Compose manifest references analyze outputs by UUID to preserve traceability.
- Envelope schema: `spec/schemas/llm_envelope.schema.json` defines separation between `instructions[]`, `source_content[]`, `system_policies[]`, `safety_tags[]`; Compose/Analyze nodes validate compliance before invoking models.

______________________________________________________________________

## 5) Failure Modes

**Purpose:** Capture the failure taxonomy, retry behaviour, and mitigation strategies that keep agent pipelines reliable. **|**
**Contract:** Agents classify failures into deterministic categories (`TRANSIENT`, `POLICY`, `INPUT`, `INTEGRITY`, `CONCURRENCY`) and respond with defined retries or escalations. **|**
**State:** Ops metadata JSON records `{code, class, attempt, final, retry_after}`; manifests flag partial outputs; QA logs capture verification failures. **|**
**Failures & handling:** Transient provider errors retry with exponential backoff; policy violations quarantine; input errors surface; integrity mismatches halt and trigger audit; concurrency conflicts short-retry before manual intervention. **|**
**Observability:** Metrics `agent_retry_total{class=}`, `agent_job_duration_seconds{outcome=}` and synthetic jobs monitor reliability. **|**
**Breadcrumbs:** Failure taxonomy `packages/core/agents/errors.py`, retry logic `packages/core/agents/retry.py`, tests `tests/agents/test_failure_modes.py`. **|**
**References:** LangGraph runtime and this spec.

- Cancellation semantics: GraphRunner issues cancellation tokens to active nodes; nodes honour cooperative cancellation and persist progress for partial outputs.
- Resume rules: resumed jobs verify checkpoint digests, ensuring idempotent behaviour; if pipeline definitions drift, the runtime raises `E_INTEGRITY_MISMATCH` and recommends a fresh run.
- Provider failure mitigations: fallback providers require waiver and explicit assignment; backlog watchers page after configurable SLO breaches.
- QA failure handling: QA lane `E_POLICY_FORBIDDEN` stops promotion; reviewers receive ops log pointers and findings.

______________________________________________________________________

## 6) Observability

**Purpose:** Define the metrics, QA harnesses, and continuous evaluation commitments for LangGraph agents. **|**
**Contract:** All pipelines must emit metrics for job duration, retries, QA issue density, WER (transcription), review deltas (Analyze/Compose), and FinOps cost budgets. QA harnesses replay golden datasets per release. **|**
**State:** Metrics exported via Prometheus/Grafana; QA harness outputs stored as artifacts (`analysis/<job_id>__qa_report.json`), QA issue logs appended to ops JSON. Quality review summaries archived as `QUALITY_KPI_REPORT` artifacts. **|**
**Failures & handling:** Metric regressions trigger runbooks; QA harness failures block release; FinOps anomalies create decision-log entries (`DECISION_LOG_AGENTS`). **|**
**Observability:** Dashboards “Agent Pipelines – Activation”, “Agent Shadow Runs”, “QA Acceptance”, FinOps monitors; synthetic jobs generate consistent load. **|**
**Breadcrumbs:** QA harness `tests/agents/test_langgraph_acceptance.py`, WER evaluation `tests/agents/test_transcription_quality.py`, Grafana dashboards `infra/grafana/agents_quality.json`, FinOps monitors `ops/finops/agents_cost_dashboard.json`. **|**
**References:** This document.

- **Transcription accuracy:** WER ≤ 8 % on on-demand, ≤ 6 % on batch measured quarterly; metrics `transcription_wer_pct{mode,language}`; regressions ≥ 2 % trigger incident review.

- **Review delta:** Reviewer change rate ≤ 15 % of sections; QA issue density ≤ 0.2 blocking defects per artifact; tracked via QA logs.
- **FinOps blend:** Monitor tokens-per-approved artifact and rejection counts to ensure budget adherence without quality degradation.
- **Shadow acceptance:** Shadow runs must match production outputs within tolerance windows (§8.2) before promoting new pipelines.

### 6.1 SLOs & Targets (binding)

**Purpose:** Capture availability, quality, latency, and cost expectations for LangGraph pipelines. **|**
**Contract:** Agent run completion, QA acceptance, lane latency, and token budgets must meet the thresholds below before promotions proceed. **|**
**State:** Metrics `agent_job_completion_ratio`, `agent_lane_duration_seconds`, `agent_queue_latency_seconds`, `agent_token_budget_violation_total`; dashboards “Agent Pipelines – Activation”, “Agent QA Acceptance”, FinOps monitors `ops/finops/agents_cost_dashboard.json`. **|**
**Failures & handling:** Breaches invoke RB-AGENT-PIPELINE, RB-AGENT-QA, or RB-FINOPS-LANGGRAPH before enabling new activations. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, QA harness reports, and shadow run comparisons provide evidence. **|**
**Breadcrumbs:** QA harness `tests/agents/test_langgraph_acceptance.py`, telemetry `packages/core/agents/logging.py`, runbooks `docs/ops/runbooks/agents/*.md`. **|**
**References:** This document.

- **Pipeline availability:** ≥99.5% of LangGraph runs complete without manual retry, measured via `agent_job_completion_ratio`; breaches trigger RB-AGENT-PIPELINE before promotions proceed.
- **QA acceptance:** Automated QA issue density stays ≤0.2 blocking defects per artifact; exceedances invoke RB-AGENT-QA and pause affected pipelines.
- **Lane latency:** Analyze lane P95 ≤ 15 minutes, Compose lane P95 ≤ 45 minutes, Transcribe backlog clearance P95 ≤ 5 minutes (`agent_lane_duration_seconds{lane}` / `agent_queue_latency_seconds`). Breaches require corrective action before enabling new activations.
- **FinOps guard:** `agent_token_budget_violation_total` remains zero; if triggered, RB-FINOPS-LANGGRAPH engages and approvals halt until the budget recovers.

______________________________________________________________________

## 7) Security & Compliance (binding)

**Purpose:** Summarize how LangGraph pipelines respect platform security, residency, and privacy controls. **|**
**Contract:** Pipelines must honour settings snapshots, residency/waiver metadata, Guardian judgments, and redact PII/PHI from logs; no node may bypass policy enforcement owned by Guardian, Policy Residency, or Observability specs. **|**
**State:** Settings snapshots, residency annotations, Guardian manifests, and ops JSONL logs capture security posture per job. **|**
**Failures & handling:** Residency drifts or Guardian overrides block pipeline promotion until RB-RES-BLOCK or RB-AGENT-QA remediation completes; logging/redaction incidents route to RB-MASK. **|**
**Observability:** Metrics `agent_guardian_block_total`, `agent_logging_neverlog_violation_total`, runbook evidence, and Guardian dashboards. **|**
**Breadcrumbs:** Guardian spec, Policy Residency spec, Observability spec, Ops runbooks RB-AGENT-QA / RB-MASK. **|**
**References:** Policy Residency §2, Guardian §5, Observability §7.

______________________________________________________________________

## 8) Operational Notes (binding)

**Purpose:** Document activation, migration, and incident workflows required to run LangGraph pipelines safely. **|**
**Contract:** Pipelines ship via staged activations (shadow → pilot → general) with automated rollback; migrations must preserve checkpoints and manifests; incidents follow RB-AGENT-\* playbooks. **|**
**State:** Activation manifests under `ops/agents/activations/<pipeline>.json`, shadow run evidence `ops/shadow_runs/<pipeline>/<timestamp>.json`, migration plans in `ops/agents/migrations/*.md`. **|**
**Failures & handling:** Activation failure, shadow divergence, or migration drift triggers rollback plus incident review before resumes. **|**
**Observability:** Dashboards “Agent Activations”, “Shadow Acceptance”, `agent_activation_status` metrics, and ops manifests record rollout health. **|**
**Breadcrumbs:** Activation scripts `scripts/agents/activate_pipeline.py`, Ops runbooks RB-AGENT-ACTIVATION/RB-AGENT-SHADOW. **|**
**References:** Worker cluster spec §8, Ops governance policy, RB-AGENT-* runbooks.

### 8.1 Operational Posture (binding)

**Purpose:** Capture staffing, maintenance windows, and readiness expectations. **|**
**Contract:** Applied AI Engineering owns the primary pager with Platform Operations as secondary; acknowledge pages within 15 minutes and maintain 24/7 coverage. **|**
**State:** On-call rosters `ops/oncall/agents.md`, maintenance calendar `ops/agents/maintenance.ics`, readiness checklist `ops/agents/readiness.md`. **|**
**Failures & handling:** Coverage gaps escalate to Platform Operations leadership and block releases until rota restored. **|**
**Observability:** PagerDuty analytics (`agents_oncall_ack_latency_seconds`), rota health dashboards. **|**
**Breadcrumbs:** Ops/oncall repo, incident management policy, RB-AGENT-ACTIVATION. **|**
**References:** Ops governance policy §3, Worker cluster spec §8.

- Primary on-call rotates weekly (Applied AI Engineering); Platform Operations maintains a shadow rotation for redundancy.
- Maintenance windows: weekly Tuesday 02:00–04:00 local and monthly Saturday 20:00–22:00 UTC for migrations; customer-impacting changes require 72-hour notice.

### 8.2 Incident Triggers (binding)

**Purpose:** Define the alerts and dashboards that escalate LangGraph incidents. **|**
**Contract:** Each trigger maps to RB-AGENT playbooks with paging enabled during coverage windows. **|**
**State:** Alert definitions under `infra/monitoring/agents-prometheus-rules.yaml`; suppression policies in `ops/agents/alerts.md`. **|**
**Failures & handling:** Monthly alert reviews prune noisy signals; missing runbooks block rollout until remediation. **|**
**Observability:** Grafana “Agent Alerts” dashboard, Alertmanager audit logs. **|**
**Breadcrumbs:** Monitoring repo, Ops runbooks RB-AGENT-*. **|**
**References:** Observability spec §6, Ops governance policy.

- `agent_shadow_divergence_total` or replay mismatches trigger `RB-AGENT-SHADOW` to disable the candidate pipeline and roll back to the prior manifest.
- `agent_job_duration_seconds` / `agent_retry_total` breaches signal backlog or provider instability and dispatch `RB-AGENT-ACTIVATION`.
- QA failure spikes (`qa_blocking_total`, `qa_issue_density`) page via `RB-AGENT-QA` to rerun validation and quarantine outputs.
- Settings activation failures (`agents_pipeline_activation_failed_total`) route to `RB-AGENT-ACTIVATION`; responders collect manifests and block further rollouts.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Ensure operators have actionable playbooks for agent degradations, activation failures, and QA regressions. **|**
**Contract:** Runbooks listed here must remain current, link to Ops catalog entries, and surface evidence expectations for compliance. **|**
**State:** Runbook markdown lives under `docs/ops/runbooks/agents/`; drill evidence and after-action reviews are archived in `ops/runbooks/agents/drills/<date>/`. **|**
**Failures & handling:** Missing or stale runbooks block launch; drills uncover coverage gaps and feed remediation tickets. **|**
**Observability:** Ops catalog build (`make docs.sync.runbooks`), drill checklist dashboards, and on-call retros track preparedness. **|**
**Breadcrumbs:** Runbook catalog `docs/ops/runbooks.md`, evidence store `ops/runbooks/agents/`, drill tracker `ops/runbooks/agents/drill_log.csv`. **|**
**References:** Ops governance policy, RB-AGENT-* runbooks.

- Runbooks must cover activation rollback, shadow divergence, QA defect surge, plus the temporary LangSmith/LangFuse workflows documented under `specs/001-ai-refactor-plan/reports/`.
- On-call rotation uses `RB-AGENT-TIMEOUT`, `RB-AGENT-RETRY`, `RB-AGENT-ACTIVATION`, `RB-AGENT-SHADOW`, and `RB-AGENT-QA`.
- Drill cadence and evidence capture feed quarterly readiness reviews and SOC2/SOCPA audits.

#### 8.3.1 Runbook Index (informative)

The catalog enumerates each runbook with owner, verification cadence, and Ops catalog ID. Maintained via `make docs.sync.runbooks`; stale ownership or verification dates fail the docs lint and block merges.

- `RB-AGENT-ACTIVATION` — Applied AI Engineering (primary), Platform Operations (secondary), verified quarterly.
- `RB-AGENT-SHADOW` — Platform Operations (primary), Applied AI Engineering (secondary), verified quarterly.
- `RB-AGENT-TIMEOUT` — Verified monthly.

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Highlight the runbooks that must exist before activating or modifying agent pipelines. **|**
**Contract:** Each primary runbook documents trigger conditions, escalation path, mitigation steps, and evidence capture. **|**
**State:** Markdown sources under `docs/ops/runbooks/agents/`; evidence appended to drill log. **|**
**Failures & handling:** Missing steps or outdated escalations prompt remediation tickets before launch readiness sign-off. **|**
**Observability:** Ops QA reviews, incident postmortems, and audit sampling confirm runbook quality. **|**
**Breadcrumbs:** `docs/ops/runbooks/agents/agent_activation.md`, `docs/ops/runbooks/agents/agent_shadow.md`, `docs/ops/runbooks/agents/agent_retry.md`. **|**
**References:** Ops QA policy.

- Activation rollback: capture commands to revert settings activation, disable pipelines, and restore prior manifests.
- LangSmith evaluation ingest: include the `packages/devops/readiness` CLI flow plus evidence artifacts (`reports/langsmith_workspace_records.jsonl`, `reports/langsmith_eval_export.json`, `reports/langsmith_smoke.jsonl`) before promoting prompts.
- LangFuse R&D enablement: reference the SOP in `specs/001-ai-refactor-plan/reports/langfuse_enable_disable.md`, enforce the 15-minute disable SLA, and list `reports/langfuse_enable_disable.md` as the binding evidence log.
- Activation dry-runs: follow `specs/001-ai-refactor-plan/reports/activation_plan.md`, log steps via `reports/activation_dry_run.jsonl`, and store checklists/signoff artifacts referenced below.
- Shadow divergence: enumerate alert thresholds, disable steps, data capture for analysis, and communications checklist.
- QA defect surge: describe manual QA staffing and follow-up tasks.

#### 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover SLO breach recovery, quarantine spikes, backlog management, and manual reconciliation; evidence stored in `ops/runboo../data/agents/<YYYY>/<MM>/` with retrospective notes.
- `make docs.check.runbooks` plus PagerDuty analytics verify execution; missed drills require catch-up within 30 days and block activation rollouts.
- Compliance reviews reference drill evidence, incident logs, and manual review ledgers to demonstrate readiness for auditors.

### 8.4 Migrations & Backfills (normative)

**Purpose:** Describe operational work required to migrate manifests or backfill lineage after pipeline changes. **|**
**Contract:** Backfill scripts must be idempotent, record audit entries, and run under controlled settings toggles. **|**
**State:** Migration scripts live under `ops/scripts/agents/`; run logs and manifests stored with timestamps in `ops/backfill/agents/`. **|**
**Failures & handling:** Backfill failures trigger rollback and incident tracking. **|**
**Observability:** Backfill dashboards, ops JSONL entries (`ops_agents_backfill.jsonl`), and post-run validation harness. **|**
**Breadcrumbs:** Backfill tooling `ops/scripts/agents/backfill_manifests.py`, validation tests `tests/agents/test_backfill_validation.py`. **|**
**References:** TDD §6 summary, Ops runbooks `RB-AGENT-BACKFILL`, Settings spec §5.4.

- Define cutover windows and pause new jobs if required.
- Record pre/post metrics (job backlog, QA pass rate) and attach to backfill evidence.
- Ensure manifests re-hash outputs and judgments remain consistent post-backfill.

### 8.5 Operational Workflows (informative)

**Purpose:** Capture day-to-day operational routines for the agent platform. **|**
**Contract:** Workflows cover daily health checks, backlog triage, and QA sampling. **|**
**State:** Daily checklists stored in `ops/runbooks/checklists/agents_daily.md`; backlog reports archived in `ops/reports/agents/backlog/`. **|**
**Failures & handling:** Missing daily checks escalate to on-call; backlog beyond thresholds triggers surge staffing per Ops policy. **|**
**Observability:** Daily metrics dashboard (“Agent Daily Health”), backlog alerting, QA sampling logs. **|**
**Breadcrumbs:** Daily checklist `ops/runbooks/checklists/agents_daily.md`, backlog script `ops/scripts/agents/backlog_report.py`, QA sampling summary `ops/reports/agents/qa_sampling.csv`. **|**
**References:** This document.

- Morning health review covers pipeline activation status, queue depth, shadow divergence, and QA defect trend.
- Backlog triage reassigns concurrency slots to focus on SLA-bound cases.
- Daily QA sampling selects artifacts for manual review, reconciling QA harness findings with QA harness findings.

______________________________________________________________________

## 9) Dependencies (binding)

**Purpose:** Describe upstream/downstream systems LangGraph relies on. **|**
**Contract:** Pipelines depend on Settings activations, Policy Residency catalogs, Guardian judgments, worker cluster capacity, and provider registries; changes to those dependencies follow their specs. **|**
**State:** Shared manifests, event streams (`agents.pipeline.activation`, `guardian.judgment.*`), and residency annotations link outputs to dependencies. **|**
**Failures & handling:** Dependency drift (Settings failure, residency block, provider outage) triggers the respective RB-* runbook plus RB-AGENT-ACTIVATION before resuming pipelines. **|**
**Observability:** Dependency dashboards (Settings health, residency waiver boards, provider parity) appear alongside agent dashboards. **|**
**Breadcrumbs:** Settings spec §7, Policy Residency spec, Guardian spec, Worker cluster spec, Speech/LLM Registry specs. **|**
**References:** TDD §§5–7, Ops runbooks RB-RES-BLOCK/RB-LLM-003.

______________________________________________________________________

## 10) References (informative)

- TDD §5 Automation & Agent Pipelines
- Platform Runtime §3 (API contracts & activation)
- Guardian Specification §5–§8
- Policy Residency & OPA Policy Plane specifications
- Ops runbooks RB-AGENT-*, RB-RES-BLOCK, RB-LLM-003

______________________________________________________________________

## Appendix A – Agent schemas & error taxonomy (binding)

**Purpose:** Provide typed schema examples and canonical error codes for agent outputs. **|**
**Contract:** Schemas must remain in sync with implementation; error codes are authoritative and map to failure classes in §5. **|**
**State:** Pydantic models live in `packages/core/agents/schemas.py`; schema snapshots export to `spec/schemas/agents/*.schema.json`; lane validators and QA harnesses use these schemas for runtime validation. **|**
**Failures & handling:** Schema drift fails CI; unknown error codes block merges via lint; manifests lacking schema versions trigger `E_INTEGRITY_MISMATCH`. **|**
**Observability:** Schema lints in CI, error code coverage dashboards, QA harness logs. **|**
**Breadcrumbs:** Models `packages/core/agents/schemas.py`, schemas `spec/schemas/agents/`, tests `tests/agents/test_schema_consistency.py`. **|**
**References:** Compose spec Appendix B, Analyze spec Appendix A, Platform TDD §6.

### A.1 Analyze agent schema (binding)

- Pydantic models: `packages.core.agents.schemas.analyze` (new module) defines `AnalyzeState`, `AnalyzeLaneResult`, `AnalyzeRevisionDirective`, `SummaryJSON`, `TimelineEvent`, `EntityRecord`, and supporting value objects (`EvidencePointer`, `QuestionnaireFinding`). Classes are frozen dataclasses or `BaseModel` subclasses with `ConfigDict(frozen=True)` to enforce immutability per LangGraph node.
- Exported JSON Schemas (all under `spec/schemas/agents/`):
  - `transcript_v1.schema.json` — TranscriptJSON (segment UUIDs, speakers, hashes, diarisation flag).
  - `analyze_outline_v1.schema.json` — OutlineJSON derived from DOCX/template headings.
  - `analyze_timeline_v1.schema.json` — TimelineJSON with events (`uuid`, timestamps, speaker, text, labels).
  - `analyze_entities_v1.schema.json` — EntitiesJSON with entities and relations (plus evidence pointers).
  - `analyze_issues_v1.schema.json` — IssuesJSON describing issue text, risk level, notes, evidence references.
  - `analyze_gaps_v1.schema.json` — GapsJSON capturing missing information, impact, and follow-up needs.
  - `analyze_flags_v1.schema.json` — FlagsJSON enumerating case flags with severity levels and references.
  - `analyze_alerts_v1.schema.json` — AlertsJSON highlighting priority alerts and escalation metadata.
  - `analyze_summary_v1.schema.json` — SummaryJSON (case metadata summary, executive summary bullets, detailed narrative sections, procedural posture, issues, checklist, supporting quotes).
  - `analyze_staff_report_v1.schema.json` — Staff report metadata capturing markdown path, reviewer, scoring rubric, and questionnaire deltas.
  - `analyze_qa_report_v1.schema.json` — QAReportJSON with completeness/consistency/schema scores and narrative notes.
  - `analyze_lane_result_v1.schema.json` — LaneResult envelope capturing status, emitted artifacts, usage, dirty UUIDs, and evidence references.
  - `analyze_revision_directive_v1.schema.json` — RevisionDirective payload describing `stage_id`, `target_uuid[]`, `failing_checks[]`, `instructions`, `preserve_spans[]`, and `acceptance_criteria[]`.

Span identity (binding):

- Timeline spans: `event_uuid` (from canonical event signature).
- Outline spans: ordered path of `section_uuid` values from root to leaf.
- Entities spans: `entity_uuid` and `relation_uuid` for edges; relations reference existing entity UUIDs.
- Summary spans: `section_anchor` + `entry_uuid` for discrete bullets/paragraphs.
- Determinism requirements: every schema exposes a `uuid` derived from `uuid5(NAMESPACE_ANALYZE, canonical_content)`, plus `schema_version`, `produced_at`, `settings_snapshot_sha`, and `idempotency_key`. Directives must enumerate `preserve_spans[]`; QA rejects directives lacking an explicit protected set.

### A.2 Compose agent schema (binding)

- `compose_section_output_v1.schema.json` — SectionOutput (section identifiers, role, markdown body, linked issues).
- `compose_document_v1.schema.json` — Deliverable container for client, lawyer, or bundle outputs.
- `compose_qa_report_v1.schema.json` — Compose QA report (status, findings, references).
- `compose_manifest_v1.schema.json` — Manifest snapshot linking templates, analyze artifacts, and provider selections.
- `compose_lane_result_v1.schema.json` — LaneResult envelope parallel to Analyze for QA parity.
- `compose_revision_directive_v1.schema.json` — Directive structure aligned with Analyze but scoped to section/paragraph UUIDs.

Span identity (binding):

- Client/Lawyer sections: `section_anchor` + `entry_uuid`.
- Bundle excerpt: `entry_uuid` referencing source summary/issue UUIDs.

### A.3 Additional lane models

- Shared helpers:
  - `event_reference.schema.json` — Canonical reference to timeline events by UUID and timestamp.
  - `issue_reference.schema.json` — Lightweight pointer to Analyze issues for Compose sections and QA findings.
  - `evidence_pointer.schema.json` — Standardised pointer to transcript segments or document excerpts.
  - `idempotency_key.schema.json` — Manifest record of lane-specific idempotency tokens.
  - `prompt_provenance.schema.json` — Recorded for every LLM invocation in per-run metadata.
- QA metrics & usage:
  - `qa_metric.schema.json` — Normalised representation of completeness/consistency/schema scores embedded in Analyze and Compose QA reports.
  - `lane_usage.schema.json` — Token + cost usage envelopes keyed by `idempotency_key` for FinOps + policy accounting.

______________________________________________________________________

## Appendix B – Determinism & Canonicalization (binding)

**Purpose:** Define canonical forms used for UUID derivation, idempotency keys, and equality checks so retries and revisions remain deterministic. **|**
**Contract:** Every artifact records its canonical content hash; UUIDv5 derivations use the same canonical form end-to-end. **|**
**Scope:** Canonicalization applies only to LangGraph agent inputs/outputs.

### B.1 Common normalization

- Unicode: NFKC normalize; lowercase (casefold); strip leading/trailing whitespace; collapse internal whitespace to single spaces.
- Punctuation: normalize curly quotes/dashes to ASCII; remove zero-width characters; trim trailing punctuation where not semantically relevant.
- JSON: sort object keys lexicographically; arrays sorted when order is not semantically relevant (explicitly noted per schema); numbers rendered without locale formatting.

### B.2 Artifact-specific canonical forms

- Timeline event signature: concat of `{start_ts_rounded_s}|{end_ts_rounded_s}|{speaker_id}|{normalized_text}|{evidence_hash}`; evidence set sorted by pointer path.
- Entity signature: `{normalized_name_lemma}|{entity_type}|{sorted_aliases}|{evidence_hash}` with aliases dedup + sorted; evidence pointers sorted.
- Summary section signature: `{section_anchor}|{normalized_body}|{sorted_citations}` where citations are normalized and sorted.

### B.3 UUID and idempotency derivation

- UUID: `uuid5(NAMESPACE, canonical_signature)` where `NAMESPACE` is fixed per artifact class.
- Idempotency: `sha256(job_id || pipeline_id || node_id || graph_version || input_hash)` where `input_hash` is computed from the canonical form.

### B.4 Preservation & merge checks

- Preserved spans must remain byte-identical under canonical form; merges verify equality before accepting revisions.
- Dirty set = UUIDs found in `revision.target_uuid[]` minus `preserve_spans[]`; only the dirty set is replaced during revision merges.
- QA metrics:
  - `qa_metric.schema.json` — Normalised representation of completeness/consistency/schema scores embedded in Analyze and Compose QA reports.

### A.4 Error codes

- `E_TRANSIENT_PROVIDER` → class `TRANSIENT`
- `E_POLICY_FORBIDDEN` → class `POLICY`
- `E_INPUT_INVALID` → class `INPUT`
- `E_INTEGRITY_MISMATCH` → class `INTEGRITY`
- `E_CONFLICT` → class `CONCURRENCY`

Ops JSON includes `{code, class, message, attempt, final}` for every failure; UI shows human-friendly error strings mapped from this table.

______________________________________________________________________

## Appendix C – Settings & activation keys (informative)

**Purpose:** Reference the Settings keys and activation artifacts that control LangGraph agents. **|**
**Contract:** Keys remain authoritative; additions require spec update and Settings validators. **|**
**State:** Keys live in `settings/schema/agents.yaml`; activations recorded in `ops/settings_activation/agents/*.json`; manifests capture snapshot hashes. **|**
**Failures & handling:** Activation drift triggers lint failures; missing keys block promotion. **|**
**Observability:** Settings activation dashboards, lint scripts, manual reviewer checklist (`docs/CONTRIBUTING-docs.md`). **|**
**Breadcrumbs:** Settings schema `config/settings/agents.py`, activation validators `apps/platform/settings/validators/agents.py`, tests `tests/settings/test_agents_keys.py`. **|**
**References:** Settings spec §5, TDD §6 summary, Ops runbooks `RB-SETTINGS-ACTIVATION`.

| Key | Scope | Description |
| --- | --- | --- |
| `agents.pipeline.definitions[]` | SYSTEM | Canonical pipeline catalog (see §3.2). |
| `agents.pipeline.assignments[]` | SYSTEM\|ORG | Maps org/case to pipeline + version. |
| `agents.pipeline.overrides[]` | SYSTEM\|ORG | Lane enablement, template overrides within validator bounds. |
| `agents.tools.catalog[]` | SYSTEM | Tool registry entries with schema + binding metadata. |
| `agents.tools.assignments[]` | SYSTEM\|ORG | Tool availability per org/case. |
| `assistant.*` | SYSTEM\|ORG | Conversational pipeline configuration. |
| `agents.runtime.langgraph_enabled` | SYSTEM | Feature flag gating LangGraph runtime. |

______________________________________________________________________

## Appendix D – Roadmap & Open Questions (informative)

- LangGraph adoption guardrails: maintain linear fallback until shadow mode and QA metrics remain stable for three consecutive releases; GraphRunner feature flag stays available for emergency rollback.
- Timeline/relationship agents: graduate from informative to binding once schemas finalise and QA thresholds are met.
- Generative QA evaluators: expand QA harness to include automated fact checks; pending ADR.
- Human-in-the-loop telemetry: integrate Manual/Agent edit signals directly into manifests to trigger automatic QA reruns.
