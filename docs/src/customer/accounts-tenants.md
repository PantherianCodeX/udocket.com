---
title: uDocket — Accounts & Tenants Service Specification
subtitle: Organization Provisioning, Identity Federation, and Lifecycle Controls
author:
  - Access & Tenant Lifecycle Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Engineering
  - Identity & Access
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - Compliance Lead
  - Customer Operations Lead
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
  - <header class="page-header">uDocket — Accounts & Tenants Service Specification <br>
    Organization Provisioning, Identity Federation, and Lifecycle Controls</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Access & Tenant Lifecycle Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Engineering; Identity & Access |
| Reviewers | Compliance Lead; Customer Operations Lead |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Describes the Accounts & Tenants service responsible for organization provisioning, workspace lifecycle, role assignment, SSO/SAML federation, billing flags, and tenant offboarding (TDD §4, §14.1). Differentiates org-level constructs (tenants) from platform-wide identities.
- **Structure:** Sections mirror the service template: charter and responsibilities, API contract, state management, failure handling, observability, security/compliance, operations, dependencies, and references. Appendices align with Identity service RLS patterns (Identity spec Appendix A) and TDD Appendix S (ownership map).
- **Maintenance:** Run `python -m docs.tools.lint_docs docs/src/customer/accounts-tenants.md docs/src/platform/identity.md docs/src/overview/tdd.md` before submitting. Changes to lifecycle stages require updates to TDD §14.1 checklists and runbook catalog entries.
- **Change protocol:** Provisioning/offboarding changes must reference this doc, Identity spec, Ops runbooks, and ADR-0001 where Guardian roles adjust. Schema changes require migrations plus doc updates.
- **References:** TDD §4 Tenancy & Access, §14 retention/offboarding, Identity spec §4, Settings Registry §4 (`tenancy.*`), Ops runbooks `RB-TENANT-*`.
- **Contacts:** Identity & Access (service ownership), Customer Operations (tenant onboarding/offboarding), escalation `#ops-accounts`, on-call `identity-oncall@`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Provide a governed lifecycle for organizations (tenants), workspaces, and user membership with clear activation/offboarding checkpoints. **|**
**Contract:** Tenants advance through Provisioning → Active → Suspended → Decommissioned with deterministic workflows, audit trails, and residency/billing gates. Roles and entitlements derive from Identity service assignments but use tenant-scoped policies. **|**
**State:** Owns `accounts_organization`, `accounts_workspace`, `accounts_membership`, provisioning ledger `tenant_event`, and org-scoped settings. **|**
**Failures & handling:** Provisioning failures, SSO metadata drift, or stale suspension states trigger Ops runbooks and hold new user invites. **|**
**Observability:** Metrics `tenant_activation_latency_seconds`, `tenant_membership_provision_total`, `tenant_deprovision_backlog_total`; dashboards “Tenant Lifecycle” and “Provisioning Health”. **|**
**Breadcrumbs:** Implementation `apps/platform/accounts/service.py`, provisioning flows `apps/platform/accounts/provisioning.py`, SSO handlers `apps/platform/accounts/sso/`, tests `tests/platform/accounts/`. **|**
**References:** TDD §4.1–§4.5, §14.1, Identity spec §3–§4.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Clarify the responsibilities the Accounts & Tenants service owns and the invariants it must uphold. **|**
**Contract:** Manage provisioning, membership, tenant configuration, suspension/offboarding, and residency/billing checks. **|**
**State:** Tenant records, membership assignments, lifecycle ledger, SSO metadata. **|**
**Failures & handling:** Identify failure points (activation errors, stale SSO certs, orphaned workspaces) and escalation paths. **|**
**Observability:** Metrics/dashboards to prove responsibilities. **|**
**Breadcrumbs:** Implementation references, migrations, runbooks. **|**
**References:** TDD §4, §14.1, Identity spec Appendix A.

### 2.1 Tenant provisioning (binding)

- **Contract:** Provisioning pipeline creates organization, default workspace, and initial admin membership within <15 minutes P95. Requires signed MSA, residency selection, and Settings snapshot baseline. **|**
- **State:** `tenant_event` records `PROVISIONING_REQUESTED`, `PROVISIONED`, `FAILED`, `ROLLED_BACK`. **|**
- **Observability:** Metrics `tenant_activation_latency_seconds`, audit log `TENANT_PROVISIONED`. **|**
- **Failures & handling:** On failure, rollback created artifacts, notify Ops, keep tenant in `PROVISIONING` until resolved. **|**
- **Breadcrumbs:** Celery task `apps/platform/accounts/tasks/provision_tenant.py`, ops runbook `RB-TENANT-PROVISION`, tests `tests/platform/accounts/test_provisioning.py`. **|**

### 2.2 Tenant suspension & holds (binding)

- **Contract:** Suspension toggles (billing delinquency, compliance hold) must block new artifact creation while retaining read access for investigators. Applies Settings overrides `tenancy.suspension.mode`. **|**
- **State:** `tenant_suspension` ledger with reason, actor, expected resolution. **|**
- **Observability:** Metric `tenant_suspension_active_total`, audit events `TENANT_SUSPENDED`, `TENANT_RESUMED`. **|**
- **Failures & handling:** Unexpected suspension removal requires dual approval; missing reason codes fail lint checks. **|**
- **Breadcrumbs:** Suspension API `apps/platform/accounts/views.py::suspend`, tests `tests/platform/accounts/test_suspension.py`. **|**

### 2.3 Offboarding & retention (binding)

- **Contract:** Offboarding follows TDD §14.1: disable access, archive artifacts, enforce retention timers (`artifacts.retention.*`), then purge after approvals. All steps recorded in `tenant_offboarding` ledger. **|**
- **State:** DSAR references, export manifests, workspace closure flags. **|**
- **Observability:** Metric `tenant_offboarding_backlog_total`, dashboards “Offboarding Progress”. **|**
- **Failures & handling:** Block release until exports succeed; escalate via `RB-TENANT-OFFBOARD`. **|**
- **Breadcrumbs:** Offboarding scripts `apps/platform/accounts/offboarding.py`, tests `tests/platform/accounts/test_offboarding.py`. **|**

### 2.4 Membership & role mapping (binding)

- **Contract:** Membership assignments map Identity service principals to tenant roles; RLS policies updated atomically (TDD §4.4). Invitations require verified email and locale selection. **|**
- **State:** `accounts_membership`, `accounts_role_assignment`, invitation tokens. **|**
- **Observability:** `tenant_membership_provision_total`, `tenant_invitation_expired_total`. **|**
- **Failures & handling:** Orphaned roles flagged by nightly reconciler; mismatched roles escalate via `RB-TENANT-ROLES`. **|**
- **Breadcrumbs:** Membership service `apps/platform/accounts/membership.py`, tests `tests/platform/accounts/test_membership.py`. **|**

______________________________________________________________________

## 3) API Contract

**Purpose:** Define external/internal APIs (REST, event streams, SSO endpoints). **|**
**Contract:** Provide authenticated admin APIs, SSO metadata endpoints, and lifecycle webhooks. **|**
**State:** API responses align with tenant records and settings snapshots. **|**
**Failures & handling:** Document error codes, retry semantics. **|**
**Observability:** Track API latency and error rate metrics. **|**
**Breadcrumbs:** Viewsets, serializers, tests. **|**
**References:** API error appendix (Accounts section), Identity spec.

### 3.1 External Interfaces (binding)

- `POST /api/admin/tenants/` — Creates tenant (admin-only); returns provisioning job id. Errors: `VALIDATION_ERROR`, `POLICY_BLOCK` (missing compliance artifacts), `CONFLICT` (duplicate domain). **|**
- `POST /api/admin/tenants/<tenant_id>/suspend/` — Applies suspension hold; requires reason code. **|**
- `POST /api/admin/tenants/<tenant_id>/offboard/` — Initiates offboarding job; streaming status via Jobs SSE. **|**
- `POST /api/admin/tenants/<tenant_id>/members/` — Adds membership with RBAC checks. **|**
- Breadcrumbs: `apps/platform/accounts/api.py`, `tests/platform/accounts/test_api.py`. **|**

### 3.2 Internal Interfaces (binding)

- SAML metadata and ACS endpoints served per-tenant under `/sso/<tenant_slug>/metadata` and `/sso/<tenant_slug>/acs`. **|**
- Certificates rotated via admin UI; `tenant_event` logs rotations. **|**
- Error handling: `POLICY_BLOCK` when metadata validation fails; `PROVIDER_DEGRADED` when IdP unreachable. **|**
- Breadcrumbs: `apps/platform/accounts/sso/views.py`, tests `tests/platform/accounts/test_sso.py`. **|**

### 3.3 Webhooks & events (binding) {#3-3-webhooks-events-binding}

- Emits `TENANT_PROVISIONED`, `TENANT_SUSPENDED`, `TENANT_OFFBOARDING_STARTED`, `TENANT_DECOMMISSIONED` onto Jobs SSE for UI updates. **|**
- Guardian/Settings watchers update caches when tenant state changes. **|**
- Breadcrumbs: `apps/platform/events/tenants.py`, tests `tests/platform/events/test_tenant_events.py`. **|**

### 3.3 API Error Codes (binding)

**Purpose:** Declare Accounts & Tenants error codes beyond the platform baseline. **|**
**Contract:** Current REST endpoints reuse core platform codes; no Accounts-specific codes exist yet but the catalog remains to track future additions. **|**
**State:** Stored in `docs/src/customer/accounts-tenants/error_codes.yaml`. **|**
**Failures & handling:** Rely on platform responses (`CONFLICT`, `POLICY_BLOCK`, `VALIDATION_ERROR`) detailed in Platform Runtime §3.3. **|**
**Observability:** Unknown codes emit `accounts_api_error_unknown_total` and page on-call. **|**
**Breadcrumbs:** API views `apps/platform/accounts/api.py`, audit events `tenant_event`, tests `tests/platform/accounts/test_api.py`. **|**
**References:** Platform Runtime §3.3, Identity §3, Settings §5.

> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#accounts-tenants-service)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Tenant already exists or lifecycle state prevents the requested transition. | Refresh tenant state, resolve outstanding provisioning/offboarding steps, then retry. |
| `POLICY_BLOCK` | Residency, compliance hold, or approval policy forbids processing the request. | Coordinate with Compliance/Records to clear the hold or obtain approval, then retry once unblocked. |
| `VALIDATION_ERROR` | Tenant payload failed schema validation or residency selection rules. | Correct the request body (domains, residency, legal artefacts) and resubmit. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | Yes | accounts_api_error_total<br>tenant_event_conflict_total |
| `POLICY_BLOCK` | 403 | Yes | accounts_api_error_total<br>tenant_suspension_active_total |
| `VALIDATION_ERROR` | 400 | No | accounts_api_error_total<br>tenant_activation_latency_seconds |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

______________________________________________________________________

## 4) State Management (binding)

**Purpose:** Document how tenant, workspace, and lifecycle state persists. **|**
**Contract:** Guarantee transactional lifecycle ledgers, RLS policies, and cached settings snapshots remain in sync. **|**
**State:** `accounts_organization`, `accounts_workspace`, `accounts_membership`, `tenant_event`, SSO metadata, cached settings. **|**
**Failures & handling:** Drift triggers nightly reconciliation; stale caches invalidated via Settings activation. **|**
**Observability:** Metrics `tenant_state_reconcile_total`, dashboards “Tenant Lifecycle”. **|**
**Breadcrumbs:** ORM models `apps/platform/accounts/models.py`, migrations `apps/platform/migrations/`, SSO cache `apps/platform/accounts/sso/cache.py`. **|**
**References:** TDD §4.1–§4.5, Appendix S ownership map, Identity spec Appendix A.

- Tenants tracked via `accounts_organization` with immutable slug, residency, legal agreement references. **|**
- Workspaces (`accounts_workspace`) reference tenants and include retention/residency overrides. **|**
- `tenant_event` ledger stores lifecycle transitions with user, timestamp, reason. **|**
- RLS enforced via `TENANT_MEMBERSHIP_POLICY` linking principal to tenant/org roles; uses Identity spec Appendix A helpers. **|**
- Cached settings stored in Settings Registry snapshots; invalidated on state changes. **|**

______________________________________________________________________

## 5) Failure Modes (binding)

**Purpose:** Outline primary failure scenarios for tenant lifecycle operations. **|**
**Contract:** Provisioning/offboarding must fail closed with audit evidence; SSO drift detected within configured windows. **|**
**State:** Provisioning jobs, suspension ledger, offboarding queue, SSO metadata caches. **|**
**Failures & handling:** Runbooks `RB-TENANT-*` restore state; Guardian assists on role drift. **|**
**Observability:** Alerts `tenant_activation_latency_seconds`, `tenant_suspension_active_total`, dashboards “Tenant Lifecycle”. **|**
**Breadcrumbs:** Incident retros `ops/tenants/incidents/*.md`, automation logs `ops/tenants/scripts/`. **|**
**References:** TDD §4.1–§4.5, §14.1.

- **Provisioning failures:** Partial tenants rolled back; error recorded, operations alerted via `RB-TENANT-PROVISION`. **|**
- **SSO drift:** Metadata changes without rotation; detection via `tenant_sso_metadata_outdated_total`. **|**
- **Suspension misfires:** Inconsistent toggles flagged by reconciler; block operations until resolved. **|**
- **Offboarding backlog:** More than 3 tenants pending >30 days triggers compliance escalation. **|**
- **Role drift:** Unexpected admin role grants flagged by Guardian heuristics (TDD §4.5). **|**

______________________________________________________________________

## 6) Observability (binding)

**Purpose:** Describe telemetry proving tenant lifecycle health. **|**
**Contract:** Emit metrics for provisioning latency, membership churn, suspension backlog, and SSO freshness; retain structured audit logs. **|**
**State:** Metrics, audit events, dashboards, synthetic probes. **|**
**Failures & handling:** Unknown metrics or gaps block releases; high backlog pages on-call. **|**
**Observability:** Dashboards “Tenant Lifecycle”, “Tenant Membership”, “Tenant Compliance Holds”. **|**
**Breadcrumbs:** Metrics module `apps/platform/accounts/metrics.py`, dashboard JSON `infra/monitoring/tenants_dashboard.json`. **|**
**References:** Observability spec §4, Appendix B metrics.

- Metrics: `tenant_activation_latency_seconds`, `tenant_membership_provision_total`, `tenant_suspension_active_total`, `tenant_offboarding_backlog_total`, `tenant_sso_metadata_outdated_total`. **|**
- Logs: Structured audit events `TENANT_*`, membership `MEMBERSHIP_*`, SSO rotation logs with certificate fingerprints. **|**
- Dashboards: “Tenant Lifecycle”, “Tenant Membership”, “Tenant Compliance Holds”. **|**
- Alerts: Burn-rate alerts on provisioning latency, suspension backlog, SSO expiry. **|**

### 6.1 SLOs & Targets (binding)

**Purpose:** Track lifecycle objectives necessary for production readiness. **|**
**Contract:** Provisioning P95 ≤ 15 min, zero overdue offboarding > 30 days, SSO metadata refreshed within 48 h of drift detection. **|**
**State:** Prometheus rules `infra/monitoring/tenants-slo-rules.yaml`, Grafana dashboard “Tenant Lifecycle – SLO”. **|**
**Failures & handling:** Breaches trigger RB-TENANT-PROVISION or RB-TENANT-OFFBOARD; releases pause until evidence captured. **|**
**Observability:** Burn-rate alerts `tenant_provision_slo_burn`, `tenant_offboarding_slo_burn`, `tenant_sso_refresh_burn`. **|**
**Breadcrumbs:** SLO config `infra/monitoring/tenants_slo.json`, tests `tests/integration/test_tenant_slo.py`. **|**
**References:** TDD §4.2, Appendix I controls map.

______________________________________________________________________

## 7) Security & Compliance (binding)

**Purpose:** Capture tenant provisioning security, residency, and audit controls. **|**
**Contract:** Enforce residency selection, dual approval for suspensions/holds, MFA for admin roles, and DSAR evidence retention. **|**
**State:** SSO metadata store, legal agreements, suspended tenant ledger, DSAR references. **|**
**Failures & handling:** Residency or SSO drift escalates via RB-TENANT-SSO/Guardian. **|**
**Observability:** Security alerts `tenant_residency_violation_total`, audit log checks, compliance dashboards. **|**
**Breadcrumbs:** IAM policies `infra/terraform/identity`, compliance docs `ops/compliance/tenants/`. **|**
**References:** TDD §4, §14.1, Identity spec §4.

- Residency enforcement ties tenant region to artifact locations; Settings keys `tenancy.residency.region` validated at provisioning. **|**
- Compliance holds triggered by audits; ensures retention timeline freeze until clearance. **|**
- Access control inherits Identity service RBAC; tenant admins require multi-factor per Identity spec §4.3. **|**
- Legal agreements stored per tenant with version history; DSAR responses include tenant scope. **|**
- Audit logs retained for ≥7 years; append-only with tamper-evident hashing. **|**

______________________________________________________________________

## 8) Operational Notes (binding)

**Purpose:** Summarize operational posture, runbooks, and drill cadence for Accounts & Tenants. **|**
**Contract:** Maintain on-call coverage, documented runbooks, and drill evidence before enabling production changes. **|**
**State:** Runbooks, drill evidence, automation scripts, roster calendars. **|**
**Failures & handling:** Missed drills or stale runbooks block releases per docs lint. **|**
**Observability:** Runbook catalog freshness, drill scheduler, pager metrics. **|**
**Breadcrumbs:** Runbooks `docs/src/ops/runbooks/accounts/*.md`, automation `scripts/ops/tenant_*.py`, staffing roster `ops/tenants/rota.md`. **|**
**References:** Ops catalog, Appendix S ownership map.

- Runbooks: `RB-TENANT-PROVISION`, `RB-TENANT-OFFBOARD`, `RB-TENANT-ROLES`, `RB-TENANT-SSO`. **|**
- Drills: Quarterly provisioning dry-run, semi-annual offboarding rehearsal, SSO rotation tabletop. Evidence in `ops/tenants/drills/<date>/`. **|**
- Automation: `scripts/ops/tenant_provision_check.py`, `scripts/ops/tenant_offboarding_audit.py`. **|**
- On-call: `identity-oncall@`, `#ops-accounts` Slack channel, escalation to Customer Ops leadership. **|**

### 8.1 Operational Posture (binding)

**Purpose:** Describe staffing model, maintenance windows, and readiness gates. **|**
**Contract:** Identity Engineering primary on-call with Platform Ops backup; acknowledge within 5 minutes, mitigation within 30 minutes; Saturday 03:00–05:00 PT maintenance window. **|**
**State:** Rosters `ops/tenants/rota.md`, maintenance calendar `ops/change/tenants.ics`, readiness checklist `ops/tenants/checklists/operational_posture.md`. **|**
**Failures & handling:** Coverage gaps escalate to Customer Ops leadership; releases blocked when readiness checklist incomplete. **|**
**Observability:** PagerDuty analytics, staffing dashboard “Tenant Ops Posture”, docs lint check `docs_staffing_posture_missing_total`. **|**
**Breadcrumbs:** Incident response guide `docs/src/ops/runbooks/accounts/README.md`, staffing policy `ops/tenants/policies/staffing.md`. **|**
**References:** Ops runbook catalog, Appendix S ownership map.

### 8.2 Incident Triggers (binding)

**Purpose:** Enumerate alerts and monitors that declare an incident. **|**
**Contract:** Alerts `tenant_activation_latency_seconds`, `tenant_offboarding_backlog_total`, `tenant_sso_metadata_outdated_total`, and Guardian role-drift heuristics must page on-call; synthetic provisioning job failure also pages. **|**
**State:** Alert definitions `infra/monitoring/tenants-alerts.yaml`, synthetic job `scripts/ops/tenant_provision_check.py`, Guardian heuristics `packages/udocket_core/guardian/role_monitor.py`. **|**
**Failures & handling:** Alert misfires tuned via SRE ticket; silent failures result in governance review and updated alert thresholds. **|**
**Observability:** Grafana “Tenant Incident Triggers”, PagerDuty incident exports, docs metric `tenant_alert_suppressed_total`. **|**
**Breadcrumbs:** Alert rules, PagerDuty services, Guardian analytics dashboards. **|**
**References:** §6 Observability, `RB-TENANT-*` runbooks.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Keep runbooks executable and drills current. **|**
**Contract:** Alerts map to RB-TENANT-\* identifiers; quarterly/annual drills executed with evidence recorded. **|**
**State:** Runbooks `docs/src/ops/runbooks/accounts/*.md`, drill evidence `ops/tenants/drills/<date>/`, automation `scripts/ops/tenant_*.py`. **|**
**Failures & handling:** Runbook drift or missing evidence blocks releases until resolved; docs lint enforces freshness. **|**
**Observability:** Runbook catalog output, drill scheduler metrics, governance dashboard. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler docs, Slack `#ops-accounts`. **|**
**References:** `RB-TENANT-PROVISION`, `RB-TENANT-OFFBOARD`, `RB-TENANT-ROLES`, `RB-TENANT-SSO`.

#### 8.3.1 Runbook Index (informative)

| Runbook code | Scenario | Notes |
| --- | --- | --- |
| `RB-TENANT-PROVISION` | Provisioning outage or rollback | Evidence captured in `ops/tenants/drills/<date>/provisioning.md` |
| `RB-TENANT-OFFBOARD` | Offboarding backlog/export failure | Coordinates Records & Compliance sign-off |
| `RB-TENANT-ROLES` | Suspicious role grants / Guardian alert | Validates role state and approvals |
| `RB-TENANT-SSO` | Federation metadata drift/rotation | Engages IdP contacts, rotates secrets |

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarize key playbooks executed during incidents. **|**
**Contract:** Keep runbooks versioned, linked to alerts, and reviewed quarterly. **|**
**State:** Markdown in `docs/src/ops/runbooks/accounts/*.md`, automation scripts `scripts/ops/tenant_*.py`. **|**
**Failures & handling:** Stale runbooks flagged by docs lint `runbook_catalog_stale_total`. **|**
**Observability:** Governance dashboard, runbook catalog output. **|**
**Breadcrumbs:** Runbook files, automation scripts, incident templates. **|**
**References:** `RB-TENANT-PROVISION`, `RB-TENANT-OFFBOARD`, `RB-TENANT-ROLES`, `RB-TENANT-SSO`.

- `RB-TENANT-PROVISION` — Provisioning outage recovery and evidence capture. **|**
- `RB-TENANT-OFFBOARD` — Coordinated offboarding and retention handshake. **|**
- `RB-TENANT-ROLES` — Role drift remediation with Guardian validation. **|**
- `RB-TENANT-SSO` — Federation rotation/drift response, certificate replacement. **|**

#### 8.3.3 Drill Cadence & Evidence (binding)

Quarterly and semi-annual drills rehearse provisioning, offboarding, and SSO recovery steps while preserving audit evidence. **|**

- Quarterly provisioning dry-run with synthetic tenants; results stored in `ops/tenants/drills/<date>/provisioning.md`. **|**
- Semi-annual offboarding rehearsal; evidence includes export manifests and DSAR confirmations. **|**
- Quarterly SSO rotation tabletop; notes recorded in `ops/tenants/drills/<date>/sso.md`. **|**

- Incident and drill artifacts archived under `ops/tenan../data/<date>/`; Grafana snapshots included. **|**
- Compliance reviews sample evidence twice yearly; gaps create action items tracked in governance dashboard. **|**
- Docs lint monitors `docs_runbook_evidence_missing_total` for stale or missing folders. **|**

### 8.4 Migrations & Backfills (binding)

**Purpose:** Capture tenant/SSO migration and backfill procedures. **|**
**Contract:** Run provisioning migrations via `ops/scripts/tenants/migrate.py`, capture before/after snapshots, and coordinate with Accounts & Tenants approvals. **|**
**State:** Migration manifests `ops/tenants/migrations/`, replay tooling `scripts/ops/tenant_replay.py`. **|**
**Failures & handling:** Failed migrations rolled back using transactional snapshots; incidents documented with evidence. **|**
**Observability:** Migration dashboards track job progress and errors. **|**
**Breadcrumbs:** Migration scripts, change calendars, ADR references. **|**
**References:** TDD §4.1 (tenant provisioning), §14.1 (offboarding), Ops catalog.

### 8.5 Operational Workflows (binding)

**Purpose:** Document recurring tasks such as tenant audits and waiver reviews. **|**
**Contract:** Weekly provisioning audit, monthly suspension review, and quarterly SSO metadata validation executed by designated owners. **|**
**State:** Checklists `ops/tenants/workflows/*.md`, automation outputs `ops/tenants/reports/*.csv`. **|**
**Failures & handling:** Missed workflows raise alerts `tenant_workflow_overdue_total` and block releases until caught up. **|**
**Observability:** Workflow dashboard, audit logs, docs lint. **|**
**Breadcrumbs:** Workflow docs, automation scripts, staffing rosters. **|**
**References:** Incident management handbook, Compliance playbooks.

______________________________________________________________________

## 9) Dependencies (binding)

**Purpose:** List upstream/downstream services Accounts & Tenants relies on. **|**
**Contract:** Maintain dependency mappings for impact analysis and incident coordination. **|**
**State:** Captured in Platform Runtime service catalog plus this table. **|**
**Failures & handling:** Dependency incidents route through referenced runbooks. **|**
**Observability:** Dependency dashboards overlay service health metrics. **|**
**Breadcrumbs:** Platform Runtime catalog, Ops runbook index, Settings `tenancy.*` keys. **|**
**References:** Platform Runtime §3 (service catalog), Settings §5 (`tenancy.*` keys), Billing & Artifact Store specs.

| Dependency | Responsibility | Notes |
| --- | --- | --- |
| Identity service | Authentication, MFA, principal directory | Shared RBAC helpers and SSO metadata |
| Settings Registry | Tenant configuration (residency, features) | Keys `tenancy.*`, `billing.*` |
| Artifact Store | Applies retention/offboarding actions | Requires tenant state to determine purge timings |
| Billing service | Reflects tenant status (active/suspended) | `billing_subscription` references tenant state |
| Guardian | Enforces role approvals and monitors suspicious grants | Guardian signals block risky assignments |
| Ops runbook catalog | Operational guidance | RB entries for provisioning/offboarding |

______________________________________________________________________

## 10) References

- TDD §4 Tenancy & Access, §14.1 Tenant provisioning/offboarding.
- Identity & Access specification — `../platform/identity.md`.
- Settings Registry specification — `../platform/settings.md`.
- Artifact Store specification — `../data/artifact-store.md`.
- Billing & Subscriptions specification — `../customer/billing-subscriptions.md`.
- Ops runbook catalog — `../ops/runbooks.md`.
