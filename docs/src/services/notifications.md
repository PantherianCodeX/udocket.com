---
title: uDocket — Notifications Service Specification
subtitle: Multi-channel Delivery, Receipts, and In-App Alerts
author:
  - Communications & Outbound Delivery Working Group
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
  - Compliance Lead
  - SRE Manager
adr_index: docs/adr/README.md
related_adrs:
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
  - <header class="page-header">uDocket — Notifications Service Specification <br>
    Multi-channel Delivery, Receipts, and In-App Alerts</header>
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
| Reviewers      | Compliance Lead; SRE Manager |
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

- **Scope:** Governs outbound communications (email, SMS, phone-adjacent alerts, secure download tokens) and in-app notifications emitted by the uDocket platform. Covers outbox/state machines, provider adapters, webhook ingestion, receipts, audit posture, digest generation, and rate limiting. Portal banners and SSE fan-out ride on the same orchestration, so UI sections reference this specification for delivery guarantees.
- **Structure:** Sections follow the 0–10 template. Responsibilities (§2) enumerate channels and compliance requirements; APIs (§3) describe outbound queues and webhook callbacks; State management (§4) documents schema, RLS, and secure-view contracts; Failure/Observability (§5–§6) map to alerting; Security & Compliance (§7) captures DMARC/SMS obligations; Operations (§8) links to runbooks/digests; Dependencies, references close the doc.
- **Maintenance:** Run `python scripts/docs/lint_docs.py docs/src/services/notifications.md docs/src/overview/tdd.md docs/tdd_modularization.md` before submitting changes. Updates that alter schema, queue semantics, or provider adapters also require `build_runbook_catalog.py --check` to pass. Notify Platform + Ops architecture lists on PRs.
- **Change protocol:** Any PR affecting `outbox_delivery`/`delivery_receipt` schema, webhook signatures, download token format, or notification templates must reference this spec and ADR-0003. Provider onboarding/offboarding, DMARC policy changes, or SMS compliance updates demand Security + Architecture approval and runbook refreshes per §8.
- **References:** TDD §11 summary, Settings Registry §5 (keys under `notifications.*`), Guardian §5 (quarantine notifications), LP Engine §7 (localization bundles), Ops runbook catalog (RB-NOTIFY-\*), policy references in ADR-0003/0004.
- **Contacts:** Platform Engineering (service ownership), Operations Engineering (runbooks/delivery providers), on-call `notify-oncall@`, escalation `#ops-notifications`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Provide reliable, auditable delivery across email, SMS, and in-app channels while enforcing residency, privacy, and compliance guardrails. **|**
**Contract:** Notifications guarantees idempotent sends, signed download tokens, provider receipt correlation, and organizational rate limits. Deliveries either succeed with recorded receipts or fail closed with actionable audit reasons. **|**
**State:** Owns `outbox_delivery`, `delivery_receipt`, `download_token`, in-app notification queues, digest artifacts, and channel templates. Workers and webhooks mutate state under OCC to prevent duplicates. **|**
**Failure modes & handling:** Provider outages, webhook signature drift, STOP/HELP compliance events, or token misuse trigger runbooks (§5, §8) and fan-out warnings. **|**
**Observability:** Grafana dashboards “Notifications Delivery” (`delivery_success_ratio`, `delivery_retry_total`), “In-App Notifications” (`inapp_notification_sent_total`, `inapp_notification_click_total`), “Download Tokens” (`download_token_validation_total`). Alert catalog tags RB-NOTIFY-\* entries. **|**
**References:** §2 Responsibilities, §4 State management, §5 Failure modes, §7 Security & compliance, Ops runbooks RB-NOTIFY-OUTAGE/RB-NOTIFY-WEBHOOK/RB-NOTIFY-SMS. **|**
**Breadcrumbs:** Implementation `apps/platform/notifications/outbox.py`, provider adapters `apps/platform/notifications/providers/*.py`, webhook handlers `apps/platform/notifications/webhooks.py`, SSE publisher `apps/platform/events/notifications.py`, dashboards `infra/observability/dashboards/notifications_delivery.json`, tests `tests/platform/notifications/test_outbox.py`, `tests/platform/notifications/test_webhooks.py`.

______________________________________________________________________

## 2) Responsibilities

### 2.1 Outbox orchestration & delivery pipeline (binding)

**Purpose:** Ensure every outbound message transitions through a deterministic pipeline with OCC and retry safeguards. **|**
**Contract:** Outbox rows (`status='PENDING'| 'SENDING'| 'SENT'| 'FAILED'`) advanced atomically via `FOR UPDATE SKIP LOCKED`; OCC `version` increments each state change. Only a single worker may own a delivery attempt. **|**
**State:** `outbox_delivery` holds payloads, provider metadata, retry counters; `delivery_receipt` records confirmations; audit events tie both to artifacts/cases. **|**
**Failure modes & handling:** Lost locks, retry exhaustion, poison payloads route into DLQ with capped replays and RB-NOTIFY-OUTAGE escalation. **|**
**Observability:** Metrics `delivery_success_ratio`, `delivery_retry_total`, `delivery_queue_depth`; structured audit `NOTIFY_SEND_ATTEMPT`, `NOTIFY_SEND_FAILED`, `NOTIFY_DLQ_PARKED`. **|**
**Breadcrumbs:** Outbox workers `apps/platform/notifications/outbox.py::send_batch`, task module `apps/platform/operations/task_modules/notifications.py::dispatch_outbox`, tests `tests/platform/notifications/test_outbox_retry.py`. **|**
**References:** §4.1 Schema, §5.1 Provider outage.

- Workers claim rows with `SELECT ... FOR UPDATE SKIP LOCKED` to avoid thundering herds.
- Delivery attempts stamp `external_message_id` for provider correlation and store `provider_response`.
- DLQ semantics: after `notifications.delivery.max_attempts` retries, row transitions to `FAILED`, audit emits `NOTIFY_DLQ_PARKED`, and operators triage via RB-NOTIFY-OUTAGE.
- Weekly residency scanner digests (stored under `ops/residency/digest_<iso_week>.json`) reuse the outbox to notify org admins about waivers, remediation SLAs, and drift events.

### 2.2 Provider adapters & compliance envelopes (binding)

**Purpose:** Encapsulate provider-specific delivery logic while enforcing org-level compliance (DMARC, STOP/HELP, residency). **|**
**Contract:** Adapter registry defines connectors (`email`, `sms`, future push); each adapter must be idempotent, sign payloads, and honor residency (`regions.allowlist.messaging`). Email requires SPF/DKIM alignment and DMARC >= `quarantine`; SMS implements opt-in/opt-out flows with STOP/HELP keywords and regional sender policies. **|**
**State:** Adapter metadata lives in Settings (`notifications.providers[]`); runtime caches provider capabilities and throttle envelopes. **|**
**Failure modes & handling:** Provider drift (status≠healthy) opens circuit, pauses sends, and triggers RB-NOTIFY-OUTAGE; compliance violations quarantine org sending until resolved. **|**
**Observability:** Provider health metrics `notifications_provider_status_total`, `notifications_compliance_violation_total`; alerts `alert_notifications_delivery_health`, `alert_notifications_sms_compliance`. **|**
**Breadcrumbs:** Adapter registry `apps/platform/notifications/providers/__init__.py`, email adapter `apps/platform/notifications/providers/email.py`, SMS adapter `apps/platform/notifications/providers/sms.py`, tests `tests/platform/notifications/test_email_adapter.py`, `tests/platform/notifications/test_sms_opt_in.py`. **|**
**References:** §3.1 Webhooks, §7 Security & compliance.

- Org onboarding validates SPF/DKIM alignment before enabling custom sending domains; DMARC posture enforced via Settings `notifications.email.required_dmarc_policy`.
- SMS opt-out triggers `recipient_state='blocked'`; future sends return `HTTP 409` with reason `RECIPIENT_BLOCKED`.
- Link shortener ensures tokens stay case/org scoped and reuse download-token logic.

### 2.3 Webhook intake & receipt ledger (binding)

**Purpose:** Correlate provider callbacks with receipts while preventing spoofing. **|**
**Contract:** Webhooks require HMAC signature header `X-Request-Signature`; payload includes `external_message_id` or `provider_event_id`. Intake updates `delivery_receipt` via OCC, writes `delivery_receipt_secure` view rows, and emits audit events such as `NOTIFY_DELIVERY_CONFIRMED`. **|**
**State:** `delivery_receipt` rows store `{artifact_id?, channel, recipient, status, provider_event_id, details}` under RLS. **|**
**Failure modes & handling:** Signature mismatch → HTTP 401 `AUTH_SIGNATURE_INVALID`, audit `NOTIFY_WEBHOOK_SIGNATURE_FAIL`, RB-NOTIFY-WEBHOOK. Duplicated events deduped by unique constraint. **|**
**Observability:** Metrics `notifications_webhook_total{status}`, `notifications_receipt_latency_seconds`; alert `alert_notifications_webhook_signature`. **|**
**Breadcrumbs:** Webhook handler `apps/platform/notifications/webhooks.py::handle_provider_event`, tests `tests/platform/notifications/test_webhook_hmac.py`, secure view migration `db/migrations/security/015_delivery_receipt_secure.sql`. **|**
**References:** §4.2 Receipts schema, §6 Observability.

- Download attempts revalidate residency each time by comparing `artifact.manifest.storage_region` against current allowlists; violations return 403 `POLICY_BLOCK` and log `NOTIFY_REGION_BLOCKED`.
- Audit events include correlation IDs linking outbox row, receipt, artifact, and job.

### 2.4 Download tokens & secure delivery (binding)

**Purpose:** Limit artifact downloads to signed tokens with residency and expiry enforcement. **|**
**Contract:** Tokens embed `{artifact_id, org_id, checksum, expires_at, single_use?}` signed with service key. Validation checks signature, expiry, single-use, and residency before streaming. **|**
**State:** `download_token` table captures issued tokens, redemption timestamps, issuer, and advisory metadata. **|**
**Failure modes & handling:** Tampered token → 403 `TOKEN_INVALID`; expired token → 410 `TOKEN_EXPIRED`; single-use replays produce 409 `TOKEN_ALREADY_USED`; audit `DOWNLOAD_TOKEN_DENIED`. **|**
**Observability:** Metrics `download_token_validation_total{outcome}`, `download_stream_started_total`; Grafana “Download Tokens” panel. **|**
**Breadcrumbs:** Token issuer `apps/platform/notifications/download_tokens.py::issue`, validator `apps/platform/notifications/download_tokens.py::validate`, tests `tests/platform/notifications/test_download_tokens.py`. **|**
**References:** Guardian §5 (artifact quarantine), Settings §5 (token TTL keys).

- Portal invalidation calls `apps/platform/portal/notifications.py::invalidate_links`, emits SSE `portal.link_invalidated`, and writes audit entries; see TDD §11.5 summary.
- Tokens include optional `limited_scope` field for per-role gating (e.g., `client_portal` vs. `staff`).

### 2.5 Templates, digests, and escalation (normative)

**Purpose:** Ensure message content stays localized, policy-compliant, and audited. **|**
**Contract:** Templates (`notifications.templates[]` in Settings) define channel, locale, compliance tags, and allowed merge fields. Changes require dual approval and produce `NOTIFY_TEMPLATE_VERSION` artifacts. Weekly digests (residency, policy waivers) render via Lang templates and store audit JSON under `ops/residency/`. **|**
**State:** Template manifests record `{template_id, version, locale, checksum}`; digests produce `DIGEST` artifacts with metadata linking incidents. **|**
**Failure modes & handling:** Missing localization fallback → job failure `TEMPLATE_LOCALE_MISSING`; compliance tag mismatch blocks send with `NOTIFY_TEMPLATE_POLICY_BLOCK`. **|**
**Observability:** Metrics `notifications_template_render_total`, `notifications_digest_generated_total`; digest pipeline logs `ops/residency/digest_<iso_week>.json`. **|**
**Breadcrumbs:** Template renderer `apps/platform/notifications/templates.py`, digest job `apps/platform/operations/task_modules/notifications.py::generate_digest`, tests `tests/platform/notifications/test_template_render.py`. **|**
**References:** LP Engine §2 (localization bundles), Settings §5.2 template keys.

- Review timeout escalation (Settings `reviews.timeout_hours`) triggers notifications to reviewers and `org_admin`, recording audit `REVIEW_TIMEOUT_ESCALATED`.
- Compliance templates for regulator/customer incidents tracked under `ops/runbooks/index.md`.

### 2.6 In-app notifications & SSE fan-out (binding)

**Purpose:** Deliver low-latency notifications within staff and client portals with read receipts and rate limiting. **|**
**Contract:** In-app notifications emit SSE/Channels payloads, persist `IN_APP_NOTIFICATION` artifacts when audit requires retention, and obey Settings caps `notifications.in_app.rate_limit_per_minute`, `notifications.in_app.daily_cap`. Read receipts recorded per user. **|**
**State:** In-app queue stores pending events with OCC fields to prevent duplicate delivery; receipts tie to case/job context. **|**
**Failure modes & handling:** Rate-limit breaches respond with 429 `NOTIFY_RATE_LIMITED`; SSE failure triggers reconnect with exponential backoff; anomalies escalate via `alert_notifications_inapp_anomaly`. **|**
**Observability:** Metrics `inapp_notification_sent_total`, `inapp_notification_read_total`, `sse_connection_drop_total`; dashboards “In-App Notifications” and “SSE Health”. **|**
**Breadcrumbs:** Fan-out service `apps/platform/notifications/inapp.py`, SSE publisher `apps/platform/events/notifications.py`, tests `tests/platform/notifications/test_inapp_rate_limits.py`, `tests/platform/ui/test_notification_toast.py`. **|**
**References:** Guardian §5 (quarantine notices), TDD §11 summary.

- Edit workflows emit notifications `edit.started`, `edit.updated`, `edit.ready_for_review`, `edit.policy_blocked` with deep links; Guardian quarantines produce Security/Compliance notifications carrying context metadata.
- Portal invalidations broadcast `portal.link_invalidated` to affected sessions.

______________________________________________________________________

## 3) API contract

**Purpose:** Document the interfaces used to enqueue outbound messages, fetch receipts, and accept provider callbacks. **|**
**Contract:** Internal APIs accept authenticated REST requests (OAuth2) with OCC; provider callbacks rely on HMAC-signed webhooks. All endpoints versioned under `/api/v1/notifications/`. **|**
**State:** REST endpoints mutate `outbox_delivery`, `delivery_receipt`, `download_token`, and in-app notification queues. **|**
**Failure modes & handling:** Idempotency conflicts, missing HMAC signatures, stale tokens return typed errors with audit events. **|**
**Observability:** API metrics `notifications_api_request_total`, latency histograms, audit `NOTIFY_API_*` events; Spectral lints enforce OpenAPI coverage. **|**
**Breadcrumbs:** API router `apps/platform/api/notifications.py`, schema `spec/schemas/notification_outbox.schema.json`, tests `tests/platform/api/test_notifications_api.py`. **|**
**References:** OpenAPI bundle `ops/openapi/uDocket-platform.openapi.yaml`, ADR-0003.

### 3.1 External interfaces

- `POST /api/v1/notifications/outbox` — enqueue email/SMS/in-app notifications; requires `Idempotency-Key`. Payload includes `{channel, template_id, locale, recipient, context}`. Responds with `{outbox_id, status}`.
- `GET /api/v1/notifications/outbox/{id}` — fetch status; includes receipt summary.
- `POST /api/v1/notifications/providers/{provider}:webhook` — provider callbacks; signed with `X-Request-Signature`. Returns 202 when accepted.
- `POST /api/v1/notifications/download-tokens` — issue signed tokens; returns `{token, expires_at}`. Allowed roles defined in Settings.
- `POST /api/v1/notifications/inapp` — internal endpoint for agent workers to enqueue in-app notifications with case/job scoping.

### 3.2 Internal interfaces

- Celery tasks `notifications.dispatch_outbox` and `notifications.generate_digest` run within worker cluster, sized separately from agent queues.
- SSE publisher `apps/platform/events/notifications.py` broadcasts in-app and portal invalidation events. Channel topics namespaced `notifications.org.{org_id}` and `notifications.case.{case_id}`.
- Guardian/Compose integrations call `notifications.outbox.enqueue_review_timeout` to alert reviewers and escalate timeouts.

______________________________________________________________________

## 4) State management

**Purpose:** Describe persistence, retention, and access patterns for notifications artifacts. **|**
**Contract:** `outbox_delivery`, `delivery_receipt`, and `download_token` enforce OCC, secure views, and residency-friendly partitioning. **|**
**State:** Tables partitioned by month (`created_at`), RLS enforced via secure views, single writer per row through version increments. **|**
**Failure modes & handling:** Schema drift or RLS misconfiguration blocks deploys (lint), partitions auto-rotate via ops scripts. **|**
**Observability:** Metrics `notifications_partition_lag_days`, `notifications_rls_violation_total`; CLI `python ops/db/rotate_partitions.py` monitors rotation. **|**
**Breadcrumbs:** Migrations `db/migrations/notifications/001_outbox_delivery.sql`, `db/migrations/notifications/002_delivery_receipt.sql`, secure view `db/migrations/security/015_delivery_receipt_secure.sql`, partition rotation script `ops/db/rotate_partitions.py`, tests `tests/platform/db/test_notifications_schema.py`. **|**
**References:** Appendix J (DB governance), Settings Registry §5 (notifications keys).

### 4.1 Outbox schema (binding)

```sql
ALTER TABLE outbox_delivery
    ADD COLUMN external_message_id TEXT,
    ADD COLUMN version INT NOT NULL DEFAULT 0,
    ADD CONSTRAINT outbox_unique_extmsg UNIQUE (org_id, channel, external_message_id);

CREATE INDEX IF NOT EXISTS outbox_delivery_status_org_idx
  ON outbox_delivery (org_id, status, scheduled_at);
```

- `version` increments on each update; workers include `WHERE version = :expected` to guarantee OCC.
- Unique constraint prevents replays when providers resend the same external id.
- Poison messages rerouted to DLQ table `outbox_delivery_dlq` with the same schema plus `failure_reason`.

### 4.2 Receipt ledger & secure access (binding)

```sql
ALTER TABLE delivery_receipt
    ADD COLUMN provider_event_id TEXT,
    ADD CONSTRAINT receipt_provider_event_unique UNIQUE (org_id, channel, provider_event_id);

DROP POLICY IF EXISTS delivery_vis ON delivery_receipt;
CREATE POLICY delivery_vis ON delivery_receipt
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND EXISTS (
    SELECT 1
      FROM artifact a
      JOIN "case" c ON c.id = a.case_id
     WHERE a.id = delivery_receipt.artifact_id
       AND udocket_can('DELIVERY_RECEIPT', 'read', c.id, a.id, NULL)
  )
);

ALTER TABLE delivery_receipt FORCE ROW LEVEL SECURITY;

CREATE VIEW delivery_receipt_secure WITH (security_barrier=true) AS
SELECT id,
       artifact_id,
       org_id,
       channel,
       recipient,
       status,
       details,
       created_at,
       provider_event_id
  FROM delivery_receipt;

REVOKE SELECT ON delivery_receipt FROM udocket_app;
GRANT SELECT ON delivery_receipt_secure TO udocket_app;
```

- Secure view exposes only masked fields; details JSON scrubbed of PII via trigger.
- Access restricted to case members by policy `udocket_can('DELIVERY_RECEIPT', ...)`.
- Partitioning rotates monthly: `CREATE TABLE delivery_receipt_2025_01 PARTITION OF delivery_receipt FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');`.

### 4.3 Download token persistence (informative)

- Table columns `{token_hash, artifact_id, org_id, issued_by, issued_at, expires_at, single_use, redeemed_at, redeemed_by}`.
- Hash stored instead of raw token; validation recomputes hash for constant-time comparison.
- Indices: `(org_id, artifact_id)`, `(expires_at)` for eviction job `notifications.purge_expired_tokens`.
- Retention: tokens purged 24 hours after expiry; audit logs maintain canonical history.

______________________________________________________________________

## 5) Failure modes

### 5.1 Provider outage or degradation (binding)

- Circuit breaker opens when provider health crosses thresholds; outbox stays in `PENDING` and SLA timer starts. Alerts `alert_notifications_delivery_health` page on-call; RB-NOTIFY-OUTAGE orchestrates failover or hold.
- Customer notifications triggered if pause >15 minutes or SLA breach risk; message templates stored under `INCIDENT_TEMPLATE`.

### 5.2 Webhook signature mismatch or drift (binding)

- Signature failures return 401, log `NOTIFY_WEBHOOK_SIGNATURE_FAIL`, and suspend webhook processing until provider keys validated. RB-NOTIFY-WEBHOOK covers key rotation, backlog replay, and audit evidence.

### 5.3 Compliance violations (STOP/HELP, DMARC drift) (binding)

- SMS STOP updates recipient state to `blocked`, logs `NOTIFY_SMS_STOP_RECEIVED`, and halts further sends until opt-in regained (`HELP` flows or manual override). DMARC drift blocks email channel until SPF/DKIM restored; Security team notified.

### 5.4 Download token abuse (binding)

- Repeated invalid tokens from an IP trigger rate-limit and Security alert `alert_notifications_token_abuse`. RB-NOTIFY-TOKEN details investigation, user lockout, and forced token rotation.

### 5.5 Internal queue backlog (normative)

- `delivery_queue_depth` and `inapp_notification_queue_depth` thresholds alert when backlog age exceeds SLA. RB-NOTIFY-QUEUE directs scale-up, DLQ inspection, and digest catch-up steps.

______________________________________________________________________

## 6) Observability

- Metrics:
  - Delivery: `delivery_success_ratio`, `delivery_retry_total`, `notifications_provider_status_total`, `notifications_webhook_total{status}`, `notifications_receipt_latency_seconds`.
  - In-app: `inapp_notification_sent_total`, `inapp_notification_click_total`, `sse_connection_drop_total`.
  - Tokens: `download_token_validation_total{outcome}`, `download_stream_started_total`.
  - Digests/templates: `notifications_digest_generated_total`, `notifications_template_render_total`.
- Logs: structured events `NOTIFY_SEND_*`, `NOTIFY_WEBHOOK_*`, `DOWNLOAD_TOKEN_*`; correlation IDs align outbox, receipt, artifact, case.
- Traces: span `notifications.send` wraps provider API calls with tags `{provider, channel, attempt}`; webhook ingestion spans annotate signature status.
- Dashboards: `infra/observability/dashboards/notifications_delivery.json`, `notifications_inapp.json`, `download_tokens.json`.
- Alert catalogue entries map to RB-NOTIFY-\* runbooks; docs CI ensures runbook references rely on catalog.

______________________________________________________________________

## 7) Security & compliance

- Authentication:
  - Internal APIs require OAuth2 scopes `notifications.outbox.write`, `notifications.outbox.read`.
  - Webhooks validated via HMAC using shared secrets stored in `secrets/notifications/{provider}` (Kubernetes secret) rotated quarterly.
  - Download token signature keys rotated via Settings activation; rotation writes `DOWNLOAD_TOKEN_KEY@<version>` audit artifact.
- Privacy & residency:
  - Channels respect `regions.allowlist.messaging`; cross-region delivery forbidden without waiver (`waivers/notifications_residency.yaml`).
  - Payload scrubbing removes PII beyond required fields; attachments never inlined—notifications link to Guardian-approved artifacts.
- Compliance:
  - Email DMARC policy must be `quarantine` or `reject`; SPF/DKIM tests run at onboarding and continuously monitored.
  - SMS STOP/HELP enforced with automatic responses; compliance artifacts stored for regulators.
  - Audit artifacts: `delivery_receipt_secure`, `download_token`, `notifications_digest`.
- Security events: `NOTIFY_REGION_BLOCKED`, `NOTIFY_TOKEN_ABUSE`, `NOTIFY_SMS_STOP_RECEIVED`, `NOTIFY_DMARC_DRIFT` feed Security SIEM.
- Guardian integration: Quarantined artifacts block notifications and record `NOTIFY_GUARDIAN_BLOCKED`.

______________________________________________________________________

## 8) Operations & runbooks

**Purpose:** Maintain operational readiness and evidence for audits. **|**
**Contract:** Runbooks must stay aligned with alert catalog; quarterly drills validate provider failover, webhook compromise response, STOP/HELP surge handling, and download token abuse detection. **|**
**State:** Runbooks listed under RB-NOTIFY-\* in `docs/src/ops/runbooks/index.md`; drill evidence stored in `ops/notifications/drills/<date>/`. **|**
**Failure modes & handling:** Missing runbook references or overdue drills flagged by docs lint and Ops governance. **|**
**Observability:** Docs lint ensures runbook catalog fresh; dashboards track drill cadence. **|**
**Breadcrumbs:** Runbook catalog `docs/src/ops/runbooks/index.md`, drill scheduler `ops/scripts/notifications/schedule_drills.py`, incident templates `ops/runbooks/templates/notifications/*.md`. **|**
**References:** Alert catalogue, Ops governance policy App.N.

### 8.3 Runbook index (informative)

| Runbook code      | Scenario                                   | Notes |
| ----------------- | ------------------------------------------ | ----- |
| RB-NOTIFY-OUTAGE  | Provider outage / degraded delivery        | Provider escalation paths, failover to backup channel |
| RB-NOTIFY-WEBHOOK | Webhook signature drift / compromise       | Key rotation, backlog replay, SIEM coordination |
| RB-NOTIFY-SMS     | STOP/HELP surge & regulatory response      | Compliance scripts, opt-in reinstatement |
| RB-NOTIFY-TOKEN   | Download token abuse or leak               | Token rotation, artifact quarantine |

### 8.4 Drill cadence & evidence (normative)

- Quarterly tabletop covering provider failover, webhook compromise, STOP/HELP compliance surge, and download token abuse.
- Evidence stored in `ops/notifications/drills/<iso_week>/summary.md` with timestamps, participants, remediation tasks.
- Ops governance job verifies last drill ≤ 90 days; failures escalate to Operations leadership.

______________________________________________________________________

## 9) Dependencies

| Dependency             | Interface / artifact                                                                   | Responsibilities                                                                                      | Notes                                                                 |
| ---------------------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Settings Registry      | Keys `notifications.*`, rate limits, provider configs                                   | Supplies templates, throttles, provider secrets, DMARC policy enforcement                            | Activation diff artifacts archived with template/version metadata     |
| Localization & Policy Engine | Locale bundles `i18n.notifications.*`, residency policy hints                      | Ensures localized copy, policy context for residency checks                                          | Digests rely on LP Engine fallback logic                              |
| Guardian               | Quarantine verdicts, moderation verdict SSE                                            | Blocks unsafe notifications, provides context for Security/Compliance notifications                  | Quarantine reasons surface in notifications payloads                  |
| Worker Cluster (Celery)| Task modules `notifications.dispatch_outbox`, `notifications.generate_digest`          | Executes delivery batches, digest generation, DLQ fan-out                                            | Separate queue to isolate from agent workloads                        |
| Portal/Client apps     | SSE endpoints, download token validation                                                | Renders in-app notifications, enforces single-use tokens, shows invalidation banners                 | Portal invalidation logic in `apps/platform/portal/notifications.py`  |
| Ops analytics          | Runbook catalog, drill scheduler                                                        | Tracks runbook freshness, drill cadence, compliance evidence                                         | Buildkite docs job fails when catalog stale                           |

______________________________________________________________________

## 10) References

- TDD overview summary — `../overview/tdd.md §11` (Notifications bullet list).
- Settings Registry specification — `../services/settings.md §5.2` (notifications keys).
- Localization & Policy Engine — `../services/lp-engine.md §2.1` (locale bundles for notifications).
- Ops runbook catalog — `../ops/runbooks/index.md` (RB-NOTIFY-\* entries).
- ADR-0003 — API versioning & sunset policy for notification endpoints.
- ADR-0004 — Localization & Policy Engine governance for templates.
