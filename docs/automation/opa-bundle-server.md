---
title: uDocket — OPA Policy Plane & Bundle Server Specification
subtitle: Signed policy distribution, discovery, and enforcement observability
author:
  - Policy Runtime Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Architecture
  - Security Engineering
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - QA Engineering Lead
  - SRE Manager
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
    <header class="page-header">uDocket — OPA Policy Plane &amp; Bundle Server Specification <br> Signed policy distribution, discovery, and enforcement observability</header>
  - |
    <footer class="page-footer">Confidential · Last updated 2025-10-29 · Page <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Policy Runtime Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Architecture; Security Engineering |
| Reviewers | QA Engineering Lead; SRE Manager |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Describes the OPA policy plane responsible for ingesting LPE bundles, dual-signing artifacts, distributing them via discovery endpoints, and streaming decision logs.
- **Structure:** Template-compliant sections map purpose/responsibilities (§1–§2), APIs/state/failure/observability (§3–§6), security/ops workflows (§7–§8), dependencies (§9), and references (§10).
- **Maintenance:** Bundle format/pipeline changes require ADR reference, dual approval, and updated drills; run `make docs.lint`/`make docs.build` before merging.
- **Change protocol:** Any change affecting discovery URLs, signature scheme, or decision log schema must cite ADR-0004 and update Ops runbooks RB-OPA-ROLLBACK/RB-OPA-DECISIONLOG.
- **References:** LPE spec (compiler), Policy Residency spec, Audit spec, Ops runbooks, Observability spec.
- **Contacts:** Policy Runtime Working Group (`opa-plane@`), Security Engineering for bundle signing, SRE for cluster operations.

______________________________________________________________________

## 1) Purpose

**Purpose:** Provide a hardened distribution plane so every enforcement surface consumes the same signed policies. **|**
**Contract:** Bundle server ingests LPE outputs, appends residency metadata, dual-signs bundles (Ed25519 + ECDSA P-256), serves HA discovery endpoints, and forwards decision logs. **|**
**State:** Signed bundles stored under `ops/policy/bundles/`, discovery metadata (versions, ETags), decision log buffers, Prometheus telemetry. **|**
**Failures & handling:** Signature failure, stale bundle, or decision log outage triggers RB-OPA-ROLLBACK/RB-OPA-DECISIONLOG. **|**
**Observability:** Dashboards “OPA Policy Plane”, “Bundle Signature Health”, “Decision Log Latency”; metrics `opa_bundle_status`, `opa_bundle_signature_error_total`, `opa_decision_latency_seconds`. **|**
**Breadcrumbs:** `services/opa-bundle-server/src`, signing scripts `scripts/opa/sign_bundle.py`, infra manifests `infra/kubernetes/opa/`. **|**
**References:** LPE spec, Policy Residency spec, Audit spec.

______________________________________________________________________

## 2) Responsibilities (binding)

**Purpose:** Enumerate bundle server duties. **|**
**Contract:** Fulfil the following duties for every bundle promotion. **|**
**State:** Bundle store, signing keys, discovery metadata, decision log buffers, runbook automation scripts. **|**
**Failures & handling:** Signature failure or stale bundle fails closed; decision log outage buffers locally then pages SRE. **|**
**Observability:** Metrics covering bundle signatures, discovery latency, decision log throughput. **|**
**Breadcrumbs:** Repo source, runbooks, monitoring configs. **|**
**References:** ADR-0004, Ops runbooks.

- Accept compiled bundles from LPE, inject residency/waiver metadata, sign, and publish.
- Serve `/bundles/<channel>` + `.well-known/opa/status` endpoints with strong authz and caching semantics.
- Stream structured decision logs to Kafka/warehouse with deterministic redaction.
- Provide automation hooks for RB-OPA-ROLLBACK, RB-OPA-DECISIONLOG, RB-OPA-FIPS.

______________________________________________________________________

## 3) API Contract (normative)

**Purpose:** Document discovery + decision log interfaces. **|**
**Contract:** Endpoints must require mTLS/service tokens, include signature headers, and expose deterministic metadata (version, SHA, signer key). **|**
**State:** Status endpoints backed by discovery store; decision log collector writes to Kafka topic `opa.decision.logs`. **|**
**Failures & handling:** Error codes below instruct clients to halt bundle promotion until remediation. **|**
**Observability:** Access logs, OpenTelemetry spans, API latency metrics. **|**
**Breadcrumbs:** `services/opa-bundle-server/src/api.py`, schema definitions. **|**
**References:** ADR-0004, Observability spec, Audit spec.

### 3.1 External Interfaces

- `GET /.well-known/opa/status` — returns bundle version/signature status.
- `GET /bundles/<channel>` — downloads bundle plus signature headers.
- `POST /decision-logs` — optional collector endpoint for centralized ingestion.

### 3.2 Internal Interfaces

- gRPC/Unix socket for on-host sidecars to fetch bundles without egress.
- Event `opa.bundle.promoted` -> audit stream with `{channel, version, sha256, signer_key}`.

### 3.3 API Error Codes

**Purpose:** Capture OPA bundle-plane `ApiError.code` values so clients halt unsafe promotions deterministically. **|**
**Contract:** Codes extend Platform Runtime §3.3 for signature drift, stale bundles, and decision-log outages. **|**
**State:** YAML catalog `docs/automation/opa-bundle-server/error_codes.yaml` renders this section and the appendix. **|**
**Failures & handling:** Unknown codes fail docs lint and page `opa_bundle_status{state="unknown_code"}` alerts. **|**
**Observability:** Metrics `opa_bundle_status{}` and `opa_bundle_signature_error_total{code}` feed dashboards. **|**
**Breadcrumbs:** Error-code YAML, API handlers `services/opa-bundle-server/src/api.py`, tests `tests/opa/test_bundle_signatures.py`. **|**
**References:** Platform Runtime §3.3, API error appendix.

> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#opa-policy-plane-bundle-server)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `opa_bundle_signature_invalid` | Latest bundle failed signature verification. | Block bundle promotion, execute RB-OPA-ROLLBACK to the last-known-good version, and retry discovery after signatures validate. |
| `opa_bundle_stale` | Client requested a bundle older than the minimum supported version. | Refresh the discovery cache or force a bundle update; if the issue persists, investigate connectivity before retrying. |
| `opa_decision_log_unavailable` | Decision log ingestion temporarily unavailable. | Buffer locally per RB-OPA-DECISIONLOG, monitor ingestion health, and replay logs once the collector recovers. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `opa_bundle_signature_invalid` | 503 | Yes | — |
| `opa_bundle_stale` | 409 | No | — |
| `opa_decision_log_unavailable` | 502 | No | — |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

______________________________________________________________________

## 4) State Management (binding)

**Purpose:** Capture bundle/artifact persistence. **|**
**Contract:** Bundles + metadata stored immutably with version/sha/signer; discovery cache replicates across AZs; decision logs persisted with at-least-once semantics. **|**
**State:** Bundle storage, discovery DB/Redis, decision log buffers, ops audit records. **|**
**Failures & handling:** Signature mismatch halts promotion; discovery cache corruption triggers RB-OPA-ROLLBACK; decision log buffer overflow pages RB-OPA-DECISIONLOG. **|**
**Observability:** Hash digests, buffer utilization metrics. **|**
**Breadcrumbs:** Storage manifests, DB migrations. **|**
**References:** Audit spec, Security policy.

______________________________________________________________________

## 5) Failure Modes (binding)

**Purpose:** Document resilience strategy. **|**
**Contract:** Fail closed on signature errors, stale bundles, missing decision logs, or FIPS attestation issues. **|**
**State:** Failure state recorded in ops logs and `opa_bundle_status`. **|**
**Failures & handling:** RB-OPA-ROLLBACK, RB-OPA-DECISIONLOG, RB-OPA-FIPS. **|**
**Observability:** Alerts `opa_bundle_signature_error_total`, `opa_bundle_stale_total`, `opa_decision_log_delivery_gap_total`. **|**
**Breadcrumbs:** Runbooks, monitoring repo. **|**
**References:** ADR-0004, Ops catalog.

______________________________________________________________________

## 6) Observability (binding)

**Purpose:** Keep bundle plane verifiable. **|**
**Contract:** Metrics/dashboards enumerated here must exist; signatures + decision logs traced. **|**
**State:** Prometheus rules `infra/monitoring/opa-bundle-prometheus-rules.yaml`, dashboards `infra/observability/dashboards/opa_bundle.json`, audit logs. **|**
**Failures & handling:** Missing telemetry blocks deployments. **|**
**Observability:** `opa_bundle_status`, `opa_bundle_signature_error_total`, `opa_decision_latency_seconds`, `opa_decision_log_delivery_gap_total`. **|**
**Breadcrumbs:** Monitoring repo, Alertmanager config. **|**
**References:** Observability spec, Audit spec.

### 6.1 SLOs & Targets

**Purpose:** Define measurable success. **|**
**Contract:** Bundle promotion success ≥99.95 %, discovery P95 ≤2 s globally, decision log delivery ≥99.9 % within 60 s. **|**
**State:** SLO dashboards, burn-rate alerts. **|**
**Failures & handling:** Breaches trigger RB-OPA-ROLLBACK or RB-OPA-DECISIONLOG. **|**
**Observability:** Prometheus SLO queries, synthetic fetchers. **|**
**Breadcrumbs:** Monitoring repo. **|**
**References:** Observability spec §6.

______________________________________________________________________

## 7) Security & Compliance (binding)

**Purpose:** Document signing, FIPS, and audit requirements. **|**
**Contract:** Bundles must be dual-signed with HSM keys, carry residency annotations, and publish audit artifacts; decision logs stored per retention policy. **|**
**State:** Signing keys, attestations, audit logs, decision log archives. **|**
**Failures & handling:** Signature/fips issues escalate to Security via RB-OPA-FIPS; audit log gaps trigger compliance tickets. **|**
**Observability:** Key rotation logs, signature dashboards, audit log monitors. **|**
**Breadcrumbs:** Security policy, Audit spec, Ops runbooks. **|**
**References:** ADR-0004, Audit spec §4/§5.

______________________________________________________________________

## 8) Operational Notes (binding)

**Purpose:** Capture day-2 operations. **|**
**Contract:** Maintain on-call coverage, runbooks, drills, and rollout automation. **|**
**State:** Runbooks in `docs/ops/runbooks/opa/`, drill evidence `ops/opa/drills/<date>/`, deployment manifests. **|**
**Failures & handling:** Missing evidence or stale runbooks block release. **|**
**Observability:** Deployment dashboards, drill tracker metrics. **|**
**Breadcrumbs:** Ops runbooks, Helm charts. **|**
**References:** Ops governance, LPE spec.

### 8.1 Operational Posture

**Purpose:** Document staffing + readiness. **|**
**Contract:** Policy Runtime WG primary pager, Security backup; FIPS specialists on-call during rotations. **|**
**State:** Rota files `ops/oncall/opa.md`. **|**
**Failures & handling:** Coverage gaps escalate to Architecture + Security leads. **|**
**Observability:** Pager metrics. **|**
**Breadcrumbs:** On-call repo. **|**
**References:** Incident policy.

### 8.2 Incident Triggers

**Purpose:** Map alerts to severity. **|**
**Contract:** Alerts map to runbooks and remain actionable with paging enabled. **|**
**State:** Alert definitions. **|**
**Failures & handling:** Weekly review to adjust thresholds. **|**
**Observability:** Alert dashboards. **|**
**Breadcrumbs:** Monitoring repo. **|**
**References:** Observability spec.

- `opa_bundle_signature_error_total` → RB-OPA-ROLLBACK (Sev-2)
- `opa_bundle_stale_total` → RB-OPA-ROLLBACK (Sev-3)
- `opa_decision_log_delivery_gap_total` → RB-OPA-DECISIONLOG (Sev-2)

### 8.3 Runbooks & Drills

**Purpose:** Keep playbooks executable. **|**
**Contract:** Maintain RB-OPA-ROLLBACK, RB-OPA-DECISIONLOG, RB-OPA-FIPS; execute quarterly drills. **|**
**State:** Runbooks + automation scripts. **|**
**Failures & handling:** Evidence gaps block release. **|**
**Observability:** Drill tracker metrics. **|**
**Breadcrumbs:** Ops runbooks. **|**
**References:** Ops governance.

#### 8.3.1 Runbook Index

| Signal | Runbook | Notes |
| --- | --- | --- |
| `opa_bundle_signature_error_total` | RB-OPA-ROLLBACK | Signature failure |
| `opa_bundle_stale_total` | RB-OPA-ROLLBACK | Discovery drift |
| `opa_decision_log_delivery_gap_total` | RB-OPA-DECISIONLOG | Collector outage |

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Outline the critical runbooks responders execute. **|**
**Contract:** Keep RB-OPA-ROLLBACK / RB-OPA-DECISIONLOG / RB-OPA-FIPS current with clear triggers and evidence capture. **|**
**State:** Markdown runbooks and automation scripts under `docs/ops/runbooks/opa/`. **|**
**Failures & handling:** Missing steps or stale ownership blocks deployments until remediated. **|**
**Observability:** Ops catalog + drill tracker verify coverage. **|**
**Breadcrumbs:** Runbook repo, drill evidence `ops/opa/drills/<date>/`. **|**
**References:** Ops governance policy.

- **RB-OPA-ROLLBACK:** Promote last-known-good bundle, flush caches, verify signatures before re-enabling traffic.
- **RB-OPA-DECISIONLOG:** Buffer logs locally, restart collector, backfill warehouse gaps.
- **RB-OPA-FIPS:** Re-attest HSM, rotate signing keys, capture evidence for compliance.

#### 8.3.3 Drill Cadence & Evidence

- Quarterly bundle rollback tabletop.
- Semi-annual decision-log outage simulation.
- Annual FIPS attestation drill.
- Evidence stored under `ops/opa/drills/<date>/summary.md`.

### 8.4 Migrations & Backfills

**Purpose:** Describe bundle format/migration workflows. **|**
**Contract:** Versioned bundle schema; migrations require compatibility staging + signed artifacts. **|**
**State:** Schema docs, migration scripts, compatibility reports. **|**
**Failures & handling:** Roll back to prior bundle schema if parity fails. **|**
**Observability:** Compatibility dashboards. **|**
**Breadcrumbs:** Repo docs. **|**
**References:** ADR-0004.

### 8.5 Operational Workflows

**Purpose:** Document recurring tasks (key rotation, audit exports). **|**
**Contract:** Quarterly key rotation, monthly log export, weekly bundle audit. **|**
**State:** Checklists `ops/opa/workflows/*.md`. **|**
**Failures & handling:** Skipped workflows escalate to Security. **|**
**Observability:** Workflow dashboard. **|**
**Breadcrumbs:** Ops workflows. **|**
**References:** Security policy.

______________________________________________________________________

## 9) Dependencies (normative)

**Purpose:** Capture upstream/downstream systems. **|**
**Contract:** Depends on LPE outputs, Policy Residency catalogs, signing infrastructure, observability pipeline; downstream consumers include Guardian, Portal, automation workers. **|**
**State:** Shared schemas/events. **|**
**Failures & handling:** Dependency drift triggers joint incident reviews. **|**
**Observability:** Dependency dashboards + event lag metrics. **|**
**Breadcrumbs:** Dependency specs. **|**
**References:** LPE, Policy Residency, Observability specs.

______________________________________________________________________

## 10) References (informative)

- ADR-0004 (OPA Policy Plane)
- LPE specification
- Policy Residency specification
- Audit specification (state + logs)
- Ops runbooks RB-OPA-ROLLBACK / RB-OPA-DECISIONLOG / RB-OPA-FIPS
