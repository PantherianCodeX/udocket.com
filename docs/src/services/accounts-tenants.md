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
- **Maintenance:** Run `python scripts/docs/lint_docs.py docs/src/services/accounts-tenants.md docs/src/services/identity.md docs/src/overview/tdd.md` before submitting. Changes to lifecycle stages require updates to TDD §14.1 checklists and runbook catalog entries.
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

### 3.1 REST endpoints (binding)

- `POST /api/admin/tenants/` — Creates tenant (admin-only); returns provisioning job id. Errors: `VALIDATION_ERROR`, `POLICY_BLOCK` (missing compliance artifacts), `CONFLICT` (duplicate domain). **|**
- `POST /api/admin/tenants/<tenant_id>/suspend/` — Applies suspension hold; requires reason code. **|**
- `POST /api/admin/tenants/<tenant_id>/offboard/` — Initiates offboarding job; streaming status via Jobs SSE. **|**
- `POST /api/admin/tenants/<tenant_id>/members/` — Adds membership with RBAC checks. **|**
- Breadcrumbs: `apps/platform/accounts/api.py`, `tests/platform/accounts/test_api.py`. **|**

### 3.2 Federation endpoints (binding)

- SAML metadata and ACS endpoints served per-tenant under `/sso/<tenant_slug>/metadata` and `/sso/<tenant_slug>/acs`. **|**
- Certificates rotated via admin UI; `tenant_event` logs rotations. **|**
- Error handling: `POLICY_BLOCK` when metadata validation fails; `PROVIDER_DEGRADED` when IdP unreachable. **|**
- Breadcrumbs: `apps/platform/accounts/sso/views.py`, tests `tests/platform/accounts/test_sso.py`. **|**

### 3.3 Webhooks & events (binding)

- Emits `TENANT_PROVISIONED`, `TENANT_SUSPENDED`, `TENANT_OFFBOARDING_STARTED`, `TENANT_DECOMMISSIONED` onto Jobs SSE for UI updates. **|**
- Guardian/Settings watchers update caches when tenant state changes. **|**
- Breadcrumbs: `apps/platform/events/tenants.py`, tests `tests/platform/events/test_tenant_events.py`. **|**

______________________________________________________________________

## 4) State Management (binding)

- Tenants tracked via `accounts_organization` with immutable slug, residency, legal agreement references. **|**
- Workspaces (`accounts_workspace`) reference tenants and include retention/residency overrides. **|**
- `tenant_event` ledger stores lifecycle transitions with user, timestamp, reason. **|**
- RLS enforced via `TENANT_MEMBERSHIP_POLICY` linking principal to tenant/org roles; uses Identity spec Appendix A helpers. **|**
- Cached settings stored in Settings Registry snapshots; invalidated on state changes. **|**

______________________________________________________________________

## 5) Failure modes & resiliency (binding)

- **Provisioning failures:** Partial tenants rolled back; error recorded, operations alerted via `RB-TENANT-PROVISION`. **|**
- **SSO drift:** Metadata changes without rotation; detection via `tenant_sso_metadata_outdated_total`. **|**
- **Suspension misfires:** Inconsistent toggles flagged by reconciler; block operations until resolved. **|**
- **Offboarding backlog:** More than 3 tenants pending >30 days triggers compliance escalation. **|**
- **Role drift:** Unexpected admin role grants flagged by Guardian heuristics (TDD §4.5). **|**

______________________________________________________________________

## 6) Observability (binding)

- Metrics: `tenant_activation_latency_seconds`, `tenant_membership_provision_total`, `tenant_suspension_active_total`, `tenant_offboarding_backlog_total`, `tenant_sso_metadata_outdated_total`. **|**
- Logs: Structured audit events `TENANT_*`, membership `MEMBERSHIP_*`, SSO rotation logs with certificate fingerprints. **|**
- Dashboards: “Tenant Lifecycle”, “Tenant Membership”, “Tenant Compliance Holds”. **|**
- Alerts: Burn-rate alerts on provisioning latency, suspension backlog, SSO expiry. **|**

______________________________________________________________________

## 7) Security & compliance (binding)

- Residency enforcement ties tenant region to artifact locations; Settings keys `tenancy.residency.region` validated at provisioning. **|**
- Compliance holds triggered by audits; ensures retention timeline freeze until clearance. **|**
- Access control inherits Identity service RBAC; tenant admins require multi-factor per Identity spec §4.3. **|**
- Legal agreements stored per tenant with version history; DSAR responses include tenant scope. **|**
- Audit logs retained for ≥7 years; append-only with tamper-evident hashing. **|**

______________________________________________________________________

## 8) Operations & runbooks (binding)

- Runbooks: `RB-TENANT-PROVISION`, `RB-TENANT-OFFBOARD`, `RB-TENANT-ROLES`, `RB-TENANT-SSO`. **|**
- Drills: Quarterly provisioning dry-run, semi-annual offboarding rehearsal, SSO rotation tabletop. Evidence in `ops/tenants/drills/<date>/`. **|**
- Automation: `scripts/ops/tenant_provision_check.py`, `scripts/ops/tenant_offboarding_audit.py`. **|**
- On-call: `identity-oncall@`, `#ops-accounts` Slack channel, escalation to Customer Ops leadership. **|**

______________________________________________________________________

## 9) Dependencies (binding)

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
- Identity & Access specification — `../services/identity.md`.
- Settings Registry specification — `../services/settings.md`.
- Artifact Store specification — `../services/artifact-store.md`.
- Billing & Subscriptions specification — `../services/billing-subscriptions.md`.
- Ops runbook catalog — `../ops/runbooks.md`.

