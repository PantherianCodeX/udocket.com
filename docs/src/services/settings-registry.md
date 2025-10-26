---
title: "uDocket — Settings Registry Technical Design"
subtitle: "Configuration Governance & Activation Specification"
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
  - '<base href="..">'
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
  - '<header class="page-header">uDocket — Settings Registry Technical Design <br> Configuration Governance &amp; Activation Specification</header>'
  - '<footer class="page-footer">Confidential · Last updated 2025-10-23 · Page <span class="page-number"></span> of <span class="page-count"></span></footer>'
---

**Audience:** Platform engineering, Guardian, Localization & Policy Engine, Reference Manager, SRE, QA, Product Operations\
**Purpose:** Define Settings Registry (SR) responsibilities, contracts, activation lifecycle, and observability so every service consumes consistent, auditable configuration.

---

## Document controls

| Field           | Value |
| --------------- | ----- |
| Version         | 0.1-draft |
| Status          | Implementable (mirrors front matter `status`; KEP lifecycle applies: Provisional → Implementable → Implemented) |
| Last updated    | 2025-10-23 (source of truth is the front matter `last_updated`) |
| Primary owners  | Platform Architecture; Security Engineering; Settings Program |
| Approvers       | Architecture Steering Committee; Security Review Board |
| Reviewers       | QA Engineering Lead; SRE Manager |
| ADR index       | `docs/adr/README.md` (immutable ADRs referenced in front matter `related_adrs`) |
| Migration plan  | Supersede legacy TDD §9 and Appendix E once Architecture/Security approvals record; platform TDD now links here for SR specifics |
| Docs validation | `python scripts/docs/lint_docs.py` (see `docs/README.md` for tooling) |
| Link lint       | `python scripts/docs/link_check.py --strict` (CI `docs-link-check` stage blocks unresolved §/App./ADR refs) |

Body sections follow the Purpose/Contract/State/Failure/Observability/Breadcrumb scaffold enforced by `scripts/docs/lint_docs.py --check-template`. Section tags `(binding)` and `(normative)` align with the platform TDD.

---

## 0) Reading guide

- **Scope:** Service charter, hierarchical model, API/SDK contracts, activation workflow, governance controls, integrations, telemetry, and key catalog for the Settings Registry.
- **Structure:** Numbered sections limited to three levels of depth; appendices surface detailed key maps, metrics, and seed bundle references.
- **Cross-references:** Use `§<number>` for this document, `TDD §<number>` for the platform TDD, and `App.<letter>` when pointing at appendices.
- **Maintenance:** Run `python scripts/docs/lint_docs.py` before submitting edits. Schema snippets must match `spec/schemas/*` fixtures; CI enforces parity for key catalogs and activation templates.
- **Doc change protocol:** Any PR modifying SR APIs, activation logic, bundle schemas, or governance gates must update this document and cite relevant ADRs. Architecture/Security reviewers block merges when code, SDKs, or docs diverge.

---

## 1) Service overview

### 1.1 Charter & mandate (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/service.py::create_app`, Tests `tests/platform/settings/test_charter.py::test_scope_enforced`, Observability Grafana “Settings Registry – Availability” dashboard (metrics `settings_request_total`, `settings_error_total`).\
*Purpose: Describe Settings Registry responsibilities, success criteria, and lifecycle expectations.*\
*Contract: SR centralizes configuration for system, organization, and case scopes; publishes audited activations; and provides immutable snapshots consumed across services.*\
*State: Configuration persists in Postgres tables `setting_bundle`, `setting_bundle_version`, `setting_activation`, and Redis caches keyed by `(scope, org_id, case_id, bundle_id)`.*\
*Failure modes & retries: Service degrades to read-only when activation validators fail or advisory locks remain held; clients must block unsafe writes and use embedded snapshots for in-flight jobs.*\
*Observability: Availability SLO 99.9%, request/error metrics above plus `settings_activation_total{result}`, traces annotate `settings_version` and `activation_id`.*

- SR governs configuration inheritance, residency allowlists, FinOps ceilings, LLM profiles, Guardian/Signer knobs, and UI feature flags.
- Service lifecycle aligns with ADR states; deprecations or structural changes require ADR updates and dual approval.
- All downstream decisions must cite snapshot digests, ensuring reproducibility for audits and incident response.

### 1.2 Stakeholders & integrations (normative)

**Breadcrumbs:** Implementation `apps/platform/settings/clients.py::SettingsClient`, Tests `tests/platform/settings/test_client_contract.py::test_snapshot_integrity`, Observability Grafana “Settings Registry – Consumer Adoption” dashboard (metrics `settings_snapshot_issued_total`, `settings_snapshot_stale_total`).\
*Purpose: Enumerate primary consumers and integration responsibilities.*\
*Contract: SR serves Guardian, LPE, Reference Manager, Portal, Workers, and Observability fabric with consistent configuration snapshots and change events.*\
*State: Consumers register adoption status in `settings_consumer_adoption` (org, bundle, version, status). Event bus topics `settings.changed` and `settings.snapshot_issued` record propagation.*\
*Failure modes & retries: Missed invalidation events trigger drift detection jobs and synthetic fetches; consumers fall back to last known good snapshot but must block mutations until refreshed.*\
*Observability: Consumer dashboards show adoption lag, invalidation latency, and stale snapshot counts.*

- Guardian enforces judgment flows using SR-configured policies and waivers.
- LPE activation dry-runs integrate with SR validators to ensure residency and localization remain compliant.
- Workers embed `settings_snapshot_sha256` and `settings_version_id` into manifests and telemetry for each job.
- Portal and staff UI consume SR toggles for feature availability, localization hints, and approval flows.

### 1.3 Service-level objectives (binding)

**Breadcrumbs:** Implementation Helm chart `infra/kubernetes/settings/values.yaml`, Tests `tests/synthetics/test_settings_slo.py::test_latency_budget`, Observability Grafana “Settings Registry – SLO” dashboard (metric `settings_latency_seconds`).\
*Purpose: State reliability targets and deployment guardrails.*\
*Contract: SR maintains 99.9% availability, p95 read latency ≤ 120 ms, activation completion p95 ≤ 2 minutes, and cache invalidation propagation ≤ 60 seconds.*\
*State: SLO tracking stored in `sre_error_budget` with monthly burn rate entries.*\
*Failure modes & retries: Breach of burn rate >1.0 for 60 minutes freezes activations and halts blue/green promotion until mitigated.*\
*Observability: Synthetic monitors exercise read/activation APIs per deploy; alerts `settings_availability_breach` and `settings_activation_delay` gate releases.*

---

## 2) Configuration model

### 2.1 Hierarchical scopes & precedence (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/models.py::Scope`, Tests `tests/platform/settings/test_scope_precedence.py::test_effective_resolution`, Observability Grafana “Settings – Scope Mix” panel (metric `settings_scope_resolution_total`).\
*Purpose: Describe how configuration inherits and overrides safely across tenants.*\
*Contract: SR evaluates configuration by overlaying CASE over ORG over SYSTEM scopes using Pydantic bundle definitions with explicit precedence rules.*\
*State: Effective settings materialize into `setting_effective` with foreign keys to contributing bundle versions.*\
*Failure modes & retries: Invalid overrides (e.g., CASE relaxing residency) raise `SETTINGS_INVALID_OVERRIDE`; activation rejected until corrected.*\
*Observability: Metrics track override rates and rejected overrides; traces include contributing scope chain.*

- Sensitive keys (secrets, trust roots) remain encrypted at rest; read APIs redact secrets while activation history retains digests.
- Bundles include schema metadata referencing Appendix A for key catalog and defaults.
- Certain keys enforce immutability at lower scopes (residency, immutable logging sinks) and rely on validator guardrails.

### 2.2 Definition schema & validation (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/settings/schema.py::SettingDefinition`, Tests `tests/platform/settings/test_definition_schema.py::test_validator_bounds`, Observability Grafana “Settings – Validation” panel (metric `settings_validation_failure_total`).\
*Purpose: Detail the schema enforcing data types, constraints, and documentation for settings keys.*\
*Contract: All definitions use the shared `SettingDefinition` model with literal datatypes, scope guards, default values, documentation strings, and validator hooks.*\
*State: Definitions load from `config/settings_definitions.json` and compile into versioned JSON Schema artifacts stored in `setting_definition_schema`.*\
*Failure modes & retries: Missing or malformed definitions fail CI (`python scripts/docs/check_settings_keys.py`) and block deployment until corrected.*\
*Observability: Validation metrics categorize failure reasons (type_mismatch, range_violation, forbidden_scope); audit logs attach schema version IDs.*

- Case-scoped keys include agent prompt overrides, retry ceilings, visibility toggles, and portal expiry limits.
- System/org keys cover residency allowlists, quotas, notifications, TLS policy, encryption posture, FinOps thresholds, and enumerations for cases and artifacts.
- Privacy helpers publish templates via `/api/v1/settings/privacy/templates`, ensuring DPIA/RoPA tooling aligns with Appendix C (platform TDD).

### 2.3 Snapshot & manifest contract (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/settings/snapshot.py::SettingsSnapshot`, Tests `tests/platform/settings/test_snapshot_contract.py::test_digest_stability`, Observability Grafana “Settings – Snapshot Integrity” dashboard (metric `settings_snapshot_mismatch_total`).\
*Purpose: Ensure downstream services embed immutable configuration context.*\
*Contract: Snapshots include `{version_id, bundle_ids[], contributing_scopes[], sha256}`; consumers persist digests in manifests, telemetry, and audit logs.*\
*State: Snapshot records stored in `settings_snapshot` and attached to jobs, artifacts, and policy contexts via foreign keys.*\
*Failure modes & retries: Snapshot mismatches trigger drift incidents; workers block new jobs until updated snapshot retrieved.*\
*Observability: Drift detection compares stored digests to current effective hashes and alerts `settings_snapshot_stale_total`.*

- Every job manifest includes `settings_snapshot_sha256` and `settings_version_id` for replay.
- Guardian, Portal, and Workers log snapshot digests within structured events for traceability.

### 2.4 Residency & egress controls (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/validators/residency.py::validate_residency_controls`, Tests `tests/platform/settings/test_residency_validators.py::test_allowlist_enforcement`, Observability Grafana “Residency Compliance” dashboard (metric `settings_residency_violation_total`).\
*Purpose: Capture residency, egress, and waiver rules enforced by SR.*\
*Contract: SR validates `regions.allowlist.*`, `network.egress.allowed_hosts`, and residency waivers against Reference Manager catalogues before activation.*\
*State: Residency metadata persists in `settings_residency_profile` with cross-references to RM bundles and waiver records.*\
*Failure modes & retries: Missing catalog entries raise `RESIDENCY_ENDPOINT_NEW`; activations remain blocked until RM ingestion completes or waiver approved.*\
*Observability: Audit events `RESIDENCY_ENDPOINT_NEW`, metrics `settings_residency_violation_total`, and nightly drift scans ensure compliance.*

- Change detection opens Security tickets (`SEC-RESIDENCY-ENDPOINT`) and requires dual approval for temporary waivers.
- Closure requires two consecutive compliant scans before incidents resolve; evidence attaches to decision log entries.

---

## 3) API surface & clients

### 3.1 REST endpoints (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/api.py`, Tests `tests/platform/settings/test_api_endpoints.py::test_rest_contract`, Observability Grafana “Settings API” panel (metric `settings_api_latency_seconds`).\
*Purpose: Define SR REST APIs and required behaviour.*\
*Contract: SR exposes `GET /api/v1/settings/<scope>`, `GET /api/v1/settings/bundles/<id>`, `POST /api/v1/settings/bundles`, and `/api/v1/settings/validate/*`; responses must include version metadata and contributing scopes.*\
*State: API definitions live in `ops/openapi/settings.openapi.yaml`; generated clients remain in sync via `scripts/sdk/check_openapi_alignment.py`.*\
*Failure modes & retries: Idempotency enforced via advisory locks; conflicting activations yield `409` with retry-after guidance.*\
*Observability: Structured logs capture request IDs, actor IDs, scopes; rate metrics differentiate read vs activation traffic.*

- `/api/v1/settings/privacy/templates` surfaces DPIA/RoPA metadata keyed by matrix version.
- Read APIs respect `If-None-Match` ETags based on snapshot hash to reduce load.

### 3.2 SDK usage & caching (normative)

**Breadcrumbs:** Implementation `packages/udocket_core/settings/client.py::SettingsClient`, Tests `tests/platform/settings/test_sdk_cache.py::test_cache_invalidation`, Observability Grafana “Settings Client Cache” panel (metric `settings_cache_hit_ratio`).\
*Purpose: Provide client contract for caching and snapshotting.*\
*Contract: SDK caches results per request context, supports typed access (`get(key, type=...)`), and persists snapshots for embedding in jobs.*\
*State: Client caches store TTL metadata and version IDs; invalidation subscribes to Redis pub/sub channel `settings.changed`.*\
*Failure modes & retries: Cache misses fallback to API fetch; stale caches after invalidation trigger warnings and forced reload.*\
*Observability: Metrics track cache hit ratio and invalidation lag; traces annotate cache status.*

- Clients avoid `.env` usage beyond bootstrapping; runtime relies on SR for truth.
- SDK exports helpers for dry-run validation and diff preview consumption.

### 3.3 Authentication & request signing (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/security.py::sign_request`, Tests `tests/platform/settings/test_auth.py::test_hmac_signature`, Observability Grafana “Settings Auth” dashboard (metric `settings_auth_failure_total`).\
*Purpose: Enforce secure access to mutating endpoints.*\
*Contract: Mutations require service tokens plus HMAC signing; actors supply `X-Signature-Key-Id`, `X-Timestamp`, and Idempotency headers.*\
*State: Key metadata stored in `settings_hmac_key`; rotations recorded with activation references.*\
*Failure modes & retries: Signature mismatches return `401`; clients must refresh keys or resync clocks (±30 seconds skew allowed).*\
*Observability: Auth failure metrics categorize reasons (signature_mismatch, expired_timestamp, disabled_key); audit events capture actor and bundle IDs.*

### 3.4 Privacy & redaction (normative)

**Breadcrumbs:** Implementation `apps/platform/settings/redaction.py::redact_sensitive_values`, Tests `tests/platform/settings/test_redaction.py::test_secret_masking`, Observability Grafana “Settings – Secret Access” panel (metric `settings_secret_read_total`).\
*Purpose: Protect sensitive configuration when displayed or exported.*\
*Contract: SR redacts secret values in API responses, CLI exports, and diff previews; only hashed digests stored in activation history.*\
*State: Secret metadata tracked in `settings_secret_meta` including scope, rotation cadence, and masking policy.*\
*Failure modes & retries: Attempts to expose secrets trigger `SECRET_DISCLOSURE_BLOCKED`; audit entries require Security review.*\
*Observability: Secret access counters segmented by actor role; anomaly detection alerts on spikes.*

---

## 4) Activation workflow & governance

### 4.1 Activation pipeline (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/services/activation.py::activate_bundle`, Tests `tests/platform/settings/test_activation_flow.py::test_pipeline_success`, Observability Grafana “Settings Activation” dashboard (metric `settings_activation_duration_seconds`).\
*Purpose: Describe the activation flow from submission through publish.*\
*Contract: Activations compute diffs, run validators, persist audit trails, publish invalidation events, and enforce blue/green rollout sequencing.*\
*State: Pipeline stages recorded in `setting_activation_stage`; advisory locks guard concurrent activations per org/bundle.*\
*Failure modes & retries: Validator failures mark activations unsafe; operators must remediate and resubmit. Rollback replays previous bundle with identical audit metadata.*\
*Observability: Activation metrics track durations, unsafe counts, rollback frequency; traces link to change tickets.*

- Diff previews produce human-readable and machine JSON artifacts for reviewers.
- Activation history retains signatures, actor IDs, roles, and justification text.

### 4.2 Diff preview & dry-run validation (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/services/diff.py::render_diff`, Tests `tests/platform/settings/test_diff_preview.py::test_diff_outputs`, Observability Grafana “Settings Diff” panel (metric `settings_diff_generated_total`).\
*Purpose: Provide reviewers visibility into proposed changes before approval.*\
*Contract: Dry-runs compare compiled tables (`effective_permission`, `field_mask_rule`, residency profiles) and surface unsafe reasons requiring dual approval.*\
*State: Diff artifacts stored in `settings_activation_diff` with SHA-256 digests.*\
*Failure modes & retries: Missing diff or compilation error blocks approval; rerun pipeline after correcting data.*\
*Observability: Diff generation metrics segmented by bundle type; alerts fire when diff generation fails >3 times consecutively.*

### 4.3 Dual approval & waiver workflow (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/services/approvals.py::require_dual_approval`, Tests `tests/platform/settings/test_governance.py::test_dual_approval_required`, Observability Grafana “Settings Governance” dashboard (metric `settings_dual_approval_total`).\
*Purpose: Enforce governance for risky changes.*\
*Contract: Activations flagged unsafe demand dual approval (Security + Architecture) with step-up MFA and recorded justification; waivers embed waiver IDs and expiry.*\
*State: Approval records stored in `settings_activation_approval`; waivers tracked in `settings_waiver` referencing App.O decision log entries.*\
*Failure modes & retries: Missing approvals keep activation pending; expired waivers trigger alerts and block reactivation.*\
*Observability: Governance metrics track waiver counts, unsafe activations, and approval latency; audit events `SETTINGS_CHANGE_REQUESTED` and `SETTINGS_WAIVER_APPLIED` broadcast.*

### 4.4 Locking & concurrency control (normative)

**Breadcrumbs:** Implementation `apps/platform/settings/services/locks.py::acquire_activation_lock`, Tests `tests/platform/settings/test_locks.py::test_lock_scope`, Observability Grafana “Settings Lock” panel (metric `settings_activation_lock_wait_seconds`).\
*Purpose: Prevent conflicting activations and enforce uniqueness.*\
*Contract: SR acquires advisory lock `settings-activate:{org_id}` and enforces OCC on active bundle rows; only one ACTIVE bundle per org/bundle combination.*\
*State: Lock metadata recorded in `settings_activation_lock` with timestamps and holder IDs.*\
*Failure modes & retries: Lock timeout surfaces `ACTIVATION_CONFLICT`; retry after backoff once lock released.*\
*Observability: Lock wait metrics highlight contention; alerts trigger when waits exceed 30 seconds.*

### 4.5 Caching & invalidation (normative)

**Breadcrumbs:** Implementation `apps/platform/settings/cache.py::invalidate`, Tests `tests/platform/settings/test_invalidation.py::test_cache_flush`, Observability Grafana “Settings Cache” dashboard (metric `settings_cache_invalidation_lag_seconds`).\
*Purpose: Keep runtime views consistent without stale decisions.*\
*Contract: SR publishes `settings.changed` events `{scope, org_id, case_id, bundle_id}`; subscribers flush caches and refresh on next access.*\
*State: Redis pub/sub channel stores event history for 1 hour; fallback polling verifies adoption.*\
*Failure modes & retries: Missed events trigger fallback poller; repeated misses raise incident `SETTINGS_INVALIDATION_STALLED`.*\
*Observability: Cache lag metrics and synthetic fetches confirm propagation within 60 seconds.*

### 4.6 Telemetry & drift detection (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/telemetry.py::record_metrics`, Tests `tests/platform/settings/test_drift.py::test_snapshot_drift_detection`, Observability Grafana “Settings Drift” dashboard (metric `settings_snapshot_drift_total`).\
*Purpose: Provide visibility into configuration usage and anomalies.*\
*Contract: SR emits metrics `settings_cache_hit_ratio`, `settings_activation_total`, `settings_validation_failure_total`, `policy_compile_duration_seconds`, and drift alerts comparing snapshots vs effective hashes.*\
*State: Drift findings stored in `settings_drift_finding` with remediation workflow.*\
*Failure modes & retries: Unresolved drift escalates to incident management; activations freeze until resolved.*\
*Observability: Dashboards aggregate drift severity; alerts integrate with on-call rotations.*

---

## 5) Agent & automation configuration

### 5.1 Pipeline bundles & staged overrides (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/services/pipeline_bundle.py::apply_pipeline_bundle`, Tests `tests/platform/settings/test_pipeline_bundle.py::test_override_validation`, Observability Grafana “Agent Pipeline Rollouts” dashboard (metric `pipeline_rollout_state`).\
*Purpose: Externalize LangGraph pipeline composition, prompts, and ceilings into audited configuration.*\
*Contract: Keys `agents.pipeline.definitions[]`, `agents.pipeline.assignments[]`, `agents.pipeline.overrides[]`, `agents.prompts.*`, and `agents.llm_profiles.*` define pipeline manifests, assignments, overrides, prompts, and LLM profiles with validator-enforced safety bounds.*\
*State: Pipeline definitions stored in `settings_pipeline_definition`; rollouts tracked in `settings_pipeline_rollout` with wave metadata.*\
*Failure modes & retries: Invalid prompt references, tool IDs, or ceiling relaxations raise validation errors; activations blocked until corrected.*\
*Observability: Telemetry records rollout state per org, prompt revisions, and cost ceilings; job telemetry logs `pipeline_definition_version`.*

- Assistant knobs (`assistant.retrieval.sources[]`, `assistant.moderation.tiers[]`, `assistant.citation.style`) share validator framework ensuring alignment with shared assets.
- Activations altering definitions or rollouts tag `change_class="system"`, require change ticket linkage, and follow blue/green rollout gates.

### 5.2 Tool catalog & capability gating (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/services/tool_catalog.py::sync_catalog`, Tests `tests/platform/settings/test_tool_catalog.py::test_catalog_validation`, Observability Grafana “Agent Tooling” panel (metric `tool_invocation_total`).\
*Purpose: Govern LangGraph tool introduction and exposure per tenant.*\
*Contract: Keys `agents.tools.catalog[]`, `agents.tools.allowlist[]`, and `agents.tools.policies.*` register tools, expose allowlists, and enforce residency/classification ceilings.*\
*State: Catalog entries persist in `settings_tool_catalog`; allowlists stored in `settings_tool_allowlist` per scope.*\
*Failure modes & retries: Schema mismatches or attempts to widen residency/cost without approvals raise validation errors; forced overrides require dual approval with waiver metadata.*\
*Observability: Metrics and audit logs (`ops/tools/ops_tools.jsonl`) track invocation counts, error rates, and cost estimates.*

- `GET /api/v1/settings/tools/catalog` returns effective catalog JSON for operators and editors.

### 5.3 LLM profiles & moderation controls (normative)

**Breadcrumbs:** Implementation `apps/platform/settings/services/llm_profiles.py::validate_profiles`, Tests `tests/platform/settings/test_llm_profiles.py::test_profile_bounds`, Observability Grafana “LLM Profile Adoption” dashboard (metric `llm_profile_assignment_total`).\
*Purpose: Manage provider catalogs, version pins, moderation thresholds, and BYO vetting.*\
*Contract: Keys `llm.providers[]`, `llm.models[]`, `llm.models.version_pin`, `llm.enforce_model_version`, `llm.moderation.*`, and `llm.byo.*` define provider usage, pins, moderation thresholds, and BYO requirements.*\
*State: Provider and model metadata stored in `settings_llm_profile`; BYO endpoints cross-referenced with RM catalog.*\
*Failure modes & retries: Drift from version pins or missing evaluation suites block activation; BYO entries require validated VPC endpoints and evaluation IDs.*\
*Observability: Metrics track provider adoption, moderation enforcement, and BYO utilization; alerts raise on version drift.*

### 5.4 Seed bundles & no-code configuration (binding)

**Breadcrumbs:** Implementation `ops/scripts/bootstrap_platform.py`, Tests `tests/platform/settings/test_seed_bundles.py::test_seed_validation`, Observability CI job “settings-seed-validate” (artifact `ops/settings/seed_validate.json`).\
*Purpose: Enable environment bootstrap without code changes using validated JSON bundles.*\
*Contract: Repository ships versioned JSON seed bundles ingested via SR with identical validators to runtime activation; operators adjust prompts or policies by editing JSON, running validators, and activating bundles.*\
*State: Seeds stored under `config/` with metadata `{version, source_commit, checksum}`; ingestion records entries in `settings_seed_history`.*\
*Failure modes & retries: Seeds referencing unknown keys or out-of-range values fail validation; CI blocks merges until corrected.*\
*Observability: Seed validation reports published in CI; deployment automation logs ingestion status and checksum verification.*

---

## 6) Integrations & enforcement points

### 6.1 Enforcement touchpoints (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/services/enforcement.py::list_touchpoints`, Tests `tests/platform/settings/test_enforcement_points.py::test_required_fetch`, Observability Grafana “Settings Enforcement” dashboard (metric `settings_enforcement_lookup_total`).\
*Purpose: Enumerate runtime surfaces that must consult SR.*\
*Contract: APIs, workers, front-end flows, and database policies fetch current settings snapshots before decision-making and record digests in logs.*\
*State: Enforcement registry stored in `settings_enforcement_point` with required bundles and validation hooks.*\
*Failure modes & retries: Missing enforcement registration triggers lint failures; runtime detection of stale snapshots blocks operations until refreshed.*\
*Observability: Enforcement metrics cover lookup volume and stale detection; alerts signal when TTL thresholds exceeded.*

- API enforcement covers RBAC writes, CORS, rate limits, portal downloads, HIPAA/PHIPA banners, and residency gating.
- Worker enforcement includes agent configurations, FinOps ceilings, Guardian/Signer integration, and waiver gating.
- Front-end enforcement drives feature flags, approvals, messaging flows, and localization decisions.
- Database enforcement ensures RLS and masking profiles reference compiled tables from SR activations and LPE contexts.

### 6.2 Guardian, LPE, and RM alignment (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/services/integration.py::sync_with_guardian`, Tests `tests/platform/settings/test_lpe_guardian_bridge.py::test_bundle_alignment`, Observability Grafana “Settings Integration” dashboard (metric `settings_integration_sync_total`).\
*Purpose: Define coordination with Guardian, LPE, and Reference Manager.*\
*Contract: SR consumes RM bundles for residency/provider catalogs, triggers LPE dry-run compiles, and exposes Guardian waivers and policy toggles with shared digests.*\
*State: Integration metadata persisted in `settings_integration_status` referencing RM bundle IDs and LPE compile versions.*\
*Failure modes & retries: Missing RM bundle or failed LPE compile flags activation unsafe; require remediation before approval.*\
*Observability: Integration metrics capture sync success, waiver usage, and compile durations.*

- Residency endpoint changes open Security tickets; waivers demand dual approval and manifest stamping until replacement endpoints validated.
- Guardian gating configuration, including review modes and operator visibility, surfaces via SR keys and audit events.

### 6.3 Portal & client experience (normative)

**Breadcrumbs:** Implementation `apps/platform/settings/services/portal_profile.py::render_portal_settings`, Tests `tests/platform/settings/test_portal_profile.py::test_portal_contract`, Observability Grafana “Portal Settings” dashboard (metric `portal_settings_lookup_total`).\
*Purpose: Outline SR responsibilities for portal/client exposures.*\
*Contract: SR provides localized disclaimers, enabled locales, HIPAA allowances, rate limits, and chat assistant toggles for portal consumption.*\
*State: Portal profile snapshots stored in `settings_portal_profile` with `portal_visible=true` filters.*\
*Failure modes & retries: Attempting to expose masked fields triggers validation errors; portal blocks rendering until resolved.*\
*Observability: Metrics track portal profile lookups and cache hit ratios; alerts fire on mismatch between SR and portal caches.*

- Chat assistants mirror SR rate limits and token budgets; Settings updates propagate to portal warnings and UI pickers.

### 6.4 Worker pipelines & job manifests (binding)

**Breadcrumbs:** Implementation `apps/platform/operations/tasks.py::hydrate_settings_snapshot`, Tests `tests/platform/operations/test_settings_snapshot.py::test_manifest_embedding`, Observability Grafana “Worker Settings” panel (metric `settings_snapshot_job_total`).\
*Purpose: Ensure job pipelines consume SR snapshots consistently.*\
*Contract: Workers fetch settings before task execution, embed snapshot digests in manifests, and persist to ops logs and audit JSONL.*\
*State: Snapshot references stored alongside job records and artifact manifests.*\
*Failure modes & retries: Failed fetch blocks job start; backlog alerts fire when snapshot retrieval exceeds retry window.*\
*Observability: Metrics capture job snapshot usage; alerts highlight stale snapshots or fetch failures.*

---

## 7) Security, compliance, and incident response

### 7.1 Access control & RLS (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/models.py::SettingAccessPolicy`, Tests `tests/platform/settings/test_access_control.py::test_role_permissions`, Observability Grafana “Settings Access” dashboard (metric `settings_access_violation_total`).\
*Purpose: Define SR access model.*\
*Contract: SR enforces deny-by-default policies using compiled `effective_permission` tables; only `sysadmin` bypasses via explicit policy.*\
*State: Access grants stored in `setting_permission` referencing roles and resources.*\
*Failure modes & retries: Unauthorized attempts raise `403`; audit logs capture actor, scope, and requested action.*\
*Observability: Access violation metrics feed security dashboards; anomalies escalate via SIEM integrations.*

- Field masking rules compile into `field_mask_rule` tables refreshed per activation.

### 7.2 Audit logging & retention (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/audit.py::record_activation_audit`, Tests `tests/platform/settings/test_audit_log.py::test_audit_entries`, Observability Grafana “Settings Audit Trail” dashboard (metric `settings_audit_event_total`).\
*Purpose: Maintain complete audit history for regulatory review.*\
*Contract: Every activation, validation failure, unsafe reason, waiver, and cache invalidation produces structured audit events stored in immutable sinks.*\
*State: Audit events stream to `ops/settings/ops_settings.jsonl` and warehouse tables with retention aligned to compliance policies.*\
*Failure modes & retries: Immutable sink toggle attempts blocked; fallback storage engaged if sink unavailable, triggering incident.*\
*Observability: Audit completeness monitors ensure sink ingestion; alerts fire if events missing beyond 5 minutes.*

### 7.3 Incident response & rollback (binding)

**Breadcrumbs:** Implementation guidance Appendix R entry RB-GOV-008, Scripts `ops/runbooks/settings_rollback.py`, Tests `tests/platform/settings/test_rollback.py::test_replay_last_good`, Observability Grafana “Settings Incidents” panel (metric `settings_incident_open_total`).\
*Purpose: Provide repeatable rollback and incident handling procedures.*\
*Contract: On unsafe activation or drift incident, freeze new activations, replay last known good bundle, notify stakeholders, and document remediation per the Appendix R entry.*\
*State: Automation stores rollback checkpoints and evidence attachments.*\
*Failure modes & retries: Rollback failure escalates to incident commander; automation retries with exponential backoff before manual intervention.*\
*Observability: Incident metrics track open vs resolved counts; postmortem artifacts reference activation IDs and audit digests.*

### 7.4 Compliance & privacy obligations (normative)

**Breadcrumbs:** Implementation `apps/platform/settings/compliance.py::enforce_compliance_keys`, Tests `tests/platform/settings/test_compliance.py::test_retention_controls`, Observability Grafana “Settings Compliance” dashboard (metric `settings_compliance_violation_total`).\
*Purpose: Capture DSAR, retention, HIPAA, and disclosure requirements enforced by SR.*\
*Contract: Keys such as `compliance.erasure_mode`, `compliance.subject_hkdf_salt`, `privacy.hipaa.*`, and `privacy.legal.matrix_version` must exist and pass validators before activation.*\
*State: Compliance profile metadata stored in `settings_compliance_profile` tied to Reference Manager legal matrices.*\
*Failure modes & retries: Missing keys or invalid values block activation; forced overrides demand dual approval and audit citations.*\
*Observability: Compliance metrics track enforcement outcomes; alerts highlight expiring HIPAA bundles or DSAR configuration drift.*

---

## Appendix A — Settings key map & traceability index

**Breadcrumbs:** Implementation `scripts/docs/check_settings_keys.py`, Tests `tests/docs/test_check_settings_keys.py::test_registry_complete`, Observability Grafana "Docs – Settings Coverage" dashboard (metric `docs_settings_key_missing_total`).\
*Purpose: Link platform behaviour to Settings Registry configuration for audit and troubleshooting.*\
*Contract: Every key referenced in code, bundles, or docs must appear in this appendix with scope, defaults, and enforcement notes.*\
*State: Appendix maintained in version control; automation cross-checks against `config/settings_definitions.json`, runtime validators, and seed bundles.*\
*Failure modes & retries: Missing mappings fail `python scripts/docs/check_settings_keys.py`; fix definitions and update this appendix in the same patch.*\
*Observability: Docs lint metrics raise alerts on coverage gaps; release checklist blocks promotion when lint fails.*

### A.1 Key catalog (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/settings/schema.py::SettingDefinition`, Tests `tests/platform/settings/test_definition_schema.py::test_all_keys_documented`, Observability Grafana "Settings – Definition Coverage" dashboard (metric `settings_definition_gap_total`).\
*Purpose: Provide authoritative coverage of Settings Registry keys, scopes, defaults, and enforcement hooks.*\
*Contract: Keys listed here must exist in definitions, validators, and runtime usage; consumers reference this table instead of duplicating values elsewhere.*\
*State: Source-of-truth definitions live in `config/settings_definitions.json`; effective settings surface through `setting_effective` and `settings_snapshot` tables.*\
*Failure modes & retries: Divergence between documentation and schema blocks CI; activations referencing undocumented keys are rejected.*\
*Observability: Validators emit `settings_definition_gap_total`; lint dashboards flag omissions.*

| Key | Scope | Default | Description / Enforcement |
| --- | ----- | ------- | ------------------------- |
| `regions.allowlist.compute` | ORG | [na-us-1, na-us-2] | Allowed compute regions; enforced by §3.8. |
| `regions.allowlist.storage` | ORG | [na-us-1, na-us-2] | Allowed storage regions; enforced by §3.8 and §5.3. |
| `network.egress.allowed_hosts[]` | SYSTEM\|ORG | [] | Host allowlist rendered to ServiceEntry/AuthorizationPolicy; §3.2.1. |
| `analyze.model.id` | ORG\|CASE | default profile | LLM model profile for Analyze lanes; see §8 and §6.3. |
| `analyze.token_ceiling` | ORG\|CASE | 100000 | Max tokens per Analyze job; see §8.3. |
| `analyze.max_retries` | ORG\|CASE | 2 | Retry budget per lane; see §6.3 QA loops. |
| `compose.model.id` | ORG\|CASE | default profile | LLM model profile for Compose; see §8 and §6.4. |
| `compose.token_ceiling` | ORG\|CASE | 100000 | Max tokens per Compose job; §8.3. |
| `compose.max_retries` | ORG\|CASE | 2 | Retry budget per lane; §6.4. |
| `compose.policy.forbidden_patterns[]` | ORG | [] | Content forbids; §6.4 QA. |
| `compose.templates.client.template_id` | ORG | default | DOCX/MD template selection; §6.4. |
| `compose.templates.lawyer.template_id` | ORG | default | DOCX/MD template selection; §6.4. |
| `reviews.timeout_hours` | ORG | 72 | Approval escalation threshold (reminders/escalations); §11.2.3. |
| `reviews.backlog.alert_minutes` | ORG | 30 | Minutes before `QUEUED_FOR_REVIEW` items trigger reviewer escalation banners/alerts; §7.1.3, §11.1. |
| `sign.trust_roots[]` | SYSTEM\|ORG | [] | Trust roots for signing; §7.2. |
| `sign.tsa.endpoint` | SYSTEM\|ORG | null | TSA API endpoint; §7.2. |
| `sign.tsa.max_time_drift_secs` | SYSTEM | 5 | NTP drift tolerance; §7.2, §3.2. |
| `security.tls.min_version` | SYSTEM | TLSv1.3 | Minimum TLS version for ingress; §3.2. |
| `security.tls.cipher_profile` | SYSTEM | default | TLS cipher profile for ingress; §3.2. |
| `security.tls.fips_mode` | SYSTEM | false | Enforce FIPS-approved cipher suites and modules; §3.2, §7.2. |
| `security.tls.legacy_exceptions[]` | SYSTEM | [] | Temporary TLS 1.2 exceptions (≤30 days, alert at T-7); §3.2, §9.2. |
| `db.pgbouncer.pool_mode` | SYSTEM | transaction | Allowed PgBouncer pooling mode (`transaction` default, `session` optional); §3.2.1. |
| `llm.providers[]` | SYSTEM\|ORG | [] | Provider catalog; §8.1. |
| `llm.models[]` | SYSTEM\|ORG | [] | Model catalog and fallback priorities; §8.1. |
| `llm.models.version_pin` | SYSTEM\|ORG | provider‑specific | Explicit provider model snapshot/version pin; §8.1/§8.5. |
| `llm.enforce_model_version` | ORG\|CASE | true | Fail when provider model version drifts from pin; §8.1/§8.5. |
| `llm.moderation.enabled` | ORG | true | Enable automated input/output moderation; §8.4. |
| `llm.moderation.provider` | ORG | azure\|openai\|local | Moderation provider selection; §8.4. |
| `llm.moderation.enforcement` | SYSTEM\|ORG | block | Enforcement mode: `block` (default) or `warn`; §8.4. |
| `llm.moderation.thresholds.toxicity` | ORG | 0.5 | Classification threshold; §8.4. |
| `llm.moderation.thresholds.self_harm` | ORG | 0.5 | Classification threshold; §8.4. |
| `llm.moderation.thresholds.sexual_content` | ORG | 0.5 | Classification threshold; §8.4. |
| `llm.moderation.thresholds.pii_reintroduction` | ORG | 0.5 | Classification threshold; §8.4. |
| `llm.byo.allowed` | ORG\|CASE | false | Permit bring-your-own model endpoints; §8.1.3. |
| `llm.byo.evaluation_suite_id` | ORG | default | Evaluation suite applied to BYO providers; §8.1.3. |
| `llm.byo.vpc_endpoints[]` | ORG | [] | Allowed BYO endpoint hostnames (reconciled with mesh policies); §8.1.3. |
| `agents.langgraph.runner` | SYSTEM\|ORG | langgraph | Graph runner selection (`langgraph` or `linear`); §6.7.2. |
| `agents.langgraph.fallback_mode` | SYSTEM | false | Force manual drafting fallback; §6.7.2, App.D RB-LLM-003. |
| `speech.providers[]` | SYSTEM\|ORG | [] | Speech provider catalog (health, residency, parity evidence); §6.2.1. |
| `speech.jobs[]` | SYSTEM\|ORG | [] | Transcription job profiles and fallback chains; §6.2.1. |
| `speech.allow_preprocessing` | ORG\|CASE | false | Permit loudness normalization/compression before transcription; §6.2.3. |
| `speech.require_locale_match` | ORG\|CASE | true | Fail fast when provider lacks requested locale; §6.2.3. |
| `speech.detect_language.enabled` | ORG\|CASE | false | Enable automatic source-language detection; §6.2.4. |
| `speech.multilingual_segments.enabled` | ORG\|CASE | false | Emit language-tagged segments for code-switched audio; §6.2.4. |
| `speech.translation.enabled` | ORG\|CASE | false | Allow generation of translated transcripts; §6.2.4. |
| `speech.translation.targets_default[]` | ORG | [] | Default target locales for translation requests; §6.2.4. |
| `speech.translation.provider` | ORG\|CASE | null | Translation provider identifier; §6.2.4. |
| `speech.translation.glossary_set` | ORG\|CASE | null | Reference Manager glossary bundle for translations; §6.2.4. |
| `speech.translation.max_parallel_targets` | ORG\|CASE | 3 | Parallel translation limit per job; §6.2.4. |
| `speech.translation.allow_unverified_pairs` | ORG\|CASE | false | Permit translation pairs not in the verified registry (waiver required); §6.2.3, §6.2.4. |
| `speech.translation.language_pair_overrides[]` | ORG\|CASE | [] | Disable or remap specific source→target pairs for contractual/compliance reasons; §6.2.3, §6.2.4. |
| `chat.staff.enabled` | ORG\|CASE | false | Enable staff Copilot assistant; §11.11. |
| `chat.staff.rate_limit.rpm` | ORG\|CASE | 30 | Staff assistant requests per minute; §11.11. |
| `chat.staff.token_cap_daily` | ORG\|CASE | 20000 | Staff assistant daily token budget; §11.11. |
| `chat.client.enabled` | ORG\|CASE | false | Enable portal chat assistant; §11.11. |
| `chat.client.rate_limit.rpm` | ORG\|CASE | 10 | Client assistant requests per minute; §11.11. |
| `chat.client.token_cap_daily` | ORG\|CASE | 10000 | Client assistant daily token budget; §11.11. |
| `chat.session.max_active_per_user` | ORG\|CASE | 2 | Concurrent chat sessions allowed per user; §11.11. |
| `chat.auto_disable_on_abuse` | ORG\|CASE | true | Auto-disable assistants on policy violations; §11.11. |
| `chat.provider.profile` | ORG\|CASE | null | LLM profile assignment for assistants; §8.1.4, §11.11. |
| `portal.chat.hipaa_allowed` | ORG | false | Permit client chat when HIPAA mode active; §11.11. |
| `portal.chat.export.enabled` | ORG\|CASE | false | Allow client chat transcript exports; §11.11. |
| `notifications.in_app.rate_limit_per_minute` | ORG | 60 | In-app notification dispatch rate; §11.9. |
| `notifications.in_app.daily_cap` | ORG | 500 | In-app notification max per day; §11.9. |
| `llm.finops.monthly_cap_usd` | ORG | 0 (disabled) | Monthly LLM spend cap; §8.3, §13.4. |
| `jobs.watchdog.no_progress_minutes` | SYSTEM\|ORG | 5 | Minutes without heartbeat before watchdog warns; §10.2, §12.1, Appendix R entry [RB-JOB-WATCHDOG](runbooks.md#rb-job-watchdog). |
| `jobs.watchdog.timeout_minutes` | SYSTEM\|ORG | 15 | Minutes without heartbeat before watchdog fails the job; §10.2, §12.1, Appendix R entry [RB-JOB-WATCHDOG](runbooks.md#rb-job-watchdog). |
| `uploads.scan.engine` | SYSTEM | clamav | Malware engine used in the upload scan pipeline; §6.2, §12.1. |
| `uploads.scan.yara_ruleset_version` | SYSTEM | latest | Version tag for YARA rules synced from Security; §6.2. |
| `uploads.scan.timeout_seconds` | SYSTEM\|ORG | 120 | Max scan duration before treating file as suspicious and quarantining; §6.2, Appendix R entry [RB-UPLOAD-SCAN](runbooks.md#rb-upload-scan). |
| `uploads.scan.override_hashes[]` | SYSTEM\|ORG | [] | Temporary allowlist for known-clean artifacts while rules are tuned (dual approval, time-boxed); Appendix R entry [RB-UPLOAD-SCAN](runbooks.md#rb-upload-scan). |
| `uploads.enabled` | SYSTEM\|ORG | true | Toggle to accept new uploads; disabled during major scanner outages; Appendix R entry [RB-UPLOAD-SCAN](runbooks.md#rb-upload-scan). |
| `api.idempotency.ttl_hours` | SYSTEM | 24 | TTL for idempotency; §10.3. |
| `api.rate_limits.web.rpm_per_org` | SYSTEM\|ORG | 600 (guardrail 10-2000; activation validator enforces range) | Org RPM; §10.5. |
| `api.rate_limits.web.rpm_per_ip` | SYSTEM\|ORG | 300 (guardrail 10-2000) | IP RPM; §10.5. |
| `portal.download.rate_limits.user_rpm` | ORG | 60 (guardrail 10-2000) | Portal download/user; §10.5. |
| `portal.download.rate_limits.org_rpm` | ORG | 200 (guardrail 10-2000) | Portal download/org; §10.5. |
| `security.org_switch.step_up_required` | SYSTEM | true | Enforce step-up on privilege increase; §4.3. |
| `security.disclosure.contact` | SYSTEM | null | Security.txt contact; §14.9. |
| `security.disclosure.encryption_key_url` | SYSTEM | null | PGP key URL; §14.9. |
| `security.pentest.cadence` | SYSTEM | annual | Pentest schedule; §14.9. |
| `security.mfa.webauthn_required_roles` | ORG | [] | Roles requiring WebAuthn step-up (HIPAA mode); §2.2, §4.3. |
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
| `privacy.hipaa.phi_detection.strict_mode` | ORG\|CASE | true | Enforce layered PHI detection (waiver required to relax); §2.2. |
| `privacy.hipaa.phi_detection.rescan_hours` | ORG | 24 | Interval for scheduled PHI re-scan jobs; §2.2. |
| `i18n.supported_locales[]` | ORG | [] | Supported locales (BCP-47 codes) surfaced in UI toggles; must include at least one locale; §11.3. |
| `identity.org.primary_idp` | ORG | keycloak | Primary IdP assignment (`keycloak` or `external:<id>`); §4.1. |
| `storage.bucket_versioning_required` | SYSTEM | true | Bucket versioning must be enabled; §5.3, §12.1. |
| `storage.remote_hash.enabled` | ORG\|CASE | false | Record remote hashes for batch inputs; §5.3. |
| `storage.remote_hash.max_mb` | ORG\|CASE | 50 | Max remote bytes to hash; §5.3. |
| `settings.activation.require_dual_approval` | SYSTEM | true | Dual approval for unsafe changes; §9.3. |
| `logging.redaction.enabled` | SYSTEM | true | Redact PII in logs; §12.1. |
| `logging.access.roles[]` | SYSTEM | [] | Role mapping for log query privileges (`observability.reader\|engineer\|auditor`); §12.1.2. |
| `logging.cost.daily_budget_mb_per_service` | SYSTEM\|ORG | 500 | Daily log volume budget per service; §12.1.6. |
| `logging.cost.alert_threshold_pct` | SYSTEM\|ORG | 80 | Alert threshold as % of daily log budget; §12.1.6. |
| `logging.level.default` | SYSTEM | "INFO" | Default production log level; §12.1.6. |
| `logging.level.overrides[]` | ORG | [] | Per-service log level overrides; §12.1.6. |
| `portal.logging.enabled` | ORG | true | Enable client telemetry capture; §12.1.5. |
| `evidence_store.redacted_excerpts.enabled` | ORG | true | Allow storage of prompt/response excerpts; HIPAA enable guard forces false and triggers purge; §2.2, §8.2. |
| `logging.immutable_sink.enabled` | SYSTEM | true (prod) | Mirror structured logs to immutable storage alongside the audit sink; validators block `false` in production and mark overrides unsafe (§9.11, §12.1). |
| `llm.finops.guard.threshold_pct` | SYSTEM\|ORG | 10 | MoM regression ceiling for deploy gate; §8.7, §13.5. |
| `llm.finops.guard.trailing7d_pct` | SYSTEM\|ORG | 25 | Trailing 7-day burn ceiling (% of monthly cap) for deploy gate; §8.7, §13.5. |
| `llm.finops.override_until` | SYSTEM | null | Optional timestamp (max +72h) to temporarily relax FinOps guard (dual approval required); §8.7. |

### A.2 Traceability map (normative)

**Breadcrumbs:** Implementation `apps/platform/settings/services/enforcement.py::list_touchpoints`, Tests `tests/platform/settings/test_enforcement_points.py::test_required_fetch`, Observability Grafana "Settings Enforcement" dashboard (metric `settings_enforcement_lookup_total`).\
*Purpose: Show which platform surfaces depend on each key family so audits can confirm coverage.*\
*Contract: Every consumer references the relevant bundle IDs listed here; additions require updating this map and associated tests.*\
*State: Enforcement registry stored in `settings_enforcement_point` with bundle-to-service mappings.*\
*Failure modes & retries: Missing mappings trigger lint failures and synthetic alert `settings_enforcement_lookup_total{status="missing"}`.*\
*Observability: Adoption dashboards display bundle coverage per service.*

- Agents → `analyze.*`, `compose.*`, `llm.*` (TDD §6, §8).
- Guardian → `guardian.*` (judgment policies; see Services · Guardian).
- Signer → `sign.*` (digital signature policies; TDD §7).
- Storage & integrity → `storage.*`, `logging.*` (TDD §5, §12).
- Portal & client UX → `portal.*`, `i18n.*`, `chat.*`, `security.*` (TDD §11).
- APIs & rate limits → `api.*`, `uploads.*`, `notifications.*` (TDD §10, §11.9).
- Operations & governance → `udlock.*`, `privacy.*`, `security.pentest.*`, `logging.*` (Appendix R procedures, TDD §12, §14).

### A.3 Linting & parity gates (binding)

**Breadcrumbs:** Implementation `scripts/docs/check_settings_keys.py`, Tests `tests/docs/test_lint_rules.py::test_settings_key_lint`, Observability CI job "docs-lint" (metric `docs_template_missing_total`).\
*Purpose: Ensure Settings documentation, schemas, and runtime references remain in lockstep.*\
*Contract: CI must fail when settings keys referenced in code lack appendix coverage, or when appendix keys lack schema/tests.*\
*State: Lint scripts load this appendix, inspect OpenAPI/spec/config usage, and compare against registry definitions.*\
*Failure modes & retries: Any mismatch fails `settings:lint-keys`; update definitions, tests, and this appendix atomically.*\
*Observability: CI dashboards track lint duration and failure rate.*

- Regions & residency → `regions.allowlist.*`, `privacy.*`; validated by residency scanners and RM catalog ingest.
- APIs & rate limits → `api.*`, `portal.download.*`; OpenAPI spectral rules enforce header/limit parity.
- FinOps → `llm.finops.*`; drift detection jobs surface monthly spend anomalies.
- Security & compliance → `security.*`, `logging.redaction.*`, `compliance.*`; test suites enforce RLS/masking.
- Ops & locks → `udlock.*`; advisory lock registry and Appendix R entries confirm enforcement.

### A.4 Activation checklist (binding)

**Breadcrumbs:** Implementation `apps/platform/settings/services/activation.py::activate_bundle`, Tests `tests/platform/settings/test_activation_flow.py::test_requires_checklist`, Observability Grafana "Settings Activation" dashboard (metric `settings_activation_total{result="blocked"}`).\
*Purpose: Provide the required evidence when promoting a settings bundle.*\
*Contract: Every activation records justification, reviewers, validator outputs, and rollout timeline before promotion.*\
*State: Activation metadata stored in `settings_activation`, approvals in `settings_activation_approval`, waivers in `settings_waiver` with App.O decision log links.*\
*Failure modes & retries: Missing checklist fields mark the activation `unsafe`; promotion halted until evidence supplied.*\
*Observability: Governance dashboard highlights incomplete activations; alert `settings_governance_override_total` pages owners.*

Checklist items:

1. Link to change ticket, ADR (if applicable), and decision log entry.
2. Attach validator results (`unsafe_reasons[]`, residency, safety, cost) and diff preview hashes.
3. Confirm dual approval requirements (Security + Architecture) met for protected scopes.
4. Record rollout plan, blast radius, and rollback window; attach staging dry-run evidence.
5. Store bundle, activation JSON, and diff artifacts under `ops/settings/<date>/`.

### A.5 Change log handoff (informative)

**Breadcrumbs:** Implementation `ops/settings/change_log.md`, Tests `tests/platform/settings/test_change_log.py::test_entry_schema`, Observability Docs bot "settings-change-log" (metric `settings_change_log_missing_total`).\
*Purpose: Keep a rolling history of key modifications discoverable for audits.*\
*Contract: Each production activation with customer impact must append an entry summarizing scope, bundle ID, approvals, and evidence pointers.*\
*State: Change log maintained alongside this document (`ops/settings/change_log.md`) and mirrored into App.O decision log.*\
*Failure modes & retries: Missing change log entry triggers release checklist failure; remediate by adding the entry with backdated evidence.*\
*Observability: Weekly docs lint verifies latest activations appear in the log.*


## Appendix B — Metrics & alerts

**Breadcrumbs:** Implementation `apps/platform/settings/telemetry.py::record_metrics`, Tests `tests/platform/settings/test_metrics.py::test_metric_contract`, Observability Grafana dashboards listed below (SLO, Governance, Compliance).\
*Purpose: Define the telemetry set that proves Settings Registry health, governance controls, and security posture.*\
*Contract: Metrics and alerts enumerated here must exist in production dashboards; owners keep thresholds aligned with SLOs and audit requirements.*\
*State: Metrics emitted via OpenTelemetry exporters from the Settings service and background jobs; alerts configured in Grafana OnCall.*\
*Failure modes & retries: Missing metrics or stale thresholds block release checklists; on-call reviews incidents weekly to confirm coverage.*\
*Observability: Dashboards — “Settings Registry – Availability”, “Settings Governance”, “Settings Compliance”, “Settings Integrations”.*

### B.1 Service health (binding)

| Metric / Alert | Description | Owner |
| -------------- | ----------- | ----- |
| `settings_request_total{result}` | Request volume by outcome (`success`, `error`, `unauthorized`, `denied`) | SRE |
| `settings_latency_seconds{route}` | Histogram + SLO burn tracking for read/write endpoints | SRE |
| `settings_cache_hit_ratio` | Redis/local cache hit percentage; alert when \< 0.9 | Platform Architecture |
| `settings_cache_invalidation_lag_seconds` | Duration from activation publish to cache flush across nodes | SRE |
| `settings_snapshot_issued_total{scope}` | Snapshots delivered to workers, portal, Guardian, LPE | Platform Architecture |
| `settings_snapshot_drift_total{detector}` | Drift findings comparing embedded snapshot hashes vs effective values | SRE |
| `settings_enforcement_lookup_total{status}` | Enforcement touchpoints (required/optional/missing) used by downstream services | Platform Architecture |

### B.2 Governance & security (binding)

| Metric / Alert | Description | Owner |
| -------------- | ----------- | ----- |
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

Alert hooks include `settings_availability_breach`, `settings_activation_delay`, `settings_governance_override_total`, `settings_auth_failure_spike`, and `settings_secret_access_anomaly`; each alert links to Appendix R procedures.


## Appendix C — Seed bundle inventory

| Bundle | Location | Purpose | Validation |
| ------ | -------- | ------- | ---------- |
| `bootstrap_defaults.json` | `config/` | System defaults for general operation | `ops/scripts/bootstrap_platform.py` + schema validators |
| `guardian_defaults.json` | `config/` | Guardian-specific knobs consumed via SR | Guardian integration tests |
| `analyze_defaults.json` | `config/` | Analyze agent pipeline defaults | Agent contract tests |
| `llm_assignments.json` | `config/` | LLM profile assignments | `tests/platform/settings/test_llm_profiles.py` |
| `llm_providers.json` | `config/` | Provider catalog entries | `tests/platform/settings/test_llm_profiles.py` |
| `agents.pipeline/*.json` | `config/agents.pipeline/` | LangGraph pipeline manifests and rollouts | `tests/platform/settings/test_pipeline_bundle.py` |




## Appendix R — Runbooks & drills

**Breadcrumbs:** Implementation runbooks under `ops/runbooks/settings/`, Tests `tests/platform/settings/test_rollback.py::test_replay_last_good` and peers listed per runbook, Observability Grafana OnCall incidents tagged `settings`.\
*Purpose: Centralize operational playbooks tied to Settings Registry alerts.*\
*Contract: Alerts enumerated in Appendix B must link to these runbooks; responders keep procedures current with quarterly tabletop reviews.*\
*State: Runbooks live alongside automation scripts in the ops repository; this appendix summarizes trigger conditions and critical steps.*\
*Failure modes & retries: Missing or stale runbooks trigger post-incident corrective actions and block deploy sign-off.*\
*Observability: OnCall analytics track time-to-ack/resolve for Settings incidents; drills recorded in App.O decision log.*

### R.1 Runbook index (informative)

**Breadcrumbs:** Implementation `ops/runbooks/settings/index.md`, Tests `tests/platform/settings/test_runbook_index.py::test_entries_present`, Observability Docs lint metric `docs_runbook_missing_total`.\
*Purpose: Provide a quick map from alert codes to runbook IDs.*\
*Contract: Every Settings alert references one of these IDs; new alerts require index updates.*\
*State: Index maintained in version control and mirrored here.*\
*Failure modes & retries: Lint script fails when index missing an alert; add entry before merging.*\
*Observability: Weekly docs lint verifies the index matches OnCall configuration.*

- RB-GOV-008 — Settings governance toggle / rollback
- RB-RES-ENDPOINT — Residency endpoint drift remediation
- RB-RES-BLOCK — Residency waiver / block handling
- RB-LOCK-006 — Activation lock stale detection & remediation
- RB-LLM-003 — Provider degradation / circuit breaker
- RB-JOB-WATCHDOG — Job stall watchdog
- RB-UPLOAD-SCAN — Upload scanning outage response

### R.2 RB-GOV-008 — Settings governance toggle / rollback (binding)

**Breadcrumbs:** Implementation `ops/runbooks/settings/governance_toggle.md`, Tests `tests/platform/settings/test_rollback.py::test_replay_last_good`, Observability Grafana “Settings Governance” dashboard (alert `settings_governance_override_total`).\
*Purpose: Safely activate or revert high-sensitivity governance toggles (waivers, residency overrides, cross-org pilots).*\
*Contract: Any activation flagged `unsafe` or touching governance scopes must follow this sequence before promotion.*\
*State: Runbook automation uses `ops/runbooks/settings_rollback.py`; evidence stored under `ops/settings/<date>/`.*\
*Failure modes & retries: Missing approvals or failed smoke tests require immediate rollback via `settings rollback --bundle <previous_id>`.*\
*Observability: Alert clears once activation completes with both approvals and validation metrics green.*

Triggers: `settings_governance_override_total`, change tickets tagged `GOV-TOGGLE`, or manual escalation from Security/Architecture.

Execution checklist:

1. Announce maintenance window with activation/rollback times in `#ops-announcements`.
2. Validate staging dry-run (matching bundle hash) and attach diff evidence to change ticket.
3. Execute activation via CLI/UI, capturing activation ID and `unsafe_reasons[]` result (expected empty).
4. Run targeted smoke tests (API read/write, portal toggle, worker snapshot) tied to the toggle.
5. Update change ticket and decision log with activation ID, evidence, and rollback window.

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
2. Inspect Istio AuthorizationPolicy revisions to ensure offending hosts remain blocked.
3. Identify impacted providers/orgs via activation diff linked in alert payload.

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
2. Validate provider endpoints and DNS; compare to RM catalogue snapshots.
3. If cross-region access required, capture dual approval, set `cross_region_waiver=true`, and document expiry.
4. Re-run activation or job; confirm Guardian manifests reference waiver ID.
5. Audit waiver usage daily until expiry or remediation.

### R.5 RB-LOCK-006 — Activation lock stale detection & remediation (binding)

**Breadcrumbs:** Implementation `ops/runbooks/settings/activation_lock.md`, Tests `tests/platform/settings/test_locks.py::test_lock_scope`, Observability Grafana “Settings Lock” panel (alert `settings_activation_lock_wait_seconds`).\
*Purpose: Detect and remediate stuck activation locks without risking concurrent edits.*\
*Contract: Lock holders must release within configured `udlock.max_session_hold_seconds`; stale locks trigger this runbook.*\
*State: Lock registry tracked in `settings_activation_lock`; helper scripts expose current holders.*\
*Failure modes & retries: Forcing unlock without verifying holder state risks split-brain activations; follow decision tree below.*\
*Observability: Alert clears when lock age returns under threshold and registry shows no stale entries.*

Checklist:

1. Inspect lock registry via `scripts/settings/show_activation_locks.py` filtered by environment.
2. Verify holder liveness (`SELECT ... FROM pg_stat_activity`) to differentiate idle vs active transactions.
3. If holder dead or idle-in-transaction, coordinate worker/web restart or issue `SELECT pg_terminate_backend(...)` per policy.
4. After release, rerun activation pipeline smoke tests; capture evidence in incident log.
5. File follow-up if lock reappears within 24h (root cause investigation, automation fix).

### R.6 RB-LLM-003 — Provider degradation / circuit breaker (binding)

**Breadcrumbs:** Implementation `ops/runbooks/settings/provider_circuit_breaker.md`, Tests `tests/platform/settings/test_llm_circuit.py::test_half_open_probe`, Observability Grafana “FinOps – LLM Cost & Circuit” dashboard (alert `alert_llm_circuit_open`).\
*Purpose: Handle degraded LLM providers to protect cost and SLA budgets.*\
*Contract: OPEN circuits remain until provider health verifies; half-open probes follow cadence defined here.*\
*State: Circuit state stored in `settings_llm_circuit`; fallback chains defined in Settings bundles.*\
*Failure modes & retries: Prematurely closing circuits or leaving fallback unmonitored risks runaway spend and job failures.*\
*Observability: Alert resolves when circuit state returns to CLOSED for affected models and cost deltas stabilize.*

Response steps:

1. Confirm affected models via dashboard filters (`llm_circuit_state{model}`) and review recent error/latency metrics.
2. Validate fallback outcomes in logs (`PRIMARY_DEGRADED`, `FALLBACK_USED`) and ensure FinOps guardrails intact.
3. Keep circuits OPEN until three consecutive successful half-open probes; adjust fallback priorities if secondary models degrade.
4. Notify vendor/support with incident details when degradation persists >15 minutes; record ticket IDs in incident log.
5. After recovery, document budget impact and corrective actions; update preventive tasks (synthetic prompts, timeout tuning).

### R.7 RB-JOB-WATCHDOG — Job stall watchdog (binding)

**Breadcrumbs:** Implementation `ops/runbooks/platform/job_watchdog.md`, Tests `tests/platform/watchdog/test_job_timeout.py::test_timeout_escalation`, Observability Grafana “Watchdog Runner” dashboard (alerts `job_watchdog_warning_total`, `job_watchdog_timeout_total`).\
*Purpose: Restore stuck jobs and protect downstream SLAs when heartbeats lapse.*\
*Contract: Watchdog alerts trigger within `jobs.watchdog.no_progress_minutes` / `jobs.watchdog.timeout_minutes`; responders must either resume progress or terminate safely.*\
*State: Heartbeats stored in `job_progress_heartbeat`; remediation evidence captured in incident ticket (`ops/watchdog/<date>/`).*\
*Failure modes & retries: Premature termination can lose customer work; skipping checkpoint verification risks replaying corrupted artifacts.*\
*Observability: Alert clears after watchdog completes remediation and fresh heartbeats resume for affected jobs.*

Triage & remediation:

1. Identify affected job IDs from alert payload; confirm `job_progress_heartbeat` age and last known task lane.
2. Inspect worker logs for stalled tasks, resource exhaustion, or upstream dependency failures; capture excerpts in incident notes.
3. If work-in-progress artifacts exist, trigger checkpoint validation (`ops/jobs/verify_checkpoint.py`) before retrying.
4. Attempt safe resume via `jobs resume --job <id>` when the worker is healthy; otherwise cancel and requeue after addressing root cause.
5. Close alert once heartbeats refresh (< 2 × `jobs.watchdog.heartbeat_interval`) and audit trail updated with remediation steps.

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
2. Freeze new intake by toggling `uploads.enabled=false` in Settings; announce customer impact and expected review window.
3. Validate scanner health: check ClamAV/YARA signature freshness, sandbox resource utilization, and recent deployment changes.
4. For malware detections, coordinate with Security to analyze samples; maintain quarantine until signatures updated and retest passes.
5. Once scanners stable, re-enable uploads, replay quarantined items through the pipeline, and attach evidence (dashboards, signature reports) to the incident record.

Follow-up:

- File change tasks for signature automation gaps or scaling adjustments discovered during the incident.
- Update customer/regulator communications templates with incident summary and remediation timeline.
