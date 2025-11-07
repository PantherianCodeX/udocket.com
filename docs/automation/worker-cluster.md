---
title: uDocket — Worker Cluster Specification
subtitle: Job Orchestration, Watchdogs, and Background Operations
author:
  - Worker Cluster Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Engineering
  - Operations Engineering
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - SRE Manager
  - Applied AI Programs
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
  - <header class="page-header">uDocket — Worker Cluster Specification <br>
    Job Orchestration, Watchdogs, and Background Operations</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Worker Cluster Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Engineering; Operations Engineering |
| Reviewers | SRE Manager; Applied AI Programs |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Celery workers, beat schedulers, and task modules that execute agent pipelines, storage operations, notifications, watchdogs, and backfills. Covers queue topology, retries, residency enforcement, settings snapshots, and observability.
- **Structure:** Follows the standard 0–10 template. Responsibilities (§2) describe orchestration, queue management, watchdog automation, and provider integrations. APIs (§3) reference task entry points, job control RPC endpoints, and SSE updates. State, failure, observability, security, and ops guidance live in §§4–8.
- **Maintenance:** Run `python -m doc_tools.manage_docs --lint docs/automation/worker-cluster.md docs/overview/tdd.md docs/tdd_modularization.md` plus `make docs.check.runbooks` before landing worker changes. Update task-module AGENTS guides when adding queues or long-running jobs.
- **Change protocol:** Celery queue additions, watchdog changes, provider adapter updates, or retry semantics must reference this spec and note affected Settings keys. Provider failover logic requires Security + Architecture approval.
- **References:** TDD §12 summary, Transcription agent spec, Communications spec, Guardian spec, Settings Registry keys (`jobs.*`, `watchdog.*`), Ops runbooks `RB-JOB-WATCHDOG`, `RB-LOCK-006`.
- **Contacts:** Platform Engineering (queue topology), Operations Engineering (KEDA/scaling), Applied AI Programs (agent orchestration), `#worker-cluster` Slack, on-call `workers-oncall@`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Coordinate all background jobs—agent pipelines, notifications, watchdogs, backfills—while enforcing policy, residency, and reproducibility guarantees. **|**
**Contract:** Workers consume durable queues, propagate Settings snapshots, emit structured telemetry, and surface SSE/job updates with deterministic state transitions. **|**
**State:** Job manifests, checkpoints, watchdog tables, advisory locks, Settings snapshots, audit JSON/JSONL logs, and DLQs. **|**
**Failures & handling:** Provider outages, queue backlogs, watchdog stalls, or RLS guard failures trigger runbooks and pause processing safely. **|**
**Observability:** Dashboards “Worker Queues”, “Watchdog Runner”, “Job Progress”, metrics `celery_queue_depth`, `job_duration_seconds`, `watchdog_runner_lag_seconds`, `job_watchdog_warning_total`. **|**
**Breadcrumbs:** Celery config `apps/platform/operations/tasks.py`, task modules `apps/platform/operations/task_modules/*`, beat scheduler `apps/platform/operations/bootstrap.py`, watchdog runner `apps/platform/operations/watchdogs.py`, tests `tests/platform/operations/test_watchdogs.py`, `tests/platform/jobs/test_provider_progress_adapter.py`. **|**
**References:** §2 Responsibilities, §4 State management, §5 Failure modes, §7 Security & compliance, Ops runbooks `RB-JOB-WATCHDOG`/`RB-LOCK-006`.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Enumerate functional responsibilities and non-goals. **|**
**Contract:** Spell out mandatory behaviours, idempotency, regulatory duties. **|**
**State:** Describe ownership of state transitions or data stewardship. **|**
**Failures & handling:** Identify responsibility gaps and escalation paths. **|**
**Observability:** Checks proving each responsibility works. **|**
**Breadcrumbs:** Implementation/tests supporting each responsibility. **|**
**References:** Service/TDD sections that expand on responsibilities.

### 2.1 Agent orchestration & job lifecycle (binding)

**Purpose:** Execute Transcribe/Analyze/Compose and related agents with reproducibility and policy compliance. **|**
**Contract:** Tasks load Settings snapshots, resolve provider capabilities, and write manifests (`job_manifest`, `job_checkpoint`) with `{settings_snapshot_sha256, retry_token, retry_generation}` for every run. **|**
**State:** Artifacts, manifests, `job_checkpoint.progress_meta`, ops logs (`ops/<job_id>__*.jsonl`). **|**
**Failures & handling:** Capability mismatches or provider failures trigger parity-aware failover (`ModelFailoverOrchestrator`, `SpeechFailoverController`); exhausted fallback chain pauses jobs (`PAUSED_AWAITING_PROVIDER`) via `RB-LLM-003`. **|**
**Observability:** Metrics `job_duration_seconds{lane}`, `provider_progress_percent_complete`, `job_retry_total`; SSE `job.update` events include `provider_progress`. **|**
**Breadcrumbs:** Task modules `apps/platform/operations/task_modules/analyze.py`, `compose.py`, `transcribe.py`; capability map `packages/core/llm/registry.py`, speech failover `packages/core/failover/speech.py`; tests `tests/platform/jobs/test_provider_progress_adapter.py`. **|**
**References:** LLM registry spec §2.1–§2.3, Transcription agent doc, Communications spec §2.1.

- Workers run prefork Celery pools with dedicated queues per agent class; queue names encode priority (`analyze-high`, `compose-default`, `backfill-low`).
- Settings snapshots accompany every job to guarantee replay parity and are persisted alongside manifests.
- Provider adapters expose normalized progress snapshots; SSE payloads map to UI badges.
- Speech fallback controller manages multi-provider equivalence (WER/diarization parity, residency attestation) and track merge workflows when channels exceed provider support.

### 2.2 Queue topology, scaling, and DLQ management (binding)

**Purpose:** Maintain reliable queue processing with autoscaling and bounded retries. **|**
**Contract:** Queues leverage KEDA scaling based on `celery_queue_depth`; workers enforce OCC (`FOR UPDATE SKIP LOCKED`) for outbox/delivery tasks and bounded retry counts. DLQs capture poison messages with remediation workflow. **|**
**State:** Primary queues, DLQ tables (`*_dlq`), retry counters, Celery beat schedules. **|**
**Failures & handling:** Queue backlog alerts page SRE; DLQ backlog triggers `RB-JOB-WATCHDOG` or `RB-NOTIFY-OUTAGE` depending on queue type. **|**
**Observability:** Metrics `celery_queue_depth{queue}`, `celery_task_retry_total`, `dlq_messages_total`, `keda_scaler_events_total`. **|**
**Breadcrumbs:** Celery config `apps/platform/operations/bootstrap.py`, scaling manifests `infra/kubernetes/workers/`, tests `tests/platform/operations/test_queue_backpressure.py`. **|**
**References:** Communications spec §2.1, Settings Registry keys `jobs.queues.*`, Ops runbook catalog (queue remediation).

- Prefork pool defaults: `minReplicas=2`, `maxReplicas=10`, CPU target 70%; KEDA triggers on queue depth thresholds (default 25/50/100).
- Beat schedules manage periodic tasks (watchdogs, residency scanners, integrity checks); schedule metadata recorded in ops telemetry.
- DLQ consumers run under `notifications.generate_digest` or ad-hoc remediation tasks to re-queue after human review.

### 2.3 Watchdog runner & automation (binding)

**Purpose:** Detect stalled jobs, guardian backlog, advisory lock leaks, and integrity issues automatically. **|**
**Contract:** `watchdog-runner` Celery beat executes every minute, invoking configured watchdog tasks; failures emit SSE warnings and escalate per `RB-JOB-WATCHDOG`. **|**
**State:** Watchdog heartbeat table, ops logs `ops/watchdog/<date>.jsonl`, metrics. **|**
**Failures & handling:** Missed heartbeats (`watchdog_runner_missed_total`) require manual invocation and remediation before re-enabling automation. **|**
**Observability:** Metrics `watchdog_runner_lag_seconds`, `watchdog_runner_missed_total`, `job_watchdog_warning_total`, `udlock_watchdog_stale_total`. **|**
**Breadcrumbs:** Watchdog definitions `apps/platform/operations/watchdogs.py`, tests `tests/platform/operations/test_watchdogs.py`, runbook `RB-JOB-WATCHDOG`, `RB-LOCK-006`. **|**
**References:** Guardian spec §5 (backlog), Settings Registry `watchdog.*`.

### 2.4 Communications & back-office pipelines (binding)

**Purpose:** Fan out notification deliveries, upload scanning, case imports, and backfills via shared worker infrastructure. **|**
**Contract:** Task modules enforce idempotency (`retry_token`, advisory locks) and integrate with Communications service for outbox events. **|**
**State:** `outbox_delivery`, `delivery_receipt`, upload sessions, case import manifests, backfill logs. **|**
**Failures & handling:** Upload scanning failures quarantine staging blobs; case import errors halt portal exposure pending human review. **|**
**Observability:** Metrics `delivery_success_ratio`, `upload_scan_duration_seconds`, `case_import_duration_seconds`, `backfill_progress_percent`; audit events `CASE_IMPORT_ATTEMPT`, `UPLOAD_SCAN_FAILED`. **|**
**Breadcrumbs:** Task modules `apps/platform/operations/task_modules/files.py`, `notifications.py`, case import scripts `scripts/import/validate_case_bundle.py`, tests `tests/platform/files/test_upload_scan.py`. **|**
**References:** Communications spec, Ops runbook `RB-UPLOAD-SCAN`, Settings keys `upload.scan.*`.

### 2.5 Provider integration & capability registry (binding)

**Purpose:** Abstract provider capabilities (LLM, speech) with parity validation and residency enforcement. **|**
**Contract:** Capability registry maps provider metadata to execution plans; activation requires evaluation digests and residency attestations. Workers use controllers to ensure fallback chains honor parity and policy. **|**
**State:** Capability cache, parity evidence hashes, Settings `llm.models[]`, `speech.providers[]`. **|**
**Failures & handling:** Missing parity evidence blocks activation; drift triggers `PROVIDER_DATA_POLICY_DRIFT` and opens circuits. **|**
**Observability:** Metrics `llm_region_fallback_total`, `speech_failover_attempt_total`, synthetic probes `synthetics/llm_residency.yaml`. **|**
**Breadcrumbs:** Capability map `packages/core/llm/registry.py`, speech controller `packages/core/failover/speech.py`, tests `tests/core/llm/test_registry.py`, `tests/core/speech/test_failover.py`. **|**
**References:** LLM registry spec §2.1–§2.3, Transcription agent spec.

______________________________________________________________________

## 3) API Contract

**Purpose:** Document interfaces for enqueueing jobs, controlling runs, and surfacing progress. **|**
**Contract:** Job creation (`POST /api/v1/cases/{case_id}/jobs/{kind}`) returns `retry_token`; control endpoints (`pause`, `resume`, `cancel`, `retry`) require OCC and idempotency keys. Workers publish SSE `job.update` events with schema-versioned payloads. **|**
**State:** HTTP APIs mutate job rows, manifests, and checkpoints; Celery tasks consume queue messages; SSE topics broadcast updates. **|**
**Failures & handling:** Missing or stale idempotency keys return `409`; unsupported controls produce `400`; retries limited by policy. **|**
**Observability:** API metrics `job_control_request_total{action}`, SSE monitor `job_sse_schema_mismatch_total`, audit `JOB_*` events. **|**
**Breadcrumbs:** API handlers `apps/platform/jobs/views.py`, SSE publisher `apps/platform/events/jobs.py`, schema fixtures `spec/schemas/job_event.schema.json`. **|**
**References:** TDD §10 (job APIs), Communications spec (outbox endpoints).

### 3.1 External Interfaces

- `POST /api/v1/jobs/{id}:pause|resume|cancel|retry` enforce OCC on `version`, require `Idempotency-Key`, and propagate `retry_token` to keep retries idempotent.
- Responses include current status, warnings (`BUDGET_HELD`, `REGION_DRIFT`), and updated `retry_generation`.
- Upload finalize endpoint (`POST /api/v1/files/uploads/{id}:finalize`) interacts with worker tasks for storage conversions and validation.
- SSE topics `job.accepted|running|blocked|completed` broadcast progress with schema-versioned payloads for UI and automation consumers.

### 3.2 Internal Interfaces

- Primary task modules live in `apps/platform/operations/task_modules/*.py`; each declares queue bindings, retry budgets, and capability requirements.
- Beat schedules defined in `apps/platform/operations/bootstrap.py`; scheduling changes require documentation updates and runbook references.
- Workers communicate with provider controllers (LLM, speech) through `packages/core/*` registry facades for parity enforcement.
- Internal publish/subscribe uses Redis streams (`worker.events`) for watchdog and audit fan-out.

### 3.3 API Error Codes (binding)

**Purpose:** Enumerate worker-control `ApiError.code` values so API clients and automation react consistently. **|**
**Contract:** Worker Cluster reuses the platform catalog in [`Platform Runtime §3.3`](../platform/runtime.md#33-api-error-codes-binding) and applies the scenarios below for job control, upload finalize, and pipeline orchestration requests. **|**
**State:** Error responses originate from `apps/platform/jobs/views.py`, upload finalize controller `apps/platform/files/views.py`, and worker orchestration services; enums align with `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and `tests/platform/jobs/test_error_envelope.py`; runtime emissions trigger `job_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards “Worker Cluster – API” and “Upload Finalize” watch `job_api_error_total{code}`, `upload_finalize_total{status}`; synthetic controls exercise pause/resume/cancel paths. **|**
**Breadcrumbs:** Controllers `apps/platform/jobs/views.py`, upload guard `apps/platform/files/views.py::finalize_upload`, idempotency helpers `packages/core/idem/store.py`, tests `tests/platform/jobs/test_job_controls.py`, `tests/platform/files/test_upload_finalize.py`. **|**
**References:** Platform Runtime §3.3, Settings keys `api.idempotency.*`, Ops runbooks `RB-JOB-WATCHDOG`, `RB-UPLOAD-SCAN`.
> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#worker-cluster)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Idempotency payload hash mismatch or stale version when retrying job controls. | Re-fetch job state, regenerate the Idempotency-Key, and retry once with the updated payload. |
| `INTEGRITY_ERROR` | Upload finalize detected a hash mismatch against staged content. | Re-upload chunks with the correct digest and avoid blind retries until integrity matches. |
| `POLICY_BLOCK` | Guardian or residency guard, or a budget hold, prevented job execution. | Surface Guardian reason or budget hold, remediate policy or quota before retrying. |
| `PROVIDER_DEGRADED` | Downstream provider or queue paused (PAUSED_AWAITING_PROVIDER, circuit open). | Respect backoff, surface degraded status to operators, and retry when health probes recover. |
| `RATE_LIMIT` | Org or job-kind concurrency ceiling exceeded. | Honor Retry-After, queue retries with exponential backoff, and reduce burst size. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | No | job_api_error_total<br>idempotency_conflict_total |
| `INTEGRITY_ERROR` | 412 | Yes | job_api_error_total<br>upload_finalize_total |
| `POLICY_BLOCK` | 403 | Yes | job_api_error_total |
| `PROVIDER_DEGRADED` | 503 | Yes | job_api_error_total<br>job_dependency_degraded_total |
| `RATE_LIMIT` | 429 | No | job_api_error_total<br>job_rate_limit_total |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

### 3.4 Idempotency store & replay headers (binding)

**Purpose:** Capture the shared idempotency table and replay semantics so every worker-facing API behaves consistently. **|**
**Contract:** Requests persist entries before side effects, reuse stored responses on replays, and raise explicit collisions when payload hashes drift. **|**
**State:** Postgres table `idempotency_keys` plus supporting indices store canonical hashes, status, and replay metadata; helpers live in `packages.core.idem.*`. **|**
**Failures & handling:** Mismatched payload hashes return `409 CONFLICT` with `details.reason="IDEMPOTENCY_SIGNATURE_MISMATCH"` and do not mutate downstream state. **|**
**Observability:** Metrics `idempotency_replay_total`, `idempotency_conflict_total`, and structured logs include `idempotency_status`; dashboards pair with Alertmanager burn-rate alerts. **|**
**Breadcrumbs:** Store helpers `packages/core/idem/store.py`, API mixins `apps/platform/api/mixins/idempotency.py`, tests `tests/platform/operations/test_guardian_enqueue.py::test_idempotent_submit`. **|**
**References:** TDD §10 (job APIs), Settings Registry keys `api.idempotency.*`.

Schema excerpt:

```sql
CREATE TABLE idempotency_keys (
  org_id UUID NOT NULL,
  scope  TEXT NOT NULL,
  key    TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  case_id UUID NULL,
  request_hash BYTEA NOT NULL,
  status TEXT NOT NULL DEFAULT 'in_progress',
  result_ref TEXT NULL,
  response_code INTEGER NULL,
  response_hash BYTEA NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (org_id, scope, key)
);

CREATE UNIQUE INDEX idempotency_request_dedupe_idx
    ON idempotency_keys (org_id, scope, endpoint, request_hash);
CREATE INDEX idempotency_keys_expiry_idx
    ON idempotency_keys (expires_at);
```

Scope dimensions:

| Column | Description |
| --- | --- |
| `scope` | Logical action bucket (for example `job:create`, `artifact:approve`, `upload:finalize`); constants live in `packages.core.idem.constants`. |
| `endpoint` | Canonical `METHOD:/api/...` string preventing cross-route collisions. |
| `case_id` | Optional discriminator for case-scoped flows (null for global jobs). |
| `request_hash` | `sha256` of the canonical payload (body + sorted query + idempotency key). |
| `status` | `in_progress` during execution, `succeeded` after persistence, `conflict` when a mismatched replay occurs. |
| `result_ref` | Identifier returned to the caller (artifact ID, job ID, etc.). |
| `response_hash` | `sha256` of the serialized response body for auditability. |
| `response_code` | HTTP status associated with the stored response. |
| `last_seen_at` / `expires_at` | Replay window accounting; default TTL set by `api.idempotency.ttl_hours`. |

Replay headers:

```http
HTTP/1.1 200 OK
Content-Type: application/json
Idempotency-Key: 6d2fdc4c-483f-4f5b-9f4d-0f514c214766
Idempotency-Status: replay
X-Request-ID: 4f1a9c8c-0da5-4b27-9acd-6b6ddfd402c2

{ "artifact_id": "a7b9495c-4a5c-4e3b-91c6-5adef1d22264" }
```

Workers MUST update `last_seen_at` on every replay, echo the stored payload when `Idempotency-Status: replay`, and return `Idempotency-Status: conflict` when the canonical hash changes.



### 3.5 Job SSE replay contract (binding)

**Purpose:** Define the Server-Sent Events pattern workers use to stream job progress so clients can resume consumption safely. **|**
**Contract:** SSE endpoints honour `Last-Event-ID`, emit monotonically increasing IDs, and replay the most recent event on reconnect. **|**
**State:** Job manifests persist the last emitted event ID; SSE publisher `apps/platform/events/jobs.py` reads from that cursor. **|**
**Failures & handling:** Missing IDs return the latest cursor with `event: heartbeat`; stale IDs older than retention raise `410 GONE` and instruct clients to refetch job state. **|**
**Observability:** Metrics `job_sse_connection_total`, `job_sse_replay_total`, and structured logs capture reconnect behaviour. **|**
**Breadcrumbs:** SSE implementation `apps/platform/events/jobs.py`, tests `tests/platform/events/test_jobs_sse.py`. **|**
**References:** Portal spec §4, Communications spec §4 (in-app streams).

```bash
curl -N -H "Authorization: Bearer $TOKEN" \
  -H "Last-Event-ID: $LAST_ID" \
  https://platform.local/api/v1/jobs/$JOB_ID/events
```



### 3.6 Upload finalize endpoint (binding)

**Purpose:** Capture the JSON contract workers expect when a client finalizes an upload session. **|**
**Contract:** Clients provide the SHA-256 digest, optional manifest metadata, and `Idempotency-Key`; mismatched hashes return `412 PRECONDITION_FAILED`. **|**
**State:** Upload manifests persist in `upload_session` and `upload_manifest`; staging blobs remain until workers verify digests. **|**
**Failures & handling:** Expired sessions return `409`, integrity mismatches emit `INTEGRITY_ERROR`, and automation retries reuse the stored idempotency record. **|**
**Observability:** Metrics `upload_finalize_total{status}`, integrity dashboards, and audit logs monitor success rates. **|**
**Breadcrumbs:** API handler `apps/platform/files/views.py::finalize_upload`, schema `spec/schemas/upload_finalize.schema.json`, tests `tests/platform/files/test_upload_finalize.py`. **|**
**References:** Settings keys `upload.scan.*`, Ops runbook `RB-UPLOAD-SCAN`.

```yaml
openapi: 3.1.0
paths:
  /api/v1/uploads/{upload_session_id}/finalize:
    post:
      parameters:
        - in: header
          name: X-Signature-Key-Id
          required: true
          schema: { type: string }
        - in: header
          name: X-Timestamp
          required: true
          schema: { type: string, format: date-time }
        - in: header
          name: Idempotency-Key
          required: true
          schema: { type: string }
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [sha256]
              properties:
                sha256: { type: string, pattern: "^[a-f0-9]{64}$" }
                manifest: { type: object }
                auto_submit_guardian: { type: boolean, default: true }
      responses:
        "200":
          description: Finalized
          content:
            application/json:
              schema:
                type: object
                properties:
                  artifact_id: { type: string, format: uuid }
        "409": { description: Conflict (expired/aborted/idempotency mismatch) }
        "412": { description: INTEGRITY_ERROR (hash mismatch) }
      security:
        - oidc: []
        - hmacSignature: []
```

### 3.7 Job lifecycle endpoints (binding)

**Purpose:** Capture the deterministic behaviour for job creation, control actions, and cancellation so workers, UI, and API clients stay in sync. **|**
**Contract:** Job APIs enforce OCC, idempotency, and Guardian/SSE signalling; cancellation follows a three-step contract that blocks partial artifacts from persisting unnoticed. **|**
**State:** Job rows (`apps/platform/jobs/models.py`), control handlers (`apps/platform/jobs/views.py`), SSE publisher `apps/platform/events/jobs.py`, audit events `JOB_*`. **|**
**Failures & handling:** Missing idempotency headers return `400`; stale versions raise `409`; provider abort failures emit warnings and retry until the watchdog intervenes. **|**
**Observability:** Metrics `job_control_request_total{action}`, `job_cancel_latency_seconds`, `job_retry_total`, SSE monitors; runbooks `RB-JOB-WATCHDOG`, `RB-LOCK-006`. **|**
**Breadcrumbs:** API tests `tests/platform/jobs/test_job_controls.py`, provider adapters `packages/core/agents/*`, cancellation helpers `apps/platform/jobs/service.py`.

- `POST /api/v1/cases/{case_id}/jobs/{kind}` — requires `Idempotency-Key`; returns `{id, retry_token, version}`. Replays with the same payload reuse the existing job; mismatches raise `IDEMPOTENCY_SIGNATURE_MISMATCH`.
- `GET /api/v1/jobs/{id}` — reads job state plus manifest/checkpoint digests.
- Control RPCs `POST /api/v1/jobs/{id}:pause|resume|cancel|retry` — require OCC `version`, `Idempotency-Key`, and propagate `retry_token` when applicable. Responses include updated status, warnings (`BUDGET_HELD`, `REGION_DRIFT`), and the new `retry_generation`.
- Cancellation contract:
  1. Transition eligible jobs (`PENDING|QUEUED|RUNNING|PAUSED|PAUSED_AWAITING_BUDGET|PAUSED_AWAITING_PROVIDER`) to `CANCELING`. Emit SSE `job.accepted` (if previously queued) followed by `job.canceling {schema_version, emitted_at, job_id, actor_id, reason}` so clients stop optimistic UI updates.
  1. Invoke provider-specific aborts (Azure Speech Batch delete, streaming stop, LangGraph lane cancel). Azure Speech revokes SAS URLs and purges staging blobs; LangGraph lanes abort tool execution and release advisory locks. Providers have a 60-second grace period before the platform marks them canceled.
  1. Finalize `CANCELING → CANCELED`, emit SSE `job.canceled` and downstream `artifact.status` updates, append audit `JOB_CANCELED` (`reason`, `actor_id`, `provider_outcome`), and write auxiliary `JOB_CANCELLATION_REPORT` artifacts capturing checkpoints, partial outputs, and cleanup actions. Artifacts linked to the job persist with `depends_on_canceled_job=true` for operator review. Repeat cancels are idempotent.
- Retries require the stored `retry_token`; Guardian and Settings snapshots remain identical across attempts to guarantee reproducibility. Tool invocations declared in `agents.tools.catalog[]` include `idempotent` metadata and optional `tool_idempotency_key` so LangGraph runners can dedupe external calls when resuming checkpoints.
- SSE replay: `GET /api/v1/jobs/{id}/events` honours `Last-Event-ID` and `If-None-Match` (manifest digest). Servers return `ETag` headers and emit the schema enumerated in `spec/schemas/job_event.schema.json` (`job.accepted`, `job.running`, `job.update`, `job.complete`, `job.canceled`, policy holds). Clients must store the cursor and resume from the last event on reconnect.
- Provider progress normalization: `ProviderProgressAdapter` implementations wrap Azure Speech Batch, Azure OpenAI, and future providers to produce `{phase, percent_complete, estimated_remaining_seconds}` snapshots. Workers include snapshots in `job.update` SSE payloads (`provider_progress`) and persist them under `job_checkpoint.progress_meta`. Pause/resume/cancel calls fan out through the adapters to keep provider state aligned; failed provider-side pauses do not advance internal state machines.
- Provider health endpoint: `GET /api/v1/providers/health` aggregates the latest adapter heartbeat per `{provider, region}` with `{status, latency_ms_p95, error_rate, observed_at}`. Responses cache for 10 seconds and drive the `provider.health` SSE topic used by operator dashboards; degradation raises alerts even when queues are idle.
- Watchdog integration: heartbeat table `job_progress_heartbeat` records `{job_id, last_heartbeat_at, progress_pct}` updates. If age exceeds `jobs.watchdog.no_progress_minutes`, workers emit `job.watchdog_warning` SSE events and increment `job_watchdog_warning_total`. Exceeding `jobs.watchdog.timeout_minutes` transitions the job to `FAILED`, files audit `JOB_WATCHDOG_TIMEOUT`, and triggers [RB-JOB-WATCHDOG](../ops/runbooks.md#rb-job-watchdog).
- Overlap guard: advisory lock `jobkind:{case_id}/{kind}` prevents concurrent executions of mutually exclusive jobs, returning `409 JOB_KIND_BUSY` when a conflicting job is still active.

______________________________________________________________________

## 4) State Management

**Purpose:** Explain storage and configuration strategy. **|**
**Contract:** Define persistence guarantees, migration expectations, and retention. **|**
**State:** Describe schemas, caches, and configuration sources. **|**
**Failures & handling:** Cover corruption, drift, and reconciliation flows. **|**
**Observability:** Metrics for storage health, cache hit rates, or config parity. **|**
**Breadcrumbs:** ORM models, migrations, infrastructure manifests. **|**
**References:** TDD appendices or diagrams related to state.

- Job manifests (`job_manifest`) persist settings snapshot hashes, fallback reason codes, retry metadata, and artifact linkage.
- Checkpoints store progress meta JSON (provider progress percent, estimated remaining seconds) and SSE replay cursors.
- DLQ tables capture serialized payloads, failure reason, and retry counts; ops scripts drain after remediation.
- Watchdog heartbeat table records last execution per task; SSE references this data for dashboard displays.
- Upload sessions maintain resumable upload metadata and status transitions; expired sessions purged hourly alongside staging object deletion.

______________________________________________________________________

## 5) Failure Modes

**Purpose:** Provide the resilience profile and default mitigations. **|**
**Contract:** Identify what must fail closed vs. degraded. **|**
**State:** Note circuit breakers, queues, or compensating transactions. **|**
**Failures & handling:** Enumerate incidents, fallback procedures, and manual runbooks. **|**
**Observability:** Alerts, dashboards, and SLOs tied to failure handling. **|**
**Breadcrumbs:** Runbooks, incident retros, chaos tests. **|**
**References:** Link to ops docs or ADRs describing failure strategy.

- **Provider outage:** Fallback controller advances to next healthy model; if chain exhausted, jobs enter `PAUSED_AWAITING_PROVIDER` with alerts (`alert_llm_circuit_open`); `RB-LLM-003` executed.
- **Queue backlog / DLQ growth:** Alerts `celery_queue_depth_high` and `dlq_messages_total` escalate; workers throttled, DLQ drained following `RB-JOB-WATCHDOG` or notifications runbooks.
- **Watchdog stall:** Metrics `watchdog_runner_missed_total` > 0 triggers PagerDuty; automation paused until manual run confirms healthy state.
- **RLS context failure:** `rls_context_assert()` exceptions abort tasks; incidents logged as `RLS_CONTEXT_MISSING` and require bootstrap fix before resuming queue.
- **Upload scanning failure:** Files quarantined; `RB-UPLOAD-SCAN` executed before reprocessing.

______________________________________________________________________

## 6) Observability

**Purpose:** Show how to detect and diagnose issues. **|**
**Contract:** List mandatory telemetry and alerting coverage. **|**
**State:** Capture dashboards, log pipelines, or tracing spans. **|**
**Failures & handling:** Note alert fatigue risks or blind spots. **|**
**Observability:** Detail metrics/logs/traces plus owners. **|**
**Breadcrumbs:** Monitoring configs, dashboards, alert definitions. **|**
**References:** Observability standards or shared appendices.

- Metrics: `celery_queue_depth{queue}`, `job_duration_seconds`, `job_retry_total`, `job_watchdog_warning_total`, `watchdog_runner_lag_seconds`, `delivery_success_ratio`, `upload_scan_duration_seconds`, `case_import_duration_seconds`.
- Logs: Structured `WORKER_TASK`, `JOB_PROGRESS`, `WATCHDOG_RUN`, `DLQ_EVENT` with correlation IDs and masked fields; error-level duplicates to stderr only.
- Traces: Workers propagate W3C trace context via Celery headers; spans tagged with `{queue, task_name, retry}`; sampling 15% baseline, 100% on errors.
- Dashboards: “Worker Queues”, “Watchdog Runner”, “Job Progress”, “Upload Scanning”, “Case Import”; synthetic monitors verify watchdog heartbeat and SSE schema versions.

### 6.1 SLOs & Targets (binding)

**Purpose:** Capture queue throughput, job completion, and watchdog timing guarantees. **|**
**Contract:** Queue latency, completion ratio, watchdog heartbeat, and upload scanning throughput must stay within the thresholds below before new jobs launch. **|**
**State:** Metrics `celery_queue_depth`, `agent_job_completion_ratio`, `job_retry_total`, `watchdog_runner_lag_seconds`, `watchdog_runner_missed_total`, `upload_scan_duration_seconds`; dashboards “Worker Queues”, “Watchdog Runner”, “Upload Scanning”. **|**
**Failures & handling:** Breaches trigger RB-JOB-QUEUE, RB-JOB-WATCHDOG, or RB-UPLOAD-SCAN prior to resuming automation. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, synthetic watchdog checks, and queue latency probes provide evidence. **|**
**Breadcrumbs:** Monitoring rules `infra/monitoring/worker-prometheus-rules.yaml`, synthetic definitions `synthetics/worker_*`, runbooks `docs/ops/runbooks/worker/*.md`. **|**
**References:** TDD §12, Logging spec §6, Communications spec §6.

- **Queue latency:** 95th percentile job start delay (`celery_queue_depth` + derived latency) ≤ 2 minutes for standard queues; breaches trigger RB-WORKER-QUEUE before new jobs enter backlog.
- **Job completion:** ≥99.5% of jobs complete without DLQ escalation per rolling 24h (`job_retry_total`, `dlq_event_total`); higher failure rates require RB-WORKER-DLQ and leadership update.
- **Watchdog heartbeat:** `watchdog_runner_lag_seconds` stays ≤ 60 seconds with `watchdog_runner_missed_total = 0`; missed beats invoke RB-JOB-WATCHDOG and block releases until restored.
- **Upload scanning throughput:** `upload_scan_duration_seconds` P95 stays within SLA; breaches page RB-UPLOAD-SCAN and pause ingestion.

______________________________________________________________________

## 7) Security & Compliance

**Purpose:** Capture authZ/authN, data handling classes, and regulatory duties. **|**
**Contract:** Define encryption rules, residency bounds, and audit requirements. **|**
**State:** Describe secrets, key rotation, and data classifications. **|**
**Failures & handling:** Explain how breaches or policy drifts are detected and resolved. **|**
**Observability:** Security alerts, audit trails, compliance evidence. **|**
**Breadcrumbs:** IAM configs, policy bundles, compliance tests. **|**
**References:** Link to residency or policy appendices/ADRs.

- Celery workers run with restricted service accounts; environment variables limited to per-queue secrets.
- RLS context guard (`rls_context_assert()`) executed at task start; PgBouncer pooling limited to `transaction` or `session`.
- Settings snapshots ensure HIPAA and residency policies persist across retries; fallback controllers forbid region drift without waivers.
- Upload scanning enforces malware and residency policies; quarantined artifacts remain blocked until cleared.
- Audit trails (`JOB_*`, `WATCHDOG_*`, `DLQ_*`) stored in immutable logs; break-glass operations require dual approval.

______________________________________________________________________

## 8) Operational Notes

**Purpose:** Maintain the worker fleet’s readiness, watchdog coverage, and remediation playbooks. **|**
**Contract:** On-call rotations, runbooks, and drills must remain current; queues pause when automation gates fail until remediation completes. **|**
**State:** Runbooks in `ops/runbooks/worker/`, drill evidence `ops/workers/drills/<date>/`, freeze calendars `ops/workers/freeze_windows.ics`. **|**
**Failures & handling:** Stale playbooks, missed drills, or unstaffed rotations block change approvals and keep automation paused. **|**
**Observability:** Docs lint (`make docs.check.runbooks`), dashboards “Worker Queues”/“Watchdog Runner”, alert `watchdog_runner_missed_total`. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler `ops/scripts/worker/schedule_drills.py`, governance policies App.N. **|**
**References:** §5 Failure modes, §6 Observability, §7 Security & compliance.

### 8.1 Operational Posture (binding)

**Purpose:** Capture staffing and readiness expectations for the worker cluster. **|**
**Contract:** Platform Engineering staffs PagerDuty “Worker Queue SLO”, maintains blue/green deployment freezes during major migrations, and ensures watchdog-runner automation continues within ±60s schedule. **|**
**State:** Roster `ops/workers/roster.yaml`, freeze calendar `ops/workers/freeze_windows.ics`, watchdog timer reports `ops/workers/watchdog_status.json`. **|**
**Failures & handling:** Staffing gaps or missed watchdog runs trigger `RB-JOB-WATCHDOG` before resuming automation. **|**
**Observability:** PagerDuty metrics, watchdog dashboards, alert `watchdog_runner_missed_total`. **|**
**Breadcrumbs:** Roster files, freeze calendars, watchdog status logs. **|**
**References:** `RB-JOB-WATCHDOG`, §6 Observability.

### 8.2 Incident Triggers (binding)

**Purpose:** Map queue and automation alerts to worker runbooks. **|**
**Contract:** Alert rules (`infra/monitoring/worker-prometheus-rules.yaml`) embed RB-\* identifiers; responders capture evidence before resolving. **|**
**State:** Incident records `ops/workers/incidents/<date>.jsonl` document alert context and applied remediation. **|**
**Failures & handling:** Missing annotations or silenced alerts require governance review and follow-up tasks. **|**
**Observability:** Dashboards “Worker Queues”, “Watchdog Runner”, Alertmanager routes. **|**
**Breadcrumbs:** Alert rule files, PagerDuty services, SIEM dashboards. **|**
**References:** `RB-JOB-WATCHDOG`, `RB-LOCK-006`, `RB-NOTIFY-\*`.

- `celery_queue_depth_high` or `dlq_messages_total` breaches invoke RB-JOB-QUEUE to throttle enqueue, scale workers, and reconcile offsets.
- `watchdog_runner_missed_total` or `watchdog_runner_lag_seconds` triggers RB-JOB-WATCHDOG to restore automation and notify portal/UI.
- `worker_residency_violation_total` and queue segregation alerts fire RB-JOB-RESIDENCY for allowlist reconciliation.
- Planned deploys or node failures requiring drain signal RB-JOB-DRAIN to preserve in-flight jobs and evidence.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Keep worker playbooks current and drills executed on schedule. **|**
**Contract:** Alerts map to RB-\*; quarterly exercises cover watchdog stalls, provider failover simulations, queue backlog remediation, and DLQ replay drills. **|**
**State:** Runbooks `ops/runbooks/worker/*.md`, drill evidence `ops/workers/drills/<date>/`. **|**
**Failures & handling:** Missing drill evidence or outdated steps block automation restart after incidents. **|**
**Observability:** Docs lint, drill scheduler reports, Ops governance dashboards. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler, Ops governance records. **|**
**References:** `RB-JOB-WATCHDOG`, `RB-LOCK-006`, `RB-NOTIFY-\*`, `RB-UPLOAD-SCAN`, `RB-CASE-IMPORT`.

#### 8.3.1 Runbook Index (informative)

- `RB-JOB-WATCHDOG` — Worker/job watchdog
- `RB-JOB-DRAIN` — Graceful worker drain and redeploy
- `RB-JOB-RESIDENCY` — Residency drift remediation
- `RB-JOB-QUEUE` — Queue backlog triage

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarise worker cluster runbooks so responders execute consistent mitigations for job orchestration incidents. **|**
**Contract:** Each runbook ties to specific alerts and evidence expectations; responders update these guides after incidents or drills. **|**
**State:** Runbooks live in `ops/runbooks/worker/`, automation scripts in `ops/scripts/worker/`, and incident evidence under `ops/worker/incidents/`. **|**
**Failures & handling:** Missing steps or stale guidance blocks deployment approvals. **|**
**Observability:** Docs lint, PagerDuty analytics, and Ops dashboards track runbook freshness and drill coverage. **|**
**Breadcrumbs:** `ops/runbooks/worker/*.md`, `ops/scripts/worker/*.py`, incident templates `ops/worker/incidents/*.md`. **|**
**References:** Alert catalog, Guardian/Settings integration docs.

- `RB-JOB-WATCHDOG`: Recover from stalled or failed jobs by replaying Celery tasks, verifying locks, and notifying portal/UI.
- `RB-JOB-DRAIN`: Drain workers safely before deploys or failures, ensuring in-flight jobs persist and resume.
- `RB-JOB-RESIDENCY`: Handle residency drift by enforcing queue segregation, updating allowlists, and coordinating with Settings.
- `RB-JOB-QUEUE`: Manage backlog spikes, scale workers, and reconcile queue offsets with audit evidence.

#### 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover watchdog recovery, drain rehearsal, residency enforcement, and backlog triage; evidence stored in `ops/worker/drills/<date>/` with retrospective notes.
- Docs lint (`make docs.check.runbooks`) and PagerDuty analytics confirm drill execution; missed drills block release approvals.
- Compliance reviews reference drill evidence, queue audits, and residency logs to demonstrate readiness.

### 8.4 Migrations & Backfills (normative)

**Purpose:** Manage queue migrations, Celery upgrades, and DLQ replays. **|**
**Contract:** Queue renames and Celery upgrades require change tickets, KEDA dry runs, and rollback plans; DLQ replays run in preview before promotion. **|**
**State:** Migration scripts `ops/scripts/worker/migrate_queue.py`, upgrade playbooks `ops/runbooks/worker/celery_upgrade.md`, DLQ replay logs `ops/workers/dlq_replay/<date>/`. **|**
**Failures & handling:** Failed migrations revert to prior queue configuration; replay failures quarantine payloads for manual inspection. **|**
**Observability:** Metrics `worker_migration_success_total`, `dlq_replay_success_total`, change tickets in App.O. **|**
**Breadcrumbs:** Migration scripts, upgrade playbooks, DLQ tooling. **|**
**References:** §4 State management, Communications spec §4.

### 8.5 Operational Workflows (normative)

**Purpose:** Document recurring worker tasks (queue audits, watchdog verification, capacity reviews). **|**
**Contract:** Teams review queue depth daily, reconcile watchdog heartbeat reports, audit Settings snapshot adoption, and refresh worker autoscaling parameters quarterly. **|**
**State:** Queue audit reports `ops/workers/queue_audit/<date>.csv`, watchdog summaries `ops/workers/watchdog_status.json`, capacity review decks `ops/workers/capacity/<quarter>.pptx`. **|**
**Failures & handling:** Missing audits trigger `RB-JOB-WATCHDOG` follow-up; outdated scaling parameters escalate via Ops governance. **|**
**Observability:** Metrics `celery_queue_depth`, `watchdog_runner_lag_seconds`, capacity dashboards. **|**
**Breadcrumbs:** Audit scripts `ops/scripts/worker/audit_queues.py`, watchdog tools, capacity planning docs. **|**
**References:** Settings spec §6, LLM registry spec §2.4.

- Daily queue audits catch runaway jobs and coordinate with agent owners for mitigation.
- Weekly watchdog verifications ensure metrics, SSE, and logs reflect automation health.
- Quarterly capacity reviews adjust KEDA/HPA thresholds and record scaling decisions in Ops governance.

______________________________________________________________________

## 9) Dependencies

**Purpose:** List upstream/downstream systems and their contracts. **|**
**Contract:** Describe expectations on dependency behaviour and change management. **|**
**State:** Identify shared schemas/events and their owners. **|**
**Failures & handling:** Explain cascading failure protections. **|**
**Observability:** Dependency health checks and joint dashboards. **|**
**Breadcrumbs:** Integration specs, dependency docs. **|**
**References:** Link to other service docs or appendices.

| Dependency | Responsibility | Notes |
| --- | --- | --- |
| Settings Registry | Supplies queue definitions, watchdog toggles, provider metadata | Activation diff artifacts archived with change requests |
| Guardian | Provides verdicts, quarantine actions, and backlog metrics | Workers escalate Guardian failures via SSE and runbooks |
| Communications service | Outbox delivery and receipt tracking for email/SMS/in-app | Shared queues, DLQ handling, signed download tokens |
| LLM Registry & Speech | Capability registry, parity evidence, failover orchestrators | Workers consume controllers to enforce residency and parity |
| Storage subsystem | Artifact staging, upload sessions, case import bundles | Workers manage lifecycle and cleanup |
| Worker infrastructure | KEDA, Kubernetes HPA, monitoring dashboards | Ops Engineering maintains scaling policies |
| Ops runbook catalog | Incident response and drill references | Docs lint keeps RB-\* entries current |

______________________________________________________________________

## 10) References

- TDD overview summary — `../overview/tdd.md §12`.
- LLM Registry specification — `../automation/llm-registry.md`.
- Communications service specification — `../customer/communications.md`.
- Transcription agent implementation — `packages/core/agents/transcribe_lib.py`.
- Ops runbook catalog — `../ops/runbooks.md`.
- Settings Registry specification — `../platform/settings.md`.
