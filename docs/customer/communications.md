---
title: uDocket — Communications Service Specification
subtitle: Multi-channel Delivery, Receipts, and In-App Alerts
author:
  - Communications & Outbound Delivery Working Group
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
  - <header class="page-header">uDocket — Communications Service Specification <br>
    Multi-channel Delivery, Receipts, and In-App Alerts</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Communications & Outbound Delivery Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Engineering; Operations Engineering |
| Reviewers | Compliance Lead; SRE Manager |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Governs outbound communications (email, SMS, phone-adjacent alerts, secure download tokens) and in-app notifications emitted by the uDocket platform. Covers outbox/state machines, provider adapters, webhook ingestion, receipts, audit posture, digest generation, and rate limiting. Portal banners and SSE fan-out ride on the same orchestration, so UI sections reference this specification for delivery guarantees. Historically branded “Notifications,” the runtime modules remain under `apps/platform/notifications/*`; this spec widens the domain to all outbound communications.
- **Structure:** Sections follow the 0–10 template. Responsibilities (§2) enumerate channels and compliance requirements; APIs (§3) describe outbound queues and webhook callbacks; State management (§4) documents schema, RLS, and secure-view contracts; Failure/Observability (§5–§6) map to alerting; Security & Compliance (§7) captures DMARC/SMS obligations; Operations (§8) links to runbooks/digests; Dependencies, references close the doc.
- **Maintenance:** Run `python -m doc_tools.manage_docs --lint docs/customer/communications.md docs/overview/tdd.md docs/tdd_modularization.md` before submitting changes. Updates that alter schema, queue semantics, or provider adapters also require `make docs.check.runbooks` to pass. Notify Platform + Ops architecture lists on PRs.
- **Change protocol:** Any PR affecting `outbox_delivery`/`delivery_receipt` schema, webhook signatures, download token format, or notification templates must reference this spec and ADR-0002. Provider onboarding/offboarding, DMARC policy changes, or SMS compliance updates demand Security + Architecture approval and runbook refreshes per §8.
- **References:** TDD §11 summary, Settings Registry §5 (keys under `notifications.*`), Guardian §5 (quarantine notifications), LP Engine §7 (localization bundles), Ops runbook catalog (`RB-NOTIFY-\*`), policy references in ADR-0002/0004.
- **Contacts:** Platform Engineering (service ownership), Operations Engineering (runbooks/delivery providers), on-call `notify-oncall@`, escalation `#ops-notifications`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Provide reliable, auditable delivery across email, SMS, and in-app channels while enforcing residency, privacy, and compliance guardrails. **|**
**Contract:** Communications service (legacy module `apps/platform/notifications`) guarantees idempotent sends, signed download tokens, provider receipt correlation, and organizational rate limits. Deliveries either succeed with recorded receipts or fail closed with actionable audit reasons. **|**
**State:** Owns `outbox_delivery`, `delivery_receipt`, `download_token`, in-app notification queues, digest artifacts, and channel templates. Workers and webhooks mutate state under OCC to prevent duplicates. **|**
**Failures & handling:** Provider outages, webhook signature drift, STOP/HELP compliance events, or token misuse trigger runbooks (§5, §8) and fan-out warnings. **|**
**Observability:** Grafana dashboards “Notifications Delivery” (`delivery_success_ratio`, `delivery_retry_total`), “In-App Notifications” (`inapp_notification_sent_total`, `inapp_notification_click_total`), “Download Tokens” (`download_token_validation_total`). Alert catalog tags `RB-NOTIFY-\*` entries. **|**
**Breadcrumbs:** Implementation `apps/platform/notifications/outbox.py`, provider adapters `apps/platform/notifications/providers/*.py`, webhook handlers `apps/platform/notifications/webhooks.py`, SSE publisher `apps/platform/events/notifications.py`, dashboards `infra/observability/dashboards/notifications_delivery.json`, tests `tests/platform/notifications/test_outbox.py`, `tests/platform/notifications/test_webhooks.py`. **|**
**References:** §2 Responsibilities, §4 State management, §5 Failure modes, §7 Security & compliance, Ops runbooks `RB-NOTIFY-OUTAGE`/`RB-NOTIFY-WEBHOOK`/`RB-NOTIFY-SMS`.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Enumerate functional responsibilities and non-goals. **|**
**Contract:** Spell out mandatory behaviours, idempotency, regulatory duties. **|**
**State:** Describe ownership of state transitions or data stewardship. **|**
**Failures & handling:** Identify responsibility gaps and escalation paths. **|**
**Observability:** Checks proving each responsibility works. **|**
**Breadcrumbs:** Implementation/tests supporting each responsibility. **|**
**References:** Service/TDD sections that expand on responsibilities.

### 2.1 Outbox orchestration & delivery pipeline (binding)

**Purpose:** Ensure every outbound message transitions through a deterministic pipeline with OCC and retry safeguards. **|**
**Contract:** Outbox rows (`status='PENDING'| 'SENDING'| 'SENT'| 'FAILED'`) advanced atomically via `FOR UPDATE SKIP LOCKED`; OCC `version` increments each state change. Only a single worker may own a delivery attempt. **|**
**State:** `outbox_delivery` holds payloads, provider metadata, retry counters; `delivery_receipt` records confirmations; audit events tie both to artifacts/cases. **|**
**Failures & handling:** Lost locks, retry exhaustion, poison payloads route into DLQ with capped replays and `RB-NOTIFY-OUTAGE` escalation. **|**
**Observability:** Metrics `delivery_success_ratio`, `delivery_retry_total`, `delivery_queue_depth`; structured audit `NOTIFY_SEND_ATTEMPT`, `NOTIFY_SEND_FAILED`, `NOTIFY_DLQ_PARKED`. **|**
**Breadcrumbs:** Outbox workers `apps/platform/notifications/outbox.py::send_batch`, task module `apps/platform/operations/task_modules/notifications.py::dispatch_outbox`, tests `tests/platform/notifications/test_outbox_retry.py`. **|**
**References:** §4.1 Schema, §5.1 Provider outage.

- Workers claim rows with `SELECT ... FOR UPDATE SKIP LOCKED` to avoid thundering herds.
- Delivery attempts stamp `external_message_id` for provider correlation and store `provider_response`.
- DLQ semantics: after `notifications.delivery.max_attempts` retries, row transitions to `FAILED`, audit emits `NOTIFY_DLQ_PARKED`, and operators triage via `RB-NOTIFY-OUTAGE`.
- Weekly residency scanner digests (stored under `ops/residency/digest_<iso_week>.json`) reuse the outbox to notify org admins about waivers, remediation SLAs, and drift events.

### 2.2 Provider adapters & compliance envelopes (binding)

**Purpose:** Encapsulate provider-specific delivery logic while enforcing org-level compliance (DMARC, STOP/HELP, residency). **|**
**Contract:** Adapter registry defines connectors (`email`, `sms`, future push); each adapter must be idempotent, sign payloads, and honor residency (`regions.allowlist.messaging`). Email requires SPF/DKIM alignment and DMARC >= `quarantine`; SMS implements opt-in/opt-out flows with STOP/HELP keywords and regional sender policies. **|**
**State:** Adapter metadata lives in Settings (`notifications.providers[]`); runtime caches provider capabilities and throttle envelopes. **|**
**Failures & handling:** Provider drift (status≠healthy) opens circuit, pauses sends, and triggers `RB-NOTIFY-OUTAGE`; compliance violations quarantine org sending until resolved. **|**
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
**Failures & handling:** Signature mismatch → HTTP 401 `AUTH_SIGNATURE_INVALID`, audit `NOTIFY_WEBHOOK_SIGNATURE_FAIL`, `RB-NOTIFY-WEBHOOK`. Duplicated events deduped by unique constraint. **|**
**Observability:** Metrics `notifications_webhook_total{status}`, `notifications_receipt_latency_seconds`; alert `alert_notifications_webhook_signature`. **|**
**Breadcrumbs:** Webhook handler `apps/platform/notifications/webhooks.py::handle_provider_event`, tests `tests/platform/notifications/test_webhook_hmac.py`, secure view migration `db/migrations/security/015_delivery_receipt_secure.sql`. **|**
**References:** §4.2 Receipts schema, §6 Observability.

- Download attempts revalidate residency each time by comparing `artifact.manifest.storage_region` against current allowlists; violations return 403 `POLICY_BLOCK` and log `NOTIFY_REGION_BLOCKED`.
- Audit events include correlation IDs linking outbox row, receipt, artifact, and job.

### 2.4 Download tokens & secure delivery (binding)

**Purpose:** Limit artifact downloads to signed tokens with residency and expiry enforcement. **|**
**Contract:** Tokens embed `{artifact_id, org_id, checksum, expires_at, single_use?}` signed with service key. Validation checks signature, expiry, single-use, and residency before streaming. **|**
**State:** `download_token` table captures issued tokens, redemption timestamps, issuer, and advisory metadata. **|**
**Failures & handling:** Tampered token → 403 `TOKEN_INVALID`; expired token → 410 `TOKEN_EXPIRED`; single-use replays produce 409 `TOKEN_ALREADY_USED`; audit `DOWNLOAD_TOKEN_DENIED`. **|**
**Observability:** Metrics `download_token_validation_total{outcome}`, `download_stream_started_total`; Grafana “Download Tokens” panel. **|**
**Breadcrumbs:** Token issuer `apps/platform/notifications/download_tokens.py::issue`, validator `apps/platform/notifications/download_tokens.py::validate`, tests `tests/platform/notifications/test_download_tokens.py`. **|**
**References:** Guardian §5 (artifact quarantine), Settings §5 (token TTL keys).

- Portal invalidation calls `apps/platform/portal/notifications.py::invalidate_links`, emits SSE `portal.link_invalidated`, and writes audit entries; see TDD §11.5 summary.
- Tokens include optional `limited_scope` field for per-role gating (e.g., `client_portal` vs. `staff`).

### 2.5 Templates, digests, and escalation (normative)

**Purpose:** Ensure message content stays localized, policy-compliant, and audited. **|**
**Contract:** Templates (`notifications.templates[]` in Settings) define channel, locale, compliance tags, and allowed merge fields. Changes require dual approval and produce `NOTIFY_TEMPLATE_VERSION` artifacts. Weekly digests (residency, policy waivers) render via Lang templates and store audit JSON under `ops/residency/`. **|**
**State:** Template manifests record `{template_id, version, locale, checksum}`; digests produce `DIGEST` artifacts with metadata linking incidents. **|**
**Failures & handling:** Missing localization fallback → job failure `TEMPLATE_LOCALE_MISSING`; compliance tag mismatch blocks send with `NOTIFY_TEMPLATE_POLICY_BLOCK`. **|**
**Observability:** Metrics `notifications_template_render_total`, `notifications_digest_generated_total`; digest pipeline logs `ops/residency/digest_<iso_week>.json`. **|**
**Breadcrumbs:** Template renderer `apps/platform/notifications/templates.py`, digest job `apps/platform/operations/task_modules/notifications.py::generate_digest`, tests `tests/platform/notifications/test_template_render.py`. **|**
**References:** LP Engine §2 (localization bundles), Settings §5.2 template keys.

- Review timeout escalation (Settings `reviews.timeout_hours`) triggers notifications to reviewers and `org_admin`, recording audit `REVIEW_TIMEOUT_ESCALATED`.
- Compliance templates for regulator/customer incidents tracked under `ops/runbooks.md`.

### 2.6 In-app notifications & SSE fan-out (binding)

**Purpose:** Deliver low-latency notifications within staff and client portals with read receipts and rate limiting. **|**
**Contract:** In-app notifications emit SSE/Channels payloads, persist `IN_APP_NOTIFICATION` artifacts when audit requires retention, and obey Settings caps `notifications.in_app.rate_limit_per_minute`, `notifications.in_app.daily_cap`. Read receipts recorded per user. **|**
**State:** In-app queue stores pending events with OCC fields to prevent duplicate delivery; receipts tie to case/job context. **|**
**Failures & handling:** Rate-limit breaches respond with 429 `NOTIFY_RATE_LIMITED`; SSE failure triggers reconnect with exponential backoff; anomalies escalate via `alert_notifications_inapp_anomaly`. **|**
**Observability:** Metrics `inapp_notification_sent_total`, `inapp_notification_read_total`, `sse_connection_drop_total`; dashboards “In-App Notifications” and “SSE Health”. **|**
**Breadcrumbs:** Fan-out service `apps/platform/notifications/inapp.py`, SSE publisher `apps/platform/events/notifications.py`, tests `tests/platform/notifications/test_inapp_rate_limits.py`, `tests/platform/ui/test_notification_toast.py`. **|**
**References:** Guardian §5 (quarantine notices), TDD §11 summary.

- Edit workflows emit notifications `edit.started`, `edit.updated`, `edit.ready_for_review`, `edit.policy_blocked` with deep links; Guardian quarantines produce Security/Compliance notifications carrying context metadata.
- Portal invalidations broadcast `portal.link_invalidated` to affected sessions.

______________________________________________________________________

## 3) API Contract

**Purpose:** Document the interfaces used to enqueue outbound messages, fetch receipts, and accept provider callbacks. **|**
**Contract:** Internal APIs accept authenticated REST requests (OAuth2) with OCC; provider callbacks rely on HMAC-signed webhooks. All endpoints versioned under `/api/v1/notifications/`. **|**
**State:** REST endpoints mutate `outbox_delivery`, `delivery_receipt`, `download_token`, and in-app notification queues. **|**
**Failures & handling:** Idempotency conflicts, missing HMAC signatures, stale tokens return typed errors with audit events. **|**
**Observability:** API metrics `notifications_api_request_total`, latency histograms, audit `NOTIFY_API_*` events; Spectral lints enforce OpenAPI coverage. **|**
**Breadcrumbs:** API router `apps/platform/api/notifications.py`, schema `spec/schemas/notification_outbox.schema.json`, tests `tests/platform/api/test_notifications_api.py`. **|**
**References:** OpenAPI bundle `ops/openapi/uDocket-platform.openapi.yaml`, ADR-0002.

### 3.1 External Interfaces

- `POST /api/v1/notifications/outbox` — enqueue email/SMS/in-app notifications; requires `Idempotency-Key`. Payload includes `{channel, template_id, locale, recipient, context}`. Responds with `{outbox_id, status}`.
- `GET /api/v1/notifications/outbox/{id}` — fetch status; includes receipt summary.
- `POST /api/v1/notifications/providers/{provider}:webhook` — provider callbacks; signed with `X-Request-Signature`. Returns 202 when accepted.
- `POST /api/v1/notifications/download-tokens` — issue signed tokens; returns `{token, expires_at}`. Allowed roles defined in Settings.
- `POST /api/v1/notifications/inapp` — internal endpoint for agent workers to enqueue in-app notifications with case/job scoping.

### 3.2 Internal Interfaces

- Celery tasks `notifications.dispatch_outbox` and `notifications.generate_digest` run within worker cluster, sized separately from agent queues.
- SSE publisher `apps/platform/events/notifications.py` broadcasts in-app and portal invalidation events. Channel topics namespaced `notifications.org.{org_id}` and `notifications.case.{case_id}`.
- Guardian/Compose integrations call `notifications.outbox.enqueue_review_timeout` to alert reviewers and escalate timeouts.

### 3.3 API Error Codes (binding) {#3-3-api-error-codes-binding}

**Purpose:** Enumerate Notifications `ApiError.code` values so producers, webhooks, and portal clients handle throttling and policy blocks consistently. **|**
**Contract:** Notifications reuse the platform catalog in [`Platform Runtime §3.3`](../platform/runtime.md#33-api-error-codes); the scenarios below map those codes to messaging semantics. **|**
**State:** Error envelopes originate from outbox APIs, download token issuance, and webhook ingestion; schema parity enforced by `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and `tests/platform/notifications/test_api_errors.py`; runtime emissions trigger `notifications_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards “Notifications – API Errors” and “Notifications – Webhooks” monitor `notifications_api_error_total{code}`, `notify_rate_limit_total`; synthetic sends validate throttling and masking flows. **|**
**Breadcrumbs:** Controllers `apps/platform/notifications/views.py`, outbox workers `apps/platform/notifications/outbox.py`, webhook signer `apps/platform/notifications/webhooks.py`, tests `tests/platform/notifications/test_outbox_api.py`. **|**
**References:** Platform Runtime §3.3, Guardian spec §2.2, Settings spec §2.6, Ops runbooks `RB-NOTIFY-RATE`, `RB-NOTIFY-WEBHOOK`.

> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#communications-service)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Outbox entry replayed with a different payload or stale version. | Re-fetch outbox status, regenerate the payload or Idempotency-Key, and retry once. |
| `POLICY_BLOCK` | Guardian or masking rules blocked a message, attachment, or portal download token. | Show the Guardian reason, remediate content or policy configuration, and retry once cleared. |
| `PROVIDER_DEGRADED` | Email or SMS provider, or webhook endpoint, marked degraded with an open circuit. | Pause sends for the affected provider, alert operators, and resume once health recovers. |
| `RATE_LIMIT` | Org or channel exceeded outbound messaging or webhook throughput limits. | Honor Retry-After headers, queue retries with exponential backoff, and coordinate for sustained spikes. |
| `VALIDATION_ERROR` | Template context, attachment metadata, or download request failed schema checks. | Correct payload or template data and resubmit after validation passes. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | No | notifications_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | notifications_api_error_total<br>notify_policy_block_total |
| `PROVIDER_DEGRADED` | 503 | Yes | notifications_api_error_total<br>notifications_provider_health_total |
| `RATE_LIMIT` | 429 | No | notify_rate_limit_total |
| `VALIDATION_ERROR` | 400 | No | notifications_api_error_total |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

## 4) State Management (binding)

**Purpose:** Capture how notification templates, outbox state, and token metadata persist to guarantee delivery guarantees and auditing. **|**
**Contract:** Maintain append-only outbox entries, versioned templates, and signed download tokens tied to Settings activation and Guardian policies. **|**
**State:** Outbox tables, template registry, webhook signer state, token ledger, and Settings snapshots. **|**
**Failures & handling:** Outbox replay errors, template drift, or token mismatches raise `PORTAL_RATE_LIMIT`, Guardian policy blocks, or outbox retry alerts and trigger RB-NOTIFY-* runbooks. **|**
**Observability:** Dashboards “Notifications – Outbox” and “Notifications – Webhooks”, metrics `notify_outbox_pending_total`, `notify_rate_limit_total`, `notify_webhook_error_total`. **|**
**Breadcrumbs:** Outbox worker `apps/platform/notifications/outbox.py`, template activation `apps/platform/notifications/template_service.py`, token signer `apps/platform/notifications/webhooks.py`, tests `tests/platform/notifications/test_state_management.py`. **|**
**References:** Settings §2.6, Guardian §2.3, Observability §4.

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

## 5) Failure Modes

**Purpose:** Provide the resilience profile and default mitigations. **|**
**Contract:** Identify what must fail closed vs. degraded. **|**
**State:** Note circuit breakers, queues, or compensating transactions. **|**
**Failures & handling:** Enumerate incidents, fallback procedures, and manual runbooks. **|**
**Observability:** Alerts, dashboards, and SLOs tied to failure handling. **|**
**Breadcrumbs:** Runbooks, incident retros, chaos tests. **|**
**References:** Link to ops docs or ADRs describing failure strategy.

### 5.1 Provider outage or degradation (binding)

- Circuit breaker opens when provider health crosses thresholds; outbox stays in `PENDING` and SLA timer starts. Alerts `alert_notifications_delivery_health` page on-call; `RB-NOTIFY-OUTAGE` orchestrates failover or hold.
- Customer notifications triggered if pause >15 minutes or SLA breach risk; message templates stored under `INCIDENT_TEMPLATE`.

### 5.2 Webhook signature mismatch or drift (binding)

- Signature failures return 401, log `NOTIFY_WEBHOOK_SIGNATURE_FAIL`, and suspend webhook processing until provider keys validated. `RB-NOTIFY-WEBHOOK` covers key rotation, backlog replay, and audit evidence.

### 5.3 Compliance violations (STOP/HELP, DMARC drift) (binding)

- SMS STOP updates recipient state to `blocked`, logs `NOTIFY_SMS_STOP_RECEIVED`, and halts further sends until opt-in regained (`HELP` flows or manual override). DMARC drift blocks email channel until SPF/DKIM restored; Security team notified.

### 5.4 Download token abuse (binding)

- Repeated invalid tokens from an IP trigger rate-limit and Security alert `alert_notifications_token_abuse`. `RB-NOTIFY-TOKEN` details investigation, user lockout, and forced token rotation.

### 5.5 Internal queue backlog (normative)

- `delivery_queue_depth` and `inapp_notification_queue_depth` thresholds alert when backlog age exceeds SLA. RB-NOTIFY-QUEUE directs scale-up, DLQ inspection, and digest catch-up steps.

______________________________________________________________________

## 6) Observability

**Purpose:** Show how to detect and diagnose issues. **|**
**Contract:** List mandatory telemetry and alerting coverage. **|**
**State:** Capture dashboards, log pipelines, or tracing spans. **|**
**Failures & handling:** Note alert fatigue risks or blind spots. **|**
**Observability:** Detail metrics/logs/traces plus owners. **|**
**Breadcrumbs:** Monitoring configs, dashboards, alert definitions. **|**
**References:** Observability standards or shared appendices.

- Metrics:
  - Delivery: `delivery_success_ratio`, `delivery_retry_total`, `notifications_provider_status_total`, `notifications_webhook_total{status}`, `notifications_receipt_latency_seconds`.
  - In-app: `inapp_notification_sent_total`, `inapp_notification_click_total`, `sse_connection_drop_total`.
  - Tokens: `download_token_validation_total{outcome}`, `download_stream_started_total`.
  - Digests/templates: `notifications_digest_generated_total`, `notifications_template_render_total`.
- Logs: structured events `NOTIFY_SEND_*`, `NOTIFY_WEBHOOK_*`, `DOWNLOAD_TOKEN_*`; correlation IDs align outbox, receipt, artifact, case.
- Traces: span `notifications.send` wraps provider API calls with tags `{provider, channel, attempt}`; webhook ingestion spans annotate signature status.
- Dashboards: `infra/observability/dashboards/notifications_delivery.json`, `notifications_inapp.json`, `download_tokens.json`.
- Alert catalogue entries map to `RB-NOTIFY-\*` runbooks; docs CI ensures runbook references rely on catalog.

### 6.1 SLOs & Targets (binding)

**Purpose:** Capture delivery, webhook, in-app, and token reliability goals. **|**
**Contract:** Notification delivery, webhook ingestion, SSE drop rate, and token validation must satisfy the thresholds below before campaigns launch. **|**
**State:** Metrics `delivery_success_ratio`, `notifications_receipt_latency_seconds`, `sse_connection_drop_total`, `download_token_validation_total{outcome}`; dashboards “Notifications Delivery”, “Notifications In-App”, “Download Tokens”. **|**
**Failures & handling:** Breaches invoke RB-NOTIFY-OUTAGE, RB-NOTIFY-WEBHOOK, RB-NOTIFY-INAPP, or RB-NOTIFY-TOKEN prior to resuming automation. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, portal synthetics, and SSE monitors provide evidence. **|**
**Breadcrumbs:** Prometheus rules `infra/monitoring/notifications-prometheus-rules.yaml`, synthetic definitions `synthetics/notifications_*`, runbooks `docs/ops/runbooks/notifications/*.md`. **|**
**References:** TDD §11, Web App §6, Audit §4.

- **Delivery success:** ≥99.5% of outbound notifications reach provider or user receipt within channel SLA, tracked by `delivery_success_ratio` and `notifications_receipt_latency_seconds`. Breaches trigger RB-NOTIFY-OUTAGE and pause new campaigns until resolved.
- **Webhook ingestion latency:** Provider callbacks process within 60 seconds P95 (`notifications_receipt_latency_seconds` subset); overruns invoke RB-NOTIFY-WEBHOOK and force retry throttling audits.
- **In-app realtime health:** SSE drop rate (`sse_connection_drop_total` / connections) stays below 1% rolling 15 minutes; exceeding threshold pages RB-NOTIFY-INAPP before customer-facing impact widens.
- **Download token validation:** Unexpected deny rate (`download_token_validation_total{outcome="denied"}` minus abuse baseline) remains under 0.5%; anomalies escalate via RB-NOTIFY-TOKEN with security review.

______________________________________________________________________

## 7) Security & Compliance

**Purpose:** Capture authZ/authN, data handling classes, and regulatory duties. **|**
**Contract:** Define encryption rules, residency bounds, and audit requirements. **|**
**State:** Describe secrets, key rotation, and data classifications. **|**
**Failures & handling:** Explain how breaches or policy drifts are detected and resolved. **|**
**Observability:** Security alerts, audit trails, compliance evidence. **|**
**Breadcrumbs:** IAM configs, policy bundles, compliance tests. **|**
**References:** Link to residency or policy appendices/ADRs.

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

## 8) Operational Notes

**Purpose:** Maintain resilient notification delivery, provider readiness, and compliance evidence. **|**
**Contract:** On-call rotations, runbooks, drills, and release workflows must remain current; notification channels pause when health or compliance gates fail until remediation completes. **|**
**State:** Runbooks under `ops/runbooks/notifications/`, drill evidence `ops/notifications/drills/<date>/`, DMARC onboarding reports `ops/notifications/dmarc/`, STOP/HELP audit logs in App.O. **|**
**Failures & handling:** Stale playbooks, missed drills, or expired DMARC/SPF attestations trigger incidents and block change approvals. **|**
**Observability:** Docs lint (`make docs.check.runbooks`), dashboards “Notifications Delivery” / “In-App Notifications”, alert `alert_notifications_delivery_health`. **|**
**Breadcrumbs:** Runbook catalog `docs/ops/runbooks.md`, drill scheduler `ops/scripts/notifications/schedule_drills.py`, provider automation `ops/scripts/notifications/*.py`. **|**
**References:** §5 Failure modes, §6 Observability, §7 Security & compliance, Ops governance policy App.N.

### 8.1 Operational Posture (binding)

**Purpose:** Capture on-call coverage, freeze windows, and readiness expectations. **|**
**Contract:** Platform Engineering (queue health) and Operations Engineering (provider integrations) share PagerDuty “Notifications SLO”, staff a 24/7 rotation, and honor change freezes during major provider cutovers. **|**
**State:** Roster `ops/notifications/roster.yaml`, freeze calendar `ops/notifications/freeze_windows.ics`, provider credential inventory `ops/notifications/provider_credentials.md`. **|**
**Failures & handling:** Staffing gaps or ignored freezes trigger management review; deployments pause until coverage restored. **|**
**Observability:** PagerDuty analytics, delivery dashboards, alert `notifications_oncall_gap_total`. **|**
**Breadcrumbs:** Roster docs, freeze calendars, App.O escalation notes. **|**
**References:** Communications spec §7, `RB-NOTIFY-\*`.

### 8.2 Incident Triggers (binding)

**Purpose:** Map alerts and dashboards to notification runbooks so responders act immediately. **|**
**Contract:** Alert rules (`infra/monitoring/notifications-prometheus-rules.yaml`) embed `RB-NOTIFY-\*` identifiers; evidence logged before closing incidents. **|**
**State:** Incident records `ops/notifications/incidents/<date>.jsonl` capture provider, channel, and alert metadata. **|**
**Failures & handling:** Missing annotations or muted routes require corrective PRs and Ops governance follow-up. **|**
**Observability:** Dashboards “Notifications Delivery”, “SMS Compliance”, Alertmanager routes. **|**
**Breadcrumbs:** Alert rule files, PagerDuty services, SIEM integrations. **|**
**References:** §5 Failure modes, `RB-NOTIFY-OUTAGE`, `RB-NOTIFY-WEBHOOK`, `RB-NOTIFY-SMS`, `RB-NOTIFY-TOKEN`.

- `alert_notifications_delivery_health` detects provider degradation and opens `RB-NOTIFY-OUTAGE`.
- `alert_notifications_sms_compliance` / `notifications_sms_stop_spike_total` drive `RB-NOTIFY-SMS` for STOP/HELP surges and regulatory response.
- `notifications_token_abuse_total` escalates access breaches via `RB-NOTIFY-TOKEN`.
- `notifications_webhook_signature_fail_total` triggers `RB-NOTIFY-WEBHOOK` for signature rotation and backlog replay.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Keep playbooks executable and drills current for core notification scenarios. **|**
**Contract:** Alerts map to `RB-NOTIFY-\*` runbooks; quarterly drills rehearse provider failover, webhook compromise, STOP/HELP compliance surges, and download-token abuse investigations. **|**
**State:** Runbooks `ops/runbooks/notifications/*.md`, drill evidence `ops/notifications/drills/<date>/summary.md`. **|**
**Failures & handling:** Missing drill evidence or outdated steps block change approval until updated. **|**
**Observability:** Docs lint, Ops governance dashboards, drill scheduler reports. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler, Slack `#ops-notifications`. **|**
**References:** `RB-NOTIFY-OUTAGE`, `RB-NOTIFY-WEBHOOK`, `RB-NOTIFY-SMS`, `RB-NOTIFY-TOKEN`.

#### 8.3.1 Runbook Index (informative)

| Runbook code | Scenario | Notes |
| --- | --- | --- |
| `RB-NOTIFY-OUTAGE` | Provider outage / degraded delivery | Provider escalation paths, failover to backup channel |
| `RB-NOTIFY-WEBHOOK` | Webhook signature drift / compromise | Key rotation, backlog replay, SIEM coordination |
| `RB-NOTIFY-SMS` | STOP/HELP surge & regulatory response | Compliance scripts, opt-in reinstatement |
| `RB-NOTIFY-TOKEN` | Download token abuse or leak | Token rotation, artifact quarantine |

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Document operational playbooks responders execute during incidents or exercises. **|**
**Contract:** Link production alerts to runbook identifiers, outline execution cadence, and name the maintaining team. **|**
**State:** Summarize where runbooks live (repo paths, automation scripts) and what evidence they produce. **|**
**Failures & handling:** Explain how missing, stale, or skipped runbooks are surfaced and remediated. **|**
**Observability:** Note tooling that tracks drill frequency, runbook completion, and incident follow-up. **|**
**Breadcrumbs:** Runbook files, automation scripts, incident templates. **|**
**References:** Alert catalogs, governance docs referencing the runbooks.

- `RB-NOTIFY-OUTAGE` — Executes provider failover, backlog drainage, and SLA communications.
- `RB-NOTIFY-WEBHOOK` — Rotates webhook secrets, replays payloads, and coordinates SIEM review.
- `RB-NOTIFY-SMS` — Handles STOP/HELP surges, regulator notifications, and opt-in reconciliation.
- `RB-NOTIFY-TOKEN` — Investigates token abuse, rotates secrets, and quarantines compromised artifacts.

#### 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover provider failover, webhook compromise, STOP/HELP surge, and token abuse scenarios with evidence stored in `ops/notifications/drills/<date>/`.
- Drill scheduler `ops/scripts/notifications/schedule_drills.py` tracks cadence; missed drills block change approvals until evidence uploaded.
- Docs lint and Ops governance dashboards verify runbook freshness and drill completion ahead of production changes.

### 8.4 Migrations & Backfills (normative)

**Purpose:** Govern provider onboarding, template migrations, and DLQ replays. **|**
**Contract:** Provider credential rotations and template migrations require change tickets, dry-run evidence, and rollback plans; DLQ replays run in preview before promotion. **|**
**State:** Migration scripts `ops/scripts/notifications/onboard_provider.py`, template bundles `config/notifications/templates/*.json`, DLQ replay logs `ops/notifications/dlq_replay/<date>/`. **|**
**Failures & handling:** Failed migrations revert to previous provider/template and open `RB-NOTIFY-OUTAGE`; replay failures quarantine payloads until corrected. **|**
**Observability:** Metrics `notifications_migration_success_total`, `notifications_dlq_replay_total`, App.O change tickets. **|**
**Breadcrumbs:** Migration scripts, template bundles, DLQ tooling. **|**
**References:** Settings spec §5, Communications spec §4.

### 8.5 Operational Workflows (normative)

**Purpose:** Document recurring tasks that sustain notification compliance and quality. **|**
**Contract:** Teams review DMARC/SPF attestations quarterly, refresh STOP/HELP evidence, generate weekly residency digests, and audit digest accuracy before distribution. **|**
**State:** DMARC reports `ops/notifications/dmarc/<quarter>/`, residency digests `ops/residency/digest_<iso_week>.json`, STOP/HELP audit logs `ops/notifications/sms_opt_out.csv`. **|**
**Failures & handling:** Expired DMARC alignment or missing digests trigger `RB-NOTIFY-SMS` and governance follow-up; digest discrepancies open App.O remediation tasks. **|**
**Observability:** Metrics `notifications_digest_generated_total`, `notifications_dmca_alignment_total`, STOP/HELP dashboards in SIEM. **|**
**Breadcrumbs:** Digest generator `apps/platform/operations/task_modules/notifications.py::generate_digest`, compliance scripts `ops/scripts/notifications/audit_opt_out.py`. **|**
**References:** §7 Security & compliance, §4 State management.

- Weekly residency digests aggregate waivers, remediation SLAs, and provider drift; evidence archived alongside digests.
- STOP/HELP audit jobs reconcile opt-out state with provider receipts to enforce compliance.
- DMARC/SPF attestations renewed before enabling custom sender domains; automation blocks production traffic when alignment lapses.

______________________________________________________________________

## 9) Dependencies

**Purpose:** List upstream/downstream systems and their contracts. **|**
**Contract:** Describe expectations on dependency behaviour and change management. **|**
**State:** Identify shared schemas/events and their owners. **|**
**Failures & handling:** Explain cascading failure protections. **|**
**Observability:** Dependency health checks and joint dashboards. **|**
**Breadcrumbs:** Integration specs, dependency docs. **|**
**References:** Link to other service docs or appendices.

| Dependency | Interface / artifact | Responsibilities | Notes |
| --- | --- | --- | --- |
| Settings Registry | Keys `notifications.*`, rate limits, provider configs | Supplies templates, throttles, provider secrets, DMARC policy enforcement | Activation diff artifacts archived with template/version metadata |
| Localization & Policy Engine | Locale bundles `i18n.notifications.*`, residency policy hints | Ensures localized copy, policy context for residency checks | Digests rely on LP Engine fallback logic |
| Guardian | Quarantine verdicts, moderation verdict SSE | Blocks unsafe notifications, provides context for Security/Compliance notifications | Quarantine reasons surface in notifications payloads |
| Worker Cluster (Celery)| Task modules `notifications.dispatch_outbox`, `notifications.generate_digest` | Executes delivery batches, digest generation, DLQ fan-out | Separate queue to isolate from agent workloads |
| Portal/Client apps | SSE endpoints, download token validation | Renders in-app notifications, enforces single-use tokens, shows invalidation banners | Portal invalidation logic in `apps/platform/portal/notifications.py` |
| Ops analytics | Runbook catalog, drill scheduler | Tracks runbook freshness, drill cadence, compliance evidence | Buildkite docs job fails when catalog stale |

______________________________________________________________________

## 10) References

- TDD overview summary — `../overview/tdd.md §11` (Notifications bullet list).
- Settings Registry specification — `../platform/settings.md §5.2` (notifications keys).
- Localization & Policy Engine — `../automation/lp-engine.md §2.1` (locale bundles for notifications).
- Ops runbook catalog — `../ops/runbooks.md` (`RB-NOTIFY-\*` entries).
- ADR-0002 — API versioning & sunset policy for notification endpoints.
- ADR-0003 — Localization & Policy Engine governance for templates.

______________________________________________________________________

## Appendix A — Event catalog & streaming contract (binding) {#appendix-a-event-catalog-streaming-contract}

**Purpose:** Keep the authoritative catalog of notification and portal SSE events in one place. **|**
**Contract:** Publishers emit events that validate against the shared schemas; consumers implement the envelope contract and respect replay/SLO requirements. **|**
**State:** Schemas live at `spec/schemas/sse/event_envelope.schema.json` with code‑generated models in `packages/udocket_core/events/schemas.py`. Redis streams back SSE buffers with 24 h retention. **|**
**Failures & handling:** Schema drift or SLO regressions fail staging drills and block deploys; alerts `alert_sse_delivery_lag_high` and `alert_sse_snapshot_regression` route to on-call. **|**
**Observability:** Dashboards “SSE Health” and “Notifications Fan-out” track `sse_client_delivery_lag_seconds`, `sse_snapshot_size_bytes`, `notifications_inapp_sent_total`. **|**
**Breadcrumbs:** Publishers `apps/platform/events/*.py`, fan-out service `apps/platform/notifications/inapp.py`, tests `tests/platform/realtime/test_sse_payloads.py`, `tests/e2e/test_sse_reconnect.py`, `tests/e2e/test_sse_token_binding.py`. **|**
**References:** Web app spec Appendix A, Settings Registry §5.2 (`notifications.*` keys).

### A.1 Event types

- Core lifecycle: `job.accepted`, `job.running`, `job.update`, `job.blocked`, `job.quarantined`, `job.completed`, `job.canceling`, `job.canceled`.
- Artifact transitions: `artifact.status`, `qa.notes`, `SIGNATURE.APPLIED`, `DELIVERABLE.RELEASED`, `DELIVERABLE.REVOKED`.
- Portal & notifications: `portal_link_invalidated`, `notifications.toast`, `notifications.digest_ready`.
- Provider health: `provider.health`, `settings.activated`, `settings.changed`.
- Status model lifecycle: `OBJECT.STORED`, `OBJECT.PROCESSING.START|END`, `OBJECT.FAILED`, `OBJECT.PENDING_JUDGMENT`, `OBJECT.CLEARED_FOR_USE`, `OBJECT.OPERATOR_PREP`, `REVIEW.REQUESTED`, `REVIEW.QUEUED`, `REVIEW.SKIPPED`, `REVIEW.APPROVED`, `REVIEW.CHANGES_REQUESTED`, `REVIEW.QUARANTINED`, `GUARDIAN.JUDGMENT.PASS|WARN|BLOCK|WAIVED`.

Each payload includes `schema_version` and `emitted_at` (RFC3339 with timezone) so clients can branch logic during schema upgrades. Producers emit at-most-once business transitions but SSE delivery remains at-least-once; consumers dedupe on `id`.

### A.2 Envelope and replay semantics

- Envelope fields: `id` (monotonic per stream), `event`, `data` (JSON), optional `retry` (ms). `id` echoes in `Last-Event-ID`.
- Digest + caching: Clients send `If-None-Match` with the last digest; servers respond with `ETag: sse:{scope}:{digest_sha256}`. Digest mismatches trigger bounded snapshots (≤ 500 events, `watermark_ts` included) before live tailing.
- Size limits: events ≤ 8 KiB payload (post‑JSON), snapshots ≤ 5 MiB serialized, build time ≤ 2 s. Schemas encode field length limits to make budgets enforceable.
- Retention: Redis stream retains 24 h; reconnects beyond the window receive latest snapshot plus live tail.
- Load testing: quarterly chaos run `scripts/sse/load_test.py` fans 5k concurrent tails at 1 Hz updates to validate capacity.

### A.3 SLOs & acceptance

- Delivery latency: 95th percentile \< 2 s, 99th percentile \< 5 s (`sse_client_delivery_lag_seconds`).
- Snapshot guardrails: `sse_snapshot_build_duration_seconds` and `sse_snapshot_size_bytes` stay within limits; alert `alert_sse_snapshot_regression` blocks deploys if breached.
- Token binding & security: `tests/e2e/test_sse_token_binding.py::test_disconnect_on_org_switch` ensures token/org mismatches close connections and emit `SSE_DISCONNECT_TOKEN_MISMATCH`.
- Contract validation: `tests/platform/realtime/test_sse_payloads.py` validates schema; `tests/e2e/test_sse_reconnect.py` exercises Last-Event-ID replay plus snapshot delivery.

### A.4 Payload hints

`data.meta` may include `{phase, percent, next_action, badges[]}` aligned with UI progress widgets (e.g., `phase="Judgment"`, `badges=["WARN:PII detector"]`). Providers pipe region/latency metrics into `provider.health`; finance signals surface via `job.blocked` with `warning="BUDGET_HELD"`.

______________________________________________________________________

## Appendix B — Database enforcement patterns (binding) {#appendix-b--database-enforcement-patterns}

**Purpose:** Capture authoritative SQL for portal messaging row-level security, delivery receipt partitioning, and download token enforcement.

### B.1 Portal messaging RLS

```sql
CREATE POLICY msg_thread_vis ON message_thread
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('MESSAGE_THREAD', 'read', case_id, NULL, NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('MESSAGE_THREAD', 'write', case_id, NULL, NULL)
);

CREATE POLICY msg_vis ON message
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('MESSAGE', 'read', case_id, NULL, NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('MESSAGE', 'write', case_id, NULL, NULL)
);

CREATE POLICY msg_att_vis ON message_attachment
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('MESSAGE_ATTACHMENT', 'read', case_id, NULL, NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('MESSAGE_ATTACHMENT', 'write', case_id, NULL, NULL)
);

CREATE POLICY msg_read_vis ON message_read_receipt
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND EXISTS (
    SELECT 1 FROM message m
    WHERE m.id = message_read_receipt.message_id
      AND udocket_can('MESSAGE', 'read', m.case_id, NULL, NULL)
  )
);
```

### B.2 Messaging tables (illustrative DDL)

```sql
CREATE TABLE message_thread (
  id uuid PRIMARY KEY,
  org_id uuid NOT NULL,
  case_id uuid NOT NULL,
  title text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE message (
  id uuid PRIMARY KEY,
  org_id uuid NOT NULL,
  case_id uuid NOT NULL,
  thread_id uuid NOT NULL REFERENCES message_thread(id) ON DELETE CASCADE,
  author_id uuid NOT NULL,
  body text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE message_attachment (
  id uuid PRIMARY KEY,
  org_id uuid NOT NULL,
  case_id uuid NOT NULL,
  message_id uuid NOT NULL REFERENCES message(id) ON DELETE CASCADE,
  content_uri text NOT NULL,
  content_sha256 text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE message_read_receipt (
  id uuid PRIMARY KEY,
  org_id uuid NOT NULL,
  message_id uuid NOT NULL REFERENCES message(id) ON DELETE CASCADE,
  reader_id uuid NOT NULL,
  read_at timestamptz NOT NULL DEFAULT now()
);
```

### B.3 Receipt partitioning

```sql
ALTER TABLE delivery_receipt PARTITION BY RANGE (created_at);
CREATE TABLE delivery_receipt_2025_01 PARTITION OF delivery_receipt
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

- Rotation job `ops/db/rotate_partitions.py` creates upcoming partitions, seals old partitions, and refreshes indexes. `audit_event` partitioning remains documented in the Platform Runtime specification.

### B.4 Download tokens (single-use enforcement)

```sql
CREATE TABLE download_token (
  id UUID PRIMARY KEY,
  artifact_id UUID NOT NULL,
  org_id UUID NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  single_use BOOLEAN NOT NULL DEFAULT FALSE,
  consumed_at TIMESTAMPTZ NULL
);

CREATE INDEX download_token_lookup
  ON download_token (artifact_id, expires_at);

UPDATE download_token
   SET consumed_at = now()
 WHERE id = :token_id
   AND single_use = TRUE
   AND consumed_at IS NULL
   AND expires_at > now()
RETURNING 1;
```

- Validation logic must succeed before streaming artifacts, then verify Guardian status, storage region allowlists, and audit logging. Metrics `download_token_validation_total{outcome}` and `download_stream_started_total` monitor enforcement.

### B.5 Delivery receipt secure view

```sql
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

REVOKE SELECT ON TABLE delivery_receipt FROM udocket_app;
GRANT  SELECT ON delivery_receipt_secure TO udocket_app;
```

- View enforces org-scoped access and pairs with Settings-driven masking/retention policies. Identity’s Appendix A covers the shared `udocket_can` enforcement that this view relies on.
