---
title: "uDocket — TDD Appendix: API Error Codes Index"
subtitle: "Consolidated service and app error-code contracts"
authors:
  - "Platform Documentation Team"
version: "0.1-draft"
status: implementable
classification: Confidential
last_updated: "2025-10-30"
updated_by: "Documentation Team"
owners:
  - "Platform Documentation Team"
reviewers:
  - "Platform Architecture"
approvers:
  - "Architecture Steering Committee"
approved_by:
approved_date:
---

______________________________________________________________________

## Document Controls

| Field | Value |
| --- | --- |
| Authors | Platform Documentation Team |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-30 |
| Updated by | Documentation Team |
| Owners | Platform Documentation Team |
| Reviewers | Platform Architecture |
| Approvers | Architecture Steering Committee |
| Approved by |  |
| Approved date |  |

______________________________________________________________________

## Appendix Overview

This appendix aggregates the API error code sections from every service and app specification. Refresh it with `python scripts/docs/build_api_error_index.py` whenever those sections change.

<!-- BEGIN AUTO-GENERATED API ERROR INDEX -->
<!-- AUTO-GENERATED: Run `python scripts/docs/build_api_error_index.py` to refresh. -->

### [Audit & Evidence](../../../services/audit.md)

**Purpose:** Document Audit & Evidence `ApiError.code` emissions so downstream services and auditors can apply the correct remediation flow. **|**
**Contract:** Audit APIs reuse the platform catalog in [`Platform Runtime §3.3`](../../../services/platform-runtime.md#33-api-error-codes) and surface the codes below for domain-specific failures. **|**
**State:** Codes originate from `apps/platform/audit/api.py` and ledger services, with matching audit events appended to `ops/audit/ops_audit.jsonl`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and contract tests; runtime emissions trigger `audit_api_error_total{code}` alerts. **|**
**Observability:** Metrics `audit_api_error_total{code}` and dashboards “Audit Seal Integrity” / “Compliance Evidence” monitor error rates; synthetic DSAR drills confirm semantics. **|**
**Breadcrumbs:** API handlers `apps/platform/audit/api.py`, waiver service `apps/platform/compliance/waiver.py`, DSAR runner `ops/privacy/dsar_runner.py`, tests `tests/platform/audit/test_api_errors.py`. **|**
**References:** Platform Runtime §3.3, Guardian spec §2.3, Settings spec §7.3.

| Code | Scenario | Client guidance |
|---|---|---|
| `POLICY_BLOCK` | Legal hold, residency, or waiver guard prevents evidence release or deletion. | Surface Guardian/waiver reason, engage RB-AUDIT-004 or RB-WAIVER-GOV before retrying. |
| `QUARANTINED` | Evidence quarantined pending Guardian/manual review. | Escalate to Guardian reviewers; do not retry until quarantine cleared. |
| `INTEGRITY_ERROR` | Seal manifest hash mismatch or immutable sink divergence detected. | Rebuild manifests via `ops/audit/rebuild_manifest.py`, regenerate seal, retry once integrity restored. |
| `VALIDATION_ERROR` | Waiver/DSAR payload fails schema or policy validation. | Inspect `details[]`, correct input, resubmit. |
| `NOT_FOUND` | Evidence bundle absent or redacted per retention policy. | Treat as terminal; refresh catalog or request prior version rather than retrying blindly. |

______________________________________________________________________

### [Digital Signer](../../../services/digital-signer.md)

**Purpose:** Enumerate signer-specific `ApiError.code` values so service consumers and monitoring can distinguish signing failures from upstream transport issues. **|**
**Contract:** Digital Signer emits the platform baseline codes (`POLICY_BLOCK`, `PROVIDER_DEGRADED`, etc.) plus the scenarios below when signature policy, manifest integrity, or replay rules fail. **|**
**State:** Codes originate from `apps/platform/signer/api.py`, worker pipeline guards, and replay tooling; audit events append to `ops/signer/signature_ops.jsonl`. **|**
**Failures & handling:** Unknown codes fail contract tests and block deploys; Alertmanager routes `signer_api_error_total{code}` spikes to RB-SIGN-INCIDENT. **|**
**Observability:** Dashboards “Signer & TSA”, metrics `signer_api_error_total{code}`, `signer_signature_policy_violation_total`, and synthetic signing drills capture error distribution. **|**
**Breadcrumbs:** API handlers `apps/platform/signer/api.py`, manifest validator `packages/udocket_core/signer/manifest.py`, replay utilities `ops/scripts/signer/replay_signature.py`, tests `tests/platform/operations/test_signer_api.py`. **|**
**References:** Platform Runtime §3.3, Settings spec §3.4, Guardian spec §2.2.

| Code | Scenario | Client guidance |
|---|---|---|
| `SIGNATURE_MANIFEST_INVALID` | Manifest hash mismatch, missing TSA evidence, or unsupported format detected before release. | Investigate manifest diff, regenerate evidence via `ops/signer/validate_manifests.py`, retry submission. |
| `SIGNING_PIPELINE_BLOCKED` | Signing queue halted due to FIPS waiver expiry, trust-root drift, or Guardian quarantine. | Follow RB-SIGN-INCIDENT / RB-SIGN-TSA, refresh waivers or trust roots, resubmit once pipeline resumes. |
| `SIGNATURE_POLICY_MISMATCH` | Requested policy does not match Settings (`sign.signature_policies[]`) or deliverable class. | Align request payload with active policy or update Settings; avoid blind retries. |
| `SIGN_IDEMPOTENCY_CONFLICT` | Replayed signing request with differing payload or digest. | Generate new `Idempotency-Key`, ensure canonical payload remains unchanged, retry once. |
| `SIGNATURE_REPLAY_MISMATCH` | Replay verification detected output drift versus stored manifest. | Quarantine artifact, run replay validation (`ops/scripts/signer/replay_signature.py`), remediate before reissuing. |

______________________________________________________________________

### [Guardian Service](../../../services/guardian.md)

**Purpose:** Enumerate Guardian-specific `ApiError.code` values so downstream services, UI surfaces, and monitoring dashboards can distinguish policy rejections from transient infrastructure issues. **|**
**Contract:** Guardian inherits the platform catalog in [`Platform Runtime §3.3`](../../../services/platform-runtime.md#33-api-error-codes) and layers detector/policy-specific codes listed below. **|**
**State:** Codes originate from submission validation (`apps/platform/guardian/views.py`), pipeline stages (`packages/udocket_core/guardian/pipeline.py`), and review endpoints. **|**
**Failures & handling:** Unknown codes fail contract tests (`tests/platform/guardian/test_api_errors.py`) and trigger `guardian_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Metrics `guardian_api_error_total{code}`, SSE topics `guardian.judgment.failed`, and dashboards “Guardian Decisions”/“Policy Drift” highlight error rates; synthetic submissions replay canonical failures every deploy. **|**
**Breadcrumbs:** Pipeline `packages/udocket_core/guardian/pipeline.py`, detector integrations `packages/udocket_core/guardian/detectors/*`, review API `apps/platform/guardian/views.py`, tests `tests/platform/guardian/test_pipeline.py`, `tests/platform/guardian/test_review_actions.py`. **|**
**References:** Platform Runtime §3.3, Settings spec §2.6, Notifications spec §3.2.

| Code | Scenario | Client guidance |
|---|---|---|
| `SCHEMA_POLICY_BLOCK` | Request payload failed schema validation or missing required policy context. | Fix payload, rerun submission; repeated failures escalate to RB-GUARD-QUEUE. |
| `RESIDENCY_POLICY_BLOCK` | Residency or waiver policy prohibits processing (e.g., provider drift, missing attestation). | Coordinate with Settings/Reference Manager waivers, update residency catalog, retry once cleared. |
| `POLICY_FORBIDDEN_PATTERN` | Detectors matched forbidden content (PII/PHI pattern, legal hold, leakage). | Follow Guardian remediation guidance, redact or waive content before resubmission. |
| `CLASSIFIER_LOW_CONFIDENCE` | ML detectors produced low-confidence spans requiring manual review. | Surface to reviewers; expect `WARN`/manual decision instead of auto retry. |
| `PARENT_NOT_APPROVED` | Upstream artifact reverted or lacks PASS while dependant artifact submitted. | Approve/restore parent artifact, resubmit child once lineage consistent. |
| `GUARDIAN_SUBMISSION_TIMEOUT` | Queue processing exceeded timeout or detector unavailable. | Workers auto-retry; clients may poll status; escalate if repeated (`guardian_submission_timeout_total`). |
| `QUARANTINED` | Guardian quarantined artifact due to detector or policy breach. | Resolve root cause, obtain manual clearance via `POST /guardian/quarantine`, then rerun pipeline. |

### [Identity & Access](../../../services/identity.md)

**Purpose:** Record the `ApiError.code` values emitted by identity and session APIs so clients respond safely to authentication and governance failures. **|**
**Contract:** Identity surfaces the platform catalog in [`Platform Runtime §3.3`](../../../services/platform-runtime.md#33-api-error-codes); the table below maps those codes to identity-specific flows. **|**
**State:** Errors arise from token issuance (`/api/v1/auth/token`), break-glass workflows, device binding checks, and portal/staff session APIs; schemas align with `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and `tests/platform/auth/test_api_errors.py`; runtime emissions trigger `identity_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards “Identity – API Errors” and “Session Integrity” chart `identity_api_error_total{code}`, `identity_device_fp_mismatch_total`; synthetic token flows validate MFA/clock skew guardrails. **|**
**Breadcrumbs:** Controllers `apps/platform/auth/views.py`, session manager `apps/platform/session/binding.py`, break-glass services `apps/platform/auth/break_glass.py`, tests `tests/platform/auth/test_token_api.py`, `tests/platform/auth/test_break_glass.py`. **|**
**References:** Platform Runtime §3.3, Settings spec §3.4, Guardian spec §2.2, Ops runbooks `RB-IDP-FAILOVER`, `RB-BREAK-GLASS`.

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `AUTH_ERROR` | Invalid credentials, disabled account, or revoked session token. | Prompt user to re-authenticate, enforce MFA if required, and avoid retry loops with stale tokens. |
| `AUTH_CLOCK_SKEW` | Signed requests outside the ±120 second tolerance. | Sync client clocks with NTP/Chrony, retry once skew corrected. |
| `AUTH_SIGNATURE_INVALID` | HMAC signature mismatch for privileged service calls. | Regenerate canonical string, rotate keys if necessary, and retry with corrected signature. |
| `POLICY_BLOCK` | Break-glass or residency policy forbids requested action (e.g., missing retrospective). | Surface remediation steps, complete break-glass workflow or obtain waiver before retrying. |
| `RATE_LIMIT` | Org/actor exceeded login, password reset, or session creation quotas. | Honor `Retry-After`, enforce backoff in UI, and notify operators for sustained spikes. |

### [LangGraph Agent Orchestration](../../../services/langgraph-agents.md)

**Purpose:** Enumerate LangGraph agent `ApiError.code` values so service clients, worker orchestration, and UI flows respond deterministically. **|**
**Contract:** Agent launch and management endpoints reuse the platform catalog in [`Platform Runtime §3.3`](../../../services/platform-runtime.md#33-api-error-codes); the scenarios below capture how those codes manifest for LangGraph pipelines. **|**
**State:** Responses originate from `apps/platform/agents/views.py`, pipeline runtime `packages/udocket_core/agents/runtime.py`, and Guardian adapters; schema parity enforced by `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and `tests/platform/agents/test_agent_errors.py`; runtime emissions trigger `agent_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards “Agents – Launch API” and “Agents – Guardian Blocks” chart `agent_api_error_total{code}`, `agent_guardian_block_total`; synthetic launches follow the pause/resume flows. **|**
**Breadcrumbs:** Controllers `apps/platform/agents/views.py`, runtime orchestrator `packages/udocket_core/agents/runtime.py`, Guardian bridge `packages/udocket_core/agents/guardian.py`, tests `tests/platform/agents/test_launch_api.py`. **|**
**References:** Platform Runtime §3.3, Settings spec §5.4, Worker Cluster spec §3.4, Guardian spec §2.3, Ops runbooks `RB-AGENT-SHADOW`, `RB-JOB-WATCHDOG`.

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `POLICY_BLOCK` | Guardian/residency guard or waiver policy rejected a pipeline launch or artifact promotion. | Present Guardian reason codes, remediate policy inputs, or seek waiver approval before retrying. |
| `CONFLICT` | Idempotency key replay with different payload or stale manifest `version`. | Read the latest manifest, regenerate the payload, and retry with a fresh `Idempotency-Key`. |
| `PROVIDER_DEGRADED` | LLM provider or speech service unavailable; fallback chain exhausted. | Record degraded status, halt automatic retries, and resume once health probes report recovery. |
| `QUARANTINED` | Generated artifact or intermediate output quarantined pending Guardian review. | Route to reviewer workflow, capture remediation notes, and relaunch only after clearance. |
| `RATE_LIMIT` | Org/agent concurrency or FinOps budget limit exceeded. | Honour `Retry-After`, shed background runs, and reschedule once budget resets. |

### [LLM Registry & Runtime Governance](../../../services/llm-registry.md)

**Purpose:** Document the `ApiError.code` values emitted by the LLM Registry so calling services handle retries, fallbacks, and throttling consistently. **|**
**Contract:** Registry APIs reuse the platform catalog in [`Platform Runtime §3.3`](../../../services/platform-runtime.md#33-api-error-codes); the table below maps those codes to registry-specific scenarios. **|**
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

### [Localization & Policy Engine](../../../services/lp-engine.md)

**Purpose:** Enumerate LPE-specific `ApiError.code` values so downstream services and automation interpret failures consistently. **|**
**Contract:** LPE APIs reuse the platform catalog in [`Platform Runtime §3.3`](../../../services/platform-runtime.md#33-api-error-codes); the scenarios below describe how those codes manifest during policy compilation and evaluation. **|**
**State:** Error envelopes originate from `/api/v1/lpe/policy-contexts`, `/api/v1/lpe/compile`, and `/api/v1/lpe/evaluate`; schema parity maintained via `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and `tests/platform/policy/test_api_errors.py`; runtime emissions trigger `lpe_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards “LPE – Compilation” and “LPE – Policy Evaluation” track `lpe_api_error_total{code}`, `lpe_compiler_duration_seconds`; synthetic evaluations verify waivers/residency scenarios. **|**
**Breadcrumbs:** Controllers `apps/platform/policy/views.py`, compiler `packages/udocket_core/policy/compiler.py`, runtime `packages/udocket_core/policy/runtime.py`, tests `tests/platform/policy/test_compile_api.py`, `tests/platform/policy/test_evaluate_api.py`. **|**
**References:** Platform Runtime §3.3, Reference Manager spec §3.4, Settings spec §3.4, Guardian spec §2.2.

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `POLICY_BLOCK` | Evaluation detected residency, waiver, or privacy violations that must block the requested action. | Present `policy_block_code`/waiver metadata to operators, remediate configuration, or obtain waiver before retrying. |
| `VALIDATION_ERROR` | Policy bundle or context payload failed schema or semantic validation. | Inspect `details[]`, correct inputs (missing locales, duplicate rules), and resubmit compile/evaluate. |
| `CONFLICT` | Concurrent activation changed the same PolicyContext version/hash. | Refresh digests via conditional GET, merge changes, and retry with updated `If-Match`/`Idempotency-Key`. |
| `PROVIDER_DEGRADED` | Reference Manager or policy bundle fetch unavailable; fallback chain exhausted. | Pause rollouts, retry once dependencies healthy, and notify Ops of degraded state. |
| `RATE_LIMIT` | Org exceeded compilation/evaluation budget or concurrency ceiling. | Honor `Retry-After`, stagger batch compiles, and request higher limits through governance. |

### [Notifications Service](../../../services/notifications.md)

**Purpose:** Enumerate Notifications `ApiError.code` values so producers, webhooks, and portal clients handle throttling and policy blocks consistently. **|**
**Contract:** Notifications reuse the platform catalog in [`Platform Runtime §3.3`](../../../services/platform-runtime.md#33-api-error-codes); the scenarios below map those codes to messaging semantics. **|**
**State:** Error envelopes originate from outbox APIs, download token issuance, and webhook ingestion; schema parity enforced by `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and `tests/platform/notifications/test_api_errors.py`; runtime emissions trigger `notifications_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards “Notifications – API Errors” and “Notifications – Webhooks” monitor `notifications_api_error_total{code}`, `notify_rate_limit_total`; synthetic sends validate throttling and masking flows. **|**
**Breadcrumbs:** Controllers `apps/platform/notifications/views.py`, outbox workers `apps/platform/notifications/outbox.py`, webhook signer `apps/platform/notifications/webhooks.py`, tests `tests/platform/notifications/test_outbox_api.py`. **|**
**References:** Platform Runtime §3.3, Guardian spec §2.2, Settings spec §2.6, Ops runbooks `RB-NOTIFY-RATE`, `RB-NOTIFY-WEBHOOK`.

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `POLICY_BLOCK` | Guardian/masking rules blocked a message, attachment, or portal download token. | Show Guardian reason, remediate content or policy configuration, then retry once cleared. |
| `RATE_LIMIT` | Org/channel exceeded outbound messaging or webhook throughput limits. | Honor `Retry-After`, queue retries with exponential backoff, and coordinate for sustained spikes. |
| `CONFLICT` | Outbox entry replayed with different payload or stale `version`. | Re-fetch outbox status, regenerate payload/`Idempotency-Key`, and retry once. |
| `PROVIDER_DEGRADED` | Email/SMS provider or webhook endpoint marked degraded (`OPEN` circuit). | Pause sends for affected provider, alert operators, and resume once health recovers. |
| `VALIDATION_ERROR` | Template context, attachment metadata, or download request failed schema checks. | Correct payload/template data and resubmit after validation passes. |

______________________________________________________________________

### [Observability](../../../services/observability.md)

**Purpose:** Enumerate Observability `ApiError.code` values so teams updating alert rules, dashboards, or telemetry exports react consistently when operations fail. **|**
**Contract:** Observability APIs reuse the platform catalog in [`Platform Runtime §3.3`](../../../services/platform-runtime.md#33-api-error-codes); the table below maps those codes to observability-specific workflows. **|**
**State:** Errors stem from alert CRUD APIs, dashboard export tooling, and telemetry ingestion guardrails; schema parity enforced via `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and `tests/observability/test_api_errors.py`; runtime emissions raise `observability_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards “Observability – API Errors” and “Ingestion Health” track `observability_api_error_total{code}`, `telemetry_ingest_rate_limit_total`; synthetic alert CRUD flows run per deploy. **|**
**Breadcrumbs:** Controllers `apps/platform/observability/views.py`, alert orchestrator `apps/platform/observability/alerts.py`, ingest guard `apps/platform/observability/ingest_guard.py`, tests `tests/observability/test_alert_api.py`. **|**
**References:** Platform Runtime §3.3, Settings spec §2, Ops runbooks `RB-OBS-ALERTS`, `RB-OBS-INGEST`.

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Alert/dashboard update failed optimistic concurrency (`expected_version` mismatch). | Re-fetch configuration, merge edits, and retry with the latest `expected_version`. |
| `POLICY_BLOCK` | Compliance policy forbade enabling an alert (missing escalation/runbook mapping). | Supply required metadata or approvals, then retry once policy passes. |
| `RATE_LIMIT` | Telemetry ingestion or dashboard export exceeded assigned quota. | Respect `Retry-After`, throttle exporters, and coordinate capacity adjustments. |
| `PROVIDER_DEGRADED` | Downstream telemetry pipeline (Prometheus, Loki, Tempo) degraded/unavailable. | Buffer locally where possible, alert SRE, and retry after health recovers. |
| `VALIDATION_ERROR` | Alert/dash payload failed schema validation or referenced unknown metrics. | Correct payload (metrics, labels), rerun validation, and resubmit. |

______________________________________________________________________

### [Platform Runtime](../../../services/platform-runtime.md)

**Purpose:** Keep API consumers, SDKs, and monitoring dashboards aligned on the standardized `ApiError.code` values. **|**
**Contract:** All REST and GraphQL surfaces emit one of the enumerated codes below; additions require schema (`spec/schemas/api_error.schema.json`) and Spectral rule (`ops/openapi/rules/apierror-enum.yaml`) updates before deployment. **|**
**State:** Platform Runtime owns the canonical code catalog; generated clients consume the same enumeration and raise on unknown values. **|**
**Failures & handling:** Emitting an unknown code fails Spectral lint, triggers `api_error_unknown_total`, and blocks rollout until the catalog updates. **|**
**Observability:** Metrics `api_error_total{code}`, synthetic probes, and alert rules `api_error_unknown_total`/`api_error_rate_spike_total` track drifts. **|**
**Breadcrumbs:** Schema `spec/schemas/api_error.schema.json`, middleware `apps/platform/api/errors.py`, tests `tests/platform/api/test_api_error_schema.py`, dashboards “API Gateway – Errors”. **|**
**References:** Settings spec §3.4, Guardian spec §2.2, Notifications spec §3.3, Ops runbooks `RB-API-GATEWAY-ERROR`.

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `POLICY_BLOCK` | Guardian, residency, or settings policy prevented the action. | Surface `details.reason`, remediate policy or obtain an approved waiver before retrying. |
| `QUARANTINED` | Artifact quarantined for manual review or remediation. | Hold follow-on actions until Guardian releases the artifact; do not retry automatically. |
| `INTEGRITY_ERROR` | Hash or ETag validation failed for the submitted content. | Recompute digests, re-upload content, and avoid blind retries without correcting the payload. |
| `VALIDATION_ERROR` | Request payload failed schema or semantic validation. | Inspect `details[]`, correct the offending fields, and resubmit the request. |
| `AUTH_ERROR` | Caller failed authentication or presented an expired token. | Re-authenticate, ensure the correct audience, and retry with a fresh credential. |
| `AUTH_CLOCK_SKEW` | `X-Timestamp` fell outside the permitted ±120 second window. | Synchronize system clocks (NTP/Chrony) and retry with an accurate timestamp. |
| `AUTH_SIGNATURE_INVALID` | HMAC signature mismatch or revoked key identifier. | Regenerate the canonical string, rotate keys if necessary, and retry with a valid signature. |
| `NOT_FOUND` | Resource missing, masked by RLS, or already archived. | Treat as terminal; refresh indices or scope before retrying with a new identifier. |
| `CONFLICT` | Optimistic concurrency or idempotency conflict detected. | Fetch the latest state, update the payload or `Idempotency-Key`, and retry once. |
| `RATE_LIMIT` | Rate, quota, or budget exceeded for the caller. | Honor `Retry-After`, apply exponential backoff, and present throttling feedback to operators. |
| `PROVIDER_DEGRADED` | Downstream dependency unavailable or circuit breaker open. | Implement retry with jitter respecting `Retry-After`; surface degraded status to operators. |

HTTP mapping examples (informative):

- `409 CONFLICT`: `code="CONFLICT"` (stale `version`, duplicate idempotency signature).
- `412 PRECONDITION_FAILED`: `code="INTEGRITY_ERROR"` (hash mismatch) or `code="POLICY_BLOCK"` (portal invalidation, Guardian override).
- `429 TOO_MANY_REQUESTS`: `code="RATE_LIMIT"` (RPM/token ceiling); include `Retry-After` header and `details.retry_after_ms` when known.
- `503 SERVICE_UNAVAILABLE`: `code="PROVIDER_DEGRADED"` (dependency outage, provider throttle).

Client retry guidance (normative):

| Error code | Typical cause | Client action |
|---|---|---|
| `CONFLICT` + stale `version` | Optimistic concurrency failure | Re-fetch state, apply latest `version`, retry mutation. |
| `CONFLICT` + idempotency mismatch | Replayed `Idempotency-Key` with new payload | Regenerate key; ensure body matches original request before retrying. |
| `RATE_LIMIT` | Per-org or per-user quota exceeded | Honor `Retry-After`, apply exponential backoff, surface warning to operators. |
| `POLICY_BLOCK` | Guardian or residency guard denied action | Present Guardian reasons, resolve policy violation, retry only after remediation. |
| `QUARANTINED` | Guardian quarantined artifact or deliverable | Require manual review/unquarantine before retry. |
| `INTEGRITY_ERROR` | Hash/ETag mismatch on upload/download | Recompute hash, re-upload source, avoid blind retries. |
| `AUTH_CLOCK_SKEW` | Request timestamp outside tolerance | Sync system clock; retry with corrected timestamp. |

All error responses include `X-Request-ID`; callers must log the value for support. Services echo the `Idempotency-Key` header when present to aid replay diagnostics.

<a id="33-tls-posture"></a>

### [Reference Manager](../../../services/ref-manager.md)

**Purpose:** Enumerate Reference Manager (`RM`) `ApiError.code` values so downstream automation and reviewers respond deterministically. **|**
**Contract:** RM APIs reuse the platform catalog in [`Platform Runtime §3.3`](../../../services/platform-runtime.md#33-api-error-codes); the scenarios below cover harvest, publish, and adoption flows. **|**
**State:** Error envelopes originate from `/api/v1/reference/bundles`, `/api/v1/reference/templates`, and adoption acknowledgment endpoints; schema parity enforced by `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and `tests/reference/test_api_errors.py`; runtime emissions trigger `reference_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards “Reference Manager – Publish” and “Reference Manager – Adoption” track `reference_api_error_total{code}`, `reference_manager_publish_guard_failure`; synthetic publishes exercise hotfix + rollback paths. **|**
**Breadcrumbs:** API handlers `apps/platform/reference_manager/views.py`, publisher `packages/udocket_core/reference_manager/publish.py`, adoption service `packages/udocket_core/reference_manager/adoption.py`, tests `tests/reference/test_publish_api.py`. **|**
**References:** Platform Runtime §3.3, Settings spec §3.3, LPE spec §3.5, Guardian spec §2.2.

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `POLICY_BLOCK` | License, residency, or waiver policy prevented bundle publish or acknowledgment. | Surface waiver/licensing metadata, resolve policy issues, and rerun publish/adoption after remediation. |
| `VALIDATION_ERROR` | Bundle/template payload failed schema, checksum, or coverage validation. | Inspect validation report, correct source data or manifests, and resubmit publish job. |
| `CONFLICT` | Publish request collided with an in-flight version (`bundle@version` already exists). | Refresh bundle catalog, increment semantic version, and retry once. |
| `PROVIDER_DEGRADED` | Source connector offline or Reference Manager put into protective pause. | Alert Content Ops/Legal Ops, retry after source recovers or manual upload completes. |
| `RATE_LIMIT` | Org or system-wide publish cadence exceeded governance limits. | Respect `Retry-After`, reschedule batch publishes, or escalate for temporary quota increase. |

### [Settings Registry](../../../services/settings.md)

**Purpose:** Enumerate Settings-specific `ApiError.code` values so platform consumers can build deterministic retry logic. **|**
**Contract:** Settings Registry reuses the platform catalog in [`Platform Runtime §3.3`](../../../services/platform-runtime.md#33-api-error-codes) and supplements it with the service-specific codes below. Mutating endpoints surface the same envelope schema and echo `Idempotency-Key` when supplied. **|**
**State:** Codes map directly to validation branches in `apps/platform/settings/api.py` and activation services. **|**
**Failures & handling:** Unknown codes fail Spectral lint and contract tests; runtime mis-emissions trigger `settings_error_unknown_total` alerts. **|**
**Observability:** Metrics `settings_error_total{code}` and `settings_auth_failure_total{reason}` feed the “Settings Registry – Availability” dashboard; synthetic activations assert error semantics before release. **|**
**Breadcrumbs:** API handlers `apps/platform/settings/api.py`, security helpers `apps/platform/settings/security.py`, tests `tests/platform/settings/test_auth.py`, `tests/platform/settings/test_activation_flow.py`, schema `spec/schemas/api_error.schema.json`. **|**
**References:** Platform Runtime §3.3, Guardian spec §2.2, Reference Manager spec §3.4, Ops runbooks `RB-SETTINGS-ACTIVATION`, `RB-HMAC-ROTATE`.

| Code | Scenario | Client guidance |
|---|---|---|
| `AUTH_SIGNATURE_INVALID` | HMAC signature mismatch on mutating requests (`X-Request-Signature` wrong or key revoked). | Recompute signature, rotate credentials via RB-HMAC-ROTATE if repeated. |
| `AUTH_CLOCK_SKEW` | `X-Timestamp` outside ±120 seconds tolerance. | Sync clocks, retry with corrected timestamp. |
| `SECRET_DISCLOSURE_BLOCKED` | Attempt to export masked secret fields through diff previews or read APIs. | Remove secret fields from request; fetch redacted values only. |
| `VALIDATION_ERROR` | Bundle schema violation, unsafe override, or diff failing semantic guard. | Inspect `details[]`, remediate configuration, rerun validation. |
| `CONFLICT` | Activation `expected_version` mismatch or replayed `Idempotency-Key`. | Re-fetch activation state, regenerate idempotency token, retry. |
| `POLICY_BLOCK` | Residency, waiver, or governance policy rejected the activation. | Obtain waiver/approval, update policy inputs, resubmit activation. |

Settings surfaces continue to emit `POLICY_BLOCK`, `QUARANTINED`, `INTEGRITY_ERROR`, and other shared codes as defined in the Platform Runtime catalog.

### [Web Application & Portal](../../../apps/web-app.md)

**Purpose:** Document the `ApiError.code` values that the web application surfaces so UX flows handle retries and blocking states consistently. **|**
**Contract:** Staff and portal clients reuse the platform catalog in [`Platform Runtime §3.3`](../../../services/platform-runtime.md#33-api-error-codes); the UI introduces the cases below for assistant and portal interactions. **|**
**State:** Codes originate from REST responses (`/api/v1/chat/*`, `/api/v1/portal/*`) and SSE events; enum definitions live alongside the platform schema (`spec/schemas/api_error.schema.json`) with UI adapters in `apps/platform/ui/errors.py`. **|**
**Failures & handling:** Unknown codes fail UI Spectral lint and unit tests; runtime emissions trigger `ui_api_error_unknown_total` alerts. **|**
**Observability:** Dashboards “Web App – API Errors” and “Portal Integrity” watch `ui_api_error_total{code}`; synthetic probes cover chat availability and portal download flows. **|**
**Breadcrumbs:** Controllers `apps/platform/api/chat.py`, portal download guard `apps/platform/portal/downloads.py`, UI error mappers `apps/platform/ui/errors.py`, tests `tests/platform/ui/test_error_adapters.py`, `tests/platform/portal/test_portal_errors.py`. **|**
**References:** Platform Runtime §3.3, Notifications spec §2.4 (download tokens), Settings spec §11.11 (assistant toggles), TDD §10.12.

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CHAT_DISABLED` | Org-level settings or Guardian policy disabled assistants for the active org/case. | Display the assistant-disabled banner, suppress retries, direct operators to review Settings or Guardian waivers. |
| `PORTAL_DOWNLOAD_PRECONDITION` | Portal download request failed the `If-Match` guard or token validation. | Prompt the client to refresh the deliverable list, regenerate the download link, and avoid automatic retry loops. |
| `POLICY_BLOCK` | Guardian or residency guard blocked an action invoked from the UI (approvals, compose publish, portal download). | Surface Guardian reason/details, require operator remediation before enabling another attempt. |
| `RATE_LIMIT` | Client exceeded the configured RPM/token limits for chat or portal download APIs. | Honor `Retry-After`, show throttling guidance, and backoff additional attempts. |

### [Worker Cluster](../../../services/worker-cluster.md)

**Purpose:** Enumerate worker-control `ApiError.code` values so API clients and automation react consistently. **|**
**Contract:** Worker Cluster reuses the platform catalog in [`Platform Runtime §3.3`](../../../services/platform-runtime.md#33-api-error-codes) and applies the scenarios below for job control, upload finalize, and pipeline orchestration requests. **|**
**State:** Error responses originate from `apps/platform/jobs/views.py`, upload finalize controller `apps/platform/files/views.py`, and worker orchestration services; enums align with `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and `tests/platform/jobs/test_error_envelope.py`; runtime emissions trigger `job_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards “Worker Cluster – API” and “Upload Finalize” watch `job_api_error_total{code}`, `upload_finalize_total{status}`; synthetic controls exercise pause/resume/cancel paths. **|**
**Breadcrumbs:** Controllers `apps/platform/jobs/views.py`, upload guard `apps/platform/files/views.py::finalize_upload`, idempotency helpers `packages/udocket_core/idem/store.py`, tests `tests/platform/jobs/test_job_controls.py`, `tests/platform/files/test_upload_finalize.py`. **|**
**References:** Platform Runtime §3.3, Settings keys `api.idempotency.*`, Ops runbooks `RB-JOB-WATCHDOG`, `RB-UPLOAD-SCAN`.

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Idempotency payload hash mismatch or stale `version` when retrying job controls. | Re-fetch job state, regenerate `Idempotency-Key`, and retry once with updated payload. |
| `POLICY_BLOCK` | Guardian/residency guard or budget hold prevented job execution. | Surface Guardian reason or budget hold, remediate policy (waiver, quota) before retrying. |
| `INTEGRITY_ERROR` | Upload finalize detected a hash mismatch against staged content. | Re-upload chunks with the correct digest and avoid blind retries until integrity matches. |
| `PROVIDER_DEGRADED` | Downstream provider/queue paused (`PAUSED_AWAITING_PROVIDER`, circuit open). | Respect backoff, surface degraded status to operators, and retry when health probes recover. |
| `RATE_LIMIT` | Org or job-kind concurrency ceiling exceeded. | Honor `Retry-After`, queue retries with exponential backoff, and reduce burst size. |

<a id="worker-api-idempotency"></a>
<!-- END AUTO-GENERATED API ERROR INDEX -->
