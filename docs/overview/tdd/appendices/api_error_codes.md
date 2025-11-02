---
title: "uDocket — TDD Appendix: API Error Codes"
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

This appendix aggregates the API error code sections from every service and app specification. Refresh it with `python -m doc_tools.build.api_error_codes` whenever those sections change.

<!-- BEGIN AUTO-GENERATED: api-error-index -->
<!-- AUTO-GENERATED: Run `python -m doc_tools.build.api_error_codes` to refresh. -->

### [Accounts & Tenants Service](../../../customer/accounts-tenants.md#3-3-webhooks-events-binding) {#accounts-tenants-service}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Tenant already exists or lifecycle state prevents the requested transition. | Refresh tenant state, resolve outstanding provisioning/offboarding steps, then retry. |
| `POLICY_BLOCK` | Residency, compliance hold, or approval policy forbids processing the request. | Coordinate with Compliance/Records to clear the hold or obtain approval, then retry once unblocked. |
| `VALIDATION_ERROR` | Tenant payload failed schema validation or residency selection rules. | Correct the request body (domains, residency, legal artefacts) and resubmit. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | Yes | accounts_api_error_total<br>tenant_event_conflict_total |
| `POLICY_BLOCK` | 403 | Yes | accounts_api_error_total<br>tenant_suspension_active_total |
| `VALIDATION_ERROR` | 400 | No | accounts_api_error_total<br>tenant_activation_latency_seconds |

### [Artifact Store Service](../../../data/artifact-store.md#3-3-api-error-codes-binding) {#artifact-store-service}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | ExclusiveSwap detected an in-flight or newer deliverable/promotion for the same lineage. | Refresh artifact state, resolve outstanding approvals, and retry promotion after reviewers clear the conflict. |
| `POLICY_BLOCK` | Guardian, residency, or retention policy forbids writing or deleting the artifact. | Review Guardian verdicts, residency waivers, or retention windows; obtain approval before resubmitting. |
| `VALIDATION_ERROR` | Artifact metadata failed schema validation (hash mismatch, unsupported type, or missing manifest fields). | Fix the payload or recompute hashes locally before retrying the upload/promotion request. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | Yes | artifact_api_error_total<br>artifact_promotion_conflict_total |
| `POLICY_BLOCK` | 403 | Yes | artifact_api_error_total<br>artifact_retention_violation_total |
| `VALIDATION_ERROR` | 400 | No | artifact_api_error_total<br>artifact_store_hash_mismatch_total |

### [Audit & Evidence](../../../data/audit.md#3-3-api-error-codes-binding) {#audit-evidence}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `INTEGRITY_ERROR` | Seal manifest hash mismatch or immutable sink divergence detected. | Rebuild manifests via `ops/audit/rebuild_manifest.py`, regenerate seal, then retry once integrity is restored. |
| `NOT_FOUND` | Evidence bundle absent or redacted per retention policy. | Treat as terminal; refresh catalog or request prior version rather than retrying blindly. |
| `POLICY_BLOCK` | Legal hold, residency, or waiver guard prevents evidence release or deletion. | Surface Guardian/waiver reason, engage RB-AUDIT-004 or RB-WAIVER-GOV before retrying. |
| `QUARANTINED` | Evidence quarantined pending Guardian or manual review. | Escalate to Guardian reviewers; do not retry until quarantine cleared. |
| `VALIDATION_ERROR` | Waiver or DSAR payload fails schema or policy validation. | Inspect `details[]`, correct the input, and resubmit. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `INTEGRITY_ERROR` | 412 | Yes | audit_api_error_total<br>audit_seal_errors_total |
| `NOT_FOUND` | 404 | No | audit_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | audit_api_error_total<br>waiver_expiring_total |
| `QUARANTINED` | 423 | Yes | audit_api_error_total |
| `VALIDATION_ERROR` | 400 | No | audit_api_error_total |

### [Billing & Subscriptions Service](../../../customer/billing-subscriptions.md#3-3-api-error-codes-binding) {#billing-subscriptions-service}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Subscription state changed since the caller fetched it (pending change or grace period overlap). | Refresh subscription state, resolve pending changes, and resubmit with the latest version. |
| `POLICY_BLOCK` | Finance approval or compliance policy prevented plan activation or subscription change. | Obtain required Finance/Compliance approval, update Settings overrides, then retry. |
| `PROVIDER_DEGRADED` | External billing provider (Stripe) reported degraded health or webhook replay backlog. | Pause billing mutations, monitor provider status, and resume once health recovers; follow RB-BILLING-PAYMENT. |
| `VALIDATION_ERROR` | Plan or subscription payload failed schema validation (pricing tiers, effective dates, billing contact data). | Correct the request body and rerun once validation passes; reference plan catalog guardrails. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | Yes | billing_api_error_total<br>billing_subscription_conflict_total |
| `POLICY_BLOCK` | 403 | Yes | billing_api_error_total<br>billing_policy_block_total |
| `PROVIDER_DEGRADED` | 503 | Yes | billing_api_error_total<br>billing_payment_failed_total |
| `VALIDATION_ERROR` | 400 | No | billing_api_error_total<br>billing_plan_update_total |

### [Communications Service](../../../customer/communications.md#3-3-api-error-codes-binding) {#communications-service}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Outbox entry replayed with a different payload or stale version. | Re-fetch outbox status, regenerate the payload or Idempotency-Key, and retry once. |
| `POLICY_BLOCK` | Guardian or masking rules blocked a message, attachment, or portal download token. | Show the Guardian reason, remediate content or policy configuration, and retry once cleared. |
| `PROVIDER_DEGRADED` | Email or SMS provider, or webhook endpoint, marked degraded with an open circuit. | Pause sends for the affected provider, alert operators, and resume once health recovers. |
| `RATE_LIMIT` | Org or channel exceeded outbound messaging or webhook throughput limits. | Honor Retry-After headers, queue retries with exponential backoff, and coordinate for sustained spikes. |
| `VALIDATION_ERROR` | Template context, attachment metadata, or download request failed schema checks. | Correct payload or template data and resubmit after validation passes. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | No | notifications_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | notifications_api_error_total<br>notify_policy_block_total |
| `PROVIDER_DEGRADED` | 503 | Yes | notifications_api_error_total<br>notifications_provider_health_total |
| `RATE_LIMIT` | 429 | No | notify_rate_limit_total |
| `VALIDATION_ERROR` | 400 | No | notifications_api_error_total |

### [Digital Signer](../../../data/digital-signer.md#3-3-api-error-codes-binding) {#digital-signer}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `SIGNATURE_MANIFEST_INVALID` | Manifest hash mismatch, missing TSA evidence, or unsupported format detected before release. | Investigate manifest diff, regenerate evidence via ops/signer/validate_manifests.py, then retry the submission. |
| `SIGNATURE_POLICY_MISMATCH` | Requested policy does not match Settings (sign.signature_policies[]) or deliverable class. | Align the request payload with the active policy or update Settings; avoid blind retries. |
| `SIGNATURE_REPLAY_MISMATCH` | Replay verification detected output drift versus the stored manifest. | Quarantine the artifact, run replay validation (ops/scripts/signer/replay_signature.py), and remediate before reissuing. |
| `SIGNING_PIPELINE_BLOCKED` | Signing queue halted due to FIPS waiver expiry, trust-root drift, or Guardian quarantine. | Follow RB-SIGN-INCIDENT or RB-SIGN-TSA, refresh waivers or trust roots, and resubmit once the pipeline resumes. |
| `SIGN_IDEMPOTENCY_CONFLICT` | Replayed signing request with differing payload or digest. | Generate a new Idempotency-Key, ensure the canonical payload remains unchanged, and retry once. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `SIGNATURE_MANIFEST_INVALID` | 409 | Yes | signer_api_error_total<br>signer_signature_policy_violation_total |
| `SIGNATURE_POLICY_MISMATCH` | 409 | Yes | signer_signature_policy_violation_total |
| `SIGNATURE_REPLAY_MISMATCH` | 412 | Yes | signer_api_error_total<br>signer_signature_policy_violation_total |
| `SIGNING_PIPELINE_BLOCKED` | 503 | Yes | signer_api_error_total<br>signer_pipeline_blocked_total |
| `SIGN_IDEMPOTENCY_CONFLICT` | 409 | No | signer_api_error_total |

### [Guardian Service](../../../platform/guardian.md#3-3-api-error-codes-binding) {#guardian-service}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CLASSIFIER_LOW_CONFIDENCE` | ML detectors produced low-confidence spans that require manual review. | Surface the decision to reviewers; expect WARN/manual decision instead of automatic retry. |
| `GUARDIAN_SUBMISSION_TIMEOUT` | Queue processing exceeded timeout or a detector became unavailable. | Workers auto-retry; clients may poll status; escalate if repeated via guardian_submission_timeout_total. |
| `PARENT_NOT_APPROVED` | Upstream artifact reverted or lacks PASS while a dependant artifact was submitted. | Approve or restore the parent artifact, then resubmit once lineage is consistent. |
| `POLICY_FORBIDDEN_PATTERN` | Detectors matched forbidden content such as PII/PHI patterns, legal hold signals, or leakage. | Follow Guardian remediation guidance, redact or waive content before resubmission. |
| `QUARANTINED` | Guardian quarantined the artifact due to detector or policy breach. | Resolve the root cause, obtain manual clearance via POST /guardian/quarantine, then rerun the pipeline. |
| `RESIDENCY_POLICY_BLOCK` | Residency or waiver policy prohibits processing (for example, provider drift or missing attestation). | Coordinate with Settings or Reference Manager waivers, update residency catalog, and retry once cleared. |
| `SCHEMA_POLICY_BLOCK` | Request payload failed schema validation or was missing required policy context. | Fix the payload, rerun submission; repeated failures escalate to RB-GUARD-QUEUE. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CLASSIFIER_LOW_CONFIDENCE` | 409 | Yes | guardian_api_error_total |
| `GUARDIAN_SUBMISSION_TIMEOUT` | 503 | Yes | guardian_submission_timeout_total |
| `PARENT_NOT_APPROVED` | 409 | Yes | guardian_api_error_total |
| `POLICY_FORBIDDEN_PATTERN` | 403 | Yes | guardian_policy_block_total |
| `QUARANTINED` | 423 | Yes | guardian_api_error_total<br>guardian_policy_block_total |
| `RESIDENCY_POLICY_BLOCK` | 403 | Yes | guardian_api_error_total<br>guardian_policy_block_total |
| `SCHEMA_POLICY_BLOCK` | 400 | No | guardian_api_error_total<br>guardian_detector_errors_total |

### [Identity & Access](../../../platform/identity.md#3-3-api-error-codes-binding) {#identity-access}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `AUTH_CLOCK_SKEW` | Signed request timestamp fell outside the ±120 second tolerance. | Sync client clocks with NTP or Chrony, then retry once the skew is corrected. |
| `AUTH_ERROR` | Invalid credentials, disabled account, or revoked session token. | Prompt the user to re-authenticate, enforce MFA if required, and avoid retry loops with stale tokens. |
| `AUTH_SIGNATURE_INVALID` | HMAC signature mismatch for privileged service calls. | Regenerate the canonical string, rotate keys if necessary, and retry with a corrected signature. |
| `POLICY_BLOCK` | Break-glass or residency policy forbids the requested action. | Surface remediation steps, complete the break-glass workflow or obtain a waiver before retrying. |
| `RATE_LIMIT` | Org or actor exceeded login, password reset, or session creation quotas. | Honor Retry-After, enforce backoff in the UI, and notify operators for sustained spikes. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `AUTH_CLOCK_SKEW` | 401 | No | identity_api_error_total |
| `AUTH_ERROR` | 401 | Yes | identity_api_error_total |
| `AUTH_SIGNATURE_INVALID` | 401 | Yes | identity_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | identity_api_error_total |
| `RATE_LIMIT` | 429 | No | identity_api_error_total<br>identity_rate_limit_total |

### [LangGraph Agent Orchestration](../../../automation/langgraph-agents.md#3-3-api-error-codes-binding) {#langgraph-agent-orchestration}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Idempotency key replay with a different payload or stale manifest version. | Read the latest manifest, regenerate the payload, and retry with a fresh Idempotency-Key. |
| `POLICY_BLOCK` | Guardian or residency guard rejected a pipeline launch or artifact promotion. | Present Guardian reason codes, remediate policy inputs, or seek waiver approval before retrying. |
| `PROVIDER_DEGRADED` | LLM provider or speech service unavailable and fallback chain exhausted. | Record degraded status, halt automatic retries, and resume once health probes report recovery. |
| `QUARANTINED` | Generated artifact or intermediate output quarantined pending Guardian review. | Route to reviewer workflow, capture remediation notes, and relaunch only after clearance. |
| `RATE_LIMIT` | Org or agent exceeded concurrency or FinOps budgets. | Honour Retry-After, shed background runs, and reschedule once the budget resets. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | No | agent_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | agent_guardian_block_total<br>agent_api_error_total |
| `PROVIDER_DEGRADED` | 503 | Yes | agent_api_error_total |
| `QUARANTINED` | 423 | Yes | agent_guardian_block_total |
| `RATE_LIMIT` | 429 | No | agent_api_error_total<br>agent_rate_limit_total |

### [LLM Registry & Runtime Governance](../../../automation/llm-registry.md#3-3-api-error-codes-binding) {#llm-registry-runtime-governance}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Concurrent activation modified the same provider or version. | Refresh the catalog snapshot, increment the provider version, and retry with a fresh Idempotency-Key. |
| `POLICY_BLOCK` | Residency, waiver, or moderation policy prevents provider or model activation. | Present the blocking reason to operators, adjust residency or masking settings, or obtain a waiver before retrying activation. |
| `PROVIDER_DEGRADED` | Registry placed provider circuit into OPEN or PAUSED_AWAITING_PROVIDER. | Respect the degraded status, shift traffic using the fallback chain, and retry once health returns to CLOSED. |
| `RATE_LIMIT` | Org exceeded moderation or inference budget thresholds enforced by the registry. | Honor Retry-After, shed traffic, and coordinate a FinOps waiver before resuming. |
| `VALIDATION_ERROR` | Provider catalog entry failed schema, checksum, or residency coverage validation. | Fix catalog metadata (regions, digests, pricing), rerun Settings activation, and revalidate. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | No | llm_registry_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | llm_registry_api_error_total<br>llm_circuit_state |
| `PROVIDER_DEGRADED` | 503 | Yes | llm_circuit_state<br>llm_registry_api_error_total |
| `RATE_LIMIT` | 429 | No | llm_registry_api_error_total<br>llm_cost_estimate_total |
| `VALIDATION_ERROR` | 400 | No | llm_registry_api_error_total |

### [Localization & Policy Engine](../../../automation/lp-engine.md#3-3-api-error-codes-binding) {#localization-policy-engine}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Concurrent activation changed the same PolicyContext version or hash. | Refresh digests via conditional GET, merge changes, and retry with updated If-Match or Idempotency-Key headers. |
| `POLICY_BLOCK` | Evaluation detected residency, waiver, or privacy violations that must block the requested action. | Present policy_block_code and waiver metadata to operators, remediate configuration, or obtain a waiver before retrying. |
| `PROVIDER_DEGRADED` | Reference Manager or policy bundle fetch unavailable; fallback chain exhausted. | Pause rollouts, retry once dependencies are healthy, and notify Ops of the degraded state. |
| `RATE_LIMIT` | Org exceeded compilation or evaluation budget or concurrency ceiling. | Honor Retry-After headers, stagger batch compiles, and request higher limits through governance. |
| `VALIDATION_ERROR` | Policy bundle or context payload failed schema or semantic validation. | Inspect details[], correct inputs such as missing locales or duplicate rules, and resubmit compile/evaluate. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | No | lpe_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | lpe_policy_block_total<br>guardian_policy_block_total |
| `PROVIDER_DEGRADED` | 503 | Yes | lpe_api_error_total<br>lpe_compiler_duration_seconds |
| `RATE_LIMIT` | 429 | No | lpe_api_error_total<br>lpe_rate_limit_total |
| `VALIDATION_ERROR` | 400 | No | lpe_api_error_total |

### [Observability](../../../platform/observability.md#3-3-api-error-codes-binding) {#observability}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Alert or dashboard update failed optimistic concurrency (expected_version mismatch). | Re-fetch the configuration, merge edits, and retry with the latest expected_version. |
| `POLICY_BLOCK` | Compliance policy forbade enabling an alert because metadata was missing. | Supply the required escalation or runbook metadata, then retry once policy checks pass. |
| `PROVIDER_DEGRADED` | Downstream telemetry pipeline (Prometheus, Loki, Tempo) degraded or unavailable. | Buffer locally where possible, alert SRE, and retry after health recovers. |
| `RATE_LIMIT` | Telemetry ingestion or dashboard export exceeded the assigned quota. | Respect Retry-After headers, throttle exporters, and coordinate capacity adjustments. |
| `VALIDATION_ERROR` | Alert or dashboard payload failed schema validation or referenced unknown metrics. | Correct the payload (metrics or labels), rerun validation, and resubmit. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | No | observability_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | observability_api_error_total<br>observability_policy_block_total |
| `PROVIDER_DEGRADED` | 503 | Yes | observability_api_error_total<br>telemetry_pipeline_health_total |
| `RATE_LIMIT` | 429 | No | telemetry_ingest_rate_limit_total |
| `VALIDATION_ERROR` | 400 | No | observability_api_error_total |

### [Platform Runtime](../../../platform/runtime.md#33-api-error-codes) {#platform-runtime}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `AUTH_CLOCK_SKEW` | X-Timestamp fell outside the permitted ±120 second window. | Synchronize system clocks (NTP/Chrony) and retry with an accurate timestamp. |
| `AUTH_ERROR` | Caller failed authentication or presented an expired token. | Re-authenticate, ensure the correct audience, and retry with a fresh credential. |
| `AUTH_SIGNATURE_INVALID` | HMAC signature mismatch or revoked key identifier. | Regenerate the canonical string, rotate keys if necessary, and retry with a valid signature. |
| `CONFLICT` | Optimistic concurrency or idempotency conflict detected. | Fetch the latest state, update the payload or Idempotency-Key, and retry once. |
| `INTEGRITY_ERROR` | Hash or ETag validation failed for the submitted content. | Recompute digests, re-upload content, and avoid blind retries without correcting the payload. |
| `NOT_FOUND` | Resource missing, masked by RLS, or already archived. | Treat as terminal; refresh indices or scope before retrying with a new identifier. |
| `POLICY_BLOCK` | Guardian, residency, or settings policy prevented the action. | Surface details.reason, remediate policy or obtain an approved waiver before retrying. |
| `PROVIDER_DEGRADED` | Downstream dependency unavailable or circuit breaker open. | Implement retry with jitter respecting Retry-After; surface degraded status to operators. |
| `QUARANTINED` | Artifact quarantined for manual review or remediation. | Hold follow-on actions until Guardian releases the artifact; do not retry automatically. |
| `RATE_LIMIT` | Rate, quota, or budget exceeded for the caller. | Honor Retry-After, apply exponential backoff, and present throttling feedback to operators. |
| `VALIDATION_ERROR` | Request payload failed schema or semantic validation. | Inspect details[], correct the offending fields, and resubmit the request. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `AUTH_CLOCK_SKEW` | 401 | No | api_error_total |
| `AUTH_ERROR` | 401 | Yes | api_error_total |
| `AUTH_SIGNATURE_INVALID` | 401 | Yes | api_error_total |
| `CONFLICT` | 409 | No | api_error_total |
| `INTEGRITY_ERROR` | 412 | Yes | api_error_total |
| `NOT_FOUND` | 404 | No | api_error_total |
| `POLICY_BLOCK` | 403 | Yes | api_error_total<br>api_error_unknown_total |
| `PROVIDER_DEGRADED` | 503 | Yes | api_error_total<br>api_error_rate_spike_total |
| `QUARANTINED` | 423 | Yes | api_error_total |
| `RATE_LIMIT` | 429 | No | api_error_total |
| `VALIDATION_ERROR` | 400 | No | api_error_total |

### [Reference Manager](../../../data/ref-manager.md#3-3-api-error-codes-binding) {#reference-manager}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Publish request collided with an in-flight version where the bundle version already exists. | Refresh the bundle catalog, increment the semantic version, and retry once. |
| `POLICY_BLOCK` | License, residency, or waiver policy prevented bundle publish or acknowledgment. | Surface waiver or licensing metadata, resolve policy issues, and rerun publish or adoption after remediation. |
| `PROVIDER_DEGRADED` | Source connector offline or Reference Manager put into protective pause. | Alert Content Ops or Legal Ops, retry after the source recovers or manual upload completes. |
| `RATE_LIMIT` | Org or system-wide publish cadence exceeded governance limits. | Respect Retry-After, reschedule batch publishes, or escalate for a temporary quota increase. |
| `VALIDATION_ERROR` | Bundle or template payload failed schema, checksum, or coverage validation. | Inspect the validation report, correct source data or manifests, and resubmit the publish job. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | No | reference_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | reference_api_error_total<br>reference_manager_publish_guard_failure |
| `PROVIDER_DEGRADED` | 503 | Yes | reference_api_error_total<br>reference_manager_harvest_error_total |
| `RATE_LIMIT` | 429 | No | reference_api_error_total<br>reference_publish_rate_limit_total |
| `VALIDATION_ERROR` | 400 | No | reference_api_error_total |

### [Search & Indexing Service](../../../data/search-index.md#3-3-api-error-codes-binding) {#search-indexing-service}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `POLICY_BLOCK` | Access policy, Guardian verdict, or tenant residency rule forbids returning requested results. | Confirm caller permissions, review Guardian verdicts, or adjust residency scope before retrying. |
| `PROVIDER_DEGRADED` | Underlying search index or embedding service is unavailable or lagging beyond thresholds. | Retry after backoff; system falls back to lexical only. Escalate using RB-SEARCH-INGEST if the incident persists. |
| `VALIDATION_ERROR` | Query payload or filter parameters failed validation (unsupported field, malformed vector, or tenant scope missing). | Correct the query parameters using the published schema and retry. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `POLICY_BLOCK` | 403 | Yes | search_api_error_total<br>search_acl_violation_total |
| `PROVIDER_DEGRADED` | 503 | Yes | search_api_error_total<br>search_index_backlog_total |
| `VALIDATION_ERROR` | 400 | No | search_api_error_total<br>search_query_validation_total |

### [Settings Registry](../../../platform/settings.md#3-3-api-error-codes-binding) {#settings-registry}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `AUTH_CLOCK_SKEW` | X-Timestamp header outside the ±120 second tolerance. | Sync clocks and retry with a corrected timestamp. |
| `AUTH_SIGNATURE_INVALID` | HMAC signature mismatch on mutating requests. | Recompute the signature, rotate credentials via RB-HMAC-ROTATE if repeated, and retry. |
| `CONFLICT` | Activation expected_version mismatch or replayed Idempotency-Key. | Re-fetch activation state, regenerate the idempotency token, and retry. |
| `POLICY_BLOCK` | Residency, waiver, or governance policy rejected the activation. | Obtain waiver or approval, update policy inputs, and resubmit the activation. |
| `SECRET_DISCLOSURE_BLOCKED` | Attempt to export masked secret fields through diff previews or read APIs. | Remove secret fields from the request; fetch redacted values only. |
| `VALIDATION_ERROR` | Bundle schema violation, unsafe override, or diff failing semantic guard. | Inspect details[], remediate configuration, rerun validation. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `AUTH_CLOCK_SKEW` | 401 | No | settings_auth_failure_total |
| `AUTH_SIGNATURE_INVALID` | 401 | Yes | settings_auth_failure_total |
| `CONFLICT` | 409 | No | settings_error_total |
| `POLICY_BLOCK` | 403 | Yes | settings_error_total<br>settings_policy_block_total |
| `SECRET_DISCLOSURE_BLOCKED` | 403 | Yes | settings_error_total |
| `VALIDATION_ERROR` | 400 | No | settings_error_total |

### [Web Application & Portal](../../../experience/web-app.md#3-3-api-error-codes-binding) {#web-application-portal}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CHAT_DISABLED` | Org-level settings or Guardian policy disabled assistants for the active org or case. | Display the assistant-disabled banner, suppress retries, direct operators to review Settings or Guardian waivers. |
| `POLICY_BLOCK` | Guardian or residency guard blocked an action invoked from the UI. | Surface Guardian reason/details, require operator remediation before enabling another attempt. |
| `PORTAL_DOWNLOAD_PRECONDITION` | Portal download request failed the If-Match guard or token validation. | Prompt the client to refresh the deliverable list, regenerate the download link, and avoid automatic retry loops. |
| `RATE_LIMIT` | Client exceeded the configured RPM or token limits for chat or portal download APIs. | Honor Retry-After headers, show throttling guidance, and back off additional attempts. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CHAT_DISABLED` | 403 | No | ui_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | ui_api_error_total |
| `PORTAL_DOWNLOAD_PRECONDITION` | 412 | No | portal_download_error_total |
| `RATE_LIMIT` | 429 | No | ui_api_error_total<br>ui_rate_limit_total |

### [Worker Cluster](../../../automation/worker-cluster.md#3-3-api-error-codes-binding) {#worker-cluster}

| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Idempotency payload hash mismatch or stale version when retrying job controls. | Re-fetch job state, regenerate the Idempotency-Key, and retry once with the updated payload. |
| `INTEGRITY_ERROR` | Upload finalize detected a hash mismatch against staged content. | Re-upload chunks with the correct digest and avoid blind retries until integrity matches. |
| `POLICY_BLOCK` | Guardian or residency guard, or a budget hold, prevented job execution. | Surface Guardian reason or budget hold, remediate policy or quota before retrying. |
| `PROVIDER_DEGRADED` | Downstream provider or queue paused (PAUSED_AWAITING_PROVIDER, circuit open). | Respect backoff, surface degraded status to operators, and retry when health probes recover. |
| `RATE_LIMIT` | Org or job-kind concurrency ceiling exceeded. | Honor Retry-After, queue retries with exponential backoff, and reduce burst size. |

| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | No | job_api_error_total<br>idempotency_conflict_total |
| `INTEGRITY_ERROR` | 412 | Yes | job_api_error_total<br>upload_finalize_total |
| `POLICY_BLOCK` | 403 | Yes | job_api_error_total |
| `PROVIDER_DEGRADED` | 503 | Yes | job_api_error_total<br>job_dependency_degraded_total |
| `RATE_LIMIT` | 429 | No | job_api_error_total<br>job_rate_limit_total |
<!-- END AUTO-GENERATED: api-error-index -->
