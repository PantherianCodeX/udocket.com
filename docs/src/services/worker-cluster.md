---
title: uDocket — Worker Cluster Specification
subtitle: Job Orchestration, Watchdogs, and Background Operations
author:
  - Worker Cluster Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-23
owners:
  - Platform Engineering
  - Operations Engineering
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - SRE Manager
  - Applied AI Programs
adr_index: docs/adr/README.md
related_adrs:
  - ADR-0001-guardian-ready-quarantine.md
  - ADR-0003-api-versioning-and-sunset.md
  - ADR-0004-localization-and-policy-engine.md
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
  - <header class="page-header">uDocket — Worker Cluster Specification <br>
    Job Orchestration, Watchdogs, and Background Operations</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document controls

| Field          | Value |
| -------------- | ----- |
| Version        | 0.1-draft |
| Status         | Implementable |
| Last updated   | 2025-10-28 |
| Primary owners | Platform Engineering; Operations Engineering |
| Approvers      | Architecture Steering Committee; Security Review Board |
| Reviewers      | SRE Manager; Applied AI Programs |
| Approved by    | |
| Approved date  | |

**Status:** KEP: Provisional → Implementable → Implemented

**Section Requirements (binding):**
    - Preamble: Purpose/Contract/State/Failure/Observability/References/Breadcrumbs (`scripts/docs/lint_docs.py --check-template`)
    - Section tags: `(binding)`, `(normative)` or `(informative)`
    - Links resolve: §/App./ADR (`docs-link-check`)
    - Document validation: `python scripts/docs/lint_docs.py` (see `docs/README.md` for tooling)
    - Settings keys: Document/code are in-sync
    - All requirements are CI gated

**Section tags:**
    - `(binding)` denotes requirements that block launch until implemented and tested.
    - `(normative)` captures default behaviors that may evolve via waivers or roadmap.
    - `(informative)` provides background or examples.
    - When a subsection omits a tag it is treated as informative by default—add the explicit tag when the content carries binding or normative weight.

______________________________________________________________________

## Reading guide

- **Scope:** Celery workers, beat schedulers, and task modules that execute agent pipelines, storage operations, notifications, watchdogs, and backfills. Covers queue topology, retries, residency enforcement, settings snapshots, and observability.
- **Structure:** Follows the standard 0–10 template. Responsibilities (§2) describe orchestration, queue management, watchdog automation, and provider integrations. APIs (§3) reference task entry points, job control RPC endpoints, and SSE updates. State, failure, observability, security, and ops guidance live in §§4–8.
- **Maintenance:** Run `python scripts/docs/lint_docs.py docs/src/services/worker-cluster.md docs/src/overview/tdd.md docs/tdd_modularization.md` plus `build_runbook_catalog.py --check` before landing worker changes. Update task-module AGENTS guides when adding queues or long-running jobs.
- **Change protocol:** Celery queue additions, watchdog changes, provider adapter updates, or retry semantics must reference this spec and note affected Settings keys. Provider failover logic requires Security + Architecture approval.
- **References:** TDD §12 summary, Transcription agent spec, Notifications spec, Guardian spec, Settings Registry keys (`jobs.*`, `watchdog.*`), Ops runbooks RB-JOB-WATCHDOG, RB-LOCK-006.
- **Contacts:** Platform Engineering (queue topology), Operations Engineering (KEDA/scaling), Applied AI Programs (agent orchestration), `#worker-cluster` Slack, on-call `workers-oncall@`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Coordinate all background jobs—agent pipelines, notifications, watchdogs, backfills—while enforcing policy, residency, and reproducibility guarantees. **|**
**Contract:** Workers consume durable queues, propagate Settings snapshots, emit structured telemetry, and surface SSE/job updates with deterministic state transitions. **|**
**State:** Job manifests, checkpoints, watchdog tables, advisory locks, Settings snapshots, audit JSON/JSONL logs, and DLQs. **|**
**Failure modes & handling:** Provider outages, queue backlogs, watchdog stalls, or RLS guard failures trigger runbooks and pause processing safely. **|**
**Observability:** Dashboards “Worker Queues”, “Watchdog Runner”, “Job Progress”, metrics `celery_queue_depth`, `job_duration_seconds`, `watchdog_runner_lag_seconds`, `job_watchdog_warning_total`. **|**
**References:** §2 Responsibilities, §4 State management, §5 Failure modes, §7 Security & compliance, Ops runbooks RB-JOB-WATCHDOG/RB-LOCK-006. **|**
**Breadcrumbs:** Celery config `apps/platform/operations/tasks.py`, task modules `apps/platform/operations/task_modules/*`, beat scheduler `apps/platform/operations/bootstrap.py`, watchdog runner `apps/platform/operations/watchdogs.py`, tests `tests/platform/operations/test_watchdogs.py`, `tests/platform/jobs/test_provider_progress_adapter.py`. **|**

______________________________________________________________________

## 2) Responsibilities

### 2.1 Agent orchestration & job lifecycle (binding)

**Purpose:** Execute Transcribe/Analyze/Compose and related agents with reproducibility and policy compliance. **|**
**Contract:** Tasks load Settings snapshots, resolve provider capabilities, and write manifests (`job_manifest`, `job_checkpoint`) with `{settings_snapshot_sha256, retry_token, retry_generation}` for every run. **|**
**State:** Artifacts, manifests, `job_checkpoint.progress_meta`, ops logs (`ops/<job_id>__*.jsonl`). **|**
**Failure modes & handling:** Capability mismatches or provider failures trigger parity-aware failover (`ModelFailoverOrchestrator`, `SpeechFailoverController`); exhausted fallback chain pauses jobs (`PAUSED_AWAITING_PROVIDER`) via RB-LLM-003. **|**
**Observability:** Metrics `job_duration_seconds{lane}`, `provider_progress_percent_complete`, `job_retry_total`; SSE `job.update` events include `provider_progress`. **|**
**Breadcrumbs:** Task modules `apps/platform/operations/task_modules/analyze.py`, `compose.py`, `transcribe.py`; capability map `packages/udocket_core/llm/registry.py`, speech failover `packages/udocket_core/failover/speech.py`; tests `tests/platform/jobs/test_provider_progress_adapter.py`. **|**
**References:** LLM registry spec §2.1–§2.3, Transcription agent doc, Notifications spec §2.1.

- Workers run prefork Celery pools with dedicated queues per agent class; queue names encode priority (`analyze-high`, `compose-default`, `backfill-low`).
- Settings snapshots accompany every job to guarantee replay parity and are persisted alongside manifests.
- Provider adapters expose normalized progress snapshots; SSE payloads map to UI badges.
- Speech fallback controller manages multi-provider equivalence (WER/diarization parity, residency attestation) and track merge workflows when channels exceed provider support.

### 2.2 Queue topology, scaling, and DLQ management (binding)

**Purpose:** Maintain reliable queue processing with autoscaling and bounded retries. **|**
**Contract:** Queues leverage KEDA scaling based on `celery_queue_depth`; workers enforce OCC (`FOR UPDATE SKIP LOCKED`) for outbox/delivery tasks and bounded retry counts. DLQs capture poison messages with remediation workflow. **|**
**State:** Primary queues, DLQ tables (`*_dlq`), retry counters, Celery beat schedules. **|**
**Failure modes & handling:** Queue backlog alerts page SRE; DLQ backlog triggers RB-JOB-WATCHDOG or RB-NOTIFY-OUTAGE depending on queue type. **|**
**Observability:** Metrics `celery_queue_depth{queue}`, `celery_task_retry_total`, `dlq_messages_total`, `keda_scaler_events_total`. **|**
**Breadcrumbs:** Celery config `apps/platform/operations/bootstrap.py`, scaling manifests `infra/kubernetes/workers/`, tests `tests/platform/operations/test_queue_backpressure.py`. **|**
**References:** Notifications spec §2.1, Settings Registry keys `jobs.queues.*`, Ops runbook catalog (queue remediation).

- Prefork pool defaults: `minReplicas=2`, `maxReplicas=10`, CPU target 70%; KEDA triggers on queue depth thresholds (default 25/50/100).
- Beat schedules manage periodic tasks (watchdogs, residency scanners, integrity checks); schedule metadata recorded in ops telemetry.
- DLQ consumers run under `notifications.generate_digest` or ad-hoc remediation tasks to re-queue after human review.

### 2.3 Watchdog runner & automation (binding)

**Purpose:** Detect stalled jobs, guardian backlog, advisory lock leaks, and integrity issues automatically. **|**
**Contract:** `watchdog-runner` Celery beat executes every minute, invoking configured watchdog tasks; failures emit SSE warnings and escalate per RB-JOB-WATCHDOG. **|**
**State:** Watchdog heartbeat table, ops logs `ops/watchdog/<date>.jsonl`, metrics. **|**
**Failure modes & handling:** Missed heartbeats (`watchdog_runner_missed_total`) require manual invocation and remediation before re-enabling automation. **|**
**Observability:** Metrics `watchdog_runner_lag_seconds`, `watchdog_runner_missed_total`, `job_watchdog_warning_total`, `udlock_watchdog_stale_total`. **|**
**Breadcrumbs:** Watchdog definitions `apps/platform/operations/watchdogs.py`, tests `tests/platform/operations/test_watchdogs.py`, runbook RB-JOB-WATCHDOG, RB-LOCK-006. **|**
**References:** Guardian spec §5 (backlog), Settings Registry `watchdog.*`.

### 2.4 Notifications & back-office pipelines (binding)

**Purpose:** Fan out notification deliveries, upload scanning, case imports, and backfills via shared worker infrastructure. **|**
**Contract:** Task modules enforce idempotency (`retry_token`, advisory locks) and integrate with Notifications service for outbox events. **|**
**State:** `outbox_delivery`, `delivery_receipt`, upload sessions, case import manifests, backfill logs. **|**
**Failure modes & handling:** Upload scanning failures quarantine staging blobs; case import errors halt portal exposure pending human review. **|**
**Observability:** Metrics `delivery_success_ratio`, `upload_scan_duration_seconds`, `case_import_duration_seconds`, `backfill_progress_percent`; audit events `CASE_IMPORT_ATTEMPT`, `UPLOAD_SCAN_FAILED`. **|**
**Breadcrumbs:** Task modules `apps/platform/operations/task_modules/files.py`, `notifications.py`, case import scripts `scripts/import/validate_case_bundle.py`, tests `tests/platform/files/test_upload_scan.py`. **|**
**References:** Notifications spec, Ops runbook RB-UPLOAD-SCAN, Settings keys `upload.scan.*`.

### 2.5 Provider integration & capability registry (binding)

**Purpose:** Abstract provider capabilities (LLM, speech) with parity validation and residency enforcement. **|**
**Contract:** Capability registry maps provider metadata to execution plans; activation requires evaluation digests and residency attestations. Workers use controllers to ensure fallback chains honor parity and policy. **|**
**State:** Capability cache, parity evidence hashes, Settings `llm.models[]`, `speech.providers[]`. **|**
**Failure modes & handling:** Missing parity evidence blocks activation; drift triggers `PROVIDER_DATA_POLICY_DRIFT` and opens circuits. **|**
**Observability:** Metrics `llm_region_fallback_total`, `speech_failover_attempt_total`, synthetic probes `synthetics/llm_residency.yaml`. **|**
**Breadcrumbs:** Capability map `packages/udocket_core/llm/registry.py`, speech controller `packages/udocket_core/failover/speech.py`, tests `tests/udocket_core/llm/test_registry.py`, `tests/udocket_core/speech/test_failover.py`. **|**
**References:** LLM registry spec §2.1–§2.3, Transcription agent spec.

______________________________________________________________________

## 3) API contract

**Purpose:** Document interfaces for enqueueing jobs, controlling runs, and surfacing progress. **|**
**Contract:** Job creation (`POST /api/v1/cases/{case_id}/jobs/{kind}`) returns `retry_token`; control endpoints (`pause`, `resume`, `cancel`, `retry`) require OCC and idempotency keys. Workers publish SSE `job.update` events with schema-versioned payloads. **|**
**State:** HTTP APIs mutate job rows, manifests, and checkpoints; Celery tasks consume queue messages; SSE topics broadcast updates. **|**
**Failure modes & handling:** Missing or stale idempotency keys return `409`; unsupported controls produce `400`; retries limited by policy. **|**
**Observability:** API metrics `job_control_request_total{action}`, SSE monitor `job_sse_schema_mismatch_total`, audit `JOB_*` events. **|**
**Breadcrumbs:** API handlers `apps/platform/jobs/views.py`, SSE publisher `apps/platform/events/jobs.py`, schema fixtures `spec/schemas/job_event.schema.json`. **|**
**References:** TDD §10 (job APIs), Notifications spec (outbox endpoints).

### 3.1 Task modules & entry points

- Primary tasks located in `apps/platform/operations/task_modules/*.py`; each module declares queue bindings, retry policies, and capability requirements.
- Beat schedules defined in `apps/platform/operations/bootstrap.py`; scheduling changes require documentation updates and runbook references.

### 3.2 Job control endpoints

- `POST /api/v1/jobs/{id}:pause|resume|cancel|retry` enforce OCC on `version`, require `Idempotency-Key`, and propagate `retry_token` to keep retries idempotent.
- Responses include current status, warnings (`BUDGET_HELD`, `REGION_DRIFT`), and updated `retry_generation`.

______________________________________________________________________

## 4) State management

- Job manifests (`job_manifest`) persist settings snapshot hashes, fallback reason codes, retry metadata, and artifact linkage.
- Checkpoints store progress meta JSON (provider progress percent, estimated remaining seconds) and SSE replay cursors.
- DLQ tables capture serialized payloads, failure reason, and retry counts; ops scripts drain after remediation.
- Watchdog heartbeat table records last execution per task; SSE references this data for dashboard displays.
- Upload sessions maintain resumable upload metadata and status transitions; expired sessions purged hourly alongside staging object deletion.

______________________________________________________________________

## 5) Failure modes

- **Provider outage:** Fallback controller advances to next healthy model; if chain exhausted, jobs enter `PAUSED_AWAITING_PROVIDER` with alerts (`alert_llm_circuit_open`); RB-LLM-003 executed.
- **Queue backlog / DLQ growth:** Alerts `celery_queue_depth_high` and `dlq_messages_total` escalate; workers throttled, DLQ drained following RB-JOB-WATCHDOG or notifications runbooks.
- **Watchdog stall:** Metrics `watchdog_runner_missed_total` > 0 triggers PagerDuty; automation paused until manual run confirms healthy state.
- **RLS context failure:** `rls_context_assert()` exceptions abort tasks; incidents logged as `RLS_CONTEXT_MISSING` and require bootstrap fix before resuming queue.
- **Upload scanning failure:** Files quarantined; RB-UPLOAD-SCAN executed before reprocessing.

______________________________________________________________________

## 6) Observability

- Metrics: `celery_queue_depth{queue}`, `job_duration_seconds`, `job_retry_total`, `job_watchdog_warning_total`, `watchdog_runner_lag_seconds`, `delivery_success_ratio`, `upload_scan_duration_seconds`, `case_import_duration_seconds`.
- Logs: Structured `WORKER_TASK`, `JOB_PROGRESS`, `WATCHDOG_RUN`, `DLQ_EVENT` with correlation IDs and masked fields; error-level duplicates to stderr only.
- Traces: Workers propagate W3C trace context via Celery headers; spans tagged with `{queue, task_name, retry}`; sampling 15% baseline, 100% on errors.
- Dashboards: “Worker Queues”, “Watchdog Runner”, “Job Progress”, “Upload Scanning”, “Case Import”; synthetic monitors verify watchdog heartbeat and SSE schema versions.

______________________________________________________________________

## 7) Security & compliance

- Celery workers run with restricted service accounts; environment variables limited to per-queue secrets.
- RLS context guard (`rls_context_assert()`) executed at task start; PgBouncer pooling limited to `transaction` or `session`.
- Settings snapshots ensure HIPAA and residency policies persist across retries; fallback controllers forbid region drift without waivers.
- Upload scanning enforces malware and residency policies; quarantined artifacts remain blocked until cleared.
- Audit trails (`JOB_*`, `WATCHDOG_*`, `DLQ_*`) stored in immutable logs; break-glass operations require dual approval.

______________________________________________________________________

## 8) Operations & runbooks

- Primary runbooks: RB-JOB-WATCHDOG (job watchdog/remediation), RB-LOCK-006 (advisory locks), RB-NOTIFY-* (delivery queues), RB-UPLOAD-SCAN (scanning), RB-CASE-IMPORT (legacy import).
- Drill cadence: quarterly watchdog stall simulation, queue backlog remediation, provider failover tabletop, backfill replay exercise.
- Evidence stored in `ops/workers/drills/<date>/` with participants, remediation tasks, and dashboards.

______________________________________________________________________

## 9) Dependencies

| Dependency                | Responsibility                                                             | Notes                                                                |
| ------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Settings Registry         | Supplies queue definitions, watchdog toggles, provider metadata            | Activation diff artifacts archived with change requests              |
| Guardian                  | Provides verdicts, quarantine actions, and backlog metrics                 | Workers escalate Guardian failures via SSE and runbooks              |
| Notifications service     | Outbox delivery and receipt tracking for email/SMS/in-app                  | Shared queues, DLQ handling, signed download tokens                  |
| LLM Registry & Speech     | Capability registry, parity evidence, failover orchestrators               | Workers consume controllers to enforce residency and parity          |
| Storage subsystem         | Artifact staging, upload sessions, case import bundles                     | Workers manage lifecycle and cleanup                                 |
| Worker infrastructure     | KEDA, Kubernetes HPA, monitoring dashboards                                | Ops Engineering maintains scaling policies                           |
| Ops runbook catalog       | Incident response and drill references                                     | Docs lint keeps RB-* entries current                                 |

______________________________________________________________________

## 10) References

- TDD overview summary — `../overview/tdd.md §12`.
- LLM Registry specification — `../services/llm-registry.md`.
- Notifications service specification — `../services/notifications.md`.
- Transcription agent implementation — `packages/udocket_core/agents/transcribe_lib.py`.
- Ops runbook catalog — `../ops/runbooks/index.md`.
- Settings Registry specification — `../services/settings.md`.
