---
title: uDocket — Policy Residency Service Specification
subtitle: Residency catalogs, waiver manifests, and enforcement mesh integration
author:
  - Residency Governance Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Security Engineering
  - Platform Architecture
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - QA Engineering Lead
  - Compliance Lead
approved_by:
approved_date:
header-includes:
  - |
    <style>
      table{font-size:8.5pt;}
      table td,table th{font-size:inherit;word-break:break-word;overflow-wrap:anywhere;}
      figure svg text,figure svg tspan{fill:#111!important;}
      figure svg text{font-family:"DejaVu Sans","Trebuchet MS",Arial,sans-serif!important;}
      figure.full-width-diagram img{width:100%;height:auto;display:block;}
    </style>
  - |
    <header class="page-header">uDocket — Policy Residency Service Specification <br> Residency catalogs, waiver manifests, and enforcement mesh integration</header>
  - |
    <footer class="page-footer">Confidential · Last updated 2025-10-29 · Page <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Residency Governance Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Security Engineering; Platform Architecture |
| Reviewers | QA Engineering Lead; Compliance Lead |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Documents the standalone Policy Residency service supplying catalogs, waivers, and enforcement meshes to all runtime components.
- **Structure:** Template-compliant sections define purpose/responsibilities (§1–§2), API/state/failure/observability expectations (§3–§6), security/ops workflows (§7–§8), dependencies, and references.
- **Maintenance:** Catalog/waiver edits require dual approval, signed manifests, and drill evidence updates; run `python -m doc_tools.manage_docs --lint` before merging.
- **Change protocol:** Pull requests touching catalogs, mesh manifests, or waiver schemas must cite this spec + ADR-0003; high-risk changes pass CAB review.
- **References:** TDD §7, Settings spec §7, Ops runbooks `RB-RES-BLOCK`, `RB-RES-ENDPOINT`, `RB-WAIVER-GOV`.
- **Contacts:** Security Engineering (catalog/mesh), Compliance (waivers/audit), Platform Architecture (integration).

______________________________________________________________________

## 1) Purpose

**Purpose:** Deliver authoritative residency catalogs and waivers so every service enforces regional policy consistently. **|**
**Contract:** Policy Residency signs catalogs, distributes enforcement meshes, and exposes waiver manifests consumed by LPE, Guardian, automation, and networking layers. **|**
**State:** Catalogs under `policy_residency_catalog`, waivers under `policy_residency_waiver`, mesh artifacts under `ops/policy-residency/mesh/`, signed packages in `ops/policy-residency/catalog@<version>.json`. **|**
**Failures & handling:** Catalog drift, expired waivers, or mesh mismatch trigger RB-RES-BLOCK/RB-RES-ENDPOINT. **|**
**Observability:** Dashboards “Residency Mesh & Waivers”, metrics `residency_catalog_out_of_date_total`, `residency_waiver_expired_total`, `residency_mesh_drift_total`. **|**
**Breadcrumbs:** `services/policy-residency/src`, Settings `apps/platform/settings/services/residency.py`, Ops manifests. **|**
**References:** Settings spec, Audit spec, Ops runbooks.

______________________________________________________________________

## 2) Responsibilities (binding)

**Purpose:** Define the deterministic duties of the service. **|**
**Contract:** Maintain the following capabilities before publishing catalogs or waivers. **|**
**State:** Catalog + waiver database tables, signed artifacts, event history. **|**
**Failures & handling:** Catalog or mesh drift fails open to RB-RES-BLOCK; waiver expiry returns `RESIDENCY_WAIVER_EXPIRED`. **|**
**Observability:** Adoption metrics (mesh vs. catalog version), waiver dashboards. **|**
**Breadcrumbs:** Service source, Ops manifests, Waiver tooling. **|**
**References:** Policy docs, Ops runbooks.

- Maintain canonical region/provider allowlists per org/tenant and ensure Settings activations reference signed catalogs.
- Validate, approve, and publish waivers with scope, expiry, and remediation steps.
- Generate enforcement meshes (e.g., ServiceMesh AuthorizationPolicy) aligned with catalogs; expose digests for reconciliation.
- Emit events so downstream services (LPE, automation, Guardian) refresh contexts on change.

______________________________________________________________________

## 3) API Contract (normative)

**Purpose:** Describe REST/event surfaces powering residency enforcement. **|**
**Contract:** APIs must be authenticated, return signed manifests, and surface waiver metadata deterministically. **|**
**State:** Responses include catalog version, mesh digest, waiver metadata; events include `{version, hash, affected_regions[], mesh_digest}`. **|**
**Failures & handling:** Error codes documented below instruct services to halt cross-region work until remediation. **|**
**Observability:** API latency/errors, event lag metrics, audit logs. **|**
**Breadcrumbs:** `services/policy-residency/src/api.py`, schema definitions, tests `tests/platform/settings/test_residency_catalog.py`. **|**
**References:** Settings spec, Automation specs, Policy docs.

### 3.1 External Interfaces

- `GET /policy/residency/catalog` — returns signed catalog + mesh digests; clients cache via ETag.
- `GET /policy/residency/catalog/<version>/mesh` — download enforcement mesh bundle.
- `GET /policy/residency/waivers/<waiver_id>` — retrieve waiver manifest for audit.
- `POST /policy/residency/waivers:request` — initiate waiver workflow (requires dual approval).

### 3.2 Internal Interfaces

- Events `policy.residency.catalog.updated` and `policy.residency.waiver.updated` propagate to LPE/Guardian/automation.
- Admin CLI `policy_residency.catalog.sign` signs manifests and publishes to storage + Settings.

### 3.3 API Error Codes

**Purpose:** Surface Policy Residency–specific `ApiError.code` values so services halt unsafe cross-region work deterministically. **|**
**Contract:** Codes align with Platform Runtime §3.3 and map to catalog/waiver/mesh failures described in §5. **|**
**State:** YAML catalog `docs/data/policy-residency/error_codes.yaml` feeds this section and the global appendix. **|**
**Failures & handling:** Unknown codes fail docs lint and page via `policy_residency_api_error_total{code="unknown"}`. **|**
**Observability:** Metrics `policy_residency_api_error_total{code}` and Alertmanager alerts. **|**
**Breadcrumbs:** Error-code YAML, API handlers `services/policy-residency/src/api.py`, tests `tests/platform/settings/test_residency_catalog.py`. **|**
**References:** Platform Runtime §3.3, API error appendix.

> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#policy-residency-service)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `residency_catalog_missing` | Residency catalog unavailable or not activated. | Pause cross-region work, regenerate the catalog from Settings, verify signatures, and reissue the request once activation succeeds. |
| `residency_mesh_drift` | Enforcement mesh does not match the active catalog version. | Redeploy the mesh from the current catalog version and confirm hashes match before reissuing the request. |
| `residency_waiver_expired` | Waiver referenced by the request has expired. | Renew or replace the waiver (with dual approval) or adjust the job scope to stay within current allowlists before retrying. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `residency_catalog_missing` | 503 | Yes | — |
| `residency_mesh_drift` | 500 | Yes | — |
| `residency_waiver_expired` | 409 | Yes | — |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

______________________________________________________________________

## 4) State Management (binding)

**Purpose:** Capture persistence requirements. **|**
**Contract:** Catalogs/waivers are append-only, signed, and auditable; mesh artifacts track version+hash. **|**
**State:** Postgres tables, signed JSON artifacts, mesh bundles, waiver evidence. **|**
**Failures & handling:** Signature failures halt activation; drift triggers RB-RES-ENDPOINT. **|**
**Observability:** Migration logs, artifact hash dashboards. **|**
**Breadcrumbs:** Database migrations, signing scripts, ops manifests. **|**
**References:** Audit spec, Security policy.

______________________________________________________________________

## 5) Failure Modes (binding)

**Purpose:** Enumerate common failures. **|**
**Contract:** Fail closed for missing catalog, expired waivers, mesh drift; provide actionable errors. **|**
**State:** Failure state recorded in ops logs and events. **|**
**Failures & handling:** RB-RES-BLOCK (catalog missing), RB-WAIVER-GOV (waiver expired), RB-RES-ENDPOINT (mesh drift). **|**
**Observability:** Alerts on `residency_catalog_out_of_date_total`, `residency_waiver_expired_total`, `residency_mesh_drift_total`. **|**
**Breadcrumbs:** Ops runbooks, dashboards. **|**
**References:** Policy docs, Ops catalog.

______________________________________________________________________

## 6) Observability (binding)

**Purpose:** Keep residency enforcement visible. **|**
**Contract:** Metrics/logs/dashboards enumerated here must exist before rollout. **|**
**State:** Prometheus rules `infra/monitoring/policy-residency-prometheus-rules.yaml`, dashboards `infra/observability/dashboards/policy_residency.json`, audit logs. **|**
**Failures & handling:** Missing telemetry blocks change approvals. **|**
**Observability:** `residency_catalog_out_of_date_total`, `residency_waiver_expired_total`, `residency_mesh_drift_total`, `policy_residency_event_lag_seconds`. **|**
**Breadcrumbs:** Monitoring repo, alert definitions. **|**
**References:** Observability spec, Policy docs.

### 6.1 SLOs & Targets (binding)

**Purpose:** Provide measurable objectives. **|**
**Contract:** Catalog publish success ≥99.9 %; mesh deployment parity <5 min; waiver decision P95 ≤2 business days. **|**
**State:** SLO dashboards + burn-rate rules. **|**
**Failures & handling:** Breaches trigger RB-RES-BLOCK or RB-WAIVER-GOV until metrics recover. **|**
**Observability:** Prometheus SLO queries, FinOps dashboards. **|**
**Breadcrumbs:** Monitoring repo. **|**
**References:** Compliance policy, Ops governance.

______________________________________________________________________

## 7) Security & Compliance (binding)

**Purpose:** Document residency + waiver governance. **|**
**Contract:** Catalog changes require dual approval + signatures; waivers log justification, expiry, and remediation. **|**
**State:** Signed artifacts, waiver evidence, audit logs. **|**
**Failures & handling:** Non-compliant catalogs or waivers escalate to Compliance; service halts cross-region work. **|**
**Observability:** Audit logs, dashboards showing waiver usage. **|**
**Breadcrumbs:** Compliance policy, Audit spec. **|**
**References:** ADR-0003, Ops runbooks.

______________________________________________________________________

## 8) Operational Notes (binding)

**Purpose:** Capture staffing, runbooks, workflows. **|**
**Contract:** Maintain on-call coverage, runbooks, and drill evidence before releases. **|**
**State:** Runbooks `docs/ops/runbooks/residency/*.md`, drill logs `ops/policy-residency/drills/<date>/`. **|**
**Failures & handling:** Missing evidence blocks release. **|**
**Observability:** Drill tracker metrics. **|**
**Breadcrumbs:** Ops runbooks, on-call rosters. **|**
**References:** Ops governance, Compliance policy.

### 8.1 Operational Posture

**Purpose:** Document on-call staffing. **|**
**Contract:** Security Engineering primary pager, Compliance backup; ≤15 min ack. **|**
**State:** Schedules `ops/oncall/residency.md`. **|**
**Failures & handling:** Gaps escalate to Ops Steering. **|**
**Observability:** Pager analytics. **|**
**Breadcrumbs:** On-call repo. **|**
**References:** Incident policy.

### 8.2 Incident Triggers

**Purpose:** Map alerts to runbooks. **|**
**Contract:** Alerts map to runbooks and remain actionable with paging enabled. **|**
**State:** Alert definitions. **|**
**Failures & handling:** Weekly review; missing runbooks added before release. **|**
**Observability:** Alert dashboards. **|**
**Breadcrumbs:** Monitoring repo. **|**
**References:** Ops governance.

- `residency_catalog_out_of_date_total` → RB-RES-BLOCK.
- `residency_mesh_drift_total` → RB-RES-ENDPOINT.
- `residency_waiver_expired_total` → RB-WAIVER-GOV.

### 8.3 Runbooks & Drills

**Purpose:** Ensure responders maintain executable playbooks. **|**
**Contract:** Keep RB-RES-BLOCK, RB-RES-ENDPOINT, RB-WAIVER-GOV current; quarterly drills produce evidence. **|**
**State:** Runbook markdown, drill evidence directories. **|**
**Failures & handling:** Evidence gaps block deployments. **|**
**Observability:** Drill tracker metrics. **|**
**Breadcrumbs:** Runbook repo. **|**
**References:** Compliance policy.

#### 8.3.1 Runbook Index

| Signal | Runbook | Notes |
| --- | --- | --- |
| `residency_catalog_out_of_date_total` | RB-RES-BLOCK | Catalog missing/stale |
| `residency_mesh_drift_total` | RB-RES-ENDPOINT | Mesh/cd mismatch |
| `residency_waiver_expired_total` | RB-WAIVER-GOV | Waiver expired |

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarize the runbooks responders execute during incidents. **|**
**Contract:** Keep RB-RES-BLOCK/RB-RES-ENDPOINT/RB-WAIVER-GOV current with clear triggers and evidence expectations. **|**
**State:** Markdown runbooks + automation scripts `docs/ops/runbooks/residency/*.md`. **|**
**Failures & handling:** Missing steps or stale ownership blocks deployments until updated. **|**
**Observability:** Ops catalog + drill tracker verify coverage. **|**
**Breadcrumbs:** Runbook repo, drill evidence `ops/policy-residency/drills/<date>/`. **|**
**References:** Compliance policy, Ops governance.

- **RB-RES-BLOCK:** Regenerate catalog, resign, republish, notify tenants.
- **RB-RES-ENDPOINT:** Compare mesh vs. catalog, redeploy mesh, confirm hashes.
- **RB-WAIVER-GOV:** Review expirations, notify tenants, capture remediation.

#### 8.3.3 Drill Cadence & Evidence

- Quarterly catalog regeneration tabletop.
- Semi-annual mesh parity drill.
- Annual waiver governance review.
- Evidence stored `ops/policy-residency/drills/<date>/summary.md`.

### 8.4 Migrations & Backfills

**Purpose:** Govern catalog migrations/backfills. **|**
**Contract:** Append-only migrations; backfills require signed digests + approvals. **|**
**State:** Migration scripts, replay tooling. **|**
**Failures & handling:** Use `policy_residency.migrations.rollback` for failures. **|**
**Observability:** Migration dashboards. **|**
**Breadcrumbs:** Repo docs. **|**
**References:** Database governance.

### 8.5 Operational Workflows

**Purpose:** Describe recurring workflows (catalog review, waiver audit). **|**
**Contract:** Monthly catalog reconciliation, quarterly waiver audit, mesh drift checks. **|**
**State:** Checklists `ops/policy-residency/workflows/*.md`. **|**
**Failures & handling:** Missing tasks escalate to Compliance. **|**
**Observability:** Workflow dashboard. **|**
**Breadcrumbs:** Ops workflows. **|**
**References:** Compliance guide.

______________________________________________________________________

## 9) Dependencies (normative)

**Purpose:** Capture upstream/downstream systems. **|**
**Contract:** Policy Residency depends on Reference Manager (jurisdiction data), Settings activation, LPE, OPA bundle server. Downstream consumers must refresh contexts on events. **|**
**State:** Shared schemas, events. **|**
**Failures & handling:** Joint incident reviews when dependencies drift. **|**
**Observability:** Dependency dashboards. **|**
**Breadcrumbs:** Dependency specs. **|**
**References:** Reference Manager, Settings, OPA policy plane specs.

______________________________________________________________________

## 10) References (informative)

- TDD §7
- ADR-0003 (Localization & Policy Engine)
- Settings Registry specification §7
- OPA Policy Plane specification
- Ops runbooks RB-RES-BLOCK / RB-RES-ENDPOINT / RB-WAIVER-GOV
