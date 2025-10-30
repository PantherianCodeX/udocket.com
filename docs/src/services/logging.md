---
title: uDocket — Observability & Logging Specification
subtitle: Telemetry Pipeline, Log Access Controls, and Cost Guardrails
author:
  - Observability Engineering Guild
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Site Reliability Engineering
  - Platform Engineering
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - Compliance Engineering
  - Applied AI Engineering
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
      figure.full-width-diagram img {
        width: 100%;
        height: auto;
        display: block;
      }
    </style>
  - <header class="page-header">uDocket — Observability & Logging Specification <br>
    Telemetry Pipeline, Log Access Controls, and Cost Guardrails</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-29 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

| Field | Value |
| --- | --- |
| Authors | Observability Engineering Guild |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Site Reliability Engineering; Platform Engineering |
| Reviewers | Compliance Engineering; Applied AI Engineering |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |

**Status:** KEP: Provisional → Implementable → Implemented

**Section Requirements (binding):**
    - Preamble: Purpose/Contract/State/Failure/Observability/References/Breadcrumbs (`scripts/docs/lint_docs.py --check-template`)
    - Section tags: `(binding)`, `(normative)` or `(informative)`
    - Links resolve: §/App./ADR (`docs-link-check`)
    - Document validation: `python scripts/docs/lint_docs.py`
    - Settings keys: Document/code are in-sync
    - All requirements are CI gated

**Section tags:**
    - `(binding)` denotes requirements that block launch until implemented and tested.
    - `(normative)` captures default behaviors that may evolve via waivers or roadmap.
    - `(informative)` provides background or examples.
    - When a subsection omits a tag it is treated as informative by default—add the explicit tag when the content carries binding or normative weight.

______________________________________________________________________

## 0) Reading guide

- **Scope:** This specification governs the observability stack (logs, metrics, traces), structured logging schema, ingest pipeline, sampling and cost controls, and operator access workflows. Audit evidence, manifests, and seal pipelines are documented separately in `../services/audit.md`.
- **Audience:** SRE, Platform, service owners, and compliance reviewers who need consistent telemetry behavior and log governance.
- **Related specs:** TDD §12 provides the overview; Settings (§7.2) enumerates telemetry knobs; Guardian (§7) and LP Engine (§5) describe dependent judgments and policy contexts.
- **Change process:** Any pipeline, schema, or access control change must link this spec in the PR description, update `settings.md` keys, and include roll-forward/rollback plans. Run `python scripts/docs/check_structure.py docs/src/services/logging.md` before submission.

______________________________________________________________________

## 1) Purpose (binding)

**Purpose:** Deliver consistent, privacy-aware observability so every action is traceable and operators can remediate incidents quickly without leaking sensitive data. **|**
**Contract:** All services emit structured logs to the managed pipeline, preserve trace correlation, respect “never log” rules, and honour sampling/cost guardrails defined here. **|**
**State:** Telemetry collectors, Fluent Bit buffers, pipeline configuration, log schemas, sampling policies, Settings keys, cost budgets, and synthetic monitors. **|**
**Failures & handling:** Pipelines degrade by dropping logs, exceeding budget, or losing correlation; fail-close behaviors page on-call via RB-LOG-007 and enforce immutable sink mirroring. **|**
**Observability:** Dashboards “Logging Pipeline”, “Trace Correlation”, “Logging Cost”, metrics `logging_ingest_lag_seconds`, `logging_drop_rate_pct`, `trace_sampling_rate`, `logging_volume_budget_violation_total`. **|**
**Breadcrumbs:** Helm values `infra/logging/helm/values.yaml`, collector configs `infra/logging/fluentbit/`, structured formatter `packages/udocket_core/logging/jsonlog.py`, cost controller `apps/platform/logging/cost_controller.py`, tests `tests/logging/*`. **|**
**References:** TDD §12.1 summary, Settings §7.2, Audit spec §4.

______________________________________________________________________

## 2) Responsibilities (binding)

**Purpose:** Define what the observability platform must provide and which guarantees individual services must uphold. **|**
**Contract:** Platform delivers multi-tenant logging + metrics with 12h back-pressure buffers, immutable mirror, and correlation tokens; service teams emit JSON logs, register schemas, and close budget loops. **|**
**State:** Log schemas (`spec/schemas/log_record.schema.json`, `spec/schemas/judgment_event.schema.json`), registration catalog, sampling policies, cost budgets, redaction rules. **|**
**Failures & handling:** Schema drift, missing registration, redaction violations, or budget overruns block deploys (`lint-logging`) and trigger RB-LOG-007; violations escalate to Sev-1 when PII is detected. **|**
**Observability:** `logging_service_registered_total`, `logging_redaction_dropped_total`, `logging_neverlog_violation_total`, `logging_registration_missing_total`. **|**
**Breadcrumbs:** Registration script `ops/logging/register_service.py`, redaction rules `packages/udocket_core/logging/redaction.py`, schema tests `tests/logging/test_registration.py`, cost controller tests `tests/logging/test_cost_controls.py`. **|**
**References:** §3 Pipeline, §4 Schema, §6 Access Control, §7 Cost Management.

______________________________________________________________________

## 3) API Contract (binding)

**Purpose:** Describe how services send telemetry and how the pipeline exposes ingestion endpoints. **|**
**Contract:** Emit newline-delimited JSON to stdout, register schema metadata before deployment, and honour immutable mirroring when enabled. **|**
**State:** Registration catalog, CLI tooling, OpenTelemetry exporters, Fluent Bit buffers, Kafka topics, and immutable sink configuration. **|**
**Failures & handling:** Schema registration failures or ingestion lag block releases via `lint-logging` and RB-LOG-007; immutable mirror issues escalate to Audit §5. **|**
**Observability:** Dashboard “Logging Pipeline”, metrics `logging_ingest_lag_seconds`, `logging_spool_utilization_pct`, `logging_registration_missing_total`. **|**
**Breadcrumbs:** Registration CLI `ops/logging/register_service.py`, Otel/Fluent Bit charts `infra/logging/helm/`, tests `tests/logging/test_pipeline_health.py`. **|**
**References:** Settings §7.2 (`logging.pipeline.*`), Audit §4, Worker Cluster §3.

### 3.1 External Interfaces

- Services emit structured logs to stdout via `packages.udocket_core.logging.jsonlog.StructuredJSONFormatter`; stderr reserved for `ERROR+` duplicates only.
- Schema registration uses `ops/logging/register_service.py --service <name> --schema log_record@1` and is enforced by CI (`lint-logging`).
- APIs that expose log access do so through `apps/platform/logging/access.py` with WebAuthn step-up; details in Security §7.

### 3.2 Internal Interfaces

- Otel collector sidecars forward stdout to Fluent Bit, which batches into Kafka topics `logs.<env>.<service>` and writes to OpenSearch indices `logs.<env>.<service>-YYYY.MM.DD`.
- When `logging.immutable_sink.enabled=true`, Fluent Bit forks the stream to the immutable WORM bucket alongside metadata captured by Audit §4.
- Seal runner `ops/audit/seal_runner.py` consumes immutable batches hourly; verification job `ops/audit/verify_seal_chain.py` feeds Audit §5.

______________________________________________________________________

## 4) State Management (binding) {#4-log-schema--redaction}

**Purpose:** Capture persistent telemetry assets—schemas, buffers, indices, and retention policies. **|**
**Contract:** Maintain 12-hour local buffers, monthly OpenSearch/`audit_event` partitions, ILM policies for hot→warm→cold tiers, and immutable retention per jurisdiction. **|**
**State:** Otel config maps, Fluent Bit buffers, Kafka topics, OpenSearch ILM policies, WORM storage, `spec/schemas/log_record.schema.json`, `spec/schemas/judgment_event.schema.json`. **|**
**Failures & handling:** Partition rotation failures raise `audit_partition_rotation_failed_total`; ILM drift triggers `logging_retention_violation_total`; schema drift blocked by CI and RB-LOG-007. **|**
**Observability:** Dashboards “Logging Retention” and “Immutable Sink”. **|**
**Breadcrumbs:** ILM configs `infra/logging/opensearch/ilm/`, partition script `ops/db/rotate_partitions.py`, schema tests `tests/logging/test_schema_validation.py`. **|**
**References:** Audit §4, Settings §7.2, Audit §5 seals.

### 4.1 Schema & redaction assets

- `log_record@1` and `judgment_event@1` define canonical fields (`ts`, `service`, `trace_id`, etc.).
- Redaction denylist lives in `packages/udocket_core/logging/redaction.py`; CI fuzz tests enforce coverage.

### 4.2 Retention policies

- Staff/API successes sampled 10% (90-day hot, 365-day cold); 4xx/5xx unsampled.
- LLM evidence logs retained 365 days (HIPAA 180 days) with excerpt suppression.
- Synthetic and audit streams unsampled and mirrored immutably.

______________________________________________________________________

## 5) Failure Modes (binding)

**Purpose:** Outline failure scenarios and required remediation. **|**
**Contract:** Fail closed on ingest drops, immutable lag, or redaction violations; throttle gracefully on budget exhaustion. **|**
**State:** Incident runbooks RB-LOG-007, RB-TRACE-CORR, RB-COST, RB-MASK; PagerDuty services `observability-ingest`, `observability-trace`. **|**
**Failures & handling:** See scenario list below. **|**
**Observability:** Incident metrics `logging_incident_total`, `mttr_minutes`. **|**
**Breadcrumbs:** Runbooks in `../ops/runbooks.md`. **|**
**References:** Audit §5, Settings §7.2, TDD §12 summary.

- `logging_ingest_lag_seconds > 30` → scale collectors, drain queues, validate mirror (RB-LOG-007).
- Non-zero `logging_drop_rate_pct` → investigate Fluent Bit/Kafka, replay buffers.
- Immutable lag (`audit_worm_lag_seconds`) → pause approvals, work with Audit §5.
- Redaction violation (`logging_neverlog_violation_total`) → RB-MASK + Security Sev-1.
- Sampling drift (`trace_sampling_drift_total`) → RB-TRACE-CORR to recalibrate.
- Budget breach (`logging_volume_budget_violation_total`) → RB-COST adjusts sampling and informs FinOps.

______________________________________________________________________

## 6) Observability (binding) {#6-observability--quality}

**Purpose:** Ensure ingest, trace correlation, immutable mirroring, and cost posture stay measurable and alertable. **|**
**Contract:** Prometheus rules, dashboards, synthetics, and alert routes enumerated here are mandatory; any removal triggers RB-LOG-007 until coverage is restored. **|**
**State:** Prometheus rules (`infra/monitoring/logging-prometheus-rules.yaml`), Grafana views (“Logging Pipeline”, “Trace Correlation”, “Logging Cost”, “Immutable Sink”), synthetics (`synthetics/logging_ingest.yaml`), and seal verifiers. **|**
**Failures & handling:** Gaps escalate through RB-LOG-007 or linked runbooks (RB-AUDIT-004, RB-TRACE-CORR, RB-COST) before gates reopen. **|**
**Observability:** Metrics `logging_ingest_lag_seconds`, `logging_drop_rate_pct`, `logging_spool_utilization_pct`, `trace_sampling_rate`, `audit_worm_lag_seconds` feed burn-rate alerts and dashboards. **|**
**Breadcrumbs:** Monitoring configs `infra/monitoring/logging-prometheus-rules.yaml`, dashboards `infra/observability/dashboards/logging_*.json`, synthetic definitions `synthetics/logging_ingest.yaml`. **|**
**References:** Audit spec §5, Settings spec §7.2, TDD §12 Observability overview.

### 6.1 SLOs & Targets (binding)

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

## 7) Security & Compliance (binding) {#6-access-control--auditing}

**Purpose:** Prevent sensitive data leakage and enforce authorized access. **|**
**Contract:** Apply “never log” scrubber, enforce WebAuthn + justification for log queries, respect immutable mirroring, and limit client telemetry to anonymized aggregates. **|**
**State:** Redaction denylist, access roles (`observability.reader|engineer|auditor`), audit tables `log_query_audit`, client telemetry toggles, immutable sink settings. **|**
**Failures & handling:** Redaction violations escalate to Security; unauthorized access attempts log `LOG_ACCESS_DENIED` and trigger RB-MASK; mirror drift handled per Audit §5. **|**
**Observability:** Dashboards “Log Access” and “Portal Telemetry”, metrics `logging_neverlog_violation_total`, `logging_access_denied_total`, `client_logging_mode_violation_total`. **|**
**Breadcrumbs:** Access middleware `apps/platform/logging/access.py`, telemetry modules `apps/platform/ui/telemetry.py`, Audit spec §4/§5. **|**
**References:** Settings §7.2 (`logging.redaction.*`, `logging.access.roles[]`, `portal.logging.enabled`), Audit §4, Audit §5.

### 7.1 Access control

- Log queries require WebAuthn step-up, purpose entry, and emit `LOG_QUERY` events.
- Bulk exports demand dual approval and produce `LOG_EXPORT` artifacts with SHA-256 manifests.

### 7.2 Data minimization

- Scrubber removes auth headers, tokens, signed URLs, PHI, transcripts/exhibits.
- LLM evidence logs confirm provider “no training/no logging” flags via LLM Registry §6.

### 7.3 Client telemetry posture {#42-client--portal-telemetry}

- Portal WebVitals capture anonymized aggregates; console capture disabled except for time-boxed incidents with ticket references cleared within 24h.

______________________________________________________________________

## 8) Operational Notes (normative)

**Purpose:** Summarize day-2 operations, rollout cadence, and automation. **|**
**Contract:** Keep helm charts current, execute quarterly seal/ingest drills, and document staffing plans. **|**
**State:** Helm releases, Terraform modules, runbook catalog entries, automation scripts `ops/logging/*`. **|**
**Failures & handling:** Drill gaps escalate to SRE leadership; rollout failures revert via `helm rollback` recipes documented in RB-LOG-007. **|**
**Observability:** Deployment dashboards, runbook execution trackers, release checklist metrics. **|**
**Breadcrumbs:** Helm chart `infra/logging/helm/`, deployment pipeline configs `.buildkite/pipelines/logging.yml`, runbooks `../ops/runbooks.md`. **|**
**References:** Platform Runtime §3, Audit §5, ADR-0006.

### 8.1 Operational Posture (binding)

**Purpose:** Define on-call coverage and readiness. **|**
**Contract:** Observability on-call must respond within 15 minutes, maintain runbooks, and execute quarterly drills covering ingest drop, trace drift, and immutable lag. **|**
**State:** PagerDuty schedules `observability-ingest`, staffing rosters in `ops/oncall/observability.md`. **|**
**Failures & handling:** Coverage gaps escalate to SRE director and trigger staffing action items. **|**
**Observability:** Staffing dashboard “Pager Health”, metric `oncall_ack_latency_seconds`. **|**
**Breadcrumbs:** Rota configs `ops/oncall/`, runbooks RB-LOG-007, RB-TRACE-CORR. **|**
**References:** Incident management policy, Platform Runtime §3.

### 8.2 Incident Triggers (binding)

**Purpose:** Enumerate signals that declare incidents. **|**
**Contract:** Trigger Sev-2 for ingest lag >30s, any non-zero drop rate, immutable lag (`audit_worm_lag_seconds`), or redaction violation; trigger Sev-3 for sampling drift or cost overrun. **|**
**State:** Alert definitions in `infra/monitoring/logging-prometheus-rules.yaml`, PagerDuty services `observability-ingest`, `observability-trace`, `observability-cost`. **|**
**Failures & handling:** Alert review weekly to prune false positives; escalate missing triggers to SRE leadership. **|**
**Observability:** Alert dashboard “Logging Alerts”, incident review cadence monthly. **|**
**Breadcrumbs:** Prometheus alert rules, PagerDuty configs, incident templates. **|**
**References:** Runbooks RB-LOG-007, RB-TRACE-CORR, RB-COST.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Ensure playbooks stay current and executed. **|**
**Contract:** Runbooks RB-LOG-007, RB-TRACE-CORR, RB-COST, RB-MASK reviewed quarterly; ingest/seal drills recorded as `AUDIT_DRILL` artifacts. **|**
**State:** Runbook repo `docs/src/ops/runbooks/`, drill evidence under `ops/logging/drills/<date>/`. **|**
**Failures & handling:** Missed reviews trigger compliance ticket and block release sign-off. **|**
**Observability:** Drill completion dashboard, metric `logging_drill_overdue_total`. **|**
**Breadcrumbs:** Runbook catalog, drill scripts `ops/logging/drill_runner.py`. **|**
**References:** Audit §5, Compliance policy.

#### 8.3.1 Runbook Index

- `logging_ingest_lag_seconds` → RB-LOG-007  
- `trace_sampling_drift_total` → RB-TRACE-CORR  
- `logging_volume_budget_violation_total` → RB-COST  
- `logging_neverlog_violation_total` → RB-MASK

#### 8.3.2 Primary Runbooks

**Purpose:** Summarize top-tier playbooks. **|**
**Contract:** Maintain up-to-date steps, owners, evidence collection. **|**
**State:** RB-LOG-007 (ingest triage), RB-TRACE-CORR (trace drift), RB-COST (budget control), RB-MASK (redaction incident). **|**
**Failures & handling:** Stale runbooks flagged during quarterly review; blocking for release until updated. **|**
**Observability:** Runbook freshness tracker. **|**
**Breadcrumbs:** `docs/src/ops/runbooks/logging/`. **|**
**References:** Incident governance policy.

#### 8.3.3 Drill Cadence & Evidence

- Quarterly ingest + seal tabletop; evidence stored under `ops/logging/drills/<date>/ingest.md`.
- Semi-annual trace correlation live drill with synthetic failure.
- Annual cost-control drill verifying sampling overrides and alerting.

### 8.4 Migrations & Backfills (informative)

**Purpose:** Capture schema/data migrations and replay tooling. **|**
**Contract:** `ops/logging/backfill_registration.py` handles registration catalog updates; OpenSearch ILM adjustments require Architecture approval and rollback plan. **|**
**State:** Migration scripts `ops/logging/migrations/`, ILM templates, replay tooling for Kafka topic reprocessing. **|**
**Failures & handling:** Failed migration detected via `logging_migration_failure_total`; rollback instructions captured in RB-LOG-007 appendix. **|**
**Observability:** Migration dashboard tracks progress, errors, and throughput. **|**
**Breadcrumbs:** Migration scripts, ILM configs, change-management tickets. **|**
**References:** ADR-0006, change-management SOP.

### 8.5 Operational Workflows (informative)

**Purpose:** Describe recurring operational tasks. **|**
**Contract:** Weekly registration diff review, monthly alert tuning, quarterly cost budget review, annual immutable sink validation. **|**
**State:** Checklists in `ops/logging/workflows/`, automated reminders via Opsgenie. **|**
**Failures & handling:** Missed workflow triggers ticket `OBS-WORKFLOW-MISS` and blocks release if >7 days overdue. **|**
**Observability:** Workflow dashboard showing completion SLAs. **|**
**Breadcrumbs:** Workflow docs, automation scripts, staffing rosters. **|**
**References:** Observability guild charter, compliance calendar.

______________________________________________________________________

______________________________________________________________________

## 9) Dependencies (informative)

**Purpose:** Highlight upstream/downstream systems required for observability. **|**
**Contract:** Dependencies must remain compatible; changes require coordination and doc updates. **|**
**State:** Otel collectors (Kubernetes DaemonSets), Fluent Bit images, Kafka cluster, OpenSearch domain, immutable storage, metrics stack, Settings, Audit seal service. **|**
**Failures & handling:** Dependency outages escalate via RB-LOG-007 and relevant service runbooks; maintain compatibility matrices. **|**
**Observability:** Dependency health dashboards (Kafka, OpenSearch, storage). **|**
**Breadcrumbs:** Infra repos `infra/logging/`, `infra/kafka/`, `infra/opensearch/`, SLOs `infra/observability/dashboards/logging_pipeline.json`. **|**
**References:** Platform Runtime §3, Audit §5, Worker Cluster §3.6.

______________________________________________________________________

## 10) References

- Technical Design Document §12 (summary)  
- Settings Service specification — `../services/settings.md` (§7.2 telemetry keys)  
- Audit & Evidence specification — `../services/audit.md`  
- Guardian specification — `../services/guardian.md` §7  
- LP Engine specification — `../services/lp-engine.md` §5  
- Ops runbook catalog — `../ops/runbooks.md` (RB-LOG-007, RB-TRACE-CORR, RB-COST, RB-MASK)  
- ADR index — `../adr/README.md` (ADR-0004 logging posture, ADR-0006 immutable sink)
