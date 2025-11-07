---
title: uDocket — Billing & Subscriptions Service Specification
subtitle: Account Entitlements, Usage Metering, and Revenue Controls
author:
  - Revenue Platform Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Engineering
  - Finance Operations
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - Compliance Lead
  - Finance Controller
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
  - <header class="page-header">uDocket — Billing & Subscriptions Service Specification <br>
    Account Entitlements, Usage Metering, and Revenue Controls</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Revenue Platform Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Engineering; Finance Operations |
| Reviewers | Compliance Lead; Finance Controller |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Describes the Billing & Subscriptions service that governs price plans, entitlements, usage metering, invoicing, delinquency detection, and FinOps hooks referenced in TDD §3.9 (FinOps guardrails) and §14.4 (billing retention). Covers integration with external billing provider, portal subscription UI, and Operations runbooks.
- **Structure:** Follows standard sections covering charter, responsibilities, API contracts (internal REST + billing provider webhooks), state management, resiliency, observability, security/compliance, operations, dependencies, and references.
- **Maintenance:** Run `python -m doc_tools.manage_docs --lint docs/customer/billing-subscriptions.md docs/overview/tdd.md docs/tdd_modularization.md` before submitting. Contract changes must update TDD billing tables and Ops runbooks `RB-BILLING-*`.
- **Change protocol:** Changes to pricing plans, usage quotas, or delinquency behaviour require Finance + Compliance approval and updated Settings keys (`billing.*`). Schema changes require migrations plus doc updates.
- **References:** TDD §3.9 (FinOps), §4 (tenant holds), §14.4 (billing records), Ops runbooks `RB-BILLING-DELINQUENCY`, Settings spec §5 (`billing.*`), Accounts & Tenants spec.
- **Contacts:** Finance Ops (billing owner), Platform Engineering (service implementation), escalation `#ops-billing`, on-call `billing-oncall@`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Manage subscription lifecycles, entitlements, and billing records to support revenue recognition and enforce platform quotas. **|**
**Contract:** Ensure active tenants have valid plans, usage metering is immutable, invoices reconcile with Finance, and delinquency states propagate to Accounts & Tenants for suspension. **|**
**State:** Owns `billing_plan`, `billing_subscription`, `billing_invoice`, `usage_meter`, and `billing_event` ledgers. **|**
**Failures & handling:** Provider outages, webhook signature mismatches, or metering drift trigger self-healing jobs and billing on-call (`RB-BILLING-*`). **|**
**Observability:** Metrics `billing_subscription_active_total`, `billing_invoice_overdue_total`, `usage_meter_lag_seconds`, dashboards “Billing Health”, “Usage Metering”. **|**
**Breadcrumbs:** Implementation `apps/platform/billing/service.py`, metering jobs `apps/platform/billing/metering.py`, provider adapters `apps/platform/billing/providers/`, tests `tests/platform/billing/`. **|**
**References:** TDD §3.9, §4.2, §14.4.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Define the behaviours Billing & Subscriptions must own. **|**
**Contract:** Price plan management, entitlement enforcement, metering, invoicing, delinquency detection. **|**
**State:** Subscription + metering tables, invoice records, provider reconciliation. **|**
**Failures & handling:** Identify failure points and runbook paths. **|**
**Observability:** Metrics, dashboards, audits verifying responsibilities. **|**
**Breadcrumbs:** Implementation modules, tests, scripts. **|**
**References:** TDD §3.9, §4.2, §14.4, Settings spec.

### 2.1 Plan catalog & pricing (binding)

- **Contract:** Plans stored in `billing_plan` with immutable IDs, currency, price, included usage, overage pricing. Updates require versioning (`plan_version`), backfilled Settings diff, and Finance approval. **|**
- **State:** Plan catalogue with effective dates, marketing descriptors. **|**
- **Observability:** Metric `billing_plan_active_total`; audit log `BILLING_PLAN_UPDATED`. **|**
- **Failures & handling:** Conflicting plan updates blocked; require migration path. **|**
- **Breadcrumbs:** Admin UI `apps/platform/billing/admin.py`, tests `tests/platform/billing/test_plan_catalog.py`. **|**

### 2.2 Subscription lifecycle (binding)

- **Contract:** Subscriptions progress `PENDING_ACTIVATION → ACTIVE → GRACE → SUSPENDED → CANCELLED`. Aligns with Accounts & Tenants holds. Billing ensures no suspended tenant remains `ACTIVE` >24h. **|**
- **State:** `billing_subscription` with plan, start/end dates, payment method references. **|**
- **Observability:** Metrics `billing_subscription_active_total`, `billing_subscription_grace_total`. **|**
- **Failures & handling:** Failed renewals escalate to `RB-BILLING-DELINQUENCY`; after grace expiry, Accounts service receives suspension event. **|**
- **Breadcrumbs:** Subscription service `apps/platform/billing/subscriptions.py`, tests `tests/platform/billing/test_subscriptions.py`. **|**

### 2.3 Usage metering (binding)

- **Contract:** Metering pipeline captures agent consumption (minutes, tokens, storage) and portal seats. Data append-only in `usage_meter`; nightly job reconciles with providers. **|**
- **State:** `usage_meter` rows keyed by tenant, feature, timeframe. **|**
- **Observability:** Metrics `usage_meter_lag_seconds`, `usage_meter_discrepancy_total`. **|**
- **Failures & handling:** Reconciler replays events; persistent drift triggers `RB-BILLING-METERING`. **|**
- **Breadcrumbs:** Metering tasks `apps/platform/billing/metering.py`, tests `tests/platform/billing/test_metering.py`. **|**

### 2.4 Invoicing & payments (binding)

- **Contract:** Generates invoices via external billing provider (Stripe). Invoices must reconcile with usage; each invoice carries hash of source usage lines. **|**
- **State:** `billing_invoice`, `billing_payment` tables with provider IDs, status, PDF references stored in Artifact Store `docs/`. **|**
- **Observability:** Metrics `billing_invoice_overdue_total`, `billing_payment_failed_total`. **|**
- **Failures & handling:** Provider outage or signature mismatch triggers `RB-BILLING-PAYMENT`. **|**
- **Breadcrumbs:** Invoice job `apps/platform/billing/invoicing.py`, tests `tests/platform/billing/test_invoicing.py`. **|**

### 2.5 Delinquency detection (binding)

- **Contract:** Once invoice overdue > grace period, emit `BILLING_DELINQUENT` event, notify Accounts service to suspend tenant. Restoring payment clears suspension with explicit audit event. **|**
- **State:** `billing_delinquency` ledger with reason, actions taken. **|**
- **Observability:** `billing_invoice_overdue_total`, `billing_delinquency_active_total`. **|**
- **Failures & handling:** False positives require Finance override and doc updates; tracked via `RB-BILLING-DELINQUENCY`. **|**
- **Breadcrumbs:** Delinquency monitor `apps/platform/billing/delinquency.py`, tests `tests/platform/billing/test_delinquency.py`. **|**

______________________________________________________________________

## 3) API Contract

**Purpose:** Capture REST APIs, provider integrations, and event streams. **|**
**Contract:** Provide admin APIs for managing plans/subscriptions, webhook endpoints for billing provider, event fan-out to Accounts. **|**
**State:** API interactions update subscription tables and audits. **|**
**Failures & handling:** Document error codes/retry semantics. **|**
**Observability:** API metrics and logs. **|**
**Breadcrumbs:** Views, serializers, webhook handlers, tests. **|**
**References:** Platform Runtime §3.3, Accounts & Tenants §3, Settings §5 (`billing.*`).

### 3.1 External Interfaces (binding)

- `POST /api/admin/billing/plans/` — Create plan version; returns plan ID. Errors: `VALIDATION_ERROR`, `CONFLICT`, `POLICY_BLOCK` (Finance approval missing). **|**
- `POST /api/admin/billing/subscriptions/<subscription_id>/change-plan/` — Schedules plan change next billing cycle. **|**
- `POST /api/admin/billing/subscriptions/<subscription_id>/cancel/` — Cancels at period end or immediately (with reason). **|**
- **Breadcrumbs:** `apps/platform/billing/views.py`, tests `tests/platform/billing/test_admin_api.py`. **|**

### 3.2 Internal Interfaces (binding)

- `/webhooks/billing/payment_succeeded` and `/webhooks/billing/payment_failed` accept Stripe events (Canada region). Requests validated via signing secret; mismatches return 400. **|**
- `/webhooks/billing/customer_updated` refreshes billing contact details. **|**
- Webhook failures retried with exponential backoff; security logs capture attempts. **|**
- **Breadcrumbs:** `apps/platform/billing/providers/stripe/webhooks.py`, tests `tests/platform/billing/test_stripe_webhooks.py`. **|**

### 3.3 API Error Codes (binding)

**Purpose:** Capture Billing-specific error codes beyond the platform catalog. **|**
**Contract:** Current APIs emit only shared platform codes; this catalog stays empty until billing introduces dedicated codes. **|**
**State:** Catalog stored in `docs/customer/billing-subscriptions/error_codes.yaml`. **|**
**Failures & handling:** Callers rely on Platform Runtime §3.3 behaviours; unknown codes trigger alerts. **|**
**Observability:** Metric `billing_api_error_unknown_total` watches for unmapped codes. **|**
**Breadcrumbs:** API middleware `apps/platform/billing/api_errors.py`, tests `tests/platform/billing/test_api_errors.py`. **|**
**References:** Platform Runtime §3.3, Accounts & Tenants §3.1.

> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#billing-subscriptions-service)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Subscription state changed since the caller fetched it (pending change or grace period overlap). | Refresh subscription state, resolve pending changes, and resubmit with the latest version. |
| `POLICY_BLOCK` | Finance approval or compliance policy prevented plan activation or subscription change. | Obtain required Finance/Compliance approval, update Settings overrides, then retry. |
| `PROVIDER_DEGRADED` | External billing provider (Stripe) reported degraded health or webhook replay backlog. | Pause billing mutations, monitor provider status, and resume once health recovers; follow RB-BILLING-PAYMENT. |
| `VALIDATION_ERROR` | Plan or subscription payload failed schema validation (pricing tiers, effective dates, billing contact data). | Correct the request body and rerun once validation passes; reference plan catalog guardrails. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | Yes | billing_api_error_total<br>billing_subscription_conflict_total |
| `POLICY_BLOCK` | 403 | Yes | billing_api_error_total<br>billing_policy_block_total |
| `PROVIDER_DEGRADED` | 503 | Yes | billing_api_error_total<br>billing_payment_failed_total |
| `VALIDATION_ERROR` | 400 | No | billing_api_error_total<br>billing_plan_update_total |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

### 3.4 Events & integrations (binding)

- Emits events `BILLING_SUBSCRIPTION_UPDATED`, `BILLING_DELINQUENT`, `BILLING_PAYMENT_RECEIVED` on Jobs SSE and Celery signals for Accounts service. **|**
- FinOps ingestion exports to data warehouse nightly (Appendix L). **|**
- **Breadcrumbs:** `apps/platform/events/billing.py`, tests `tests/platform/events/test_billing_events.py`. **|**

______________________________________________________________________

## 4) State Management (binding)

**Purpose:** Describe how billing data persists and synchronizes across systems. **|**
**Contract:** Guarantee ledger immutability, append-only audit logs, and canonical usage records for reconciliation. **|**
**State:** Billing plans, subscriptions, invoices, payments, usage meter partitions, delinquency ledgers. **|**
**Failures & handling:** Drift reconciled nightly; audit tables enforce signature checks; DSAR/retention rules applied per Finance policy. **|**
**Observability:** Metrics `billing_state_reconcile_total`, dashboards “Billing State Health”. **|**
**Breadcrumbs:** ORM models `apps/platform/billing/models.py`, migrations `apps/platform/migrations/`, warehouse export scripts `ops/finops/export_usage.py`. **|**
**References:** TDD §3.9, §14.4, Accounts & Tenants §4.2.

- All billing tables use Canadian-region Postgres cluster with row-level security tied to Finance/Platform roles. **|**
- Sensitive payment metadata stored via provider tokens; no raw card data persisted. **|**
- Audit tables `billing_event`, `billing_invoice_audit` append-only with signature checks. **|**
- Usage meter uses partitioned tables by month, retention per Finance policy (7 years). **|**
- Tenant status sync: Accounts service caches subscription state; updated via events + nightly reconciliation job. **|**

______________________________________________________________________

## 5) Failure Modes (binding)

**Purpose:** Outline default failure handling for billing workflows. **|**
**Contract:** Fail closed on provider outages, signature mismatches, or currency conflicts while keeping audit evidence. **|**
**State:** Retry queues, delinquency ledgers, webhook replay cache. **|**
**Failures & handling:** Runbooks `RB-BILLING-*` govern response; overrides require Finance approval. **|**
**Observability:** Alerts `billing_invoice_overdue_total`, `billing_payment_failed_total`, `usage_meter_lag_seconds`. **|**
**Breadcrumbs:** Runbooks `docs/ops/runbooks/billing/*.md`, incident retros `ops/billing/incidents/*.md`. **|**
**References:** TDD §3.9 FinOps guardrails, Appendix I controls map.

- **Provider outage:** Fallback to queuing invoices; escalate to Finance via `RB-BILLING-PAYMENT`. **|**
- **Webhook replay:** Detect via idempotency keys; duplicates ignored. **|**
- **Metering lag:** When `usage_meter_lag_seconds > 900`, throttle new invoices and alert FinOps. **|**
- **Delinquency false positive:** Flag via manual override, audit in `billing_delinquency_override`. **|**
- **Currency mismatch:** Block invoice generation if currency mismatch detected between plan and provider. **|**

______________________________________________________________________

## 6) Observability (binding)

**Purpose:** Provide telemetry coverage required for billing health. **|**
**Contract:** Monitor subscription lifecycle, delinquency, metering pipelines, and provider integrations via shared dashboards. **|**
**State:** Metrics, logs, audit events, warehouse exports. **|**
**Failures & handling:** Alert fatigue controlled with FinOps thresholds; unknown metrics block releases. **|**
**Observability:** Dashboards “Billing Health”, “Usage Metering”, “Stripe Webhooks”. **|**
**Breadcrumbs:** Metrics module `apps/platform/billing/metrics.py`, dashboards `infra/monitoring/billing_dashboard.json`. **|**
**References:** Observability spec §4, FinOps handbook.

- Metrics: `billing_subscription_active_total`, `billing_invoice_overdue_total`, `billing_payment_failed_total`, `usage_meter_lag_seconds`, `billing_delinquency_active_total`. **|**
- Logs: Structured events `BILLING_*`, webhook audit logs with signature validity, invoice hash records. **|**
- Dashboards: “Billing Health”, “Usage Metering”, “Stripe Webhooks”. **|**
- Alerts: Burn-rate alerts on failed payments, webhook failures, metering lag. **|**

### 6.1 SLOs & Targets (binding)

**Purpose:** Track measurable objectives for billing operations. **|**
**Contract:** Maintain ≤2% overdue invoices (P95 clearance < 48 h), metering lag < 15 minutes P95, webhook success rate ≥99.5%. **|**
**State:** Prometheus rules `infra/monitoring/billing-slo-rules.yaml`, FinOps dashboards. **|**
**Failures & handling:** Breaches trigger RB-BILLING-DELINQUENCY or RB-BILLING-METERING; releases paused until resolved. **|**
**Observability:** Burn-rate alerts `billing_invoice_slo_burn`, `billing_metering_slo_burn`, webhook alerts `billing_webhook_error_burn`. **|**
**Breadcrumbs:** SLO config `infra/monitoring/billing_slo.json`, tests `tests/integration/test_billing_slo.py`. **|**
**References:** TDD §3.9, FinOps dashboards.

______________________________________________________________________

## 7) Security & Compliance (binding)

**Purpose:** Describe billing security, PCI, and compliance obligations. **|**
**Contract:** Enforce tokenized payments, regional storage, dual approval for plan changes, and RFC 8594 deprecation guidance. **|**
**State:** Secrets vault, PCI documentation, delinquency overrides, audit trails. **|**
**Failures & handling:** PCI scope breaches escalate immediately; delinquency overrides logged with Finance approvals. **|**
**Observability:** Security alerts `billing_security_violation_total`, audit logs, policy dashboards. **|**
**Breadcrumbs:** IAM configs `infra/terraform/billing`, compliance docs `ops/compliance/billing/*.md`. **|**
**References:** Settings keys `billing.*`, Accounts & Tenants §7, [RFC 8594](https://www.rfc-editor.org/rfc/rfc8594).

- PCI scope: Stripe handles card data; platform stores only tokens. Annual PCI-DSS SAQ documented in Appendix P. **|**
- Residency: Billing data stored in Canada region; exports sanitized for cross-border data warehouse with Finance approval. **|**
- Access: Finance roles gated by Identity spec; actions require dual approval for plan changes. **|**
- Audit: Invoices and subscription changes hashed and stored in Artifact Store `docs/` with appended metadata. **|**
- Compliance: Supports deprecation headers per [RFC 8594](https://www.rfc-editor.org/rfc/rfc8594) when APIs change. **|**

______________________________________________________________________

## 8) Operational Notes (binding)

**Purpose:** Summarize operating model, runbooks, and drill cadence for billing. **|**
**Contract:** Maintain on-call coverage, runbook freshness, and drill evidence before promoting changes. **|**
**State:** Runbooks, drill records, automation scripts, FinOps evidence. **|**
**Failures & handling:** Runbook drift or missing evidence blocks releases; FinOps variance escalates. **|**
**Observability:** Runbook catalog, drill scheduler, FinOps dashboards. **|**
**Breadcrumbs:** Runbooks `docs/ops/runbooks/billing/*.md`, automation `scripts/ops/billing_*.py`, FinOps reports `ops/finops/reports/`. **|**
**References:** Ops catalog, FinOps handbook.

- Runbooks: `RB-BILLING-DELINQUENCY`, `RB-BILLING-PAYMENT`, `RB-BILLING-METERING`, `RB-BILLING-PLAN-ROLLBACK`. **|**
- Drills: Quarterly delinquency tabletop, semi-annual invoice reconciliation dry run, webhook failure simulation. Evidence `ops/billing/drills/<date>/`. **|**
- Automation: `scripts/ops/billing_reconcile.py`, `scripts/ops/metering_backfill.py`. **|**
- On-call: `billing-oncall@`, Slack `#ops-billing`, escalation to Finance leadership for incidents > Sev2. **|**

### 8.1 Operational Posture (binding)

**Purpose:** Capture staffing expectations and maintenance windows. **|**
**Contract:** Finance Ops primary on-call with Platform Engineering secondary; acknowledge within 5 minutes, mitigation within 30 minutes; maintenance window Sunday 04:00–06:00 PT for invoicing jobs. **|**
**State:** Rosters `ops/billing/rota.md`, maintenance calendar `ops/change/billing.ics`, readiness checklist `ops/billing/checklists/operational_posture.md`. **|**
**Failures & handling:** Coverage gaps escalate to Finance leadership; readiness checklist enforced before releases. **|**
**Observability:** PagerDuty analytics, staffing dashboard “Billing Ops Posture”. **|**
**Breadcrumbs:** Staffing policy `ops/billing/policies/staffing.md`, incident response guide `docs/ops/runbooks/billing/README.md`. **|**
**References:** Ops catalog, Appendix S roles.

### 8.2 Incident Triggers (binding)

**Purpose:** Define alerts that declare billing incidents. **|**
**Contract:** Alerts `billing_payment_failed_total`, `billing_invoice_overdue_total`, `usage_meter_lag_seconds`, and Stripe webhook failure rates > threshold must page on-call; FinOps anomaly detection triggers escalate. **|**
**State:** Alert definitions `infra/monitoring/billing-alerts.yaml`, anomaly detector `scripts/finops/check_anomaly.py`. **|**
**Failures & handling:** Alert tuning handled jointly by SRE and Finance; missed alerts reviewed in postmortems. **|**
**Observability:** Grafana “Billing Incident Triggers”, FinOps anomaly dashboard. **|**
**Breadcrumbs:** Alert rules, PagerDuty services, FinOps anomaly dashboards. **|**
**References:** §6 Observability, RB-BILLING-DELINQUENCY, RB-BILLING-PAYMENT.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Ensure runbooks and drills stay current. **|**
**Contract:** Alerts map to RB-BILLING-* identifiers; drills executed per cadence with evidence recorded. **|**
**State:** Runbooks `docs/ops/runbooks/billing/*.md`, drill evidence `ops/billing/drills/<date>/`, automation `scripts/ops/billing_*.py`. **|**
**Failures & handling:** Runbook drift or missing evidence blocks releases until resolved; FinOps variance escalates. **|**
**Observability:** Runbook catalog output, drill scheduler metrics, FinOps governance dashboard. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler, Slack `#ops-billing`. **|**
**References:** RB-BILLING-DELINQUENCY, RB-BILLING-PAYMENT, RB-BILLING-METERING, RB-BILLING-PLAN-ROLLBACK.

#### 8.3.1 Runbook Index (informative)

| Runbook code | Scenario | Notes |
| --- | --- | --- |
| `RB-BILLING-DELINQUENCY` | Delinquency surge response, tenant suspension coordination, finance communications | Evidence stored in `ops/billing/drills/<date>/delinquency.md` |
| `RB-BILLING-PAYMENT` | Payment provider outage, manual reconciliation, customer notifications | Includes provider escalation contacts |
| `RB-BILLING-METERING` | Usage metering backlog remediation, replay scripts, FinOps validation | Leverages `scripts/ops/metering_backfill.py` |
| `RB-BILLING-PLAN-ROLLBACK` | Plan catalog rollback, customer entitlement adjustments, audit logging | Requires Finance approval + audit trail |

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarize the key playbooks responders execute during incidents. **|**
**Contract:** Keep runbooks versioned, linked to alerts, and reviewed quarterly. **|**
**State:** Markdown in `docs/ops/runbooks/billing/*.md`, automation scripts `scripts/ops/billing_*.py`. **|**
**Failures & handling:** Stale runbooks flagged by docs lint `runbook_catalog_stale_total`. **|**
**Observability:** Governance dashboard, runbook catalog output. **|**
**Breadcrumbs:** Runbook files, automation scripts, incident templates. **|**
**References:** RB-BILLING-DELINQUENCY, RB-BILLING-PAYMENT, RB-BILLING-METERING, RB-BILLING-PLAN-ROLLBACK.

- `RB-BILLING-DELINQUENCY` — Delinquency surge response, tenant suspension coordination, finance communications. **|**
- `RB-BILLING-PAYMENT` — Payment provider outage, manual reconciliation, customer notifications. **|**
- `RB-BILLING-METERING` — Usage metering backlog remediation, replay scripts, FinOps validation. **|**
- `RB-BILLING-PLAN-ROLLBACK` — Plan catalog rollback, customer entitlement adjustments, audit logging. **|**

#### 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly delinquency tabletop verifying tenant suspension handoff; evidence stored in `ops/billing/drills/<date>/delinquency.md`. **|**
- Semi-annual invoice reconciliation dry run with synthetic data; evidence includes diff reports and Finance sign-off. **|**
- Quarterly webhook failure simulation capturing replay metrics and provider engagement notes. **|**
- Drill and incident evidence archived under `ops/billi../data/<date>/`; Grafana snapshots and FinOps exports attached. **|**
- Compliance reviews audit evidence quarterly; gaps tracked via `billing_evidence_gap_total`. **|**
- Docs lint monitors for missing folders and blocks merges when absent. **|**

### 8.4 Migrations & Backfills (binding)

**Purpose:** Capture schema/data migrations, backfills, and replay tooling required to maintain billing. **|**
**Contract:** Execute migrations via `scripts/ops/billing_migrate.py`, record before/after hashes, and retain rollback checkpoints aligned with Finance approvals. **|**
**State:** Migration manifests `ops/billing/migrations/`, warehouse reconciliation scripts, change calendar entries. **|**
**Failures & handling:** Failed migrations roll back using database snapshots; incidents recorded with Finance ops evidence. **|**
**Observability:** Migration dashboard “Billing Migrations” plus alerts `billing_migration_failure_total`. **|**
**Breadcrumbs:** Migration scripts, change tickets, ADR-0002 sunset guidance. **|**
**References:** TDD §14.4, FinOps handbook.

### 8.5 Operational Workflows (binding)

**Purpose:** Describe recurring operational tasks such as delinquency reviews and metering audits. **|**
**Contract:** Weekly delinquency sweep, monthly invoice reconciliation, quarterly metering backfill review executed with Finance sign-off. **|**
**State:** Workflow checklists `ops/billing/workflows/*.md`, automation outputs `ops/finops/reports/*.csv`. **|**
**Failures & handling:** Missed workflows trigger alert `billing_workflow_overdue_total` and block releases until resolved. **|**
**Observability:** Workflow dashboard, docs lint, FinOps anomaly monitors. **|**
**Breadcrumbs:** Workflow docs, automation scripts, staffing rosters. **|**
**References:** Compliance playbooks, Ops catalog.

## 9) Dependencies (binding)

**Purpose:** List core upstream/downstream services impacting billing flows. **|**
**Contract:** Track responsibilities and change coordination expectations with each dependency. **|**
**State:** Service catalog entries, integration manifests, FinOps data contracts. **|**
**Failures & handling:** Dependency incidents coordinated via referenced runbooks. **|**
**Observability:** Dependency dashboards overlay health metrics. **|**
**Breadcrumbs:** Platform Runtime catalog, Ops runbook index, FinOps integration docs. **|**
**References:** Platform Runtime §3, Settings §5 (`billing.*`), Accounts & Tenants §4.

| Dependency | Responsibility | Notes |
| --- | --- | --- |
| Accounts & Tenants | Tenant status, suspension propagation | Subscription state drives tenant holds |
| Settings Registry | Plan availability, quotas, billing toggles | Keys `billing.*`, `tenancy.*` |
| Artifact Store | Stores invoices, statements, exports | Deliverables hashed + referenced |
| Stripe (or successor) | Payment processing, invoice delivery | Canada data residency enforced |
| FinOps data warehouse | Usage analytics, revenue reporting | Nightly exports with hashed batches |
| Ops runbook catalog | Operational readiness | RB entries for billing incidents |

______________________________________________________________________

## 10) References

- TDD §3.9 FinOps guardrails, §4.2 Tenant suspension coupling, §14.4 Billing retention.
- Accounts & Tenants specification — `../customer/accounts-tenants.md`.
- Settings Registry specification — `../platform/settings.md`.
- Artifact Store specification — `../data/artifact-store.md`.
- Ops runbook catalog — `../ops/runbooks.md`.
- ADR-0002 API Versioning & Sunset (billing APIs use deprecation headers).
