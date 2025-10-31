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

- **Scope:** Defines the Artifact Store service that governs storage/media layout under `storage/media/cases/<case_id>/`, lifecycle invariants for Source Assets/Work Products/Deliverables (TDD §5), retention/erasure workflows (TDD §14), and append-only ops ledgers used by downstream agents.
- **Structure:** Sections follow the 0–10 pattern: purpose and responsibilities, API/file interfaces, state management, failure handbooks, observability, security/compliance, operations, dependencies, and references. Appendices align with ExclusiveSwap invariants and retention tables described in TDD §5.4 and Appendix J.
- **Maintenance:** Run `python scripts/docs/lint_docs.py docs/src/services/artifact-store.md docs/src/overview/tdd.md docs/tdd_modularization.md` before submitting. Changes to storage layout or retention policy require synchronized updates to migration scripts and Appendix J tables.
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
**Breadcrumbs:** Implementation `apps/platform/artifacts/store.py`, hashing utilities `packages/udocket_core/artifacts/hash.py`, retention workers `apps/platform/operations/task_modules/artifacts.py`, tests `tests/platform/artifacts/test_store.py`. **|**
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

- **Contract:** Every case stores artifacts under `storage/media/cases/<case_id>/` with subdirectories `audio/`, `transcript/`, `analysis/`, `docs/`, `ops/`. Filenames follow `<job_id>__<artifact>[_vN].<ext>`. Layout changes require migration plans and Appendix updates. **|**
- **State:** Directory structure plus manifest table `artifact_file` linking database rows to filesystem paths and hashes. **|**
- **Observability:** `artifact_store_missing_file_total` and periodic reconciler jobs flag drift. **|**
- **Failures & handling:** Reconciler attempts rehydrate from cold storage; unresolved gaps escalate to `RB-ARTIFACT-CORRUPTION`. **|**
- **Breadcrumbs:** `apps/platform/artifacts/store.py::ArtifactStore`, migration `apps/platform/migrations/0042_artifact_file_manifest.py`, reconciler `apps/platform/operations/tasks/reconcile_artifacts.py`. **|**

### 2.2 Integrity & hashing (binding)

- **Contract:** Artifact writes compute SHA-256 (and MD5 when `BATCH_HASH_REMOTE=1`) captured in metadata and ops logs. Hash mismatches block promotion and trigger Guardian quarantine. **|**
- **State:** Hash catalog stored in `artifact_hash` table and JSON metadata under `ops/<job_id>__artifact_log.json`. **|**
- **Observability:** Metrics `artifact_store_hash_mismatch_total`, dashboards “Artifact Hash Integrity”. **|**
- **Failures & handling:** Recompute hash, compare with remote storage, escalate via `RB-ARTIFACT-CORRUPTION`. **|**
- **Breadcrumbs:** Hashing utilities `packages/udocket_core/artifacts/hash.py`, Celery task `apps/platform/operations/tasks/hash_artifacts.py`, tests `tests/platform/artifacts/test_hash_integrity.py`. **|**

### 2.3 Promotion & ExclusiveSwap (binding)

- **Contract:** Deliverable promotion uses ExclusiveSwap (TDD §5.4.1). Only one Deliverable is `RELEASED` per artifact lineage; new approvals swap status atomically while preserving audit history. **|**
- **State:** Database views `artifact_secure`, `deliverable_latest`, plus ops audit `ops/ops_artifacts.jsonl`. **|**
- **Observability:** Metrics `artifact_exclusive_swap_total`, audit check `ExclusiveSwapConsistencyCheck`. **|**
- **Failures & handling:** Swap conflicts roll back transaction, flag `artifact_promotion_conflict_total`, and require reviewer intervention. **|**
- **Breadcrumbs:** Promotion APIs `apps/platform/artifacts/service.py::promote_deliverable`, Compose integration `packages/udocket_core/agents/compose/*.py`, tests `tests/platform/artifacts/test_exclusive_swap.py`. **|**

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

### 3.1 External interfaces (binding)

- `POST /api/cases/<case_id>/artifacts/` uploads Source Assets; expects pre-signed upload tokens and returns artifact metadata with hash commitments. **|**
- `POST /api/artifacts/<artifact_id>/promote/` promotes Work Products to Deliverables, enforcing ExclusiveSwap and Guardian approvals. **|**
- `POST /api/artifacts/<artifact_id>/delete/` enqueues DSAR erasure; available only when `compliance.erasure_mode='hard_purge'` and reviewer approved. **|**
- Error codes align with Appendix API index (`artifact-store` section). `CONFLICT` for ExclusiveSwap collisions, `POLICY_BLOCK` when Guardian or residency gates fail, `VALIDATION_ERROR` for schema mismatches. **|**
- Breadcrumbs: Views `apps/platform/artifacts/views.py`, serializers `apps/platform/artifacts/serializers.py`, integration tests `tests/platform/artifacts/test_api.py`. **|**

### 3.2 Internal hooks (binding)

- Celery topic `artifacts.retention` enforces retention windows; tasks idempotently operate via manifest snapshots. **|**
- Signals from Guardian/Compose update artifact states and ops audit logs (`ArtifactPromotionSignal`, `ArtifactHashMismatchSignal`). **|**
- Storage adapters (`packages/udocket_core/storage/`) abstract local vs. Azure Blob (batch). **|**

______________________________________________________________________

## 4) State Management (binding)

- Artifact manifests store path, hash, size, creator, and version; RLS via `artifact_secure` restricts access by case/org. **|**
- Ops logs under `ops/<job_id>__artifact_log.json` include source job, hash, size, version, retention horizon, and DSAR references. **|**
- State transitions follow `STORED → PROCESSING → PENDING_JUDGMENT → CLEARED_FOR_USE/OPERATOR_PREP → RELEASED`. Deliverables add `SIGNED`/`ARCHIVED` per TDD §5.4. **|**
- Column-level masking hides PII fields for non-privileged roles; JSONB manifests store extra metadata but disallow arbitrary user writes. **|**

______________________________________________________________________

## 5) Failure modes & resiliency (binding)

- **Hash drift:** Detected via reconciler; triggers Guardian quarantine, hash recompute, potential re-ingest. **|**
- **Missing files:** Rehydrate from cold storage or re-run agent; escalate if immutable evidence lost. **|**
- **Retention backlog:** When `artifact_retention_overdue_total > 0` for 24h, block new DSAR approvals until backlog cleared. **|**
- **Storage capacity:** `artifact_storage_capacity_pct` > 80% triggers scaling plan and FinOps review. **|**
- **Corrupted ops logs:** Append-only JSONL validated via schema; corruption halts promotions and requires manual repair. **|**

______________________________________________________________________

## 6) Observability (binding)

- Metrics: `artifact_store_hash_mismatch_total`, `artifact_store_missing_file_total`, `artifact_promotion_conflict_total`, `artifact_retention_overdue_total`, `artifact_storage_capacity_pct`. **|**
- Logs: Structured operations appended to `ops/ops_artifacts.jsonl` with deterministic fields (`case_id`, `artifact_id`, `job_id`, `hash_sha256`, `action`, `actor`). **|**
- Tracing: Promotion and retention tasks emit spans `artifact.promote`, `artifact.retention.sweep` with case + artifact tags. **|**
- Dashboards: “Artifact Store Health”, “Retention & DSAR”, “ExclusiveSwap Compliance”. **|**
- Alerts: Burn-rate alerts on hash mismatches, retention backlog, storage capacity; inform records & platform on-call. **|**

______________________________________________________________________

## 7) Security & compliance (binding)

- Residency: Files stored in region-specific buckets; Azure SAS usage gated to Canada regions per settings `storage.region`. **|**
- Access: RLS policies enforce per-org + per-case access; Guard rails validated via Appendix J queries. **|**
- Encryption: Rest encryption via platform storage config; key rotation tracked in Appendix Q (sub-processors). **|**
- Audit: Ops logs retained for ≥7 years; append-only, with tamper-evident hashing pipeline. **|**
- DSAR: All erasures logged with `dsar_request_id`, reviewer approvals, and hash of deleted payload. **|**

______________________________________________________________________

## 8) Operations & runbooks (binding)

- Primary runbooks: `RB-ARTIFACT-CORRUPTION`, `RB-RETENTION-DRIFT`, `RB-ARTIFACT-CAPACITY`. **|**
- Drills: Semi-annual artifact integrity reconciliation; quarterly retention playback using synthetic cases. Evidence stored under `ops/artifacts/drills/<date>/`. **|**
- Ops tooling: `scripts/ops/check_artifact_hashes.py`, `scripts/ops/retention_backlog.py`, dashboards referenced above. **|**
- On-call: `storage-oncall@`, escalation `#ops-artifacts`, war room `#incident-artifacts` when severity ≥2. **|**

______________________________________________________________________

## 9) Dependencies (binding)

| Dependency | Responsibility | Notes |
| --- | --- | --- |
| Settings Registry | Retention windows, residency toggles, hash requirements | Keys `artifacts.retention.*`, `artifacts.residency.region` |
| Guardian | Quarantine decisions, hash validation, blocklist enforcement | Guardian PASS/WARN gating promotions |
| Compose service | Deliverable promotion inputs/outputs, signature pipelines | Requires stable file manifests |
| Storage subsystem | Object storage backend (local path/Azure Blob) | Abstraction `packages/udocket_core/storage` ensures deterministic writes |
| Worker Cluster | Retention sweeps, hash reconciliation tasks | Celery queue `artifacts.retention` |
| Ops runbook catalog | Incident handling and drills | Docs lint ensures RB-ARTIFACT entries updated |

______________________________________________________________________

## 10) References

- TDD §5 Artifact lifecycle and ExclusiveSwap invariant.
- TDD §14 Retention, DSAR, and erasure governance.
- Settings Registry specification — `../services/settings.md`.
- Guardian specification — `../services/guardian.md`.
- Compose specification — `../services/langgraph-agents.md`.
- Ops runbook catalog — `../ops/runbooks.md`.
- Appendix J — SQL policy patterns (artifact RLS/masking).

