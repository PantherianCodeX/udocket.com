---
title: "uDocket — TDD Appendix: SLO Index"
subtitle: "Consolidated service and app service-level objectives"
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

This appendix lists the SLOs defined in each service and app specification. Refresh it with `python scripts/docs/build_slo_index.py` when SLO sections change.

<!-- BEGIN AUTO-GENERATED: slo-index -->
<!-- AUTO-GENERATED: Run `python scripts/docs/build_slo_index.py` to refresh. -->

### [Audit & Evidence](../../../services/audit.md)

**Purpose:** Capture the availability and timeliness guarantees that keep audit evidence defensible. **|**
**Contract:** Seal verification, immutable mirroring, waiver reviews, and DSAR handling must satisfy the thresholds below before approvals continue. **|**
**State:** Metrics `audit_seal_errors_total`, `audit_worm_lag_seconds`, `waiver_expiring_total`, `dsar_journal_pending_total`; stored seal artifacts, waiver ledger entries, and DSAR journals provide evidence. **|**
**Failures & handling:** Breaches invoke RB-AUDIT-004, RB-WAIVER-GOV, or RB-PRIV-DSAR prior to resuming promotions. **|**
**Observability:** Dashboards “Audit Seal Integrity”, “Waiver Ledger”, and synthetic `audit_verify` runs monitor compliance. **|**
**Breadcrumbs:** Seal runner `ops/audit/seal_runner.py`, waiver ledger `packages/udocket_core/compliance/waiver.py`, DSAR tooling `ops/privacy/dsar_runner.py`. **|**
**References:** Logging spec §6, Settings spec §7.3, TDD §12.

- **Seal continuity:** Hourly seal verification succeeds with ≤1 failed interval per quarter; tracked via `audit_seal_errors_total` and synthetic `audit_verify` job, escalating through RB-AUDIT-004 on breach.
- **Immutable lag:** `audit_worm_lag_seconds` stays ≤15 minutes; exceeding lag blocks approvals and requires joint remediation with Observability before restart.
- **Compliance workflows:** Waiver backlog (`waiver_expiring_total`) resolved within 5 business days; DSAR backlog (`dsar_journal_pending_total`) remains within regulatory SLA (45 days CCPA/30 days GDPR) with automated reminders and RB-PRIV-DSAR if breached.

______________________________________________________________________

### [Digital Signer](../../../services/digital-signer.md)

**Purpose:** Define reliability expectations for signing, TSA, and OCSP operations. **|**
**Contract:** Signing requests, timestamping, and OCSP validation must meet the thresholds below before releases continue. **|**
**State:** Metrics `signer_request_latency_seconds`, `signer_error_total`, `tsa_time_drift_seconds`, `ocsp_latency_seconds`; dashboards “Signer & TSA” and “Deliverable Signatures”; audit artifacts for key rotations. **|**
**Failures & handling:** Breaches trigger RB-SIGN-INCIDENT, RB-SIGN-TSA, or RB-SIGN-OCSP as appropriate before new deliverables are approved. **|**
**Observability:** Grafana dashboards “Signer & TSA”, Alertmanager routes for signer/TSA/OCSP, synthetic signing tests. **|**
**Breadcrumbs:** Observability config `infra/observability/dashboards/signer.json`, Prometheus rules `infra/monitoring/signer-prometheus-rules.yaml`, runbooks `docs/src/ops/runbooks/signer/*.md`. **|**
**References:** TDD §12, Audit spec §4, Settings spec §7.3.

- **Signing success:** ≥99.9% of signing requests complete successfully each month; enforced via `signer_request_latency_seconds` P95 ≤ 5 seconds and `signer_error_total` burn-rate alerts tied to RB-SIGN-INCIDENT.
- **Timestamp authority drift:** `tsa_time_drift_seconds` remains ≤ 5 seconds absolute; violations trigger RB-SIGN-TSA and pause releases until corrected.
- **OCSP responsiveness:** OCSP round-trip P95 ≤ 5 seconds (`ocsp_latency_seconds`); sustained breaches escalate to RB-SIGN-OCSP before deliverables can be promoted.

______________________________________________________________________

### [Guardian Service](../../../services/guardian.md)

**Purpose:** Capture Guardian’s core latency and quality guarantees so approvals remain safe. **|**
**Contract:** Judgment latency, manual review throughput, and false-positive ceiling must meet the thresholds below before artifacts progress. **|**
**State:** Metrics `guardian_judgment_latency_seconds`, `guardian_pending_oldest_seconds`, `guardian_quarantine_false_positive_total`; dashboards “Guardian SLO” and “Guardian Manual Review”; synthetic job `guardian_slo.yaml`. **|**
**Failures & handling:** Breaches invoke RB-GUARD-QUEUE, RB-GUARD-REVIEW, or RB-GUARD-POLICY before approvals resume. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, and synthetic runs monitor compliance. **|**
**Breadcrumbs:** Telemetry `packages/udocket_core/guardian/metrics.py`, runbooks `docs/src/ops/runbooks/guardian/*.md`. **|**
**References:** TDD §6, Audit spec §5, Settings spec §7.3.

- **Judgment latency:** 99.9 % availability with P95 ≤ 5 minutes measured via `guardian_judgment_latency_seconds` and synthetic `guardian_slo.yaml`; burn-rate alerts 2×/6× open RB-GUARD-QUEUE.
- **Manual review throughput:** Reviewer queue backlog P95 ≤ 30 minutes (`review_queue_oldest_seconds`); sustained breaches require manual escalation and review of staffing plan before further launches.
- **False-positive quarantine ceiling:** `guardian_quarantine_false_positive_total` maintains ≤5 % of total quarantines on rolling 30-day basis; exceeding threshold requires policy tuning and Security sign-off.

### [Identity & Access](../../../services/identity.md)

**Purpose:** Capture the reliability expectations for authentication, RLS enforcement, and masking governance. **|**
**Contract:** Token issuance, context setup, and masking/break-glass workflows must meet the thresholds below before releases continue. **|**
**State:** Metrics `identity_token_flow`, `auth_layer_violation_total`, `rls_context_missing_total`, `logging_neverlog_violation_total`, `break_glass_event_missing_retrospective_total`; dashboards “Identity Posture” and “RLS Context Guards”; synthetic probes `synthetics/identity_*`. **|**
**Failures & handling:** Breaches trigger RB-IDP-FAILOVER, RB-RLS-CONTEXT, RB-MASK, or RB-BREAK-GLASS prior to resuming automation. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, and synthetic runs ensure compliance. **|**
**Breadcrumbs:** Telemetry modules `apps/platform/logging/access.py`, `packages/udocket_core/permissions`, runbooks `docs/src/ops/runbooks/identity/*.md`. **|**
**References:** Settings spec §7, TDD §12, Guardian spec §7.

- **Authentication availability:** ≥99.9% success for token issuance and session validation, measured via synthetic `identity_token_flow` and `auth_layer_violation_total`; breaches page RB-IDP-FAILOVER and require RCA prior to release.
- **RLS context enforcement:** `rls_context_missing_total` remains at zero sustained; any incident triggers RB-RLS-CONTEXT and blocks deployments until resolved.
- **Masking & break-glass governance:** `logging_neverlog_violation_total` and `break_glass_event_missing_retrospective_total` stay at zero; violations escalate via RB-MASK/RB-BREAK-GLASS within 24 hours.

### [LangGraph Agent Orchestration](../../../services/langgraph-agents.md)

**Purpose:** Capture availability, quality, latency, and cost expectations for LangGraph pipelines. **|**
**Contract:** Agent run completion, QA acceptance, lane latency, and token budgets must meet the thresholds below before promotions proceed. **|**
**State:** Metrics `agent_job_completion_ratio`, `agent_lane_duration_seconds`, `agent_queue_latency_seconds`, `agent_token_budget_violation_total`; dashboards “Agent Pipelines – Activation”, “Agent QA Acceptance”, FinOps monitors `ops/finops/agents_cost_dashboard.json`. **|**
**Failures & handling:** Breaches invoke RB-AGENT-PIPELINE, RB-AGENT-QA, or RB-FINOPS-LANGGRAPH before enabling new activations. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, QA harness reports, and shadow run comparisons provide evidence. **|**
**Breadcrumbs:** QA harness `tests/agents/test_langgraph_acceptance.py`, telemetry `packages/udocket_core/agents/logging.py`, runbooks `docs/src/ops/runbooks/agents/*.md`. **|**
**References:** TDD §6, Worker Cluster spec §3.5, Guardian spec §7.

- **Pipeline availability:** ≥99.5% of LangGraph runs complete without manual retry, measured via `agent_job_completion_ratio`; breaches trigger RB-AGENT-PIPELINE before promotions proceed.
- **QA acceptance:** Automated QA issue density stays ≤0.2 blocking defects per artifact; exceedances invoke RB-AGENT-QA and pause affected pipelines.
- **Lane latency:** Analyze lane P95 ≤ 15 minutes, Compose lane P95 ≤ 45 minutes, Transcribe backlog clearance P95 ≤ 5 minutes (`agent_lane_duration_seconds{lane}` / `agent_queue_latency_seconds`). Breaches require corrective action before enabling new activations.
- **FinOps guard:** `agent_token_budget_violation_total` remains zero; if triggered, RB-FINOPS-LANGGRAPH engages and approvals halt until the budget recovers.

______________________________________________________________________

### [LLM Registry & Runtime Governance](../../../services/llm-registry.md)

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

### [Localization & Policy Engine](../../../services/lp-engine.md)

**Purpose:** Capture PolicyContext availability, compile latency, and residency enforcement expectations. **|**
**Contract:** Lookups, compiles, and policy blocks must satisfy the thresholds below before activations or bundle promotions proceed. **|**
**State:** Metrics `lpe_lookup_latency_seconds`, `lpe_compiler_duration_seconds`, `lpe_policy_block_total`; dashboards “LPE – Enforcement & Residency”, “LPE Compiler”, synthetic HIPAA/PIPEDA probes. **|**
**Failures & handling:** Breaches invoke RB-LPE-CONTEXT, RB-LPE-COMPILER, or residency runbooks before unfreezing activations. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, synthetic activation jobs, and decision-log audits provide evidence. **|**
**Breadcrumbs:** Telemetry `packages/udocket_core/lpe/telemetry.py`, synthetic definitions `synthetics/lpe_*`, runbooks `docs/src/ops/runbooks/lpe/*.md`. **|**
**References:** TDD §6, Settings spec §7.3, Guardian spec §7.

- **PolicyContext availability:** ≥99.9% of lookups succeed each month (`lpe_lookup_latency_seconds` + synthetic HIPAA/PIPEDA probes). Breaches trigger RB-LPE-CONTEXT and block Settings activations.
- **Compile latency:** 95th percentile `lpe_compiler_duration_seconds` ≤ 2 seconds; exceeding the budget pauses rollout until regression is resolved and documented.
- **Residency enforcement responsiveness:** `lpe_policy_block_total` records blocks within 60 seconds of unsafe activation; missed blocks escalate to Security and halt bundle promotion.

______________________________________________________________________

### [Notifications Service](../../../services/notifications.md)

**Purpose:** Capture delivery, webhook, in-app, and token reliability goals. **|**
**Contract:** Notification delivery, webhook ingestion, SSE drop rate, and token validation must satisfy the thresholds below before campaigns launch. **|**
**State:** Metrics `delivery_success_ratio`, `notifications_receipt_latency_seconds`, `sse_connection_drop_total`, `download_token_validation_total{outcome}`; dashboards “Notifications Delivery”, “Notifications In-App”, “Download Tokens”. **|**
**Failures & handling:** Breaches invoke RB-NOTIFY-OUTAGE, RB-NOTIFY-WEBHOOK, RB-NOTIFY-INAPP, or RB-NOTIFY-TOKEN prior to resuming automation. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, portal synthetics, and SSE monitors provide evidence. **|**
**Breadcrumbs:** Prometheus rules `infra/monitoring/notifications-prometheus-rules.yaml`, synthetic definitions `synthetics/notifications_*`, runbooks `docs/src/ops/runbooks/notifications/*.md`. **|**
**References:** TDD §11, Web App §6, Audit §4.

- **Delivery success:** ≥99.5% of outbound notifications reach provider or user receipt within channel SLA, tracked by `delivery_success_ratio` and `notifications_receipt_latency_seconds`. Breaches trigger RB-NOTIFY-OUTAGE and pause new campaigns until resolved.
- **Webhook ingestion latency:** Provider callbacks process within 60 seconds P95 (`notifications_receipt_latency_seconds` subset); overruns invoke RB-NOTIFY-WEBHOOK and force retry throttling audits.
- **In-app realtime health:** SSE drop rate (`sse_connection_drop_total` / connections) stays below 1% rolling 15 minutes; exceeding threshold pages RB-NOTIFY-INAPP before customer-facing impact widens.
- **Download token validation:** Unexpected deny rate (`download_token_validation_total{outcome="denied"}` minus abuse baseline) remains under 0.5%; anomalies escalate via RB-NOTIFY-TOKEN with security review.

______________________________________________________________________

### [Observability](../../../services/observability.md)

**Purpose:** Outline ingestion, mirroring, correlation, and cost objectives that keep observability trustworthy. **|**
**Contract:** Log ingestion, immutable mirroring, trace correlation, and cost budgets must satisfy the thresholds below before deploy gates reopen. **|**
**State:** Metrics `logging_ingest_lag_seconds`, `logging_drop_rate_pct`, `audit_worm_lag_seconds`, `trace_sampling_drift_total`, `logging_volume_budget_violation_total`; dashboards “Logging Pipeline”, “Trace Correlation”, “Logging Cost”. **|**
**Failures & handling:** Breaches invoke RB-LOG-007, RB-AUDIT-004, RB-TRACE-CORR, or RB-COST prior to resuming approvals. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, synthetic ingest checks, and seal verifiers provide evidence. **|**
**Breadcrumbs:** Prometheus rules `infra/monitoring/logging-prometheus-rules.yaml`, seal runner `ops/audit/seal_runner.py`, runbooks `docs/src/ops/runbooks/logging/*.md`. **|**
**References:** TDD §12, Audit spec §5, Settings §7.2.

- **Ingest availability:** ≥99.9% successful log ingestion each month, enforced by `logging_ingest_lag_seconds` < 30s P95 and `logging_drop_rate_pct = 0`; burn-rate alerts open RB-LOG-007.
- **Immutable mirror lag:** Mirror delay stays ≤1 collection interval (≤15 minutes) measured via `audit_worm_lag_seconds`; breaches pause approvals until RB-AUDIT-004 completes.
- **Trace correlation fidelity:** Sampling drift between trace/error rates <5% sustained, tracked by `trace_sampling_drift_total`; violations trigger RB-TRACE-CORR before release sign-off.
<a id="7-cost-management--budgets"></a>

- **Cost guardrails:** Daily log volume per service remains within configured budgets (`logging_volume_budget_violation_total = 0`); overrides require RB-COST and FinOps approval within 1 business day.

______________________________________________________________________

### [Platform Runtime](../../../services/platform-runtime.md)

**Purpose:** Define reliability expectations for the shared runtime footprint. **|**
**Contract:** Kubernetes control plane, Flux convergence, and guardrail enforcement must meet the thresholds below before releases proceed. **|**
**State:** Metrics `platform_control_plane_up`, `platform_flux_sync_seconds`, `pod_security_violation_total`, `mesh_policy_violation_total`, `residency_drift_detected_total`; dashboards “Platform Runtime”, “Kubernetes Guardrails”, “Residency & Endpoint Posture”. **|**
**Failures & handling:** Breaches invoke RB-K8S-FENCE and the residency runbooks before automation resumes. **|**
**Observability:** Grafana SLO dashboards with burn-rate alerts, synthetic `/readyz` checks, and residency scanners provide evidence. **|**
**Breadcrumbs:** Monitoring configs `infra/monitoring/platform-runtime-prometheus-rules.yaml`, synthetic scripts `scripts/security/check_tls_ciphers.py`, `scripts/residency/scan_endpoints.py`. **|**
**References:** TDD §12, Settings spec §7.2, Logging spec §6.

- **Control plane availability:** ≥99.9% monthly uptime for the managed Kubernetes API and ingress endpoints, measured via synthetic `/readyz` probes and `platform_control_plane_up`. Burn-rate alerts (1×/6×) page platform runtime on-call via RB-K8S-FENCE.
- **Flux convergence:** 95th percentile reconciliation latency ≤5 minutes as captured by `platform_flux_sync_seconds`; breaches block releases until drift is resolved and recorded in RB-K8S-FENCE.
- **Guardrail enforcement:** Policy enforcement alerts (`pod_security_violation_total`, `mesh_policy_violation_total`, `residency_drift_detected_total`) must remain at zero sustained; any recurring breach triggers incident review prior to release sign-off.

______________________________________________________________________

### [Reference Manager](../../../services/ref-manager.md)

**Purpose:** Capture content ingestion, publish, adoption, and compliance objectives for the reference manager. **|**
**Contract:** Harvest availability, publish latency, adoption acknowledgements, and license enforcement must meet the thresholds below before new bundles ship. **|**
**State:** Metrics `reference_manager_harvest_total`, `reference_manager_publish_latency_seconds`, `reference_bundle_adoption_latency_seconds`, `reference_manager_license_violation_total`; dashboards “Reference Manager – Harvest”, “Publish Pipeline”, “Adoption”, “Compliance”. **|**
**Failures & handling:** Breaches invoke RB-RM-HARVEST, RB-RM-PUBLISH, RB-RM-ADOPTION, or RB-RM-LICENSE before resuming operations. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, synthetic harvest/publish jobs, and adoption drills provide evidence. **|**
**Breadcrumbs:** Telemetry `packages/udocket_core/reference_manager/telemetry.py`, synthetic definitions `ops/reference/synthetics/*.yaml`, runbooks `docs/src/ops/runbooks/reference/*.md`. **|**
**References:** TDD §6, Settings spec §7.3, Audit spec §4.

- **Harvest availability:** ≥99.5% availability for provider harvest runs, measured via `reference_manager_harvest_total` success rate and synthetic connector checks; breaches trigger RB-RM-HARVEST.
- **Publish latency:** 95th percentile publish pipeline latency (`reference_manager_publish_latency_seconds`) ≤ 10 minutes; exceeding budget blocks new publishes and invokes RB-RM-PUBLISH.
- **Adoption acknowledgement:** Bundles adopted within 24 hours P95 (`reference_bundle_adoption_latency_seconds`); backlog alerts enforce RB-RM-ADOPTION.
- **Compliance enforcement:** License violations (`reference_manager_license_violation_total`) remain zero; detection escalates via RB-RM-LICENSE before additional ingest occurs.

### [Settings Registry](../../../services/settings.md)

**Purpose:** Capture registry availability, activation latency, cache freshness, and residency enforcement guarantees. **|**
**Contract:** API availability, activation duration, cache invalidation, and residency checks must satisfy the thresholds below before new settings are promoted. **|**
**State:** Metrics `settings_request_total`, `settings_error_total`, `settings_activation_duration_seconds`, `settings_cache_invalidation_lag_seconds`, `settings_residency_violation_total`; dashboards “Settings Registry – SLO”, “Settings Cache”, “Settings Drift”. **|**
**Failures & handling:** Breaches invoke RB-GOV-008, RB-SETTINGS-CACHE, or RB-RES-\* prior to resuming activations. **|**
**Observability:** Grafana dashboards, synthetic activation tests, and burn-rate alerts supply evidence. **|**
**Breadcrumbs:** Prometheus rules `infra/monitoring/settings-prometheus-rules.yaml`, synthetic configs `ops/synthetics/settings_slo.yaml`, runbooks `docs/src/ops/runbooks/settings/*.md`. **|**
**References:** TDD §12, Logging spec §6, Audit spec §5.

- **API availability:** ≥99.9% monthly success rate for read/write operations (`settings_request_total` vs `settings_error_total`). Breaches trigger RB-GOV-008 and freeze releases until the budget recovers.
- **Activation latency:** 95th percentile activation duration (`settings_activation_duration_seconds`) ≤ 120 seconds; overruns pause activations and require RCA prior to thaw.
- **Cache freshness:** `settings_cache_invalidation_lag_seconds` stays ≤ 60 seconds P95; sustained lag opens RB-SETTINGS-CACHE and blocks deploys.
- **Residency enforcement:** `settings_residency_violation_total` remains zero; any event invokes RB-RES-\* and requires waiver or remediation before continuing.

### [Web Application & Portal](../../../apps/web-app.md)

**Purpose:** Capture availability, latency, notification, and assistant policy goals for the web experience. **|**
**Contract:** Portal uptime, latency, SSE reliability, and assistant guardrails must meet the thresholds below before releases ship. **|**
**State:** Metrics `portal_http_availability`, `portal_ttfb_seconds`, `ui_interaction_latency_seconds`, `sse_connection_drop_total`, `chat_policy_block_total`; dashboards “Portal Integrity”, “Operator Workspace”, “Notifications Delivery”, “Assistant Usage”. **|**
**Failures & handling:** Breaches invoke RB-PORTAL-AVAIL, RB-PORTAL-PERF, RB-NOTIFY-INAPP, or RB-ASSISTANT-GUARDRAIL prior to resuming deploys. **|**
**Observability:** Grafana dashboards, synthetic portal tests, SSE monitors, and assistant QA reports provide evidence. **|**
**Breadcrumbs:** Prometheus rules `infra/monitoring/web-app-prometheus-rules.yaml`, synthetics `synthetics/web_portal_*.yaml`, runbooks `docs/src/ops/runbooks/web-app/*.md`. **|**
**References:** Notifications §6, Guardian §7, Settings §6.

- **Portal availability:** ≥99.9% monthly uptime for authenticated views, measured via synthetic portal smoke tests and `portal_http_availability`. Breaches trigger RB-PORTAL-AVAIL and pause deploys.
- **Latency:** Portal TTFB P95 ≤ 400 ms for in-region clients (`portal_ttfb_seconds`), and staff workspace interactive latency (`ui_interaction_latency_seconds`) P95 ≤ 250 ms. Exceeding budgets invokes RB-PORTAL-PERF.
- **Notification fan-out:** SSE drop rate (`sse_connection_drop_total`) < 1% rolling 15 minutes; higher rates trigger RB-NOTIFY-INAPP before UI degradation spreads.
- **Assistant policy adherence:** Policy block rate (`chat_policy_block_total / chat_sessions_total`) stays below 5% while ensuring zero policy escapes; breaches trigger RB-ASSISTANT-GUARDRAIL review.

______________________________________________________________________

### [Worker Cluster](../../../services/worker-cluster.md)

**Purpose:** Capture queue throughput, job completion, and watchdog timing guarantees. **|**
**Contract:** Queue latency, completion ratio, watchdog heartbeat, and upload scanning throughput must stay within the thresholds below before new jobs launch. **|**
**State:** Metrics `celery_queue_depth`, `agent_job_completion_ratio`, `job_retry_total`, `watchdog_runner_lag_seconds`, `watchdog_runner_missed_total`, `upload_scan_duration_seconds`; dashboards “Worker Queues”, “Watchdog Runner”, “Upload Scanning”. **|**
**Failures & handling:** Breaches trigger RB-JOB-QUEUE, RB-JOB-WATCHDOG, or RB-UPLOAD-SCAN prior to resuming automation. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, synthetic watchdog checks, and queue latency probes provide evidence. **|**
**Breadcrumbs:** Monitoring rules `infra/monitoring/worker-prometheus-rules.yaml`, synthetic definitions `synthetics/worker_*`, runbooks `docs/src/ops/runbooks/worker/*.md`. **|**
**References:** TDD §12, Logging spec §6, Notifications spec §6.

- **Queue latency:** 95th percentile job start delay (`celery_queue_depth` + derived latency) ≤ 2 minutes for standard queues; breaches trigger RB-WORKER-QUEUE before new jobs enter backlog.
- **Job completion:** ≥99.5% of jobs complete without DLQ escalation per rolling 24h (`job_retry_total`, `dlq_event_total`); higher failure rates require RB-WORKER-DLQ and leadership update.
- **Watchdog heartbeat:** `watchdog_runner_lag_seconds` stays ≤ 60 seconds with `watchdog_runner_missed_total = 0`; missed beats invoke RB-JOB-WATCHDOG and block releases until restored.
- **Upload scanning throughput:** `upload_scan_duration_seconds` P95 stays within SLA; breaches page RB-UPLOAD-SCAN and pause ingestion.

______________________________________________________________________
<!-- END AUTO-GENERATED: slo-index -->
