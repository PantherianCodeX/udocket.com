---
title: uDocket — Settings Registry Technical Design
subtitle: Configuration Governance & Activation Specification
author:
  - uDocket Platform Architecture Team
  - Settings Program Leads
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Architecture
  - Security Engineering
  - Settings Program
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
  - <header class="page-header">uDocket — Settings Registry Technical Design 
    <br> Configuration Governance & Activation Specification</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page 
    <span class="page-number"></span> of <span 
    class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | uDocket Platform Architecture Team; Settings Program Leads |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Architecture; Security Engineering; Settings Program |
| Reviewers | QA Engineering Lead; SRE Manager |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Service charter, hierarchical model, API/SDK contracts, activation workflow, governance controls, integrations, telemetry, and key catalog for the Settings Registry.
- **Structure:** Numbered sections limited to three levels of depth; appendices surface detailed key maps, metrics, and seed bundle references.
- **Cross-references:** Use `§<number>` for this document, `TDD §<number>` for the platform TDD, and `App.<letter>` when pointing at appendices.
- **Maintenance:** Run `python -m doc_tools.manage_docs --lint` before submitting edits. Schema snippets must match `spec/schemas/*` fixtures; CI enforces parity for key catalogs and activation templates.
- **Doc change protocol:** Any PR modifying SR APIs, activation logic, bundle schemas, or governance gates must update this document and cite relevant ADRs. Architecture/Security reviewers block merges when code, SDKs, or docs diverge.

______________________________________________________________________

## 1) Purpose

**Purpose:** Establish the Settings Registry (SR) as the canonical configuration service for every platform scope. **|**
**Contract:** SR centralizes system, organization, and case configuration, publishes audited activations, and emits immutable snapshots that downstream services must embed and honor. **|**
**State:** Configuration persists in Postgres tables (`setting_bundle`, `setting_bundle_version`, `setting_activation`) with Redis caches keyed by `(scope, org_id, case_id, bundle_id)`; adoption status lives in `settings_consumer_adoption`. **|**
**Failures & handling:** Validator failures or long-held advisory locks force SR into read-only mode; consumers rely on embedded snapshots until remediation (see §5). **|**
**Observability:** Availability SLO 99.9%, metrics `settings_request_total`, `settings_error_total`, and `settings_activation_total{result}` feed the “Settings Registry – Availability” dashboard; traces annotate `settings_version` and `activation_id`. **|**
**Breadcrumbs:** Implementation `apps/platform/settings/service.py::create_app`, Tests `tests/platform/settings/test_charter.py::test_scope_enforced`, Grafana “Settings Registry – Availability”. **|**
**References:** §2 Responsibilities, §3 API contract, §4 State management, §6 Observability, ADR-0002, ADR-0003.

- SR governs configuration inheritance, residency allowlists, FinOps ceilings, LLM profiles, Guardian/Signer guards, and UI feature flags.
- Lifecycle changes flow through ADRs; structural edits require dual Architecture/Security approval.
- Downstream systems must cite snapshot digests in manifests, telemetry, and audit logs to preserve reproducibility.

### 1.1 Charter & mandate (binding)

**Purpose:** Detail the charter that defines SR’s scope and success criteria. **|**
**Contract:** SR owns configuration authoring, validation, activation, and distribution across all scopes; it guarantees determinism and traceable history for every activation. **|**
**State:** Bundles, versions, activations, and advisory lock records reside in Postgres; caches mirror effective configuration for hot reads. **|**
**Failures & handling:** Unsafe activations drop SR into read-only mode until validators pass; existing jobs continue with embedded snapshots. **|**
**Observability:** Request/error counters, activation metrics, and traces capture throughput and failure reasons. **|**
**References:** §2 Responsibilities, §4 State management, Appendix A.
**Breadcrumbs:** Service bootstrap `apps/platform/settings/service.py`, schema `packages/udocket_core/settings/schema.py`, tests `tests/platform/settings/test_charter.py`.

- Governs inheritance rules, scope guardrails, and immutable keys (for example residency) that lower scopes cannot relax.
- Maintains dual-track lifecycle (draft → reviewed → activated) mirrored in ADR status.
- Publishes change events (`settings.changed`, `settings.snapshot_issued`) for consumers.

### 1.2 Stakeholders & integrations (normative)

**Purpose:** Identify SR’s consumers and integration touchpoints. **|**
**Contract:** Guardian, LPE, Reference Manager, Portal, Workers, Ops tooling, and Observability must fetch snapshots, record digests, and respect invalidation events before mutating state. **|**
**State:** Adoption telemetry in `settings_consumer_adoption` tracks bundle/version uptake; integration sync jobs persist status in `settings_integration_status`. **|**
**Failures & handling:** Missed invalidations trigger drift detectors and synthetic fetches; consumers block risky operations until snapshots refresh. **|**
**Observability:** “Settings Registry – Consumer Adoption” dashboard charts `settings_snapshot_issued_total`, `settings_snapshot_stale_total`, and invalidation latency. **|**
**References:** §2 Responsibilities, §6 Dependencies, Appendix B.
**Breadcrumbs:** Client library `apps/platform/settings/clients.py`, adoption jobs `apps/platform/settings/tasks.py`, tests `tests/platform/settings/test_client_contract.py`.

- Guardian enforces judgment flows using SR-configured policies and waivers.
- LPE activation dry-runs invoke SR validators to ensure residency/localization coherence.
- Workers embed `settings_snapshot_sha256` and `settings_version_id` in manifests and telemetry.
- Portal and staff UI honor SR toggles for feature availability, localization hints, and approval flows.

### 1.3 Service-level objectives (binding)

**Purpose:** Capture SR’s reliability targets and deployment guardrails. **|**
**Contract:** Maintain 99.9 % availability, read p95 latency ≤ 120 ms, activation completion p95 ≤ 2 minutes, and cache invalidation propagation ≤ 60 seconds; exceeding burn-rate thresholds freezes activations. **|**
**State:** Error budget tracking persists in `sre_error_budget` with monthly burn-rate snapshots; release gates consult these metrics. **|**
**Failures & handling:** Burn rate > 1.0 for 60 minutes halts blue/green promotion; SLO breaches invoke RB-GOV-008 (§8.3). **|**
**Observability:** Synthetic monitors exercise read and activation APIs per deploy; alerts `settings_availability_breach` and `settings_activation_delay` gate releases. **|**
**References:** §6 Observability, Appendix B, §8.3.
**Breadcrumbs:** Helm chart `infra/kubernetes/settings/`, SLO tests `tests/synthetics/test_settings_slo.py`, Grafana “Settings Registry – SLO”.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Describe the functional areas SR owns—from scope resolution through agent configuration—so teams understand what lives inside the registry. **|**
**Contract:** SR defines schemas, validates inputs, manages precedence, and publishes bundles for services, agents, and UI surfaces while enforcing governance and residency guardrails. **|**
**State:** Definitions, bundles, and effective values live in Postgres (`setting_definition_schema`, `setting_bundle`, `setting_effective`) with companion JSON artifacts under `config/` and `ops/settings/`. **|**
**Failures & handling:** Invalid overrides, unknown keys, or failed validators reject activations and block dependent workflows until corrected (see §5). **|**
**Observability:** Scope mix, validation failure, and bundle adoption metrics feed “Settings – Scope Mix” and “Settings – Validation” dashboards. **|**
**Breadcrumbs:** Models `apps/platform/settings/models.py`, schema `packages/udocket_core/settings/schema.py`, governance services `apps/platform/settings/services/`. **|**
**References:** §3 API contract, §4 State management, Appendix A, Appendix C.

### 2.1 Hierarchical scopes & precedence (binding)

**Purpose:** Explain how configuration inherits and overrides safely across tenants. **|**
**Contract:** SR resolves effective configuration by overlaying CASE over ORG over SYSTEM scopes with explicit precedence, immutable keys, and validator-enforced guardrails. **|**
**State:** Effective values materialize into `setting_effective` with foreign keys to contributing bundle versions; ancestry is persisted for audit drill-down. **|**
**Failures & handling:** Invalid overrides (for example, CASE relaxing residency) raise `SETTINGS_INVALID_OVERRIDE`; activations fail until corrected. **|**
**Observability:** Metric `settings_scope_resolution_total` tracks override mix; traces include contributing scope chains. **|**
**References:** Appendix A key catalog, §4 State management.
**Breadcrumbs:** Implementation `apps/platform/settings/models.py::Scope`, tests `tests/platform/settings/test_scope_precedence.py`.

- Sensitive keys (secrets, trust roots) remain encrypted at rest; read APIs redact secrets while activation history retains digests.
- Bundles include schema metadata referencing Appendix A for key catalog and defaults.
- Certain keys enforce immutability at lower scopes (residency, immutable logging sinks) and rely on validator guardrails.

### 2.2 Definition schema & validation (binding)

**Purpose:** Define the schema that enforces data types, constraints, and documentation for settings keys. **|**
**Contract:** All definitions use the shared `SettingDefinition` model with literal datatypes, scope guards, default values, documentation strings, and validator hooks; CI checks block unknown or malformed keys. **|**
**State:** Definitions load from `config/settings_definitions.json` and compile into versioned JSON Schema artifacts stored in `setting_definition_schema`. **|**
**Failures & handling:** Missing or malformed definitions fail `python -m doc_tools.check_settings_keys` and production activations; authors must update schema before merging. **|**
**Observability:** Metric `settings_validation_failure_total` categorizes error reasons; audit logs attach schema version IDs. **|**
**References:** Appendix A key catalog, Appendix C seed bundles.
**Breadcrumbs:** Schema implementation `packages/udocket_core/settings/schema.py`, tests `tests/platform/settings/test_definition_schema.py`.

- Case-scoped keys include agent prompt overrides, retry ceilings, visibility toggles, and portal expiry limits.
- System/org keys cover residency allowlists, quotas, notifications, TLS policy, encryption posture, FinOps thresholds, and enumerations for cases and artifacts.
- Privacy helpers publish templates via `/api/v1/settings/privacy/templates`, ensuring DPIA/RoPA tooling aligns with Appendix C (platform TDD).

### 2.3 Snapshot & manifest contract (binding)

**Purpose:** Ensure downstream services embed immutable configuration context. **|**
**Contract:** Snapshots include `{version_id, bundle_ids[], contributing_scopes[], sha256}`; consumers persist digests in manifests, telemetry, and audit logs to guarantee reproducibility. **|**
**State:** Snapshot records reside in `settings_snapshot` and attach to jobs, artifacts, and policy contexts via foreign keys; digests mirror compiled outputs. **|**
**Failures & handling:** Snapshot mismatches trigger drift incidents; workers block new jobs until refreshed snapshots arrive or incidents are resolved. **|**
**Observability:** Dashboard “Settings – Snapshot Integrity” tracks `settings_snapshot_mismatch_total` and `settings_snapshot_stale_total`. **|**
**References:** §4 State management, Appendix B metrics.
**Breadcrumbs:** Implementation `packages/udocket_core/settings/snapshot.py`, tests `tests/platform/settings/test_snapshot_contract.py`.

- Every job manifest includes `settings_snapshot_sha256` and `settings_version_id` for replay.
- Guardian, Portal, and Workers log snapshot digests within structured events for traceability.

### 2.4 Residency & egress controls (binding)

**Purpose:** Capture residency, egress, and waiver rules enforced by SR. **|**
**Contract:** SR validates `regions.allowlist.*`, `network.egress.allowed_hosts`, and residency waivers against Reference Manager catalogues prior to activation; unsafe changes require dual approval and manifest stamping. **|**
**State:** Residency metadata persists in `settings_residency_profile` cross-linked to RM bundles and waiver records. **|**
**Failures & handling:** Missing catalog entries raise `RESIDENCY_ENDPOINT_NEW`; activations stay blocked until RM ingestion completes or waiver approved. **|**
**Observability:** Audit events `RESIDENCY_ENDPOINT_NEW`, metric `settings_residency_violation_total`, and nightly drift scans enforce compliance. **|**
**References:** §7 Security & compliance, §8.3.3–§8.3.4 RB-RES-\* runbooks.
**Breadcrumbs:** Validators `apps/platform/settings/validators/residency.py`, tests `tests/platform/settings/test_residency_validators.py`.

- Change detection opens Security tickets (`SEC-RESIDENCY-ENDPOINT`) and requires dual approval for temporary waivers.
- Closure requires two consecutive compliant scans before incidents resolve; evidence attaches to decision log entries.

### 2.5 Pipeline bundles & staged overrides (binding)

**Purpose:** Externalize LangGraph pipeline composition, prompts, and ceilings into audited configuration. **|**
**Contract:** Keys `agents.pipeline.definitions[]`, `agents.pipeline.assignments[]`, `agents.pipeline.overrides[]`, `agents.prompts.*`, and `agents.llm_profiles.*` define pipeline manifests, assignments, overrides, prompts, and LLM profiles with validator-enforced bounds. **|**
**State:** Pipeline definitions live in `settings_pipeline_definition`; rollouts track in `settings_pipeline_rollout` with wave metadata and change tickets. **|**
**Failures & handling:** Invalid prompt references, tool IDs, or ceiling relaxations raise validation errors; activations remain blocked until corrected. **|**
**Observability:** “Agent Pipeline Rollouts” dashboard charts rollout state, prompt revisions, and cost ceilings; job telemetry logs `pipeline_definition_version`. **|**
**References:** Appendix C seed bundles, §4 State management.
**Breadcrumbs:** Implementation `apps/platform/settings/services/pipeline_bundle.py`, tests `tests/platform/settings/test_pipeline_bundle.py`.

- Assistant knobs (`assistant.retrieval.sources[]`, `assistant.moderation.tiers[]`, `assistant.citation.style`) share validator framework ensuring alignment with shared assets.
- Activations altering definitions or rollouts tag `change_class="system"`, require change ticket linkage, and follow blue/green rollout gates.

### 2.6 Tool catalog & capability gating (binding)

**Purpose:** Govern LangGraph tool introduction and exposure per tenant. **|**
**Contract:** Keys `agents.tools.catalog[]`, `agents.tools.allowlist[]`, and `agents.tools.policies.*` register tools, expose allowlists, and enforce residency/classification ceilings; overrides require dual approval. **|**
**State:** Catalog entries persist in `settings_tool_catalog`; allowlists live in `settings_tool_allowlist` per scope with waiver metadata. **|**
**Failures & handling:** Schema mismatches or attempts to widen residency/cost ceilings raise validation errors; forced overrides demand waiver records. **|**
**Observability:** “Agent Tooling” panel tracks invocation counts, error rates, and cost estimates; audit logs live under `ops/tools/ops_tools.jsonl`. **|**
**References:** §6 Dependencies, Appendix A tool catalog.
**Breadcrumbs:** Catalog sync `apps/platform/settings/services/tool_catalog.py`, tests `tests/platform/settings/test_tool_catalog.py`.

- `GET /api/v1/settings/tools/catalog` returns effective catalog JSON for operators and editors.

### 2.7 LLM profiles & moderation controls (normative)

**Purpose:** Manage provider catalogs, version pins, moderation thresholds, and BYO vetting. **|**
**Contract:** Keys `llm.providers[]`, `llm.models[]`, `llm.models.version_pin`, `llm.enforce_model_version`, `llm.moderation.*`, and `llm.byo.*` define provider usage and compliance requirements; BYO entries demand validated evaluation suites. **|**
**State:** Provider/model metadata resides in `settings_llm_profile`; BYO endpoints cross-reference Reference Manager catalogs and residency policies. **|**
**Failures & handling:** Version drift or missing evaluation IDs block activations; moderation thresholds outside guardrails require waiver review. **|**
**Observability:** “LLM Profile Adoption” dashboard tracks `llm_profile_assignment_total`, moderation enforcement, and BYO utilization. **|**
**References:** §6 Dependencies, Appendix C seed bundles.
**Breadcrumbs:** Implementation `apps/platform/settings/services/llm_profiles.py`, tests `tests/platform/settings/test_llm_profiles.py`.

### 2.8 Seed bundles & no-code configuration (binding)

**Purpose:** Enable environment bootstrap without code changes using validated JSON bundles. **|**
**Contract:** Repo ships versioned seed bundles ingested through SR with identical validators to runtime activation; operators edit JSON, run validators, and activate bundles through the standard pipeline. **|**
**State:** Seeds live under `config/` with metadata `{version, source_commit, checksum}`; ingestion records persist in `settings_seed_history`. **|**
**Failures & handling:** Seeds referencing unknown keys or out-of-range values fail validation; CI (`settings-seed-validate`) blocks merges until corrected. **|**
**Observability:** CI artifacts capture validation reports; deployment automation logs ingestion status and checksum verification. **|**
**References:** Appendix C seed inventory, §4 Activation pipeline.
**Breadcrumbs:** Bootstrap script `ops/scripts/bootstrap_platform.py`, tests `tests/platform/settings/test_seed_bundles.py`.

______________________________________________________________________

## 3) API Contract

**Purpose:** Document SR’s programmatic interfaces and client expectations for distributing configuration. **|**
**Contract:** REST APIs, SDK helpers, and signing requirements deliver configuration with immutable version metadata and deterministic idempotency rules. **|**
**State:** OpenAPI definitions live in `ops/openapi/settings.openapi.yaml`; SDKs wrap REST endpoints with caching and snapshot persistence. **|**
**Failures & handling:** Signature mismatches, stale caches, or idempotency conflicts return explicit errors and require client remediation. **|**
**Observability:** “Settings API”, “Settings Client Cache”, and “Settings Auth” dashboards monitor traffic, cache hit ratio, and auth errors. **|**
**Breadcrumbs:** API implementation `apps/platform/settings/api.py`, client `packages/udocket_core/settings/client.py`, security helpers `apps/platform/settings/security.py`. **|**
**References:** §2 Responsibilities, §4 State management, Appendix A key catalog.

### 3.1 External Interfaces (binding)

- `/api/v1/settings/privacy/templates` surfaces DPIA/RoPA metadata keyed by matrix version.
- Read APIs respect `If-None-Match` ETags based on snapshot hash to reduce load.

### 3.2 Internal Interfaces (normative)

- Clients avoid `.env` usage beyond bootstrapping; runtime relies on SR for truth.
- SDK exports helpers for dry-run validation and diff preview consumption.

### 3.3 API Error Codes (binding) {#3-3-api-error-codes-binding}

**Purpose:** Enumerate Settings-specific `ApiError.code` values so platform consumers can build deterministic retry logic. **|**
**Contract:** Settings Registry reuses the platform catalog in [`Platform Runtime §3.3`](../platform/runtime.md#33-api-error-codes) and supplements it with the service-specific codes below. Mutating endpoints surface the same envelope schema and echo `Idempotency-Key` when supplied. **|**
**State:** Codes map directly to validation branches in `apps/platform/settings/api.py` and activation services. **|**
**Failures & handling:** Unknown codes fail Spectral lint and contract tests; runtime mis-emissions trigger `settings_error_unknown_total` alerts. **|**
**Observability:** Metrics `settings_error_total{code}` and `settings_auth_failure_total{reason}` feed the “Settings Registry – Availability” dashboard; synthetic activations assert error semantics before release. **|**
**Breadcrumbs:** API handlers `apps/platform/settings/api.py`, security helpers `apps/platform/settings/security.py`, tests `tests/platform/settings/test_auth.py`, `tests/platform/settings/test_activation_flow.py`, schema `spec/schemas/api_error.schema.json`. **|**
**References:** Platform Runtime §3.3, Guardian spec §2.2, Reference Manager spec §3.4, Ops runbooks `RB-SETTINGS-ACTIVATION`, `RB-HMAC-ROTATE`.
> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#settings-registry)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `AUTH_CLOCK_SKEW` | X-Timestamp header outside the ±120 second tolerance. | Sync clocks and retry with a corrected timestamp. |
| `AUTH_SIGNATURE_INVALID` | HMAC signature mismatch on mutating requests. | Recompute the signature, rotate credentials via RB-HMAC-ROTATE if repeated, and retry. |
| `CONFLICT` | Activation expected_version mismatch or replayed Idempotency-Key. | Re-fetch activation state, regenerate the idempotency token, and retry. |
| `POLICY_BLOCK` | Residency, waiver, or governance policy rejected the activation. | Obtain waiver or approval, update policy inputs, and resubmit the activation. |
| `SECRET_DISCLOSURE_BLOCKED` | Attempt to export masked secret fields through diff previews or read APIs. | Remove secret fields from the request; fetch redacted values only. |
| `VALIDATION_ERROR` | Bundle schema violation, unsafe override, or diff failing semantic guard. | Inspect details[], remediate configuration, rerun validation. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `AUTH_CLOCK_SKEW` | 401 | No | settings_auth_failure_total |
| `AUTH_SIGNATURE_INVALID` | 401 | Yes | settings_auth_failure_total |
| `CONFLICT` | 409 | No | settings_error_total |
| `POLICY_BLOCK` | 403 | Yes | settings_error_total<br>settings_policy_block_total |
| `SECRET_DISCLOSURE_BLOCKED` | 403 | Yes | settings_error_total |
| `VALIDATION_ERROR` | 400 | No | settings_error_total |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

### 3.4 Authentication & request signing (binding)

**Purpose:** Enforce secure access to mutating endpoints. **|**
**Contract:** Mutations require service tokens plus HMAC signing; actors supply `X-Signature-Key-Id`, `X-Timestamp`, and Idempotency headers with ±30 second skew tolerance. **|**
**State:** Key metadata stores in `settings_hmac_key`; rotations link to activation records and audit trails. **|**
**Failures & handling:** Signature mismatches return `401`; clients refresh keys or resync clocks before retrying. **|**
**Observability:** “Settings Auth” dashboard segments `settings_auth_failure_total` by reason (signature_mismatch, expired_timestamp, disabled_key); audit events capture actor and bundle IDs. **|**
**References:** §7 Security & compliance, §8.3 Runbooks & drills.
**Breadcrumbs:** Security helpers `apps/platform/settings/security.py`, tests `tests/platform/settings/test_auth.py`.

### 3.5 Privacy & redaction (normative)

**Purpose:** Protect sensitive configuration when displayed or exported. **|**
**Contract:** SR redacts secret values in API responses, CLI exports, and diff previews; activation history stores hashed digests only. **|**
**State:** Secret metadata tracked in `settings_secret_meta` including scope, rotation cadence, and masking policy. **|**
**Failures & handling:** Attempts to expose secrets trigger `SECRET_DISCLOSURE_BLOCKED`; Security reviews audit trails before re-enabling access. **|**
**Observability:** “Settings – Secret Access” panel tracks `settings_secret_read_total` by actor role; anomaly detection alerts on spikes. **|**
**References:** §7 Security & compliance, Appendix A.
**Breadcrumbs:** Redaction helpers `apps/platform/settings/redaction.py`, tests `tests/platform/settings/test_redaction.py`.

______________________________________________________________________

## 4) State Management {#4-activation-workflow-governance}

**Purpose:** Explain how SR processes activations, persists governance state, and keeps caches consistent. **|**
**Contract:** Activations execute deterministic stages (diff, validation, approval, publish) with advisory locks, dual approvals, and rollback support. **|**
**State:** Activation records, stage history, diff artifacts, and lock metadata reside in Postgres (`setting_activation`, `setting_activation_stage`, `settings_activation_lock`) with companion artifacts under `storage/media/settings/`. **|**
**Failures & handling:** Validator failures, lock contention, or stale caches halt activations until remediation (see §§4.2–4.5 and §5). **|**
**Observability:** “Settings Activation”, “Settings Diff”, “Settings Lock”, and “Settings Cache” dashboards track duration, unsafe counts, contention, and invalidation lag. **|**
**Breadcrumbs:** Activation services `apps/platform/settings/services/`, diff renderer `apps/platform/settings/services/diff.py`, lock manager `apps/platform/settings/services/locks.py`. **|**
**References:** §2 Responsibilities, §3 API contract, §5 Failure modes, §8.3 Runbooks & drills.

### 4.1 Activation pipeline (binding)

**Purpose:** Describe the activation flow from submission through publish. **|**
**Contract:** Activations compute diffs, run validators, persist audit trails, publish invalidation events, and enforce blue/green rollout sequencing with advisory locks. **|**
**State:** Pipeline stages record in `setting_activation_stage`; lock state maintained per org/bundle. **|**
**Failures & handling:** Validator failures mark activations unsafe; operators remediate and resubmit. Rollback replays previous bundles with preserved audit metadata. **|**
**Observability:** “Settings Activation” dashboard tracks `settings_activation_duration_seconds`, unsafe counts, and rollback frequency; traces link to change tickets. **|**
**References:** §5 Failure modes, §8.3.2 RB-GOV-008.
**Breadcrumbs:** Activation service `apps/platform/settings/services/activation.py`, tests `tests/platform/settings/test_activation_flow.py`.

- Diff previews produce human-readable and machine JSON artifacts for reviewers.
- Activation history retains signatures, actor IDs, roles, and justification text.

### 4.2 Diff preview & dry-run validation (binding)

**Purpose:** Provide reviewers visibility into proposed changes before approval. **|**
**Contract:** Dry runs compare compiled tables (`effective_permission`, `field_mask_rule`, residency profiles) and surface unsafe reasons requiring dual approval. **|**
**State:** Diff artifacts persist in `settings_activation_diff` with SHA-256 digests and reviewer annotations. **|**
**Failures & handling:** Missing diff or compilation errors block approval; remediate data and rerun pipeline. **|**
**Observability:** “Settings Diff” panel charts `settings_diff_generated_total` by bundle type; alerts fire when diff generation fails repeatedly. **|**
**References:** Appendix A traceability map, §8.3.2 RB-GOV-008.
**Breadcrumbs:** Diff renderer `apps/platform/settings/services/diff.py`, tests `tests/platform/settings/test_diff_preview.py`.

### 4.3 Dual approval & waiver workflow (binding)

**Purpose:** Enforce governance for risky changes. **|**
**Contract:** Unsafe activations demand dual approval (Security + Architecture) with step-up MFA and recorded justification; waivers embed waiver IDs and expiry metadata. **|**
**State:** Approval records persist in `settings_activation_approval`; waivers track in `settings_waiver` referencing App.O decision log entries. **|**
**Failures & handling:** Missing approvals keep activations pending; expired waivers trigger alerts and block reactivation until renewed. **|**
**Observability:** “Settings Governance” dashboard charts `settings_dual_approval_total`, waiver counts, and decision latency; audit events `SETTINGS_CHANGE_REQUESTED` and `SETTINGS_WAIVER_APPLIED` broadcast outcomes. **|**
**References:** §7 Security & compliance, §8.3.2 RB-GOV-008.
**Breadcrumbs:** Governance service `apps/platform/settings/services/approvals.py`, tests `tests/platform/settings/test_governance.py`.

### 4.4 Locking & concurrency control (normative)

**Purpose:** Prevent conflicting activations and enforce uniqueness. **|**
**Contract:** SR acquires advisory lock `settings-activate:{org_id}` and enforces optimistic concurrency on active bundle rows, ensuring one ACTIVE bundle per org/bundle combination. **|**
**State:** Lock metadata lives in `settings_activation_lock` with timestamps and holder IDs. **|**
**Failures & handling:** Lock timeouts surface `ACTIVATION_CONFLICT`; clients retry after backoff once lock releases. **|**
**Observability:** “Settings Lock” panel highlights `settings_activation_lock_wait_seconds`; alerts trigger when waits exceed 30 seconds. **|**
**References:** §5 Failure modes, §8.3.5 RB-LOCK-006.
**Breadcrumbs:** Lock utilities `apps/platform/settings/services/locks.py`, tests `tests/platform/settings/test_locks.py`.

### 4.5 Caching & invalidation (normative)

**Purpose:** Keep runtime views consistent without stale decisions. **|**
**Contract:** SR publishes `settings.changed` events `{scope, org_id, case_id, bundle_id}`; subscribers flush caches and refresh on next access, with polling safeguards if events are missed. **|**
**State:** Redis pub/sub stores event history for one hour; adoption trackers confirm refresh success. **|**
**Failures & handling:** Missed events trigger fallback pollers; repeated misses raise incident `SETTINGS_INVALIDATION_STALLED`. **|**
**Observability:** “Settings Cache” dashboard monitors `settings_cache_invalidation_lag_seconds`; synthetic fetches confirm propagation within 60 seconds. **|**
**References:** §3.2 SDK usage, §6 Observability.
**Breadcrumbs:** Cache manager `apps/platform/settings/cache.py`, tests `tests/platform/settings/test_invalidation.py`.

______________________________________________________________________

## 5) Failure Modes (binding)

**Purpose:** Capture the primary ways SR can degrade and the responses required to keep configuration trustworthy. **|**
**Contract:** SR must fail closed on unsafe activations, drift, or residency violations; manual overrides require documented waivers and adherence to §8.3 Runbooks & drills. **|**
**State:** Incidents log in `ops/guardian/incidents/` (shared format), `settings_drift_finding`, and `settings_activation` status fields. **|**
**Failures & handling:** Validator failures, snapshot mismatches, and residency drift each trigger dedicated runbooks detailed below. **|**
**Observability:** Alerts on `settings_activation_unsafe_total`, `settings_snapshot_mismatch_total`, and `settings_residency_violation_total` page on-call responders. **|**
**Breadcrumbs:** Incident automation `ops/scripts/guardian/*.py` (shared framework), drift detector `apps/platform/settings/telemetry.py`, residency validators `apps/platform/settings/validators/residency.py`. **|**
**References:** §4 State management, §6 Observability, §8.3.2 RB-GOV-008 / §8.3.3–§8.3.4 RB-RES-\* / §8.3.5 RB-LOCK-006.

### 5.1 Activation validator failure (binding)

**Purpose:** Address situations where validators block an activation. **|**
**Contract:** Unsafe activations remain `READY_FOR_REVIEW` with `unsafe_reasons[]`; teams must remediate data or apply approved waivers before reenabling. **|**
**State:** Unsafe details recorded in `settings_activation_validation`; approvers annotate mitigation steps. **|**
**Failures & handling:** Runbook RB-GOV-008 outlines rollback, manual review, and dual approval flow; automation freezes subsequent activations until the incident closes. **|**
**Observability:** Alerts `settings_activation_unsafe_total` and SLO burn-rate alarms escalate to Architecture/Security. **|**
**References:** §4.1 Activation pipeline, §4.3 Dual approval, §8.3.2 RB-GOV-008.
**Breadcrumbs:** Validation services `apps/platform/settings/services/validation.py`, tests `tests/platform/settings/test_activation_flow.py::test_pipeline_rejects_invalid`.

### 5.2 Snapshot mismatch & drift (binding)

**Purpose:** Respond to mismatched digests or drift between stored snapshots and effective configuration. **|**
**Contract:** Consumers halt mutating operations when `settings_snapshot_mismatch_total` > 0 and fetch fresh snapshots; SR reconciles drift before resuming activations. **|**
**State:** Drift findings persist in `settings_drift_finding` with remediation tickets and timestamps. **|**
**Failures & handling:** RB-RES-ENDPOINT and RB-JOB-WATCHDOG guide reconciliation; SR may replay last known good bundle or regenerate snapshots. **|**
**Observability:** “Settings Drift” dashboard, alerts `settings_snapshot_mismatch_total`, and synthetic fetches confirm when drift resolves. **|**
**References:** §2.3 Snapshot contract, §6 Observability, §8.3.3 RB-RES-ENDPOINT / §8.3.7 RB-JOB-WATCHDOG.
**Breadcrumbs:** Telemetry module `apps/platform/settings/telemetry.py`, tests `tests/platform/settings/test_drift.py`.

### 5.3 Residency enforcement incident (binding)

**Purpose:** Outline remediation when residency controls fail or new endpoints appear. **|**
**Contract:** Activations must block until Reference Manager catalogs align; waivers require Security + Architecture approval with manifest stamping. **|**
**State:** Residency findings recorded in `settings_residency_profile` and incident logs; waivers tracked with expiry. **|**
**Failures & handling:** RB-RES-BLOCK and RB-RES-ENDPOINT guide containment, catalog sync, and waiver approval; Guardian cross-checks waivers before judgments resume. **|**
**Observability:** Alerts `settings_residency_violation_total`, audit events `RESIDENCY_ENDPOINT_NEW`, and Security tickets `SEC-RESIDENCY-ENDPOINT` drive follow-up. **|**
**References:** §2.4 Residency & egress, §7 Security & compliance, §8.3.3–§8.3.4 RB-RES-\* runbooks.
**Breadcrumbs:** Validators `apps/platform/settings/validators/residency.py`, tests `tests/platform/settings/test_residency_validators.py`.

______________________________________________________________________

## 6) Observability (binding)

**Purpose:** Define the telemetry, dashboards, and synthetic coverage that prove SR is meeting its safety and latency commitments. **|**
**Contract:** Metrics, logs, and synthetic probes listed here are mandatory; removing or renaming signals requires Observability + Security approval and doc updates. **|**
**State:** Metrics publish via Prometheus (`settings_*` series), logs/audits persist in Postgres and `storage/media/settings/`, and synthetic jobs emit structured artifacts in `ops/synthetics/`. **|**
**Failures & handling:** Breaches escalate through Section 5 runbooks (RB-GOV-008, RB-RES-\*, RB-LOCK-006) before activations resume. **|**
**Observability:** Grafana dashboards “Settings Registry – SLO”, “Settings Cache”, “Settings Drift”, and “Settings Governance” visualize health; Alertmanager routes incidents to Settings on-call. **|**
**Breadcrumbs:** Dashboards `infra/grafana/settings_*.json`, synthetic config `ops/synthetics/settings_slo.yaml`, telemetry module `apps/platform/settings/telemetry.py`. **|**
**References:** §1 Purpose, §4 State management, §5 Failure modes, Appendix B metrics, §8.3 Runbooks & drills.

### 6.1 SLOs & Targets (binding)

**Purpose:** Capture registry availability, activation latency, cache freshness, and residency enforcement guarantees. **|**
**Contract:** API availability, activation duration, cache invalidation, and residency checks must satisfy the thresholds below before new settings are promoted. **|**
**State:** Metrics `settings_request_total`, `settings_error_total`, `settings_activation_duration_seconds`, `settings_cache_invalidation_lag_seconds`, `settings_residency_violation_total`; dashboards “Settings Registry – SLO”, “Settings Cache”, “Settings Drift”. **|**
**Failures & handling:** Breaches invoke RB-GOV-008, RB-SETTINGS-CACHE, or RB-RES-\* prior to resuming activations. **|**
**Observability:** Grafana dashboards, synthetic activation tests, and burn-rate alerts supply evidence. **|**
**Breadcrumbs:** Prometheus rules `infra/monitoring/settings-prometheus-rules.yaml`, synthetic configs `ops/synthetics/settings_slo.yaml`, runbooks `docs/ops/runbooks/settings/*.md`. **|**
**References:** TDD §12, Logging spec §6, Audit spec §5.

- **API availability:** ≥99.9% monthly success rate for read/write operations (`settings_request_total` vs `settings_error_total`). Breaches trigger RB-GOV-008 and freeze releases until the budget recovers.
- **Activation latency:** 95th percentile activation duration (`settings_activation_duration_seconds`) ≤ 120 seconds; overruns pause activations and require RCA prior to thaw.
- **Cache freshness:** `settings_cache_invalidation_lag_seconds` stays ≤ 60 seconds P95; sustained lag opens RB-SETTINGS-CACHE and blocks deploys.
- **Residency enforcement:** `settings_residency_violation_total` remains zero; any event invokes RB-RES-\* and requires waiver or remediation before continuing.

### 6.2 Metrics

**Purpose:** Summarize key quantitative signals. **|**
**Contract:** Maintain metrics `settings_latency_seconds`, `settings_request_total`, `settings_error_total`, `settings_activation_duration_seconds`, `settings_activation_unsafe_total`, `settings_validation_failure_total`, `settings_cache_invalidation_lag_seconds`, `settings_snapshot_mismatch_total`, and `settings_residency_violation_total`. **|**
**State:** Metrics originate from application instrumentation and activation pipeline hooks; error budget tracking stores monthly summaries in `sre_error_budget`. **|**
**Failures & handling:** Threshold breaches drive runbooks in §5; burn-rate alarms freeze activations. **|**
**Observability:** Grafana “Settings Registry – SLO” and “Settings Drift” dashboards chart trends; alert definitions live in `infra/monitoring/settings-prometheus-rules.yaml`. **|**
**References:** Appendix B.
**Breadcrumbs:** Telemetry helpers `apps/platform/settings/telemetry.py`, Prometheus rules `infra/monitoring/settings-prometheus-rules.yaml`.

### 6.3 Logs & audits

**Purpose:** Describe the audit footprint that supports incident response and compliance. **|**
**Contract:** Activation history, diff artifacts, approvals, waivers, and drift findings must be append-only with immutable digests; redaction policies govern secret output. **|**
**State:** Logs persist in `setting_activation`, `setting_activation_diff`, `settings_activation_approval`, `settings_drift_finding`, and case-scoped ops directories under `storage/media/settings/`. **|**
**Failures & handling:** Missing artifacts or retention gaps trigger compliance incidents; responders follow §8.3.2 RB-GOV-008 and RB-LOCK-006. **|**
**Observability:** Audit pipeline metrics, partition age checks, and log retention alerts verify coverage. **|**
**References:** §4 State management, §7 Security & compliance, Appendix A traceability.
**Breadcrumbs:** Logging config `infra/logging/settings.json`, rotation script `ops/db/rotate_partitions.py`, tests `tests/platform/settings/test_audit_trail.py`.

### 6.4 Synthetic monitoring

**Purpose:** Continuously exercise SR surfaces to detect regressions early. **|**
**Contract:** Synthetic jobs execute read, activation, invalidation, and diff workflows on each deploy; failures block releases until mitigated. **|**
**State:** Synthetic definitions live in `ops/synthetics/settings_slo.yaml`; results archive to incident dashboards and CI logs. **|**
**Failures & handling:** Failures escalate via RB-GOV-008; subsequent activations freeze until synthetic success. **|**
**Observability:** Grafana panels and PagerDuty integrations track synthetic success rates and latency. **|**
**References:** §4 Activation pipeline, §5 Failure modes, §8.3.2 RB-GOV-008.
**Breadcrumbs:** Synthetic scripts `ops/synthetics/`, tests `tests/synthetics/test_settings_slo.py`.

### 6.5 Drift detection (binding)

**Purpose:** Detect mismatches between stored snapshots and effective configuration. **|**
**Contract:** Drift detectors compare snapshot digests, schema versions, and residency profiles on a schedule; any mismatch raises incidents and freezes activations. **|**
**State:** Findings persist in `settings_drift_finding` with remediation steps and linked tickets. **|**
**Failures & handling:** Unresolved drift escalates to Security and §8.3.3 RB-RES-ENDPOINT; SR may regenerate snapshots or rollback bundles. **|**
**Observability:** “Settings Drift” dashboard charts `settings_snapshot_drift_total` and severity; alerts integrate with on-call rotations. **|**
**References:** §2.3 Snapshot contract, §5.2 Snapshot mismatch.
**Breadcrumbs:** Drift detector `apps/platform/settings/telemetry.py`, tests `tests/platform/settings/test_drift.py`.

______________________________________________________________________

## 7) Security & Compliance (binding)

**Purpose:** Capture SR’s security posture, residency guarantees, and regulatory obligations. **|**
**Contract:** SR enforces RLS, secret redaction, residency controls, dual approval, and tamper-evident logs; waivers and manual overrides require documented approval with expiry. **|**
**State:** Security policies live in IAM roles, RLS definitions, HSM-managed signing keys, and audit tables described below. **|**
**Failures & handling:** Auth violations, residency breaches, or secret exposure escalate through §8.3 Runbooks & drills and Security incident workflows. **|**
**Observability:** Dashboards “Settings Auth”, “Settings Governance”, and “Residency Compliance” plus audit alerts surface violations. **|**
**Breadcrumbs:** IAM policies `infra/iam/settings/`, RLS definitions `apps/platform/settings/models.py`, security tests `tests/platform/settings/test_security.py`. **|**
**References:** §2.4 Residency, §3.4 Authentication, §5 Failure modes, §8.3.3–§8.3.4 RB-RES-\*/RB-GOV-008.

### 7.1 Access control & RLS (binding)

**Purpose:** Define SR’s access model. **|**
**Contract:** SR enforces deny-by-default policies using compiled `effective_permission` tables; only explicitly authorized roles (including `sysadmin`) may modify configuration. **|**
**State:** Access grants persist in `setting_permission` referencing roles and resources; policy compilation aligns with Appendix A traceability. **|**
**Failures & handling:** Unauthorized attempts raise `403`; audit logs record actor, scope, and requested action for SIEM ingestion. **|**
**Observability:** “Settings Access” dashboard charts `settings_access_violation_total`; anomalies route to security analysts. **|**
**References:** §3.4 Authentication, Appendix A key catalog.
**Breadcrumbs:** Access policy implementation `apps/platform/settings/models.py::SettingAccessPolicy`, tests `tests/platform/settings/test_access_control.py`.

- Field masking rules compile into `field_mask_rule` tables refreshed per activation.

### 7.2 Audit logging & retention (binding)

**Purpose:** Maintain complete audit history for regulatory review. **|**
**Contract:** Every activation, validation failure, unsafe reason, waiver, and cache invalidation produces structured audit events stored in immutable sinks; retention periods align with HIPAA/PHIPA and internal governance policies. **|**
**State:** Audit events stream to `ops/settings/ops_settings.jsonl` and warehouse tables; manifest digests link to Appendix A traceability. **|**
**Failures & handling:** Immutable sink toggles are blocked; fallback storage engages if sinks are unavailable, triggering incident escalation. **|**
**Observability:** “Settings Audit Trail” dashboard tracks `settings_audit_event_total`; completeness monitors alert if events lag beyond five minutes. **|**
**References:** §6.2 Logs & audits, Appendix B metrics.
**Breadcrumbs:** Audit writer `apps/platform/settings/audit.py`, tests `tests/platform/settings/test_audit_log.py`.

### 7.3 Incident response & rollback (binding)

**Purpose:** Provide repeatable rollback and incident handling procedures. **|**
**Contract:** Unsafe activations or drift incidents freeze new activations, replay last known good bundles, notify stakeholders, and document remediation per §8.3.2 RB-GOV-008. **|**
**State:** Automation stores rollback checkpoints and evidence attachments alongside incident tickets. **|**
**Failures & handling:** Rollback failures escalate to the incident commander; automation retries with exponential backoff before manual intervention. **|**
**Observability:** “Settings Incidents” panel tracks `settings_incident_open_total`; postmortems reference activation IDs and audit digests. **|**
**References:** §5 Failure modes, §8.3.2 RB-GOV-008/RB-LOCK-006.
**Breadcrumbs:** Runbook scripts `ops/runbooks/settings_rollback.py`, tests `tests/platform/settings/test_rollback.py`.

### 7.4 Compliance & privacy obligations (normative)

**Purpose:** Capture DSAR, retention, HIPAA, and disclosure requirements enforced by SR. **|**
**Contract:** Keys such as `compliance.erasure_mode`, `compliance.subject_hkdf_salt`, `privacy.hipaa.*`, and `privacy.legal.matrix_version` must exist and pass validators before activation; overrides require dual approval with legal citations. **|**
**State:** Compliance profile metadata lives in `settings_compliance_profile` and links to Reference Manager legal matrices. **|**
**Failures & handling:** Missing keys or invalid values block activation; forced overrides demand dual approval and §8.3 documentation. **|**
**Observability:** “Settings Compliance” dashboard monitors `settings_compliance_violation_total`; alerts highlight expiring HIPAA bundles or DSAR configuration drift. **|**
**References:** §2 Responsibilities, §5.3 Residency incidents, §8.3.4 RB-RES-BLOCK.
**Breadcrumbs:** Compliance enforcement `apps/platform/settings/compliance.py`, tests `tests/platform/settings/test_compliance.py`.

______________________________________________________________________

## 8) Operational Notes (normative)

**Purpose:** Capture day-to-day operational practices, release mechanics, and tooling used to keep SR healthy. **|**
**Contract:** Teams must follow documented change control, runbook execution, and release cadence; deviations require incident documentation and retro actions. **|**
**State:** Operational metadata lives in runbooks under `ops/runbooks/settings/`, deployment scripts, and incident retros in shared `ops/guardian/incidents/` templates. **|**
**Failures & handling:** Skipping change control or drifting from operational guides increases audit risk; §8.3 runbooks codify the required responses. **|**
**Observability:** Deployment dashboards, runbook completion checklists, and CI jobs surface operational hygiene. **|**
**Breadcrumbs:** Deployment scripts `ops/scripts/settings_deploy.py`, CI workflows `.github/workflows/docs-ci.yml`, runbooks `ops/runbooks/settings/`. **|**
**References:** §4 State management, §5 Failure modes, §8.3 Runbooks & drills, Appendix B alerts.

### 8.1 Operational Posture (binding)

**Purpose:** Outline staffing, freeze windows, and readiness expectations that keep SR governable. **|**
**Contract:** Settings on-call (shared with Guardian and LPE) staffs PagerDuty “Settings SLO”, honors blue/green deployment freezes, and executes RB-GOV-008/RB-RES-\* before resuming automation after incidents. **|**
**State:** Roster lives in `ops/guardian/roster.yaml` (annotated with SR owners); freeze calendars and change tickets track release windows. **|**
**Failures & handling:** Missing coverage or ignored freezes trigger management review and corrective actions. **|**
**Observability:** PagerDuty response metrics, deployment dashboards, and freeze indicators highlight posture drift. **|**
**Breadcrumbs:** Roster `ops/guardian/roster.yaml`, freeze calendar `ops/settings/freeze_windows.yaml`, workflow `.github/workflows/settings-deploy.yml`. **|**
**References:** §6 Observability, §8.3 Runbooks & drills, §8.5.1 Release cadence & change control.

- Blue/green deploys require active change tickets and explicit freeze acknowledgements; freezes lift only after post-deploy SLO burn remains < 0.5 for two hours.
- Duty officers escalate to Architecture and Security when governance toggles or residency incidents occur; contact paths live in the roster file.
- Quarterly readiness reviews sample incident evidence to confirm runbook adherence and staffing coverage.

### 8.2 Incident Triggers (binding)

**Purpose:** Map SR alerts to the playbooks responders execute so incidents open with the right context. **|**
**Contract:** Alert definitions in `infra/monitoring/settings-prometheus-rules.yaml` each specify the RB-\* identifier to run; Responders capture evidence before clearing the alert. **|**
**State:** Alert payloads include runbook IDs and change-ticket links; incidents log under `ops/settings/incidents/<date>.jsonl`. **|**
**Failures & handling:** Misconfigured alert → runbook mapping or suppressed notifications require Ops sign-off and follow-up tasks. **|**
**Observability:** Grafana dashboards, Alertmanager routing, and post-incident reviews track trigger efficacy. **|**
**Breadcrumbs:** Alert configuration `infra/monitoring/settings-prometheus-rules.yaml`, PagerDuty “Settings SLO”, incident templates `ops/settings/incident_template.md`. **|**
**References:** §5 Failure modes, §8.3 Runbooks & drills, Appendix B metrics.

- `settings_activation_failure_total` and governance toggle alerts invoke RB-SETTINGS-ACTIVATION to validate diffs, roll back, or re-run promotion.
- `settings_residency_violation_total` and endpoint drift alerts route to RB-RES-ENDPOINT for allowlist reconciliation and cache flush.
- `settings_governance_override_total` and manual toggle changes trigger RB-GOV-008 to restore approved configuration and evidence.
- `settings_waiver_expiring_total` or audit findings escalate via RB-SETTINGS-WAIVER for renewal/retirement workflows.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Maintain authoritative SR recovery guides, drills, and manual procedures executed during incidents. **|**
**Contract:** Alerts enumerated in §8.2 and Appendix B map to RB-\* identifiers documented here; responders update these runbooks after every incident or drill. **|**
**State:** Procedures live alongside automation scripts in `ops/runbooks/settings/`, with evidence logged under `ops/settings/<date>/` for each activation or remediation. **|**
**Failures & handling:** Missing or stale steps block deployment sign-off; responders raise follow-up tasks to refresh runbooks before closing incidents. **|**
**Observability:** Post-incident retros, quarterly tabletop exercises, and docs lint verify runbook coverage. **|**
**Breadcrumbs:** Runbooks `ops/runbooks/settings/*.md`, automation scripts under `ops/scripts/settings/`, tests `tests/platform/settings/test_runbook_integrity.py`. **|**
**References:** §5 Failure modes, §8.1 Operational posture, Appendix B metrics, ADR-0003.

#### 8.3.1 Runbook Index (informative)

- `RB-GOV-008` — Settings governance toggle / rollback
- `RB-RES-ENDPOINT` — Residency endpoint drift remediation
- `RB-SETTINGS-ACTIVATION` — Activation failure response
- `RB-SETTINGS-WAIVER` — Waiver renewal and auditing

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Capture Settings service playbooks so responders execute consistent mitigation and evidence capture. **|**
**Contract:** Each runbook links to alert identifiers, change tickets, and required evidence; responders update the runbooks after incidents or drills. **|**
**State:** Runbooks under `ops/runbooks/settings/`, automation scripts under `ops/scripts/settings/`, evidence stored in `ops/settings/incidents/`. **|**
**Failures & handling:** Missing or outdated instructions block deployment approvals. **|**
**Observability:** Docs lint, PagerDuty analytics, and governance dashboards track freshness and drill coverage. **|**
**Breadcrumbs:** `ops/runbooks/settings/*.md`, `ops/scripts/settings/*.py`, incident templates `ops/settings/incidents/*.md`. **|**
**References:** Alert catalog, residency policy, FinOps governance.

- `RB-GOV-008`: Roll back governance toggles, restore prior snapshots, and document change approvals before reactivating.
- `RB-RES-ENDPOINT`: Remediate residency drift by updating endpoint allowlists, flushing caches, and verifying Guardian exposure.
- `RB-SETTINGS-ACTIVATION`: Handle activation failures by validating schema diffs, rerunning validation harnesses, and coordinating rollback/promotion sequencing.
- `RB-SETTINGS-WAIVER`: Renew or retire waivers, update allowlists, run verification scripts, and log approvals in App.O.

#### 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover activation rollback, residency drift, governance toggle rollback, and waiver renewal; evidence stored in `ops/settings/drills/<date>/` with retrospectives.
- Docs lint (`python -m doc_tools.build.runbook_catalog --check`) and PagerDuty analytics confirm drill execution; missed drills block releases until mitigated.
- Compliance reviews reference drill artefacts, waiver logs, and activation evidence to demonstrate readiness.

### 8.4 Migrations & Backfills (binding)

**Purpose:** Capture schema, bundle, and catalog migrations required to keep SR state aligned. **|**
**Contract:** Migration scripts run with dry-run evidence, tagged change tickets, and rollback checkpoints; any partial completion requires incident response. **|**
**State:** Migration manifests live in `ops/settings/migrations/`, `settings_activation` history logs bundle hashes, and reference catalog digests live in `reference_catalog_snapshot`. **|**
**Failures & handling:** Partial migrations risk drift; responders must execute RB-LOCK-006 or RB-RES-\* before re-opening activations. **|**
**Observability:** Dashboards “Settings Deployment” and “Residency Compliance” plus CI migration smoke tests confirm success. **|**
**Breadcrumbs:** Migration scripts `ops/scripts/settings/migrate.py`, backfill tooling `ops/scripts/settings/replay_snapshot.py`, change-control template `ops/settings/migrations/README.md`. **|**
**References:** §4 State management, §5 Failure modes, ADR-0003, §8.3 Runbooks & drills.

- Run `ops/scripts/settings/migrate.py --dry-run` before production execution; attach output to the change ticket.
- Capture bundle digests before/after migration; verify consumers emit `settings.changed` events.
- Roll back via `settings rollback --bundle <id>` if post-migration smoke tests fail; document residual drift and remediation tasks.

### 8.5 Operational Workflows (normative)

**Purpose:** Describe recurring operational tasks that preserve SR readiness outside of incidents. **|**
**Contract:** Each workflow enumerated here has an owner, cadence, and evidence requirement; skipped cadences block deploy approvals until remediated. **|**
**State:** Checklists and automations live in `ops/guardian/checklists/` and docs lint scripts; outputs append to `ops/settings/workflow_log.jsonl`. **|**
**Failures & handling:** Missed cadences surface in quarterly audits; owners must backfill evidence and update processes. **|**
**Observability:** Staffing dashboards, workflow logs, and CI history provide signals. **|**
**Breadcrumbs:** Workflow docs `ops/settings/workflows/*.md`, automation scripts `packages/udocket_docs/src/doc_tools/*.py`, staffing roster `ops/guardian/roster.yaml`. **|**
**References:** §8.3 Runbooks & drills, §6 Observability, Appendix B metrics.

#### 8.5.1 Release cadence & change control (binding)

**Purpose:** Document how SR code and configuration rollouts occur. **|**
**Contract:** Code deploys follow blue/green strategy with activation freeze windows; configuration changes require change ticket linkage and dual approval before hitting production. **|**
**State:** Deployment metadata recorded in GitHub Actions artifacts and `settings_activation` history (`change_ticket`, `release_channel`). **|**
**Failures & handling:** Failed deploys auto-roll back to previous release; configuration freezes remain active until SLOs stabilize. **|**
**Observability:** Release dashboards show deployment status, activation backlog, and freeze indicators. **|**
**References:** §4 Activation pipeline, §8.1 Operational posture, §8.3.2 RB-GOV-008.
**Breadcrumbs:** Deployment script `ops/scripts/settings_deploy.py`, tests `tests/platform/settings/test_release_workflow.py`.

#### 8.5.2 Tooling & automation checks (normative)

**Purpose:** Summarize supporting tooling that keeps SR governance consistent. **|**
**Contract:** Teams run `python -m doc_tools.manage_docs --lint`, `python -m doc_tools.build.runbook_catalog`, `python -m doc_tools.check_settings_keys`, and `scripts/sdk/check_openapi_alignment.py` before merging SR changes. **|**
**State:** CI workflows enforce linting, seed bundle validation, and OpenAPI drift detection; runbook catalog renders the runbook index. **|**
**Failures & handling:** Failing automation blocks merges; overrides require Architecture approval with follow-up tasks. **|**
**Observability:** CI dashboards display job history; governance board reviews automation health monthly. **|**
**References:** §2 Responsibilities, Appendix C seed inventory, §8.3 Runbooks & drills.
**Breadcrumbs:** Scripts under `packages/udocket_docs/src/doc_tools/`, CI definitions `.github/workflows/docs-ci.yml`.

______________________________________________________________________

## 9) Dependencies (informative) {#5-agent-automation-configuration}

**Purpose:** Map SR’s upstream and downstream relationships so teams understand how configuration changes cascade. **|**
**Contract:** SR depends on Guardian, LPE, Reference Manager, Portal, and Worker pipelines consuming snapshots, respecting invalidations, and surfacing digests in their own telemetry. **|**
**State:** Integration metadata resides in `settings_enforcement_point`, `settings_integration_status`, `settings_portal_profile`, and job manifests with snapshot digests. **|**
**Failures & handling:** Missed invalidations or integration drift trigger Section 5 runbooks (RB-RES-\*, RB-JOB-WATCHDOG) and §8.3.2 RB-GOV-008 coordination. **|**
**Observability:** Dashboards “Settings Enforcement”, “Settings Integration”, “Portal Settings”, and “Worker Settings” expose adoption health; alerts highlight stale snapshots or misaligned bundles. **|**
**Breadcrumbs:** Integration services `apps/platform/settings/services/`, worker tasks `apps/platform/operations/tasks.py`, tests `tests/platform/settings/test_enforcement_points.py`, `tests/platform/settings/test_lpe_guardian_bridge.py`. **|**
**References:** §2 Responsibilities, §3 API contract, §6 Observability, Appendix B metrics.

### 9.1 Enforcement touchpoints (binding) {#6-integrations-enforcement-points}

**Purpose:** Enumerate runtime surfaces that must consult SR. **|**
**Contract:** APIs, workers, front-end flows, and database policies fetch current settings snapshots before decision-making and record digests in logs; missing enforcement registrations fail lint checks. **|**
**State:** Enforcement registry stored in `settings_enforcement_point` with required bundles and validation hooks. **|**
**Failures & handling:** Runtime detection of stale snapshots blocks operations until refreshed; lint failures must be resolved before merge. **|**
**Observability:** “Settings Enforcement” dashboard tracks `settings_enforcement_lookup_total` and stale detection alerts. **|**
**References:** §4 State management, §5 Failure modes.
**Breadcrumbs:** Enforcement helpers `apps/platform/settings/services/enforcement.py`, tests `tests/platform/settings/test_enforcement_points.py`.

- API enforcement covers RBAC writes, CORS, rate limits, portal downloads, HIPAA/PHIPA banners, and residency gating.
- Worker enforcement includes agent configurations, FinOps ceilings, Guardian/Signer integration, and waiver gating.
- Front-end enforcement drives feature flags, approvals, messaging flows, and localization decisions.
- Database enforcement ensures RLS and masking profiles reference compiled tables from SR activations and LPE contexts.

### 9.2 Guardian, LPE, and RM alignment (binding)

**Purpose:** Define coordination with Guardian, LPE, and Reference Manager. **|**
**Contract:** SR consumes RM bundles for residency/provider catalogs, triggers LPE dry-run compiles, and exposes Guardian waivers and policy toggles with shared digests; integration drift blocks activation. **|**
**State:** Integration metadata persists in `settings_integration_status` referencing RM bundle IDs and LPE compile versions. **|**
**Failures & handling:** Missing RM bundles or failed LPE compiles flag activations unsafe; teams remediate before approval proceeds. **|**
**Observability:** “Settings Integration” dashboard captures sync success, waiver usage, and compile durations; alerts open Security tickets when residency endpoints change. **|**
**References:** §2.4 Residency, §5.3 Residency incidents, §8.3.3 RB-RES-ENDPOINT.
**Breadcrumbs:** Integration service `apps/platform/settings/services/integration.py`, tests `tests/platform/settings/test_lpe_guardian_bridge.py`.

- Residency endpoint changes open Security tickets; waivers demand dual approval and manifest stamping until replacement endpoints validated.
- Guardian gating configuration, including review modes and operator visibility, surfaces via SR keys and audit events.

### 9.3 Portal & client experience (normative)

**Purpose:** Outline SR responsibilities for portal/client exposures. **|**
**Contract:** SR provides localized disclaimers, enabled locales, HIPAA allowances, rate limits, and chat assistant toggles for portal consumption. **|**
**State:** Portal profile snapshots store in `settings_portal_profile` with `portal_visible=true` filters. **|**
**Failures & handling:** Exposing masked fields triggers validation errors; portal blocks rendering until resolved. **|**
**Observability:** “Portal Settings” dashboard monitors lookup counts and cache hit ratios; alerts fire on mismatch between SR and portal caches. **|**
**References:** §2.5 Pipeline bundles, Appendix C seed bundles.
**Breadcrumbs:** Portal profile service `apps/platform/settings/services/portal_profile.py`, tests `tests/platform/settings/test_portal_profile.py`.

- Chat assistants mirror SR rate limits and token budgets; Settings updates propagate to portal warnings and UI pickers.

### 9.4 Worker pipelines & job manifests (binding)

**Purpose:** Ensure job pipelines consume SR snapshots consistently. **|**
**Contract:** Workers fetch settings before task execution, embed snapshot digests in manifests, and persist evidence to ops logs and audit JSONL. **|**
**State:** Snapshot references stored alongside job records and artifact manifests; drift detection cross-checks manifests. **|**
**Failures & handling:** Failed fetches block job start; backlog alerts fire when retrieval exceeds retry windows. **|**
**Observability:** “Worker Settings” panel tracks `settings_snapshot_job_total` and stale-snapshot alerts. **|**
**References:** §2.3 Snapshot contract, §5.2 Snapshot mismatch.
**Breadcrumbs:** Worker tasks `apps/platform/operations/tasks.py::hydrate_settings_snapshot`, tests `tests/platform/operations/test_settings_snapshot.py`.

______________________________________________________________________

## 10) References (informative)

- ADRs: ADR-0002 API Versioning & Sunset, ADR-0003 Localization & Policy Engine, ADR-0004 OPA Policy Plane. - TDD: TDD §5 Security Architecture, TDD §7 Settings Governance, TDD Appendix H Operational Guides.
- Runbooks: §8.3.2 RB-GOV-008, RB-RES-ENDPOINT, RB-RES-BLOCK, RB-JOB-WATCHDOG, RB-LOCK-006.
- Diagrams: `docs/platform/settings/diagrams/*.mmd`, `docs/overview/tdd/diagrams/data-lineage-v1.mmd`.
- Scripts & tooling: `python -m doc_tools.check_settings_keys`, `scripts/sdk/check_openapi_alignment.py`, `ops/scripts/settings_deploy.py`.
- Metrics dashboards: `infra/grafana/settings_slo.json`, `infra/grafana/settings_drift.json`, `infra/grafana/settings_enforcement.json`.

______________________________________________________________________

## Appendix A — Settings key map & traceability index {#appendix-a-settings-key-map-traceability-index}

**Purpose:** Link platform behaviour to Settings Registry configuration for audit and troubleshooting. **|**
**Contract:** Every key referenced in code, bundles, or docs appears here with scope, defaults, and enforcement notes; automation cross-checks ensure completeness. **|**
**State:** Maintained in version control; automation compares against `config/settings_definitions.json`, runtime validators, and seed bundles. **|**
**Failures & handling:** Missing mappings fail `python -m doc_tools.check_settings_keys`; authors update definitions and this appendix together. **|**
**Observability:** Docs lint metrics raise alerts on coverage gaps; release checklists block promotion when lint fails. **|**
**References:** §2 Responsibilities, Appendix C seed inventory.
**Breadcrumbs:** Script `python -m doc_tools.check_settings_keys`, tests `tests/docs/test_check_settings_keys.py`, dashboard “Docs – Settings Coverage”.

### A.0 SettingDefinition model (binding)

```python
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class SettingDefinition(BaseModel):
    key: str
    datatype: Literal["BOOL", "INT", "FLOAT", "STRING", "DURATION", "ENUM", "JSON", "REGION", "PERCENT"]
    enum_values: list[str] | None = None
    default_value: Any
    mutable_scope: list[Literal["SYSTEM", "ORG", "CASE"]]
    validation_schema: dict[str, Any] | None = None
```

### A.1 Key catalog (binding)

**Purpose:** Provide authoritative coverage of SR keys, scopes, defaults, and enforcement hooks. **|**
**Contract:** Keys listed here must exist in definitions, validators, and runtime usage; consumers reference this table instead of duplicating values elsewhere. **|**
**State:** Source-of-truth definitions live in `config/settings_definitions.json`; effective settings surface through `setting_effective` and `settings_snapshot` tables. **|**
**Failures & handling:** Divergence between documentation and schema blocks CI; activations referencing undocumented keys are rejected. **|**
**Observability:** Validators emit `settings_definition_gap_total`; lint dashboards flag omissions. **|**
**References:** §2 Responsibilities, §4 State management.
**Breadcrumbs:** Schema `packages/udocket_core/settings/schema.py`, tests `tests/platform/settings/test_definition_schema.py`.

| Key | Scope | Default | Description / Enforcement |
| --- | --- | --- | --- |
| `regions.allowlist.compute` | ORG | \[na-us-1, na-us-2\] | Allowed compute regions; enforced by §3.8. |
| `regions.allowlist.storage` | ORG | \[na-us-1, na-us-2\] | Allowed storage regions; enforced by §3.8 and §5.3. |
| `network.egress.allowed_hosts[]` | SYSTEM\|ORG | \[\] | Host allowlist rendered to ServiceEntry/AuthorizationPolicy; [`platform-runtime §3.2`](../platform/runtime.md#32-reference-manifests). |
| `analyze.model.id` | ORG\|CASE   | default profile | LLM model profile for Analyze lanes; see §8 and §6.3. |
| `analyze.token_ceiling` | ORG\|CASE   | 100000 | Max tokens per Analyze job; see §8.3. |
| `analyze.max_retries` | ORG\|CASE   | 2 | Retry budget per lane; see §6.3 QA loops. |
| `compose.model.id` | ORG\|CASE   | default profile | LLM model profile for Compose; see §8 and §6.4. |
| `compose.token_ceiling` | ORG\|CASE   | 100000 | Max tokens per Compose job; §8.3. |
| `compose.max_retries` | ORG\|CASE   | 2 | Retry budget per lane; §6.4. |
| `compose.policy.forbidden_patterns[]` | ORG | \[\] | Content forbids; §6.4 QA. |
| `compose.templates.client.template_id` | ORG | default | DOCX/MD template selection; §6.4. |
| `compose.templates.lawyer.template_id` | ORG | default | DOCX/MD template selection; §6.4. |
| `reviews.timeout_hours` | ORG | 72 | Approval escalation threshold (reminders/escalations); §11.2.3. |
| `reviews.backlog.alert_minutes` | ORG | 30 | Minutes before `QUEUED_FOR_REVIEW` items trigger reviewer escalation banners/alerts; §7.1.3, §11.1. |
| `sign.trust_roots[]` | SYSTEM\|ORG | \[\] | Trust roots for signing; §7.2. |
| `sign.tsa.endpoint` | SYSTEM\|ORG | null | TSA API endpoint; §7.2. |
| `sign.tsa.max_time_drift_secs` | SYSTEM | 5 | NTP drift tolerance; §7.2, [`platform-runtime §3.1`](../platform/runtime.md#31-environment-topology). |
| `security.tls.min_version` | SYSTEM | TLSv1.3 | Minimum TLS version for ingress; [`platform-runtime §3.4`](../platform/runtime.md#34-tls-posture). |
| `security.tls.cipher_profile` | SYSTEM | default | TLS cipher profile for ingress; [`platform-runtime §3.4`](../platform/runtime.md#34-tls-posture). |
| `security.tls.fips_mode` | SYSTEM | false | Enforce FIPS-approved cipher suites and modules; [`platform-runtime §3.4`](../platform/runtime.md#34-tls-posture), §7.2. |
| `security.tls.legacy_exceptions[]` | SYSTEM | \[\] | Temporary TLS 1.2 exceptions (≤30 days, alert at T-7); [`platform-runtime §3.4`](../platform/runtime.md#34-tls-posture), §9.2. |
| `db.pgbouncer.pool_mode` | SYSTEM | transaction | Allowed PgBouncer pooling mode (`transaction` default, `session` optional); [`platform-runtime §3.2`](../platform/runtime.md#32-reference-manifests). |
| `llm.providers[]` | SYSTEM\|ORG | \[\] | Provider catalog; §8.1. |
| `llm.models[]` | SYSTEM\|ORG | \[\] | Model catalog and fallback priorities; §8.1. |
| `llm.models.version_pin` | SYSTEM\|ORG | provider‑specific | Explicit provider model snapshot/version pin; §8.1/§8.5. |
| `llm.enforce_model_version` | ORG\|CASE   | true | Fail when provider model version drifts from pin; §8.1/§8.5. |
| `llm.moderation.enabled` | ORG | true | Enable automated input/output moderation; §8.4. |
| `llm.moderation.provider` | ORG | azure\|openai\|local                                         | Moderation provider selection; §8.4. |
| `llm.moderation.enforcement` | SYSTEM\|ORG | block | Enforcement mode: `block` (default) or `warn`; §8.4. |
| `llm.moderation.thresholds.toxicity` | ORG | 0.5 | Classification threshold; §8.4. |
| `llm.moderation.thresholds.self_harm` | ORG | 0.5 | Classification threshold; §8.4. |
| `llm.moderation.thresholds.sexual_content` | ORG | 0.5 | Classification threshold; §8.4. |
| `llm.moderation.thresholds.pii_reintroduction` | ORG | 0.5 | Classification threshold; §8.4. |
| `llm.byo.allowed` | ORG\|CASE   | false | Permit bring-your-own model endpoints; §8.1.3. |
| `llm.byo.evaluation_suite_id` | ORG | default | Evaluation suite applied to BYO providers; §8.1.3. |
| `llm.byo.vpc_endpoints[]` | ORG | \[\] | Allowed BYO endpoint hostnames (reconciled with mesh policies); §8.1.3. |
| `agents.langgraph.runner` | SYSTEM\|ORG | langgraph | Graph runner selection (`langgraph` or `linear`); §6.7.2. |
| `agents.langgraph.fallback_mode` | SYSTEM | false | Force manual drafting fallback; §6.7.2, App.D RB-LLM-003. |
| `speech.providers[]` | SYSTEM\|ORG | \[\] | Speech provider catalog (health, residency, parity evidence); §6.2.1. |
| `speech.jobs[]` | SYSTEM\|ORG | \[\] | Transcription job profiles and fallback chains; §6.2.1. |
| `speech.allow_preprocessing` | ORG\|CASE   | false | Permit loudness normalization/compression before transcription; §6.2.3. |
| `speech.require_locale_match` | ORG\|CASE   | true | Fail fast when provider lacks requested locale; §6.2.3. |
| `speech.detect_language.enabled` | ORG\|CASE   | false | Enable automatic source-language detection; §6.2.4. |
| `speech.multilingual_segments.enabled` | ORG\|CASE   | false | Emit language-tagged segments for code-switched audio; §6.2.4. |
| `speech.translation.enabled` | ORG\|CASE   | false | Allow generation of translated transcripts; §6.2.4. |
| `speech.translation.targets_default[]` | ORG | \[\] | Default target locales for translation requests; §6.2.4. |
| `speech.translation.provider` | ORG\|CASE   | null | Translation provider identifier; §6.2.4. |
| `speech.translation.glossary_set` | ORG\|CASE   | null | Reference Manager glossary bundle for translations; §6.2.4. |
| `speech.translation.max_parallel_targets` | ORG\|CASE   | 3 | Parallel translation limit per job; §6.2.4. |
| `speech.translation.allow_unverified_pairs` | ORG\|CASE   | false | Permit translation pairs not in the verified registry (waiver required); §6.2.3, §6.2.4. |
| `speech.translation.language_pair_overrides[]` | ORG\|CASE   | \[\] | Disable or remap specific source→target pairs for contractual/compliance reasons; §6.2.3, §6.2.4. |
| `chat.staff.enabled` | ORG\|CASE   | false | Enable staff Copilot assistant; §11.11. |
| `chat.staff.rate_limit.rpm` | ORG\|CASE   | 30 | Staff assistant requests per minute; §11.11. |
| `chat.staff.token_cap_daily` | ORG\|CASE   | 20000 | Staff assistant daily token budget; §11.11. |
| `chat.client.enabled` | ORG\|CASE   | false | Enable portal chat assistant; §11.11. |
| `chat.client.rate_limit.rpm` | ORG\|CASE   | 10 | Client assistant requests per minute; §11.11. |
| `chat.client.token_cap_daily` | ORG\|CASE   | 10000 | Client assistant daily token budget; §11.11. |
| `chat.session.max_active_per_user` | ORG\|CASE   | 2 | Concurrent chat sessions allowed per user; §11.11. |
| `chat.auto_disable_on_abuse` | ORG\|CASE   | true | Auto-disable assistants on policy violations; §11.11. |
| `chat.provider.profile` | ORG\|CASE   | null | LLM profile assignment for assistants; §8.1.4, §11.11. |
| `portal.chat.hipaa_allowed` | ORG | false | Permit client chat when HIPAA mode active; §11.11. |
| `portal.chat.export.enabled` | ORG\|CASE   | false | Allow client chat transcript exports; §11.11. |
| `notifications.in_app.rate_limit_per_minute` | ORG | 60 | In-app notification dispatch rate; §11.9. |
| `notifications.in_app.daily_cap` | ORG | 500 | In-app notification max per day; §11.9. |
| `llm.finops.monthly_cap_usd` | ORG | 0 (disabled) | Monthly LLM spend cap; §8.3, §13.4. |
| `jobs.watchdog.no_progress_minutes` | SYSTEM\|ORG | 5 | Minutes without heartbeat before watchdog warns; §10.2, §12.1, §8.3 entry [RB-JOB-WATCHDOG](../ops/runbooks.md#rb-job-watchdog). |
| `jobs.watchdog.timeout_minutes` | SYSTEM\|ORG | 15 | Minutes without heartbeat before watchdog fails the job; §10.2, §12.1, §8.3 entry [RB-JOB-WATCHDOG](../ops/runbooks.md#rb-job-watchdog). |
| `uploads.scan.engine` | SYSTEM | clamav | Malware engine used in the upload scan pipeline; §6.2, §12.1. |
| `uploads.scan.yara_ruleset_version` | SYSTEM | latest | Version tag for YARA rules synced from Security; §6.2. |
| `uploads.scan.timeout_seconds` | SYSTEM\|ORG | 120 | Max scan duration before treating file as suspicious and quarantining; §6.2, §8.3 entry [RB-UPLOAD-SCAN](../ops/runbooks.md#rb-upload-scan). |
| `uploads.scan.override_hashes[]` | SYSTEM\|ORG | \[\] | Temporary allowlist for known-clean artifacts while rules are tuned (dual approval, time-boxed); §8.3 entry [RB-UPLOAD-SCAN](../ops/runbooks.md#rb-upload-scan). |
| `uploads.enabled` | SYSTEM\|ORG | true | Toggle to accept new uploads; disabled during major scanner outages; §8.3 entry [RB-UPLOAD-SCAN](../ops/runbooks.md#rb-upload-scan). |
| `api.idempotency.ttl_hours` | SYSTEM | 24 | TTL for idempotency; §10.3. |
| `api.rate_limits.web.rpm_per_org` | SYSTEM\|ORG | 600 (guardrail 10-2000; activation validator enforces range) | Org RPM; §10.5. |
| `api.rate_limits.web.rpm_per_ip` | SYSTEM\|ORG | 300 (guardrail 10-2000) | IP RPM; §10.5. |
| `portal.download.rate_limits.user_rpm` | ORG | 60 (guardrail 10-2000) | Portal download/user; §10.5. |
| `portal.download.rate_limits.org_rpm` | ORG | 200 (guardrail 10-2000) | Portal download/org; §10.5. |
| `security.org_switch.step_up_required` | SYSTEM | true | Enforce step-up on privilege increase; §4.3. |
| `security.disclosure.contact` | SYSTEM | null | Security.txt contact; §14.9. |
| `security.disclosure.encryption_key_url` | SYSTEM | null | PGP key URL; §14.9. |
| `security.pentest.cadence` | SYSTEM | annual | Pentest schedule; §14.9. |
| `security.mfa.webauthn_required_roles` | ORG | \[\] | Roles requiring WebAuthn step-up (HIPAA mode); §2.2, §4.3. |
| `security.session.device_bind.ip_prefix_len_v4` | ORG | 24 | IPv4 prefix length for device binding; §4.3 (soft/hard modes). |
| `security.session.device_bind.ip_prefix_len_v6` | ORG | 48 | IPv6 prefix length for device binding; §4.3 (soft/hard modes). |
| `security.session.device_bind.mode` | ORG | "soft" | Device fingerprint reaction (`soft` or `hard`); §4.3. |
| `udlock.max_session_hold_seconds` | SYSTEM | 300 | Advisory lock hold time; App.D RB-LOCK-006. |
| `udlock.heartbeat.interval_seconds` | SYSTEM | 5 | Heartbeat period; App.D RB-LOCK-006. |
| `compliance.erasure_mode` | ORG | off | Hard-purge toggle for DSAR mode; §14.2.1. |
| `compliance.subject_hkdf_salt` | SYSTEM | managed secret | HKDF salt for DSAR subject hashing; §14.2.1. |
| `privacy.legal.matrix_version` | SYSTEM | semver | Data residency/legal matrix version; App.C. |
| `privacy.hipaa.enabled` | ORG | false | HIPAA override mode toggle; §2.2, §14.2, App.C. |
| `privacy.hipaa.bundle_version` | SYSTEM | semver | HIPAA policy bundle version pin; §2.2, App.C. |
| `privacy.hipaa.phi_detection.strict_mode` | ORG\|CASE   | true | Enforce layered PHI detection (waiver required to relax); §2.2. |
| `privacy.hipaa.phi_detection.rescan_hours` | ORG | 24 | Interval for scheduled PHI re-scan jobs; §2.2. |
| `i18n.supported_locales[]` | ORG | \[\] | Supported locales (BCP-47 codes) surfaced in UI toggles; must include at least one locale; §11.3. |
| `identity.org.primary_idp` | ORG | keycloak | Primary IdP assignment (`keycloak` or `external:<id>`); §4.1. |
| `storage.bucket_versioning_required` | SYSTEM | true | Bucket versioning must be enabled; §5.3, §12.1. |
| `storage.remote_hash.enabled` | ORG\|CASE   | false | Record remote hashes for batch inputs; §5.3. |
| `storage.remote_hash.max_mb` | ORG\|CASE   | 50 | Max remote bytes to hash; §5.3. |
| `settings.activation.require_dual_approval` | SYSTEM | true | Dual approval for unsafe changes; §9.3. |
| `logging.redaction.enabled` | SYSTEM | true | Redact PII in logs; [`Logging §4`](../platform/observability.md#4-state-management). |
| `logging.access.roles[]` | SYSTEM | \[\] | Role mapping for log query privileges (`observability.reader\|engineer\|auditor`); [`Logging §6`](../platform/observability.md#6-access-control--auditing). |
| `logging.cost.daily_budget_mb_per_service` | SYSTEM\|ORG | 500 | Daily log volume budget per service; [`Logging §7`](../platform/observability.md#7-cost-management--budgets). |
| `logging.cost.alert_threshold_pct` | SYSTEM\|ORG | 80 | Alert threshold as % of daily log budget; [`Logging §7`](../platform/observability.md#7-cost-management--budgets). |
| `logging.level.default` | SYSTEM | "INFO" | Default production log level; [`Logging §7`](../platform/observability.md#7-cost-management--budgets). |
| `logging.level.overrides[]` | ORG | \[\] | Per-service log level overrides; [`Logging §7`](../platform/observability.md#7-cost-management--budgets). |
| `portal.logging.enabled` | ORG | true | Enable client telemetry capture; [`Logging §4.2`](../platform/observability.md#42-client--portal-telemetry). |
| `evidence_store.redacted_excerpts.enabled` | ORG | true | Allow storage of prompt/response excerpts; HIPAA enable guard forces false and triggers purge; §2.2, §8.2. |
| `logging.immutable_sink.enabled` | SYSTEM | true (prod) | Mirror structured logs to immutable storage alongside the audit sink; validators block `false` in production and mark overrides unsafe (§9.11, [`Audit §4`](../data/audit.md#4-immutable-storage--replication)). |
| `llm.finops.guard.threshold_pct` | SYSTEM\|ORG | 10 | MoM regression ceiling for deploy gate; §8.7, §13.5. |
| `llm.finops.guard.trailing7d_pct` | SYSTEM\|ORG | 25 | Trailing 7-day burn ceiling (% of monthly cap) for deploy gate; §8.7, §13.5. |
| `llm.finops.override_until` | SYSTEM | null | Optional timestamp (max +72h) to temporarily relax FinOps guard (dual approval required); §8.7. |

### A.2 Traceability map (normative)

**Purpose:** Show which platform surfaces depend on each key family so audits can confirm coverage. **|**
**Contract:** Every consumer references the relevant bundle IDs listed here; additions require updating this map and associated tests. **|**
**State:** Enforcement registry stored in `settings_enforcement_point` with bundle-to-service mappings. **|**
**Failures & handling:** Missing mappings trigger lint failures and synthetic alert `settings_enforcement_lookup_total{status="missing"}`. **|**
**Observability:** Adoption dashboards display bundle coverage per service. **|**
**References:** §9.1 Enforcement touchpoints, Appendix B metrics.
**Breadcrumbs:** Enforcement registry `apps/platform/settings/services/enforcement.py`, tests `tests/platform/settings/test_enforcement_points.py`.

- Agents → `analyze.*`, `compose.*`, `llm.*` (TDD §6, §8).
- Guardian → `guardian.*` (judgment policies; see Services · Guardian).
- Signer → `sign.*` (digital signature policies; TDD §7).
- Storage & integrity → `storage.*`, `logging.*` (TDD §5, §12).
- Portal & client UX → `portal.*`, `i18n.*`, `chat.*`, `security.*` (TDD §11).
- APIs & rate limits → `api.*`, `uploads.*`, `notifications.*` (TDD §10, §11.9).
- Operations & governance → `udlock.*`, `privacy.*`, `security.pentest.*`, `logging.*` (§8.3 procedures, TDD §12, §14).

### A.3 Linting & parity gates (binding)

**Purpose:** Ensure SR documentation, schemas, and runtime references remain in lockstep. **|**
**Contract:** CI fails when settings keys referenced in code lack appendix coverage or when appendix keys lack schema/tests. **|**
**State:** Lint scripts load this appendix, inspect OpenAPI/spec/config usage, and compare against registry definitions. **|**
**Failures & handling:** Any mismatch fails `settings:lint-keys`; update definitions, tests, and this appendix atomically. **|**
**Observability:** CI dashboards track lint duration and failure rate. **|**
**References:** §2 Responsibilities, §8.3 Tooling & automation.
**Breadcrumbs:** Script `python -m doc_tools.check_settings_keys`, tests `tests/docs/test_lint_rules.py`.

- Regions & residency → `regions.allowlist.*`, `privacy.*`; validated by residency scanners and RM catalog ingest.
- APIs & rate limits → `api.*`, `portal.download.*`; OpenAPI spectral rules enforce header/limit parity.
- FinOps → `llm.finops.*`; drift detection jobs surface monthly spend anomalies.
- Security & compliance → `security.*`, `logging.redaction.*`, `compliance.*`; test suites enforce RLS/masking.
- Ops & locks → `udlock.*`; advisory lock registry and §8.3 entries confirm enforcement.

### A.4 Activation checklist (binding)

**Purpose:** Provide the required evidence when promoting a settings bundle. **|**
**Contract:** Every activation records justification, reviewers, validator outputs, and rollout timeline before promotion; missing artifacts keep activations unsafe. **|**
**State:** Activation metadata resides in `settings_activation`, approvals in `settings_activation_approval`, waivers in `settings_waiver` with App.O decision log links. **|**
**Failures & handling:** Missing checklist items mark the activation `unsafe`; promotion halts until evidence supplied. **|**
**Observability:** Governance dashboard highlights incomplete activations; alert `settings_governance_override_total` pages owners. **|**
**References:** §4 State management, §5 Failure modes, §8.3.2 RB-GOV-008.
**Breadcrumbs:** Activation service `apps/platform/settings/services/activation.py`, tests `tests/platform/settings/test_activation_flow.py`.

Checklist items:

1. Link to change ticket, ADR (if applicable), and decision log entry.
2. Attach validator results (`unsafe_reasons[]`, residency, safety, cost) and diff preview hashes.
3. Confirm dual approval requirements (Security + Architecture) met for protected scopes.
4. Record rollout plan, blast radius, and rollback window; attach staging dry-run evidence.
5. Store bundle, activation JSON, and diff artifacts under `ops/settings/<date>/`.

### A.5 Change log handoff (informative)

**Purpose:** Maintain a rolling history of key modifications discoverable for audits. **|**
**Contract:** Each production activation with customer impact appends an entry summarizing scope, bundle ID, approvals, and evidence pointers. **|**
**State:** Change log lives beside this document (`ops/settings/change_log.md`) and mirrors into App.O decision logs. **|**
**Failures & handling:** Missing change-log entries trigger release checklist failures; add entries with backdated evidence before closing the change. **|**
**Observability:** Weekly docs lint verifies latest activations appear in the log. **|**
**References:** §4 Activation pipeline, §8 Operational notes.
**Breadcrumbs:** Change log `ops/settings/change_log.md`, tests `tests/platform/settings/test_change_log.py`.

## Appendix B — Metrics & alerts {#appendix-b-metrics-alerts}

**Purpose:** Define the telemetry set that proves SR health, governance controls, and security posture. **|**
**Contract:** Metrics and alerts enumerated here must exist in production dashboards; owners keep thresholds aligned with SLOs and audit requirements. **|**
**State:** Metrics emit via OpenTelemetry exporters from the Settings service and background jobs; alerts live in Grafana OnCall. **|**
**Failures & handling:** Missing metrics or stale thresholds block release checklists; on-call reviews incidents weekly to confirm coverage. **|**
**Observability:** Dashboards — “Settings Registry – Availability”, “Settings Governance”, “Settings Compliance”, “Settings Integrations”. **|**
**References:** §6 Observability, tables below.
**Breadcrumbs:** Telemetry module `apps/platform/settings/telemetry.py`, tests `tests/platform/settings/test_metrics.py`.

### B.1 Service health (binding)

| Metric / Alert | Description | Owner |
| --- | --- | --- |
| `settings_request_total{result}` | Request volume by outcome (`success`, `error`, `unauthorized`, `denied`) | SRE |
| `settings_latency_seconds{route}` | Histogram + SLO burn tracking for read/write endpoints | SRE |
| `settings_cache_hit_ratio` | Redis/local cache hit percentage; alert when \< 0.9 | Platform Architecture |
| `settings_cache_invalidation_lag_seconds` | Duration from activation publish to cache flush across nodes | SRE |
| `settings_snapshot_issued_total{scope}` | Snapshots delivered to workers, portal, Guardian, LPE | Platform Architecture |
| `settings_snapshot_drift_total{detector}` | Drift findings comparing embedded snapshot hashes vs effective values | SRE |
| `settings_enforcement_lookup_total{status}` | Enforcement touchpoints (required/optional/missing) used by downstream services | Platform Architecture |

### B.2 Governance & security (binding)

| Metric / Alert | Description | Owner |
| --- | --- | --- |
| `settings_activation_total{result}` | Activation outcomes (`success`, `unsafe`, `rollback`) powering release gates | Settings Program |
| `settings_activation_duration_seconds` | Activation execution latency (start→publish) by bundle type | Settings Program |
| `settings_validation_failure_total{reason}` | Validator failures grouped by guardrail (`residency`, `safety`, `finops`, `schema`) | Settings Program |
| `settings_dual_approval_total{bundle}` | Dual-approval events by protected bundle category | Security Engineering |
| `settings_waiver_active_total{expiry_window}` | Active waiver counts bucketed by days to expiry | Security Engineering |
| `settings_auth_failure_total{stage}` | Failed HMAC signature or token authentication attempts against the Settings API | Platform Architecture |
| `settings_secret_read_total{role}` | Secret/config read requests segmented by authorized role | Security Engineering |
| `settings_audit_event_total{kind}` | Structured audit entries emitted (activation, waiver, rollback, drift) | Security Engineering |
| `settings_compliance_violation_total{category}` | Compliance guard hits (HIPAA, DSAR, residency) that block activations | Security Engineering |
| `settings_integration_sync_total{target}` | Sync runs to Guardian, LPE, Reference Manager, portal, and worker manifests | Platform Architecture |
| `settings_incident_open_total{severity}` | Open incidents tied to Settings alerts/procedures | SRE |

Alert hooks include `settings_availability_breach`, `settings_activation_delay`, `settings_governance_override_total`, `settings_auth_failure_spike`, and `settings_secret_access_anomaly`; each alert links to §8.3 procedures.

## Appendix C — Seed bundle inventory

**Purpose:** Document the curated seed bundles shipped with SR for environment bootstrap and testing. **|**
**Contract:** Bundles listed here must remain validated by CI and kept in sync with schema and agent expectations; edits follow the activation workflow. **|**
**State:** Bundles live under `config/` and `config/agents.pipeline/` with checksums recorded in `settings_seed_history`. **|**
**Failures & handling:** Validation failures block merges and deployments; update bundles, validators, and associated tests together. **|**
**Observability:** CI job `settings-seed-validate` reports status; dashboards track bundle ingestion and checksum drift. **|**
**References:** §2.8 Seed bundles, Appendix C inventory table below.
**Breadcrumbs:** Seed scripts `ops/scripts/bootstrap_platform.py`, tests `tests/platform/settings/test_seed_bundles.py`.

| Bundle | Location | Purpose | Validation |
| --- | --- | --- | --- |
| `bootstrap_defaults.json` | `config/` | System defaults for general operation | `ops/scripts/bootstrap_platform.py` + schema validators |
| `guardian_defaults.json` | `config/` | Guardian-specific knobs consumed via SR | Guardian integration tests |
| `analyze_defaults.json` | `config/` | Analyze agent pipeline defaults | Agent contract tests |
| `llm_assignments.json` | `config/` | LLM profile assignments | `tests/platform/settings/test_llm_profiles.py` |
| `llm_providers.json` | `config/` | Provider catalog entries | `tests/platform/settings/test_llm_profiles.py` |
| `agents.pipeline/*.json` | `config/agents.pipeline/` | LangGraph pipeline manifests and rollouts | `tests/platform/settings/test_pipeline_bundle.py` |
