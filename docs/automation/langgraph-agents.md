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
      table {
        font-size: 8.5pt;
      }
      table td,
      table th {
        font-size: inherit;
        word-break: break-word;
        overflow-wrap: anywhere;
      }
      figure svg text,
      figure svg tspan {
        fill: #111 !important;
      }
      figure svg text {
        font-family: "DejaVu Sans", "Trebuchet MS", Arial, sans-serif !important;
      }
      figure.full-width-diagram img {
        width: 100%;
        height: auto;
        display: block;
      }
    </style>
  - <header class="page-header">uDocket — LangGraph Agent Orchestration Specification <br>
    Canonical pipelines for Transcribe, Analyze, Compose, Timeline, and Relationship agents</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-28 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
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
- **Maintenance:** Run `python -m doc_tools.manage_docs --lint docs/automation/langgraph-agents.md` plus targeted lints (`python -m doc_tools.check_links --strict`) before shipping agent changes. Graph modifications require LangGraph contract tests (§3.2) and QA harness replays (§6.1) to pass in CI.
- **Change protocol:** Any change that alters agent outputs, pipeline structure, or QA gating must update this spec, cite relevant ADRs, and include LangGraph acceptance test results in the PR description. Guardian/Security approvals are mandatory for policy or residency-impacting edits.
- **References:** TDD §6 summary, Settings Registry spec §5, LLM Registry spec §2, Worker Cluster spec §3, Ops Runbooks `RB-AGENT-\*`, QA harness documentation in tests README.
- **Contacts:** Applied AI Engineering (primary owners), Platform Architecture (co-owners), Operations Eng (shadow mode), Guardian (safety), `#langgraph-agents` Slack, on-call alias `agents-oncall@`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Define the canonical LangGraph-based agent pipelines, contracts, and guardrails that transform transcripts into downstream analyses and deliverables. **|**
**Contract:** This spec owns the agent interface, graph configuration model, QA gates, and operational controls that keep agents deterministic, observable, and compliant. Implementations must adhere to the shared manifests, artifact naming conventions, and error taxonomy defined here. **|**
**State:** Pipelines, tool catalogs, and assignments are stored in Settings (`agents.pipeline.*`, `agents.tools.*`), with manifests persisted per job under `storage/media/tenants/<ORG_ID>/cases/<case>/analysis|docs|ops`. Celery job state, audit events, envelope hashes, and metrics tie back to these pipelines. **|**
**Failures & handling:** Graph activation rejects invalid schemas; runtime failures follow the taxonomy in §5; Guardian enforces residency/policy gates; Shadow mode (§8.2) and QA harnesses catch regressions before promotion. **|**
**Observability:** Metrics dashboards (“Agent Pipelines – Activation”, “LangGraph QA”, “Agent Shadow Runs”), ops JSONL streams (`ops_transcription.jsonl`, `ops_summary.jsonl`, `ops_compose.jsonl`), and manifests record pipeline versions, tool usage, and retry history. **|**
**Breadcrumbs:** Orchestration runtime `packages/udocket_core/agents/graph_runner.py`, pipeline catalog `packages/udocket_core/agents/pipeline_catalog.py`, Celery tasks `apps/platform/operations/tasks/agents.py`, QA harness `tests/agents/test_langgraph_acceptance.py`, Settings integration `apps/platform/settings/agents_pipeline.py`. **|**
**References:** TDD §6 (summary), Settings spec §5.4, Worker Cluster spec §3.3, Guardian spec §2.3, LLM Registry spec §2.2, Ops Runbooks `RB-AGENT-SHADOW`, `RB-JOB-WATCHDOG`.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Enumerate each agent’s charter, lane responsibilities, and artifact ownership. **|**
**Contract:** Agents must implement the shared `AgentRunner` interface, persist deterministic outputs, honour Guardian judgments, and expose audit-friendly manifests for every job. **|**
**State:** Each agent manages job manifests, manifests for derived artifacts, envelope hashes, QA logs, and Ops JSON per run. **|**
**Failures & handling:** Runtime failures map to the taxonomy in §5; Guardian quarantine or waiver flows apply when policy gates fail; Worker Cluster retries jobs according to agent-specific rules. **|**
**Observability:** Metrics `agent_job_duration_seconds{agent=}`, `agent_retry_total`, QA issue density, and pipeline activation dashboards track compliance; SSE updates keep UI state in sync. **|**
**Breadcrumbs:** Transcription `packages/udocket_core/agents/transcribe_lib.py`, Analyze `packages/udocket_core/agents/analyze_lib.py` + stages `packages/udocket_core/agents/analyze/stages/`, Compose `packages/udocket_core/agents/compose_lib.py` + orchestrator `packages/udocket_core/agents/compose/orchestrator.py`, Celery wrappers `apps/platform/operations/tasks/agents.py`, manifests `packages/udocket_core/agents/manifests.py`. **|**
**References:** TDD §6 summary, Guardian spec §2–§3, Worker Cluster spec §3, Ops runbooks `RB-AGENT-TIMEOUT`, `RB-AGENT-RETRY`.

### 2.1 Transcription agent (binding) {#21-transcription-agent}

- Modes: streaming (WebSocket) and batch (provider-hosted jobs). Diarisation is enabled for batch jobs only.
- Inputs: local filesystem path or HTTPS SAS URL, language, region (any value permitted by Settings allowlists), diarisation flag (batch only), optional transcription overrides (`transcription.*`).
- Outputs: transcript text `storage/media/tenants/<ORG_ID>/cases/<case>/transcript/<job_id>__transcript.txt`, structured transcript JSON `transcript/<job_id>__transcript_v1.json` (segments with deterministic UUIDs, speaker roster, hashes), per-run metadata JSON `ops/<job_id>__transcription_log.json`, human-readable log, and audit append `ops/ops_transcription.jsonl`.
- Header & manifest metadata: case/job identifiers, source hashes, language, region, duration, diarisation mode, settings snapshot SHA, provider version, conversion fingerprints (e.g., ffmpeg SHA-256).
- Retry semantics: streaming jobs resume from buffered offsets; batch jobs poll provider status and retry failed uploads with exponential backoff capped by settings budgets. Provider fallback is disabled unless Settings explicitly assigns alternates.
- Capability negotiation: `TranscriptionCapabilityMap` validates language/diarisation support before dispatch; unsupported combinations raise `E_INPUT_INVALID`.
- Cancellation: best-effort cancellation propagates through provider APIs; manifests mark `cancel_requested` and retain partial progress for audit.

### 2.2 Analyze agent (binding) {#22-analyze-agent}

- Inputs: transcript JSON (or transcript text fallback), intake/questionnaire artifacts, DOCX outline template headers, case metadata, Settings overrides for prompts, stage concurrency, token budgets, and idempotency keys.
- Parallel lanes: outline-from-template, timeline (events), entities (and relations), issues, gaps, flags/alerts. Lanes run concurrently with deterministic UUID generation (`uuid5` signatures) and schema enforcement.
- Outputs: discrete artifacts under `analysis/` — `outline_v1.json`, `timeline_v1.json`, `entities_v1.json`, `issues_v1.json`, `gaps_v1.json`, `flags_v1.json`, `alerts_v1.json`, `summary_v1.json`, `staff_report_v1.md`, `qa_report_v1.json` — plus per-run metadata JSON and `ops/ops_summary.jsonl` audit entries.
- Summary lane: consumes all upstream JSON artifacts (not Analyze Markdown) to generate canonical `summary_v1.json`; Compose reads this JSON directly.
- QA gating: every lane validates against JSON Schema snapshots (exported to `spec/schemas/agents/`). QA stage aggregates coverage metrics into `qa_report_v1.json` and blocks finalize on schema failures or questionnaire gaps.
- Retry & cancellation: lane retries follow transient budgets; GraphRunner cancellation halts active nodes and preserves checkpoint digests so resumed jobs avoid duplicate work.

### 2.3 Compose agent (binding) {#23-compose-agent}

- Inputs: Analyze summary JSON, timeline/entities/issues/gaps/flags/alerts artifacts, intake data, deliverable templates (DOCX/Markdown), organization policies (`compose.policy.*`, `guardian.policy.*`), and Settings concurrency budgets.
- Lanes: parallel client and lawyer deliverable pipelines (draft → editor passes → lane QA), optional bundle excerpt, followed by cross-lane QA review and final packaging. Lanes share shared context (summary JSON + structured artifacts) but render voice-specific outputs.
- Outputs: client and lawyer deliverables (`docs/<job_id>__compose_client_v1.md|.docx`, `docs/<job_id>__compose_lawyer_v1.md|.docx`), bundle excerpt Markdown (if enabled), compose staff report (`docs/<job_id>__compose_staff_report_v1.md`), compose QA report (`docs/<job_id>__compose_qa_report_v1.md` / `.json`), per-run metadata JSON, and `ops/ops_compose.jsonl` audit lines.
- Safety & policy: lane validators enforce forbidden patterns, required sections, link limits, and jurisdictional voice guidance. Guardian refuses promotion without QA PASS and documented policy compliance.
- Retry & cancellation: SectionWriter nodes retry within configured budgets; QA issues capture severity and references. Cancellation stops graph execution, leaves partial artifacts versioned `_v{n}`, and records state in manifests.

<figure class="full-width-diagram">
  <img class="diagram" src="../../build/diagrams/automation/langgraph-agents/analyze-pipeline-v2.svg" alt="Transcribe, Analyze, and Compose pipeline flow">
  <figcaption style="font-size: 0.9em; color: #555;">Transcribe, Analyze, and Compose pipeline flow</figcaption>
</figure>

### 2.4 Timeline & relationship agents (roadmap, informative) {#24-timeline-relationship-agents}

- Roadmap agents will consume Analyze timeline/events and entities JSON to produce richer chronological visualisations and relationship graphs with deterministic UUID lineage.
- Responsibilities: maintain speaker attribution, event windows, entity linkage, and evidence references; align outputs with Guardian gating and Settings activation before UI exposure.
- Dependencies: reuse LangGraph pipelines with dedicated nodes for diarisation merge, event normalisation, entity clustering, and QA scoring.
- Current status: prototypes remain in shadow mode until QA metrics meet §6 targets; binding specification will follow once promoted.

______________________________________________________________________

## 3) API Contract {#3-api-contract}

**Purpose:** Govern the configurable LangGraph pipelines, tool catalog, concurrency rules, and agent interfaces that keep jobs deterministic, auditable, and region-aware. **|**
**Contract:** Pipelines are defined in Settings (`agents.pipeline.*`), tools in `agents.tools.*`, and assistant graphs follow the same activation rules. GraphRunner enforces schema hashes, stage ordering, deterministic manifests, and single-writer finalize semantics. **|**
**State:** Activation metadata captures `graph_version`, `graph_schema_sha256`, `settings_snapshot_sha256`, lane concurrency budgets, and idempotency keys; compiled graphs are cached for reuse alongside per-job checkpoints. Tool registry cache stores schema-validated bindings. **|**
**Failures & handling:** Invalid activations fail closed with actionable errors (`E_INPUT_INVALID`, `E_SCHEMA_MISMATCH`); runtime mismatches raise `E_INTEGRITY_MISMATCH`; missing tools block activation. **|**
**Observability:** Activation dashboards, CI contract tests, tool registry validation logs, prompts provenance, and ops manifests capture pipeline changes and drifting configurations. **|**
**Breadcrumbs:** Settings integration `apps/platform/settings/agents_pipeline.py`, pipeline catalog `packages/udocket_core/agents/pipeline_catalog.py`, LangGraph orchestrator `packages/udocket_core/agents/langgraph_orchestrator.py`, analyze stages `packages/udocket_core/agents/analyze/stages/`, compose orchestrator `packages/udocket_core/agents/compose/orchestrator.py`, activation tests `tests/agents/test_pipeline_catalog.py`. **|**
**References:** TDD §6 summary, Settings spec §5.4, LLM Registry spec §2, Worker Cluster spec §3, Ops runbooks `RB-SETTINGS-ACTIVATION`, `RB-AGENT-ACTIVATION`.

<figure class="full-width-diagram">
  <img class="diagram" src="../../build/diagrams/automation/langgraph-agents/agent-orchestration-classes-v1.svg" alt="Agent orchestration classes">
  <figcaption style="font-size: 0.9em; color: #555;">Agent orchestration classes</figcaption>
</figure>

### 3.1 External Interfaces (binding)

- Celery task wrappers under `apps/platform/operations/tasks/agents.py` expose LangGraph pipelines to Operations and publish progress/events over SSE to UI clients. Task payloads carry manifest references, idempotency keys, and settings snapshot hashes for replay.
- Settings activation endpoints (`agents.pipeline.*`, `agents.tools.*`, `assistant.*`) gate configuration changes; they validate JSON Schemas, concurrency budgets, region allowlists, and provider credentials before promotion.
- Guardian, Worker Cluster, and Web App integrations consume structured status payloads (`job.accepted|running|completed`), QA summaries, and artifact pointers to drive UI visibility and safety gating.
- Manual/Agent edit tooling uses `ops/agent_edit` APIs that accept deterministic manifests, enforce reviewer approvals, and produce new artifact versions before promotion.

### 3.2 Internal Interfaces (binding)

- Pipeline catalog, tool registry, and LangGraph orchestrator form the internal contract that manages stage ordering, lane concurrency, retries, and checkpoint management.
- Analyze stage implementations (`packages/udocket_core/agents/analyze/stages/*`) expose typed callables that operate on transcript JSON, intake data, and lane-specific context, returning structured payloads that comply with exported JSON Schemas.
- Compose orchestrator merges shared context (summary JSON + analysis artifacts) into role-specific lanes, ensuring that only finalize nodes write deliverables.

- `agents.pipeline.definitions[]` enumerates each pipeline with `{pipeline_id, graph_version, graph_schema_sha256, runner, stages[]}`; defaults populate from `config/*.json`.
- Stage metadata: `{stage_id, langgraph_node_id, llm_profile_id, prompt_template_id, tool_ids[], enabled, retry_budget, cost_ceiling, depends_on[]}`. Structural edits (`stages[]` reorder/insert/delete) require SYSTEM scope.
- Assignments & overrides: `agents.pipeline.assignments[]` maps org/case to pipelines; `agents.pipeline.overrides[]` permits tightening budgets, toggling stage enablement, or swapping templates within validator bounds.
- Activation safety: contract tests validate schema hashes, stage wiring, and GraphRunner compatibility before promotion. Activations follow blue/green rollout; manifests capture which orgs completed cutover.
- Versioning: stage definitions are additive; prior versions remain callable for queued jobs & replays until Guardian signs off; deletion blocked until archival manifests exist.

### 3.3 API Error Codes (binding) {#33-api-error-codes}

**Purpose:** Enumerate LangGraph agent `ApiError.code` values so service clients, worker orchestration, and UI flows respond deterministically. **|**
**Contract:** Agent launch and management endpoints reuse the platform catalog in [`Platform Runtime §3.3`](../platform/runtime.md#33-api-error-codes); the scenarios below capture how those codes manifest for LangGraph pipelines. **|**
**State:** Responses originate from `apps/platform/agents/views.py`, pipeline runtime `packages/udocket_core/agents/runtime.py`, and Guardian adapters; schema parity enforced by `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and `tests/platform/agents/test_agent_errors.py`; runtime emissions trigger `agent_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards “Agents – Launch API” and “Agents – Guardian Blocks” chart `agent_api_error_total{code}`, `agent_guardian_block_total`; synthetic launches follow the pause/resume flows. **|**
**Breadcrumbs:** Controllers `apps/platform/agents/views.py`, runtime orchestrator `packages/udocket_core/agents/runtime.py`, Guardian bridge `packages/udocket_core/agents/guardian.py`, tests `tests/platform/agents/test_launch_api.py`. **|**
**References:** Platform Runtime §3.3, Settings spec §5.4, Worker Cluster spec §3.4, Guardian spec §2.3, Ops runbooks `RB-AGENT-SHADOW`, `RB-JOB-WATCHDOG`.

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

### 3.4 LangGraph Tool Registry & Onboarding (binding)

- Catalog stored in `agents.tools.catalog[]` with each entry describing `{tool_id, description, input_schema, output_schema, binding, timeout_seconds, cost_profile_id, residency_classification, pii_classification, idempotent?, tool_idempotency_key}`.
- Validators ensure JSON Schema compliance, unique IDs, deterministic idempotency keys, and safe retry budgets. Non-idempotent tools require `max_attempts=1`.
- Tool bindings map to Python adapters, gRPC services, or HTTP endpoints resolved via `ToolFactory`. Guardian-approved residency + PII metadata recorded in catalog.
- Activation runs schema validation, dry-run LangGraph graphs using the tool, and telemetry registration checks (`tool_invocation_total`, `tool_cost_estimate_total`).
- Audit: tool changes recorded in ops manifests with `{tool_id, version, schema_sha256}`, linked to ADR or waiver when policy/residency impacted.

### 3.5 Conversational Assistant Pipelines (binding)

- Assistant pipelines (`assistant.staff`, `assistant.client`, future variants) share the same activation flow as task agents. Nodes include retrieval, guardrails, responder lanes, moderation, and post-processing writers.
- Settings overrides: `assistant.retrieval.sources[]`, `assistant.voice.*`, `assistant.moderation.*` allow org-level tuning within validator limits; lane structure changes remain SYSTEM-only.
- QA: conversational replay harness replays standardized transcripts and portal conversations; acceptance tests assert retrieval scope, guardrail triggers, and moderation escalations.
- Safety: assistant lanes inherit Guardian gating (no unreviewed deliverables), and replays ensure disclaimers + audit logs cover instructions/responses.

### 3.6 LangGraph Runtime Contracts (normative)

- GraphRunner compiles LangGraph graphs to Python callables, stores compiled graphs keyed by `{pipeline_id, graph_version}`, and enforces deterministic node execution with replayable checkpoints.
- Nodes record checkpoint digests (input + output hashes); retries compare digests to avoid duplicate work; concurrency locks ensure stage-level OCC.
- Deterministic identity: nodes/stages generate reproducible `uuid5` identifiers from `{pipeline_id, node_id, graph_version}`; manifests reference these IDs for audit alignment.
- Adoption guardrails: fallback plan keeps linear pipelines available; feature toggles `agents.runtime.langgraph_enabled` guard release; shadow mode (§8.2) and acceptance tests required before toggling default.

______________________________________________________________________

## 4) State Management {#4-state-management}

**Purpose:** Describe how agents persist manifests, artifacts, and lineage to provide forensic traceability. **|**
**Contract:** Every agent job produces manifests capturing input hashes, settings snapshot, pipeline + graph versions, tool usage, Guardian/Signer dependencies, and resulting artifact paths. **|**
**State:** Manifests stored under `storage/media/tenants/<ORG_ID>/cases/<case>/ops/<job_id>__<agent>_manifest.json`; audit JSONL streams append to `ops/ops_<agent>.jsonl`; QA logs and acceptance verdicts live alongside artifacts. **|**
**Failures & handling:** Missing or corrupt manifests trigger `E_INTEGRITY_MISMATCH` and quarantine outputs; pipeline activation blocks if manifests fail schema validation. **|**
**Observability:** Manifests feed lineage diagrams, QA dashboards, and FinOps metrics. `python -m doc_tools.manage_docs --lint --check-manifests` ensures schema parity during CI. **|**
**Breadcrumbs:** Manifest models `packages/udocket_core/agents/manifests.py`, ops logging `packages/udocket_core/agents/logging.py`, lineage tooling `packages/udocket_core/agents/lineage.py`, QA harness `tests/agents/test_manifest_compliance.py`. **|**
**References:** TDD §5.2, §6 summary, Compose spec §4, Guardian spec §2.4, Ops runbooks `RB-LINEAGE-BACKFILL`.

- Filesystem layout: transcripts (text + JSON) under `transcript/`; analysis artifacts (`outline_v1.json`, `timeline_v1.json`, `entities_v1.json`, `issues_v1.json`, `gaps_v1.json`, `flags_v1.json`, `alerts_v1.json`, `summary_v1.json`, `staff_report_v1.md`, `qa_report_v1.json`) under `analysis/`; compose deliverables and QA/staff artifacts under `docs/`; ops metadata/logs under `ops/`.
- Naming convention: `<job_id>__<artifact>[_v{n}]<extension>` ensures sorted history; manual or agent edits create new versions requiring reviewer approval.
- Hashing: manifests include SHA-256 of outputs, pipeline manifest version, tool versions, provider/model versions, compute/storage regions, Guardian judgment IDs, and settings snapshot hash.
- Lineage: manifests link `source_transcript`, `case_id`, `job_id`, upstream artifact IDs, template IDs, and Guardian judgment reference. Compose manifest references analyze outputs by UUID to preserve traceability.
- Envelope schema: `spec/schemas/llm_envelope.schema.json` defines separation between `instructions[]`, `source_content[]`, `system_policies[]`, `safety_tags[]`; Compose/Analyze nodes validate compliance before invoking models.

______________________________________________________________________

## 5) Failure Modes

**Purpose:** Capture the failure taxonomy, retry behaviour, and mitigation strategies that keep agent pipelines reliable. **|**
**Contract:** Agents classify failures into deterministic categories (`TRANSIENT`, `POLICY`, `INPUT`, `INTEGRITY`, `CONCURRENCY`, `REGION_POLICY`) and respond with defined retries or escalations. Worker Cluster respects per-agent retry budgets and backoff strategies. **|**
**State:** Ops metadata JSON records `{code, class, attempt, final, retry_after}`; manifests flag partial outputs; QA logs capture verification failures. **|**
**Failures & handling:** Transient provider errors retry with exponential backoff; policy violations quarantine; input errors surface to UI; integrity mismatches halt and trigger audit; concurrency conflicts short-retry before manual intervention; residency violations raise `E_REGION_POLICY`. **|**
**Observability:** Metrics `agent_retry_total{class=}`, `agent_job_duration_seconds{outcome=}`, synthetic jobs, and Guardian/Settings alerts monitor reliability. **|**
**Breadcrumbs:** Failure taxonomy `packages/udocket_core/agents/errors.py`, retry logic `packages/udocket_core/agents/retry.py`, Worker Cluster job controller `apps/platform/operations/job_runner.py`, tests `tests/agents/test_failure_modes.py`. **|**
**References:** TDD §6 summary, Worker Cluster spec §3.4, Guardian spec §2.3, Ops runbooks `RB-AGENT-RETRY`, `RB-AGENT-TIMEOUT`.

- Cancellation semantics: GraphRunner issues cancellation tokens to active nodes; nodes honour cooperative cancellation and persist progress for partial outputs.
- Resume rules: resumed jobs verify checkpoint digests, ensuring idempotent behaviour; GraphRunner refuses resume if pipeline version drifts beyond allowed migration window (§8.1).
- Provider failure mitigations: fallback providers require waiver and explicit assignment; backlog watchers page after configurable SLO breaches.
- QA failure handling: QA lane `E_POLICY_FORBIDDEN` stops promotion; staff reviewers receive ops log pointers and Guardian verdict.
- Region enforcement: settings `regions.allowlist.compute/storage/vector` cross-checked before job dispatch; region mismatch triggers `E_REGION_POLICY`.

______________________________________________________________________

## 6) Observability {#6-observability}

**Purpose:** Define the metrics, QA harnesses, and continuous evaluation commitments for LangGraph agents. **|**
**Contract:** All pipelines must emit metrics for job duration, retries, QA issue density, WER (transcription), review deltas (Analyze/Compose), and FinOps cost budgets. QA harnesses replay golden datasets per release. **|**
**State:** Metrics exported via Prometheus/Grafana; QA harness outputs stored as artifacts (`analysis/<job_id>__qa_report.json`), QA issue logs appended to ops JSON. Quality review summaries archived as `QUALITY_KPI_REPORT` artifacts. **|**
**Failures & handling:** Metric regressions trigger runbooks; QA harness failures block release; FinOps anomalies create decision-log entries (`DECISION_LOG_AGENTS`). **|**
**Observability:** Dashboards “Agent Pipelines – Activation”, “Agent Shadow Runs”, “QA Acceptance”, FinOps monitors; synthetic jobs generate consistent load. **|**
**Breadcrumbs:** QA harness `tests/agents/test_langgraph_acceptance.py`, WER evaluation `tests/agents/test_transcription_quality.py`, Grafana dashboards `infra/grafana/agents_quality.json`, FinOps monitors `ops/finops/agents_cost_dashboard.json`. **|**
**References:** TDD §6 summary, Guardian spec §2.3, Compose spec §6, Ops runbooks `RB-AGENT-QA`, `RB-FINOPS-LANGGRAPH`.

- **Transcription accuracy:** WER ≤ 8 % on on-demand, ≤ 6 % on batch measured quarterly; metrics `transcription_wer_pct{mode,language}`; regressions ≥ 2 % trigger incident review.
- **Guardian effectiveness:** False-negative ≤ 0.5 % per quarter, false-positive ≤ 5 %; metrics `guardian_quarantine_false_positive_total`, `guardian_judgment_total`.
- **Review delta:** Reviewer change rate ≤ 15 % of sections; QA issue density ≤ 0.2 blocking defects per artifact; tracked via QA logs.
- **FinOps blend:** Monitor tokens-per-approved artifact and rejection counts to ensure budget adherence without quality degradation.
- **Shadow acceptance:** Shadow runs must match production outputs within tolerance windows (§8.2) before promoting new pipelines.

### 6.1 SLOs & Targets (binding)

**Purpose:** Capture availability, quality, latency, and cost expectations for LangGraph pipelines. **|**
**Contract:** Agent run completion, QA acceptance, lane latency, and token budgets must meet the thresholds below before promotions proceed. **|**
**State:** Metrics `agent_job_completion_ratio`, `agent_lane_duration_seconds`, `agent_queue_latency_seconds`, `agent_token_budget_violation_total`; dashboards “Agent Pipelines – Activation”, “Agent QA Acceptance”, FinOps monitors `ops/finops/agents_cost_dashboard.json`. **|**
**Failures & handling:** Breaches invoke RB-AGENT-PIPELINE, RB-AGENT-QA, or RB-FINOPS-LANGGRAPH before enabling new activations. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, QA harness reports, and shadow run comparisons provide evidence. **|**
**Breadcrumbs:** QA harness `tests/agents/test_langgraph_acceptance.py`, telemetry `packages/udocket_core/agents/logging.py`, runbooks `docs/ops/runbooks/agents/*.md`. **|**
**References:** TDD §6, Worker Cluster spec §3.5, Guardian spec §7.

- **Pipeline availability:** ≥99.5% of LangGraph runs complete without manual retry, measured via `agent_job_completion_ratio`; breaches trigger RB-AGENT-PIPELINE before promotions proceed.
- **QA acceptance:** Automated QA issue density stays ≤0.2 blocking defects per artifact; exceedances invoke RB-AGENT-QA and pause affected pipelines.
- **Lane latency:** Analyze lane P95 ≤ 15 minutes, Compose lane P95 ≤ 45 minutes, Transcribe backlog clearance P95 ≤ 5 minutes (`agent_lane_duration_seconds{lane}` / `agent_queue_latency_seconds`). Breaches require corrective action before enabling new activations.
- **FinOps guard:** `agent_token_budget_violation_total` remains zero; if triggered, RB-FINOPS-LANGGRAPH engages and approvals halt until the budget recovers.

______________________________________________________________________

## 7) Security & Compliance

**Purpose:** Ensure LangGraph agents honour residency, privacy, and policy constraints enforced across the platform. **|**
**Contract:** Agents execute only within organization-approved regions, enforce HIPAA/SPI policies, respect Guardian verdicts, and produce audit-ready manifests linking to waivers when exceptions granted. **|**
**State:** Residency allowlists stored in Settings, manifests record residency decisions, Guardian judgment IDs, waiver references, and policy enforcement metadata. **|**
**Failures & handling:** Residency violations block execution (`E_REGION_POLICY`); policy violations escalate to Guardian; HIPAA/SPI detection mismatch triggers quarantine and manual review per Guardian runbooks. **|**
**Observability:** Residency enforcement metrics, Guardian dashboards, audit logs, and Settings activation lint rules catch drifts. **|**
**Breadcrumbs:** Settings residency validators `packages/udocket_core/settings/validators/regions.py`, Guardian manifests `packages/udocket_core/guardian/store.py`, HIPAA policy enforcement `packages/udocket_core/agents/policies.py`, tests `tests/agents/test_residency_enforcement.py`. **|**
**References:** TDD §3.8, Guardian spec §2–§3, Settings spec §4, Ops runbooks `RB-RESIDENCY-ENFORCEMENT`, `RB-HIPAA-MODE`.

- HIPAA mode: Settings `privacy.hipaa.enabled` forces masked prompts and Guardian PHI quarantine; Compose/Analyze ensure detokenisation occurs only within Compose lane with vault controls.
- SPI enforcement: prompts & outputs redact SPI categories; manifests track classification; QA logs include evidence of redaction.
- Policy labels: Compose/Analyze outputs labelled `(binding)/(normative)/(informative)` per policy; Vale rules enforce headings and terminology (§8.3).
- Audit traceability: manifests include Guardian judgement ID, Settings snapshot, pipeline version, template versions, TSA/Signer dependencies when applicable.

______________________________________________________________________

## 8) Operational Notes

**Purpose:** Document activation, migration, and incident management workflows that keep agent pipelines reliable in production. **|**
**Contract:** Pipeline activations follow blue/green rollouts with automatic rollback on health regressions; shadow mode validation required prior to enabling new pipelines or providers. **|**
**State:** Activation manifests record rollout state per org; shadow run results stored under `ops/shadow_runs/<pipeline>/<timestamp>.json`; migration plans track pipeline version transitions. **|**
**Failures & handling:** Activation failure triggers rollback to previous pipeline; shadow divergences raise alerts; migration blockers escalate to Architecture + Guardian for remediation. **|**
**Observability:** Dashboards `Agent Pipelines – Activation`, `Agent Shadow Runs`, Celery queues, and ops manifests expose rollout status. **|**
**Breadcrumbs:** Activation scripts `apps/platform/settings/agents_pipeline.py`, shadow runner `apps/platform/operations/shadow.py`, migration tooling `packages/udocket_core/agents/migrations.py`, tests `tests/agents/test_shadow_mode.py`. **|**
**References:** TDD §6 summary, Ops runbooks `RB-AGENT-ACTIVATION`, `RB-AGENT-SHADOW`, Worker Cluster spec §3.5.

### 8.1 Operational Posture (binding)

**Purpose:** Capture staffing, maintenance windows, and readiness expectations for LangGraph operations. **|**
**Contract:** Applied AI Engineering owns primary on-call with Platform Operations as secondary; rotations guarantee <15 minute acknowledgement and 24/7 coverage for production clusters. **|**
**State:** Rosters reside in PagerDuty (`agents-oncall`), maintenance calendars under `ops/calendars/langgraph.yml`, and readiness checklists in `ops/runbooks/checklists/agents_daily.md`. **|**
**Failures & handling:** Staffing gaps or expired readiness checks trigger `RB-AGENT-POSTURE` escalation to Operations leadership; pre-planned maintenance requires dual approval via change management tickets. **|**
**Observability:** Staffing dashboards track pager load, acknowledgement latency, and open readiness tasks; weekly posture review notes live in `ops/reports/agents/posture/*.md`. **|**
**Breadcrumbs:** PagerDuty service `agents-primary`, escalation policy `ops/escalations/agents.json`, readiness checklist `ops/runbooks/checklists/agents_daily.md`, staffing SOP `ops/runbooks/agents/agent_posture.md`. **|**
**References:** TDD §12.2 (operations governance), Worker Cluster spec §3.5, Ops runbooks `RB-AGENT-POSTURE`, `RB-AGENT-TIMEOUT`.

- Primary on-call: Applied AI Engineering engineers rotate weekly; Platform Operations carries shadow rotation to absorb surge or responder fatigue.
- Maintenance windows: weekly Tuesday 02:00–04:00 local and monthly Saturday 20:00–22:00 UTC reserved for pipeline migrations; customer-impacting changes require 72-hour notice to Customer Success.
- Readiness tasks: daily checklist verifies queue depth, shadow divergence metrics, QA acceptance status, and Guardian alignment before start of business; results archived for audit.

### 8.2 Incident Triggers (binding)

**Purpose:** Define the alerts and dashboards that escalate LangGraph incidents so responders execute the correct runbooks. **|**
**Contract:** Each trigger maps to a specific RB-AGENT playbook; alerts must remain actionable with paging enabled during coverage windows. **|**
**State:** Alert definitions live in `infra/monitoring/agents-prometheus-rules.yaml`, PagerDuty service “Agents Pipeline”, and synthetic job specs `infra/synthetics/agents_shadow.yaml`. **|**
**Failures & handling:** False positives and stale alerts feed the alert hygiene backlog; unresolved gaps block activation rollouts. **|**
**Observability:** Dashboards “Agent Pipelines – Activation”, “LangGraph QA”, and synthetic runs provide drill-down context; divergence reports log to `ops/reports/agents/incidents/*.md`. **|**
**Breadcrumbs:** PagerDuty config `ops/pagerduty/agents.json`, alert catalog `docs/ops/runbooks/alert_catalog.md`, synthetic configs `infra/synthetics/agents_shadow.yaml`, QA policy `docs/policy/langgraph_incident_policy.md`. **|**
**References:** §5 Failure Modes, Ops runbooks `RB-AGENT-SHADOW`, `RB-AGENT-ACTIVATION`, `RB-AGENT-QA`.

- `agent_shadow_divergence_total` or replay mismatches trigger `RB-AGENT-SHADOW` to disable the candidate pipeline and roll back to the prior manifest.
- `agent_job_duration_seconds` / `agent_retry_total` breaches signal backlog or provider instability and dispatch `RB-AGENT-ACTIVATION` plus Worker Cluster escalation.
- QA failure spikes (`qa_blocking_total`, `qa_issue_density`) page via `RB-AGENT-QA` to rerun validation, quarantine outputs, and coordinate Guardian review.
- Settings activation failures (`agents_pipeline_activation_failed_total`) route to `RB-AGENT-ACTIVATION`; responders collect manifests and block further rollouts.
- Guardian or residency blocks (`guardian_region_policy_block_total`) require joint investigation with Guardian (§8.2) before resuming agent execution.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Ensure operators have actionable playbooks for agent degradations, activation failures, and QA regressions. **|**
**Contract:** Runbooks listed here must remain current, link to Ops catalog entries, and surface evidence expectations for compliance. **|**
**State:** Runbook markdown lives under `docs/ops/runbooks/agents/`; drill evidence and after-action reviews are archived in `ops/runboo../data/agents/`. **|**
**Failures & handling:** Missing or stale runbooks block launch; drills uncover coverage gaps and feed remediation tickets. **|**
**Observability:** Ops catalog build (`python -m doc_tools.build.runbook_catalog`), drill checklist dashboards, and on-call retros track preparedness. **|**
**Breadcrumbs:** Runbook catalog `docs/ops/runbooks.md`, evidence store `ops/runboo../data/agents/`, drill tracker `ops/runbooks/agents/drill_log.csv`. **|**
**References:** Ops runbooks index, TDD Appendix B, Worker Cluster spec §3.5, QA governance §6.

- Runbooks must cover activation rollback, shadow divergence, Guardian quarantine escalation, and QA defect surge.
- On-call rotation uses `RB-AGENT-TIMEOUT`, `RB-AGENT-RETRY`, `RB-AGENT-ACTIVATION`, `RB-AGENT-SHADOW`, and `RB-AGENT-QA`.
- Drill cadence and evidence capture feed quarterly readiness reviews and SOC2/SOCPA audits.

#### 8.3.1 Runbook Index (informative)

The catalog enumerates each runbook with owner, verification cadence, and Ops catalog ID. Maintained via `python -m doc_tools.build.runbook_catalog`; stale ownership or verification dates fail the docs lint and block merges.

- `RB-AGENT-ACTIVATION` — Applied AI Engineering (primary), Platform Operations (secondary), verified quarterly.
- `RB-AGENT-SHADOW` — Platform Operations (primary), Applied AI Engineering (secondary), verified quarterly.
- `RB-AGENT-TIMEOUT` — Worker Cluster owners, verified monthly.

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Highlight the runbooks that must exist before activating or modifying agent pipelines. **|**
**Contract:** Each primary runbook documents trigger conditions, escalation path, mitigation steps, and evidence capture. **|**
**State:** Markdown sources under `docs/ops/runbooks/agents/`; evidence appended to drill log. **|**
**Failures & handling:** Missing steps or outdated escalations prompt remediation tickets before launch readiness sign-off. **|**
**Observability:** Ops QA reviews, incident postmortems, and audit sampling confirm runbook quality. **|**
**Breadcrumbs:** `docs/ops/runbooks/agents/agent_activation.md`, `docs/ops/runbooks/agents/agent_shadow.md`, `docs/ops/runbooks/agents/agent_retry.md`. **|**
**References:** Ops QA policy, TDD §12 (observability/DR), Worker Cluster spec §3.5.

- Activation rollback: capture commands to revert settings activation, disable pipelines, and restore prior manifests.
- Shadow divergence: enumerate alert thresholds, disable steps, data capture for analysis, and communications checklist.
- QA defect surge: describe Guardian quarantine coordination, manual QA staffing, and follow-up tasks.

#### 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover SLO breach recovery, quarantine spikes, backlog management, and manual reconciliation; evidence stored in `ops/runboo../data/agents/<YYYY>/<MM>/` with retrospective notes.
- `python -m doc_tools.build.runbook_catalog --check` plus PagerDuty analytics verify execution; missed drills require catch-up within 30 days and block activation rollouts.
- Compliance reviews reference drill evidence, incident logs, and manual review ledgers to demonstrate readiness for auditors.

### 8.4 Migrations & Backfills (normative)

**Purpose:** Describe operational work required to migrate manifests or backfill lineage after pipeline changes. **|**
**Contract:** Backfill scripts must be idempotent, record audit entries, and run under controlled settings toggles. **|**
**State:** Migration scripts live under `ops/scripts/agents/`; run logs and manifests stored with timestamps in `ops/backfill/agents/`. **|**
**Failures & handling:** Backfill failures trigger rollback, Guardian quarantine for affected artifacts, and incident tracking. **|**
**Observability:** Backfill dashboards, ops JSONL entries (`ops_agents_backfill.jsonl`), and post-run validation harness. **|**
**Breadcrumbs:** Backfill tooling `ops/scripts/agents/backfill_manifests.py`, validation tests `tests/agents/test_backfill_validation.py`. **|**
**References:** TDD §6 summary, Ops runbooks `RB-AGENT-BACKFILL`, Settings spec §5.4.

- Define cutover windows, pause new jobs if required, and coordinate with Worker Cluster for job draining.
- Record pre/post metrics (job backlog, QA pass rate) and attach to backfill evidence.
- Ensure manifests re-hash outputs and Guardian judgments remain consistent post-backfill.

### 8.5 Operational Workflows (informative)

**Purpose:** Capture day-to-day operational routines for the agent platform. **|**
**Contract:** Workflows cover daily health checks, backlog triage, Guardian alignment, and QA sampling. **|**
**State:** Daily checklists stored in `ops/runbooks/checklists/agents_daily.md`; backlog reports archived in `ops/reports/agents/backlog/`. **|**
**Failures & handling:** Missing daily checks escalate to on-call; backlog beyond thresholds triggers surge staffing per Ops policy. **|**
**Observability:** Daily metrics dashboard (“Agent Daily Health”), backlog alerting, QA sampling logs. **|**
**Breadcrumbs:** Daily checklist `ops/runbooks/checklists/agents_daily.md`, backlog script `ops/scripts/agents/backlog_report.py`, QA sampling summary `ops/reports/agents/qa_sampling.csv`. **|**
**References:** Worker Cluster spec §3, Guardian spec §2, QA governance §6.

- Morning health review covers pipeline activation status, queue depth, shadow divergence, and QA defect trend.
- Backlog triage coordinates with Worker Cluster to reassign concurrency slots and focus on SLA-bound cases.
- Daily QA sampling selects artifacts for manual review, reconciling QA harness findings with Guardian verdicts.

______________________________________________________________________

## 9) Dependencies

**Purpose:** Describe how LangGraph agents interact with other platform services (Settings, LLM Registry, Worker Cluster, Guardian, Compose templates). **|**
**Contract:** Agents must resolve Settings snapshots, call LLM Registry for model selection, respect Guardian gating, stream status via Notifications, and coordinate with Worker Cluster scheduling + watchdog timers. **|**
**State:** Settings snapshots stored in manifests; LLM Registry envelopes include provider selections; Worker Cluster tracks Celery tasks; Notifications propagate SSE updates. **|**
**Failures & handling:** Missing settings or registry configurations halt activation; Guardian rejection blocks promotion; Worker Cluster watchdog triggers job retry or manual intervention. **|**
**Observability:** Settings activation logs, registry audit events, Worker Cluster dashboards, Notifications queues, and Guardian telemetry track integration health. **|**
**Breadcrumbs:** Settings spec §5, LLM Registry spec §2, Worker Cluster spec §3, Communications spec §2, Compose spec §4, tests `tests/integration/test_agent_dependencies.py`. **|**
**References:** TDD §3, §6 summary, Guardian spec §2.3, Web App spec §5 (editors/assistants), Settings spec appendices.

- Settings alignment: `agents.pipeline.*`, `agents.tools.*`, `compose.policy.*`, `analyze.policy.*`, `assistant.*` keys validated against this spec; lint scripts ensure canonical IDs and enumerations.
- LLM Registry: each node passes `llm_profile_id`, `prompt_template_id`, and envelope metadata; registry enforces residency, cost ceilings, model version pinning, and moderation guardrails.
- Worker Cluster: orchestrates Celery tasks, enforces concurrency limits, monitors job runtime, and pages on stuck jobs; integrates with Guardian for quarantine.
- Notifications: SSE updates broadcast job progress, QA status, Guardian results; Notification retries ensure UI state remains consistent.
- Compose templates & deliverable catalog: Compose lanes pull template metadata and signature policies; Signer integration ensures deliverable manifests align with pipeline outputs.

______________________________________________________________________

## 10) References

- TDD §6 Agent ecosystem summary
- Settings spec §5 (agent configuration keys)
- LLM Registry spec §2 (provider selection, residency)
- Worker Cluster spec §3 (job orchestration)
- Ops runbooks `RB-AGENT-\*`
- ADR-0003 Localization & Policy Engine, ADR-0001 Guardian READY/QUARANTINED

______________________________________________________________________

## Appendix A – Agent schemas & error taxonomy (binding) {#appendix-a-agent-schemas-error-taxonomy}

**Purpose:** Provide typed schema examples and canonical error codes for agent outputs. **|**
**Contract:** Schemas must remain in sync with implementation; error codes are authoritative and map to failure classes in §5. **|**
**State:** Pydantic models live in `packages/udocket_core/agents/schemas.py`; schema snapshots export to `spec/schemas/agents/*.schema.json`; lane validators and QA harnesses use these schemas for runtime validation. **|**
**Failures & handling:** Schema drift fails CI; unknown error codes block merges via lint; manifests lacking schema versions trigger `E_INTEGRITY_MISMATCH`. **|**
**Observability:** Schema lints in CI, error code coverage dashboards, QA harness logs. **|**
**Breadcrumbs:** Models `packages/udocket_core/agents/schemas.py`, schemas `spec/schemas/agents/`, tests `tests/agents/test_schema_consistency.py`. **|**
**References:** Compose spec Appendix B, Analyze spec Appendix A, Platform TDD §6.

### A.1 Analyze agent schema (binding)

Exported JSON Schemas (all under `spec/schemas/agents/`):

- `transcript_v1.schema.json` — TranscriptJSON (segment UUIDs, speakers, hashes, diarisation flag).
- `analyze_outline_v1.schema.json` — OutlineJSON derived from DOCX template headings.
- `analyze_timeline_v1.schema.json` — TimelineJSON with events (`uuid`, timestamps, speaker, text, labels).
- `analyze_entities_v1.schema.json` — EntitiesJSON with entities and relations (plus evidence pointers).
- `analyze_issues_v1.schema.json` — IssuesJSON describing issue text, risk level, notes, evidence references.
- `analyze_gaps_v1.schema.json` — GapsJSON capturing missing information, impact, and follow-up needs.
- `analyze_flags_v1.schema.json` — FlagsJSON enumerating case flags with severity levels and references.
- `analyze_alerts_v1.schema.json` — AlertsJSON highlighting priority alerts and escalation metadata.
- `analyze_summary_v1.schema.json` — SummaryJSON (case metadata summary, executive summary bullets, detailed narrative sections, procedural posture, issues, checklist, supporting quotes).
- `analyze_qa_report_v1.schema.json` — QAReportJSON with completeness/consistency/schema scores and narrative notes.

Each schema includes `schema_version`, `produced_at`, and deterministic UUID requirements that align with manifests.

### A.2 Compose agent schema (binding)

- `compose_section_output_v1.schema.json` — SectionOutput (section identifiers, role, markdown body, linked issues).
- `compose_document_v1.schema.json` — Deliverable container for client, lawyer, or bundle outputs.
- `compose_qa_report_v1.schema.json` — Compose QA report (status, findings, references).
- `compose_manifest_v1.schema.json` — Manifest snapshot linking templates, analyze artifacts, provider selections, Guardian verdicts.

### A.3 Additional lane models

- Shared helpers:
  - `event_reference.schema.json` — Canonical reference to timeline events by UUID and timestamp.
  - `issue_reference.schema.json` — Lightweight pointer to Analyze issues for Compose sections and QA findings.
  - `evidence_pointer.schema.json` — Standardised pointer to transcript segments or document excerpts.
  - `idempotency_key.schema.json` — Manifest record of lane-specific idempotency tokens.
  - `prompt_provenance.schema.json` — Recorded for every LLM invocation in per-run metadata.
- QA metrics:
  - `qa_metric.schema.json` — Normalised representation of completeness/consistency/schema scores embedded in Analyze and Compose QA reports.

### A.4 Error codes

- `E_TRANSIENT_PROVIDER` → class `TRANSIENT`
- `E_POLICY_FORBIDDEN` → class `POLICY`
- `E_INPUT_INVALID` → class `INPUT`
- `E_INTEGRITY_MISMATCH` → class `INTEGRITY`
- `E_CONFLICT` → class `CONCURRENCY`
- `E_REGION_POLICY` → class `REGION_POLICY`

Ops JSON includes `{code, class, message, attempt, final}` for every failure; UI shows human-friendly error strings mapped from this table.

______________________________________________________________________

## Appendix B – Settings & activation keys (informative)

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
| `compose.policy.*` | SYSTEM\|ORG | Forbidden patterns, required sections, link limits. |
| `analyze.policy.*` | SYSTEM\|ORG | Lane enablement, QA thresholds, evidence requirements. |
| `assistant.*` | SYSTEM\|ORG | Conversational pipeline configuration + moderation. |
| `speech.jobs[]` | SYSTEM\|ORG | Transcription job profiles and fallback providers. |
| `agents.runtime.langgraph_enabled` | SYSTEM | Feature flag gating LangGraph runtime. |

______________________________________________________________________

## Appendix C – Roadmap & Open Questions (informative)

- LangGraph adoption guardrails: maintain linear fallback until shadow mode and QA metrics remain stable for three consecutive releases; GraphRunner feature flag stays available for emergency rollback.
- Timeline/relationship agents: graduate from informative to binding once schemas finalise and QA thresholds are met.
- Generative QA evaluators: expand QA harness to include automated fact checks and integrate with Guardian for cross-check; pending ADR.
- Human-in-the-loop telemetry: integrate Manual/Agent edit signals directly into manifests to trigger automatic QA reruns and Guardian verification.
