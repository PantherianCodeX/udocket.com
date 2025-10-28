---
title: uDocket — Guardian Service Specification
subtitle: Canonical design, policy, and operational reference
author:
  - Guardian Service Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-23
owners:
  - Security Engineering
  - Platform Architecture
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - QA Engineering Lead
  - SRE Manager
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
  - <header class="page-header">uDocket — Guardian Service Specification <br> 
    Canonical design, policy, and operational reference</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page 
    <span class="page-number"></span> of <span 
    class="page-count"></span></footer>
---

______________________________________________________________________

## 0) Reading guide

Use this guide before changing Guardian policy, queue semantics, or downstream workflows.

- **Scope:** Guardian judgments, policy integration, API surface, queueing, observability, security, and operational controls.
- **Structure:** Sections follow the 0–10 service spec template; appendices hold payload samples and runbooks.
- **Maintenance:** Run the docs lint (`python scripts/docs/lint_docs.py`) and link check (`python scripts/docs/link_check.py --strict`) prior to submitting Guardian changes.
- **Change protocol:** Include a summary of Guardian impact in PR descriptions and link reviewers to the affected sections (`§2`, `§3`, `§4`, etc.).
- **References:** TDD §7 (Guardian), TDD Appendix H (legacy runbooks), ADR-0001, ADR-0003, ADR-0004.
- **Contacts:** Owners Security Engineering + Platform Architecture; operational mailing list `guardian-oncall@`.

______________________________________________________________________

## Document controls

| Field           | Value                                                                                                                                                                                                        |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Version         | 0.1-draft                                                                                                                                                                                                    |
| Status          | Implementable                                                                                                                                                                                                |
| Last updated    | 2025-10-23                                                                                                                                                                                                   |
| Primary owners  | Security Engineering; Platform Architecture                                                                                                                                                                  |
| Approvers       | Architecture Steering Committee; Security Review Board                                                                                                                                                       |
| Reviewers       | QA Engineering Lead; SRE Manager                                                                                                                                                                             |
| ADR index       | `docs/adr/README.md`                                                                                                                                                                                         |
| Migration plan  | Establishes this specification as the authoritative Guardian reference, absorbing the former TDD Guardian sections and Appendix H operational guides; platform TDD now links here for service-level details. |
| Docs validation | `python scripts/docs/lint_docs.py`                                                                                                                                                                           |
| Link lint       | `python scripts/docs/link_check.py --strict`                                                                                                                                                                 |

______________________________________________________________________

## 1) Purpose

**Purpose:** Establish Guardian’s mission as the platform safety gate that enforces residency, policy, and content integrity before artifacts progress.\
**Contract:** Every SA/WP/CD artifact must pass through Guardian; PASS/WARN/BLOCK/WAIVED semantics, latency targets, and queue idempotency stay consistent across releases.\
**State:** Guardian persists manifests, policy context hashes, waiver history, span detections, and queue telemetry in Postgres and the submission bus.\
**Failure modes & handling:** Queue saturation, classifier failures, or policy bundle drift trigger mitigations in §5 and operational drills in Appendix R.\
**Observability:** Grafana “Guardian SLO” dashboard (`guardian_judgment_latency_seconds`, `guardian_cleared_ratio`, `guardian_submission_queue_depth`), synthetic job `guardian_slo.yaml`, and Ops logs under `storage/media/cases/<case>/ops/guardian/`.\
**References:** §2 Responsibilities, §3 API contract, §4 State management, §5 Failure modes, §8 Operational notes, ADR-0001.\
**Breadcrumbs:** Code `apps/platform/operations/guardian.py`, `packages/udocket_core/guardian/`, Tests `tests/platform/guardian/test_guardian_enqueue.py`, Observability `infra/grafana/guardian_slo.json`.

- **Mission:** Issue deterministic PASS/WARN/BLOCK/WAIVED judgments before artifacts advance to review or client delivery, enforcing policy, residency, and safety controls.
- **Interfaces:** Internal RPC enqueue API, REST read APIs (`/readyz`, `/synthetic/status`, `/api/v1/guardian/...`), detection helpers (`/guardian/detect-and-mask`, `/guardian/quarantine`), and Postgres persistence with RLS.
- **Submission fabric:** Any SA/WP/CD creation or version bump transitions the artifact to `PENDING_JUDGMENT`; workers submit the payload to the regional Guardian queue (`guardian_submission_queue`). Guardian hydrates manifests, PolicyContext, waiver state, and classifier telemetry before emitting its judgment.
- **Event model:** Guardian emits SSE/audit events `GUARDIAN.JUDGMENT.{PASS|WARN|BLOCK|WAIVED}` with `guardian_judgment_id`, reason codes, policy snapshot hashes, and pointers to upstream findings. Reviewer-initiated quarantines round-trip through `POST /guardian/quarantine` so Guardian remains the canonical history.
- **Criticality:** 99.9% availability SLO with P95 judgment latency ≤ 5 minutes and queue backlog alert threshold of 5 minutes (`guardian.queue.backlog_alert_minutes`). Submit-time SLO is ≤ 1 second P95 from enqueue to first evaluation attempt under nominal load.
- **Region isolation:** Every residency boundary maintains an isolated Guardian deployment and queue; judgments never cross regions. HPAs keep ≥ 2 replicas per region (≤ 70 % CPU) and synthetic monitoring (`guardian_slo.yaml`) probes each cluster.
- **Dependencies:** Policy context from Localization & Policy Engine (LPE), Settings service (including `guardian.rules.version` bundles), Postgres, Redis/queue fabric, and OPA sidecars for rule evaluation.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Define Guardian’s enforcement scope, judgment vocabulary, escalation duties, and lifecycle integration points across the platform.\
**Contract:** Guardian is the single authority for PASS/WARN/BLOCK/WAIVED outcomes, status transitions, quarantine workflows, and waiver requirements.\
**State:** Judgment history, waiver manifests, quarantine records, and parent-child locks persist in Postgres tables (`guardian_judgment_history`, `guardian_waiver`, `guardian_relationship_lock`).\
**Failure modes & handling:** Mis-mapped statuses or waiver drift trigger remediation via §5.1 Incident triggers and Appendix R runbooks; parent-lock conflicts raise explicit errors.\
**Observability:** Metrics `guardian_cleared_ratio`, `guardian_waiver_total`, audit stream `storage/media/cases/<case>/ops/ops_guardian.jsonl`, and SSE event consumers instrument downstream reactions.\
**References:** TDD §7.3 (Artifact lifecycle), §5 Failure modes, Appendix A (reference artifacts), status mapping appendix in `docs/src/overview/tdd/appendices/status-mapping.md`.\
**Breadcrumbs:** Code `packages/udocket_core/guardian/judgment.py`, Queue orchestrator `apps/platform/operations/guardian.py`, Tests `tests/platform/guardian/test_status_mapping.py`.

### 2.1 Canonical judgments

| Judgment | Description                                          | Default actions                                               |
| -------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| PASS     | Requirements satisfied; artifact is safe to proceed. | Unlocks WP → `CLEARED_FOR_USE`, CD → `OPERATOR_PREP`.         |
| WARN     | Minor issues; proceed with operator banners.         | Same transitions as PASS; UI surfaces warnings.               |
| BLOCK    | Artifact violates policy, integrity, or residency.   | Sets status to `QUARANTINED`; requires remediation or waiver. |
| WAIVED   | Dual-approved override to treat as PASS.             | Same transitions as PASS; records waiver manifest entry.      |

### 2.2 Status mapping

*Purpose: Provide deterministic mapping from Guardian judgments to artifact statuses.*\\ *Contract: Tables below are the single source of truth; dependent services MUST reference them instead of duplicating logic.*

| Artifact class        | Prior status       | Guardian outcome | Next status       | Notes                             |
| --------------------- | ------------------ | ---------------- | ----------------- | --------------------------------- |
| Work Product          | `PENDING_JUDGMENT` | PASS/WARN/WAIVED | `CLEARED_FOR_USE` | WARN adds operator banner.        |
| Work Product          | `PENDING_JUDGMENT` | BLOCK            | `QUARANTINED`     | Remediation tracked via manifest. |
| Candidate Deliverable | `PENDING_JUDGMENT` | PASS/WARN/WAIVED | `OPERATOR_PREP`   | Entry point into review workflow. |
| Candidate Deliverable | `PENDING_JUDGMENT` | BLOCK            | `QUARANTINED`     | Prevents review queue admission.  |

| Condition                                             | Org policy posture    | Guardian judgment                  | Artifact status impact                        | Notes                                                                              |
| ----------------------------------------------------- | --------------------- | ---------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------- |
| PHI present while HIPAA mode **off**                  | Forbid PHI            | BLOCK (`HIPAA_REQUIRED`)           | `QUARANTINED`                                 | Requires enabling HIPAA mode or removing PHI before progression.                   |
| PHI present, HIPAA mode **on**, spans masked          | Allow masked          | PASS/WARN                          | `CLEARED_FOR_USE` (WP) / `OPERATOR_PREP` (CD) | WARN adds reviewer banner with span highlights.                                    |
| PHI present, HIPAA mode **on**, restoration requested | Allow full            | PASS                               | `APPROVED → SIGNED`                           | Compose detokenizes spans under vault policy; manifest records restoration intent. |
| Detector low confidence on high-risk entity           | Any                   | WARN (`CLASSIFIER_LOW_CONFIDENCE`) | Normal flow with banner                       | Reviewers verify spans before approval.                                            |
| Provider flags category Guardian tiers missed         | Any                   | WARN (`PROVIDER_CRITICAL_HINT`)    | Normal flow                                   | Advisory only; also files detector gap ticket.                                     |
| Parent artifact not cleared                           | Enforce parent gating | BLOCK (`PARENT_NOT_APPROVED`)      | `QUARANTINED`                                 | Deterministic parent locking prevents stale approvals.                             |

Guardian respects downstream approval invariants (ExclusiveSwap) and ensures deliverables only advance from `APPROVED` onward once Guardian history marks the latest edit as cleared.

### 2.3 Waiver & quarantine policies

- Waivers require dual approval (Security + Architecture) and manifest stamping (`guardian.manifest.waiver_id`).
- Quarantined artifacts block dependent artifacts (for example, timeline events referencing a quarantined transcript).
- HIPAA/SPI triggers escalate to Security and enable enhanced review requirements (`spi_review_required=true`).
- Org settings `org.guardian.pre_operator_gates[]` enumerate artifact classes (typically `SA`, `WP`, `CD`) that remain hidden from operators until Guardian returns PASS/WARN. Reviewer-triggered quarantines route through Guardian so the canonical log records `quarantined_by`, `quarantine_reason`, and waiver metadata.

______________________________________________________________________

## 3) API contract (binding)

**Purpose:** Describe every programmatic surface (REST, queue, events) Guardian exposes so integrators implement consistent safety gates.\
**Contract:** Guardian accepts submissions via idempotent queue APIs, serves read endpoints with RLS enforcement, and emits deterministic SSE/audit events. Schemas, reason codes, and idempotency keys remain stable across releases; any breaking change requires a new versioned path.\
**State:** Submissions carry policy-context digests, artifact hashes, and source metadata; judgments persist manifests and span evidence; SSE streams broadcast the final outcome with pointers back to stored history.\
**Failure modes & handling:** Queue timeouts, schema validation errors, and policy drift raise explicit error codes (`GUARDIAN_SUBMISSION_TIMEOUT`, `SCHEMA_POLICY_BLOCK`, `POLICY_FORBIDDEN_PATTERN`) and surface remediation guidance in §5 and Appendix R.\
**Observability:** Interfaces emit metrics (`guardian_enqueue_conflict_total`, `guardian_judgment_latency_seconds`), structured JSONL audits, and SSE counts; synthetic jobs exercise these paths continuously.\
**References:** §4 State management, §5 Failure modes, Appendix C (payload schema), TDD §7.4, ADR-0001.\
**Breadcrumbs:** Implementation `apps/platform/operations/guardian.py`, `packages/udocket_core/guardian/api.py`, `packages/udocket_core/guardian/queue.py`; Tests `tests/platform/guardian/test_guardian_api.py`, `tests/platform/guardian/test_guardian_queue.py`.

### 3.1 External interfaces (binding)

| Endpoint / Stream                  | Purpose                                    | Contract notes                                                                                                  |
| ---------------------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| `GET /readyz`                      | Liveness/readiness                         | No auth required inside cluster; used by HPA and incident playbooks.                                            |
| `GET /synthetic/status`            | Synthetic probing                          | Exercises read/write health after deployments (`guardian_slo.yaml`).                                            |
| `GET /api/v1/guardian/<id>`        | Retrieve judgment + manifest               | Requires service-to-service mTLS + RLS; returns deterministic manifest snapshot identifiers.                    |
| `GET /api/v1/guardian?artifact_id=`| List latest judgment                       | Same auth as above; pagination deterministic on `decided_at`.                                                    |
| `POST /api/v1/guardian/quarantine` | Manual quarantine/unquarantine             | Validates parent-child integrity and records reviewer metadata.                                                 |
| `POST /guardian/detect-and-mask`   | Span detection + masking                   | Returns `{detected_entities[], masked_spans[], provider_flags[], judgment}` with UUIDv7 span IDs.               |
| `GET /guardian/policy`             | Retrieve effective policy bundle metadata  | Surfaces `{policy_bundle_id, masking_defaults[], restoration_intents[]}` for UI/workers.                        |
| `POST /guardian/judgments:enqueue` | Administrative replay (internal tooling)   | Idempotent on `{resource_urn, reason}`; reuses submission bus; audited under `ops/guardian/batch_submit.jsonl`. |
| `POST /vault/detokenize`           | Restore masked spans (Compose/Signer only) | Requires `guardian_judgment_id`, purpose, and mTLS; Guardian never logs plaintext.                              |
| `SSE GUARDIAN.JUDGMENT.*`          | Broadcast PASS/WARN/BLOCK/WAIVED outcomes  | Carries `guardian_judgment_id`, reason codes, waiver IDs, `settings_snapshot_sha256`, span evidence hashes.     |

### 3.2 Submission interfaces (binding)

- Internal workers call `apps/platform/operations/guardian.py::enqueue_with_idempotency` with `artifact_id`, `artifact_class`, `payload_sha256`, `policy_context`, and `source_artifacts[]`.
- Idempotency key: `sha256(case_id + artifact_id + payload_sha256 + policy_context_hash)`; collisions return the prior judgment and increment `guardian_enqueue_conflict_total`.
- Queue timeout: 300 seconds (`guardian.queue.submission_timeout_seconds`). Workers emit `GUARDIAN_SUBMISSION_TIMEOUT` when exceeded and retry per Celery policy; sustained failures trigger §5.1 backlog mitigation.
- Submissions must use HMAC-authenticated service tokens; Guardian records request metadata in `ops/guardian/batch_submit.jsonl` and Postgres `guardian_submission_audit`.
- Replay tooling (`POST /guardian/judgments:enqueue`) shares the same queue path to guarantee identical side effects and audit history.

### 3.3 Evaluation pipeline (normative)

1. Validate schema and policy context, rejecting malformed payloads with `SCHEMA_POLICY_BLOCK`.
2. Execute residency, HIPAA, forbidden-pattern, and waiver checks against LPE/OPA bundles.
3. Run content classifiers (Azure Content Safety PHI, in-house transformer, deterministic regex heuristics).
4. Fuse detector results through a deterministic decision tree; PASS/WARN attach operator banners, BLOCK escalates reason codes (for example, `POLICY_FORBIDDEN_PATTERN`, `INTEGRITY_HASH_MISMATCH`).
5. Persist manifests, span evidence, and policy context digests; emit SSE/audit events for workflow, portal, and analytics consumers.

Guardian enforces parent-child integrity by locking upstream artifacts (`SELECT ... FOR SHARE`). If a parent demotes mid-flight, the child returns `BLOCK (PARENT_NOT_APPROVED)`. Judgments are idempotent per `{artifact_id, content_sha256}`—replays with the same hash reuse the prior verdict while new hashes create fresh history rows.

#### 3.3.1 Detection tiers (binding)

1. **Tier-0 — schema & field guards:** Validates known slots (`dob`, `mrn`, `ssn`, etc.) and emits `SCHEMA_POLICY_BLOCK` (`INVALID_FIELD_FORMAT`) when data fails canonical formatting.
2. **Tier-1 — pattern + checksum:** Jurisdiction-specific regex packs and checksum validators (Luhn, Verhoeff, ABA routing, ICD/HCPCS/CPT shape, Rx BIN/PCN length) emit `PATTERN_MATCH` evidence.
3. **Tier-2 — ML/NLP detectors:** Locale-scoped NER models sourced from LPE contribute spans with model IDs and confidence; sub-threshold spans log telemetry for drift analysis.
4. **Tier-3 — contextual verifier:** A constrained LLM re-scores contentious spans (`{"confirm": true|false, "confidence": float}`) and applies reason `CONTEXTUAL_VERIFIER`.
5. **Normalization & fusion:** Overlapping spans merge deterministically (higher confidence, stricter policy). Provenance retains contributing tiers/detectors.
6. **Masking & tokenization:** Applies masking profiles to a working copy, references vault namespace, and records whether spans are restorable before judgment.
7. **Guardian judgment:** Aggregates detections, policy context, provider telemetry, and waiver state to emit PASS/WARN/BLOCK/WAIVED with reason codes such as `HIPAA_REQUIRED`, `PII_DETECTED`, `SPI_DETECTED`, `DLP_VIOLATION`, `CLASSIFIER_LOW_CONFIDENCE`, and `PARENT_NOT_APPROVED`.

### 3.4 Review integration & audit writes (binding)

- Reviewer actions (`approve`, `changes`, `quarantine`, `waive`) route through Guardian endpoints (`/guardian/quarantine`, `/guardian/review-actions`, `/guardian/judgments:enqueue`) so the service remains the canonical history authority.
- Guardian writes every decision to `guardian_judgment_history` with deterministic UUIDv7 IDs, preserving prior verdicts even when artifacts re-enter `PENDING_JUDGMENT`. Replays with matching `{artifact_id, content_sha256}` reuse the latest record; new hashes create append-only entries.
- Manual and automated decisions both emit SSE/audit events (`GUARDIAN.JUDGMENT.*`) containing the identifiers workflow services use for manifests, approval UIs, and downstream response guides.
- Reviewer console integrations include structured comments and span references; Guardian verifies the submitted `expected_version` matches the manifest before accepting the action.
- Read-only helpers (`GET /api/v1/guardian/<id>`, `GET /api/v1/guardian?artifact_id=`) are guarded by RLS so analytics surfaces rely on the secured projections instead of direct table access.

### 3.5 Detection & masking payloads (binding)

- Guardian records span-level evidence and masking metadata using deterministic UUIDv7 identifiers so reruns reconcile reliably.
- Payloads always link to `policy_context_digest`, masking profiles, and vault namespaces so Compose/Signer can restore spans when policy allows (`POST /vault/detokenize`).
- Canonical field definitions, validation rules, and the reference JSON example live in Appendix C (binding); clients must validate against that schema before submitting detection feedback.
- Provider telemetry (speech/LLM safety APIs) lands in `guardian_provider_flags[]`; severe categories Guardian missed elevate the outcome to WARN (`PROVIDER_CRITICAL_HINT`) and auto-file detector gap tickets.

______________________________________________________________________

## 4) State management (binding)

**Purpose:** Describe the stores, queues, and configuration sources Guardian owns so persistence, reconciliation, and policy enforcement stay deterministic.\
**Contract:** Guardian maintains append-only judgment history, span evidence, and submission audit trails in Postgres; queue state mirrors the persisted records, and all configuration enters via Settings/LPE snapshots. Direct database edits or ad-hoc queue injections are prohibited.\
**State:** Postgres tables (`guardian_judgment_history`, `guardian_span_detection`, `guardian_submission_audit`), Kafka/Azure Service Bus queues, OPA policy bundles, and case-scoped ops artifacts.\
**Failure modes & handling:** Partition rotation failures, queue desynchronization, or stale policy contexts trigger mitigations in §5 and Appendix R. Reconciliation scripts (`ops/db/rotate_partitions.py`, `ops/scripts/guardian/reconcile_manual.py`) repair discrepancies.\
**Observability:** Metrics (`guardian_pending_total`, `guardian_pending_oldest_seconds`, `guardian_policy_block_total`), audit JSONL streams, and hash comparisons between Settings snapshots and Guardian manifests validate state.\
**References:** §3 API contract, §5 Failure modes, Appendix C (payload schema), Appendix R (runbooks), ADR-0001, ADR-0004.\
**Breadcrumbs:** Persistence code `packages/udocket_core/guardian/store.py`, Queue integration `packages/udocket_core/guardian/queue.py`, Config ingestion `packages/udocket_core/guardian/config.py`, Ops scripts under `ops/scripts/guardian/`.

### 4.1 Persistence model

- `guardian_judgment_history` partitions monthly on `decided_at`; rotation job `ops/db/rotate_partitions.py` creates future partitions and seals retired ones.
- Row-level security policy `guardian_history_vis` enforces org isolation. Application roles read from secure projections (`guardian_judgment_history_secure`, `guardian_judgment`) while service accounts maintain base-table permissions.
- Span evidence resides in `guardian_span_detection` with deterministic UUIDv7 identifiers tied to manifest digests and masking profiles.
- Submission metadata (`guardian_submission_audit`) captures worker identity, payload hashes, policy digests, and queue offsets so operators can reconcile message position with persisted history.
- Human-readable logs mirror structured entries under `storage/media/cases/<case>/ops/guardian/<job_id>__guardian.log` for audit parity.

### 4.2 Policy context & configuration

- `PolicyContext` inputs describe residency, HIPAA, SPI, waiver flags, allowed regions (`regions.allowlist.compute|storage|vector`), retention policies, and forbidden pattern catalogs; Guardian rejects submissions when digests diverge from Settings/LPE snapshots.
- Configuration keys sourced from Settings include:
  - `guardian.queue.backlog_alert_minutes` (default 5).
  - `guardian.queue.submission_timeout_seconds` (default 300).
  - `guardian.judgment_slo_ms` (default 300000); overrides require Architecture/Security approval.
  - `guardian.rules.version` — active policy bundle digest.
  - `privacy.hipaa.enabled`, `privacy.hipaa.phi_detection.strict_mode`, `privacy.hipaa.phi_detection.rescan_hours`.
  - `privacy.spi.retention_days`, `privacy.spi.residency`.
  - `compose.policy.forbidden_patterns[]` used during deliverable checks.
  - `org.guardian.pre_operator_gates[]` to hide artifacts until Guardian returns PASS/WARN.
  - `review.mode` / `review.approval_type.default` to respect reviewer skip modes.
- Residency enforcement rejects submissions outside org allowlists and emits `RESIDENCY_POLICY_BLOCK` audit events; waivers travel through App.O flows with manifest stamping.
- HIPAA mode enforces WebAuthn, PHI quarantine, and evidence redaction; Guardian blocks PHI artifacts until HIPAA toggles confirm enablement.
- System bundle `config/guardian_defaults.json` seeds defaults during environment bootstrap; `agents.pipeline.definitions[]` enumerates pipelines Guardian expects to evaluate (`transcription`, `analyze`, `compose`, assistants, etc.).

### 4.3 Queue and cache state

- Production uses Kafka for `guardian_submission_queue`; regulated tenants use Azure Service Bus with matching semantics. Producers include artifact workers and replay tooling; consumers are Guardian evaluators.
- Queue offsets and digests mirror `guardian_submission_audit`; reconciliation compares Kafka offsets with audit rows to detect dropped or duplicated messages.
- Materialized views expose live queue depth/age to Grafana (`guardian_pending_total`, `guardian_pending_oldest_seconds`).
- Cached policy bundles live in OPA sidecars; Guardian tracks the active digest (`guardian.rules.version`) and refresh timestamps to ensure evaluators use the expected rule set.

### 4.4 Artifacts, logs, and retention

- Case-scoped ops directories persist JSON metadata and audit JSONL (`storage/media/cases/<case>/ops/guardian/`), following the deterministic naming convention `<job_id>__guardian_log.json`.
- Retention: Guardian keeps span evidence, manifests, and audit logs ≥ 365 days to satisfy HIPAA/PHIPA obligations; manual review records persist until incident closure sign-off.
- OPA decision logs stream to immutable storage with matching `guardian_judgment_id` references so auditors can compare inline evaluations with stored manifests.

______________________________________________________________________

## 5) Failure modes (binding)

**Purpose:** Capture the primary ways Guardian can degrade and the contractual responses required to preserve artifact integrity and compliance.\
**Contract:** Guardian must fail closed on policy violations, residency breaches, and detector uncertainty; backlog or dependency failures trigger the operational playbooks in Appendix R before artifacts progress. Manual overrides require dual approval and explicit manifest stamping.\
**State:** Failure conditions are recorded in `guardian_judgment_history` (`status=BLOCK`, reason codes), queue metrics, and incident JSONL under `ops/guardian/incidents/`.\
**Failure modes & handling:** Submission backlog, detector drift, and dependency outages each have defined guardrails and runbooks summarized below.\
**Observability:** Alerts on `guardian_pending_oldest_seconds`, `guardian_policy_block_total`, `guardian_quarantine_false_positive_total`, synthetic job failures, and detector drift feed PagerDuty rotations.\
**References:** Appendix R (RB-GUARD-001/QUAR/QUEUE/MANUAL), §3.3 Detection tiers, §7 Operational readiness, TDD §7.5.\
**Breadcrumbs:** Incident automation `ops/scripts/guardian/*.py`, Grafana dashboards “Guardian SLO” and “Guardian Manual Review”, Tests `tests/platform/guardian/test_failure_modes.py`.

### 5.1 Submission backlog or queue saturation

- Trigger: `guardian_pending_oldest_seconds` exceeds `guardian.queue.backlog_alert_minutes` or `guardian_submission_timeout_total` trends upward.
- Response: Follow Appendix R entry RB-GUARD-QUEUE—throttle enqueue rates, scale evaluator pods, verify Kafka/Service Bus health, and replay stuck messages via `POST /guardian/judgments:enqueue`.
- Guarantee: Artifacts remain `PENDING_JUDGMENT` until backlog clears; manual review is disallowed unless RB-GUARD-001 escalates and dual approval authorizes manual mode.

### 5.2 Detector regression or policy drift

- Trigger: Spike in WARN/BLOCK reason codes (`PROVIDER_CRITICAL_HINT`, `CLASSIFIER_LOW_CONFIDENCE`), synthetic job failures, or `guardian_quarantine_false_positive_total` > 5 %.
- Response: Appendix R entry RB-GUARD-QUAR and RB-GUARD-001—freeze bundle activations, roll back `guardian.rules.version` if needed, and coordinate with LPE/Settings to validate PolicyContext digests.
- Guarantee: Deliverables stay quarantined until detectors are revalidated; waivers require manifest stamping and Security/Architecture approval.

### 5.3 Dependency outage or configuration mismatch

- Trigger: OPA sidecar signature verification failure, Settings snapshot hash mismatch, or upstream service outage (LPE, Settings, Reference Manager).
- Response: Appendix R entry RB-GUARD-001—shift to manual review mode only if on-call declares it, capture manifests under `ops/guardian/manual_review/<date>.jsonl`, and reconcile once dependencies recover.
- Guarantee: Guardian blocks artifacts (`BLOCK (DEPENDENCY_UNAVAILABLE)`) rather than allowing progression with stale policy; manual reconciliation records are replayed and audited post-incident.

______________________________________________________________________

## 6) Observability & SLOs (binding)

**Purpose:** Define the telemetry, dashboards, and synthetic coverage that prove Guardian is meeting its safety and latency commitments.\
**Contract:** Metrics, logs, and synthetic probes listed here are mandatory; removing any signal requires Observability + Security approval and equivalent replacement. SLOs are 99.9 % availability with judgment P95 ≤ 5 minutes.\
**State:** Metrics publish via Prometheus (`guardian_*` series), logs/audits persist in Postgres and case ops directories, and synthetic jobs emit structured results to `guardian_slo.yaml` artifacts.\
**Failure modes & handling:** Breaches escalate through Appendix R runbooks (RB-GUARD-001/QUEUE/QUAR) and drive the failure responses in §5.\
**Observability:** Grafana dashboards “Guardian SLO”, “Guardian Manual Review”, log aggregation views, and audit JSONL provide responders with context.\
**References:** §5 Failure modes, §7 Operational readiness, Appendix R (runbooks), Appendix C (payload schema).\
**Breadcrumbs:** Dashboards under `infra/grafana/guardian_*.json`, synthetic job definitions `ops/synthetics/guardian_slo.yaml`, log pipeline config `infra/logging/guardian.json`.

### 6.1 Metrics

| Metric                                                       | Description                                                                         |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| `guardian_judgment_latency_seconds`                          | Distribution of evaluation latency; SLO ≤ 5 minutes P95.                            |
| `guardian_cleared_ratio`                                     | Ratio of PASS/WARN/WAIVED to total judgments.                                       |
| `guardian_pending_total`                                     | Queue depth derived from `guardian_submission_queue`.                               |
| `guardian_pending_oldest_seconds`                            | Age of oldest pending submission; alerts at `guardian.queue.backlog_alert_minutes`. |
| `guardian_submission_timeout_total`                          | Worker watchdog count when Guardian exceeds `submission_timeout_seconds`.           |
| `guardian_enqueue_conflict_total`                            | Idempotency conflict counter.                                                       |
| `guardian_policy_block_total`                                | BLOCK outcomes by reason code.                                                      |
| `guardian_parent_block_total`                                | Child artifacts blocked due to parent quarantine.                                   |
| `guardian_quarantine_false_positive_total`                   | Recovered quarantines with same hash; governance tracks ≤ 5 % objective.            |
| `review_queue_backlog_total` / `review_queue_oldest_seconds` | Downstream readiness; alerts coordinate with Guardian backlog.                      |

### 6.2 Logs & audits

- Append-only JSONL audit stream with `guardian_judgment`, `policy_context_digest`, `settings_snapshot_sha256`, waiver IDs, reason codes, and classifier evidence hashes.
- Storage layout:
  - Base table `guardian_judgment_history` partitions monthly on `decided_at`; rotation job `ops/db/rotate_partitions.py` creates partitions one month ahead and seals retired ones.
  - RLS policy `guardian_history_vis` enforces deny-by-default access via `udocket_can('GUARDIAN_HISTORY', ...)` and requires active org/case context.
  - Secure views `guardian_judgment_history_secure` and `guardian_judgment` (latest-per-artifact) are the only read surfaces granted to application roles; base table access remains service-only.
  - Grant revocations: `REVOKE SELECT ON guardian_judgment_history FROM udocket_app; GRANT SELECT ON guardian_judgment_history_secure TO udocket_app;` ensure UI/API code consumes the secured projections.
- Manual review artifacts (`MANUAL_GUARDIAN_JUDGMENT`) and reconciliation runs append to the same history table with `source="manual"` metadata so auditors can differentiate human vs. automated outcomes.
- Human-readable ops log per judgment stored alongside artifact ops directory.
- Decision logs from OPA streamed to immutable storage (≥365 days retention).

### 6.3 Synthetic monitoring

- Synthetic job `guardian_slo.yaml` submits representative workloads (500 concurrent submissions, 5k/day) and records judgment/queue timing; success requires P95 latency ≤ configured SLO and zero submission timeouts.
- Synthetic GET requests verify `/readyz` and `/synthetic/status` per environment after deployments; failures open PagerDuty incidents tagged `GUARDIAN_SLO`.
- Synthetic coverage exercises HIPAA, SPI, and residency scenarios to validate policy gating; drift triggers `PHI_DETECTION_DRIFT` follow-up.
- Failure of synthetic job triggers RB-GUARD-001 incident response.

______________________________________________________________________

## 7) Security & compliance (binding)

**Purpose:** Capture Guardian’s security posture, residency guarantees, and regulatory obligations so downstream services rely on accurate enforcement boundaries.\
**Contract:** Guardian must enforce residency and HIPAA/SPI policies exactly as configured, reject unsigned or stale policy bundles, and preserve tamper-evident audit trails. Dual approval is mandatory for waivers or manual overrides.\
**State:** Security posture derives from policy bundles (`guardian.rules.version`), Settings toggles, HSM-managed signing keys, and audit records in `guardian_judgment_history`/`guardian_span_detection`.\
**Failure modes & handling:** Residency mismatches, key compromise, or PHI exposure follow Appendix R escalation paths and the LPE/Guardian incident playbooks.\
**Observability:** Security dashboards track residency enforcement (`guardian_residency_block_total`), HIPAA-specific metrics, and audit signature validation; cosign/verifier jobs confirm container provenance.\
**References:** §4 State management, §5 Failure modes, Appendix R, ADR-0004 (LPE), TDD §5 (Security).\
**Breadcrumbs:** IAM policies `infra/iam/guardian/`, HSM integration `packages/udocket_core/guardian/crypto.py`, residency policy bundles `packages/udocket_core/lpe/bundles/`, compliance tests `tests/platform/guardian/test_security.py`.

- **Residency controls:** Guardian enforces org allowlists, rejects submissions outside permitted compute/storage/vector regions, and emits `RESIDENCY_POLICY_BLOCK` events tied to manifest IDs. Waivers require dual approval and manifest stamping (`RESIDENCY_WAIVER_USED`) before artifacts progress.
- **HIPAA/SPI safeguards:** SPI inherits HIPAA-grade protections. Guardian quarantines PHI artifacts when HIPAA mode is disabled, enforces dual-review for SPI deliverables, and records accesses in `SPI_ACCESS_EVENT` audit trails.
- **Policy integrity:** Guardian only loads signed bundles validated by Managed HSM keys (dual Ed25519 + ECDSA when `security.tls.fips_mode=true`). Bundle rollouts track digests and expiry; stale bundles block evaluations.
- **Tamper resistance:** Judgment history, span evidence, and OPA decision logs are append-only. Images are signed via cosign, and CI policy gates verify provenance before deployment.
- **Data minimization:** Guardian scrubs plaintext spans from logs, stores masked variants in ops directories, and routes detokenization through mTLS-protected `POST /vault/detokenize` with purpose binding.

______________________________________________________________________

## 8) Operational notes (binding)

**Purpose:** Summarize Guardian’s on-call posture, deployment practices, and response coordination so operators can keep the safety gate available.\
**Contract:** Operational procedures, incident triggers, and manual review steps must stay in sync with Appendix R. Any change to runbooks, alert thresholds, or response ownership requires updating this section and the appendices simultaneously.\
**State:** Rotation calendars, deployment manifests, and incident records live in `ops/guardian/` alongside the runbooks referenced below.\
**Failure modes & handling:** Operational responses map directly to §5 (Failure modes) and Appendix R (RB-GUARD-001/QUEUE/QUAR/MANUAL).\
**Observability:** Operators rely on Grafana dashboards from §6, alertmanager routes, and audit JSONL streams in `storage/media/cases/<case>/ops/guardian/`.\
**References:** §5 Failure modes, Appendix R, `infra/kubernetes/guardian/`, `ops/runbooks/guardian/`.\
**Breadcrumbs:** Helm charts `infra/kubernetes/guardian/helm`, Terraform modules `infra/terraform/guardian`, runbooks `ops/runbooks/guardian/*.md`, deployment scripts `ops/scripts/guardian/deploy.py`.

- Response IDs RB-GUARD-001 (SLO breach), RB-GUARD-QUAR (quarantine spike), and RB-GUARD-QUEUE (submission backlog) are maintained in Appendix R (binding). Step-by-step triage and decision trees live there to keep the main flow concise.
- Manual review checklists live in Appendix R entry RB-GUARD-MANUAL; responders reference them alongside this specification.

### 8.1 Operational posture

- Guardian on-call rotations monitor `guardian_judgment_latency_seconds`, `guardian_pending_total`, and `guardian_policy_block_total` to confirm the 99.9% availability / ≤ 5 minute P95 latency commitments.
- Queue submission health depends on Celery worker heartbeats and Settings/LPE dependencies; Appendix R entry RB-GUARD-QUEUE describes how to remediate backlog growth while preserving auditability.
- Quarantine volume and waiver approvals follow Appendix R entry RB-GUARD-QUAR, keeping manifests and waiver artifacts in lockstep with Security/Architecture approvals.

### 8.2 Incident triggers

- `alert_guardian_queue_stale` (Grafana) fires when backlog age exceeds `guardian.queue.backlog_alert_minutes`; responders follow Appendix R entry RB-GUARD-QUEUE.
- `guardian_policy_block_total` spikes or synthetic job failures (`guardian_slo.yaml`) escalate via Appendix R entries RB-GUARD-001 and RB-GUARD-QUAR, depending on whether latency or policy regression drives the alert.
- `PHI_DETECTION_DRIFT` incidents originate from classifier sampling (§6.3); Appendix R entry RB-GUARD-QUAR covers containment and follow-up requirements.

### 8.3 Manual review mode

- When Guardian automation is paused, operations invoke Appendix R entry RB-GUARD-001 to route artifacts through manual review queues and capture `MANUAL_GUARDIAN_JUDGMENT` records.
- Reconciliation jobs replay queued artifacts once health recovers; responders document the waiver/incident outcomes according to Appendix R entry RB-GUARD-001 post-remediation notes.

______________________________________________________________________

## 9) Dependencies (informative)

**Purpose:** Map Guardian’s upstream and downstream relationships so teams understand how policy changes cascade across the platform.\
**Contract:** Guardian depends on LPE, Settings, Reference Manager, and queue infrastructure meeting their SLAs; downstream services must honor Guardian judgments before mutating artifact state. Dependencies are versioned—breaking changes require joint rollout plans and updated references here.\
**State:** Integration contracts live in this spec, corresponding ADRs, and shared schema fixtures (`packages/udocket_core/guardian/contracts/`).\
**Failure modes & handling:** Dependency outages feed §5.3 responses; misaligned versions trigger Appendix R coordination.\
**Observability:** Cross-service dashboards track latency/error budgets, and shared alerts notify both owners when thresholds breach.\
**References:** ADR-0001 (Guardian/Ready-Quarantine), ADR-0003 (API versioning), ADR-0004 (LPE), §3 API contract, §4 State management.\
**Breadcrumbs:** Integration code `packages/udocket_core/guardian/integration/`, queue adapters `packages/udocket_core/guardian/queue.py`, Celery orchestration `apps/platform/operations/guardian.py`.

- **Localization & Policy Engine (upstream):** Supplies signed policy bundles, residency baselines, and detector configurations. Guardian blocks evaluations when digests diverge or signatures fail.
- **Settings service (upstream):** Provides organization toggles (`guardian.rules.version`, HIPAA, SPI). Settings activations trigger Guardian dry-runs; failures roll back activation.
- **Reference Manager (upstream):** Publishes jurisdiction catalogs and court metadata; Guardian updates policy context digests during catalog revisions.
- **Workers & Celery pipelines (downstream):** Submit artifacts to Guardian and respect PASS/WARN/BLOCK before promoting statuses. Backlog handling relies on Appendix R RB-GUARD-QUEUE routines.
- **Portal, Compose, and Notifications (downstream):** Condition UI visibility and deliverables on Guardian verdicts; WARN injects banners, BLOCK halts customer presentation.
- **Signer (downstream):** Applies signatures only when Guardian manifests show PASS/WAIVED; certificates embed `guardian_judgment_id` for audit.
- **Queue fabric (shared):** Kafka/Service Bus notifies Guardian evaluators; offsets align with submission audit tables to ensure replay accuracy.

______________________________________________________________________

## 10) References (informative)

**Purpose:** Provide a curated list of authoritative materials referenced throughout this specification for quick lookup during reviews and incidents.\
**Contract:** Keep this list current when adding/removing dependencies, ADRs, diagrams, or runbooks; PRs modifying Guardian behavior must update references and link to diff context.\
**State:** Links point to immutable ADRs, diagrams, runbooks, and glossary entries maintained elsewhere in the repo.\
**Failure modes & handling:** Missing/obsolete references cause docs lint to fail (`scripts/docs/lint_docs.py`); owners must refresh the list before merging.\
**Observability:** Docs CI validates reference existence and cross-link formatting.\
**References:** ADR index `docs/adr/README.md`, Glossary `docs/src/overview/tdd/appendices/glossary.md`, Appendix R (this file).\
**Breadcrumbs:** `scripts/docs/lint_docs.py`, `scripts/docs/link_check.py`, MkDocs config `docs/mkdocs.yml`.

- **ADRs:** ADR-0001 Guardian Ready/Quarantine, ADR-0003 API Versioning & Sunset, ADR-0004 Localization & Policy Engine, ADR-0005 OPA Policy Plane.
- **TDD sections:** TDD §5 Security Architecture, TDD §7 Guardian Integration, TDD Appendix H Operational Guides.
- **Runbooks:** Appendix R entries RB-GUARD-001/QUEUE/QUAR/MANUAL plus supporting files in `ops/runbooks/guardian/`.
- **Diagrams:** `docs/src/services/guardian/diagrams/upload-guardian-approve-v1.mmd`, `docs/src/overview/tdd/diagrams/data-lineage-v1.mmd`, `docs/src/services/lp-engine/diagrams/residency-policy-enforcement-v1.mmd`.
- **Schemas & fixtures:** Appendix C, `packages/udocket_core/guardian/contracts/payloads.py`, sample manifests in `docs/examples/lineage/`.
- **Change protocol:** PRs touching Guardian code/policy must link to this section, run `python scripts/docs/lint_docs.py`, and obtain Architecture + Security approval before deploy.

______________________________________________________________________

## Appendix A — Reference artifacts (informative)

- **Diagrams:**
- `services/guardian/diagrams/upload-guardian-approve-v1.mmd` (sequence of upload → Guardian → approval).
- `services/lp-engine/diagrams/residency-policy-enforcement-v1.mmd` (policy propagation and Guardian enforcement).
- `overview/tdd/diagrams/data-lineage-v1.mmd` (artifact lineage through Guardian and Signer).
- **Examples:**
  - `docs/examples/lineage/transcript_to_compose.json` demonstrating manifest linkage with Guardian judgment IDs.
  - `docs/examples/lineage/compose_client.json` showing deliverable provenance.

This specification is the canonical source for Guardian behavior. Sections in the broader TDD now link here; future updates MUST originate here and propagate outward.

______________________________________________________________________

## Appendix R — Runbooks & drills (binding)

**Breadcrumbs:** Implementation `ops/runbooks/guardian/`, Tests `tests/ops/test_runbook_integrity.py::test_guardian_runbooks`, Observability PagerDuty service “Guardian SLO” with Grafana dashboard “Guardian SLO”.\\ *Purpose: Maintain actionable Guardian recovery guides and manual review playbooks.*\\ *Contract: Alerts enumerated in §7 map to RB-GUARD identifiers here; responders update these procedures after every incident or drill.*\\ *State: Procedures live beside automation scripts in `ops/runbooks/guardian/`; this appendix summarizes triggers, decision trees, and evidence requirements.*\\ *Failure modes & retries: Missing or stale procedures trigger corrective actions and block deploy sign-off.*\\ *Observability: Incident retros attach the executed RB-GUARD identifier and confirm Appendix R coverage during quarterly reviews.*

### R.1 Response index (informative)

- RB-GUARD-001 — Guardian SLO breach stabilization.
- RB-GUARD-QUAR — Quarantine spike investigation.
- RB-GUARD-QUEUE — Submission backlog watchdog.
- RB-GUARD-MANUAL — Manual review reconciliation.

### R.2 RB-GUARD-001 — Guardian SLO breach (binding)

**Breadcrumbs:** Implementation `ops/runbooks/guardian/slo_breach.md`, Automation `ops/scripts/guardian/scale_guardian.py`, Tests `tests/ops/test_runbook_integrity.py::test_guardian_slo_runbook`, Observability Grafana dashboard “Guardian SLO” (alerts `guardian_judgment_latency_seconds`, `guardian_submission_timeout_total`).\\ *Purpose: Restore Guardian availability and route artifacts through manual review when automated judgments breach SLO.*\\ *Contract: Any breach of the availability or latency SLO uses this sequence before re-enabling automated progression.*\\ *State: Manual review ledger entries persist under `ops/guardian/manual_review/<date>.jsonl`.*\\ *Failure modes & retries: Skipping manual review tracking risks losing audit history and invalidating waivers.*\\ *Observability: Alert clears after two healthy scrapes and manual review backlog drains.*

- **Signals:** `guardian_judgment_latency_seconds` P95 > SLO, `guardian_submission_timeout_total` increasing, synthetic job failure (`guardian_slo.yaml`).
- **Triage (≤5 minutes):**
  1. Check `/readyz` and `/synthetic/status`; capture latency panels in Grafana (“Guardian SLO”).
  2. Confirm queue depth (`guardian_pending_total`, `guardian_pending_oldest_seconds`) and worker health (Celery heartbeat, pod restarts).
  3. Inspect recent deploys/settings (`guardian.rules.version`, Helm releases) for regressions.
- **Decision tree:**
  - *Service unhealthy*: place Guardian in manual review mode (pause submissions, notify ops). Operators record `MANUAL_GUARDIAN_JUDGMENT` artifacts while following this checklist.
  - *Compute exhaustion*: scale deployment (`kubectl -n platform scale deploy/guardian --replicas=<n>`), update HPA floor post-incident.
  - *Upstream dependency slowdown*: coordinate with LPE/Settings owners; consider throttling new submissions until latency stabilizes.
- **Post-remediation:**
  - Ensure `guardian_judgment_latency_seconds` P95 ≤ SLO for 2 consecutive scrapes and `guardian_submission_timeout_total` plateaued.
  - Clear manual review backlog by replaying queued artifacts once service healthy; annotate incident log with root cause and follow-ups.

### R.3 RB-GUARD-QUAR — Quarantine spike investigation (binding)

**Breadcrumbs:** Implementation `ops/runbooks/guardian/quarantine_spike.md`, Automation `ops/scripts/guardian/replay_quarantine.py`, Tests `tests/ops/test_runbook_integrity.py::test_guardian_quarantine_runbook`, Observability Grafana dashboard “Guardian Enforcement” (alert `alert_guardian_quarantine_spike`).\\ *Purpose: Diagnose QUARANTINED spikes without bypassing policy controls.*\\ *Contract: Any surge in quarantine outcomes requires this investigation before promoting new releases or waivers.*\\ *State: Findings logged under `ops/guardian/quarantine/<incident_id>.md` with root-cause summary and evidence attachments.*\\ *Failure modes & retries: Missing waiver documentation or misaligned settings snapshots risk repeat incidents.*\\ *Observability: Alert resolves when `guardian_cleared_ratio` recovers and reason-code distribution returns to baseline.*

- **Signals:** Increased `guardian_policy_block_total{reason=...}` (e.g., `POLICY_FORBIDDEN_PATTERN`, `INTEGRITY_HASH_MISMATCH`, `SOURCE_NOT_APPROVED`); drop in `OPERATOR_PREP`/`QUEUED_FOR_REVIEW` backlog throughput.
- **Triage:**
  1. Filter Guardian dashboard by `reason_codes[]` and `org_id` to locate affected cohorts.
  2. Sample judgments from `guardian_judgment_history_secure`; confirm `guardian.rules.version` and `settings_snapshot_sha256` alignment.
  3. For `INTEGRITY_HASH_MISMATCH`, verify upload finalize and recompute hashes; for `SOURCE_NOT_APPROVED`, ensure upstream artifacts cleared.
- **Decision:**
  - `POLICY_FORBIDDEN_PATTERN`: engage Product/QA; adjust templates or policies; consider waiver only with dual approval.
  - `SOURCE_NOT_APPROVED`: instruct operators to remediate upstream artifacts or rebind inputs; Guardian enforces parent gating.
  - Region/debug issues: enforce settings fix, resubmit, and confirm waiver stamping (`RESIDENCY_WAIVER_USED`) where applicable.
- **Post-remediation:** Track `guardian_cleared_ratio` recovery, log incident with counts per reason, and file rule-tuning tasks if false positives exceed thresholds.

### R.4 RB-GUARD-QUEUE — Submission backlog watchdog (binding)

**Breadcrumbs:** Implementation `ops/runbooks/guardian/submission_backlog.md`, Automation `ops/scripts/guardian/queue_drain.py`, Tests `tests/ops/test_runbook_integrity.py::test_guardian_queue_runbook`, Observability Grafana dashboard “Guardian Queue Health” (alert `alert_guardian_queue_stale`).\\ *Purpose: Restore submission throughput before `PENDING_JUDGMENT` artifacts stall.*\\ *Contract: Any backlog alert follows this playbook before artifacts are promoted or waived.*\\ *State: Queue samples exported to `ops/guardian/queue_samples/<timestamp>.csv` for audit.*\\ *Failure modes & retries: Failing to drain backlog before resuming automation risks out-of-order judgments.*\\ *Observability: Alert resolves when backlog age drops below threshold and throughput returns to baseline.*

- **Signals:** `guardian_pending_total` trending upward for 3 scrapes, `guardian_pending_oldest_seconds` > `guardian.queue.backlog_alert_minutes * 60`, `guardian_submission_timeout_total` incrementing, `review_queue_oldest_seconds` approaching `reviews.backlog.alert_minutes`.
- **Triage (≤5 minutes):**
  1. Verify Guardian health endpoints and latency dashboards.
  2. Inspect queue detail:

     ```sql
     SELECT artifact_id,
            org_id,
            submitted_at,
            now() - submitted_at AS age,
            last_heartbeat_at,
            judgment_attempts
       FROM guardian_submission_queue
     ORDER BY submitted_at
       LIMIT 50;
     ```

  3. Sample worker logs for `FAILED_GUARDIAN_TIMEOUT`; confirm Celery pods healthy.
  4. Review recent `guardian.rules.version` activations and Guardian deploys for regressions.
- **Decision:**
  - *Compute exhaustion*: raise HPA floor, ensure DB connections within pool limits, restart pods after scaling.
  - *Policy/rules regression*: roll back offending ruleset or apply waiver/manual review following RB-GUARD-001.
  - *External dependency degradation*: coordinate with LPE/Settings teams, throttle submissions if upstream latency high.
- **Post-remediation:**
  - Confirm `guardian_pending_total` below alert threshold and `guardian_pending_oldest_seconds` < 120s for two scrapes.
  - Ensure `guardian_submission_timeout_total` stopped increasing and queued artifacts receive fresh judgments.
  - Document incident with root cause, remediation, SQL excerpt, and follow-up tasks; update HPA/alert thresholds if burst patterns changed.

### R.5 RB-GUARD-MANUAL — Manual review reconciliation (informative)

**Breadcrumbs:** Implementation `ops/runbooks/guardian/manual_review.md`, Automation `ops/scripts/guardian/reconcile_manual.py`, Tests `tests/ops/test_runbook_integrity.py::test_guardian_manual_runbook`, Observability Grafana dashboard “Guardian Manual Review” (panels `guardian_manual_pending_total`, `guardian_manual_age_seconds`).\\ *Purpose: Ensure manual decisions stay auditable and rejoin automated flow once Guardian recovers.*\\ *Contract: Manual review ledger updates must precede replay jobs so judgment history remains complete.*\\ *State: Ledger updates stored alongside incident tickets within `ops/guardian/manual_review/<date>.jsonl`.*\\ *Failure modes & retries: Omitting ledger updates or skipping reconciliation replays invalidates artifact provenance.*\\ *Observability: Manual review metrics return to baseline before incident closure.*

- Operators record manual decisions with manifest annotations while Guardian automation is paused.
- Reconciliation job replays queued artifacts once health recovers; incident owners capture waiver IDs, policy bundle hashes, and remediation tasks in the postmortem per RB-GUARD-001 follow-up checklist.

______________________________________________________________________

## Appendix C — Detection payload schema (binding)

*Purpose: Provide the canonical span-level schema and examples referenced in §4.4.*

### C.1 Field definitions

| Field                   | Type    | Required    | Description                                                                                |
| ----------------------- | ------- | ----------- | ------------------------------------------------------------------------------------------ |
| `span_id`               | UUIDv7  | Yes         | Deterministic identifier for the detected span.                                            |
| `type`                  | String  | Yes         | Guardian entity classification (for example, `PHI.MRN`, `SPI.BIOMETRIC`).                  |
| `offset_start`          | Integer | Yes         | Byte offset (UTF-8) marking span start.                                                    |
| `offset_end`            | Integer | Yes         | Byte offset marking span end (exclusive).                                                  |
| `source`                | Enum    | Yes         | Detection tier identifier (`TIER0_SCHEMA`, `TIER1_REGEX`, `TIER2_ML`, `TIER3_CONTEXTUAL`). |
| `confidence`            | Float   | Conditional | Present for probabilistic sources; `null` omitted for deterministic hits.                  |
| `locale`                | String  | Yes         | BCP 47 locale for policy alignment.                                                        |
| `attributes`            | Object  | No          | Detector-specific metadata (checksum booleans, normalization hints).                       |
| `policy_context_digest` | String  | Yes         | SHA-256 digest tying the span to the evaluated policy context.                             |
| `masking_profile`       | String  | Conditional | Applied masking profile name when Guardian masked the span.                                |
| `restorable`            | Boolean | Conditional | Indicates whether detokenization is allowed under policy/waiver.                           |

### C.2 Reference JSON payload

```json
{
  "span_id": "01916f1c-29d4-7c8f-bf1c-8c4e7c632a21",
  "type": "PHI.MRN",
  "offset_start": 152,
  "offset_end": 172,
  "source": "TIER1_REGEX",
  "confidence": 0.94,
  "locale": "en-CA",
  "attributes": {
    "format": "mrn_ca",
    "luhn_pass": true
  },
  "policy_context_digest": "b5a0c1f7...",
  "masking_profile": "hipaa_default",
  "restorable": false
}
```

Guardian validates payloads against this schema before persisting evidence in `guardian_span_detection`. Ingestion failures raise `SCHEMA_POLICY_BLOCK` errors and emit audit events for follow-up.
