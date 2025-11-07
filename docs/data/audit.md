---
title: uDocket — Audit & Evidence Specification
subtitle: Immutable Records, Seals, and Compliance Telemetry
author:
  - Compliance Engineering Guild
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Compliance Engineering
  - Platform Architecture
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - Site Reliability Engineering
  - Legal & Privacy
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
  - <header class="page-header">uDocket — Audit & Evidence Specification <br>
    Immutable Records, Seals, and Compliance Telemetry</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-29 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Compliance Engineering Guild |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Compliance Engineering; Platform Architecture |
| Reviewers | Site Reliability Engineering; Legal & Privacy |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** This spec owns immutable audit storage, structured evidence manifests, audit seals, judgment history, DSAR/waiver logging, and compliance traceability. It complements `../platform/observability.md`, which focuses on runtime observability.
- **Audience:** Compliance engineers, platform architects, Guardian/Signer teams, and auditors verifying evidence chains.
- **Change protocol:** Any schema or seal change must update this document, reference relevant ADRs, and demonstrate seal verification in staging. Run `python -m doc_tools.check_structure docs/data/audit.md` prior to submission.
- **Related references:** TDD §5 and §12 summarize lifecycle/audit obligations; Guardian (§7) describes judgment payloads; Settings (§7.3) enumerates audit keys; Audit appendices in the TDD now point here.

______________________________________________________________________

## 1) Purpose (binding)

**Purpose:** Guarantee defensible, append-only evidence for every job, approval, waiver, and retention event so auditors can verify posture without ad-hoc exports. **|**
**Contract:** All lifecycle events produce manifests, append to immutable audit sinks, and receive hourly seals; waivers and DSAR actions include structured metadata with traceable UUIDs. **|**
**State:** `audit_event` table, immutable object store, `ops_<agent>.jsonl` streams, Guardian judgment history, seal manifests, waiver ledger, DSAR journals. **|**
**Failures & handling:** Seal failures, immutable sink lag, schema drift, or missing manifests block releases until remediated with RB-AUDIT-004 and RB-RES-BLOCK/DSAR runbooks. **|**
**Observability:** Dashboards “Audit Seal Integrity”, “Waiver Ledger”, metrics `audit_worm_lag_seconds`, `audit_seal_errors_total`, `audit_manifest_missing_total`, `waiver_expiring_total`. **|**
**Breadcrumbs:** Audit store implementation `packages/core/audit/store.py`, seal runner `ops/audit/seal_runner.py`, waiver ledger `packages/core/waiver/ledger.py`, DSAR tooling `ops/privacy/dsar_runner.py`. **|**
**References:** TDD §5 summary, Logging spec §3, Guardian §7, Settings §7.3.

______________________________________________________________________

## 2) Responsibilities (binding)

**Purpose:** Clarify system-wide obligations for auditability. **|**
**Contract:** Platform persists append-only audit streams, services embed settings snapshot + Guardian IDs + SHA-256 hashes in manifests, seal service produces hourly Merkle roots, and the waiver ledger captures scope/expiry/evidence for every approval. **|**
**State:** Audit schemas, manifest definitions, seal artifacts, waiver ledger, DSAR journal, retention tombstones. **|**
**Failures & handling:** Missing manifest or seal triggers deploy gate; waiver expiry without review escalates to Compliance; DSAR journal gaps raise `dsar_journal_missing_total`. **|**
**Observability:** Dashboards “Evidence Chain” and “Waiver Governance”, metrics `audit_manifest_version_total`, `waiver_expiring_total`, `dsar_journal_pending_total`. **|**
**Breadcrumbs:** Manifest models `packages/core/manifests/`, ops streams `ops/<agent>__*.json`, schema migrations `db/migrations/audit/`. **|**
**References:** §3 API contract, §4 State management, §5 Failure modes, §6 Observability, §7 Security & Compliance.

______________________________________________________________________

## 3) API Contract (binding)

**Purpose:** Define how services emit audit evidence, how the audit store ingests it, and which artifacts external consumers rely on. **|**
**Contract:** Agent runs and platform workflows must emit manifests and JSONL events following `manifest.schema.json` and `audit_event` schema; seal service and verification APIs must remain available within SLA; waiver/DSAR tooling must expose structured endpoints. **|**
**State:** Manifest files on case storage, `ops_<agent>.jsonl` streams, Postgres `audit_event` partitions, seal artifacts, waiver ledger entries, DSAR journals. **|**
**Failures & handling:** Schema validation failures, manifest gaps, or seal errors block promotions and trigger RB-AUDIT-004; waiver APIs enforce expiry; DSAR endpoints fail closed per RB-PRIV-DSAR. **|**
**Observability:** Dashboards “Evidence Chain”, “Audit Seal Integrity”, metrics `audit_manifest_missing_total`, `audit_event_backlog_seconds`, `audit_seal_errors_total`. **|**
**Breadcrumbs:** Audit store `packages/core/audit/store.py`, manifest models `packages/core/manifests/`, waiver APIs `packages/core/compliance/waiver.py`, DSAR tooling `ops/privacy/dsar_runner.py`. **|**
**References:** TDD §5, Observability §3, Guardian §7, Settings §7.3.

### 3.1 External Interfaces

- Agent manifolds (`<job_id>__<agent>_manifest.json`) and JSONL streams consumed by Guardian, Compose, and external auditors. Schema lives in `spec/schemas/manifest.schema.json`.
- Audit REST endpoints (`POST /api/v1/audit/events/search`, `GET /api/v1/audit/seal/{id}`) expose evidence to authorized staff with WebAuthn step-up.
- Waiver ledger APIs (`POST /api/v1/compliance/waivers`) and DSAR APIs (`POST /api/v1/privacy/dsar`) accept structured payloads referencing cases/artifacts.

### 3.2 Internal Interfaces

- Celery tasks append `audit_event` rows and JSONL entries per lifecycle (`apps/platform/operations/audit.py`).
- Seal runner `ops/audit/seal_runner.py` and verifier `ops/audit/verify_seal_chain.py` operate hourly; results persisted under `AUDIT_SEAL` artifacts.
- Retention jobs `ops/privacy/retention_runner.py` consume audit logs to build `ERASURE_JOURNAL`/`DESTRUCTION_CERT` artifacts.

### 3.3 API Error Codes (binding)

**Purpose:** Document Audit & Evidence `ApiError.code` emissions so downstream services and auditors can apply the correct remediation flow. **|**
**Contract:** Audit APIs reuse the platform catalog in [`Platform Runtime §3.3`](../platform/runtime.md#33-api-error-codes-binding) and surface the codes below for domain-specific failures. **|**
**State:** Codes originate from `apps/platform/audit/api.py` and ledger services, with matching audit events appended to `ops/audit/ops_audit.jsonl`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and contract tests; runtime emissions trigger `audit_api_error_total{code}` alerts. **|**
**Observability:** Metrics `audit_api_error_total{code}` and dashboards “Audit Seal Integrity” / “Compliance Evidence” monitor error rates; synthetic DSAR drills confirm semantics. **|**
**Breadcrumbs:** API handlers `apps/platform/audit/api.py`, waiver service `apps/platform/compliance/waiver.py`, DSAR runner `ops/privacy/dsar_runner.py`, tests `tests/platform/audit/test_api_errors.py`. **|**
**References:** Platform Runtime §3.3, Guardian spec §2.3, Settings spec §7.3.

> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#audit-evidence)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `INTEGRITY_ERROR` | Seal manifest hash mismatch or immutable sink divergence detected. | Rebuild manifests via `ops/audit/rebuild_manifest.py`, regenerate seal, then retry once integrity is restored. |
| `NOT_FOUND` | Evidence bundle absent or redacted per retention policy. | Treat as terminal; refresh catalog or request prior version rather than retrying blindly. |
| `POLICY_BLOCK` | Legal hold, residency, or waiver guard prevents evidence release or deletion. | Surface Guardian/waiver reason, engage RB-AUDIT-004 or RB-WAIVER-GOV before retrying. |
| `QUARANTINED` | Evidence quarantined pending Guardian or manual review. | Escalate to Guardian reviewers; do not retry until quarantine cleared. |
| `VALIDATION_ERROR` | Waiver or DSAR payload fails schema or policy validation. | Inspect `details[]`, correct the input, and resubmit. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `INTEGRITY_ERROR` | 412 | Yes | audit_api_error_total<br>audit_seal_errors_total |
| `NOT_FOUND` | 404 | No | audit_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | audit_api_error_total<br>waiver_expiring_total |
| `QUARANTINED` | 423 | Yes | audit_api_error_total |
| `VALIDATION_ERROR` | 400 | No | audit_api_error_total |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

## 4) State Management (binding)

**Purpose:** Preserve audit evidence, manifests, and immutable replicas so records remain admissible. **|**
**Contract:** Keep manifests append-only, mirror audit events to WORM storage, and maintain waivers/DSAR logs in lockstep with production state. **|**
**State:** Manifest files, `audit_event` partitions, WORM buckets, waiver ledger, DSAR journal, and replication scripts. **|**
**Failures & handling:** Seal gaps, replication lag, or ledger drift trigger RB-AUDIT-004 or RB-WAIVER-GOV before approvals resume. **|**
**Observability:** Dashboards “Audit Seal Integrity”, “Immutable Sink”, metrics `audit_worm_lag_seconds`, `audit_seal_errors_total`, `waiver_expiring_total`. **|**
**Breadcrumbs:** Schema definitions `spec/schemas/audit_manifest.schema.json`, rotation tooling `ops/audit/rotate_partitions.py`, replication jobs `ops/audit/verify_seal_chain.py`, tests `tests/audit/test_state_management.py`. **|**
**References:** Observability §4, Settings §7.3, Observability §4.

### 4.1 Manifest & event storage

- Manifests stored under `storage/media/tenants/<ORG_ID>/cases/<case>/ops/<job_id>__<agent>_manifest.json` with SHA-256 digests.
- `audit_event` captures normalized events (case/artifact/job IDs, judgment IDs, settings hash, timestamps) and is mirrored to WORM.

### 4.2 Ledger storage

- Waiver ledger table `compliance_waiver` holds scope, jurisdiction, owners, expiry, evidence bundle path.
- DSAR journal `privacy_dsar_journal` tracks request lifecycle, deadlines, and evidence attachments.

______________________________________________________________________

## 5) Failure Modes (binding)

**Purpose:** Highlight critical failure scenarios and mitigation steps. **|**
**Contract:** Approvals halt when seals fail, immutable sink drifts, or manifests go missing; waivers and DSARs fail closed on errors. **|**
**State:** Runbooks RB-AUDIT-004, RB-WAIVER-GOV, RB-PRIV-DSAR, RB-AUDIT-MANIFEST; PagerDuty services `audit-integrity`, `compliance-ledger`. **|**
**Failures & handling:** See scenario list below. **|**
**Observability:** Incident metrics `audit_incident_total`, `audit_incident_mttr_minutes`. **|**
**Breadcrumbs:** Runbook catalog `../ops/runbooks.md`. **|**
**References:** Observability §5, Settings §7.3.

- Seal chain gap (`audit_seal_errors_total`) → pause approvals, run RB-AUDIT-004, regenerate seals.
- Immutable lag (`audit_worm_lag_seconds`) → enforce hold on approvals, coordinate with Logging RB-LOG-007.
- Manifest gap (`audit_manifest_missing_total`) → replay job manifests via `ops/audit/rebuild_manifest.py`.
- Waiver expiry (`waiver_expired_total`) → RB-WAIVER-GOV; affected flows blocked until renewed.
- DSAR backlog (`dsar_journal_pending_total`) → RB-PRIV-DSAR escalates to Privacy.

______________________________________________________________________

## 6) Observability (binding)

**Purpose:** Provide visibility into audit pipeline health. **|**
**Contract:** Maintain dashboards for evidence throughput, seal health, waiver expiries, DSAR status; synthetic seal verification runs hourly. **|**
**State:** Grafana dashboards “Audit Seal Integrity”, “Evidence Chain”, “Waiver Ledger”, Prometheus rules `infra/monitoring/audit-prometheus-rules.yaml`, synthetic job `synthetics/audit_verify.yaml`. **|**
**Failures & handling:** Missing dashboard or failing synthetic blocks releases until restored; escalate via RB-AUDIT-004 or RB-WAIVER-GOV. **|**
**Observability:** Metrics `audit_worm_lag_seconds`, `audit_seal_errors_total`, `audit_manifest_missing_total`, `waiver_expiring_total`, `dsar_journal_pending_total`. **|**
**Breadcrumbs:** Monitoring configs `infra/monitoring/`, synthetic definitions `synthetics/`. **|**
**References:** Observability §6, Settings §7.3, Compliance reporting.

### 6.1 SLOs & Targets (binding)

**Purpose:** Capture the availability and timeliness guarantees that keep audit evidence defensible. **|**
**Contract:** Seal verification, immutable mirroring, waiver reviews, and DSAR handling must satisfy the thresholds below before approvals continue. **|**
**State:** Metrics `audit_seal_errors_total`, `audit_worm_lag_seconds`, `waiver_expiring_total`, `dsar_journal_pending_total`; stored seal artifacts, waiver ledger entries, and DSAR journals provide evidence. **|**
**Failures & handling:** Breaches invoke RB-AUDIT-004, RB-WAIVER-GOV, or RB-PRIV-DSAR prior to resuming promotions. **|**
**Observability:** Dashboards “Audit Seal Integrity”, “Waiver Ledger”, and synthetic `audit_verify` runs monitor compliance. **|**
**Breadcrumbs:** Seal runner `ops/audit/seal_runner.py`, waiver ledger `packages/core/compliance/waiver.py`, DSAR tooling `ops/privacy/dsar_runner.py`. **|**
**References:** Logging spec §6, Settings spec §7.3, TDD §12.

- **Seal continuity:** Hourly seal verification succeeds with ≤1 failed interval per quarter; tracked via `audit_seal_errors_total` and synthetic `audit_verify` job, escalating through RB-AUDIT-004 on breach.
- **Immutable lag:** `audit_worm_lag_seconds` stays ≤15 minutes; exceeding lag blocks approvals and requires joint remediation with Observability before restart.
- **Compliance workflows:** Waiver backlog (`waiver_expiring_total`) resolved within 5 business days; DSAR backlog (`dsar_journal_pending_total`) remains within regulatory SLA (45 days CCPA/30 days GDPR) with automated reminders and RB-PRIV-DSAR if breached.

______________________________________________________________________

## 7) Security & Compliance (binding)

**Purpose:** Ensure audit evidence satisfies regulatory obligations and prevents tampering. **|**
**Contract:** Maintain immutable WORM storage, enforce dual approvals for waivers, log DSAR lifecycle, and align retention with jurisdictional mandates. **|**
**State:** WORM bucket policies, seal signing keys (Key Vault), waiver ledger, DSAR journal, legal hold metadata, audit artifacts (`AUDIT_SEAL`, `ERASURE_JOURNAL`, `DESTRUCTION_CERT`). **|**
**Failures & handling:** Seal or WORM issues escalate to Security; waiver drift triggers compliance tickets; DSAR SLA breaches escalate to Privacy. **|**
**Observability:** Compliance dashboards (waiver expiries, DSAR deadlines), metrics `waiver_expiring_total`, `dsar_deadline_breach_total`. **|**
**Breadcrumbs:** Policy docs `infra/compliance/`, Security approvals, ADR-0001, ADR-0006, ADR-0011. **|**
**References:** Settings §7.3–§7.4, Guardian §7, Digital Signer §4.

### 7.1 Waiver governance

- Dual approvers (Security + Product) required; evidence bundles stored under `ops/waivers/WAIVER-*.json`.
- Expiry notifications sent 7 days prior; stale waivers auto-suspend affected flows.

### 7.2 DSAR & retention compliance

- DSAR journal tracks received, due, completed status; erasure generates `ERASURE_JOURNAL` + `DESTRUCTION_CERT` artifacts referencing audit events removed.
- Legal hold toggles recorded as `LEGAL_HOLD_EVENT` with reviewer metadata.

______________________________________________________________________

## 8) Operational Notes (normative)

**Purpose:** Capture deployment cadence, drills, and staffing for audit operations. **|**
**Contract:** Run hourly seal verification, monthly waiver/DSAR reviews, quarterly immutable sink failover drills. **|**
**State:** Seal runner schedules, compliance review calendar, drill evidence directories `ops/audit/drills/`. **|**
**Failures & handling:** Missed reviews or drills block compliance sign-off and raise tickets. **|**
**Observability:** Execution tracker dashboard, metrics `audit_drill_overdue_total`, `waiver_review_overdue_total`. **|**
**Breadcrumbs:** Runbooks RB-AUDIT-004, RB-WAIVER-GOV, RB-PRIV-DSAR, RB-AUDIT-MANIFEST. **|**
**References:** Observability §8, Compliance policy.

### 8.1 Operational Posture (binding)

**Purpose:** Define on-call and staffing expectations. **|**
**Contract:** Compliance on-call must acknowledge within 15 minutes; weekly sync reviews waiver/DSAR backlog; seal runner ownership shared by SRE + Compliance. **|**
**State:** PagerDuty schedule `audit-integrity`, staffing roster `ops/oncall/compliance.md`. **|**
**Failures & handling:** Coverage gaps escalate to Compliance leadership; tracked via `audit_oncall_gap_total`. **|**
**Observability:** Staffing dashboard, pager latency metrics. **|**
**Breadcrumbs:** On-call docs, RB-AUDIT-004. **|**
**References:** Incident policy, SRE handbook.

### 8.2 Incident Triggers (binding)

**Purpose:** Enumerate signals that declare audit incidents. **|**
**Contract:** Trigger Sev-1 for seal chain gaps or immutable lag; Sev-2 for manifest gaps or waiver expiries; Sev-3 for DSAR backlog. **|**
**State:** Alert rules in `infra/monitoring/audit-prometheus-rules.yaml`, PagerDuty service `audit-integrity`. **|**
**Failures & handling:** Alert review monthly to keep thresholds tuned; missing triggers escalated to Compliance leadership. **|**
**Observability:** Alert dashboard “Audit Alerts”, incident retrospective cadence quarterly. **|**
**Breadcrumbs:** Prometheus rules, PagerDuty configs, incident templates. **|**
**References:** Runbooks RB-AUDIT-004, RB-WAIVER-GOV, RB-PRIV-DSAR.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Ensure evidence of drills and runbook freshness. **|**
**Contract:** Quarterly seal chain drill, semi-annual DSAR dry-run, annual waiver review; evidence stored alongside drill output. **|**
**State:** Drill scripts `ops/audit/drill_runner.py`, evidence directories `ops/audit/drills/<date>/`. **|**
**Failures & handling:** Missed drill triggers compliance Sev-2 and blocks release sign-off. **|**
**Observability:** Drill dashboard, metric `audit_drill_overdue_total`. **|**
**Breadcrumbs:** Runbooks RB-AUDIT-004, RB-PRIV-DSAR. **|**
**References:** Compliance governance plan.

#### 8.3.1 Runbook Index

- `audit_seal_errors_total` → RB-AUDIT-004  
- `audit_worm_lag_seconds` → RB-AUDIT-004  
- `waiver_expiring_total` → RB-WAIVER-GOV  
- `dsar_journal_pending_total` → RB-PRIV-DSAR

#### 8.3.2 Primary Runbooks

**Purpose:** Summarize core runbooks. **|**
**Contract:** Maintain RB-AUDIT-004 (seal/immutable response), RB-WAIVER-GOV (waiver review), RB-PRIV-DSAR (privacy obligations), RB-AUDIT-MANIFEST (manifest rebuild). **|**
**State:** Runbook markdown files in `docs/ops/runbooks/compliance/`. **|**
**Failures & handling:** Stale runbooks flagged during quarterly audit; block release until updated. **|**
**Observability:** Runbook freshness tracker. **|**
**Breadcrumbs:** Runbook repo. **|**
**References:** Compliance governance manual.

#### 8.3.3 Drill Cadence & Evidence

- Quarterly seal + immutable tabletop; evidence saved to `ops/audit/drills/<date>/seal.md`.\n- Semi-annual DSAR end-to-end rehearsal with sample case.\n- Annual waiver governance review documented as `WAIVER_REVIEW_REPORT` artifact.

### 8.4 Migrations & Backfills (informative)

**Purpose:** Capture schema migrations and replay tooling. **|**
**Contract:** `ops/audit/migrate_partition.py` provisions partitions ahead of time; replay jobs `ops/audit/replay_jsonl.py` rebuild `audit_event` from JSONL when needed. **|**
**State:** Migration scripts, partition schedules, replay tooling, change-management tickets. **|**
**Failures & handling:** Migration failures trip `audit_migration_failure_total`; rollbacks documented in RB-AUDIT-MANIFEST appendix. **|**
**Observability:** Migration progress dashboard, alerts for replay lag. **|**
**Breadcrumbs:** Migration scripts, replay jobs, change logs. **|**
**References:** ADR-0006, ADR-0011.

### 8.5 Operational Workflows (informative)

**Purpose:** Describe recurring compliance tasks. **|**
**Contract:** Weekly waiver ledger review, monthly DSAR SLA review, quarterly immutable sink evidence check, annual retention audit. **|**
**State:** Workflow checklists `ops/audit/workflows/`, automation reminders via Opsgenie. **|**
**Failures & handling:** Missed workflow items produce `audit_workflow_overdue_total` and block compliance sign-off. **|**
**Observability:** Workflow dashboard with SLA tracking. **|**
**Breadcrumbs:** Workflow docs, automation scripts, staffing rosters. **|**
**References:** Compliance calendar, privacy governance plan.

______________________________________________________________________

______________________________________________________________________

## 9) Dependencies (informative)

**Purpose:** Identify systems required to honor audit guarantees. **|**
**Contract:** Dependencies (Guardian, Logging, LP Engine, Settings, Key Vault, TSA/OCSP providers) must notify Compliance of breaking changes. **|**
**State:** Guardian judgment history, Logging immutable mirror, LP Engine policy contexts, Signing OCSP/TSA configuration, Key Vault for seal keys. **|**
**Failures & handling:** Dependency incidents cross-load into RB-AUDIT-004 and relevant service runbooks; audit posture cannot be marked green until dependencies restored. **|**
**Observability:** Dependency dashboards (Guardian judgments, immutable sink, TSA latency). **|**
**Breadcrumbs:** Guardian spec §7, Logging spec §3, Signer spec §4, LP Engine §5, Settings §7.3. **|**
**References:** ADR-0001 Guardian/waiver scope, ADR-0006 Immutable sink, ADR-0011 DSAR evidence.

______________________________________________________________________

## 10) References

- Technical Design Document §5 (artifact lifecycle) and §12 (summary)  
- Logging specification — `../platform/observability.md`  
- Guardian specification — `../platform/guardian.md` §7  
- Settings specification — `../platform/settings.md` §7.3–§7.4  
- Digital Signer specification — `../data/digital-signer.md` §4  
- Ops runbook catalog — `../ops/runbooks.md` (RB-AUDIT-004, RB-WAIVER-GOV, RB-PRIV-DSAR, RB-AUDIT-MANIFEST)  
- ADR index — `../adr/README.md` (ADR-0001, ADR-0006, ADR-0011)
