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
- **Maintenance:** Run `python scripts/docs/lint_docs.py docs/src/services/billing-subscriptions.md docs/src/overview/tdd.md docs/tdd_modularization.md` before submitting. Contract changes must update TDD billing tables and Ops runbooks `RB-BILLING-*`.
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

### 3.1 Admin APIs (binding)

- `POST /api/admin/billing/plans/` — Create plan version; returns plan ID. Errors: `VALIDATION_ERROR`, `CONFLICT`, `POLICY_BLOCK` (Finance approval missing). **|**
- `POST /api/admin/billing/subscriptions/<subscription_id>/change-plan/` — Schedules plan change next billing cycle. **|**
- `POST /api/admin/billing/subscriptions/<subscription_id>/cancel/` — Cancels at period end or immediately (with reason). **|**
- **Breadcrumbs:** `apps/platform/billing/views.py`, tests `tests/platform/billing/test_admin_api.py`. **|**

### 3.2 Webhooks (binding)

- `/webhooks/billing/payment_succeeded` and `/webhooks/billing/payment_failed` accept Stripe events (Canada region). Requests validated via signing secret; mismatches return 400. **|**
- `/webhooks/billing/customer_updated` refreshes billing contact details. **|**
- Webhook failures retried with exponential backoff; security logs capture attempts. **|**
- **Breadcrumbs:** `apps/platform/billing/providers/stripe/webhooks.py`, tests `tests/platform/billing/test_stripe_webhooks.py`. **|**

### 3.3 Events & integrations (binding)

- Emits events `BILLING_SUBSCRIPTION_UPDATED`, `BILLING_DELINQUENT`, `BILLING_PAYMENT_RECEIVED` on Jobs SSE and Celery signals for Accounts service. **|**
- FinOps ingestion exports to data warehouse nightly (Appendix L). **|**
- **Breadcrumbs:** `apps/platform/events/billing.py`, tests `tests/platform/events/test_billing_events.py`. **|**

______________________________________________________________________

## 4) State Management (binding)

- All billing tables use Canadian-region Postgres cluster with row-level security tied to Finance/Platform roles. **|**
- Sensitive payment metadata stored via provider tokens; no raw card data persisted. **|**
- Audit tables `billing_event`, `billing_invoice_audit` append-only with signature checks. **|**
- Usage meter uses partitioned tables by month, retention per Finance policy (7 years). **|**
- Tenant status sync: Accounts service caches subscription state; updated via events + nightly reconciliation job. **|**

______________________________________________________________________

## 5) Failure modes & resiliency (binding)

- **Provider outage:** Fallback to queuing invoices; escalate to Finance via `RB-BILLING-PAYMENT`. **|**
- **Webhook replay:** Detect via idempotency keys; duplicates ignored. **|**
- **Metering lag:** When `usage_meter_lag_seconds > 900`, throttle new invoices and alert FinOps. **|**
- **Delinquency false positive:** Flag via manual override, audit in `billing_delinquency_override`. **|**
- **Currency mismatch:** Block invoice generation if currency mismatch detected between plan and provider. **|**

______________________________________________________________________

## 6) Observability (binding)

- Metrics: `billing_subscription_active_total`, `billing_invoice_overdue_total`, `billing_payment_failed_total`, `usage_meter_lag_seconds`, `billing_delinquency_active_total`. **|**
- Logs: Structured events `BILLING_*`, webhook audit logs with signature validity, invoice hash records. **|**
- Dashboards: “Billing Health”, “Usage Metering”, “Stripe Webhooks”. **|**
- Alerts: Burn-rate alerts on failed payments, webhook failures, metering lag. **|**

______________________________________________________________________

## 7) Security & compliance (binding)

- PCI scope: Stripe handles card data; platform stores only tokens. Annual PCI-DSS SAQ documented in Appendix P. **|**
- Residency: Billing data stored in Canada region; exports sanitized for cross-border data warehouse with Finance approval. **|**
- Access: Finance roles gated by Identity spec; actions require dual approval for plan changes. **|**
- Audit: Invoices and subscription changes hashed and stored in Artifact Store `docs/` with appended metadata. **|**
- Compliance: Supports deprecation headers per [RFC 8594](https://www.rfc-editor.org/rfc/rfc8594) when APIs change. **|**

______________________________________________________________________

## 8) Operations & runbooks (binding)

- Runbooks: `RB-BILLING-DELINQUENCY`, `RB-BILLING-PAYMENT`, `RB-BILLING-METERING`, `RB-BILLING-PLAN-ROLLBACK`. **|**
- Drills: Quarterly delinquency tabletop, semi-annual invoice reconciliation dry run, webhook failure simulation. Evidence `ops/billing/drills/<date>/`. **|**
- Automation: `scripts/ops/billing_reconcile.py`, `scripts/ops/metering_backfill.py`. **|**
- On-call: `billing-oncall@`, Slack `#ops-billing`, escalation to Finance leadership for incidents > Sev2. **|**

______________________________________________________________________

## 9) Dependencies (binding)

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
- Accounts & Tenants specification — `../services/accounts-tenants.md`.
- Settings Registry specification — `../services/settings.md`.
- Artifact Store specification — `../services/artifact-store.md`.
- Ops runbook catalog — `../ops/runbooks.md`.
- ADR-0002 API Versioning & Sunset (billing APIs use deprecation headers).

