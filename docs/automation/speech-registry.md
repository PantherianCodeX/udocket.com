---
title: uDocket — Speech Registry Service Specification
subtitle: Speech provider catalog, parity controller, and diarization governance
author:
  - Speech Systems Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Architecture
  - Voice Engineering
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
    <header class="page-header">uDocket — Speech Registry Service Specification <br> Speech provider catalog, parity controller, and diarization governance</header>
  - |
    <footer class="page-footer">Confidential · Last updated 2025-10-29 · Page <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Speech Systems Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Architecture; Voice Engineering |
| Reviewers | QA Engineering Lead; SRE Manager |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Defines the Speech Registry service that catalogs speech providers/codecs, enforces residency and diarization policy, and feeds the Transcribe agent queues.
- **Structure:** Sections 1–10 follow the standard template; §2 captures agent-facing responsibilities, §3 the API/queue surface, §4–§6 state/failure/observability, and §8 covers operations/runbooks.
- **Maintenance:** Run `python -m doc_tools.manage_docs --lint` plus `make docs.build` before proposing registry changes. Provider catalog updates must include signed manifests under `ops/speech-registry/providers@<version>.json`.
- **Change protocol:** Provider additions/removals, codec table changes, and diarization policy tweaks require Architecture + Security approval, diffed manifests, and release notes tagged `SpeechRegistry`.
- **References:** TDD §5, automation LangGraph spec, Transcribe agent spec, worker-cluster spec, Ops runbooks `RB-SPEECH-FAILOVER`/`RB-SPEECH-DIARIZATION`.
- **Contacts:** Voice Engineering (`speech-registry@`), Platform Architecture (roadmap/governance), SRE Logging & Media squad for queue health.

______________________________________________________________________

## 1) Purpose

**Purpose:** Maintain a deterministic provider catalog so every speech job routes through approved regions/codecs with predictable outputs. **|**
**Contract:** Speech Registry validates residency, media characteristics, diarization eligibility, and provider health before dispatching jobs to Transcribe agents. **|**
**State:** Provider manifests, codec capability matrices, diarization policies, queue assignments, and audit logs under `ops/speech-registry/`. **|**
**Failures & handling:** Residency conflicts, codec mismatches, or provider outages block dispatch and trigger RB-SPEECH-FAILOVER/`speech_provider_block_total` alerts. **|**
**Observability:** Dashboards “Speech Provider Parity”, “Transcription Queue Health”, metrics `speech_registry_api_latency_seconds`, `speech_provider_block_total`, `audio_conversion_latency_seconds`. **|**
**Breadcrumbs:** `services/speech-registry/src`, `packages/core/audio/*`, `automation/task_modules/transcribe.py`, tests `tests/platform/operations/test_transcribe_http.py`. **|**
**References:** TDD §5, Ops runbooks `RB-SPEECH-FAILOVER`, `RB-SPEECH-DIARIZATION`.

______________________________________________________________________

## 2) Responsibilities (binding)

**Purpose:** Enumerate the deterministic duties enforced by Speech Registry. **|**
**Contract:** Enforce the following duties before dispatch. **|**
**State:** Settings bundles (`speech.registry.providers[]`, `speech.registry.diarization[]`), manifests under `ops/speech-registry/providers@<version>.json`, job metadata (conversion hashes, diarization flags). **|**
**Failures & handling:** Provider drift/outage or invalid media raise `SPEECH_PROVIDER_BLOCKED`/`SPEECH_CODEC_UNSUPPORTED`; Ops runbooks remediate before rerouting traffic. **|**
**Observability:** Metrics `speech_provider_violation_total`, `audio_conversion_error_total`, `diarization_job_latency_seconds`; Grafana dashboards display lane health. **|**
**Breadcrumbs:** Settings definitions `apps/platform/settings/services/speech.py`, registry compiler `services/speech-registry/src/catalog.py`, conversion helpers `packages/core/audio/ffmpeg.py`. **|**
**References:** Transcribe agent spec, Ops runbooks.

- Maintain per-provider residency allowlists and enforce tenant scope before dispatch.
- Normalize media (sample rate/channel/layout) and persist conversion fingerprints.
- Attach diarization policy (batch-only) and set expectations for job manifests.
- Publish provider state (READY/WARN/BLOCK) to Guardian, automation dashboards, and Ops audit streams.
- Surface deterministic manifests enabling replay of provider selections and conversions.

### 2.1 Provider catalog

- Signed manifests specify residency, codec, language, diarization capabilities, queues, and failover ordering.
- Catalog changes trigger `speech.registry.providers.updated` events consumed by automation workers.

### 2.2 Diarization governance

- Batch-only diarization support; registry enforces max duration/language list per provider and annotates manifests so Transcribe agent rejects unsupported requests.
- Diarization waits for provider health >= READY and enough queue capacity before enabling.

______________________________________________________________________

## 3) API Contract (normative)

**Purpose:** Describe registry-facing APIs used by automation/services. **|**
**Contract:** REST + Celery interfaces must be authenticated (service tokens) and emit deterministic manifests with residency decisions. **|**
**State:** API responses embed provider digest, allowed regions, conversion plans, diarization flags, fallback strategy. **|**
**Failures & handling:** REST calls emit structured error codes (`SPEECH_PROVIDER_BLOCKED`, etc.) documented below; Celery tasks return typed envelopes and retry on transient errors. **|**
**Observability:** OpenTelemetry spans, `speech_registry_api_error_total`, Celery task metrics `audio_conversion_latency_seconds`. **|**
**Breadcrumbs:** `services/speech-registry/src/api.py`, schema `spec/schemas/speech_registry.yaml`, Celery integration tests. **|**
**References:** Platform Runtime §3 (authN/authZ), automation Transcribe spec.

### 3.1 External Interfaces

- `POST /speech/registry/providers:resolve` — returns provider + conversion plan for a media asset.
- `GET /speech/registry/providers/<provider_id>` — provider metadata + residency allowlists.
- `POST /speech/registry/diarization:plan` — optional endpoint summarizing diarization viability.

### 3.2 Internal Interfaces

- Celery task `speech_registry.apply_conversion` performs ffmpeg conversions and uploads normalized media artifacts.
- Settings activation hook `speech_registry.compile_catalog` validates manifests during deploys.

### 3.3 API Error Codes

**Purpose:** Capture Speech Registry `ApiError.code` values so clients remediate deterministically. **|**
**Contract:** Codes mirror Platform Runtime §3.3 and map to residency/codec/diarization failures documented in §5. **|**
**State:** YAML catalog `docs/automation/speech-registry/error_codes.yaml` generates this section and the global appendix. **|**
**Failures & handling:** Unknown codes fail docs lint and trigger `speech_registry_api_error_total{code="unknown"}`. **|**
**Observability:** Metrics `speech_registry_api_error_total{code}` and Alertmanager notifications. **|**
**Breadcrumbs:** Error-code YAML, `services/speech-registry/src/api.py`, tests `tests/platform/operations/test_transcribe_http.py`. **|**
**References:** Platform Runtime §3.3, API error appendix.

> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#speech-registry-service)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `speech_codec_unsupported` | Uploaded media codec/sample rate is not supported. | Re-upload media in PCM WAV 16 kHz mono (or another supported format advertised in provider metadata) before retrying. |
| `speech_diarization_unavailable` | Diarization requested but no provider supports the parameters. | Disable diarization or adjust duration/language parameters until a supported provider is available, then retry. |
| `speech_provider_blocked` | Speech provider unavailable for the tenant’s residency rules. | Surface the residency violation to operators, switch to an allowed provider/region, or obtain a waiver before retrying. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `speech_codec_unsupported` | 400 | No | — |
| `speech_diarization_unavailable` | 422 | No | — |
| `speech_provider_blocked` | 409 | Yes | — |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

______________________________________________________________________

## 4) State Management (binding)

**Purpose:** Describe persistence strategy for catalogs, conversions, and manifests. **|**
**Contract:** Provider manifests are signed + versioned; conversion artifacts stored alongside cases with deterministic naming; queue state recorded for replay. **|**
**State:** Postgres tables `speech_registry_provider`, `speech_registry_conversion`, conversion cache directories, Settings snapshots. **|**
**Failures & handling:** Hash drift or unsigned manifests halt activation; conversion cache corruption forces regeneration. **|**
**Observability:** Migration history, manifest digests, conversion hash metrics. **|**
**Breadcrumbs:** Database migrations `services/speech-registry/migrations/`, `ops/speech-registry/providers@<version>.json`. **|**
**References:** Audit spec §4, Transcribe spec.

______________________________________________________________________

## 5) Failure Modes (binding)

**Purpose:** Capture resilience and remediation steps. **|**
**Contract:** Residency violations, codec errors, provider outages, and diarization lag all fail closed and page operators. **|**
**State:** Failure state persists in manifests + ops logs for audit. **|**
**Failures & handling:** RB-SPEECH-FAILOVER, RB-SPEECH-DIARIZATION, RB-SPEECH-CODEC. **|**
**Observability:** Alerts on `speech_provider_block_total`, `audio_conversion_error_total`, `diarization_backlog_high`. **|**
**Breadcrumbs:** Ops runbooks, Grafana dashboards. **|**
**References:** Worker cluster spec, Ops catalog.

______________________________________________________________________

## 6) Observability (binding)

**Purpose:** Ensure registry health is measurable and alertable. **|**
**Contract:** Metrics, logs, and dashboards enumerated here are mandatory before release. **|**
**State:** Prometheus rules `infra/monitoring/speech-registry-prometheus-rules.yaml`, dashboards `infra/observability/dashboards/speech_registry.json`, ops audit streams. **|**
**Failures & handling:** Missing telemetry blocks rollout until restored and verified by RB-SPEECH-OBS. **|**
**Observability:** `speech_registry_api_latency_seconds`, `speech_provider_block_total`, `audio_conversion_latency_seconds`, `diarization_job_latency_seconds`, SSE traces. **|**
**Breadcrumbs:** Monitoring repo, Alertmanager configs. **|**
**References:** Observability spec §6, worker cluster spec.

### 6.1 SLOs & Targets (binding)

**Purpose:** Establish measurable objectives. **|**
**Contract:** API availability ≥99.9 %, conversion enqueue P95 ≤15 s, diarization completion P95 ≤2× media duration; residency guard zero tolerance. **|**
**State:** SLO dashboards and burn-rate alerts. **|**
**Failures & handling:** Breaches trigger RB-SPEECH-FAILOVER (availability), RB-SPEECH-CODEC (conversion), RB-SPEECH-DIARIZATION (diarization). **|**
**Observability:** Prometheus SLO rules, burn-rate alerts, synthetic conversion jobs. **|**
**Breadcrumbs:** Monitoring repo, Ops runbooks. **|**
**References:** Worker cluster capacity plan, FinOps guardrails.

______________________________________________________________________

## 7) Security & Compliance (binding)

**Purpose:** Document residency + privacy controls. **|**
**Contract:** Enforce tenant residency, block disallowed providers, encrypt conversion artifacts at rest, redact PII from logs. **|**
**State:** Residency allowlists, waiver references, conversion artifact manifests. **|**
**Failures & handling:** Residency drift triggers RB-RES-BLOCK + RB-SPEECH-FAILOVER; log redaction failures escalate to Security. **|**
**Observability:** Audit logs `ops/speech-registry/providers.jsonl`, metrics `speech_provider_violation_total`. **|**
**Breadcrumbs:** Residency service spec, Audit spec, Ops runbooks. **|**
**References:** Policy Residency spec, Settings spec §7, Audit spec §4.

______________________________________________________________________

## 8) Operational Notes (binding)

**Purpose:** Describe operations, on-call, alerting, and runbook expectations. **|**
**Contract:** Release only when runbooks + staffing meet requirements; maintain evidence for drills. **|**
**State:** Runbooks under `docs/ops/runbooks/speech-registry/`, drill logs `ops/speech-registry/drills/<date>/`. **|**
**Failures & handling:** Missing runbooks or drill evidence block change approval until remediation recorded. **|**
**Observability:** Ops dashboards for queue depth, provider parity, drill cadence. **|**
**Breadcrumbs:** Ops runbooks, On-call rosters, deployment manifests. **|**
**References:** Worker cluster spec, Ops governance policy.

### 8.1 Operational Posture (binding)

**Purpose:** Capture staffing + on-call obligations. **|**
**Contract:** Voice Engineering owns 24×7 pager (`speech-registry` service) with ≤15 min acknowledge; Platform Architecture secondary for catalog issues. **|**
**State:** Rota files `ops/oncall/voice_engineering.md`, PagerDuty schedules. **|**
**Failures & handling:** Coverage gaps escalate to SRE Director; release gates close until rota restored. **|**
**Observability:** Pager latency dashboard, rota health checks. **|**
**Breadcrumbs:** Ops/oncall repo, staffing notes. **|**
**References:** Incident management policy.

### 8.2 Incident Triggers (binding)

**Purpose:** Map alerts to severity and playbooks. **|**
**Contract:** Alerts firing more than twice per day must have owner + runbook. **|**
**State:** Alert definitions in monitoring repo. **|**
**Failures & handling:** Weekly review prunes noisy alerts; missing runbooks added before release. **|**
**Observability:** Alertmanager dashboards, incident retros. **|**
**Breadcrumbs:** Monitoring repo, Ops catalog. **|**
**References:** Worker cluster spec.

- `speech_provider_block_total > 0` → Sev-2, RB-SPEECH-FAILOVER.
- `audio_conversion_error_total` sustained → Sev-3, RB-SPEECH-CODEC.
- `diarization_backlog_high` → Sev-3, RB-SPEECH-DIARIZATION.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Ensure responders have executable playbooks and evidence. **|**
**Contract:** Maintain RB-SPEECH-FAILOVER, RB-SPEECH-CODEC, RB-SPEECH-DIARIZATION; conduct quarterly drills with evidence. **|**
**State:** Markdown runbooks + automation scripts under `docs/ops/runbooks/speech-registry/`, drill evidence directories. **|**
**Failures & handling:** Missing evidence triggers compliance ticket; release blocked until remediated. **|**
**Observability:** Drill tracker metrics `speech_registry_drill_overdue_total`. **|**
**Breadcrumbs:** Ops runbooks, drill runner scripts. **|**
**References:** Ops governance policy.

#### 8.3.1 Runbook Index (informative)

| Signal | Runbook | Notes |
| --- | --- | --- |
| `speech_provider_block_total` | RB-SPEECH-FAILOVER | Residency/provider outage remediation |
| `audio_conversion_error_total` | RB-SPEECH-CODEC | Conversion backlog/codec issues |
| `diarization_backlog_high` | RB-SPEECH-DIARIZATION | Diarization lag + disablement |

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarize the runbooks executed during incidents. **|**
**Contract:** Keep RB-SPEECH-FAILOVER/RB-SPEECH-CODEC/RB-SPEECH-DIARIZATION current and linked to alerts. **|**
**State:** Markdown runbooks + automation scripts under `docs/ops/runbooks/speech-registry/`. **|**
**Failures & handling:** Missing steps or stale owners block releases until updated. **|**
**Observability:** Ops catalog and drill tracker verify coverage. **|**
**Breadcrumbs:** Ops runbook repo, drill evidence directories. **|**
**References:** Ops governance policy.

- **RB-SPEECH-FAILOVER:** Validate residency allowlists, disable offending provider, reroute to backups, capture manifests.
- **RB-SPEECH-CODEC:** Inspect conversion logs, flush cache, requeue jobs, coordinate with Transcribe agent owners.
- **RB-SPEECH-DIARIZATION:** Disable diarization flag, notify case teams, re-enable once provider recovers.

#### 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly provider failover tabletop.
- Semi-annual diarization live test.
- Evidence stored under `ops/speech-registry/drills/<date>/summary.md` with metrics snapshots.

### 8.4 Migrations & Backfills (informative)

**Purpose:** Document catalog migrations/backfills. **|**
**Contract:** Schema migrations use Alembic; catalog backfills require manifest diff + approval. **|**
**State:** Migration scripts `services/speech-registry/migrations/`, backfill notebooks `ops/speech-registry/backfills/`. **|**
**Failures & handling:** Failed migrations rolled back via `alembic downgrade`; backfills re-run with recorded digests. **|**
**Observability:** Migration dashboards, CI checks. **|**
**Breadcrumbs:** Infra repo, migration docs. **|**
**References:** Database governance policy.

### 8.5 Operational Workflows (informative)

**Purpose:** Capture recurring workflows (catalog review, provider onboarding). **|**
**Contract:** Monthly catalog reconciliation, quarterly waiver review, provider onboarding checklist. **|**
**State:** Checklists `ops/speech-registry/workflows/*.md`, ticket templates. **|**
**Failures & handling:** Missed workflows generate compliance tickets. **|**
**Observability:** Workflow dashboard tracking completion. **|**
**Breadcrumbs:** Ops workflows, Jira templates. **|**
**References:** Compliance policy.

______________________________________________________________________

## 9) Dependencies (normative)

**Purpose:** List upstream/downstream systems. **|**
**Contract:** Speech Registry depends on Policy Residency (catalogs/waivers), Transcribe agent, worker cluster, and storage adapters. **|**
**State:** Shared manifests, queue schemas, events. **|**
**Failures & handling:** Residency drift or worker outages trigger joint runbooks. **|**
**Observability:** Dependency dashboards linking Policy Residency + worker cluster. **|**
**Breadcrumbs:** Dependency specs. **|**
**References:** Policy Residency, worker-cluster, Transcribe specs.

______________________________________________________________________

## 10) References (informative)

- TDD §5 (Automation)
- Policy Residency Service Specification
- Worker Cluster Specification
- Transcribe Agent specification
- Ops runbooks RB-SPEECH-FAILOVER / RB-SPEECH-CODEC / RB-SPEECH-DIARIZATION
