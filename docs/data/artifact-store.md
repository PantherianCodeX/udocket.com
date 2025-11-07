---
title: uDocket — Artifact Store Service Specification
subtitle: Case-Scoped Storage, Retention Gates, and Audit Trails
author:
  - Records Platform Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Engineering
  - Records & Compliance
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - Compliance Lead
  - SRE Manager
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
  - <header class="page-header">uDocket — Artifact Store Service Specification <br>
    Case-Scoped Storage, Retention Gates, and Audit Trails</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Records Platform Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Engineering; Records & Compliance |
| Reviewers | Compliance Lead; SRE Manager |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Defines the Artifact Store service that governs storage/media layout under `storage/media/tenants/<ORG_ID>/cases/<case_id>/`, lifecycle invariants for Source Assets/Work Products/Deliverables (TDD §5), retention/erasure workflows (TDD §14), and append-only ops ledgers used by downstream agents.
- **Structure:** Sections follow the 0–10 pattern: purpose and responsibilities, API/file interfaces, state management, failure handbooks, observability, security/compliance, operations, dependencies, and references. Appendices align with ExclusiveSwap invariants and retention tables described in TDD §5.4 and Appendix J.
- **Maintenance:** Run `python -m doc_tools.manage_docs --lint docs/data/artifact-store.md docs/overview/tdd.md docs/tdd_modularization.md` before submitting. Changes to storage layout or retention policy require synchronized updates to migration scripts and Appendix J tables.
- **Change protocol:** Any schema/layout change (directory naming, hash strategy, retention timers) must reference this spec, TDD §5.2–§5.4, Appendix J, and corresponding migrations. Deleting artifacts or altering retention flows also requires Security + Records approval.
- **References:** TDD §5 Artifact lifecycle, §14 Retention & Compliance, Appendix J SQL policy patterns, Guardian §5 quarantine governance, Compose §6 deliverable promotion rules, Ops runbooks `RB-ARTIFACT-*`.
- **Contacts:** Platform Engineering (artifact services), Records & Compliance (retention policy), on-call `storage-oncall@`, escalation `#ops-artifacts`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Preserve, version, and surface all case artifacts (SA/WP/CD/DL/AR) with deterministic naming, retention, and audit guarantees. **|**
**Contract:** Artifact Store enforces ExclusiveSwap for Deliverables, case-scoped directory layout, immutable hashes, and append-only ops ledgers while coordinating with Guardian and Compose approvals. **|**
**State:** Owns on-disk layout (`audio/`, `transcript/`, `analysis/`, `docs/`, `ops/`), artifact metadata tables, and ops audit streams. Version suffixes (`_v2`, `_v3`) ensure replays never overwrite prior outputs. **|**
**Failures & handling:** Hash drift, missing artifacts, or retention violations trigger Guardian/Records holds and Ops runbooks (`RB-ARTIFACT-CORRUPTION`, `RB-RETENTION-DRIFT`). **|**
**Observability:** Metrics `artifact_store_hash_mismatch_total`, `artifact_store_missing_file_total`, `artifact_retention_violation_total`; Grafana dashboard “Artifact Store Health”; Append-only logs aggregated under `ops/ops_artifacts.jsonl`. **|**
**Breadcrumbs:** Implementation `apps/platform/artifacts/store.py`, hashing utilities `packages/core/artifacts/hash.py`, retention workers `apps/platform/operations/task_modules/artifacts.py`, tests `tests/platform/artifacts/test_store.py`. **|**
**References:** TDD §5.2–§5.4, Appendix J (SQL policies), Appendix L (environment baselines).

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Enumerate the Artifact Store charter and delineate responsibilities across ingestion, promotion, retention, and audit. **|**
**Contract:** Guarantee artifact integrity, deterministic naming, retention enforcement, and audit traceability. **|**
**State:** Maintains artifact rows, file manifests, hash catalogues, and ops ledgers. **|**
**Failures & handling:** Highlight failure modes (hash drift, missing files, retention gaps) and runbooks. **|**
**Observability:** Metrics/dashboards verifying each duty. **|**
**Breadcrumbs:** Code/tests/automation sustaining responsibilities. **|**
**References:** TDD §5, §14, Guardian §5, Compose §6.

### 2.1 Case directory layout (binding)

- **Contract:** Every case stores artifacts under `storage/media/tenants/<ORG_ID>/cases/<case_id>/` with subdirectories `audio/`, `transcript/`, `analysis/`, `docs/`, `ops/`. Filenames follow `<job_id>__<artifact>[_vN].<ext>`. Layout changes require migration plans and Appendix updates. **|**
- **State:** Directory structure plus manifest table `artifact_file` linking database rows to filesystem paths and hashes. **|**
- **Observability:** `artifact_store_missing_file_total` and periodic reconciler jobs flag drift. **|**
- **Failures & handling:** Reconciler attempts rehydrate from cold storage; unresolved gaps escalate to `RB-ARTIFACT-CORRUPTION`. **|**
- **Breadcrumbs:** `apps/platform/artifacts/store.py::ArtifactStore`, migration `apps/platform/migrations/0042_artifact_file_manifest.py`, reconciler `apps/platform/operations/tasks/reconcile_artifacts.py`. **|**

### 2.2 Integrity & hashing (binding)

- **Contract:** Artifact writes compute SHA-256 (and MD5 when `BATCH_HASH_REMOTE=1`) captured in metadata and ops logs. Hash mismatches block promotion and trigger Guardian quarantine. **|**
- **State:** Hash catalog stored in `artifact_hash` table and JSON metadata under `ops/<job_id>__artifact_log.json`. **|**
- **Observability:** Metrics `artifact_store_hash_mismatch_total`, dashboards “Artifact Hash Integrity”. **|**
- **Failures & handling:** Recompute hash, compare with remote storage, escalate via `RB-ARTIFACT-CORRUPTION`. **|**
- **Breadcrumbs:** Hashing utilities `packages/core/artifacts/hash.py`, Celery task `apps/platform/operations/tasks/hash_artifacts.py`, tests `tests/platform/artifacts/test_hash_integrity.py`. **|**

### 2.3 Promotion & ExclusiveSwap (binding)

- **Contract:** Deliverable promotion uses ExclusiveSwap (TDD §5.4.1). Only one Deliverable is `RELEASED` per artifact lineage; new approvals swap status atomically while preserving audit history. **|**
- **State:** Database views `artifact_secure`, `deliverable_latest`, plus ops audit `ops/ops_artifacts.jsonl`. **|**
- **Observability:** Metrics `artifact_exclusive_swap_total`, audit check `ExclusiveSwapConsistencyCheck`. **|**
- **Failures & handling:** Swap conflicts roll back transaction, flag `artifact_promotion_conflict_total`, and require reviewer intervention. **|**
- **Breadcrumbs:** Promotion APIs `apps/platform/artifacts/service.py::promote_deliverable`, Compose integration `packages/core/agents/compose/*.py`, tests `tests/platform/artifacts/test_exclusive_swap.py`. **|**

### 2.4 Retention & erasure (binding)

- **Contract:** Enforce retention/eventual erasure per TDD §14 (ORG settings `compliance.erasure_mode`). Hard purge obeys approved DSAR workflows; soft delete retains audit journals. **|**
- **State:** Retention schedule table `artifact_retention`, DSAR ledger `dsar_request`. **|**
- **Observability:** Metrics `artifact_retention_overdue_total`, `artifact_erasure_total`; dashboards “Retention & DSAR”. **|**
- **Failures & handling:** Overdue erasures trigger `RB-RETENTION-DRIFT`; audit logs capture reason codes. **|**
- **Breadcrumbs:** Jobs `apps/platform/operations/tasks/process_retention.py`, DSAR tooling `apps/platform/compliance/dsar.py`, tests `tests/platform/compliance/test_retention.py`. **|**

______________________________________________________________________

## 3) API Contract

**Purpose:** Describe interfaces (HTTP, internal services, filesystem contracts). **|**
**Contract:** Artifact Store exposes service-layer APIs for upload/promotion, Celery tasks for retention, and deterministic filesystem contracts. **|**
**State:** Request/response payloads map to database rows and file manifests. **|**
**Failures & handling:** Define error codes, retries, conflict resolution. **|**
**Observability:** Track API latency, error rates, and queue depth. **|**
**Breadcrumbs:** Endpoint handlers, serializers, task modules. **|**
**References:** TDD §5.2.2, Appendix D artifact schemas.

### 3.1 External Interfaces (binding)

- `POST /api/cases/<case_id>/artifacts/` uploads Source Assets; expects pre-signed upload tokens and returns artifact metadata with hash commitments. **|**
- `POST /api/artifacts/<artifact_id>/promote/` promotes Work Products to Deliverables, enforcing ExclusiveSwap and Guardian approvals. **|**
- `POST /api/artifacts/<artifact_id>/delete/` enqueues DSAR erasure; available only when `compliance.erasure_mode='hard_purge'` and reviewer approved. **|**
- Error codes align with Appendix API index (`artifact-store` section). `CONFLICT` for ExclusiveSwap collisions, `POLICY_BLOCK` when Guardian or residency gates fail, `VALIDATION_ERROR` for schema mismatches. **|**
- Breadcrumbs: Views `apps/platform/artifacts/views.py`, serializers `apps/platform/artifacts/serializers.py`, integration tests `tests/platform/artifacts/test_api.py`. **|**

### 3.2 Internal Interfaces (binding)

- Celery topic `artifacts.retention` enforces retention windows; tasks idempotently operate via manifest snapshots. **|**
- Signals from Guardian/Compose update artifact states and ops audit logs (`ArtifactPromotionSignal`, `ArtifactHashMismatchSignal`). **|**
- Storage adapters (`packages/core/storage/`) abstract local vs. Azure Blob (batch). **|**

### 3.3 API Error Codes (binding)

**Purpose:** Document Artifact Store specific `ApiError.code` usage so callers know when to retry versus escalate. **|**
**Contract:** Artifact promotion/deletion piggyback on the platform catalog; Artifact Store introduces no new codes beyond the shared inventory documented here. **|**
**State:** Error catalog maintained in `docs/data/artifact-store/error_codes.yaml`; empty list indicates no service-specific extensions. **|**
**Failures & handling:** Platform codes map to Guardian/Settings/Compose remediations; no additional runbooks beyond those services. **|**
**Observability:** Unknown code emissions trigger `artifact_api_error_unknown_total`; dashboards reuse Platform Runtime §3.3 metrics. **|**
**Breadcrumbs:** REST handlers `apps/platform/artifacts/views.py`, serializer errors `apps/platform/artifacts/serializers.py`, audit streams `ops/ops_artifacts.jsonl`. **|**
**References:** Platform Runtime §3.3, Guardian §5, Settings §5.

> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#artifact-store-service)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | ExclusiveSwap detected an in-flight or newer deliverable/promotion for the same lineage. | Refresh artifact state, resolve outstanding approvals, and retry promotion after reviewers clear the conflict. |
| `POLICY_BLOCK` | Guardian, residency, or retention policy forbids writing or deleting the artifact. | Review Guardian verdicts, residency waivers, or retention windows; obtain approval before resubmitting. |
| `VALIDATION_ERROR` | Artifact metadata failed schema validation (hash mismatch, unsupported type, or missing manifest fields). | Fix the payload or recompute hashes locally before retrying the upload/promotion request. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | Yes | artifact_api_error_total<br>artifact_promotion_conflict_total |
| `POLICY_BLOCK` | 403 | Yes | artifact_api_error_total<br>artifact_retention_violation_total |
| `VALIDATION_ERROR` | 400 | No | artifact_api_error_total<br>artifact_store_hash_mismatch_total |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

______________________________________________________________________

## 4) State Management (binding)

**Purpose:** Explain how Artifact Store persists manifests, hashes, and retention metadata. **|**
**Contract:** Enforces immutable manifests post-promotion, write-once ops ledgers, and synchronized retention schedules across storage backends. **|**
**State:** Case directories, manifest tables, hash catalogs, DSAR ledgers, and ops JSONL streams. **|**
**Failures & handling:** Reconciler jobs heal drift; manual intervention required if cold storage restore fails. **|**
**Observability:** Metrics `artifact_manifest_drift_total`, `artifact_hash_recompute_total`, dashboards “Artifact Store Health”. **|**
**Breadcrumbs:** ORM models `apps/platform/artifacts/models.py`, migrations `apps/platform/migrations/`, retention jobs `apps/platform/operations/tasks/process_retention.py`. **|**
**References:** TDD §5.2–§5.4, Appendix J SQL policies, Settings Appendix A (`artifacts.*`).

- Artifact manifests store path, hash, size, creator, and version; RLS via `artifact_secure` restricts access by case/org. **|**
- Ops logs under `ops/<job_id>__artifact_log.json` include source job, hash, size, version, retention horizon, and DSAR references. **|**
- State transitions follow `STORED → PROCESSING → PENDING_JUDGMENT → CLEARED_FOR_USE/OPERATOR_PREP → RELEASED`. Deliverables add `SIGNED`/`ARCHIVED` per TDD §5.4. **|**
- Column-level masking hides PII fields for non-privileged roles; JSONB manifests store extra metadata but disallow arbitrary user writes. **|**

______________________________________________________________________

## 5) Failure Modes (binding)

**Purpose:** Summarise expected failure scenarios for Artifact Store and default mitigations. **|**
**Contract:** Fail closed on hash drift or missing files; resume automatically for capacity or retention backlog once resolved. **|**
**State:** Watchdog metrics, backlog queues, cold storage inventories. **|**
**Failures & handling:** Detectors escalate via RB-ARTIFACT-CORRUPTION/RB-RETENTION-DRIFT; capacity alerts trigger FinOps review. **|**
**Observability:** Alerts `artifact_store_hash_mismatch_total`, `artifact_retention_overdue_total`, Grafana board “Artifact Store Health”. **|**
**Breadcrumbs:** Runbooks `docs/ops/runbooks/artifacts/*.md`, incident retros in `ops/artifacts/incidents/`. **|**
**References:** TDD §5.4.1 ExclusiveSwap, Appendix J SQL policies.

- **Hash drift:** Detected via reconciler; triggers Guardian quarantine, hash recompute, potential re-ingest. **|**
- **Missing files:** Rehydrate from cold storage or re-run agent; escalate if immutable evidence lost. **|**
- **Retention backlog:** When `artifact_retention_overdue_total > 0` for 24h, block new DSAR approvals until backlog cleared. **|**
- **Storage capacity:** `artifact_storage_capacity_pct` > 80% triggers scaling plan and FinOps review. **|**
- **Corrupted ops logs:** Append-only JSONL validated via schema; corruption halts promotions and requires manual repair. **|**

______________________________________________________________________

## 6) Observability (binding)

**Purpose:** Detail telemetry required to monitor Artifact Store health. **|**
**Contract:** Maintain health dashboards with hash integrity, retention backlog, and capacity signals; emit structured audit logs for all promotions. **|**
**State:** Prometheus metrics, Grafana dashboards, audit logs, traces. **|**
**Failures & handling:** Alert fatigue mitigated via tuned burn rates; unknown metric gaps block releases. **|**
**Observability:** Dashboards “Artifact Store Health”, “Retention & DSAR”, `artifact_store_*` metrics. **|**
**Breadcrumbs:** Metrics module `apps/platform/artifacts/metrics.py`, tracing instrumentation `packages/core/telemetry/artifacts.py`. **|**
**References:** Observability spec §4, Appendix B metrics.

- Metrics: `artifact_store_hash_mismatch_total`, `artifact_store_missing_file_total`, `artifact_promotion_conflict_total`, `artifact_retention_overdue_total`, `artifact_storage_capacity_pct`. **|**
- Logs: Structured operations appended to `ops/ops_artifacts.jsonl` with deterministic fields (`case_id`, `artifact_id`, `job_id`, `hash_sha256`, `action`, `actor`). **|**
- Tracing: Promotion and retention tasks emit spans `artifact.promote`, `artifact.retention.sweep` with case + artifact tags. **|**
- Dashboards: “Artifact Store Health”, “Retention & DSAR”, “ExclusiveSwap Compliance”. **|**
- Alerts: Burn-rate alerts on hash mismatches, retention backlog, storage capacity; inform records & platform on-call. **|**

### 6.1 SLOs & Targets (binding)

**Purpose:** Capture artifact integrity and retention objectives. **|**
**Contract:** Maintain ≥99.9% hash verification success and zero overdue retention tasks beyond 24 h; ExclusiveSwap conflicts remain below 0.1% of promotions. **|**
**State:** Prometheus rules `infra/monitoring/artifacts-slo-rules.yaml`, burn-rate alerts, synthetic reconciler jobs. **|**
**Failures & handling:** SLO breaches trigger RB-ARTIFACT-CORRUPTION or RB-RETENTION-DRIFT; releases pause until evidence collected. **|**
**Observability:** Grafana “Artifact Store – SLO” with panels on hash mismatch rate, retention backlog, promotion conflicts. **|**
**Breadcrumbs:** SLO configuration `infra/monitoring/artifacts-slo.json`, tests `tests/integration/test_artifact_slo.py`. **|**
**References:** TDD Appendix I controls map, Appendix J SQL policies.

______________________________________________________________________

## 7) Security & Compliance (binding)

**Purpose:** Describe controls protecting artifacts, residency, and audit obligations. **|**
**Contract:** Enforce residency-aligned storage, deterministic hashes, RLS policies, and DSAR evidence capture. **|**
**State:** Secrets for storage endpoints, RLS policies, DSAR ledgers, audit trails. **|**
**Failures & handling:** Residency drift escalates via RB-RES-ENDPOINT; DSAR gaps halt approvals. **|**
**Observability:** Security alerts `artifact_residency_violation_total`, audit logs, compliance dashboards. **|**
**Breadcrumbs:** IAM configs `infra/terraform/storage`, policy scripts `scripts/security/artifact_residency_check.py`, audits `ops/compliance/artifacts/*.md`. **|**
**References:** Settings Appendix A keys `artifacts.*`, Guardian §5, TDD §14.2.

- Residency: Files stored in region-specific buckets; Azure SAS usage gated to the organization’s approved regions per settings `storage.region`. **|**
- Access: RLS policies enforce per-org + per-case access; Guard rails validated via Appendix J queries. **|**
- Encryption: Rest encryption via platform storage config; key rotation tracked in Appendix Q (sub-processors). **|**
- Audit: Ops logs retained for ≥7 years; append-only, with tamper-evident hashing pipeline. **|**
- DSAR: All erasures logged with `dsar_request_id`, reviewer approvals, and hash of deleted payload. **|**

______________________________________________________________________

## 8) Operational Notes (binding)

**Purpose:** Summarize how Artifact Store is operated day-to-day. **|**
**Contract:** Maintain staffed on-call rotations, documented runbooks, and drill cadence before enabling production changes. **|**
**State:** Infra manifests, automation scripts, drill evidence, pager schedules. **|**
**Failures & handling:** Runbook drift or missed drills block releases until remediated. **|**
**Observability:** Deployment dashboards, runbook freshness checks, drill scheduler. **|**
**Breadcrumbs:** Terraform modules `infra/terraform/artifact_store`, runbooks `docs/ops/runbooks/artifacts/*.md`, automation scripts `scripts/ops/artifacts/*.py`. **|**
**References:** Ops catalog, TDD §12 operations.

- Primary runbooks: `RB-ARTIFACT-CORRUPTION`, `RB-RETENTION-DRIFT`, `RB-ARTIFACT-CAPACITY`. **|**
- Drills: Semi-annual artifact integrity reconciliation; quarterly retention playback using synthetic cases. Evidence stored under `ops/artifacts/drills/<date>/`. **|**
- Ops tooling: `scripts/ops/check_artifact_hashes.py`, `scripts/ops/retention_backlog.py`, dashboards referenced above. **|**
- On-call: `storage-oncall@`, escalation `#ops-artifacts`, war room `#incident-artifacts` when severity ≥2. **|**

### 8.1 Operational Posture (binding)

**Purpose:** Describe staffing, maintenance windows, and readiness expectations. **|**
**Contract:** Platform Engineering and Records & Compliance share the primary rotation with <5 min acknowledge and 30 min mitigation targets; maintenance window every Wednesday 02:00–04:00 PT. **|**
**State:** On-call roster `ops/artifacts/rota.md`, readiness checklist `ops/artifacts/checklists/operational_posture.md`, maintenance calendar `ops/change/artifacts.ics`. **|**
**Failures & handling:** Coverage gaps escalate to Records leadership; releases pause until readiness checklist completed. **|**
**Observability:** PagerDuty analytics, staffing dashboard “Artifact Ops Posture”, docs lint `docs_staffing_posture_missing_total`. **|**
**Breadcrumbs:** Runbook overview `docs/ops/runbooks/artifacts/README.md`, staffing policy `ops/artifacts/policies/staffing.md`. **|**
**References:** Ops catalog, Appendix S roles.

### 8.2 Incident Triggers (binding)

**Purpose:** Enumerate alerts that declare Artifact Store incidents. **|**
**Contract:** Alerts on hash mismatches, retention backlog, storage capacity, and unknown API errors must page on-call; synthetic reconciler failures escalate immediately. **|**
**State:** Alert definitions `infra/monitoring/artifact-alerts.yaml`, synthetic job `scripts/ops/check_artifact_hashes.py`, cold storage monitors. **|**
**Failures & handling:** False positives tuned via SRE review; silent failures trigger governance remediation. **|**
**Observability:** Dashboards “Artifact Store Health”, alert `artifact_store_hash_mismatch_total`, Ops catalog `RB-ARTIFACT-CORRUPTION`. **|**
**Breadcrumbs:** Alert rules, PagerDuty services, runbook catalog entries. **|**
**References:** §5 Failure Modes, RB-ARTIFACT-CORRUPTION, RB-RETENTION-DRIFT, RB-ARTIFACT-CAPACITY.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Capture the authoritative runbook set for Artifact Store incidents. **|**
**Contract:** Alerts map to RB-ARTIFACT-\* identifiers; drills rehearse corruption, retention backlog, and capacity events quarterly. **|**
**State:** Runbooks under `docs/ops/runbooks/artifacts/`, drill evidence `ops/artifacts/drills/<date>/`. **|**
**Failures & handling:** Missing evidence prevents change approvals; docs lint flags outdated runbooks. **|**
**Observability:** Runbook catalog, drill scheduler metrics, compliance dashboards. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler, Slack `#ops-artifacts`. **|**
**References:** `RB-ARTIFACT-CORRUPTION`, `RB-RETENTION-DRIFT`, `RB-ARTIFACT-CAPACITY`.

#### 8.3.1 Runbook Index (informative)

| Runbook code | Scenario | Notes |
| --- | --- | --- |
| `RB-ARTIFACT-CORRUPTION` | Hash drift, corrupted manifests | Includes cold storage restore checklist |
| `RB-RETENTION-DRIFT` | Retention backlog / DSAR delay | Coordinates Records approvals and evidence |
| `RB-ARTIFACT-CAPACITY` | Storage saturation / quota breach | Triggers scaling plan and FinOps review |

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarize playbooks responders execute during incidents. **|**
**Contract:** Keep runbooks versioned, reviewed quarterly, and linked to alerts. **|**
**State:** Markdown under `docs/ops/runbooks/artifacts/*.md`, automation `scripts/ops/artifacts/*.py`. **|**
**Failures & handling:** Stale runbooks flagged by docs lint `runbook_catalog_stale_total`. **|**
**Observability:** Governance dashboard, runbook catalog output. **|**
**Breadcrumbs:** Runbook files, automation scripts, incident templates. **|**
**References:** `RB-ARTIFACT-CORRUPTION`, `RB-RETENTION-DRIFT`, `RB-ARTIFACT-CAPACITY`.

- `RB-ARTIFACT-CORRUPTION` — Hash drift/corruption recovery, cold storage restore, audit evidence capture. **|**
- `RB-RETENTION-DRIFT` — Retention backlog remediation, DSAR reconciliation, approvals. **|**
- `RB-ARTIFACT-CAPACITY` — Storage saturation response, scaling plans, FinOps notifications. **|**

#### 8.3.3 Drill Cadence & Evidence (binding)

Quarterly drills ensure integrity/retention procedures stay executable and evidence remains accessible. **|**

- Semi-annual integrity drill verifying hash reconciler recovery. **|**
- Quarterly retention playback using synthetic DSAR cases. **|**
- Evidence stored in `ops/artifacts/drills/<date>/summary.md` with metrics snapshots and archived under `ops/artifac../data/<date>/` with Grafana exports. **|**
- Compliance reviews sample evidence quarterly; gaps trigger remediation tasks surfaced by `docs_runbook_evidence_missing_total`. **|**

See Ops catalog and Appendix O decision log for templates and evidence requirements.

### 8.4 Migrations & Backfills (binding)

**Purpose:** Document schema/data migrations supporting Artifact Store. **|**
**Contract:** Execute migrations via change-managed scripts with hash verification and rollback checkpoints. **|**
**State:** Migration manifests `ops/artifacts/migrations/`, replay tooling `scripts/ops/artifacts_replay.py`. **|**
**Failures & handling:** Failed migrations roll back using manifest snapshots; incidents recorded with evidence. **|**
**Observability:** Migration dashboards monitor progress and error counts. **|**
**Breadcrumbs:** Migration scripts, change calendars, ADR-0005 (artifact hash policy). **|**
**References:** TDD §5.4, Appendix J SQL policies.

### 8.5 Operational Workflows (binding)

**Purpose:** Describe recurring tasks such as retention sweeps and hash reconciliations. **|**
**Contract:** Weekly hash reconciliation, monthly retention audit, quarterly DSAR review executed with evidence stored alongside logs. **|**
**State:** Checklists `ops/artifacts/workflows/*.md`, automation outputs `ops/artifacts/reports/*.csv`. **|**
**Failures & handling:** Missed workflows trigger alert `artifact_workflow_overdue_total` and block releases. **|**
**Observability:** Workflow dashboard, docs lint, FinOps storage monitoring. **|**
**Breadcrumbs:** Workflow docs, automation scripts, staffing rosters. **|**
**References:** Compliance playbooks, Ops catalog.

______________________________________________________________________

## 9) Dependencies (binding)

**Purpose:** Enumerate upstream/downstream relationships shaping Artifact Store contracts. **|**
**Contract:** Maintain API compatibility and monitoring expectations for each dependency; update this table when new services integrate. **|**
**State:** Dependency metadata stored in Platform Runtime catalog; manifests reference service ownership. **|**
**Failures & handling:** Dependency incidents coordinate via linked runbooks; missing catalog entries block releases. **|**
**Observability:** Cross-service dashboards track dependency health metrics. **|**
**Breadcrumbs:** Platform Runtime service catalog, Settings `artifacts.*`, Ops runbook catalog. **|**
**References:** Platform Runtime §3, Settings Appendix A (`artifacts.*` keys), Guardian §5, Compose spec.

| Dependency | Responsibility | Notes |
| --- | --- | --- |
| Settings Registry | Retention windows, residency toggles, hash requirements | Keys `artifacts.retention.*`, `artifacts.residency.region` |
| Guardian | Quarantine decisions, hash validation, blocklist enforcement | Guardian PASS/WARN gating promotions |
| Compose service | Deliverable promotion inputs/outputs, signature pipelines | Requires stable file manifests |
| Storage subsystem | Object storage backend (local path/Azure Blob) | Abstraction `packages/core/storage` ensures deterministic writes |
| Worker Cluster | Retention sweeps, hash reconciliation tasks | Celery queue `artifacts.retention` |
| Ops runbook catalog | Incident handling and drills | Docs lint ensures RB-ARTIFACT entries updated |

______________________________________________________________________

## 10) References

- TDD §5 Artifact lifecycle and ExclusiveSwap invariant.
- TDD §14 Retention, DSAR, and erasure governance.
- Settings Registry specification — `../platform/settings.md`.
- Guardian specification — `../platform/guardian.md`.
- Compose specification — `../automation/langgraph-agents.md`.
- Ops runbook catalog — `../ops/runbooks.md`.
- Appendix J — SQL policy patterns (artifact RLS/masking).
