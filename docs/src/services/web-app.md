---
title: uDocket — Web Application & Portal Specification
subtitle: Staff Workspace, Client Portal, and UI Governance
author:
  - Application Experience Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-23
owners:
  - Platform Engineering
  - Product Management
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - Accessibility Program Lead
  - Operations Engineering
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
  - <header class="page-header">uDocket — Web Application & Portal Specification <br>
    Staff Workspace, Client Portal, and UI Governance</header>
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
| Primary owners | Platform Engineering; Product Management |
| Approvers      | Architecture Steering Committee; Security Review Board |
| Reviewers      | Accessibility Program Lead; Operations Engineering |
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

- **Scope:** Describes the staff-facing workspace, reviewer consoles, and the client portal. Covers accessibility, collaboration, security posture, manual/agent edit tooling, conversational assistants, and document assembly flows.
- **Structure:** Sections follow the standard 0–10 service template. Responsibilities (§2) map to the major UI pillars; APIs (§3) reference capability discovery, SSE topics, and secure download flows; state, failure, observability, and compliance requirements are consolidated in §§4–7.
- **Maintenance:** Run `python scripts/docs/lint_docs.py docs/src/services/web-app.md docs/src/overview/tdd.md docs/tdd_modularization.md` before submitting UI changes. Accessibility or localization updates must retain Appendix references and regenerate Vale/axe snapshots where noted.
- **Change protocol:** UX-affecting PRs update this spec and cite ADR-0003 when API contracts change. Security posture updates (headers, invalidation flows, break-glass) require Security + Architecture approval.
- **References:** TDD §11 summary, Guardian spec §5, Notifications spec §2.6, Settings Registry §5 (UI policy keys), Ops runbooks RB-PORTAL-INVALIDATION and RB-JOB-WATCHDOG.
- **Contacts:** Platform Engineering (frontend owners), Product Management (experience roadmap), Accessibility guild, `#web-app` Slack channel, on-call rotation `webapp-oncall@`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Deliver compliant, accessible, real-time experiences for staff and clients to review, approve, and receive platform artifacts. **|**
**Contract:** The web app must respect policy masks, Guardian verdicts, residency controls, and rate limits while providing deterministic state transitions and audit trails. **|**
**State:** UI derives state from case-scoped timelines, artifact manifests, Guardian history, outbox receipts, and Settings-driven feature toggles. **|**
**Failure modes & handling:** SSE disconnects, stale tokens, portal invalidations, or edit workflow violations surface actionable messaging, link to runbooks, and avoid silent failure. **|**
**Observability:** Grafana dashboards (“Operator Workspace”, “Portal Integrity”, “Notifications Delivery”, “Assistant Usage”) plus synthetic monitors and axe snapshots track health. **|**
**Breadcrumbs:** Frontend views `apps/platform/ui/views/*.py`, portal controllers `apps/platform/portal/*.py`, component library `packages/udocket_ui/*`, integration tests `tests/platform/ui/*.py`, Playwright suites `tests/e2e/ui/*.py`. **|**
**References:** §2 Responsibilities, §4 State management, §5 Failure modes, §7 Security & compliance.

______________________________________________________________________

## 2) Responsibilities

### 2.1 Staff operator workspace & approvals (binding)

**Purpose:** Provide case-centered tooling for operators and reviewers with deterministic status reporting. **|**
**Contract:** Case workspace renders artifact timelines, job state, approvals, Guardian outcomes, and analytics without exposing masked data. SSE/Channels feeds must stay case-scoped and honor RLS. **|**
**State:** Case dashboards pull from `case_secure`, `artifact_secure`, job manifests, Guardian verdicts, and FinOps metrics. **|**
**Failure modes & handling:** SSE disconnects fall back to polling with visible banners; missing Guardian verdicts lock approval actions pending remediation per RB-JOB-WATCHDOG. **|**
**Observability:** Metric panels `operator_break_glass_requested_total`, `review_queue_backlog_total`, `job_watchdog_warning_total`; synthetic monitors validate SSE and approval flows. **|**
**Breadcrumbs:** Operator view `apps/platform/ui/views/operator_workspace.py`, approval components `packages/udocket_ui/approvals/*`, tests `tests/platform/ui/test_operator_workspace.py`, `tests/platform/ui/test_review_approvals.py`. **|**
**References:** Notifications spec §2.6 (in-app alerts), Guardian spec §5 (verdict integration).

- Approvals panel enforces multi-step review with optimistic concurrency; UI surfaces reviewer counts, Guardian reason codes, backlog age warnings, and links to runbooks.
- Job tiles display watchdog warnings with tooltips summarizing latest heartbeat, lane, and remediation guidance.
- Analytics widgets expose LLM spend, artifact coverage, and QA issues, sourcing data from audit logs and FinOps metrics.
- Live status widget follows the accessible SSE pattern in App.U.5: `aria-live="polite"`, deterministic status badges (`data-status` mapped to design tokens), token-bound credentials, and retry backoff through shared `useConnectivity`.

### 2.2 Client portal (binding)

**Purpose:** Deliver masked, policy-compliant artifacts and messaging to clients with audit-friendly controls. **|**
**Contract:** Portal enforces org membership, masking, entitlement scopes, and download token validation; invalidations reflect instantly via SSE. **|**
**State:** Portal views consume `artifact_secure`, `delivery_receipt_secure`, entitlements, Guardian history, and notification digests. **|**
**Failure modes & handling:** Invalid or expired tokens return 403/410 with denial banners; policy violations trigger quarantine messaging and block downloads. **|**
**Observability:** Grafana “Portal Integrity” (`portal_link_invalidated_total`), “Abuse Signals” (`PORTAL_PHISHING_REPORT`), synthetic download tests. **|**
**Breadcrumbs:** Portal controllers `apps/platform/portal/*.py`, download guard `apps/platform/portal/downloads.py`, tests `tests/platform/portal/test_portal_invalidation.py`, notifications spec §2.4. **|**
**References:** Notifications spec (download tokens), Settings Registry §5.2 (portal toggles).

- Staff-triggered invalidations emit SSE `portal.link_invalidated`, revoke tokens, and present denial banners.
- Phishing reports log audit `PORTAL_PHISHING_REPORT` and feed abuse dashboards.
- Portal messaging integrates secure threads (§2.6) and applies retention aligned with case lifecycle.

### 2.3 Accessibility & localization (binding)

**Purpose:** Meet WCAG 2.2 AA requirements and deliver localized experiences across staff and portal surfaces. **|**
**Contract:** UI components honor semantic markup, keyboard navigation, focus management, and contrast budgets; localization keys originate from LP Engine bundles and pseudolocale checks block regressions. **|**
**State:** Localization assets live in Settings (`i18n.*`) and LP Engine bundles; accessibility evidence stored in Ops appendices. **|**
**Failure modes & handling:** Missing translations or accessibility regressions trigger runbook RB-LPE-LOCALE-GAP and block releases until evidence restored. **|**
**Observability:** Nightly axe snapshots, Playwright RTL runs, localization audit scripts (`ops/scripts/lpe/audit_locales.py`). **|**
**Breadcrumbs:** Component library `packages/udocket_ui/`, localization pipeline `packages/udocket_core/lpe/*`, tests `tests/e2e/test_accessibility.py`. **|**
**References:** LP Engine spec §2, Ops runbook index (LPE locale gap).

- Pseudolocale builds run pre-merge; Vale lint enforces accessibility wording.
- `aria-live`, focus trapping, and keyboard outreach patterns follow App.U guidelines; components failing contrast budgets require design review.

### 2.4 Real-time collaboration & presence (binding)

**Purpose:** Enable shared editing, presence indicators, and live updates without cross-case leakage. **|**
**Contract:** SSE and Channels sessions bind to case/org scopes, enforce SameSite cookies, and respect rate limits; optimistic updates reconcile with server events safely. **|**
**State:** Presence metadata stored in Redis; session context derived from case membership and settings toggles. **|**
**Failure modes & handling:** Connection drops raise UI banners and trigger exponential backoff; session mismatches force re-auth. **|**
**Observability:** Metrics `sse_connection_drop_total`, synthetic monitors for SSE schema version drift, audit `CHANNEL_SESSION_STARTED/ENDED`. **|**
**Breadcrumbs:** Channels configuration `apps/platform/ui/channels.py`, SSE publisher `apps/platform/events/*.py`, tests `tests/e2e/test_collaboration.py`. **|**
**References:** Notifications spec §2.6 (in-app notifications), Guardian spec (quarantine broadcasts).

### 2.5 Security posture & hardening (binding)

**Purpose:** Enforce secure defaults for headers, anti-phishing, download guards, and MFA/step-up workflows. **|**
**Contract:** Web and portal responses include CSP, HSTS, frameguard, referrer, and permissions policy headers; anti-phishing tooling logs and escalates suspicious activity. **|**
**State:** Header templates, download guard policies, phishing audit logs. **|**
**Failure modes & handling:** Header regressions fail CI; phishing detections raise alerts and prompt incident templates. **|**
**Observability:** Grafana “Frontend CSP”, `portal_412_precondition_total`, audit `PORTAL_DOWNLOAD_PRECONDITION`. **|**
**Breadcrumbs:** Security middleware `apps/platform/ui/security/csp.py`, download guard `apps/platform/portal/downloads.py`, phishing logger `apps/platform/notifications/phishing.py`, tests `tests/ui/test_csp_nonced.py`, `tests/platform/notifications/test_phishing_workflow.py`. **|**
**References:** Notifications spec (download tokens), Settings Registry (MFA/step-up toggles).

### 2.6 Secure portal messaging (binding)

**Purpose:** Offer case-scoped, RLS-enforced messaging with Guardian oversight. **|**
**Contract:** Messaging threads store artifacts (`ATTACHMENT_*`), enforce opt-in rate limits, and rely on signed URLs from the notifications service. **|**
**State:** Tables `message_thread`, `message`, `message_attachment`, `message_read_receipt`; attachments reference artifact IDs. **|**
**Failure modes & handling:** Abuse detection triggers alerts and throttles; retention aligns with case lifecycle. **|**
**Observability:** Metrics `message_delivery_total`, anomaly detectors on abuse signals, SSE updates for read receipts. **|**
**Breadcrumbs:** Messaging controllers `apps/platform/portal/messaging.py`, notifications spec §2.6, tests `tests/platform/portal/test_secure_messaging.py`. **|**
**References:** Notifications spec (tokens & in-app alerts), Guardian spec §5.

### 2.7 Manual and agent edit workflows (binding)

**Purpose:** Manage dual approval, provenance, and moderation for manual and AI-assisted edits. **|**
**Contract:** Manual edits produce child artifacts linked to parents; agent edits capture prompts, model settings, and moderation results. Dual approval enforces distinct reviewers via OCC and unique indices. **|**
**State:** Edit manifests track `{edit_type, editor_id, diff_fingerprint_sha256, model_id?, prompt_id?, moderation_outcome}` with logs in `ops/<job_id>__edit_log.jsonl`. **|**
**Failure modes & handling:** Policy violations (`EDIT_POLICY_BLOCK`) quarantine artifacts; repeated rejects page engineering. **|**
**Observability:** Metrics `edit_sessions_total{type}`, `edit_policy_block_total`, SSE events `edit.started|edit.updated|edit.ready_for_review`. **|**
**Breadcrumbs:** Edit controllers `apps/platform/ui/views/edit_flow.py`, LangGraph edit lanes `packages/udocket_core/agents/edit/*`, tests `tests/platform/ui/test_edit_workflow.py`. **|**
**References:** Guardian spec §5, LLM registry spec §2.3 (safety harness).

### 2.8 Document assembly pipeline (binding)

**Purpose:** Convert Compose outputs into deliverable-ready documents with signing prerequisites. **|**
**Contract:** Pipeline renders DOCX/PDF artifacts, lints placeholders, computes hashes, and enforces exclusive approvals; integrates with Digital Signer before portal release. **|**
**State:** `ASSEMBLED_DOC_*` artifacts progress `PROCESSING → PENDING_JUDGMENT → OPERATOR_PREP → APPROVAL_REQUESTED → QUEUED_FOR_REVIEW → APPROVED`; manifests capture template version and hash. **|**
**Failure modes & handling:** Lint errors surface warnings; pipeline halts until resolved; signing blockers escalate per Signer spec. **|**
**Observability:** Metrics `document_assembly_duration_seconds`, `document_assembly_error_total`; logs include lint warnings. **|**
**Breadcrumbs:** Assembly job `apps/platform/operations/task_modules/compose.py::assemble_documents`, signer spec §2, tests `tests/platform/operations/test_document_assembly.py`. **|**
**References:** Compose agent spec (future), Digital Signer spec §2.1.

### 2.9 Conversational assistants UX (binding)

**Purpose:** Deliver scoped AI assistants for staff and clients with auditability and policy enforcement. **|**
**Contract:** Assistants run LangGraph pipelines with retrieval restricted to authorized artifacts; sessions log manifests, Guardian verdicts, and moderation outcomes. Client assistant includes informational disclaimers. **|**
**State:** Chat sessions stored under `storage/media/cases/<case>/ops/<session_id>__chat_{audience}.jsonl`; manifests record `{model_id, prompt_version, retrieval_sources[], token_usage, latency_ms}`. **|**
**Failure modes & handling:** Policy violations (`CHAT_POLICY_BLOCK`, `CHAT_GUARDIAN_QUARANTINED`) disable access pending review; rate-limit exhaustion surfaces UI banners. **|**
**Observability:** Metrics `chat_sessions_total{audience}`, `chat_token_usage_total`, `chat_rate_limit_block_total`, dashboards “Assistant Usage” and “Assistant API”. **|**
**Breadcrumbs:** Assistant orchestrator `apps/platform/ui/assistants.py`, LangGraph pipelines `packages/udocket_core/agents/assistants/*`, tests `tests/e2e/test_chat_assistant.py`, API spec `ops/openapi/chat_assistants.yaml`. **|**
**References:** TDD §10.12 (capability APIs), LLM registry spec §2.3 (moderation), Notifications spec §2.6 (alerting).

- Staff Copilot sessions access approved artifacts, Guardian manifests, Settings snapshots, and portal messages with redaction. Outputs include citations and never mutate artifacts directly.
- Client portal guide constrains retrieval to approved deliverables and knowledge flagged `portal_visible=true`; policy violations return localized disclaimers.
- Rate limits derive from Settings `chat.staff.*` / `chat.client.*`; concurrency caps enforce `chat.session.max_active_per_user`.
- Moderation filters run pre-/post-call; Guardian escalations disable assistants automatically when severity ≥ high.

______________________________________________________________________

## 3) API contract

**Purpose:** Outline the interfaces powering the web app and portal experiences. **|**
**Contract:** REST endpoints require OAuth scopes (`org_operator`, `org_client`), enforce optimistic concurrency, and honor RLS context. SSE/Channels topics remain case/org scoped and versioned. **|**
**State:** APIs interact with views `*_secure`, outbox/download token tables, messaging threads, edit manifests, and chat session evidence. **|**
**Failure modes & handling:** Missing tokens, stale ETags, or scope violations return typed errors (`401`, `403`, `409`) with audit trails. **|**
**Observability:** API metrics `portal_request_total`, `review_action_total`, `chat_assistant_metadata_requests_total`; SSE schema changes trigger synthetic monitors. **|**
**Breadcrumbs:** REST controllers `apps/platform/api/*.py`, SSE publishers `apps/platform/events/*.py`, OpenAPI specs `ops/openapi/uDocket-platform.openapi.yaml`, `ops/openapi/chat_assistants.yaml`. **|**
**References:** Notifications spec (download/token APIs), Guardian spec (approval endpoints), ADR-0003 (versioning policy).

- Portal downloads require signed tokens from Notifications service; headers `If-Match` and download guard enforce conditional requests.
- Chat capability endpoints (`/api/v1/chat/assistants`) expose assistant metadata, rate limits, and disclaimers with ETag support.
- SSE topics: `case.{id}.timeline`, `case.{id}.edits`, `portal.link_invalidated`, `notifications.case.{id}`, `chat.assistant.updated`.

______________________________________________________________________

## 4) State management

- Secure views (`case_secure`, `artifact_secure`, `delivery_receipt_secure`, `message_thread_secure`) provide masked data to the UI; base tables remain inaccessible to the application role.
- Messaging and edit manifests capture provenance and feed Guardian/QA automation; artifacts link to versions and approvals for deterministic swap logic.
- Download tokens persist hashes, issuer, expiry, and redemption metadata; single-use enforcement lives in Notifications service.
- Chat session envelopes archive manifests and redacted transcripts under case ops directories; HIPAA mode stores hashes only.
- Localization bundles sourced from LP Engine (`i18n.*`); pseudolocale and regression evidence stored in ops appendices.

______________________________________________________________________

## 5) Failure modes

- **SSE disconnects:** UI shows offline banner, retries with exponential backoff; after repeated failure, fall back to polling and log `UI_SSE_FALLBACK`.
- **Portal invalidation:** Tokens revoked, requests return 403 with audit `PORTAL_DOWNLOAD_PRECONDITION`; UI presents denial banners and links to support.
- **Edit policy violations:** Agent edits blocked with `EDIT_POLICY_BLOCK`, Guardian quarantine triggered; reviewers notified via Notifications service.
- **Chat abuse:** Moderation triggers `CHAT_POLICY_BLOCK`; assistants disabled until Security resolves; incidents documented in App.O.
- **Accessibility regressions:** CI/VALE failures block releases; runbook RB-LPE-LOCALE-GAP executed to restore coverage.

______________________________________________________________________

## 6) Observability

- Dashboards: “Operator Workspace”, “Portal Integrity”, “Notifications Delivery”, “Assistant Usage”, “Accessibility & Localization”.
- Metrics: `review_queue_backlog_total`, `job_watchdog_warning_total`, `portal_link_invalidated_total`, `portal_phishing_report_total`, `inapp_notification_sent_total`, `chat_sessions_total{audience}`, `chat_policy_block_total`.
- Synthetic monitors: SSE schema validation, portal download smoke tests, chat latency & policy checks, axe accessibility scans.
- Logs: structured `UI_EVENT`, `PORTAL_EVENT`, `CHAT_SESSION`, `EDIT_EVENT` with correlation IDs and masked fields.

______________________________________________________________________

## 7) Security & compliance

- Enforce HSTS (min 1 year), CSP nonces, frameguard `DENY`, referrer policy `strict-origin-when-cross-origin`, permissions policy disabling camera/mic by default.
- Portal downloads require signed tokens and `If-Match` headers; replays denied even if token valid but entitlement revoked.
- Break-glass flows demand step-up MFA (WebAuthn) on activation and closure; events logged per `spec/schemas/break_glass_event.schema.json`.
- Manual/agent edits require audit provenance, dual approval for high-risk artifacts, and Guardian oversight.
- Conversational assistants require localized disclaimers, HIPAA gating, and moderation verdict logging.
- Accessibility and localization compliance captured in ops appendices for regulators; DSAR/erasure requests propagate to portal artifacts and chat transcripts.

______________________________________________________________________

## 8) Operations & runbooks

- Runbooks: RB-JOB-WATCHDOG (job tiles), RB-PORTAL-INVALIDATION (token revocation), RB-LPE-LOCALE-GAP (localization), RB-NOTIFY-* (alerts), RB-CHAT-ABUSE (assistant incident).
- Drill cadence: quarterly SSE resilience tabletop, accessibility regression audit, portal abuse simulation, assistant abuse scenario.
- Evidence: stored under `ops/webapp/drills/<date>/` with participants, remediation tasks, and dashboards snapshots.

______________________________________________________________________

## 9) Dependencies

| Dependency                | Responsibility                                                                | Notes                                                                           |
| ------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Notifications service     | In-app alerts, download tokens, escalation digests                            | See `../services/notifications.md`; SSE topics share infrastructure             |
| Guardian                  | Verdicts, quarantine enforcement, edit/assistant moderation                   | Guardian judgments gate approvals and portal delivery                           |
| LLM Registry              | Moderation & safety harness for agent edits and assistants                     | Settings keys `chat.*`, moderation controls                                     |
| LP Engine                 | Localization bundles, policy context for residency and masking                | Fallback logic for missing locales                                             |
| Settings Registry         | UI toggles, rate limits, step-up policies, chat enablement                     | Activation enforces governance and diff artifacts                               |
| Digital Signer            | Signed deliverables and manifest metadata for portal downloads                 | Document assembly pipeline produces signer inputs                               |
| Worker cluster (Celery)   | Document assembly, assistant orchestration, SSE backfills                      | Dedicated queues for UI-related background tasks                                |
| Ops runbook catalog       | Incident and drill references                                                  | Docs lint ensures RB-* entries stay current                                     |

______________________________________________________________________

## 10) References

- TDD overview summary — `../overview/tdd.md §11`.
- Notifications service specification — `../services/notifications.md`.
- Guardian specification — `../services/guardian.md`.
- Settings Registry specification — `../services/settings.md`.
- LLM Registry specification — `../services/llm-registry.md §2.3`.
- Digital Signer specification — `../services/digital-signer.md`.
- Ops runbook catalog — `../ops/runbooks/index.md`.
