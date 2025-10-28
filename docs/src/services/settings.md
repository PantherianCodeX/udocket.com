---
title: uDocket — Settings Registry Technical Design
subtitle: Configuration Governance & Activation Specification
author:
  - uDocket Platform Architecture Team
  - Settings Program Leads
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-23
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
adr_index: docs/adr/README.md
related_adrs:
  - ADR-0003-api-versioning-and-sunset.md
  - ADR-0004-localization-and-policy-engine.md
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

## 5) Failure modes (binding)

**Purpose:** Capture the primary ways SR can degrade and the responses required to keep configuration trustworthy.\
**Contract:** SR must fail closed on unsafe activations, drift, or residency violations; manual overrides require documented waivers and adherence to Appendix R runbooks.\
**State:** Incidents log in `ops/guardian/incidents/` (shared format), `settings_drift_finding`, and `settings_activation` status fields.\
**Failure modes & handling:** Validator failures, snapshot mismatches, and residency drift each trigger dedicated runbooks detailed below.\
**Observability:** Alerts on `settings_activation_unsafe_total`, `settings_snapshot_mismatch_total`, and `settings_residency_violation_total` page on-call responders.\
**References:** §4 State management, §6 Observability, Appendix R RB-GOV-008/RB-RES-*/RB-LOCK-006.\
**Breadcrumbs:** Incident automation `ops/scripts/guardian/*.py` (shared framework), drift detector `apps/platform/settings/telemetry.py`, residency validators `apps/platform/settings/validators/residency.py`.

### 5.1 Activation validator failure (binding)

**Purpose:** Address situations where validators block an activation.\
**Contract:** Unsafe activations remain `READY_FOR_REVIEW` with `unsafe_reasons[]`; teams must remediate data or apply approved waivers before reenabling.\
**State:** Unsafe details recorded in `settings_activation_validation`; approvers annotate mitigation steps.\
**Failure modes & handling:** Runbook RB-GOV-008 outlines rollback, manual review, and dual approval flow; automation freezes subsequent activations until the incident closes.\
**Observability:** Alerts `settings_activation_unsafe_total` and SLO burn-rate alarms escalate to Architecture/Security.\
**References:** §4.1 Activation pipeline, §4.3 Dual approval, Appendix R RB-GOV-008.\
**Breadcrumbs:** Validation services `apps/platform/settings/services/validation.py`, tests `tests/platform/settings/test_activation_flow.py::test_pipeline_rejects_invalid`.

### 5.2 Snapshot mismatch & drift (binding)

**Purpose:** Respond to mismatched digests or drift between stored snapshots and effective configuration.\
**Contract:** Consumers halt mutating operations when `settings_snapshot_mismatch_total` > 0 and fetch fresh snapshots; SR reconciles drift before resuming activations.\
**State:** Drift findings persist in `settings_drift_finding` with remediation tickets and timestamps.\
**Failure modes & handling:** RB-RES-ENDPOINT and RB-JOB-WATCHDOG guide reconciliation; SR may replay last known good bundle or regenerate snapshots.\
**Observability:** “Settings Drift” dashboard, alerts `settings_snapshot_mismatch_total`, and synthetic fetches confirm when drift resolves.\
**References:** §2.3 Snapshot contract, §6 Observability, Appendix R RB-RES-ENDPOINT/RB-JOB-WATCHDOG.\
**Breadcrumbs:** Telemetry module `apps/platform/settings/telemetry.py`, tests `tests/platform/settings/test_drift.py`.

### 5.3 Residency enforcement incident (binding)

**Purpose:** Outline remediation when residency controls fail or new endpoints appear.\
**Contract:** Activations must block until Reference Manager catalogs align; waivers require Security + Architecture approval with manifest stamping.\
**State:** Residency findings recorded in `settings_residency_profile` and incident logs; waivers tracked with expiry.\
**Failure modes & handling:** RB-RES-BLOCK and RB-RES-ENDPOINT guide containment, catalog sync, and waiver approval; Guardian cross-checks waivers before judgments resume.\
**Observability:** Alerts `settings_residency_violation_total`, audit events `RESIDENCY_ENDPOINT_NEW`, and Security tickets `SEC-RESIDENCY-ENDPOINT` drive follow-up.\
**References:** §2.4 Residency & egress, §7 Security & compliance, Appendix R RB-RES-* runbooks.\
**Breadcrumbs:** Validators `apps/platform/settings/validators/residency.py`, tests `tests/platform/settings/test_residency_validators.py`.

______________________________________________________________________

**Audience:** Platform engineering, Guardian, Localization & Policy Engine, Reference Manager, SRE, QA, Product Operations\\

**Purpose:** Define Settings Registry (SR) responsibilities, contracts, activation lifecycle, and observability so every service consumes consistent, auditable configuration.

______________________________________________________________________

## Document controls

| Field           | Value                                                                                                                            |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Version         | 0.1-draft                                                                                                                        |
| Status          | Implementable (mirrors front matter `status`; KEP lifecycle applies: Provisional → Implementable → Implemented)                  |
| Last updated    | 2025-10-23 (source of truth is the front matter `last_updated`)                                                                  |
| Primary owners  | Platform Architecture; Security Engineering; Settings Program                                                                    |
| Approvers       | Architecture Steering Committee; Security Review Board                                                                           |
| Reviewers       | QA Engineering Lead; SRE Manager                                                                                                 |
| ADR index       | `docs/adr/README.md` (immutable ADRs referenced in front matter `related_adrs`)                                                  |
| Migration plan  | Supersede legacy TDD §9 and Appendix E once Architecture/Security approvals record; platform TDD now links here for SR specifics |
| Docs validation | `python scripts/docs/lint_docs.py` (see `docs/README.md` for tooling)                                                            |
| Link lint       | `python scripts/docs/link_check.py --strict` (CI `docs-link-check` stage blocks unresolved §/App./ADR refs)                      |

Body sections follow the Purpose/Contract/State/Failure/Observability/Breadcrumb scaffold enforced by `scripts/docs/lint_docs.py --check-template`. Section tags `(binding)` and `(normative)` align with the platform TDD.

______________________________________________________________________

## 0) Reading guide

- **Scope:** Service charter, hierarchical model, API/SDK contracts, activation workflow, governance controls, integrations, telemetry, and key catalog for the Settings Registry.
- **Structure:** Numbered sections limited to three levels of depth; appendices surface detailed key maps, metrics, and seed bundle references.
- **Cross-references:** Use `§<number>` for this document, `TDD §<number>` for the platform TDD, and `App.<letter>` when pointing at appendices.
- **Maintenance:** Run `python scripts/docs/lint_docs.py` before submitting edits. Schema snippets must match `spec/schemas/*` fixtures; CI enforces parity for key catalogs and activation templates.
- **Doc change protocol:** Any PR modifying SR APIs, activation logic, bundle schemas, or governance gates must update this document and cite relevant ADRs. Architecture/Security reviewers block merges when code, SDKs, or docs diverge.

______________________________________________________________________

## 1) Purpose

**Purpose:** Establish the Settings Registry (SR) as the canonical configuration service for every platform scope.\
**Contract:** SR centralizes system, organization, and case configuration, publishes audited activations, and emits immutable snapshots that downstream services must embed and honor.\
**State:** Configuration persists in Postgres tables (`setting_bundle`, `setting_bundle_version`, `setting_activation`) with Redis caches keyed by `(scope, org_id, case_id, bundle_id)`; adoption status lives in `settings_consumer_adoption`.\
**Failure modes & handling:** Validator failures or long-held advisory locks force SR into read-only mode; consumers rely on embedded snapshots until remediation (see §5).\
**Observability:** Availability SLO 99.9%, metrics `settings_request_total`, `settings_error_total`, and `settings_activation_total{result}` feed the “Settings Registry – Availability” dashboard; traces annotate `settings_version` and `activation_id`.\
**References:** §2 Responsibilities, §3 API contract, §4 State management, §6 Observability, ADR-0003, ADR-0004.\
**Breadcrumbs:** Implementation `apps/platform/settings/service.py::create_app`, Tests `tests/platform/settings/test_charter.py::test_scope_enforced`, Grafana “Settings Registry – Availability”.

- SR governs configuration inheritance, residency allowlists, FinOps ceilings, LLM profiles, Guardian/Signer guards, and UI feature flags.
- Lifecycle changes flow through ADRs; structural edits require dual Architecture/Security approval.
- Downstream systems must cite snapshot digests in manifests, telemetry, and audit logs to preserve reproducibility.

### 1.1 Charter & mandate (binding)

**Purpose:** Detail the charter that defines SR’s scope and success criteria.\
**Contract:** SR owns configuration authoring, validation, activation, and distribution across all scopes; it guarantees determinism and traceable history for every activation.\
**State:** Bundles, versions, activations, and advisory lock records reside in Postgres; caches mirror effective configuration for hot reads.\
**Failure modes & handling:** Unsafe activations drop SR into read-only mode until validators pass; existing jobs continue with embedded snapshots.\
**Observability:** Request/error counters, activation metrics, and traces capture throughput and failure reasons.\
**References:** §2 Responsibilities, §4 State management, Appendix A.\
**Breadcrumbs:** Service bootstrap `apps/platform/settings/service.py`, schema `packages/udocket_core/settings/schema.py`, tests `tests/platform/settings/test_charter.py`.

- Governs inheritance rules, scope guardrails, and immutable keys (for example residency) that lower scopes cannot relax.
- Maintains dual-track lifecycle (draft → reviewed → activated) mirrored in ADR status.
- Publishes change events (`settings.changed`, `settings.snapshot_issued`) for consumers.

### 1.2 Stakeholders & integrations (normative)

**Purpose:** Identify SR’s consumers and integration touchpoints.\
**Contract:** Guardian, LPE, Reference Manager, Portal, Workers, Ops tooling, and Observability must fetch snapshots, record digests, and respect invalidation events before mutating state.\
**State:** Adoption telemetry in `settings_consumer_adoption` tracks bundle/version uptake; integration sync jobs persist status in `settings_integration_status`.\
**Failure modes & handling:** Missed invalidations trigger drift detectors and synthetic fetches; consumers block risky operations until snapshots refresh.\
**Observability:** “Settings Registry – Consumer Adoption” dashboard charts `settings_snapshot_issued_total`, `settings_snapshot_stale_total`, and invalidation latency.\
**References:** §2 Responsibilities, §6 Dependencies, Appendix B.\
**Breadcrumbs:** Client library `apps/platform/settings/clients.py`, adoption jobs `apps/platform/settings/tasks.py`, tests `tests/platform/settings/test_client_contract.py`.

- Guardian enforces judgment flows using SR-configured policies and waivers.
- LPE activation dry-runs invoke SR validators to ensure residency/localization coherence.
- Workers embed `settings_snapshot_sha256` and `settings_version_id` in manifests and telemetry.
- Portal and staff UI honor SR toggles for feature availability, localization hints, and approval flows.

### 1.3 Service-level objectives (binding)

**Purpose:** Capture SR’s reliability targets and deployment guardrails.\
**Contract:** Maintain 99.9 % availability, read p95 latency ≤ 120 ms, activation completion p95 ≤ 2 minutes, and cache invalidation propagation ≤ 60 seconds; exceeding burn-rate thresholds freezes activations.\
**State:** Error budget tracking persists in `sre_error_budget` with monthly burn-rate snapshots; release gates consult these metrics.\
**Failure modes & handling:** Burn rate > 1.0 for 60 minutes halts blue/green promotion; SLO breaches invoke RB-GOV-008 (Appendix R).\
**Observability:** Synthetic monitors exercise read and activation APIs per deploy; alerts `settings_availability_breach` and `settings_activation_delay` gate releases.\
**References:** §6 Observability, Appendix B, Appendix R.\
**Breadcrumbs:** Helm chart `infra/kubernetes/settings/`, SLO tests `tests/synthetics/test_settings_slo.py`, Grafana “Settings Registry – SLO”.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Describe the functional areas SR owns—from scope resolution through agent configuration—so teams understand what lives inside the registry.\
**Contract:** SR defines schemas, validates inputs, manages precedence, and publishes bundles for services, agents, and UI surfaces while enforcing governance and residency guardrails.\
**State:** Definitions, bundles, and effective values live in Postgres (`setting_definition_schema`, `setting_bundle`, `setting_effective`) with companion JSON artifacts under `config/` and `ops/settings/`.\
**Failure modes & handling:** Invalid overrides, unknown keys, or failed validators reject activations and block dependent workflows until corrected (see §5).\
**Observability:** Scope mix, validation failure, and bundle adoption metrics feed “Settings – Scope Mix” and “Settings – Validation” dashboards.\
**References:** §3 API contract, §4 State management, Appendix A, Appendix C.\
**Breadcrumbs:** Models `apps/platform/settings/models.py`, schema `packages/udocket_core/settings/schema.py`, governance services `apps/platform/settings/services/`.

### 2.1 Hierarchical scopes & precedence (binding)

**Purpose:** Explain how configuration inherits and overrides safely across tenants.\
**Contract:** SR resolves effective configuration by overlaying CASE over ORG over SYSTEM scopes with explicit precedence, immutable keys, and validator-enforced guardrails.\
**State:** Effective values materialize into `setting_effective` with foreign keys to contributing bundle versions; ancestry is persisted for audit drill-down.\
**Failure modes & handling:** Invalid overrides (for example, CASE relaxing residency) raise `SETTINGS_INVALID_OVERRIDE`; activations fail until corrected.\
**Observability:** Metric `settings_scope_resolution_total` tracks override mix; traces include contributing scope chains.\
**References:** Appendix A key catalog, §4 State management.\
**Breadcrumbs:** Implementation `apps/platform/settings/models.py::Scope`, tests `tests/platform/settings/test_scope_precedence.py`.

- Sensitive keys (secrets, trust roots) remain encrypted at rest; read APIs redact secrets while activation history retains digests.
- Bundles include schema metadata referencing Appendix A for key catalog and defaults.
- Certain keys enforce immutability at lower scopes (residency, immutable logging sinks) and rely on validator guardrails.

### 2.2 Definition schema & validation (binding)

**Purpose:** Define the schema that enforces data types, constraints, and documentation for settings keys.\
**Contract:** All definitions use the shared `SettingDefinition` model with literal datatypes, scope guards, default values, documentation strings, and validator hooks; CI checks block unknown or malformed keys.\
**State:** Definitions load from `config/settings_definitions.json` and compile into versioned JSON Schema artifacts stored in `setting_definition_schema`.\
**Failure modes & handling:** Missing or malformed definitions fail `python scripts/docs/check_settings_keys.py` and production activations; authors must update schema before merging.\
**Observability:** Metric `settings_validation_failure_total` categorizes error reasons; audit logs attach schema version IDs.\
**References:** Appendix A key catalog, Appendix C seed bundles.\
**Breadcrumbs:** Schema implementation `packages/udocket_core/settings/schema.py`, tests `tests/platform/settings/test_definition_schema.py`.

- Case-scoped keys include agent prompt overrides, retry ceilings, visibility toggles, and portal expiry limits.
- System/org keys cover residency allowlists, quotas, notifications, TLS policy, encryption posture, FinOps thresholds, and enumerations for cases and artifacts.
- Privacy helpers publish templates via `/api/v1/settings/privacy/templates`, ensuring DPIA/RoPA tooling aligns with Appendix C (platform TDD).

### 2.3 Snapshot & manifest contract (binding)

**Purpose:** Ensure downstream services embed immutable configuration context.\
**Contract:** Snapshots include `{version_id, bundle_ids[], contributing_scopes[], sha256}`; consumers persist digests in manifests, telemetry, and audit logs to guarantee reproducibility.\
**State:** Snapshot records reside in `settings_snapshot` and attach to jobs, artifacts, and policy contexts via foreign keys; digests mirror compiled outputs.\
**Failure modes & handling:** Snapshot mismatches trigger drift incidents; workers block new jobs until refreshed snapshots arrive or incidents are resolved.\
**Observability:** Dashboard “Settings – Snapshot Integrity” tracks `settings_snapshot_mismatch_total` and `settings_snapshot_stale_total`.\
**References:** §4 State management, Appendix B metrics.\
**Breadcrumbs:** Implementation `packages/udocket_core/settings/snapshot.py`, tests `tests/platform/settings/test_snapshot_contract.py`.

- Every job manifest includes `settings_snapshot_sha256` and `settings_version_id` for replay.
- Guardian, Portal, and Workers log snapshot digests within structured events for traceability.

### 2.4 Residency & egress controls (binding)

**Purpose:** Capture residency, egress, and waiver rules enforced by SR.\
**Contract:** SR validates `regions.allowlist.*`, `network.egress.allowed_hosts`, and residency waivers against Reference Manager catalogues prior to activation; unsafe changes require dual approval and manifest stamping.\
**State:** Residency metadata persists in `settings_residency_profile` cross-linked to RM bundles and waiver records.\
**Failure modes & handling:** Missing catalog entries raise `RESIDENCY_ENDPOINT_NEW`; activations stay blocked until RM ingestion completes or waiver approved.\
**Observability:** Audit events `RESIDENCY_ENDPOINT_NEW`, metric `settings_residency_violation_total`, and nightly drift scans enforce compliance.\
**References:** §7 Security & compliance, Appendix R RB-RES-* runbooks.\
**Breadcrumbs:** Validators `apps/platform/settings/validators/residency.py`, tests `tests/platform/settings/test_residency_validators.py`.

- Change detection opens Security tickets (`SEC-RESIDENCY-ENDPOINT`) and requires dual approval for temporary waivers.
- Closure requires two consecutive compliant scans before incidents resolve; evidence attaches to decision log entries.

### 2.5 Pipeline bundles & staged overrides (binding)

**Purpose:** Externalize LangGraph pipeline composition, prompts, and ceilings into audited configuration.\
**Contract:** Keys `agents.pipeline.definitions[]`, `agents.pipeline.assignments[]`, `agents.pipeline.overrides[]`, `agents.prompts.*`, and `agents.llm_profiles.*` define pipeline manifests, assignments, overrides, prompts, and LLM profiles with validator-enforced bounds.\
**State:** Pipeline definitions live in `settings_pipeline_definition`; rollouts track in `settings_pipeline_rollout` with wave metadata and change tickets.\
**Failure modes & handling:** Invalid prompt references, tool IDs, or ceiling relaxations raise validation errors; activations remain blocked until corrected.\
**Observability:** “Agent Pipeline Rollouts” dashboard charts rollout state, prompt revisions, and cost ceilings; job telemetry logs `pipeline_definition_version`.\
**References:** Appendix C seed bundles, §4 State management.\
**Breadcrumbs:** Implementation `apps/platform/settings/services/pipeline_bundle.py`, tests `tests/platform/settings/test_pipeline_bundle.py`.

- Assistant knobs (`assistant.retrieval.sources[]`, `assistant.moderation.tiers[]`, `assistant.citation.style`) share validator framework ensuring alignment with shared assets.
- Activations altering definitions or rollouts tag `change_class="system"`, require change ticket linkage, and follow blue/green rollout gates.

### 2.6 Tool catalog & capability gating (binding)

**Purpose:** Govern LangGraph tool introduction and exposure per tenant.\
**Contract:** Keys `agents.tools.catalog[]`, `agents.tools.allowlist[]`, and `agents.tools.policies.*` register tools, expose allowlists, and enforce residency/classification ceilings; overrides require dual approval.\
**State:** Catalog entries persist in `settings_tool_catalog`; allowlists live in `settings_tool_allowlist` per scope with waiver metadata.\
**Failure modes & handling:** Schema mismatches or attempts to widen residency/cost ceilings raise validation errors; forced overrides demand waiver records.\
**Observability:** “Agent Tooling” panel tracks invocation counts, error rates, and cost estimates; audit logs live under `ops/tools/ops_tools.jsonl`.\
**References:** §6 Dependencies, Appendix A tool catalog.\
**Breadcrumbs:** Catalog sync `apps/platform/settings/services/tool_catalog.py`, tests `tests/platform/settings/test_tool_catalog.py`.

- `GET /api/v1/settings/tools/catalog` returns effective catalog JSON for operators and editors.

### 2.7 LLM profiles & moderation controls (normative)

**Purpose:** Manage provider catalogs, version pins, moderation thresholds, and BYO vetting.\
**Contract:** Keys `llm.providers[]`, `llm.models[]`, `llm.models.version_pin`, `llm.enforce_model_version`, `llm.moderation.*`, and `llm.byo.*` define provider usage and compliance requirements; BYO entries demand validated evaluation suites.\
**State:** Provider/model metadata resides in `settings_llm_profile`; BYO endpoints cross-reference Reference Manager catalogs and residency policies.\
**Failure modes & handling:** Version drift or missing evaluation IDs block activations; moderation thresholds outside guardrails require waiver review.\
**Observability:** “LLM Profile Adoption” dashboard tracks `llm_profile_assignment_total`, moderation enforcement, and BYO utilization.\
**References:** §6 Dependencies, Appendix C seed bundles.\
**Breadcrumbs:** Implementation `apps/platform/settings/services/llm_profiles.py`, tests `tests/platform/settings/test_llm_profiles.py`.

### 2.8 Seed bundles & no-code configuration (binding)

**Purpose:** Enable environment bootstrap without code changes using validated JSON bundles.\
**Contract:** Repo ships versioned seed bundles ingested through SR with identical validators to runtime activation; operators edit JSON, run validators, and activate bundles through the standard pipeline.\
**State:** Seeds live under `config/` with metadata `{version, source_commit, checksum}`; ingestion records persist in `settings_seed_history`.\
**Failure modes & handling:** Seeds referencing unknown keys or out-of-range values fail validation; CI (`settings-seed-validate`) blocks merges until corrected.\
**Observability:** CI artifacts capture validation reports; deployment automation logs ingestion status and checksum verification.\
**References:** Appendix C seed inventory, §4 Activation pipeline.\
**Breadcrumbs:** Bootstrap script `ops/scripts/bootstrap_platform.py`, tests `tests/platform/settings/test_seed_bundles.py`.

______________________________________________________________________

## 3) API contract

**Purpose:** Document SR’s programmatic interfaces and client expectations for distributing configuration.\
**Contract:** REST APIs, SDK helpers, and signing requirements deliver configuration with immutable version metadata and deterministic idempotency rules.\
**State:** OpenAPI definitions live in `ops/openapi/settings.openapi.yaml`; SDKs wrap REST endpoints with caching and snapshot persistence.\
**Failure modes & handling:** Signature mismatches, stale caches, or idempotency conflicts return explicit errors and require client remediation.\
**Observability:** “Settings API”, “Settings Client Cache”, and “Settings Auth” dashboards monitor traffic, cache hit ratio, and auth errors.\
**References:** §2 Responsibilities, §4 State management, Appendix A key catalog.\
**Breadcrumbs:** API implementation `apps/platform/settings/api.py`, client `packages/udocket_core/settings/client.py`, security helpers `apps/platform/settings/security.py`.

### 3.1 REST endpoints (binding)

**Purpose:** Define SR REST APIs and required behaviour.\
**Contract:** SR exposes `GET /api/v1/settings/<scope>`, `GET /api/v1/settings/bundles/<id>`, `POST /api/v1/settings/bundles`, and `/api/v1/settings/validate/*`; responses include version metadata, contributing scopes, and snapshot digests.\
**State:** OpenAPI definitions live in `ops/openapi/settings.openapi.yaml`; generated clients stay aligned via `scripts/sdk/check_openapi_alignment.py`.\
**Failure modes & handling:** Idempotency enforced via advisory locks; conflicting activations yield `409` with retry-after guidance.\
**Observability:** “Settings API” dashboard tracks `settings_api_latency_seconds`, request mix, and error codes.\
**References:** Appendix A key catalog, §4 Activation pipeline.\
**Breadcrumbs:** Implementation `apps/platform/settings/api.py`, tests `tests/platform/settings/test_api_endpoints.py`.

- `/api/v1/settings/privacy/templates` surfaces DPIA/RoPA metadata keyed by matrix version.
- Read APIs respect `If-None-Match` ETags based on snapshot hash to reduce load.

### 3.2 SDK usage & caching (normative)

**Purpose:** Provide client contract for caching and snapshotting.\
**Contract:** SDK caches results per request context, supports typed access (`get(key, type=...)`), and persists snapshots for embedding in jobs; invalidation uses Redis pub/sub `settings.changed`.\
**State:** Client caches store TTL metadata and version IDs; fallback store persists in job manifests.\
**Failure modes & handling:** Cache misses fallback to API fetch; stale caches after invalidation trigger warnings and forced reload.\
**Observability:** “Settings Client Cache” panel tracks `settings_cache_hit_ratio` and invalidation lag.\
**References:** §4.5 Caching & invalidation, Appendix B metrics.\
**Breadcrumbs:** Client implementation `packages/udocket_core/settings/client.py`, tests `tests/platform/settings/test_sdk_cache.py`.

- Clients avoid `.env` usage beyond bootstrapping; runtime relies on SR for truth.
- SDK exports helpers for dry-run validation and diff preview consumption.

### 3.3 Authentication & request signing (binding)

**Purpose:** Enforce secure access to mutating endpoints.\
**Contract:** Mutations require service tokens plus HMAC signing; actors supply `X-Signature-Key-Id`, `X-Timestamp`, and Idempotency headers with ±30 second skew tolerance.\
**State:** Key metadata stores in `settings_hmac_key`; rotations link to activation records and audit trails.\
**Failure modes & handling:** Signature mismatches return `401`; clients refresh keys or resync clocks before retrying.\
**Observability:** “Settings Auth” dashboard segments `settings_auth_failure_total` by reason (signature_mismatch, expired_timestamp, disabled_key); audit events capture actor and bundle IDs.\
**References:** §7 Security & compliance, Appendix R runbooks.\
**Breadcrumbs:** Security helpers `apps/platform/settings/security.py`, tests `tests/platform/settings/test_auth.py`.

### 3.4 Privacy & redaction (normative)

**Purpose:** Protect sensitive configuration when displayed or exported.\
**Contract:** SR redacts secret values in API responses, CLI exports, and diff previews; activation history stores hashed digests only.\
**State:** Secret metadata tracked in `settings_secret_meta` including scope, rotation cadence, and masking policy.\
**Failure modes & handling:** Attempts to expose secrets trigger `SECRET_DISCLOSURE_BLOCKED`; Security reviews audit trails before re-enabling access.\
**Observability:** “Settings – Secret Access” panel tracks `settings_secret_read_total` by actor role; anomaly detection alerts on spikes.\
**References:** §7 Security & compliance, Appendix A.\
**Breadcrumbs:** Redaction helpers `apps/platform/settings/redaction.py`, tests `tests/platform/settings/test_redaction.py`.

______________________________________________________________________

## 4) State management

**Purpose:** Explain how SR processes activations, persists governance state, and keeps caches consistent.\
**Contract:** Activations execute deterministic stages (diff, validation, approval, publish) with advisory locks, dual approvals, and rollback support.\
**State:** Activation records, stage history, diff artifacts, and lock metadata reside in Postgres (`setting_activation`, `setting_activation_stage`, `settings_activation_lock`) with companion artifacts under `storage/media/settings/`.\
**Failure modes & handling:** Validator failures, lock contention, or stale caches halt activations until remediation (see §§4.2–4.5 and §5).\
**Observability:** “Settings Activation”, “Settings Diff”, “Settings Lock”, and “Settings Cache” dashboards track duration, unsafe counts, contention, and invalidation lag.\
**References:** §2 Responsibilities, §3 API contract, §5 Failure modes, Appendix R runbooks.\
**Breadcrumbs:** Activation services `apps/platform/settings/services/`, diff renderer `apps/platform/settings/services/diff.py`, lock manager `apps/platform/settings/services/locks.py`.

### 4.1 Activation pipeline (binding)

**Purpose:** Describe the activation flow from submission through publish.\
**Contract:** Activations compute diffs, run validators, persist audit trails, publish invalidation events, and enforce blue/green rollout sequencing with advisory locks.\
**State:** Pipeline stages record in `setting_activation_stage`; lock state maintained per org/bundle.\
**Failure modes & handling:** Validator failures mark activations unsafe; operators remediate and resubmit. Rollback replays previous bundles with preserved audit metadata.\
**Observability:** “Settings Activation” dashboard tracks `settings_activation_duration_seconds`, unsafe counts, and rollback frequency; traces link to change tickets.\
**References:** §5 Failure modes, Appendix R RB-GOV-008.\
**Breadcrumbs:** Activation service `apps/platform/settings/services/activation.py`, tests `tests/platform/settings/test_activation_flow.py`.

- Diff previews produce human-readable and machine JSON artifacts for reviewers.
- Activation history retains signatures, actor IDs, roles, and justification text.

### 4.2 Diff preview & dry-run validation (binding)

**Purpose:** Provide reviewers visibility into proposed changes before approval.\
**Contract:** Dry runs compare compiled tables (`effective_permission`, `field_mask_rule`, residency profiles) and surface unsafe reasons requiring dual approval.\
**State:** Diff artifacts persist in `settings_activation_diff` with SHA-256 digests and reviewer annotations.\
**Failure modes & handling:** Missing diff or compilation errors block approval; remediate data and rerun pipeline.\
**Observability:** “Settings Diff” panel charts `settings_diff_generated_total` by bundle type; alerts fire when diff generation fails repeatedly.\
**References:** Appendix A traceability map, Appendix R RB-GOV-008.\
**Breadcrumbs:** Diff renderer `apps/platform/settings/services/diff.py`, tests `tests/platform/settings/test_diff_preview.py`.

### 4.3 Dual approval & waiver workflow (binding)

**Purpose:** Enforce governance for risky changes.\
**Contract:** Unsafe activations demand dual approval (Security + Architecture) with step-up MFA and recorded justification; waivers embed waiver IDs and expiry metadata.\
**State:** Approval records persist in `settings_activation_approval`; waivers track in `settings_waiver` referencing App.O decision log entries.\
**Failure modes & handling:** Missing approvals keep activations pending; expired waivers trigger alerts and block reactivation until renewed.\
**Observability:** “Settings Governance” dashboard charts `settings_dual_approval_total`, waiver counts, and decision latency; audit events `SETTINGS_CHANGE_REQUESTED` and `SETTINGS_WAIVER_APPLIED` broadcast outcomes.\
**References:** §7 Security & compliance, Appendix R RB-GOV-008.\
**Breadcrumbs:** Governance service `apps/platform/settings/services/approvals.py`, tests `tests/platform/settings/test_governance.py`.

### 4.4 Locking & concurrency control (normative)

**Purpose:** Prevent conflicting activations and enforce uniqueness.\
**Contract:** SR acquires advisory lock `settings-activate:{org_id}` and enforces optimistic concurrency on active bundle rows, ensuring one ACTIVE bundle per org/bundle combination.\
**State:** Lock metadata lives in `settings_activation_lock` with timestamps and holder IDs.\
**Failure modes & handling:** Lock timeouts surface `ACTIVATION_CONFLICT`; clients retry after backoff once lock releases.\
**Observability:** “Settings Lock” panel highlights `settings_activation_lock_wait_seconds`; alerts trigger when waits exceed 30 seconds.\
**References:** §5 Failure modes, Appendix R RB-LOCK-006.\
**Breadcrumbs:** Lock utilities `apps/platform/settings/services/locks.py`, tests `tests/platform/settings/test_locks.py`.

### 4.5 Caching & invalidation (normative)

**Purpose:** Keep runtime views consistent without stale decisions.\
**Contract:** SR publishes `settings.changed` events `{scope, org_id, case_id, bundle_id}`; subscribers flush caches and refresh on next access, with polling safeguards if events are missed.\
**State:** Redis pub/sub stores event history for one hour; adoption trackers confirm refresh success.\
**Failure modes & handling:** Missed events trigger fallback pollers; repeated misses raise incident `SETTINGS_INVALIDATION_STALLED`.\
**Observability:** “Settings Cache” dashboard monitors `settings_cache_invalidation_lag_seconds`; synthetic fetches confirm propagation within 60 seconds.\
**References:** §3.2 SDK usage, §6 Observability.\
**Breadcrumbs:** Cache manager `apps/platform/settings/cache.py`, tests `tests/platform/settings/test_invalidation.py`.

______________________________________________________________________

______________________________________________________________________

## 6) Observability & SLOs (binding)

**Purpose:** Define the telemetry, dashboards, and synthetic coverage that prove SR is meeting its safety and latency commitments.\
**Contract:** Metrics, logs, and synthetic probes listed here are mandatory; removing or renaming signals requires Observability + Security approval and doc updates.\
**State:** Metrics publish via Prometheus (`settings_*` series), logs/audits persist in Postgres and `storage/media/settings/`, and synthetic jobs emit structured artifacts in `ops/synthetics/`.\
**Failure modes & handling:** Breaches escalate through Section 5 runbooks (RB-GOV-008, RB-RES-*, RB-LOCK-006) before activations resume.\
**Observability:** Grafana dashboards “Settings Registry – SLO”, “Settings Cache”, “Settings Drift”, and “Settings Governance” visualize health; Alertmanager routes incidents to Settings on-call.\
**References:** §1 Purpose, §4 State management, §5 Failure modes, Appendix B metrics, Appendix R runbooks.\
**Breadcrumbs:** Dashboards `infra/grafana/settings_*.json`, synthetic config `ops/synthetics/settings_slo.yaml`, telemetry module `apps/platform/settings/telemetry.py`.

### 6.1 Metrics

**Purpose:** Summarize key quantitative signals.\
**Contract:** Maintain metrics `settings_latency_seconds`, `settings_request_total`, `settings_error_total`, `settings_activation_duration_seconds`, `settings_activation_unsafe_total`, `settings_validation_failure_total`, `settings_cache_invalidation_lag_seconds`, `settings_snapshot_mismatch_total`, and `settings_residency_violation_total`.\
**State:** Metrics originate from application instrumentation and activation pipeline hooks; error budget tracking stores monthly summaries in `sre_error_budget`.\
**Failure modes & handling:** Threshold breaches drive runbooks in §5; burn-rate alarms freeze activations.\
**Observability:** Grafana “Settings Registry – SLO” and “Settings Drift” dashboards chart trends; alert definitions live in `infra/monitoring/settings-prometheus-rules.yaml`.\
**References:** Appendix B.\
**Breadcrumbs:** Telemetry helpers `apps/platform/settings/telemetry.py`, Prometheus rules `infra/monitoring/settings-prometheus-rules.yaml`.

### 6.2 Logs & audits

**Purpose:** Describe the audit footprint that supports incident response and compliance.\
**Contract:** Activation history, diff artifacts, approvals, waivers, and drift findings must be append-only with immutable digests; redaction policies govern secret output.\
**State:** Logs persist in `setting_activation`, `setting_activation_diff`, `settings_activation_approval`, `settings_drift_finding`, and case-scoped ops directories under `storage/media/settings/`.\
**Failure modes & handling:** Missing artifacts or retention gaps trigger compliance incidents; responders follow Appendix R RB-GOV-008 and RB-LOCK-006.\
**Observability:** Audit pipeline metrics, partition age checks, and log retention alerts verify coverage.\
**References:** §4 State management, §7 Security & compliance, Appendix A traceability.\
**Breadcrumbs:** Logging config `infra/logging/settings.json`, rotation script `ops/db/rotate_partitions.py`, tests `tests/platform/settings/test_audit_trail.py`.

### 6.3 Synthetic monitoring

**Purpose:** Continuously exercise SR surfaces to detect regressions early.\
**Contract:** Synthetic jobs execute read, activation, invalidation, and diff workflows on each deploy; failures block releases until mitigated.\
**State:** Synthetic definitions live in `ops/synthetics/settings_slo.yaml`; results archive to incident dashboards and CI logs.\
**Failure modes & handling:** Failures escalate via RB-GOV-008; subsequent activations freeze until synthetic success.\
**Observability:** Grafana panels and PagerDuty integrations track synthetic success rates and latency.\
**References:** §4 Activation pipeline, §5 Failure modes, Appendix R RB-GOV-008.\
**Breadcrumbs:** Synthetic scripts `ops/synthetics/`, tests `tests/synthetics/test_settings_slo.py`.

### 6.4 Drift detection (binding)

**Purpose:** Detect mismatches between stored snapshots and effective configuration.\
**Contract:** Drift detectors compare snapshot digests, schema versions, and residency profiles on a schedule; any mismatch raises incidents and freezes activations.\
**State:** Findings persist in `settings_drift_finding` with remediation steps and linked tickets.\
**Failure modes & handling:** Unresolved drift escalates to Security and Appendix R RB-RES-ENDPOINT; SR may regenerate snapshots or rollback bundles.\
**Observability:** “Settings Drift” dashboard charts `settings_snapshot_drift_total` and severity; alerts integrate with on-call rotations.\
**References:** §2.3 Snapshot contract, §5.2 Snapshot mismatch.\
**Breadcrumbs:** Drift detector `apps/platform/settings/telemetry.py`, tests `tests/platform/settings/test_drift.py`.

______________________________________________________________________

## 7) Security & compliance (binding)

**Purpose:** Capture SR’s security posture, residency guarantees, and regulatory obligations.\
**Contract:** SR enforces RLS, secret redaction, residency controls, dual approval, and tamper-evident logs; waivers and manual overrides require documented approval with expiry.\
**State:** Security policies live in IAM roles, RLS definitions, HSM-managed signing keys, and audit tables described below.\
**Failure modes & handling:** Auth violations, residency breaches, or secret exposure escalate through Appendix R runbooks and Security incident workflows.\
**Observability:** Dashboards “Settings Auth”, “Settings Governance”, and “Residency Compliance” plus audit alerts surface violations.\
**References:** §2.4 Residency, §3.3 Authentication, §5 Failure modes, Appendix R RB-RES-*/RB-GOV-008.\
**Breadcrumbs:** IAM policies `infra/iam/settings/`, RLS definitions `apps/platform/settings/models.py`, security tests `tests/platform/settings/test_security.py`.

### 7.1 Access control & RLS (binding)

**Purpose:** Define SR’s access model.\
**Contract:** SR enforces deny-by-default policies using compiled `effective_permission` tables; only explicitly authorized roles (including `sysadmin`) may modify configuration.\
**State:** Access grants persist in `setting_permission` referencing roles and resources; policy compilation aligns with Appendix A traceability.\
**Failure modes & handling:** Unauthorized attempts raise `403`; audit logs record actor, scope, and requested action for SIEM ingestion.\
**Observability:** “Settings Access” dashboard charts `settings_access_violation_total`; anomalies route to security analysts.\
**References:** §3.3 Authentication, Appendix A key catalog.\
**Breadcrumbs:** Access policy implementation `apps/platform/settings/models.py::SettingAccessPolicy`, tests `tests/platform/settings/test_access_control.py`.

- Field masking rules compile into `field_mask_rule` tables refreshed per activation.

### 7.2 Audit logging & retention (binding)

**Purpose:** Maintain complete audit history for regulatory review.\
**Contract:** Every activation, validation failure, unsafe reason, waiver, and cache invalidation produces structured audit events stored in immutable sinks; retention periods align with HIPAA/PHIPA and internal governance policies.\
**State:** Audit events stream to `ops/settings/ops_settings.jsonl` and warehouse tables; manifest digests link to Appendix A traceability.\
**Failure modes & handling:** Immutable sink toggles are blocked; fallback storage engages if sinks are unavailable, triggering incident escalation.\
**Observability:** “Settings Audit Trail” dashboard tracks `settings_audit_event_total`; completeness monitors alert if events lag beyond five minutes.\
**References:** §6.2 Logs & audits, Appendix B metrics.\
**Breadcrumbs:** Audit writer `apps/platform/settings/audit.py`, tests `tests/platform/settings/test_audit_log.py`.

### 7.3 Incident response & rollback (binding)

**Purpose:** Provide repeatable rollback and incident handling procedures.\
**Contract:** Unsafe activations or drift incidents freeze new activations, replay last known good bundles, notify stakeholders, and document remediation per Appendix R RB-GOV-008.\
**State:** Automation stores rollback checkpoints and evidence attachments alongside incident tickets.\
**Failure modes & handling:** Rollback failures escalate to the incident commander; automation retries with exponential backoff before manual intervention.\
**Observability:** “Settings Incidents” panel tracks `settings_incident_open_total`; postmortems reference activation IDs and audit digests.\
**References:** §5 Failure modes, Appendix R RB-GOV-008/RB-LOCK-006.\
**Breadcrumbs:** Runbook scripts `ops/runbooks/settings_rollback.py`, tests `tests/platform/settings/test_rollback.py`.

### 7.4 Compliance & privacy obligations (normative)

**Purpose:** Capture DSAR, retention, HIPAA, and disclosure requirements enforced by SR.\
**Contract:** Keys such as `compliance.erasure_mode`, `compliance.subject_hkdf_salt`, `privacy.hipaa.*`, and `privacy.legal.matrix_version` must exist and pass validators before activation; overrides require dual approval with legal citations.\
**State:** Compliance profile metadata lives in `settings_compliance_profile` and links to Reference Manager legal matrices.\
**Failure modes & handling:** Missing keys or invalid values block activation; forced overrides demand dual approval and Appendix R documentation.\
**Observability:** “Settings Compliance” dashboard monitors `settings_compliance_violation_total`; alerts highlight expiring HIPAA bundles or DSAR configuration drift.\
**References:** §2 Responsibilities, §5.3 Residency incidents, Appendix R RB-RES-BLOCK.\
**Breadcrumbs:** Compliance enforcement `apps/platform/settings/compliance.py`, tests `tests/platform/settings/test_compliance.py`.

______________________________________________________________________

## 8) Operational notes (normative)

**Purpose:** Capture day-to-day operational practices, release mechanics, and tooling used to keep SR healthy.\
**Contract:** Teams must follow documented change control, runbook execution, and release cadence; deviations require incident documentation and retro actions.\
**State:** Operational metadata lives in runbooks under `ops/runbooks/guardian` (shared format), `ops/runbooks/settings/`, deployment scripts, and incident retros in `ops/guardian/incidents/` (shared template).\
**Failure modes & handling:** Skipping change control or drift from operational guides increases audit risk; Appendix R enforces quarterly reviews and drill cadence.\
**Observability:** Deployment dashboards, runbook completion checklists, and CI jobs surface operational hygiene.\
**References:** §4 State management, §5 Failure modes, Appendix R RB-* entries.\
**Breadcrumbs:** Deployment scripts `ops/scripts/settings_deploy.py`, CI workflows `.github/workflows/docs-ci.yml`, runbooks `ops/runbooks/settings/`.

### 8.1 Deployment & release cadence (binding)

**Purpose:** Describe how SR code and configuration rollouts occur.\
**Contract:** Code deploys follow blue/green strategy with activation freeze windows; configuration changes require change ticket linkage and dual approval before hitting production.\
**State:** Deployment metadata recorded in GitHub Actions artifacts and `settings_activation` history (`change_ticket`, `release_channel`).\
**Failure modes & handling:** Failed deploys auto-roll back to previous release; configuration freezes remain active until SLOs stabilize.\
**Observability:** Release dashboards show deployment status, activation backlog, and freeze indicators.\
**References:** §4 Activation pipeline, Appendix R RB-GOV-008.\
**Breadcrumbs:** Deployment script `ops/scripts/settings_deploy.py`, tests `tests/platform/settings/test_release_workflow.py`.

### 8.2 On-call & staffing (binding)

**Purpose:** Outline operational ownership and escalation paths.\
**Contract:** Settings on-call rotation (shared with Guardian/LPE) monitors dashboards from §6 and executes RB-GOV-008, RB-RES-*, RB-LOCK-006 during incidents; escalation path includes Architecture and Security duty officers.\
**State:** Roster stored in `ops/guardian/roster.yaml` (shared) with SR-specific contacts annotated.\
**Failure modes & handling:** Missing coverage triggers management review; incident retros include staffing analysis.\
**Observability:** PagerDuty “Settings SLO” service tracks alert volume and response times.\
**References:** §6 Observability, Appendix R runbooks.\
**Breadcrumbs:** Roster `ops/guardian/roster.yaml`, PagerDuty configuration, tests `tests/ops/test_runbook_integrity.py`.

### 8.3 Tooling & automation (normative)

**Purpose:** Summarize supporting tooling that keeps SR governance consistent.\
**Contract:** Teams must run `python scripts/docs/lint_docs.py`, `python scripts/docs/build_runbook_catalog.py`, `python scripts/docs/check_settings_keys.py`, and `scripts/sdk/check_openapi_alignment.py` before merging changes touching SR.\
**State:** CI workflows enforce linting, seed bundle validation, and OpenAPI drift detection; runbook catalog renders Appendix R index.\
**Failure modes & handling:** Failing automation blocks merges; overrides require Architecture approval with follow-up tasks to restore automation.\
**Observability:** CI dashboards display job history; governance board reviews automation health monthly.\
**References:** §2 Responsibilities, Appendix C seed inventory.\
**Breadcrumbs:** Scripts under `scripts/docs/`, CI definitions `.github/workflows/docs-ci.yml`.

______________________________________________________________________

## 9) Dependencies (informative)

**Purpose:** Map SR’s upstream and downstream relationships so teams understand how configuration changes cascade.\
**Contract:** SR depends on Guardian, LPE, Reference Manager, Portal, and Worker pipelines consuming snapshots, respecting invalidations, and surfacing digests in their own telemetry.\
**State:** Integration metadata resides in `settings_enforcement_point`, `settings_integration_status`, `settings_portal_profile`, and job manifests with snapshot digests.\
**Failure modes & handling:** Missed invalidations or integration drift trigger Section 5 runbooks (RB-RES-*, RB-JOB-WATCHDOG) and Appendix R RB-GOV-008 coordination.\
**Observability:** Dashboards “Settings Enforcement”, “Settings Integration”, “Portal Settings”, and “Worker Settings” expose adoption health; alerts highlight stale snapshots or misaligned bundles.\
**References:** §2 Responsibilities, §3 API contract, §6 Observability, Appendix B metrics.\
**Breadcrumbs:** Integration services `apps/platform/settings/services/`, worker tasks `apps/platform/operations/tasks.py`, tests `tests/platform/settings/test_enforcement_points.py`, `tests/platform/settings/test_lpe_guardian_bridge.py`.

### 9.1 Enforcement touchpoints (binding)

**Purpose:** Enumerate runtime surfaces that must consult SR.\
**Contract:** APIs, workers, front-end flows, and database policies fetch current settings snapshots before decision-making and record digests in logs; missing enforcement registrations fail lint checks.\
**State:** Enforcement registry stored in `settings_enforcement_point` with required bundles and validation hooks.\
**Failure modes & handling:** Runtime detection of stale snapshots blocks operations until refreshed; lint failures must be resolved before merge.\
**Observability:** “Settings Enforcement” dashboard tracks `settings_enforcement_lookup_total` and stale detection alerts.\
**References:** §4 State management, §5 Failure modes.\
**Breadcrumbs:** Enforcement helpers `apps/platform/settings/services/enforcement.py`, tests `tests/platform/settings/test_enforcement_points.py`.

- API enforcement covers RBAC writes, CORS, rate limits, portal downloads, HIPAA/PHIPA banners, and residency gating.
- Worker enforcement includes agent configurations, FinOps ceilings, Guardian/Signer integration, and waiver gating.
- Front-end enforcement drives feature flags, approvals, messaging flows, and localization decisions.
- Database enforcement ensures RLS and masking profiles reference compiled tables from SR activations and LPE contexts.

### 9.2 Guardian, LPE, and RM alignment (binding)

**Purpose:** Define coordination with Guardian, LPE, and Reference Manager.\
**Contract:** SR consumes RM bundles for residency/provider catalogs, triggers LPE dry-run compiles, and exposes Guardian waivers and policy toggles with shared digests; integration drift blocks activation.\
**State:** Integration metadata persists in `settings_integration_status` referencing RM bundle IDs and LPE compile versions.\
**Failure modes & handling:** Missing RM bundles or failed LPE compiles flag activations unsafe; teams remediate before approval proceeds.\
**Observability:** “Settings Integration” dashboard captures sync success, waiver usage, and compile durations; alerts open Security tickets when residency endpoints change.\
**References:** §2.4 Residency, §5.3 Residency incidents, Appendix R RB-RES-ENDPOINT.\
**Breadcrumbs:** Integration service `apps/platform/settings/services/integration.py`, tests `tests/platform/settings/test_lpe_guardian_bridge.py`.

- Residency endpoint changes open Security tickets; waivers demand dual approval and manifest stamping until replacement endpoints validated.
- Guardian gating configuration, including review modes and operator visibility, surfaces via SR keys and audit events.

### 9.3 Portal & client experience (normative)

**Purpose:** Outline SR responsibilities for portal/client exposures.\
**Contract:** SR provides localized disclaimers, enabled locales, HIPAA allowances, rate limits, and chat assistant toggles for portal consumption.\
**State:** Portal profile snapshots store in `settings_portal_profile` with `portal_visible=true` filters.\
**Failure modes & handling:** Exposing masked fields triggers validation errors; portal blocks rendering until resolved.\
**Observability:** “Portal Settings” dashboard monitors lookup counts and cache hit ratios; alerts fire on mismatch between SR and portal caches.\
**References:** §2.5 Pipeline bundles, Appendix C seed bundles.\
**Breadcrumbs:** Portal profile service `apps/platform/settings/services/portal_profile.py`, tests `tests/platform/settings/test_portal_profile.py`.

- Chat assistants mirror SR rate limits and token budgets; Settings updates propagate to portal warnings and UI pickers.

### 9.4 Worker pipelines & job manifests (binding)

**Purpose:** Ensure job pipelines consume SR snapshots consistently.\
**Contract:** Workers fetch settings before task execution, embed snapshot digests in manifests, and persist evidence to ops logs and audit JSONL.\
**State:** Snapshot references stored alongside job records and artifact manifests; drift detection cross-checks manifests.\
**Failure modes & handling:** Failed fetches block job start; backlog alerts fire when retrieval exceeds retry windows.\
**Observability:** “Worker Settings” panel tracks `settings_snapshot_job_total` and stale-snapshot alerts.\
**References:** §2.3 Snapshot contract, §5.2 Snapshot mismatch.\
**Breadcrumbs:** Worker tasks `apps/platform/operations/tasks.py::hydrate_settings_snapshot`, tests `tests/platform/operations/test_settings_snapshot.py`.

______________________________________________________________________

## 10) References (informative)

**Purpose:** Provide quick access to the primary documents, ADRs, diagrams, and scripts supporting SR.\
**Contract:** Update this list whenever dependencies change; missing references cause docs lint failures.\
**State:** References point to immutable ADRs, diagrams, runbooks, and tooling maintained elsewhere in the repo.\
**Failure modes & handling:** Broken references must be resolved before merging; `scripts/docs/lint_docs.py` enforces completeness.\
**Observability:** Docs CI job highlights missing or stale references.\
**Breadcrumbs:** `scripts/docs/lint_docs.py`, `scripts/docs/build_runbook_catalog.py`, MkDocs navigation `docs/mkdocs.yml`.

- ADRs: ADR-0003 API Versioning & Sunset, ADR-0004 Localization & Policy Engine, ADR-0005 OPA Policy Plane.\
- TDD: TDD §5 Security Architecture, TDD §7 Settings Governance, TDD Appendix H Operational Guides.\
- Runbooks: Appendix R RB-GOV-008, RB-RES-ENDPOINT, RB-RES-BLOCK, RB-JOB-WATCHDOG, RB-LOCK-006.\
- Diagrams: `docs/src/services/settings/diagrams/*.mmd`, `docs/src/overview/tdd/diagrams/data-lineage-v1.mmd`.\
- Scripts & tooling: `scripts/docs/check_settings_keys.py`, `scripts/sdk/check_openapi_alignment.py`, `ops/scripts/settings_deploy.py`.\
- Metrics dashboards: `infra/grafana/settings_slo.json`, `infra/grafana/settings_drift.json`, `infra/grafana/settings_enforcement.json`.

______________________________________________________________________

## Appendix A — Settings key map & traceability index

**Purpose:** Link platform behaviour to Settings Registry configuration for audit and troubleshooting.\
**Contract:** Every key referenced in code, bundles, or docs appears here with scope, defaults, and enforcement notes; automation cross-checks ensure completeness.\
**State:** Maintained in version control; automation compares against `config/settings_definitions.json`, runtime validators, and seed bundles.\
**Failure modes & handling:** Missing mappings fail `python scripts/docs/check_settings_keys.py`; authors update definitions and this appendix together.\
**Observability:** Docs lint metrics raise alerts on coverage gaps; release checklists block promotion when lint fails.\
**References:** §2 Responsibilities, Appendix C seed inventory.\
**Breadcrumbs:** Script `scripts/docs/check_settings_keys.py`, tests `tests/docs/test_check_settings_keys.py`, dashboard “Docs – Settings Coverage”.

### A.1 Key catalog (binding)

**Purpose:** Provide authoritative coverage of SR keys, scopes, defaults, and enforcement hooks.\
**Contract:** Keys listed here must exist in definitions, validators, and runtime usage; consumers reference this table instead of duplicating values elsewhere.\
**State:** Source-of-truth definitions live in `config/settings_definitions.json`; effective settings surface through `setting_effective` and `settings_snapshot` tables.\
**Failure modes & handling:** Divergence between documentation and schema blocks CI; activations referencing undocumented keys are rejected.\
**Observability:** Validators emit `settings_definition_gap_total`; lint dashboards flag omissions.\
**References:** §2 Responsibilities, §4 State management.\
**Breadcrumbs:** Schema `packages/udocket_core/settings/schema.py`, tests `tests/platform/settings/test_definition_schema.py`.

| Key                                             | Scope       | Default                                                      | Description / Enforcement                                                                                                                                                    |
| ----------------------------------------------- | ----------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `regions.allowlist.compute`                     | ORG         | \[na-us-1, na-us-2\]                                         | Allowed compute regions; enforced by §3.8.                                                                                                                                   |
| `regions.allowlist.storage`                     | ORG         | \[na-us-1, na-us-2\]                                         | Allowed storage regions; enforced by §3.8 and §5.3.                                                                                                                          |
| `network.egress.allowed_hosts[]`                | SYSTEM\|ORG | \[\]                                                         | Host allowlist rendered to ServiceEntry/AuthorizationPolicy; §3.2.1.                                                                                                         |
| `analyze.model.id`                              | ORG\|CASE   | default profile                                              | LLM model profile for Analyze lanes; see §8 and §6.3.                                                                                                                        |
| `analyze.token_ceiling`                         | ORG\|CASE   | 100000                                                       | Max tokens per Analyze job; see §8.3.                                                                                                                                        |
| `analyze.max_retries`                           | ORG\|CASE   | 2                                                            | Retry budget per lane; see §6.3 QA loops.                                                                                                                                    |
| `compose.model.id`                              | ORG\|CASE   | default profile                                              | LLM model profile for Compose; see §8 and §6.4.                                                                                                                              |
| `compose.token_ceiling`                         | ORG\|CASE   | 100000                                                       | Max tokens per Compose job; §8.3.                                                                                                                                            |
| `compose.max_retries`                           | ORG\|CASE   | 2                                                            | Retry budget per lane; §6.4.                                                                                                                                                 |
| `compose.policy.forbidden_patterns[]`           | ORG         | \[\]                                                         | Content forbids; §6.4 QA.                                                                                                                                                    |
| `compose.templates.client.template_id`          | ORG         | default                                                      | DOCX/MD template selection; §6.4.                                                                                                                                            |
| `compose.templates.lawyer.template_id`          | ORG         | default                                                      | DOCX/MD template selection; §6.4.                                                                                                                                            |
| `reviews.timeout_hours`                         | ORG         | 72                                                           | Approval escalation threshold (reminders/escalations); §11.2.3.                                                                                                              |
| `reviews.backlog.alert_minutes`                 | ORG         | 30                                                           | Minutes before `QUEUED_FOR_REVIEW` items trigger reviewer escalation banners/alerts; §7.1.3, §11.1.                                                                          |
| `sign.trust_roots[]`                            | SYSTEM\|ORG | \[\]                                                         | Trust roots for signing; §7.2.                                                                                                                                               |
| `sign.tsa.endpoint`                             | SYSTEM\|ORG | null                                                         | TSA API endpoint; §7.2.                                                                                                                                                      |
| `sign.tsa.max_time_drift_secs`                  | SYSTEM      | 5                                                            | NTP drift tolerance; §7.2, §3.2.                                                                                                                                             |
| `security.tls.min_version`                      | SYSTEM      | TLSv1.3                                                      | Minimum TLS version for ingress; §3.2.                                                                                                                                       |
| `security.tls.cipher_profile`                   | SYSTEM      | default                                                      | TLS cipher profile for ingress; §3.2.                                                                                                                                        |
| `security.tls.fips_mode`                        | SYSTEM      | false                                                        | Enforce FIPS-approved cipher suites and modules; §3.2, §7.2.                                                                                                                 |
| `security.tls.legacy_exceptions[]`              | SYSTEM      | \[\]                                                         | Temporary TLS 1.2 exceptions (≤30 days, alert at T-7); §3.2, §9.2.                                                                                                           |
| `db.pgbouncer.pool_mode`                        | SYSTEM      | transaction                                                  | Allowed PgBouncer pooling mode (`transaction` default, `session` optional); §3.2.1.                                                                                          |
| `llm.providers[]`                               | SYSTEM\|ORG | \[\]                                                         | Provider catalog; §8.1.                                                                                                                                                      |
| `llm.models[]`                                  | SYSTEM\|ORG | \[\]                                                         | Model catalog and fallback priorities; §8.1.                                                                                                                                 |
| `llm.models.version_pin`                        | SYSTEM\|ORG | provider‑specific                                            | Explicit provider model snapshot/version pin; §8.1/§8.5.                                                                                                                     |
| `llm.enforce_model_version`                     | ORG\|CASE   | true                                                         | Fail when provider model version drifts from pin; §8.1/§8.5.                                                                                                                 |
| `llm.moderation.enabled`                        | ORG         | true                                                         | Enable automated input/output moderation; §8.4.                                                                                                                              |
| `llm.moderation.provider`                       | ORG         | azure\|openai\|local                                         | Moderation provider selection; §8.4.                                                                                                                                         |
| `llm.moderation.enforcement`                    | SYSTEM\|ORG | block                                                        | Enforcement mode: `block` (default) or `warn`; §8.4.                                                                                                                         |
| `llm.moderation.thresholds.toxicity`            | ORG         | 0.5                                                          | Classification threshold; §8.4.                                                                                                                                              |
| `llm.moderation.thresholds.self_harm`           | ORG         | 0.5                                                          | Classification threshold; §8.4.                                                                                                                                              |
| `llm.moderation.thresholds.sexual_content`      | ORG         | 0.5                                                          | Classification threshold; §8.4.                                                                                                                                              |
| `llm.moderation.thresholds.pii_reintroduction`  | ORG         | 0.5                                                          | Classification threshold; §8.4.                                                                                                                                              |
| `llm.byo.allowed`                               | ORG\|CASE   | false                                                        | Permit bring-your-own model endpoints; §8.1.3.                                                                                                                               |
| `llm.byo.evaluation_suite_id`                   | ORG         | default                                                      | Evaluation suite applied to BYO providers; §8.1.3.                                                                                                                           |
| `llm.byo.vpc_endpoints[]`                       | ORG         | \[\]                                                         | Allowed BYO endpoint hostnames (reconciled with mesh policies); §8.1.3.                                                                                                      |
| `agents.langgraph.runner`                       | SYSTEM\|ORG | langgraph                                                    | Graph runner selection (`langgraph` or `linear`); §6.7.2.                                                                                                                    |
| `agents.langgraph.fallback_mode`                | SYSTEM      | false                                                        | Force manual drafting fallback; §6.7.2, App.D RB-LLM-003.                                                                                                                    |
| `speech.providers[]`                            | SYSTEM\|ORG | \[\]                                                         | Speech provider catalog (health, residency, parity evidence); §6.2.1.                                                                                                        |
| `speech.jobs[]`                                 | SYSTEM\|ORG | \[\]                                                         | Transcription job profiles and fallback chains; §6.2.1.                                                                                                                      |
| `speech.allow_preprocessing`                    | ORG\|CASE   | false                                                        | Permit loudness normalization/compression before transcription; §6.2.3.                                                                                                      |
| `speech.require_locale_match`                   | ORG\|CASE   | true                                                         | Fail fast when provider lacks requested locale; §6.2.3.                                                                                                                      |
| `speech.detect_language.enabled`                | ORG\|CASE   | false                                                        | Enable automatic source-language detection; §6.2.4.                                                                                                                          |
| `speech.multilingual_segments.enabled`          | ORG\|CASE   | false                                                        | Emit language-tagged segments for code-switched audio; §6.2.4.                                                                                                               |
| `speech.translation.enabled`                    | ORG\|CASE   | false                                                        | Allow generation of translated transcripts; §6.2.4.                                                                                                                          |
| `speech.translation.targets_default[]`          | ORG         | \[\]                                                         | Default target locales for translation requests; §6.2.4.                                                                                                                     |
| `speech.translation.provider`                   | ORG\|CASE   | null                                                         | Translation provider identifier; §6.2.4.                                                                                                                                     |
| `speech.translation.glossary_set`               | ORG\|CASE   | null                                                         | Reference Manager glossary bundle for translations; §6.2.4.                                                                                                                  |
| `speech.translation.max_parallel_targets`       | ORG\|CASE   | 3                                                            | Parallel translation limit per job; §6.2.4.                                                                                                                                  |
| `speech.translation.allow_unverified_pairs`     | ORG\|CASE   | false                                                        | Permit translation pairs not in the verified registry (waiver required); §6.2.3, §6.2.4.                                                                                     |
| `speech.translation.language_pair_overrides[]`  | ORG\|CASE   | \[\]                                                         | Disable or remap specific source→target pairs for contractual/compliance reasons; §6.2.3, §6.2.4.                                                                            |
| `chat.staff.enabled`                            | ORG\|CASE   | false                                                        | Enable staff Copilot assistant; §11.11.                                                                                                                                      |
| `chat.staff.rate_limit.rpm`                     | ORG\|CASE   | 30                                                           | Staff assistant requests per minute; §11.11.                                                                                                                                 |
| `chat.staff.token_cap_daily`                    | ORG\|CASE   | 20000                                                        | Staff assistant daily token budget; §11.11.                                                                                                                                  |
| `chat.client.enabled`                           | ORG\|CASE   | false                                                        | Enable portal chat assistant; §11.11.                                                                                                                                        |
| `chat.client.rate_limit.rpm`                    | ORG\|CASE   | 10                                                           | Client assistant requests per minute; §11.11.                                                                                                                                |
| `chat.client.token_cap_daily`                   | ORG\|CASE   | 10000                                                        | Client assistant daily token budget; §11.11.                                                                                                                                 |
| `chat.session.max_active_per_user`              | ORG\|CASE   | 2                                                            | Concurrent chat sessions allowed per user; §11.11.                                                                                                                           |
| `chat.auto_disable_on_abuse`                    | ORG\|CASE   | true                                                         | Auto-disable assistants on policy violations; §11.11.                                                                                                                        |
| `chat.provider.profile`                         | ORG\|CASE   | null                                                         | LLM profile assignment for assistants; §8.1.4, §11.11.                                                                                                                       |
| `portal.chat.hipaa_allowed`                     | ORG         | false                                                        | Permit client chat when HIPAA mode active; §11.11.                                                                                                                           |
| `portal.chat.export.enabled`                    | ORG\|CASE   | false                                                        | Allow client chat transcript exports; §11.11.                                                                                                                                |
| `notifications.in_app.rate_limit_per_minute`    | ORG         | 60                                                           | In-app notification dispatch rate; §11.9.                                                                                                                                    |
| `notifications.in_app.daily_cap`                | ORG         | 500                                                          | In-app notification max per day; §11.9.                                                                                                                                      |
| `llm.finops.monthly_cap_usd`                    | ORG         | 0 (disabled)                                                 | Monthly LLM spend cap; §8.3, §13.4.                                                                                                                                          |
| `jobs.watchdog.no_progress_minutes`             | SYSTEM\|ORG | 5                                                            | Minutes without heartbeat before watchdog warns; §10.2, §12.1, Appendix R entry [RB-JOB-WATCHDOG](../ops/runbooks/index.md#rb-job-watchdog).                                 |
| `jobs.watchdog.timeout_minutes`                 | SYSTEM\|ORG | 15                                                           | Minutes without heartbeat before watchdog fails the job; §10.2, §12.1, Appendix R entry [RB-JOB-WATCHDOG](../ops/runbooks/index.md#rb-job-watchdog).                         |
| `uploads.scan.engine`                           | SYSTEM      | clamav                                                       | Malware engine used in the upload scan pipeline; §6.2, §12.1.                                                                                                                |
| `uploads.scan.yara_ruleset_version`             | SYSTEM      | latest                                                       | Version tag for YARA rules synced from Security; §6.2.                                                                                                                       |
| `uploads.scan.timeout_seconds`                  | SYSTEM\|ORG | 120                                                          | Max scan duration before treating file as suspicious and quarantining; §6.2, Appendix R entry [RB-UPLOAD-SCAN](../ops/runbooks/index.md#rb-upload-scan).                     |
| `uploads.scan.override_hashes[]`                | SYSTEM\|ORG | \[\]                                                         | Temporary allowlist for known-clean artifacts while rules are tuned (dual approval, time-boxed); Appendix R entry [RB-UPLOAD-SCAN](../ops/runbooks/index.md#rb-upload-scan). |
| `uploads.enabled`                               | SYSTEM\|ORG | true                                                         | Toggle to accept new uploads; disabled during major scanner outages; Appendix R entry [RB-UPLOAD-SCAN](../ops/runbooks/index.md#rb-upload-scan).                             |
| `api.idempotency.ttl_hours`                     | SYSTEM      | 24                                                           | TTL for idempotency; §10.3.                                                                                                                                                  |
| `api.rate_limits.web.rpm_per_org`               | SYSTEM\|ORG | 600 (guardrail 10-2000; activation validator enforces range) | Org RPM; §10.5.                                                                                                                                                              |
| `api.rate_limits.web.rpm_per_ip`                | SYSTEM\|ORG | 300 (guardrail 10-2000)                                      | IP RPM; §10.5.                                                                                                                                                               |
| `portal.download.rate_limits.user_rpm`          | ORG         | 60 (guardrail 10-2000)                                       | Portal download/user; §10.5.                                                                                                                                                 |
| `portal.download.rate_limits.org_rpm`           | ORG         | 200 (guardrail 10-2000)                                      | Portal download/org; §10.5.                                                                                                                                                  |
| `security.org_switch.step_up_required`          | SYSTEM      | true                                                         | Enforce step-up on privilege increase; §4.3.                                                                                                                                 |
| `security.disclosure.contact`                   | SYSTEM      | null                                                         | Security.txt contact; §14.9.                                                                                                                                                 |
| `security.disclosure.encryption_key_url`        | SYSTEM      | null                                                         | PGP key URL; §14.9.                                                                                                                                                          |
| `security.pentest.cadence`                      | SYSTEM      | annual                                                       | Pentest schedule; §14.9.                                                                                                                                                     |
| `security.mfa.webauthn_required_roles`          | ORG         | \[\]                                                         | Roles requiring WebAuthn step-up (HIPAA mode); §2.2, §4.3.                                                                                                                   |
| `security.session.device_bind.ip_prefix_len_v4` | ORG         | 24                                                           | IPv4 prefix length for device binding; §4.3 (soft/hard modes).                                                                                                               |
| `security.session.device_bind.ip_prefix_len_v6` | ORG         | 48                                                           | IPv6 prefix length for device binding; §4.3 (soft/hard modes).                                                                                                               |
| `security.session.device_bind.mode`             | ORG         | "soft"                                                       | Device fingerprint reaction (`soft` or `hard`); §4.3.                                                                                                                        |
| `udlock.max_session_hold_seconds`               | SYSTEM      | 300                                                          | Advisory lock hold time; App.D RB-LOCK-006.                                                                                                                                  |
| `udlock.heartbeat.interval_seconds`             | SYSTEM      | 5                                                            | Heartbeat period; App.D RB-LOCK-006.                                                                                                                                         |
| `compliance.erasure_mode`                       | ORG         | off                                                          | Hard-purge toggle for DSAR mode; §14.2.1.                                                                                                                                    |
| `compliance.subject_hkdf_salt`                  | SYSTEM      | managed secret                                               | HKDF salt for DSAR subject hashing; §14.2.1.                                                                                                                                 |
| `privacy.legal.matrix_version`                  | SYSTEM      | semver                                                       | Data residency/legal matrix version; App.C.                                                                                                                                  |
| `privacy.hipaa.enabled`                         | ORG         | false                                                        | HIPAA override mode toggle; §2.2, §14.2, App.C.                                                                                                                              |
| `privacy.hipaa.bundle_version`                  | SYSTEM      | semver                                                       | HIPAA policy bundle version pin; §2.2, App.C.                                                                                                                                |
| `privacy.hipaa.phi_detection.strict_mode`       | ORG\|CASE   | true                                                         | Enforce layered PHI detection (waiver required to relax); §2.2.                                                                                                              |
| `privacy.hipaa.phi_detection.rescan_hours`      | ORG         | 24                                                           | Interval for scheduled PHI re-scan jobs; §2.2.                                                                                                                               |
| `i18n.supported_locales[]`                      | ORG         | \[\]                                                         | Supported locales (BCP-47 codes) surfaced in UI toggles; must include at least one locale; §11.3.                                                                            |
| `identity.org.primary_idp`                      | ORG         | keycloak                                                     | Primary IdP assignment (`keycloak` or `external:<id>`); §4.1.                                                                                                                |
| `storage.bucket_versioning_required`            | SYSTEM      | true                                                         | Bucket versioning must be enabled; §5.3, §12.1.                                                                                                                              |
| `storage.remote_hash.enabled`                   | ORG\|CASE   | false                                                        | Record remote hashes for batch inputs; §5.3.                                                                                                                                 |
| `storage.remote_hash.max_mb`                    | ORG\|CASE   | 50                                                           | Max remote bytes to hash; §5.3.                                                                                                                                              |
| `settings.activation.require_dual_approval`     | SYSTEM      | true                                                         | Dual approval for unsafe changes; §9.3.                                                                                                                                      |
| `logging.redaction.enabled`                     | SYSTEM      | true                                                         | Redact PII in logs; §12.1.                                                                                                                                                   |
| `logging.access.roles[]`                        | SYSTEM      | \[\]                                                         | Role mapping for log query privileges (`observability.reader\|engineer\|auditor`); §12.1.2.                                                                                  |
| `logging.cost.daily_budget_mb_per_service`      | SYSTEM\|ORG | 500                                                          | Daily log volume budget per service; §12.1.6.                                                                                                                                |
| `logging.cost.alert_threshold_pct`              | SYSTEM\|ORG | 80                                                           | Alert threshold as % of daily log budget; §12.1.6.                                                                                                                           |
| `logging.level.default`                         | SYSTEM      | "INFO"                                                       | Default production log level; §12.1.6.                                                                                                                                       |
| `logging.level.overrides[]`                     | ORG         | \[\]                                                         | Per-service log level overrides; §12.1.6.                                                                                                                                    |
| `portal.logging.enabled`                        | ORG         | true                                                         | Enable client telemetry capture; §12.1.5.                                                                                                                                    |
| `evidence_store.redacted_excerpts.enabled`      | ORG         | true                                                         | Allow storage of prompt/response excerpts; HIPAA enable guard forces false and triggers purge; §2.2, §8.2.                                                                   |
| `logging.immutable_sink.enabled`                | SYSTEM      | true (prod)                                                  | Mirror structured logs to immutable storage alongside the audit sink; validators block `false` in production and mark overrides unsafe (§9.11, §12.1).                       |
| `llm.finops.guard.threshold_pct`                | SYSTEM\|ORG | 10                                                           | MoM regression ceiling for deploy gate; §8.7, §13.5.                                                                                                                         |
| `llm.finops.guard.trailing7d_pct`               | SYSTEM\|ORG | 25                                                           | Trailing 7-day burn ceiling (% of monthly cap) for deploy gate; §8.7, §13.5.                                                                                                 |
| `llm.finops.override_until`                     | SYSTEM      | null                                                         | Optional timestamp (max +72h) to temporarily relax FinOps guard (dual approval required); §8.7.                                                                              |

### A.2 Traceability map (normative)

**Purpose:** Show which platform surfaces depend on each key family so audits can confirm coverage.\
**Contract:** Every consumer references the relevant bundle IDs listed here; additions require updating this map and associated tests.\
**State:** Enforcement registry stored in `settings_enforcement_point` with bundle-to-service mappings.\
**Failure modes & handling:** Missing mappings trigger lint failures and synthetic alert `settings_enforcement_lookup_total{status="missing"}`.\
**Observability:** Adoption dashboards display bundle coverage per service.\
**References:** §9.1 Enforcement touchpoints, Appendix B metrics.\
**Breadcrumbs:** Enforcement registry `apps/platform/settings/services/enforcement.py`, tests `tests/platform/settings/test_enforcement_points.py`.

- Agents → `analyze.*`, `compose.*`, `llm.*` (TDD §6, §8).
- Guardian → `guardian.*` (judgment policies; see Services · Guardian).
- Signer → `sign.*` (digital signature policies; TDD §7).
- Storage & integrity → `storage.*`, `logging.*` (TDD §5, §12).
- Portal & client UX → `portal.*`, `i18n.*`, `chat.*`, `security.*` (TDD §11).
- APIs & rate limits → `api.*`, `uploads.*`, `notifications.*` (TDD §10, §11.9).
- Operations & governance → `udlock.*`, `privacy.*`, `security.pentest.*`, `logging.*` (Appendix R procedures, TDD §12, §14).

### A.3 Linting & parity gates (binding)

**Purpose:** Ensure SR documentation, schemas, and runtime references remain in lockstep.\
**Contract:** CI fails when settings keys referenced in code lack appendix coverage or when appendix keys lack schema/tests.\
**State:** Lint scripts load this appendix, inspect OpenAPI/spec/config usage, and compare against registry definitions.\
**Failure modes & handling:** Any mismatch fails `settings:lint-keys`; update definitions, tests, and this appendix atomically.\
**Observability:** CI dashboards track lint duration and failure rate.\
**References:** §2 Responsibilities, §8.3 Tooling & automation.\
**Breadcrumbs:** Script `scripts/docs/check_settings_keys.py`, tests `tests/docs/test_lint_rules.py`.

- Regions & residency → `regions.allowlist.*`, `privacy.*`; validated by residency scanners and RM catalog ingest.
- APIs & rate limits → `api.*`, `portal.download.*`; OpenAPI spectral rules enforce header/limit parity.
- FinOps → `llm.finops.*`; drift detection jobs surface monthly spend anomalies.
- Security & compliance → `security.*`, `logging.redaction.*`, `compliance.*`; test suites enforce RLS/masking.
- Ops & locks → `udlock.*`; advisory lock registry and Appendix R entries confirm enforcement.

### A.4 Activation checklist (binding)

**Purpose:** Provide the required evidence when promoting a settings bundle.\
**Contract:** Every activation records justification, reviewers, validator outputs, and rollout timeline before promotion; missing artifacts keep activations unsafe.\
**State:** Activation metadata resides in `settings_activation`, approvals in `settings_activation_approval`, waivers in `settings_waiver` with App.O decision log links.\
**Failure modes & handling:** Missing checklist items mark the activation `unsafe`; promotion halts until evidence supplied.\
**Observability:** Governance dashboard highlights incomplete activations; alert `settings_governance_override_total` pages owners.\
**References:** §4 State management, §5 Failure modes, Appendix R RB-GOV-008.\
**Breadcrumbs:** Activation service `apps/platform/settings/services/activation.py`, tests `tests/platform/settings/test_activation_flow.py`.

Checklist items:

1. Link to change ticket, ADR (if applicable), and decision log entry.
1. Attach validator results (`unsafe_reasons[]`, residency, safety, cost) and diff preview hashes.
1. Confirm dual approval requirements (Security + Architecture) met for protected scopes.
1. Record rollout plan, blast radius, and rollback window; attach staging dry-run evidence.
1. Store bundle, activation JSON, and diff artifacts under `ops/settings/<date>/`.

### A.5 Change log handoff (informative)

**Purpose:** Maintain a rolling history of key modifications discoverable for audits.\
**Contract:** Each production activation with customer impact appends an entry summarizing scope, bundle ID, approvals, and evidence pointers.\
**State:** Change log lives beside this document (`ops/settings/change_log.md`) and mirrors into App.O decision logs.\
**Failure modes & handling:** Missing change-log entries trigger release checklist failures; add entries with backdated evidence before closing the change.\
**Observability:** Weekly docs lint verifies latest activations appear in the log.\
**References:** §4 Activation pipeline, §8 Operational notes.\
**Breadcrumbs:** Change log `ops/settings/change_log.md`, tests `tests/platform/settings/test_change_log.py`.

## Appendix B — Metrics & alerts

**Purpose:** Define the telemetry set that proves SR health, governance controls, and security posture.\
**Contract:** Metrics and alerts enumerated here must exist in production dashboards; owners keep thresholds aligned with SLOs and audit requirements.\
**State:** Metrics emit via OpenTelemetry exporters from the Settings service and background jobs; alerts live in Grafana OnCall.\
**Failure modes & handling:** Missing metrics or stale thresholds block release checklists; on-call reviews incidents weekly to confirm coverage.\
**Observability:** Dashboards — “Settings Registry – Availability”, “Settings Governance”, “Settings Compliance”, “Settings Integrations”.\
**References:** §6 Observability, tables below.\
**Breadcrumbs:** Telemetry module `apps/platform/settings/telemetry.py`, tests `tests/platform/settings/test_metrics.py`.

### B.1 Service health (binding)

| Metric / Alert                              | Description                                                                     | Owner                 |
| ------------------------------------------- | ------------------------------------------------------------------------------- | --------------------- |
| `settings_request_total{result}`            | Request volume by outcome (`success`, `error`, `unauthorized`, `denied`)        | SRE                   |
| `settings_latency_seconds{route}`           | Histogram + SLO burn tracking for read/write endpoints                          | SRE                   |
| `settings_cache_hit_ratio`                  | Redis/local cache hit percentage; alert when \< 0.9                             | Platform Architecture |
| `settings_cache_invalidation_lag_seconds`   | Duration from activation publish to cache flush across nodes                    | SRE                   |
| `settings_snapshot_issued_total{scope}`     | Snapshots delivered to workers, portal, Guardian, LPE                           | Platform Architecture |
| `settings_snapshot_drift_total{detector}`   | Drift findings comparing embedded snapshot hashes vs effective values           | SRE                   |
| `settings_enforcement_lookup_total{status}` | Enforcement touchpoints (required/optional/missing) used by downstream services | Platform Architecture |

### B.2 Governance & security (binding)

| Metric / Alert                                  | Description                                                                         | Owner                 |
| ----------------------------------------------- | ----------------------------------------------------------------------------------- | --------------------- |
| `settings_activation_total{result}`             | Activation outcomes (`success`, `unsafe`, `rollback`) powering release gates        | Settings Program      |
| `settings_activation_duration_seconds`          | Activation execution latency (start→publish) by bundle type                         | Settings Program      |
| `settings_validation_failure_total{reason}`     | Validator failures grouped by guardrail (`residency`, `safety`, `finops`, `schema`) | Settings Program      |
| `settings_dual_approval_total{bundle}`          | Dual-approval events by protected bundle category                                   | Security Engineering  |
| `settings_waiver_active_total{expiry_window}`   | Active waiver counts bucketed by days to expiry                                     | Security Engineering  |
| `settings_auth_failure_total{stage}`            | Failed HMAC signature or token authentication attempts against the Settings API     | Platform Architecture |
| `settings_secret_read_total{role}`              | Secret/config read requests segmented by authorized role                            | Security Engineering  |
| `settings_audit_event_total{kind}`              | Structured audit entries emitted (activation, waiver, rollback, drift)              | Security Engineering  |
| `settings_compliance_violation_total{category}` | Compliance guard hits (HIPAA, DSAR, residency) that block activations               | Security Engineering  |
| `settings_integration_sync_total{target}`       | Sync runs to Guardian, LPE, Reference Manager, portal, and worker manifests         | Platform Architecture |
| `settings_incident_open_total{severity}`        | Open incidents tied to Settings alerts/procedures                                   | SRE                   |

Alert hooks include `settings_availability_breach`, `settings_activation_delay`, `settings_governance_override_total`, `settings_auth_failure_spike`, and `settings_secret_access_anomaly`; each alert links to Appendix R procedures.

## Appendix C — Seed bundle inventory

**Purpose:** Document the curated seed bundles shipped with SR for environment bootstrap and testing.\
**Contract:** Bundles listed here must remain validated by CI and kept in sync with schema and agent expectations; edits follow the activation workflow.\
**State:** Bundles live under `config/` and `config/agents.pipeline/` with checksums recorded in `settings_seed_history`.\
**Failure modes & handling:** Validation failures block merges and deployments; update bundles, validators, and associated tests together.\
**Observability:** CI job `settings-seed-validate` reports status; dashboards track bundle ingestion and checksum drift.\
**References:** §2.8 Seed bundles, Appendix C inventory table below.\
**Breadcrumbs:** Seed scripts `ops/scripts/bootstrap_platform.py`, tests `tests/platform/settings/test_seed_bundles.py`.

| Bundle                    | Location                  | Purpose                                   | Validation                                              |
| ------------------------- | ------------------------- | ----------------------------------------- | ------------------------------------------------------- |
| `bootstrap_defaults.json` | `config/`                 | System defaults for general operation     | `ops/scripts/bootstrap_platform.py` + schema validators |
| `guardian_defaults.json`  | `config/`                 | Guardian-specific knobs consumed via SR   | Guardian integration tests                              |
| `analyze_defaults.json`   | `config/`                 | Analyze agent pipeline defaults           | Agent contract tests                                    |
| `llm_assignments.json`    | `config/`                 | LLM profile assignments                   | `tests/platform/settings/test_llm_profiles.py`          |
| `llm_providers.json`      | `config/`                 | Provider catalog entries                  | `tests/platform/settings/test_llm_profiles.py`          |
| `agents.pipeline/*.json`  | `config/agents.pipeline/` | LangGraph pipeline manifests and rollouts | `tests/platform/settings/test_pipeline_bundle.py`       |

## Appendix R — Runbooks & drills

**Purpose:** Centralize operational playbooks tied to SR alerts.\
**Contract:** Alerts enumerated in Appendix B link to these runbooks; responders keep procedures current with quarterly tabletop reviews.\
**State:** Runbooks live alongside automation scripts in `ops/runbooks/settings/`; this appendix summarizes trigger conditions and critical steps.\
**Failure modes & handling:** Missing or stale runbooks trigger post-incident corrective actions and block deploy sign-off.\
**Observability:** OnCall analytics track time-to-ack/resolve for Settings incidents; drills recorded in App.O decision logs.\
**References:** §5 Failure modes, §8 Operational notes, Appendix B metrics.\
**Breadcrumbs:** Runbooks `ops/runbooks/settings/`, tests `tests/platform/settings/test_rollback.py` and peers, OnCall configuration `infra/monitoring/settings-prometheus-rules.yaml`.

### R.1 Runbook index (informative)

**Purpose:** Provide a quick map from alert codes to runbook IDs.\
**Contract:** Every Settings alert references one of these IDs; new alerts require index updates.\
**State:** Index maintained in version control and mirrored here.\
**Failure modes & handling:** Lint script fails when the index misses an alert; add the entry before merging.\
**Observability:** Weekly docs lint verifies the index matches OnCall configuration.\
**References:** Appendix B alerts, Appendix R entries below.\
**Breadcrumbs:** Runbook index `ops/runbooks/settings/index.md`, tests `tests/platform/settings/test_runbook_index.py`.

- RB-GOV-008 — Settings governance toggle / rollback
- RB-RES-ENDPOINT — Residency endpoint drift remediation
- RB-RES-BLOCK — Residency waiver / block handling
- RB-LOCK-006 — Activation lock stale detection & remediation
- RB-LLM-003 — Provider degradation / circuit breaker
- RB-JOB-WATCHDOG — Job stall watchdog
- RB-UPLOAD-SCAN — Upload scanning outage response

### R.2 RB-GOV-008 — Settings governance toggle / rollback (binding)

**Purpose:** Safely activate or revert high-sensitivity governance toggles (waivers, residency overrides, cross-org pilots).\
**Contract:** Any activation flagged `unsafe` or touching governance scopes must follow this sequence before promotion.\
**State:** Runbook automation uses `ops/runbooks/settings_rollback.py`; evidence stores under `ops/settings/<date>/`.\
**Failure modes & handling:** Missing approvals or failed smoke tests require immediate rollback via `settings rollback --bundle <previous_id>`.\
**Observability:** Alert clears once activation completes with both approvals and validation metrics green.\
**References:** §4 State management, §5.1 Activation failure.\
**Breadcrumbs:** Runbook `ops/runbooks/settings/governance_toggle.md`, tests `tests/platform/settings/test_rollback.py`, dashboard “Settings Governance”.

Triggers: `settings_governance_override_total`, change tickets tagged `GOV-TOGGLE`, or manual escalation from Security/Architecture.

Execution checklist:

1. Announce maintenance window with activation/rollback times in `#ops-announcements`.
1. Validate staging dry-run (matching bundle hash) and attach diff evidence to change ticket.
1. Execute activation via CLI/UI, capturing activation ID and `unsafe_reasons[]` result (expected empty).
1. Run targeted smoke tests (API read/write, portal toggle, worker snapshot) tied to the toggle.
1. Update change ticket and decision log with activation ID, evidence, and rollback window.

Rollback steps:

- Reapply prior bundle via `settings rollback --bundle <previous_id>` if smoke tests or monitors fail.
- Confirm `settings.changed` event emission and run smoke tests to verify reversion.
- Communicate rollback rationale to stakeholders and attach evidence to App.O.

Evidence requirements:

- Store activation/rollback JSON artifacts under `ops/settings/<date>/`.
- Append decision log entry referencing ADR/change ticket, activation ID, and outcome.
- Attach customer/support comms templates used (see `docs/runbooks/settings/templates/governance_toggle_announce.md`).

### R.3 RB-RES-ENDPOINT — Residency endpoint drift remediation (binding)

**Breadcrumbs:** Implementation `ops/runbooks/settings/residency_endpoint_drift.md`, Tests `tests/platform/settings/test_residency_triage.py::test_endpoint_drift_runbook`, Observability Grafana “Residency & Endpoint Posture” dashboard (alert `alert_residency_endpoint_drift`).\
*Purpose: Restore compliant residency posture when outbound endpoints drift or new hosts appear.*\
*Contract: Findings remain `open` until catalogue updates or waivers recorded per this runbook.*\
*State: Findings persist in `residency_endpoint_findings`; evidence stored in `ops/residency/endpoint_scan.jsonl`.*\
*Failure modes & retries: Waivers lacking dual approval or catalogue gaps keep the finding open and block affected activations.*\
*Observability: Alert auto-resolves after two clean scans and updated catalogue hashes.*

Triage checklist:

1. Query `residency_endpoint_findings` for `state='open'`; review evidence attachments.
1. Inspect Istio AuthorizationPolicy revisions to ensure offending hosts remain blocked.
1. Identify impacted providers/orgs via activation diff linked in alert payload.

Decision tree:

- **Provider expansion** — Engage Reference Manager to ingest metadata, rerun `residency_endpoint_scan --host <fqdn>`, and promote Settings activation once SAN + GeoIP verified.
- **DNS drift/misconfig** — Flush DNS caches (`scripts/residency/flush_dns_cache.py`), roll egress gateway if stale endpoints persist.
- **Waiver path** — Seek dual approval (Security + Architecture), set temporary waiver in Settings, ensure Guardian manifests log `RESIDENCY_WAIVER_USED`.
- **False positive** — Annotate finding, keep block in place, downgrade alert severity after evidence review.

Post-remediation:

- Verify finding transitions to `mitigated` within two scans.
- Close incident with root cause, evidence links, and preventive actions (provider engagement, automation gap).
- Record outcome in decision log and App.O waiver ledger if applicable.

### R.4 RB-RES-BLOCK — Residency waiver / block handling (binding)

**Breadcrumbs:** Implementation `ops/runbooks/settings/residency_block.md`, Tests `tests/platform/settings/test_residency_validators.py::test_block_requires_waiver`, Observability Grafana “Residency Compliance” dashboard (alert `alert_residency_policy_block`).\
*Purpose: Resolve residency policy blocks triggered during activations or runtime checks.*\
*Contract: Blocks clear only after org allowlists align with RM catalogue or waivers recorded with expiry.*\
*State: Policy blocks logged as `RESIDENCY_POLICY_BLOCK`; waiver metadata stored in `settings_waiver`.*\
*Failure modes & retries: Waivers without expiry or missing approvals invalidate activation attempts.*\
*Observability: Alert returns to green once block count drops to zero.*

Steps:

1. Confirm org allowlists (`regions.allowlist.compute/storage/vector`).
1. Validate provider endpoints and DNS; compare to RM catalogue snapshots.
1. If cross-region access required, capture dual approval, set `cross_region_waiver=true`, and document expiry.
1. Re-run activation or job; confirm Guardian manifests reference waiver ID.
1. Audit waiver usage daily until expiry or remediation.

### R.5 RB-LOCK-006 — Activation lock stale detection & remediation (binding)

**Breadcrumbs:** Implementation `ops/runbooks/settings/activation_lock.md`, Tests `tests/platform/settings/test_locks.py::test_lock_scope`, Observability Grafana “Settings Lock” panel (alert `settings_activation_lock_wait_seconds`).\
*Purpose: Detect and remediate stuck activation locks without risking concurrent edits.*\
*Contract: Lock holders must release within configured `udlock.max_session_hold_seconds`; stale locks trigger this runbook.*\
*State: Lock registry tracked in `settings_activation_lock`; helper scripts expose current holders.*\
*Failure modes & retries: Forcing unlock without verifying holder state risks split-brain activations; follow decision tree below.*\
*Observability: Alert clears when lock age returns under threshold and registry shows no stale entries.*

Checklist:

1. Inspect lock registry via `scripts/settings/show_activation_locks.py` filtered by environment.
1. Verify holder liveness (`SELECT ... FROM pg_stat_activity`) to differentiate idle vs active transactions.
1. If holder dead or idle-in-transaction, coordinate worker/web restart or issue `SELECT pg_terminate_backend(...)` per policy.
1. After release, rerun activation pipeline smoke tests; capture evidence in incident log.
1. File follow-up if lock reappears within 24h (root cause investigation, automation fix).

### R.6 RB-LLM-003 — Provider degradation / circuit breaker (binding)

**Breadcrumbs:** Implementation `ops/runbooks/settings/provider_circuit_breaker.md`, Tests `tests/platform/settings/test_llm_circuit.py::test_half_open_probe`, Observability Grafana “FinOps – LLM Cost & Circuit” dashboard (alert `alert_llm_circuit_open`).\
*Purpose: Handle degraded LLM providers to protect cost and SLA budgets.*\
*Contract: OPEN circuits remain until provider health verifies; half-open probes follow cadence defined here.*\
*State: Circuit state stored in `settings_llm_circuit`; fallback chains defined in Settings bundles.*\
*Failure modes & retries: Prematurely closing circuits or leaving fallback unmonitored risks runaway spend and job failures.*\
*Observability: Alert resolves when circuit state returns to CLOSED for affected models and cost deltas stabilize.*

Response steps:

1. Confirm affected models via dashboard filters (`llm_circuit_state{model}`) and review recent error/latency metrics.
1. Validate fallback outcomes in logs (`PRIMARY_DEGRADED`, `FALLBACK_USED`) and ensure FinOps guardrails intact.
1. Keep circuits OPEN until three consecutive successful half-open probes; adjust fallback priorities if secondary models degrade.
1. Notify vendor/support with incident details when degradation persists >15 minutes; record ticket IDs in incident log.
1. After recovery, document budget impact and corrective actions; update preventive tasks (synthetic prompts, timeout tuning).

### R.7 RB-JOB-WATCHDOG — Job stall watchdog (binding)

**Breadcrumbs:** Implementation `ops/runbooks/platform/job_watchdog.md`, Tests `tests/platform/watchdog/test_job_timeout.py::test_timeout_escalation`, Observability Grafana “Watchdog Runner” dashboard (alerts `job_watchdog_warning_total`, `job_watchdog_timeout_total`).\
*Purpose: Restore stuck jobs and protect downstream SLAs when heartbeats lapse.*\
*Contract: Watchdog alerts trigger within `jobs.watchdog.no_progress_minutes` / `jobs.watchdog.timeout_minutes`; responders must either resume progress or terminate safely.*\
*State: Heartbeats stored in `job_progress_heartbeat`; remediation evidence captured in incident ticket (`ops/watchdog/<date>/`).*\
*Failure modes & retries: Premature termination can lose customer work; skipping checkpoint verification risks replaying corrupted artifacts.*\
*Observability: Alert clears after watchdog completes remediation and fresh heartbeats resume for affected jobs.*

Triage & remediation:

1. Identify affected job IDs from alert payload; confirm `job_progress_heartbeat` age and last known task lane.
1. Inspect worker logs for stalled tasks, resource exhaustion, or upstream dependency failures; capture excerpts in incident notes.
1. If work-in-progress artifacts exist, trigger checkpoint validation (`ops/jobs/verify_checkpoint.py`) before retrying.
1. Attempt safe resume via `jobs resume --job <id>` when the worker is healthy; otherwise cancel and requeue after addressing root cause.
1. Close alert once heartbeats refresh (\< 2 × `jobs.watchdog.heartbeat_interval`) and audit trail updated with remediation steps.

Post-incident follow-up:

- File preventive tasks when repeated stalls originate from the same provider lane or dependency.
- Review Settings defaults (`jobs.watchdog.*`) to confirm thresholds remain appropriate for the workload mix.

### R.8 RB-UPLOAD-SCAN — Upload scanning outage response (binding)

**Breadcrumbs:** Implementation `ops/runbooks/security/upload_scan.md`, Tests `tests/security/test_upload_scan_guard.py::test_quarantine_on_failure`, Observability Grafana “Security — Upload Scanning” dashboard (alerts `upload_scan_error_total`, `upload_scan_queue_depth`).\
*Purpose: Maintain quarantine-first posture when malware scanning or format validation degrades.*\
*Contract: New uploads remain blocked (`uploads.enabled=false`) until scanners return to green and evidence recorded per this runbook.*\
*State: Scan attempts logged in `upload_scan_audit`; quarantined objects isolated under `storage/quarantine/<job_id>/`.*\
*Failure modes & retries: Re-enabling uploads without updated signatures risks releasing infected files; overriding quarantine without approvals violates security policy.*\
*Observability: Alert clears after two consecutive clean scan batches and queue depth normalizes below baseline.*

Response sequence:

1. Confirm scope of degradation (engine errors vs. queue backlog) using dashboard drill-downs and `upload_scan_audit` sampling.
1. Freeze new intake by toggling `uploads.enabled=false` in Settings; announce customer impact and expected review window.
1. Validate scanner health: check ClamAV/YARA signature freshness, sandbox resource utilization, and recent deployment changes.
1. For malware detections, coordinate with Security to analyze samples; maintain quarantine until signatures updated and retest passes.
1. Once scanners stable, re-enable uploads, replay quarantined items through the pipeline, and attach evidence (dashboards, signature reports) to the incident record.

Follow-up:

- File change tasks for signature automation gaps or scaling adjustments discovered during the incident.
- Update customer/regulator communications templates with incident summary and remediation timeline.
