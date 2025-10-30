---
title: uDocket — LLM Registry & Runtime Governance Specification
subtitle: Model Selection, Safety, and Observability Controls
author:
  - LLM Platform Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Architecture
  - Security Engineering
  - Applied AI Programs
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - QA Engineering Lead
  - FinOps Manager
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
  - <header class="page-header">uDocket — LLM Registry & Runtime Governance Specification <br>
    Model Selection, Safety, and Observability Controls</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page 
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

| Field | Value |
| --- | --- |
| Authors | LLM Platform Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Architecture; Security Engineering; Applied AI Programs |
| Reviewers | QA Engineering Lead; FinOps Manager |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by | |
| Approved date | |

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** LLM provider catalog, selection orchestration, residency safeguards, moderation, reproducibility, and FinOps controls governing Analyze/Compose lanes and other agent workloads.
- **Structure:** Follows the standard 0–10 template; subsections are marked (binding/normative/informative) per policy vocabulary. Appendices live in ops runbooks for golden sets and moderation configs.
- **Maintenance:** Run `python scripts/docs/lint_docs.py` before submitting changes. Update golden-set fixtures and moderation configs referenced here when models, prompts, or safety settings change.
- **Change protocol:** Any PR touching `llm.providers[]`, `llm.models[]`, failover logic, moderation, or FinOps guardrails must cite this spec and ADR-0003. Security + Architecture approval required for provider additions or residency waivers.
- **References:** TDD §8 summary, LPE spec §2 (PolicyContext), Settings spec §2 (activation), Ops runbooks RB-LLM-003/RB-LLM-JB.
- **Contacts:** Platform Architecture (catalog), Security Engineering (safety/residency), Applied AI Programs (golden sets, moderation).

______________________________________________________________________

## 1) Purpose

**Purpose:** Govern model selection, safety, and runtime controls for all LLM-backed workloads. **|**
**Contract:** Registry enforces residency, version pinning, moderation, reproducibility, and FinOps guardrails while exposing deterministic envelopes for replay and audit. **|**
**State:** Provider metadata resides in Settings bundles; runtime decisions and evidence store envelopes capture per-call provenance; FinOps metrics and circuit state drive dashboards. **|**
**Failures & handling:** Provider drift, safety violations, or cost overruns trigger circuit breakers, moderation quarantines, or deploy gates per §5. **|**
**Observability:** Grafana dashboards (“LLM Residency & Failover”, “LLM Safety & Moderation”, “FinOps – LLM Cost & Circuit”) track health, safety, and spend; alerts map to RB-LLM-003 and RB-LLM-JB. **|**
**Breadcrumbs:** Implementation `packages/udocket_core/llm/*`, Settings bundles `apps/platform/settings/services/llm.py`, moderation `packages/udocket_core/llm/moderation.py`, failover orchestrator `packages/udocket_core/failover/model.py`, tests `tests/udocket_core/llm/*`, `tests/platform/settings/test_llm_*`. **|**
**References:** §2 Responsibilities, §4 State management, §6 Observability, Ops runbooks RB-LLM-003/RB-LLM-JB.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Outline the registry’s duties across provider selection, prompts, safety, and FinOps governance. **|**
**Contract:** Responsibilities consolidate mandatory controls for residency, moderation, reproducibility, and spend while exposing deterministic behaviours to downstream agents. **|**
**State:** Settings bundles, decision traces, evidence store envelopes, and FinOps reports record ownership of provider metadata and runtime outputs. **|**
**Failures & handling:** Gaps in any responsibility open registry circuits, block workloads, and trigger runbooks summarized in §5. **|**
**Observability:** Dashboards in §6 monitor residency, moderation, and cost signals; alerts map directly to RB-LLM-\* runbooks. **|**
**Breadcrumbs:** Core modules `packages/udocket_core/llm/*`, evidence writers, decision trace logs, and tests cited throughout §2. **|**
**References:** §1 Purpose, §4 State management, §7 Security & compliance.

### 2.1 Provider registry, health, and selection (binding)

**Purpose:** Enforce residency, health, and preference constraints whenever workloads select an LLM provider. **|**
**Contract:** Registry evaluates providers using Settings catalog entries, live health probes, and fallback policies; selection must obey residency allowlists, version pins, moderation requirements, and FinOps ceilings. **|**
**State:** Settings bundles `llm.providers[]`/`llm.models[]` define endpoints, auth, pricing, fallback chains, and metadata; runtime stores capture circuit state, decision traces, and cost estimates inside evidence envelopes. **|**
**Failures & handling:** Provider degradation, residency drift, or missing parity evidence open circuits (`ModelFailoverOrchestrator`), pause jobs, and route responders to RB-LLM-003. **|**
**Observability:** Dashboards “LLM Residency & Failover” and “FinOps – LLM Cost & Circuit” track `llm_region_fallback_total`, `llm_circuit_state`, `llm_cost_estimate_total`; alerts `alert_llm_circuit_open` and `provider_data_policy_drift_total` page on-call. **|**
**References:** Settings spec §2 (activation), LPE spec §2 (PolicyContext residency hints), §2.1.2 of this document (Failover orchestrator).
**Breadcrumbs:** Implementation `packages/udocket_core/llm/registry.py`, `packages/udocket_core/llm/catalog.py`, `packages/udocket_core/llm/decision_trace.py`; tests `tests/udocket_core/llm/test_registry.py`, `tests/platform/settings/test_llm_catalog.py`.

- Settings catalog entries capture endpoints, credentials, supported locales, regions, rate limits, pricing, moderation posture, and fallback priorities.
- Health polling maintains rolling latency/error windows; circuits flip OPEN when thresholds exceed policy. Half-open probes run every 60 seconds to validate recovery.
- Circuit transitions append to evidence envelopes with `{circuit_state_before, circuit_state_after, sample_reason}` and emit audit events `LLM_CIRCUIT_STATE_CHANGE` so FinOps can reconcile spend impact.
- Selection enforces `regions.allowlist.compute/storage`, language/org preferences, case overrides when healthy, and iterates `fallback_priority` when primaries degrade. Token ceilings per lane cap prompts.
- Fallback equivalence matrix (binding): each model lists a `fallback_chain` with documented parity (±3 % quality delta on the golden set, identical residency/data-use posture, comparable latency). Activation validators require parity evidence (`fallback.evidence_sha256`).
- Decision traces log `{model_id, model_version, provider_region, reason_code, health_snapshot, cost_estimate}` for every call and feed evidence store plus FinOps dashboards.
- Model version pinning (binding): `llm.models.version_pin` or provider snapshot IDs must be present. Registry rejects mismatched live versions unless a waiver exists; envelopes embed `{model_id, model_version}` and Settings snapshots provide `settings_snapshot_sha256` for replay.
- Provider data-use posture: registry enforces vendor toggles (`llm.providers[].log_retention=false`, `llm.providers[].train_on_data=false`) and verifies headers (for example `x-ms-logging-enabled`); drift raises `PROVIDER_DATA_POLICY_DRIFT` and blocks selection until remediated.

#### 2.1.1 LLM & vector residency guard (binding)

**Purpose:** Maintain residency guarantees across LLM and vector workloads. **|**
**Contract:** Configuration lints, service-mesh policies, and runtime circuits must align with `regions.allowlist.compute/storage`; cross-region failover without waiver is forbidden. **|**
**State:** Residency metadata lives in LPE PolicyContext, Settings allowlists, and vector provider configs; runtime events record `vector_region` and waiver usage. **|**
**Failures & handling:** Region drift triggers `LLM_REGION_FALLBACK`, opens circuits, and pauses jobs via RB-LLM-003; waivers tracked in `ops/security/waivers/llm_residency.yaml`. **|**
**Observability:** Dashboard “LLM Residency & Failover”, metrics `llm_region_fallback_total`, synthetic `synthetics/llm_residency.yaml`. **|**
**Breadcrumbs:** Residency guard `packages/udocket_core/llm/residency_guard.py`, vector enforcement `packages/udocket_core/vector/residency.py`, tests `tests/udocket_core/llm/test_residency_guard.py`, `tests/udocket_core/vector/test_vector_residency.py`.

- Residency enforcement combines:
  1. Activation linting—reject providers/models outside allowlists; vector stores list shard regions and fail activation on drift.
  2. Mesh `AuthorizationPolicy` mirroring allowlists so only approved endpoints (plus waived hosts) pass egress; vector clients inherit and log `vector_region`.
  3. Runtime circuit breaker tracking provider regions; fallback to non-allowlisted regions raises `LLM_REGION_FALLBACK`, opens the circuit (`circuit_state=OPEN`, reason `REGION_DRIFT`), and blocks calls until health probes confirm recovery.
- Fallback hierarchy prioritizes residency over latency; if no healthy in-region model exists, registry returns `PROVIDER_DEGRADED` rather than spilling out of region.
- Evidence envelopes record residency policy version and waiver IDs; dashboards display residency decision distributions alongside PolicyContext version.
- Synthetic monitors validate mesh denial for banned regions and ensure golden tenants (for example `EU-REFERENCE`) retain EU residency across providers.

#### 2.1.2 Failover orchestration helper (binding)

**Purpose:** Provide deterministic provider failover with parity and safety checks. **|**
**Contract:** `ModelFailoverOrchestrator` evaluates fallback candidates, enforces parity evidence, throttling budgets, and pause/resume gating; all call sites must use the orchestrator. **|**
**State:** Orchestrator records counters (`llm_failover_attempt_total{provider,reason}`, `llm_failover_pause_total`), parity hashes, and event logs consumed by dashboards and audit pipelines. **|**
**Failures & handling:** Missing parity evidence or repeated failover attempts escalate via RB-LLM-003; circuits remain OPEN until three consecutive green probes succeed. **|**
**Observability:** Grafana “LLM Failover” dashboard, metrics `llm_circuit_state`, `llm_failover_attempt_total`; synthetic `synthetics/llm_failover.yaml`. **|**
**Breadcrumbs:** Implementation `packages/udocket_core/failover/model.py::ModelFailoverOrchestrator`, adapter registry `packages/udocket_core/failover/adapters.py`, tests `tests/udocket_core/failover/test_model_orchestrator.py`.

- Orchestrator emits standardized events (`LLM_FALLBACK_TRIGGERED`, `LLM_FAILOVER_PAUSED`, `LLM_FAILOVER_RESUMED`) with parity hashes and cost deltas.
- New providers register adapters implementing the `FailoverAdapter` protocol; missing health probes, parity metadata, or residency attestations fail activation.
- Telemetry integrates with FinOps dashboards so spend impact of failover is visible; open circuits beyond 15 minutes page on-call.

### 2.2 Prompt management, redaction, and evidence store (binding)

**Purpose:** Control prompt content, redaction, and audit-friendly evidence for all LLM calls. **|**
**Contract:** Prompt templates, directives, and guardrails are defined via Settings `agents.prompts.*`; runtimes must use masked working copies, enforce moderation, and persist reproducibility envelopes. **|**
**State:** Prompt assets materialize under `packages/udocket_core/config/`, evidence store entries record `{prompt_template_id, template_version, model_id, model_version, redaction_ruleset_id, token_ceiling, hashes}`; moderation verdicts and QA outcomes append to manifests. **|**
**Failures & handling:** Prompt drift, redaction failures, or moderation violations trigger QA holds, Guardian quarantine, or RB-LLM-JB responses. **|**
**Observability:** Dashboard “LLM Safety & Moderation” tracks `llm_content_flagged_total{reason}`, `llm_moderation_latency_seconds`, `redaction_stats{kind}`; alerts `llm_moderation_failure_total` and `llm_policy_block_total` page Security + Applied AI. **|**
**References:** Guardian spec §5 (judgment), Settings spec §2.5 (prompt activation), Ops runbooks RB-LLM-JB (jailbreak) and RB-LLM-PROMPT.
**Breadcrumbs:** Prompt tooling `packages/udocket_core/llm/prompt_registry.py`, redaction `packages/udocket_core/redaction/masking.py`, moderation `packages/udocket_core/llm/moderation.py`, evidence store `packages/udocket_core/llm/evidence_store.py`, tests `tests/udocket_core/llm/test_prompt_registry.py`, `tests/udocket_core/llm/test_evidence_store.py`.

- Prompt templates, lane directives, and guardrails reside in Settings `agents.prompts.*` (SYSTEM with ORG/CASE overrides) and lint via Pydantic validators for explicit version IDs, LangGraph-compatible placeholders, and deterministic variable ordering.
- Prompt activations inherit `change_class="system"` and flow through the blue/green rollout in §14.5; manifests stamp `{prompt_version, rollout_wave, org_id}` for audit.
- Redaction layer strips PII before dispatch; runtime rejects attempts to inject raw spans. Guardian span detections replace raw values with deterministic placeholders (for example `[PATIENT-3]`, `SSN{•-•-1234}`), and contract tests diff prompts to confirm only masked tokens leave the platform.
- Evidence store (hardened datastore) captures prompt/response hashes, model metadata, and redaction rulesets; access restricted to `auditor|sysadmin` roles.
- Logs include truncated prompt/response excerpts with redacted content for debugging; HIPAA mode (`privacy.hipaa.prompt_retention_mode`) disables excerpt storage and relies on hashes plus replay evidence.
- HIPAA enable guard (binding): Settings activation refuses `privacy.hipaa.enabled=true` until `scripts/privacy/purge_evidence_store.py` uploads a `PRIVACY_PURGE_REPORT` proving legacy excerpts removed.
- Sampling: ≥5 % of inference calls per model/org undergo manual review daily; audit sampler writes signed reports under `ops/security/provider_audits/YYYY-MM/` summarizing detections and provider response headers.
- Nightly harness runs template checksum/linting and regeneration smoke tests; failures block deployments until resolved.
- Provider assurances (“no training on customer data”) validated periodically and archived in `ops/security/provider_audits/`; agent wrappers set `x-ms-azureml-client-env-data-collection=false` (where supported) and audit provider response headers for confirmation.

Binding checkpoints (sample)

| Binding | Implementation | Test | Observability |
| --- | --- | --- | --- |
| HIPAA excerpt suppression | `packages/udocket_core/llm/evidence_store.py::store_excerpt` | `tests/udocket_core/llm/test_evidence_store.py::test_hipaa_mode_blocks_excerpts` | Audit event `HIPAA_EXCERPT_BLOCK` (Privacy dashboard) |
| Prompt masking contract | `packages/udocket_core/redaction/masking.py::mask_prompt_payload` | `tests/udocket_core/llm/test_prompt_registry.py::test_prompts_use_masked_payloads` | Metric `redaction_stats{kind="prompt"}` |
| Prompt activation rollout | `apps/platform/settings/services/llm.py::activate_prompts` | `tests/platform/settings/test_llm_prompts.py::test_activation_rolls_forward_versions` | Audit log `PROMPT_VERSION_ACTIVATED`; dashboard “LLM Prompt Rollout” |

#### 2.2.1 PII posture (binding)

- No raw PII/PHI may surface in LLM-produced artifacts; masked tokens (for example `[PATIENT-3]`, `(***) ***-1234`) are the only approved representation outside the evidence store.
- Full, unredacted prompts/outputs reside solely in the hardened evidence store with encryption at rest and RBAC limited to `auditor|sysadmin`.
- Mask–unmask maps never persist to artifacts; they remain scoped to the redaction context used inside the envelope pipeline.

### 2.3 Safety harness (jailbreak tests & policy enforcement) (binding)

**Purpose:** Detect prompt injection, bias, and policy breaches before artifacts reach reviewers or clients. **|**
**Contract:** Pre-call filters, moderation stack, QA evaluators, and Guardian gating must remain active with defined thresholds; golden-set jailbreak tests gate releases. **|**
**State:** Safety configuration keys (`llm.moderation.*`, `qa.confidence.threshold`, policy allowlists) live in Settings; moderation + QA verdicts attach to manifests and Guardian history. **|**
**Failures & handling:** Moderation outages or QA regressions block promotion, escalate via RB-LLM-JB, and require documented mitigation. **|**
**Observability:** Dashboard “LLM Safety & Moderation”, metrics `llm_content_flagged_total`, `llm_moderation_error_total`, `qa_confidence_distribution`, SSE `llm.policy_block`. **|**
**References:** Guardian spec §5, Ops runbook RB-LLM-JB, QA guidelines App.T.
**Breadcrumbs:** Moderation stack `packages/udocket_core/llm/moderation.py`, QA evaluators `packages/udocket_core/qa/evaluator.py`, tests `tests/udocket_core/llm/test_moderation.py`, `tests/udocket_core/qa/test_evaluator.py`.

- Pre-call filters sanitize prompts, enforce instruction allowlists, and ensure locale/region compatibility.
- Moderation stack (provider APIs + in-house classifiers for `toxicity`, `self_harm`, `sexual_content`, `pii_reintroduction`) runs before and after inference. Violations emit `LLM_CONTENT_FLAGGED`, mark artifacts `QUARANTINED`, and require remediation plus Guardian resubmission.
- Configuration keys (`llm.moderation.enabled`, `llm.moderation.provider`, enforcement `llm.moderation.enforcement ∈ {block,warn}`, thresholds `llm.moderation.thresholds.*`) govern behavior; production defaults to `block` unless waiver active. Non-prod orgs may temporarily select `warn` for tuning, but every WARN verdict logs to Guardian analytics and expires after the configured window.
- Guardian consumes moderation/QA verdicts and blocks promotion when `LLM_CONTENT_FLAGGED` or `POLICY_BLOCK` is set.
- Golden-set jailbreak runs execute nightly across languages; regressions page on-call and block release pipelines (`golden_set:jailbreak`).
- QA evaluators enforce schema, citation, and policy checks; configuration `qa.confidence.threshold` ensures low-confidence runs require human review even if job requested `SKIP_REVIEW`.
- Forbidden content detection automatically quarantines artifacts and logs audit events `LLM_POLICY_BLOCK`.

### 2.4 Cost controls & FinOps budgets (binding)

**Purpose:** Prevent runaway spend while maintaining visibility for FinOps and product. **|**
**Contract:** Pre-call guards enforce token ceilings and monthly caps; controllers pause jobs when projections exceed budgets; deploy gates block releases with adverse cost regressions. **|**
**State:** Settings keys `analyze|compose.token_ceiling`, `llm.finops.monthly_cap_usd`, `llm.finops.guard.threshold_pct`, `llm.finops.guard.trailing7d_pct`, and override metadata live in Settings; controllers log actions via audit events and Guardian quarantine reasons. **|**
**Failures & handling:** Budget breaches set jobs to `PAUSED_AWAITING_BUDGET`, emit `FINOPS_BUDGET_HELD`, and require override or cap adjustment; MoM guard failures block deploys until mitigated (§2.4.1). **|**
**Observability:** Dashboard “FinOps – LLM Cost & Circuit” tracks `llm_cost_estimate_total`, `finops_budget_hold_active_total`, `finops_budget_hold_duration_seconds`; deploy gate reports live in `ops/finops/mom_guard/`. **|**
**References:** Ops runbook RB-LLM-FINOPS, TDD §8.7 FinOps guard.
**Breadcrumbs:** Budget controller `packages/udocket_core/finops/guard.py`, management command `apps/platform/operations/management/commands/set_finops_override.py`, tests `tests/udocket_core/finops/test_guard.py`, `tests/platform/finops/test_override_roles.py`.

- Pre-call guards enforce tokens-in ≤ configured ceilings and verify projected spend + month-to-date ≤ cap; violations return `429 RATE_LIMIT` with reasons `TOKEN_CEILING` or `BUDGET_EXCEEDED`.
- Metrics exported: `llm_call_count`, `llm_tokens_in/out`, `llm_cost_estimate_total{org,case,job,model}` and FinOps reports `FINOPS_REPORT` per org.
- Controllers mark affected jobs `PAUSED_AWAITING_BUDGET`, emit SSE `job.blocked` with `warning="BUDGET_HELD"`, and log audit `FINOPS_BUDGET_HELD`. Resume requires override or cap increase.
- Alerts `finops_budget_hold_active_total` and `finops_budget_hold_duration_seconds` page FinOps/Product; resume events log `FINOPS_BUDGET_RESUMED` and auto-clear quarantines once relief confirmed.
- Diagram `services/lp-engine/diagrams/finops-guard-v1.mmd` visualizes the deploy guard decision flow (shared with LPE spec §7.4).

#### 2.4.1 FinOps deploy guard (binding)

**Purpose:** Block releases with unacceptable month-over-month or trailing spend regression. **|**
**Contract:** Deploy gate `scripts/finops/check_mom_guard.py` compares projected month-end spend against prior actuals; threshold default 10 % MoM, 25 % trailing 7-day of cap. Overrides require Product + Security approval and expire automatically. **|**
**State:** Reports written to `ops/finops/mom_guard/<release>.json`; Settings key `llm.finops.override_until` stores temporary bypass windows. **|**
**Failures & handling:** Gate failure blocks release until mitigation or approved override; results documented in App.O decision log. **|**
**Observability:** Metric `finops_mom_regression_flag{org}`, dashboard “FinOps Guard”, alert `finops_deploy_gate_failed_total`. **|**
**References:** TDD §8.7 FinOps guard, Ops runbook RB-LLM-FINOPS.
**Breadcrumbs:** Guard implementation `packages/udocket_core/finops/guard.py::projected_regression_pct`, override tooling `apps/platform/operations/management/commands/set_finops_override.py`, tests `tests/udocket_core/finops/test_guard.py`.

- Regression formula: `(projected_month_end - prior_month_actual) / prior_month_actual ≥ llm.finops.guard.threshold_pct` after smoothing.
- Trailing 7-day guard ensures spend stays ≤ `llm.finops.guard.trailing7d_pct` of cap; overrides bounded between 10 % and 40 %.
- Emergency overrides limited to `Security Engineering Lead` + `VP Product`, expire after 72 hours, and log audit `FINOPS_OVERRIDE_APPLIED`.

______________________________________________________________________

## 3) API Contract

**Purpose:** Document interfaces that govern registry updates, health reporting, and decision telemetry. **|**
**Contract:** Settings activation remains the authoritative write path for provider/catalog changes; runtime exposes health summaries, circuit events, and evidence envelopes rather than direct public APIs. **|**
**State:** `llm.providers[]`/`llm.models[]` Settings bundles, decision trace JSONL (`ops/llm/decision_trace.jsonl`), SSE topics (`provider.health`, `job.update` warnings), and audit events capture API outputs. **|**
**Failures & handling:** Health endpoint drift or event schema incompatibilities trigger RB-LLM-API and block downstream consumers until resolved. **|**
**Observability:** API metrics `provider_health_request_total`, `provider_health_latency_seconds`, audit `LLM_CIRCUIT_STATE_CHANGE`, SSE schema version checks in CI. **|**
**Breadcrumbs:** Health endpoint `apps/platform/api/providers.py::get_health`, decision trace writer `packages/udocket_core/llm/decision_trace.py`, SSE publisher `apps/platform/events/llm.py`, tests `tests/platform/api/test_provider_health.py`. **|**
**References:** Settings spec §2, Jobs API §10 (TDD), Guardian spec §3, Compose/Analyze agents.

### 3.1 External Interfaces

- Settings activation (`apps/platform/settings/services/llm.py`) remains the single write surface for provider metadata; change management requires ADR references and dual approval.
- Admin API `GET /ops/llm/providers/health` returns circuit status, residency posture, and probe metrics for dashboards; responses cached for 10 seconds.
- SSE channel `provider.health` broadcasts status deltas (`OPEN`, `HALF_OPEN`, `CLOSED`) so Portal, Compose, and Guardian halt workloads when registry fails closed.

### 3.2 Internal Interfaces

- Celery task modules `operations.task_modules.llm.*` invoke `RegistrySelector` helpers and emit decision traces to evidence store queues.
- Background job `llm_health_poll` writes probe results and flips circuit states; results persisted in `ops/llm/health_poll/<date>.jsonl`.
- Moderation pipeline integrates via `packages/udocket_core/llm/moderation.py::ModerationClient`, enforcing policy verdicts before Compose/Analyze continue.

- Settings activation (system scope) is the only way to add/edit providers or models; runtime code treats catalog metadata as immutable snapshots.
- Health endpoint `GET /api/v1/providers/health` aggregates adapter heartbeats, responds with cacheable 10 s payloads `{provider, region, status, latency_ms_p95, error_rate, last_heartbeat}`.
- Registry emits SSE `provider.health` ticks for operator dashboards and `LLM_CIRCUIT_STATE_CHANGE` audit events whenever state flips.
- Decision traces persist to evidence store and `ops/llm/decision_trace.jsonl`; replay tooling consumes the same format.
- Workers expose `job.update` SSE payloads with `provider_progress` fields derived from adapter snapshots and warnings (`BUDGET_HELD`, `REGION_DRIFT`).

### 3.3 API Error Codes (binding)

**Purpose:** Document the `ApiError.code` values emitted by the LLM Registry so calling services handle retries, fallbacks, and throttling consistently. **|**
**Contract:** Registry APIs reuse the platform catalog in [`Platform Runtime §3.3`](../services/platform-runtime.md#33-api-error-codes); the table below maps those codes to registry-specific scenarios. **|**
**State:** Errors surface from `/api/v1/providers/*` endpoints, Settings activation hooks, and moderation/health orchestration; schema parity maintained via `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and `tests/platform/llm/test_registry_api.py`; runtime emissions trigger `llm_registry_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards “LLM Registry – API” and “LLM Health” chart `llm_registry_api_error_total{code}`, `llm_circuit_state`; synthetic registry polls run per deploy. **|**
**Breadcrumbs:** Controllers `apps/platform/llm/views.py`, Settings activation `apps/platform/settings/services/llm.py`, moderation adapter `packages/udocket_core/llm/moderation.py`, tests `tests/platform/llm/test_registry_api.py`. **|**
**References:** Platform Runtime §3.3, Settings spec §2, Worker Cluster spec §3.4, Guardian spec §2.2, Ops runbooks `RB-LLM-CIRCUIT`, `RB-LLM-MODERATION`.

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `POLICY_BLOCK` | Residency, waiver, or moderation policy prevents provider/model activation. | Present blocking reason to operators, adjust residency/masking settings or obtain waiver before retrying activation. |
| `VALIDATION_ERROR` | Provider catalog entry failed schema, checksum, or residency coverage validation. | Fix catalog metadata (regions, digests, pricing), rerun Settings activation, and revalidate. |
| `CONFLICT` | Concurrent activation modified the same provider/version. | Refresh catalog snapshot, increment the provider version, and retry with a fresh `Idempotency-Key`. |
| `PROVIDER_DEGRADED` | Registry placed provider circuit into `OPEN`/`PAUSED_AWAITING_PROVIDER`. | Respect degraded status, shift traffic using fallback chain, and retry once health returns to CLOSED. |
| `RATE_LIMIT` | Org exceeded moderation or inference budget thresholds enforced by the registry. | Honor `Retry-After`, shed traffic, and coordinate FinOps waiver before resuming. |

______________________________________________________________________

## 4) State Management

**Purpose:** Explain storage and configuration strategy. **|**
**Contract:** Define persistence guarantees, migration expectations, and retention. **|**
**State:** Describe schemas, caches, and configuration sources. **|**
**Failures & handling:** Cover corruption, drift, and reconciliation flows. **|**
**Observability:** Metrics for storage health, cache hit rates, or config parity. **|**
**Breadcrumbs:** ORM models, migrations, infrastructure manifests. **|**
**References:** TDD appendices or diagrams related to state.

### 4.1 Reproducibility envelopes & replay strategy (binding)

**Purpose:** Allow re-execution or provider migration without ambiguity. **|**
**Contract:** Every LLM call must persist a reproducibility envelope covering prompt metadata, model details, runtime parameters, and hashes; replays obey version pins and waiver policy. **|**
**State:** Envelopes stored in evidence store tables keyed by job/artifact; manifests reference envelope IDs; Settings snapshots recorded alongside envelopes. **|**
**Failures & handling:** Missing envelopes or hash mismatches trigger `LLM_REPLAY_MISMATCH` alerts and block replays until resolved. **|**
**Observability:** Audit event `LLM_REPLAY_EXECUTED`, metrics `llm_replay_total`, replay harness logs `ops/llm/replays/<date>/`. **|**
**References:** Evidence store §2.2, Deterministic fingerprints §6.7.1 (TDD), Ops runbook RB-LLM-REPLAY.
**Breadcrumbs:** Envelope writer `packages/udocket_core/llm/evidence_store.py::store_envelope`, replay harness `ops/scripts/llm/replay.py`, tests `tests/udocket_core/llm/test_envelope.py`.

- Envelopes record `{prompt_template_id, template_version, model_id, model_version, provider, provider_region, stop_sequences, truncation_policy_version, temperature, top_p, penalties, redaction_ruleset_id, token_ceiling, settings_snapshot_sha256, input_hashes, output_hashes}`.
- Replay enforces `llm.enforce_model_version=true` to require exact model snapshots; otherwise, warnings logged and waivers link to upgraded versions.
- Replays verify schema equivalence via `content_fingerprint_sha256`; original approved output remains evidence of record.
- HIPAA mode combines `privacy.hipaa.prompt_retention_mode` with envelope hashes to support audits without storing raw prompts.
- Replay harness exercises top cases on alternate providers during exit drills and logs divergences.
- Deterministic fingerprint helper ensures Events/Entities/Facts remain stable across replays; vectors tracked via `spec/vectors/uuid_fingerprints.json`.

### 4.2 Provider matrix (informative)

**Purpose:** Provide an illustrative snapshot of approved models/regions for operational awareness (authoritative source remains Settings). **|**
**Contract:** Regions and capabilities must match Settings metadata; this table is non-normative and updated alongside catalog changes. **|**
**State:** Settings `llm.models[]` holds authoritative values; ops documentation mirrors summary tables for quick reference. **|**
**Observability:** Changes tracked through Settings activation diff artifacts and FinOps dashboards. **|**
**References:** Settings spec §2, Residency guard §2.1.1.
**Breadcrumbs:** Settings bundles `config/llm/providers/*.json`, activation diffs `ops/settings/llm_models/`, FinOps guard reports `ops/finops/mom_guard/`.

| Provider | Model ID | Regions | Max context | Notes |
| --- | --- | --- | ----------: | --- |
| azure_openai | gpt-4o-mini | na-us-1, na-us-2 | 128000 | Default Analyze/Compose profile; low latency |
| azure_openai | o3-mini | eu-west-2, eu-central-1 | 200000 | Long-context drafting; higher cost |
| azure_openai | text-embedding-3-large | ap-southeast-2 | 8192 | Embeddings for retrieval |
| byo_private | org.custom-hf/v1 | na-us-1, na-us-2 | 16000 | Bring-your-own HuggingFace Inference endpoint (evaluation digest `sha256-...`) |

Notes

- Settings `llm.models[]` define authoritative IDs/regions; waivers documented in Appendix O.
- BYO entries use `kind="byo"`; activation validators confirm evaluation digests and VPC endpoints before routing traffic.

______________________________________________________________________

## 5) Failure Modes

**Purpose:** Provide the resilience profile and default mitigations. **|**
**Contract:** Identify what must fail closed vs. degraded. **|**
**State:** Note circuit breakers, queues, or compensating transactions. **|**
**Failures & handling:** Enumerate incidents, fallback procedures, and manual runbooks. **|**
**Observability:** Alerts, dashboards, and SLOs tied to failure handling. **|**
**Breadcrumbs:** Runbooks, incident retros, chaos tests. **|**
**References:** Link to ops docs or ADRs describing failure strategy.

### 5.1 Provider degradation / circuit breaker (binding)

**Purpose:** Handle provider outages, latency spikes, or residency drift without violating SLAs. **|**
**Contract:** Circuit breakers open on threshold breach, pause jobs, emit alerts, and require RB-LLM-003 remediation before resuming. **|**
**State:** Circuit state stored in Redis/DB; jobs in `PAUSED_AWAITING_PROVIDER`; audit events logged. **|**
**Observability:** Alerts `alert_llm_circuit_open`, dashboard “LLM Residency & Failover”. **|**
**Breadcrumbs:** Runbook `ops/runbooks/settings/provider_circuit_breaker.md`, metrics `llm_circuit_state`, tests `tests/udocket_core/llm/test_registry.py::test_circuit_transitions`.

### 5.2 Moderation or safety harness failure (binding)

**Purpose:** Ensure policy violations quarantine artifacts and restore moderation capacity quickly. **|**
**Contract:** Moderation outages switch registry to fail-safe mode (block) or require documented waiver; RB-LLM-JB guides recovery. **|**
**State:** Moderation verdict logs, Guardian quarantine reasons, and audit `LLM_POLICY_BLOCK`. **|**
**Observability:** Alerts `llm_moderation_error_total`, dashboards “LLM Safety & Moderation”. **|**
**Breadcrumbs:** Runbook `ops/runbooks/llm/jailbreak_response.md`, moderation service logs.

### 5.3 FinOps budget breach (binding)

**Purpose:** Prevent uncontrolled spend and provide clear remediation. **|**
**Contract:** Budget controller pauses jobs with `FINOPS_BUDGET_HELD`; overrides require dual approval; RB-LLM-FINOPS outlines steps. **|**
**State:** Jobs flagged `PAUSED_AWAITING_BUDGET`, audit events `FINOPS_BUDGET_HELD`. **|**
**Observability:** Metrics `finops_budget_hold_active_total`, `finops_budget_hold_duration_seconds`. **|**
**Breadcrumbs:** Runbook `ops/runbooks/finops/llm_budget_hold.md`, tests `tests/udocket_core/finops/test_guard.py`.

### 5.4 Replay divergence (normative)

**Purpose:** Surface divergences between original outputs and replay results. **|**
**Contract:** Divergence triggers `LLM_REPLAY_MISMATCH`, requires review, and documents outcome per RB-LLM-REPLAY. **|**
**State:** Replay logs `ops/llm/replays/<date>/`, audit `LLM_REPLAY_MISMATCH`. **|**
**Observability:** Replay harness summary metrics `llm_replay_divergence_total`. **|**
**Breadcrumbs:** Runbook `ops/runbooks/llm/replay_divergence.md`.

______________________________________________________________________

## 6) Observability

**Purpose:** Keep registry health, safety, and cost posture visible and alertable. **|**
**Contract:** Maintain Grafana dashboards for residency/failover, moderation, and FinOps; uphold SLOs (provider health ≥ 99.5 %, moderation pipeline availability ≥ 99.9 %, budget controller response < 5 minutes). **|**
**State:** Prometheus metrics (`llm_circuit_state`, `llm_region_fallback_total`, `llm_content_flagged_total`, `llm_moderation_latency_seconds`, `llm_cost_estimate_total`, `finops_budget_hold_active_total`, `finops_mom_regression_flag`), SSE streams, and audit events feed dashboards. **|**
**Failures & handling:** Missing metrics or stale dashboards block releases until Observability sign-off; docs lint validates references. **|**
**Observability:** Dashboards “LLM Residency & Failover”, “LLM Safety & Moderation”, “FinOps – LLM Cost & Circuit”; Alertmanager routes `alert_llm_circuit_open`, `llm_moderation_error_total`, `finops_deploy_gate_failed_total`. **|**
**Breadcrumbs:** Dashboard configs `infra/observability/dashboards/llm_residency.json`, `llm_safety.json`, `finops_llm.json`; alert rules `infra/monitoring/llm-prometheus-rules.yaml`. **|**
**References:** TDD §12 Observability dashboards, TDD §8.7 FinOps guard.

- Cost dashboards surface `llm_cost_estimate_total`, `finops_cost_per_case_usd`, MoM regression panels, top N expensive cases, budget forecasts, and logging volume views (`logging_bytes_ingested_total`, budget vs actual per service).
- Alerts cover regression > threshold (default 10 %), monthly cap risk, cost forecast drift, and sustained logging budget overages; all alerts route to Product/SRE with runbook IDs (`RB-LLM-FINOPS`, `RB-LOG-007`).
- Metrics to watch: `llm_cost_estimate_total{org,case,job,model}`, `finops_cost_per_case_usd{org,case}`, `finops_cost_per_org_usd{org,month}`, `finops_mom_regression_flag{org}`, `delivery_events_total{org,channel,status}`. Budget overrides update `llm.finops.override_until` so dashboards annotate active bypass windows.
- Acceptance: dashboards and alerts must pass staging drills prior to promotion; drills replay budget breaches and log alerts in `ops/finops/mom_guard/`.

### 6.1 SLOs & Targets (binding)

**Purpose:** Capture provider availability, moderation responsiveness, FinOps guardrails, and residency enforcement obligations. **|**
**Contract:** Provider circuits, moderation pipelines, budget controllers, and residency policy checks must stay within the thresholds below before traffic continues. **|**
**State:** Metrics `llm_circuit_state`, `llm_region_fallback_total`, `llm_moderation_latency_seconds`, `llm_cost_estimate_total`, `finops_mom_regression_flag`, `provider_data_policy_drift_total`; dashboards “LLM Residency & Failover”, “LLM Safety & Moderation”, “FinOps – LLM Cost & Circuit”. **|**
**Failures & handling:** Breaches invoke RB-LLM-CIRCUIT, RB-LLM-MODERATION, or RB-LLM-FINOPS prior to resuming provider usage. **|**
**Observability:** Grafana SLO dashboards, Alertmanager routes (`alert_llm_circuit_open`, `llm_moderation_error_total`, `finops_deploy_gate_failed_total`), and synthetic failover drills provide evidence. **|**
**Breadcrumbs:** Monitoring configs `infra/monitoring/llm-prometheus-rules.yaml`, dashboards `infra/observability/dashboards/llm_*.json`, runbooks `docs/src/ops/runbooks/llm/*.md`. **|**
**References:** TDD §8, Settings spec §7.3, Logging spec §6.

- **Provider health:** Each active provider maintains ≥99.5% availability (`llm_circuit_state == "CLOSED"` and `llm_region_fallback_total` within waiver tolerances). Circuit opens trigger RB-LLM-CIRCUIT and suspend new assignments.
- **Moderation latency:** Automated moderation pipeline availability ≥99.9% with P95 latency ≤ 3 seconds (`llm_moderation_latency_seconds`); breaches page RB-LLM-MODERATION and block risky channels until remedied.
- **Cost guardrails:** Deploy gate budgets enforce `finops_mom_regression_flag = 0` and `finops_deploy_gate_failed_total = 0`; breaches require RB-LLM-FINOPS and leadership approval before continuing.
- **Residency enforcement:** `provider_data_policy_drift_total` and `llm_policy_block_total` remain zero sustained; any drift escalates to Security and blocks provider selection.

______________________________________________________________________

## 7) Security & Compliance

**Purpose:** Ensure LLM operations honor residency, privacy, and contractual data-use constraints. **|**
**Contract:** Providers must operate in approved regions, disable training/log retention, and satisfy HIPAA/PHIPA requirements; waivers documented with expiry and remediation. **|**
**State:** Settings capture provider toggles (`log_retention=false`, `train_on_data=false`), residency allowlists, HIPAA prompt retention modes; waivers stored in `ops/security/waivers/`. **|**
**Failures & handling:** Provider policy drift, HIPAA violations, or prompt retention misconfigurations trigger Security incidents and RB-LLM-COMPLIANCE. **|**
**Observability:** Alerts `provider_data_policy_drift_total`, `llm_policy_block_total`, `hipaa_prompt_retention_violation_total`; audit events `LLM_POLICY_BLOCK`, `HIPAA_EXCERPT_BLOCK`. **|**
**Breadcrumbs:** Security guard `packages/udocket_core/llm/policy_guard.py`, HIPAA purge script `scripts/privacy/purge_evidence_store.py`, tests `tests/udocket_core/llm/test_policy_guard.py`. **|**
**References:** TDD §12 (security policies), Guardian spec §5, Appendix O (waivers).

- Providers must operate in residency-approved regions (enforced via §2.1.1) and disable prompt retention/training per contract.
- HIPAA environments require prompt retention mode settings and evidence store redaction; downgrades require `FIPS_MODE_EXCEPTION`/`HIPAA_PROMPT_EXCEPTION` waivers with ≤7 day expiry.
- Golden-set fairness and bias evaluations feed compliance reporting; results archived in `ops/security/provider_audits/`.
- LLM envelopes include waiver IDs and data-use posture for audit; Guardian exposes same metadata in reviewer consoles.

______________________________________________________________________

## 8) Operational Notes

**Purpose:** Keep the LLM registry’s operational posture, failover drills, and release gates aligned with safety and cost guardrails. **|**
**Contract:** On-call rotations, runbooks, and gating evidence must stay current; registry traffic pauses when residency, moderation, or FinOps alerts breach thresholds until remediation completes. **|**
**State:** Runbooks under `ops/runbooks/llm/`, drill calendar `ops/change/llm_rotations.ics`, release checklists `ops/releases/llm_release_checklist.md`, waiver records in App.O. **|**
**Failures & handling:** Stale runbooks, missed drills, or incomplete release evidence block deployment until refreshed. **|**
**Observability:** Docs lint (`build_runbook_catalog.py --check`), dashboards “LLM Residency & Failover” / “LLM Safety & Moderation” / “FinOps – LLM Cost & Circuit”, alerts `alert_llm_circuit_open`, `llm_moderation_error_total`, `finops_budget_hold_active_total`. **|**
**Breadcrumbs:** Runbook catalog `docs/src/ops/runbooks.md`, automation scripts `ops/scripts/llm/*.py`, release tooling `scripts/finops/check_mom_guard.py`. **|**
**References:** §5 Failure modes, §6 Observability, §7 Security & compliance.

### 8.1 Operational Posture (binding)

**Purpose:** Capture staffing, freeze windows, and readiness expectations for the registry. **|**
**Contract:** Platform Architecture and Applied AI Programs share PagerDuty “LLM Registry SLO”, maintain blue/green deployment freezes during provider onboarding, and staff a weekly rotation to review parity evidence and golden-set results. **|**
**State:** Roster `ops/llm/roster.yaml`, freeze calendar `ops/change/llm_freeze_windows.ics`, parity evidence logs `ops/security/provider_audits/`. **|**
**Failures & handling:** Missing parity evidence or unstaffed shifts trigger incident review; registry remains locked in fail-safe mode until posture restored. **|**
**Observability:** PagerDuty analytics, dashboards “LLM Residency & Failover”, alert `llm_circuit_state{state="open"}`. **|**
**Breadcrumbs:** Roster files, freeze calendars, App.O decision logs, provider audit archives. **|**
**References:** §2 Responsibilities, §6 Observability, `RB-LLM-003`.

- Weekly parity review confirms fallback chains still meet quality, residency, and cost targets; failures open waivers and block new activations.
- Golden-set jailbreak runs monitored daily; regressions halt releases until RB-LLM-JB completes.
- FinOps budget dashboards reviewed alongside `finops_budget_hold_active_total`; overrides require App.O approval before resuming jobs.

### 8.2 Incident Triggers (binding)

**Purpose:** Map alerts and dashboards to registry runbooks. **|**
**Contract:** Alert rules (`infra/monitoring/llm-prometheus-rules.yaml`) annotate `RB-LLM-\*` identifiers; responders capture evidence before clearing incidents. **|**
**State:** Incident records `ops/llm/incidents/<date>.jsonl` store alert context, provider metadata, and waiver references. **|**
**Failures & handling:** Missing annotations or suppressed routes require corrective PRs and governance review. **|**
**Observability:** Dashboards “LLM Residency & Failover”, “LLM Safety & Moderation”, “FinOps – LLM Cost & Circuit”, synthetic replay jobs. **|**
**Breadcrumbs:** Alert rule files, PagerDuty service “LLM Registry SLO”, SIEM integrations. **|**
**References:** §5 Failure modes, `RB-LLM-003`, `RB-LLM-JB`, `RB-LLM-FINOPS`, `RB-LLM-REPLAY`.

- `alert_llm_circuit_open` / `llm_region_fallback_total` spikes invoke `RB-LLM-003` for provider failover.
- `llm_moderation_error_total` / `llm_content_flagged_total` spikes activate `RB-LLM-JB`.
- `finops_budget_hold_active_total` or `llm_cost_estimate_total` projections breaching guard thresholds execute `RB-LLM-FINOPS`.
- Replay mismatches (`llm_replay_mismatch_total`) trigger `RB-LLM-REPLAY` for divergence analysis.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Keep LLM runbooks actionable and drills on cadence. **|**
**Contract:** Alerts map to `RB-LLM-\*` runbooks; quarterly drills cover provider failover, moderation outage, FinOps budget breach, and replay divergence scenarios. **|**
**State:** Runbooks `ops/runbooks/llm/*.md`, drill evidence `ops/llm/drills/<date>/summary.md`, waiver logs in App.O. **|**
**Failures & handling:** Missing evidence or outdated steps block release sign-off until updated. **|**
**Observability:** Docs lint, drill calendar `ops/change/llm_rotations.ics`, Ops governance dashboards. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler, automation scripts. **|**
**References:** `RB-LLM-003`, `RB-LLM-JB`, `RB-LLM-FINOPS`, `RB-LLM-REPLAY`.

#### 8.3.1 Runbook Index (informative)

| Runbook code | Scenario | Notes |
| --- | --- | --- |
| `RB-LLM-003` | Provider degradation / residency drift | Executes failover validation and waiver workflow |
| `RB-LLM-JB` | Moderation or jailbreak regression | Locks registry in safe mode, reruns golden set, coordinates with Guardian |
| `RB-LLM-FINOPS` | Budget hold or cost breach | Pauses jobs, coordinates overrides with FinOps and App.O |
| `RB-LLM-REPLAY` | Replay divergence | Replays envelopes, compares hashes, and documents drift |

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Document operational playbooks for the registry so responders act consistently during incidents. **|**
**Contract:** Each runbook maps to specific alerts, evidence requirements, and owning teams; responders update them after every drill or incident. **|**
**State:** Runbook markdown lives in `ops/runbooks/llm/`, automation scripts under `ops/scripts/llm/`, and evidence within incident records `ops/llm/incidents/`. **|**
**Failures & handling:** Missing steps or stale guidance block deployment sign-off until refreshed. **|**
**Observability:** Docs lint, PagerDuty analytics, and Ops governance dashboards track runbook freshness and drill completion. **|**
**Breadcrumbs:** `ops/runbooks/llm/*.md`, `ops/scripts/llm/*.py`, incident templates `ops/llm/incidents/*.md`. **|**
**References:** Alert catalog, FinOps policy, Guardian integration docs.

- `RB-LLM-003` — Validates provider failover chains, residency attestations, and waiver approvals before resuming traffic.
- `RB-LLM-JB` — Investigates moderation regressions, reruns golden set, and coordinates Guardian enforcement.
- `RB-LLM-FINOPS` — Evaluates budget guardrails, pauses costly workloads, and secures FinOps/App.O overrides.
- `RB-LLM-REPLAY` — Replays envelopes, compares hashes, and files follow-up tasks for divergence remediation.

#### 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover provider failover, moderation outage, FinOps budget breach, and replay divergence with evidence in `ops/llm/drills/<date>/summary.md`.
- Drill calendar `ops/change/llm_rotations.ics` tracks cadence and ownership; missed drills block release sign-off until evidence captured.
- Docs lint and Ops governance dashboards verify runbook freshness and evidence uploads prior to production changes.

### 8.4 Migrations & Backfills (normative)

**Purpose:** Govern provider onboarding, parity evidence refresh, and replay migrations. **|**
**Contract:** Provider additions require parity evidence, evaluation digests, and residency attestations before activation; replay migrations run in staging with manifest comparisons before production. **|**
**State:** Provider manifests `config/llm/providers/*.json`, parity evidence `ops/security/provider_audits/`, replay logs `ops/llm/replays/<date>/`. **|**
**Failures & handling:** Missing evidence or residency attestations block activation; replay mismatches escalate via `RB-LLM-REPLAY`. **|**
**Observability:** Metrics `llm_provider_activation_total`, `llm_replay_divergence_total`, CI parity tests. **|**
**Breadcrumbs:** Provider onboarding scripts `ops/scripts/llm/onboard_provider.py`, parity verification tooling `scripts/ci/golden_set_jailbreak.sh`. **|**
**References:** §2 Responsibilities, §4 State management, Settings spec §5.

- Provider migrations follow change tickets with parity evidence hash (`fallback.evidence_sha256`) and residency attestations.
- Replay migrations compare envelope hashes and content fingerprints before promoting new defaults.
- Decommissioned providers archive evidence and update waiver logs in App.O.

### 8.5 Operational Workflows (normative)

**Purpose:** Document recurring tasks that sustain registry readiness. **|**
**Contract:** Teams review golden-set results daily, audit parity evidence weekly, refresh moderation thresholds, and reconcile FinOps guard reports. **|**
**State:** Golden-set reports `ops/security/provider_audits/<date>/`, moderation logs `ops/llm/moderation/<date>.json`, FinOps reports `ops/finops/mom_guard/<release>.json`. **|**
**Failures & handling:** Missed audits trigger `RB-LLM-JB` or `RB-LLM-FINOPS` follow-up; stale parity evidence blocks provider activation. **|**
**Observability:** Metrics `llm_content_flagged_total`, `finops_mom_regression_flag`, dashboards “LLM Safety & Moderation”, “FinOps – LLM Cost & Circuit”. **|**
**Breadcrumbs:** Audit scripts `ops/scripts/llm/run_golden_set.py`, moderation tuning playbooks, FinOps guard tooling. **|**
**References:** §5 Failure modes, §4 State management, Notifications spec §2.3 (alert fan-out).

- Daily golden-set jobs review jailbreak, safety, and fairness results; failures halt releases pending remediation.
- Weekly parity review ensures fallback chains still meet quality/residency/cost criteria; evidence hashed and archived.
- FinOps guard reports reviewed alongside override tickets; overrides expire automatically and require re-approval.

______________________________________________________________________

## 9) Dependencies

**Purpose:** Map upstream inputs and downstream consumers. **|**
**Contract:** Settings publishes provider catalogs and guardrails; LPE embeds residency context; Guardian enforces moderation/quarantine; Compose/Analyze agents consume selections; FinOps monitors spend. **|**
**State:** Adoption telemetry (`llm_provider_adoption_seconds`), PolicyContext digests, Guardian manifests, FinOps reports, and evidence envelopes prove alignment. **|**
**Failures & handling:** Settings drift or Guardian integration failures trigger RB-LLM-003 and Guardian runbooks; FinOps overrides require documented App.O approval. **|**
**Observability:** Dashboards “LLM Residency & Failover”, “Guardian Residency Enforcement”, “FinOps – LLM Cost & Circuit”. **|**
**Breadcrumbs:** Integration code `packages/udocket_core/llm/interfaces.py`, LPE PolicyContext `packages/udocket_core/lpe/policy_context.py`, Guardian bridge `packages/udocket_core/guardian/llm_bridge.py`. **|**
**References:** Link to other service docs or appendices.

| Dependency | Interface / artifact | Responsibilities | Notes |
| --- | --- | --- | --- |
| Settings Registry | Activation bundles (`llm.providers[]`, `llm.models[]`, `llm.moderation.*`, `llm.finops.*`) | Supplies catalog metadata, moderation configs, FinOps thresholds | Unsafe diffs block activation; diff artifacts stored with release checklist |
| LPE | PolicyContext residency hints, waiver metadata | Provides residency/compliance context consumed by registry guards | Digests embedded in decision traces and evidence envelopes |
| Guardian | Moderation verdicts, quarantine reasons | Blocks promotion when safety violations occur; records reviewer context | Quarantine reasons surface in reviewer UI and audit history |
| Compose/Analyze | Agent runtimes, LangGraph lanes | Invoke registry for model selection, rely on envelopes for reproducibility | Agents must pass `retry_token`/`envelope_id` for replays |
| FinOps | Budget controller, dashboards | Monitors spend, enforces overrides | Overrides logged via App.O and release checklist |

______________________________________________________________________

## 10) References

- Provider circuit runbook — `ops/runbooks/settings/provider_circuit_breaker.md` (RB-LLM-003).
- Jailbreak / moderation response — `ops/runbooks/llm/jailbreak_response.md` (RB-LLM-JB).
- FinOps budget hold runbook — `ops/runbooks/finops/llm_budget_hold.md` (RB-LLM-FINOPS).
- Replay divergence runbook — `ops/runbooks/llm/replay_divergence.md` (RB-LLM-REPLAY).
- Golden-set jailbreak pipeline — `scripts/ci/golden_set_jailbreak.sh`.
- FinOps deploy guard — `scripts/finops/check_mom_guard.py`.
- Evidence store tooling — `ops/scripts/llm/replay.py`, `packages/udocket_core/llm/evidence_store.py`.
- Monitoring dashboards — `infra/observability/dashboards/llm_residency.json`, `llm_safety.json`, `finops_llm.json`.
