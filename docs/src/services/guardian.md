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

## Document Controls

| Field          | Value |
| -------------- | ----- |
| Authors | Guardian Service Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-23 |
| Owners | Security Engineering; Platform Architecture |
| Reviewers | QA Engineering Lead; SRE Manager |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |

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

## Reading Guide

Use this guide before changing Guardian policy, queue semantics, or downstream workflows.

- **Scope:** Guardian judgments, policy integration, API surface, queueing, observability, security, and operational controls.
- **Structure:** Sections follow the 0–10 service spec template; appendices hold payload samples and runbooks.
- **Maintenance:** Run the docs lint (`python scripts/docs/lint_docs.py`) and link check (`python scripts/docs/link_check.py --strict`) prior to submitting Guardian changes.
- **Change protocol:** Include a summary of Guardian impact in PR descriptions and link reviewers to the affected sections (`§2`, `§3`, `§4`, etc.).
- **References:** TDD §7 (Guardian), ADR-0001, ADR-0003, ADR-0004.
- **Contacts:** Owners Security Engineering + Platform Architecture; operational mailing list `guardian-oncall@`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Establish Guardian’s mission as the platform safety gate that enforces residency, policy, and content integrity before artifacts progress. **|**
**Contract:** Every SA/WP/CD artifact must pass through Guardian; PASS/WARN/BLOCK/WAIVED semantics, latency targets, and queue idempotency stay consistent across releases. **|**
**State:** Guardian persists manifests, policy context hashes, waiver history, span detections, and queue telemetry in Postgres and the submission bus. **|**
**Failures & handling:** Queue saturation, classifier failures, or policy bundle drift trigger mitigations in §5 and operational drills in §8.3. **|**
**Observability:** Grafana “Guardian SLO” dashboard (`guardian_judgment_latency_seconds`, `guardian_cleared_ratio`, `guardian_submission_queue_depth`), synthetic job `guardian_slo.yaml`, and Ops logs under `storage/media/cases/<case>/ops/guardian/`. **|**
**Breadcrumbs:** Code `apps/platform/operations/guardian.py`, `packages/udocket_core/guardian/`, Tests `tests/platform/guardian/test_guardian_enqueue.py`, Observability `infra/grafana/guardian_slo.json`. **|**
**References:** §2 Responsibilities, §3 API contract, §4 State management, §5 Failure modes, §8 Operational notes, ADR-0001. *

- **Mission:** Issue deterministic PASS/WARN/BLOCK/WAIVED judgments before artifacts advance to review or client delivery, enforcing policy, residency, and safety controls.
- **Interfaces:** Internal RPC enqueue API, REST read APIs (`/readyz`, `/synthetic/status`, `/api/v1/guardian/...`), detection helpers (`/guardian/detect-and-mask`, `/guardian/quarantine`), and Postgres persistence with RLS.
- **Submission fabric:** Any SA/WP/CD creation or version bump transitions the artifact to `PENDING_JUDGMENT`; workers submit the payload to the regional Guardian queue (`guardian_submission_queue`). Guardian hydrates manifests, PolicyContext, waiver state, and classifier telemetry before emitting its judgment.
- **Event model:** Guardian emits SSE/audit events `GUARDIAN.JUDGMENT.{PASS|WARN|BLOCK|WAIVED}` with `guardian_judgment_id`, reason codes, policy snapshot hashes, and pointers to upstream findings. Reviewer-initiated quarantines round-trip through `POST /guardian/quarantine` so Guardian remains the canonical history.
- **Criticality:** 99.9% availability SLO with P95 judgment latency ≤ 5 minutes and queue backlog alert threshold of 5 minutes (`guardian.queue.backlog_alert_minutes`). Submit-time SLO is ≤ 1 second P95 from enqueue to first evaluation attempt under nominal load.
- **Region isolation:** Every residency boundary maintains an isolated Guardian deployment and queue; judgments never cross regions. HPAs keep ≥ 2 replicas per region (≤ 70 % CPU) and synthetic monitoring (`guardian_slo.yaml`) probes each cluster.
- **Dependencies:** Policy context from Localization & Policy Engine (LPE), Settings service (including `guardian.rules.version` bundles), Postgres, Redis/queue fabric, and OPA sidecars for rule evaluation.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Define Guardian’s enforcement scope, judgment vocabulary, escalation duties, and lifecycle integration points across the platform. **|**
**Contract:** Guardian is the single authority for PASS/WARN/BLOCK/WAIVED outcomes, status transitions, quarantine workflows, and waiver requirements. **|**
**State:** Judgment history, waiver manifests, quarantine records, and parent-child locks persist in Postgres tables (`guardian_judgment_history`, `guardian_waiver`, `guardian_relationship_lock`). **|**
**Failures & handling:** Mis-mapped statuses or waiver drift trigger remediation via §5.1 Incident triggers and §8.3 runbooks; parent-lock conflicts raise explicit errors. **|**
**Observability:** Metrics `guardian_cleared_ratio`, `guardian_waiver_total`, audit stream `storage/media/cases/<case>/ops/ops_guardian.jsonl`, and SSE event consumers instrument downstream reactions. **|**
**Breadcrumbs:** Code `packages/udocket_core/guardian/judgment.py`, Queue orchestrator `apps/platform/operations/guardian.py`, Tests `tests/platform/guardian/test_status_mapping.py`. **|**
**References:** TDD §7.3 (Artifact lifecycle), §5 Failure modes, Appendix A (reference artifacts), status mapping appendix in `docs/src/overview/tdd/appendices/status-mapping.md`. *

### 2.1 Canonical judgments

**Purpose:** Define the standardized Guardian outcomes that downstream services must honor. **|**
**Contract:** PASS/WARN/BLOCK/WAIVED semantics and default actions remain stable; new outcomes require TDD + doc updates. **|**
**State:** Judgment enums live in `packages/udocket_core/guardian/judgment.py` and database lookup tables. **|**
**Failures & handling:** Deviations lead to status mismatches caught by §5 failure procedures. **|**
**Observability:** Metrics `guardian_cleared_ratio`, audit logs, and SSE streams track verdict distribution. **|**
**References:** §2.2 Status mapping, §8.3 runbooks, TDD §7.3. **|**
**Breadcrumbs:** Enum definitions `packages/udocket_core/guardian/judgment.py`, tests `tests/platform/guardian/test_judgment_enums.py`.

| Judgment | Description                                          | Default actions                                               |
| -------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| PASS     | Requirements satisfied; artifact is safe to proceed. | Unlocks WP → `CLEARED_FOR_USE`, CD → `OPERATOR_PREP`.         |
| WARN     | Minor issues; proceed with operator banners.         | Same transitions as PASS; UI surfaces warnings.               |
| BLOCK    | Artifact violates policy, integrity, or residency.   | Sets status to `QUARANTINED`; requires remediation or waiver. |
| WAIVED   | Dual-approved override to treat as PASS.             | Same transitions as PASS; records waiver manifest entry.      |

### 2.2 Status mapping

**Purpose:** Provide deterministic mapping from Guardian judgments to downstream artifact statuses. **|**
**Contract:** Tables below are the single source of truth; dependent services must reference them instead of duplicating logic. **|**
**State:** Status transitions implement in workflow services and tests alongside this table. **|**
**Failures & handling:** Diverging mappings trigger review workflow incidents and §8.3.4 RB-GUARD-QUEUE follow-ups. **|**
**Observability:** Workflow metrics (status transition counters) and audit logs highlight mismatches. **|**
**References:** TDD Appendix H, §3.4 Review integration, §8.3. **|**
**Breadcrumbs:** Workflow code `apps/platform/workflows/status_transitions.py`, tests `tests/platform/workflows/test_status_transitions.py`.

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

**Purpose:** Explain how waivers and quarantines operate so reviewers and automation enforce the correct controls. **|**
**Contract:** Waivers require dual approval and manifest stamping; quarantines propagate to dependent artifacts until Guardian clears them. **|**
**State:** Waiver records live in `guardian_waiver`, manifests record `guardian.manifest.waiver_id`, and quarantine metadata persists in judgment history. **|**
**Failures & handling:** Improperly documented waivers or missing quarantine logs trigger compliance incidents and §8.3.3 RB-GUARD-QUAR actions. **|**
**Observability:** Metrics `guardian_waiver_total`, `guardian_quarantine_false_positive_total`, and audit logs track usage. **|**
**References:** §5 Failure modes, §8.3 Runbooks & drills, TDD Appendix H. **|**
**Breadcrumbs:** Waiver workflow `apps/platform/workflows/waiver.py`, tests `tests/platform/guardian/test_waiver_policies.py`, audit schema `packages/udocket_core/guardian/store.py`.

- Waivers require dual approval (Security + Architecture) and manifest stamping (`guardian.manifest.waiver_id`).
- Quarantined artifacts block dependent artifacts (for example, timeline events referencing a quarantined transcript).
- HIPAA/SPI triggers escalate to Security and enable enhanced review requirements (`spi_review_required=true`).
- Org settings `org.guardian.pre_operator_gates[]` enumerate artifact classes (typically `SA`, `WP`, `CD`) that remain hidden from operators until Guardian returns PASS/WARN. Reviewer-triggered quarantines route through Guardian so the canonical log records `quarantined_by`, `quarantine_reason`, and waiver metadata.

______________________________________________________________________

## 3) API Contract (binding)

**Purpose:** Describe every programmatic surface (REST, queue, events) Guardian exposes so integrators implement consistent safety gates. **|**
**Contract:** Guardian accepts submissions via idempotent queue APIs, serves read endpoints with RLS enforcement, and emits deterministic SSE/audit events. Schemas, reason codes, and idempotency keys remain stable across releases; any breaking change requires a new versioned path. **|**
**State:** Submissions carry policy-context digests, artifact hashes, and source metadata; judgments persist manifests and span evidence; SSE streams broadcast the final outcome with pointers back to stored history. **|**
**Failures & handling:** Queue timeouts, schema validation errors, and policy drift raise explicit error codes (`GUARDIAN_SUBMISSION_TIMEOUT`, `SCHEMA_POLICY_BLOCK`, `POLICY_FORBIDDEN_PATTERN`) and surface remediation guidance in §5 and §8.3. **|**
**Observability:** Interfaces emit metrics (`guardian_enqueue_conflict_total`, `guardian_judgment_latency_seconds`), structured JSONL audits, and SSE counts; synthetic jobs exercise these paths continuously. **|**
**Breadcrumbs:** Implementation `apps/platform/operations/guardian.py`, `packages/udocket_core/guardian/api.py`, `packages/udocket_core/guardian/queue.py`; Tests `tests/platform/guardian/test_guardian_api.py`, `tests/platform/guardian/test_guardian_queue.py`. **|**
**References:** §4 State management, §5 Failure modes, Appendix B (payload schema), TDD §7.4, ADR-0001. *

### 3.1 External Interfaces (binding)

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

### 3.2 Internal Interfaces (binding)

- Internal workers call `apps/platform/operations/guardian.py::enqueue_with_idempotency` with `artifact_id`, `artifact_class`, `payload_sha256`, `policy_context`, and `source_artifacts[]`.
- Idempotency key: `sha256(case_id + artifact_id + payload_sha256 + policy_context_hash)`; collisions return the prior judgment and increment `guardian_enqueue_conflict_total`.
- Queue timeout: 300 seconds (`guardian.queue.submission_timeout_seconds`). Workers emit `GUARDIAN_SUBMISSION_TIMEOUT` when exceeded and retry per Celery policy; sustained failures trigger §5.1 backlog mitigation.
- Submissions must use HMAC-authenticated service tokens; Guardian records request metadata in `ops/guardian/batch_submit.jsonl` and Postgres `guardian_submission_audit`.
- Replay tooling (`POST /guardian/judgments:enqueue`) shares the same queue path to guarantee identical side effects and audit history.

### 3.3 Evaluation pipeline (normative)

**Purpose:** Detail the evaluation stages Guardian executes for every submission so teams understand timing, determinism, and evidence capture. **|**
**Contract:** Steps run in order with deterministic rules; altering the pipeline requires updating this section and notifying downstream consumers. **|**
**State:** Intermediate artifacts include policy context digests, classifier outputs, masking profiles, and final judgments persisted to Postgres and ops logs. **|**
**Failures & handling:** Schema errors, detector drift, or policy mismatches raise specific reason codes and fall back to §5 incident responses. **|**
**Observability:** Metrics (`guardian_judgment_latency_seconds`, detector-specific counters), SSE events, and audit logs confirm each stage executed. **|**
**References:** §4 State management, Appendix B detection payload schema, §8.3.3 RB-GUARD-QUAR. **|**
**Breadcrumbs:** Pipeline implementation `packages/udocket_core/guardian/pipeline.py`, detector integrations `packages/udocket_core/guardian/detectors/`, tests `tests/platform/guardian/test_pipeline.py`.

1. Validate schema and policy context, rejecting malformed payloads with `SCHEMA_POLICY_BLOCK`.
2. Execute residency, HIPAA, forbidden-pattern, and waiver checks against LPE/OPA bundles.
3. Run content classifiers (Azure Content Safety PHI, in-house transformer, deterministic regex heuristics).
4. Fuse detector results through a deterministic decision tree; PASS/WARN attach operator banners, BLOCK escalates reason codes (for example, `POLICY_FORBIDDEN_PATTERN`, `INTEGRITY_HASH_MISMATCH`).
5. Persist manifests, span evidence, and policy context digests; emit SSE/audit events for workflow, portal, and analytics consumers.

Guardian enforces parent-child integrity by locking upstream artifacts (`SELECT ... FOR SHARE`). If a parent demotes mid-flight, the child returns `BLOCK (PARENT_NOT_APPROVED)`. Judgments are idempotent per `{artifact_id, content_sha256}`—replays with the same hash reuse the prior verdict while new hashes create fresh history rows.

#### 3.3.1 Detection tiers (binding)

**Purpose:** Define the layered detection strategy Guardian applies so detector owners understand responsibilities and provenance. **|**
**Contract:** Each tier must run in order and produce evidence with deterministic identifiers; disabling a tier requires Architecture + Security approval. **|**
**State:** Detector outputs include span IDs, confidence, and provenance metadata persisted in `guardian_span_detection` and audit logs. **|**
**Failures & handling:** Detector regression or drift triggers §5.2 responses and §8.3.3 RB-GUARD-QUAR actions. **|**
**Observability:** Detector-specific metrics (`guardian_detector_tier_latency_seconds`, `guardian_detector_errors_total`) and sampling pipelines monitor health. **|**
**References:** Appendix B payload schema, §5.2 Detector regression, §8.3.3 RB-GUARD-QUAR. **|**
**Breadcrumbs:** Detector implementations `packages/udocket_core/guardian/detectors/`, telemetry exporters `packages/udocket_core/guardian/metrics.py`, tests `tests/platform/guardian/test_detectors.py`.

1. **Tier-0 — schema & field guards:** Validates known slots (`dob`, `mrn`, `ssn`, etc.) and emits `SCHEMA_POLICY_BLOCK` (`INVALID_FIELD_FORMAT`) when data fails canonical formatting.
2. **Tier-1 — pattern + checksum:** Jurisdiction-specific regex packs and checksum validators (Luhn, Verhoeff, ABA routing, ICD/HCPCS/CPT shape, Rx BIN/PCN length) emit `PATTERN_MATCH` evidence.
3. **Tier-2 — ML/NLP detectors:** Locale-scoped NER models sourced from LPE contribute spans with model IDs and confidence; sub-threshold spans log telemetry for drift analysis.
4. **Tier-3 — contextual verifier:** A constrained LLM re-scores contentious spans (`{"confirm": true|false, "confidence": float}`) and applies reason `CONTEXTUAL_VERIFIER`.
5. **Normalization & fusion:** Overlapping spans merge deterministically (higher confidence, stricter policy). Provenance retains contributing tiers/detectors.
6. **Masking & tokenization:** Applies masking profiles to a working copy, references vault namespace, and records whether spans are restorable before judgment.
7. **Guardian judgment:** Aggregates detections, policy context, provider telemetry, and waiver state to emit PASS/WARN/BLOCK/WAIVED with reason codes such as `HIPAA_REQUIRED`, `PII_DETECTED`, `SPI_DETECTED`, `DLP_VIOLATION`, `CLASSIFIER_LOW_CONFIDENCE`, and `PARENT_NOT_APPROVED`.

### 3.4 Review integration & audit writes (binding)

**Purpose:** Explain how Guardian records reviewer actions and surfaces judgments to dependent services to maintain audit integrity. **|**
**Contract:** All review actions must flow through documented endpoints; Guardian persists immutable history and enforces version checks before accepting changes. **|**
**State:** Decisions write to `guardian_judgment_history`, SSE streams, and case ops logs with deterministic IDs. **|**
**Failures & handling:** Version mismatches, duplicate actions, or SSE delivery failures raise explicit errors and prompt §8.3 remediation. **|**
**Observability:** Metrics (`guardian_review_action_total`), audit streams, and SSE subscriber health dashboards monitor review flow. **|**
**References:** §4 State management, §8.3.5 RB-GUARD-MANUAL, Appendix B payload schema. **|**
**Breadcrumbs:** Review API `packages/udocket_core/guardian/review.py`, workflow integration `apps/platform/workflows/guardian.py`, tests `tests/platform/guardian/test_review_actions.py`.

- Reviewer actions (`approve`, `changes`, `quarantine`, `waive`) route through Guardian endpoints (`/guardian/quarantine`, `/guardian/review-actions`, `/guardian/judgments:enqueue`) so the service remains the canonical history authority.
- Guardian writes every decision to `guardian_judgment_history` with deterministic UUIDv7 IDs, preserving prior verdicts even when artifacts re-enter `PENDING_JUDGMENT`. Replays with matching `{artifact_id, content_sha256}` reuse the latest record; new hashes create append-only entries.
- Manual and automated decisions both emit SSE/audit events (`GUARDIAN.JUDGMENT.*`) containing the identifiers workflow services use for manifests, approval UIs, and downstream response guides.
- Reviewer console integrations include structured comments and span references; Guardian verifies the submitted `expected_version` matches the manifest before accepting the action.
- Read-only helpers (`GET /api/v1/guardian/<id>`, `GET /api/v1/guardian?artifact_id=`) are guarded by RLS so analytics surfaces rely on the secured projections instead of direct table access.

### 3.5 Detection & masking payloads (binding)

**Purpose:** Document the structure and provenance requirements for detection and masking payloads Guardian produces and consumes. **|**
**Contract:** Clients must honor deterministic UUIDv7 span IDs, include policy context digests, and persist masking metadata exactly as defined; schema changes require Appendix B updates. **|**
**State:** Payloads live in `guardian_span_detection`, case ops logs, and SSE/audit events with references to masking profiles and vault namespaces. **|**
**Failures & handling:** Missing digests, mismatched spans, or vault namespace errors raise `SCHEMA_POLICY_BLOCK` or `POLICY_FORBIDDEN_PATTERN` codes and escalate per §5.2. **|**
**Observability:** Schema validation metrics, audit logs, and masking success counters track payload health. **|**
**References:** Appendix B detection payload schema, §4 State management, §8.3.3 RB-GUARD-QUAR. **|**
**Breadcrumbs:** Schema definitions `packages/udocket_core/guardian/contracts/payloads.py`, masking helpers `packages/udocket_core/guardian/masking.py`, tests `tests/platform/guardian/test_detection_payloads.py`.

- Guardian records span-level evidence and masking metadata using deterministic UUIDv7 identifiers so reruns reconcile reliably.
- Payloads always link to `policy_context_digest`, masking profiles, and vault namespaces so Compose/Signer can restore spans when policy allows (`POST /vault/detokenize`).
- Canonical field definitions, validation rules, and the reference JSON example live in Appendix B (binding); clients must validate against that schema before submitting detection feedback.
- Provider telemetry (speech/LLM safety APIs) lands in `guardian_provider_flags[]`; severe categories Guardian missed elevate the outcome to WARN (`PROVIDER_CRITICAL_HINT`) and auto-file detector gap tickets.

______________________________________________________________________

## 4) State Management (binding)

**Purpose:** Describe the stores, queues, and configuration sources Guardian owns so persistence, reconciliation, and policy enforcement stay deterministic. **|**
**Contract:** Guardian maintains append-only judgment history, span evidence, and submission audit trails in Postgres; queue state mirrors the persisted records, and all configuration enters via Settings/LPE snapshots. Direct database edits or ad-hoc queue injections are prohibited. **|**
**State:** Postgres tables (`guardian_judgment_history`, `guardian_span_detection`, `guardian_submission_audit`), Kafka/Azure Service Bus queues, OPA policy bundles, and case-scoped ops artifacts. **|**
**Failures & handling:** Partition rotation failures, queue desynchronization, or stale policy contexts trigger mitigations in §5 and §8.3. Reconciliation scripts (`ops/db/rotate_partitions.py`, `ops/scripts/guardian/reconcile_manual.py`) repair discrepancies. **|**
**Observability:** Metrics (`guardian_pending_total`, `guardian_pending_oldest_seconds`, `guardian_policy_block_total`), audit JSONL streams, and hash comparisons between Settings snapshots and Guardian manifests validate state. **|**
**Breadcrumbs:** Persistence code `packages/udocket_core/guardian/store.py`, Queue integration `packages/udocket_core/guardian/queue.py`, Config ingestion `packages/udocket_core/guardian/config.py`, Ops scripts under `ops/scripts/guardian/`. **|**
**References:** §3 API contract, §5 Failure modes, Appendix B (payload schema), §8.3 Runbooks & drills, ADR-0001, ADR-0004. *

### 4.1 Persistence model

**Purpose:** Describe how Guardian structures its databases and logs so data remains auditable and partitioned by org. **|**
**Contract:** Partitioning, RLS policies, and secure projections must remain enabled; direct access to base tables is reserved for Guardian service accounts. **|**
**State:** Postgres partitions, RLS policies, submission audit tables, and case-level logs mirror judgments and submissions. **|**
**Failures & handling:** Partition rotation failures or RLS misconfigurations trigger §5 responses and require immediate remediation via `ops/db/rotate_partitions.py`. **|**
**Observability:** Database health dashboards (`guardian_db_partition_age`, `guardian_rls_denied_total`) and CI migrations checks confirm schema compliance. **|**
**References:** §5 Failure modes, §8.3.4 RB-GUARD-QUEUE, ADR-0001. **|**
**Breadcrumbs:** Schema migrations `packages/udocket_core/guardian/migrations/`, partition job `ops/db/rotate_partitions.py`, RLS definitions `packages/udocket_core/guardian/store.py`.

- `guardian_judgment_history` partitions monthly on `decided_at`; rotation job `ops/db/rotate_partitions.py` creates future partitions and seals retired ones.
- Row-level security policy `guardian_history_vis` enforces org isolation. Application roles read from secure projections (`guardian_judgment_history_secure`, `guardian_judgment`) while service accounts maintain base-table permissions.
- Span evidence resides in `guardian_span_detection` with deterministic UUIDv7 identifiers tied to manifest digests and masking profiles.
- Submission metadata (`guardian_submission_audit`) captures worker identity, payload hashes, policy digests, and queue offsets so operators can reconcile message position with persisted history.
- Human-readable logs mirror structured entries under `storage/media/cases/<case>/ops/guardian/<job_id>__guardian.log` for audit parity.

### 4.2 Policy context & configuration

**Purpose:** Capture how Guardian consumes configuration and policy data so evaluations remain deterministic and compliant. **|**
**Contract:** Guardian only honors settings delivered via Settings/LPE digests; manual toggles or partial updates are disallowed. Changes must update this section and the associated appendices. **|**
**State:** Configuration values populate PolicyContext inputs, Settings snapshots, and Guardian defaults bundles. **|**
**Failures & handling:** Digest mismatches, missing keys, or waived residency/HIPAA settings trigger §5.2 responses and §8.3 follow-up. **|**
**Observability:** Metrics `guardian_policy_bundle_version`, config hash comparisons, and Settings activation logs verify parity. **|**
**References:** §3 API contract, §5 Failure modes, §8.3.3 RB-GUARD-QUAR, ADR-0004. **|**
**Breadcrumbs:** Config loader `packages/udocket_core/guardian/config.py`, Settings schema `packages/udocket_core/settings/guardian.py`, tests `tests/platform/guardian/test_policy_context.py`.

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

**Purpose:** Outline how Guardian tracks message queues and cached policy bundles to ensure evaluators process submissions in order with the correct rules. **|**
**Contract:** Queue offsets must reconcile with submission audit tables; policy caches must match the active digest before evaluations proceed. **|**
**State:** Kafka/Azure Service Bus topics, materialized views, and OPA cache metadata record queue progress and bundle versions. **|**
**Failures & handling:** Offset gaps, replay loops, or stale policy caches trigger §5.1/§5.3 mitigations and §8.3.4 RB-GUARD-QUEUE procedures. **|**
**Observability:** Metrics (`guardian_pending_total`, `guardian_submission_queue_lag_seconds`, `guardian_policy_cache_age_seconds`) and reconciliation scripts monitor state. **|**
**References:** §3.2 Submission interfaces, §5 Failure modes, §8.3.4 RB-GUARD-QUEUE. **|**
**Breadcrumbs:** Queue admin tools `ops/scripts/guardian/queue_reconcile.py`, Kafka topics `infra/kafka/guardian.yml`, OPA cache config `infra/kubernetes/guardian/opa-config.yaml`.

- Production uses Kafka for `guardian_submission_queue`; regulated tenants use Azure Service Bus with matching semantics. Producers include artifact workers and replay tooling; consumers are Guardian evaluators.
- Queue offsets and digests mirror `guardian_submission_audit`; reconciliation compares Kafka offsets with audit rows to detect dropped or duplicated messages.
- Materialized views expose live queue depth/age to Grafana (`guardian_pending_total`, `guardian_pending_oldest_seconds`).
- Cached policy bundles live in OPA sidecars; Guardian tracks the active digest (`guardian.rules.version`) and refresh timestamps to ensure evaluators use the expected rule set.

### 4.4 Artifacts, logs, and retention

**Purpose:** Explain Guardian’s artifact footprint on disk and retention policies so audits and incident reviews can trace decisions. **|**
**Contract:** Ops directories, JSON metadata, and retention windows must match policy requirements; deleting or truncating logs requires compliance approval. **|**
**State:** Case-scoped files, retention schedules, and OPA decision logs replicate Guardian history outside the database. **|**
**Failures & handling:** Missing logs or retention gaps trigger compliance incidents and §8.3.5 RB-GUARD-MANUAL follow-ups. **|**
**Observability:** Retention jobs and checksum monitors report status to dashboards and CI scripts. **|**
**References:** §5 Failure modes, §8.3 Runbooks & drills, Appendix B payload schema. **|**
**Breadcrumbs:** File layout `storage/media/cases/<case>/ops/guardian/`, retention scripts `ops/scripts/guardian/purge_old_logs.py`, compliance monitors `infra/compliance/guardian-retention.yaml`.

- Case-scoped ops directories persist JSON metadata and audit JSONL (`storage/media/cases/<case>/ops/guardian/`), following the deterministic naming convention `<job_id>__guardian_log.json`.
- Retention: Guardian keeps span evidence, manifests, and audit logs ≥ 365 days to satisfy HIPAA/PHIPA obligations; manual review records persist until incident closure sign-off.
- OPA decision logs stream to immutable storage with matching `guardian_judgment_id` references so auditors can compare inline evaluations with stored manifests.

______________________________________________________________________

## 5) Failure Modes (binding)

**Purpose:** Capture the primary ways Guardian can degrade and the contractual responses required to preserve artifact integrity and compliance. **|**
**Contract:** Guardian must fail closed on policy violations, residency breaches, and detector uncertainty; backlog or dependency failures trigger the operational playbooks in §8.3 before artifacts progress. Manual overrides require dual approval and explicit manifest stamping. **|**
**State:** Failure conditions are recorded in `guardian_judgment_history` (`status=BLOCK`, reason codes), queue metrics, and incident JSONL under `ops/guardian/incidents/`. **|**
**Failures & handling:** Submission backlog, detector drift, and dependency outages each have defined guardrails and runbooks summarized below. **|**
**Observability:** Alerts on `guardian_pending_oldest_seconds`, `guardian_policy_block_total`, `guardian_quarantine_false_positive_total`, synthetic job failures, and detector drift feed PagerDuty rotations. **|**
**Breadcrumbs:** Incident automation `ops/scripts/guardian/*.py`, Grafana dashboards “Guardian SLO” and “Guardian Manual Review”, Tests `tests/platform/guardian/test_failure_modes.py`. **|**
**References:** §8.3.2 RB-GUARD-001 / §8.3.3 RB-GUARD-QUAR / §8.3.4 RB-GUARD-QUEUE / §8.3.5 RB-GUARD-MANUAL, §3.3 Detection tiers, §7 Operational readiness, TDD §7.5. *

### 5.1 Submission backlog or queue saturation

**Purpose:** Describe how Guardian responds when submission pipelines lag so artifacts do not bypass safety checks. **|**
**Contract:** Guardian holds artifacts in `PENDING_JUDGMENT` until backlog clears; manual review requires RB-GUARD-001 escalation with dual approval. **|**
**State:** Queue depth metrics, submission timeout counters, and audit logs (`guardian_submission_audit`) capture backlog state. **|**
**Failures & handling:** Triggered by queue age thresholds or timeout growth; responders follow §8.3.4 RB-GUARD-QUEUE. **|**
**Observability:** Metrics `guardian_pending_total`, `guardian_pending_oldest_seconds`, and alerts `alert_guardian_queue_stale` monitor this failure. **|**
**References:** §3.2 Submission interfaces, §4.3 Queue state, §8.3.4 RB-GUARD-QUEUE. **|**
**Breadcrumbs:** Queue reconciliation script `ops/scripts/guardian/queue_reconcile.py`, incident template `ops/guardian/incidents/backlog.json`, tests `tests/platform/guardian/test_backlog_handling.py`.

- Trigger: `guardian_pending_oldest_seconds` exceeds `guardian.queue.backlog_alert_minutes` or `guardian_submission_timeout_total` trends upward.
- Response: Follow §8.3.4 RB-GUARD-QUEUE—throttle enqueue rates, scale evaluator pods, verify Kafka/Service Bus health, and replay stuck messages via `POST /guardian/judgments:enqueue`.
- Guarantee: Artifacts remain `PENDING_JUDGMENT` until backlog clears; manual review is disallowed unless RB-GUARD-001 escalates and dual approval authorizes manual mode.

### 5.2 Detector regression or policy drift

**Purpose:** Outline mitigation steps when detection accuracy or policy bundles regress so Guardian never approves risky artifacts. **|**
**Contract:** Bundle rollbacks and detector adjustments require Architecture + Security approval; affected artifacts stay quarantined until diagnostics finish. **|**
**State:** Detector metrics, policy bundle digests, and quarantine manifests record the regression context. **|**
**Failures & handling:** Triggered by WARN/BLOCK reason spikes, synthetic failures, or false-positive quotas; responders execute §8.3.3 RB-GUARD-QUAR and §8.3.2 RB-GUARD-001. **|**
**Observability:** Metrics `guardian_policy_block_total`, `guardian_quarantine_false_positive_total`, synthetic job outputs, and detector telemetry dashboards. **|**
**References:** §3.3 Detection pipeline, Appendix B payload schema, §8.3.3 RB-GUARD-QUAR. **|**
**Breadcrumbs:** Detector configs `packages/udocket_core/guardian/detectors/`, bundle manifests `packages/udocket_core/lpe/bundles/`, incident template `ops/guardian/incidents/detector_regression.json`.

- Trigger: Spike in WARN/BLOCK reason codes (`PROVIDER_CRITICAL_HINT`, `CLASSIFIER_LOW_CONFIDENCE`), synthetic job failures, or `guardian_quarantine_false_positive_total` > 5 %.
- Response: §8.3.3 RB-GUARD-QUAR and RB-GUARD-001—freeze bundle activations, roll back `guardian.rules.version` if needed, and coordinate with LPE/Settings to validate PolicyContext digests.
- Guarantee: Deliverables stay quarantined until detectors are revalidated; waivers require manifest stamping and Security/Architecture approval.

### 5.3 Dependency outage or configuration mismatch

**Purpose:** Define how Guardian fails closed when upstream systems or configuration digests become unavailable or inconsistent. **|**
**Contract:** Guardian blocks artifacts with explicit `BLOCK (DEPENDENCY_UNAVAILABLE)` reason codes until dependencies recover; manual review requires ledger capture and reconciliation. **|**
**State:** Dependency health indicators, settings snapshot hashes, and incident logs in `ops/guardian/incidents/` track the outage. **|**
**Failures & handling:** Triggered by OPA signature failures, Settings hash mismatches, or upstream outages; responders invoke §8.3.2 RB-GUARD-001 and §8.3.5 RB-GUARD-MANUAL as needed. **|**
**Observability:** Synthetic probes, dependency SLIs, and configuration drift detectors highlight the issue. **|**
**References:** §3 API contract, §4 State management, §8.3.2 RB-GUARD-001/§8.3.5 RB-GUARD-MANUAL. **|**
**Breadcrumbs:** Dependency monitors `infra/monitoring/dependencies.yaml`, manual ledger `ops/guardian/manual_review/`, tests `tests/platform/guardian/test_dependency_outage.py`.

- Trigger: OPA sidecar signature verification failure, Settings snapshot hash mismatch, or upstream service outage (LPE, Settings, Reference Manager).
- Response: §8.3.2 RB-GUARD-001—shift to manual review mode only if on-call declares it, capture manifests under `ops/guardian/manual_review/<date>.jsonl`, and reconcile once dependencies recover.
- Guarantee: Guardian blocks artifacts (`BLOCK (DEPENDENCY_UNAVAILABLE)`) rather than allowing progression with stale policy; manual reconciliation records are replayed and audited post-incident.

______________________________________________________________________

## 6) Observability (binding)

**Purpose:** Define the telemetry, dashboards, and synthetic coverage that prove Guardian is meeting its safety and latency commitments. **|**
**Contract:** Metrics, logs, and synthetic probes listed here are mandatory; removing any signal requires Observability + Security approval and equivalent replacement. SLOs are 99.9 % availability with judgment P95 ≤ 5 minutes. **|**
**State:** Metrics publish via Prometheus (`guardian_*` series), logs/audits persist in Postgres and case ops directories, and synthetic jobs emit structured results to `guardian_slo.yaml` artifacts. **|**
**Failures & handling:** Breaches escalate through §8.3 Runbooks & drills (RB-GUARD-001/QUEUE/QUAR) and drive the failure responses in §5. **|**
**Observability:** Grafana dashboards “Guardian SLO”, “Guardian Manual Review”, log aggregation views, and audit JSONL provide responders with context. **|**
**Breadcrumbs:** Dashboards under `infra/grafana/guardian_*.json`, synthetic job definitions `ops/synthetics/guardian_slo.yaml`, log pipeline config `infra/logging/guardian.json`. **|**
**References:** §5 Failure modes, §7 Operational readiness, §8.3 Runbooks & drills, Appendix B (payload schema). *

### 6.1 Metrics

**Purpose:** List the key quantitative signals that demonstrate Guardian health and SLO compliance. **|**
**Contract:** These metrics must remain instrumented and alerted; removing or renaming them requires Observability sign-off and doc updates. **|**
**State:** Metrics publish via Prometheus scraping Guardian pods and queue consumers. **|**
**Failures & handling:** Threshold breaches map to §5 failure scenarios and corresponding runbooks. **|**
**Observability:** Grafana dashboards “Guardian SLO” and alertmanager routes consume these metrics. **|**
**References:** §5 Failure modes, §8.3 Runbooks & drills, infra monitoring configs. **|**
**Breadcrumbs:** Metric definitions `packages/udocket_core/guardian/metrics.py`, Prometheus rules `infra/monitoring/guardian-prometheus-rules.yaml`.

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

**Purpose:** Summarize Guardian’s structured logging and audit footprint so compliance teams can trace every decision. **|**
**Contract:** Audit streams must remain append-only with RLS safeguards; application code interacts only through secure projections. **|**
**State:** JSONL files, Postgres partitions, and immutable storage capture judgments, policy digests, and manual actions. **|**
**Failures & handling:** Missing partitions, RLS bypass attempts, or log retention breaches trigger §5.3 responses and compliance escalations. **|**
**Observability:** Partition rotation jobs, checksum verifiers, and log pipeline alerts monitor audit health. **|**
**References:** §4 State management, §8.3.5 RB-GUARD-MANUAL, ADR-0001. **|**
**Breadcrumbs:** Audit schema `packages/udocket_core/guardian/store.py`, log pipeline `infra/logging/guardian.json`, rotation script `ops/db/rotate_partitions.py`.

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

**Purpose:** Describe automated probes that continuously exercise Guardian to detect regressions before customers do. **|**
**Contract:** Synthetic jobs must run on schedule, cover HIPAA/SPI/residency scenarios, and gate releases when failing. **|**
**State:** Synthetic definitions live in `ops/synthetics/guardian_slo.yaml` with results logged to incident dashboards. **|**
**Failures & handling:** Failures escalate via §8.3.2 RB-GUARD-001 and may freeze bundle activations. **|**
**Observability:** Grafana panels, PagerDuty incidents, and synthetic job logs track outcomes. **|**
**References:** §5 Failure modes, §8 Operational notes, §8.3.2 RB-GUARD-001. **|**
**Breadcrumbs:** Synthetic config `ops/synthetics/guardian_slo.yaml`, CI hooks `scripts/docs/lint_docs.py` (synthetic link check), tests `tests/synthetics/test_guardian_slo.py`.

- Synthetic job `guardian_slo.yaml` submits representative workloads (500 concurrent submissions, 5k/day) and records judgment/queue timing; success requires P95 latency ≤ configured SLO and zero submission timeouts.
- Synthetic GET requests verify `/readyz` and `/synthetic/status` per environment after deployments; failures open PagerDuty incidents tagged `GUARDIAN_SLO`.
- Synthetic coverage exercises HIPAA, SPI, and residency scenarios to validate policy gating; drift triggers `PHI_DETECTION_DRIFT` follow-up.
- Failure of synthetic job triggers RB-GUARD-001 incident response.

______________________________________________________________________

## 7) Security & Compliance (binding)

**Purpose:** Capture Guardian’s security posture, residency guarantees, and regulatory obligations so downstream services rely on accurate enforcement boundaries. **|**
**Contract:** Guardian must enforce residency and HIPAA/SPI policies exactly as configured, reject unsigned or stale policy bundles, and preserve tamper-evident audit trails. Dual approval is mandatory for waivers or manual overrides. **|**
**State:** Security posture derives from policy bundles (`guardian.rules.version`), Settings toggles, HSM-managed signing keys, and audit records in `guardian_judgment_history`/`guardian_span_detection`. **|**
**Failures & handling:** Residency mismatches, key compromise, or PHI exposure follow §8.3 escalation paths and the LPE/Guardian incident playbooks. **|**
**Observability:** Security dashboards track residency enforcement (`guardian_residency_block_total`), HIPAA-specific metrics, and audit signature validation; cosign/verifier jobs confirm container provenance. **|**
**Breadcrumbs:** IAM policies `infra/iam/guardian/`, HSM integration `packages/udocket_core/guardian/crypto.py`, residency policy bundles `packages/udocket_core/lpe/bundles/`, compliance tests `tests/platform/guardian/test_security.py`. **|**
**References:** §4 State management, §5 Failure modes, §8.3, ADR-0004 (LPE), TDD §5 (Security). *

- **Residency controls:** Guardian enforces org allowlists, rejects submissions outside permitted compute/storage/vector regions, and emits `RESIDENCY_POLICY_BLOCK` events tied to manifest IDs. Waivers require dual approval and manifest stamping (`RESIDENCY_WAIVER_USED`) before artifacts progress.
- **HIPAA/SPI safeguards:** SPI inherits HIPAA-grade protections. Guardian quarantines PHI artifacts when HIPAA mode is disabled, enforces dual-review for SPI deliverables, and records accesses in `SPI_ACCESS_EVENT` audit trails.
- **Policy integrity:** Guardian only loads signed bundles validated by Managed HSM keys (dual Ed25519 + ECDSA when `security.tls.fips_mode=true`). Bundle rollouts track digests and expiry; stale bundles block evaluations.
- **Tamper resistance:** Judgment history, span evidence, and OPA decision logs are append-only. Images are signed via cosign, and CI policy gates verify provenance before deployment.
- **Data minimization:** Guardian scrubs plaintext spans from logs, stores masked variants in ops directories, and routes detokenization through mTLS-protected `POST /vault/detokenize` with purpose binding.

______________________________________________________________________

## 8) Operational Notes (binding)

**Purpose:** Summarize Guardian’s on-call posture, deployment practices, and response coordination so operators can keep the safety gate available. **|**
**Contract:** Operational procedures, incident triggers, and manual review steps must stay in sync with §8.3. Any change to runbooks, alert thresholds, or response ownership requires updating this section and the appendices simultaneously. **|**
**State:** Rotation calendars, deployment manifests, and incident records live in `ops/guardian/` alongside the runbooks referenced below. **|**
**Failures & handling:** Operational responses map directly to §5 (Failure modes) and §8.3 (RB-GUARD-001/QUEUE/QUAR/MANUAL). **|**
**Observability:** Operators rely on Grafana dashboards from §6, alertmanager routes, and audit JSONL streams in `storage/media/cases/<case>/ops/guardian/`. **|**
**Breadcrumbs:** Helm charts `infra/kubernetes/guardian/helm`, Terraform modules `infra/terraform/guardian`, runbooks `ops/runbooks/guardian/*.md`, deployment scripts `ops/scripts/guardian/deploy.py`. **|**
**References:** §5 Failure modes, §8.3 Runbooks & drills, §8.3, `infra/kubernetes/guardian/`, `ops/runbooks/guardian/`. *

### 8.1 Operational Posture

**Purpose:** Outline day-to-day guardrails that keep Guardian healthy outside of incidents. **|**
**Contract:** On-call rotations monitor SLO dashboards and maintain readiness to execute §8.3 procedures; ownership alternates between Security Engineering and Platform Operations. **|**
**State:** Rotation calendars and health check configurations live in `ops/guardian/roster.yaml` and Grafana dashboards. **|**
**Failures & handling:** Deviations feed §5 failure responses and §8.3 runbooks; failure to staff rotations blocks deploy approvals. **|**
**Observability:** Dashboards “Guardian SLO” and “Guardian Manual Review” plus alertmanager routes provide posture visibility. **|**
**Breadcrumbs:** Roster `ops/guardian/roster.yaml`, HPA configs `infra/kubernetes/guardian/`, alert configs `infra/monitoring/guardian-alerts.yaml`. **|**
**References:** §6 Observability, §8.3.4 RB-GUARD-QUEUE/§8.3.3 RB-GUARD-QUAR. *

- Guardian on-call rotations monitor `guardian_judgment_latency_seconds`, `guardian_pending_total`, and `guardian_policy_block_total` to confirm the 99.9 % availability / ≤ 5 minute P95 latency commitments.
- Queue submission health depends on Celery worker heartbeats and Settings/LPE dependencies; §8.3.4 RB-GUARD-QUEUE describes how to remediate backlog growth while preserving auditability.
- Quarantine volume and waiver approvals follow §8.3.3 RB-GUARD-QUAR, keeping manifests and waiver artifacts in lockstep with Security/Architecture approvals.

### 8.2 Incident Triggers

**Purpose:** Enumerate the alerts that escalate Guardian incidents and map directly to runbook entries. **|**
**Contract:** Each trigger routes to PagerDuty with the corresponding RB-GUARD identifier; responders must execute the linked runbook before mitigation counts as complete. **|**
**State:** Alert definitions live in `infra/monitoring/guardian-alerts.yaml`, and incidents log to `ops/guardian/incidents/*.jsonl`. **|**
**Failures & handling:** Alerts align with §5 failure scenarios; misconfigured thresholds require Ops approval to adjust. **|**
**Observability:** Alertmanager, Grafana annotations, and incident dashboards track trigger history. **|**
**Breadcrumbs:** Monitoring configs `infra/monitoring/guardian-alerts.yaml`, PagerDuty service “Guardian SLO”, incident logs `ops/guardian/incidents/`. **|**
**References:** §5 Failure modes, §8.3.2 RB-GUARD-001/§8.3.4 RB-GUARD-QUEUE/§8.3.3 RB-GUARD-QUAR. *

- `alert_guardian_queue_stale` (Grafana) fires when backlog age exceeds `guardian.queue.backlog_alert_minutes`; responders follow §8.3.4 RB-GUARD-QUEUE.
- `guardian_policy_block_total` spikes or synthetic job failures (`guardian_slo.yaml`) escalate via §8.3 entries RB-GUARD-001 and RB-GUARD-QUAR, depending on whether latency or policy regression drives the alert.
- `PHI_DETECTION_DRIFT` incidents originate from classifier sampling (§6.3); §8.3.3 RB-GUARD-QUAR covers containment and follow-up requirements.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Maintain authoritative Guardian recovery guides, drills, and manual review procedures executed during incidents. **|**
**Contract:** Alerts enumerated in §§5–8 map to RB-GUARD identifiers documented here; responders update these runbooks after every incident or drill. **|**
**State:** Procedures live alongside automation scripts in `ops/runbooks/guardian/`, with this section summarizing triggers, decision trees, and evidence requirements. **|**
**Failures & handling:** Missing or stale steps block deployment sign-off; responders raise follow-up tasks to refresh runbooks before closing incidents. **|**
**Observability:** Post-incident retros attach the executed RB-GUARD identifier and confirm coverage during quarterly reviews; docs CI checks referenced runbook files exist. **|**
**Breadcrumbs:** Runbooks `ops/runbooks/guardian/*.md`, automation `ops/scripts/guardian/`, tests `tests/ops/test_runbook_integrity.py::test_guardian_runbooks`, PagerDuty service “Guardian SLO”, Grafana dashboard “Guardian SLO”. **|**
**References:** §5 Failure modes, §8.1 Operational posture, §8.3, ADR-0001. *

#### 8.3.1 Runbook Index (informative)

- `RB-GUARD-001` — Guardian SLO breach stabilisation
- `RB-GUARD-QUAR` — Quarantine spike investigation
- `RB-GUARD-QUEUE` — Submission backlog watchdog
- `RB-GUARD-MANUAL` — Manual review reconciliation

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarise Guardian runbooks responders execute during incidents or exercises. **|**
**Contract:** Each runbook maps to specific alerts and evidence expectations; responders update the playbook after incidents or drills. **|**
**State:** Runbook markdown, automation scripts, and ledger templates live under `ops/runbooks/guardian/` and `ops/scripts/guardian/`. **|**
**Failures & handling:** Missing steps or stale guidance block deployment sign-off until refreshed. **|**
**Observability:** Docs lint, PagerDuty analytics, and retrospective checklists track coverage. **|**
**Breadcrumbs:** `ops/runbooks/guardian/*.md`, `ops/scripts/guardian/*.py`, incident templates `ops/guardian/incidents/*.jsonl`. **|**
**References:** §5 Failure Modes, Ops governance policy, alert catalog.

- `RB-GUARD-001`: Restore availability during SLO breaches—validate `/readyz` and `/synthetic/status`, capture queue metrics, decide whether to pause submissions or scale evaluators (`ops/scripts/guardian/scale_guardian.py`), maintain manual review ledgers in `ops/guardian/manual_review/<date>.jsonl`, and replay artifacts once latency returns to target.
- `RB-GUARD-QUAR`: Investigate quarantine spikes—compare bundle digests, sample artifacts, coordinate waivers with Security/Architecture, and log evidence (manifests, policy hashes, detector logs) before resuming automation.
- `RB-GUARD-QUEUE`: Clear submission backlog—throttle enqueue rates, scale evaluator pods, reconcile queue offsets via `ops/scripts/guardian/queue_reconcile.py`, and keep artifacts in `PENDING_JUDGMENT` until metrics recover.
- `RB-GUARD-MANUAL`: Manage manual review mode—capture reviewer decisions, enforce masking policies, and replay manual judgments once automated processing stabilises.

#### 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills rehearse SLO breach recovery, quarantine investigation, backlog management, and manual reconciliation; evidence stored in `ops/guardian/drills/<date>/` with retrospective notes.
- Docs lint (`scripts/docs/build_runbook_catalog.py --check`) and PagerDuty analytics verify execution; missed drills block release sign-off until remediated.
- Compliance reviews reference drill evidence, incident logs, and manual review ledgers to confirm coverage of Guardian runbooks.

### 8.4 Migrations & Backfills (binding)

**Purpose:** Capture the schema rotations and replay tooling required to keep Guardian’s queues, manifests, and policy caches aligned. **|**
**Contract:** Partition rotations, manifest replays, and policy cache backfills must run from tagged scripts with dry-run output captured before production execution. **|**
**State:** Migration manifests live in `ops/guardian/migrations/` with SHA-256 digests recorded in `ops/guardian/migration_log.jsonl`. **|**
**Failures & handling:** Failed rotations or partial replays lead to duplicate submissions or lost audit history; §8.3 Runbooks & drills require rollback checkpoints and post-migration validation. **|**
**Observability:** Dashboards “Guardian Queue Health” and “Guardian Policy Sync” plus synthetic submissions verify migration success; `scripts/docs/build_runbook_catalog.py` ensures referenced scripts remain present. **|**
**Breadcrumbs:** Partition rotation script `ops/scripts/guardian/rotate_partitions.py`, policy sync `ops/scripts/guardian/sync_policy.py`, migration checklist `ops/guardian/migrations/README.md`. **|**
**References:** §3 API contract, §4.3 Queue state, ADR-0001, ops README. *

- Quarterly partition rotations update queue tables to keep history bounded while preserving replay fidelity.
- Policy cache backfills run after Settings/LPE bundle releases to ensure Guardian evaluators load the latest digests.
- Reconciliation scripts compare audit tables to queue offsets and raise incidents when mismatches persist.

### 8.5 Operational Workflows (binding)

**Purpose:** Describe recurring operational tasks that preserve Guardian readiness outside of incidents. **|**
**Contract:** Each workflow enumerated here has an owner, cadence, and evidence requirement; skipping a workflow triggers a follow-up task before deploy approvals resume. **|**
**State:** Checklists and automations live in `ops/guardian/workflows/` and the on-call handbook; outputs append to `ops/guardian/workflow_log.jsonl`. **|**
**Failures & handling:** Missed cadences surface in quarterly readiness reviews; owners must backfill evidence and document process updates. **|**
**Observability:** Staffing dashboards, workflow logs, and retrospective notes provide health signals. **|**
**Breadcrumbs:** Workflow docs `ops/guardian/workflows/*.md`, automation `ops/scripts/guardian/*.py`, staffing roster `ops/guardian/roster.yaml`. **|**
**References:** §8.3.5 RB-GUARD-MANUAL, §6 Observability, §8.3. *

#### 8.5.1 Manual review cadence (binding)

**Purpose:** Describe how Guardian transitions into and out of manual review when automation is degraded. **|**
**Contract:** Manual mode activates only with Security + Architecture approval, logs every decision as `MANUAL_GUARDIAN_JUDGMENT`, and requires full reconciliation before closing the incident. **|**
**State:** Manual decisions persist in `ops/guardian/manual_review/<date>.jsonl` with cross-links to incident tickets and waiver manifests. **|**
**Failures & handling:** Missing ledger entries or skipped reconciliation jobs break provenance; §8.3.5 RB-GUARD-MANUAL mandates the recovery steps. **|**
**Observability:** Dashboard “Guardian Manual Review” tracks manual backlog and age; incident retros review ledger completeness. **|**
**References:** §4 State management, §5 Failure modes, §8.3.5 RB-GUARD-MANUAL. **|**
**Breadcrumbs:** Manual review ledger `ops/guardian/manual_review/`, reconciliation script `ops/scripts/guardian/reconcile_manual.py`, tests `tests/ops/test_runbook_integrity.py::test_guardian_manual_runbook`.

- When Guardian automation is paused, operations invoke RB-GUARD-001 to route artifacts through manual review queues and capture `MANUAL_GUARDIAN_JUDGMENT` records.
- Reconciliation jobs replay queued artifacts once health recovers; responders document the waiver/incident outcomes according to RB-GUARD-001 post-remediation notes.
- Quarterly readiness reviews sample manual review incidents to confirm ledger completeness and evidence hygiene.

______________________________________________________________________

## 9) Dependencies (informative)

**Purpose:** Map Guardian’s upstream and downstream relationships so teams understand how policy changes cascade across the platform. **|**
**Contract:** Guardian depends on LPE, Settings, Reference Manager, and queue infrastructure meeting their SLAs; downstream services must honor Guardian judgments before mutating artifact state. Dependencies are versioned—breaking changes require joint rollout plans and updated references here. **|**
**State:** Integration contracts live in this spec, corresponding ADRs, and shared schema fixtures (`packages/udocket_core/guardian/contracts/`). **|**
**Failures & handling:** Dependency outages feed §5.3 responses; misaligned versions trigger §8.3 coordination. **|**
**Observability:** Cross-service dashboards track latency/error budgets, and shared alerts notify both owners when thresholds breach. **|**
**Breadcrumbs:** Integration code `packages/udocket_core/guardian/integration/`, queue adapters `packages/udocket_core/guardian/queue.py`, Celery orchestration `apps/platform/operations/guardian.py`. **|**
**References:** ADR-0001 (Guardian/Ready-Quarantine), ADR-0003 (API versioning), ADR-0004 (LPE), §3 API contract, §4 State management. *

- **Localization & Policy Engine (upstream):** Supplies signed policy bundles, residency baselines, and detector configurations. Guardian blocks evaluations when digests diverge or signatures fail.
- **Settings service (upstream):** Provides organization toggles (`guardian.rules.version`, HIPAA, SPI). Settings activations trigger Guardian dry-runs; failures roll back activation.
- **Reference Manager (upstream):** Publishes jurisdiction catalogs and court metadata; Guardian updates policy context digests during catalog revisions.
- **Workers & Celery pipelines (downstream):** Submit artifacts to Guardian and respect PASS/WARN/BLOCK before promoting statuses. Backlog handling relies on §8.3.4 RB-GUARD-QUEUE routines.
- **Portal, Compose, and Notifications (downstream):** Condition UI visibility and deliverables on Guardian verdicts; WARN injects banners, BLOCK halts customer presentation.
- **Signer (downstream):** Applies signatures only when Guardian manifests show PASS/WAIVED; certificates embed `guardian_judgment_id` for audit.
- **Queue fabric (shared):** Kafka/Service Bus notifies Guardian evaluators; offsets align with submission audit tables to ensure replay accuracy.

______________________________________________________________________

## 10) References (informative)

- **ADRs:** ADR-0001 Guardian Ready/Quarantine, ADR-0003 API Versioning & Sunset, ADR-0004 Localization & Policy Engine, ADR-0005 OPA Policy Plane.
- **TDD sections:** TDD §5 Security Architecture, TDD §7 Guardian Integration, TDD Appendix H Operational Guides.
- **Runbooks:** §8.3 entries RB-GUARD-001/QUEUE/QUAR/MANUAL plus supporting files in `ops/runbooks/guardian/`.
- **Diagrams:** `docs/src/services/guardian/diagrams/upload-guardian-approve-v1.mmd`, `docs/src/overview/tdd/diagrams/data-lineage-v1.mmd`, `docs/src/services/lp-engine/diagrams/residency-policy-enforcement-v1.mmd`.
- **Schemas & fixtures:** Appendix B, `packages/udocket_core/guardian/contracts/payloads.py`, sample manifests in `docs/examples/lineage/`.
- **Change protocol:** PRs touching Guardian code/policy must link to this section, run `python scripts/docs/lint_docs.py`, and obtain Architecture + Security approval before deploy.

______________________________________________________________________

## Appendix A — Reference artifacts (informative)

**Purpose:** Catalog diagrams, manifests, and example payloads that illustrate Guardian workflows referenced in the main sections. **|**
**Contract:** Files listed here remain the canonical artifacts; updates must keep paths stable and refresh references in §§2–4. **|**
**State:** Artifacts live under `docs/src/services/guardian/diagrams/` and `docs/examples/lineage/` with deterministic filenames matching the associated job IDs. **|**
**Failures & handling:** Missing or stale artifacts cause docs lint/link check failures; update the assets or adjust references before merging. **|**
**Observability:** Docs CI verifies diagram availability via `scripts/docs/render_mermaid.sh` and link checks. **|**
**References:** §2 Responsibilities, §3 API contract, Appendix B payload schema. **|**
**Breadcrumbs:** Diagram sources `docs/src/services/guardian/diagrams/`, example manifests `docs/examples/lineage/`, render script `scripts/docs/render_mermaid.sh`.

- **Diagrams:**
- `services/guardian/diagrams/upload-guardian-approve-v1.mmd` (sequence of upload → Guardian → approval).
- `services/lp-engine/diagrams/residency-policy-enforcement-v1.mmd` (policy propagation and Guardian enforcement).
- `overview/tdd/diagrams/data-lineage-v1.mmd` (artifact lineage through Guardian and Signer).
- **Examples:**
  - `docs/examples/lineage/transcript_to_compose.json` demonstrating manifest linkage with Guardian judgment IDs.
  - `docs/examples/lineage/compose_client.json` showing deliverable provenance.

This specification is the canonical source for Guardian behavior. Sections in the broader TDD now link here; future updates MUST originate here and propagate outward.

______________________________________________________________________

## Appendix B — Detection payload schema (binding)

**Purpose:** Provide the canonical span-level schema and examples referenced in §3.5 and §4 so downstream services validate Guardian detections consistently. **|**
**Contract:** Clients and downstream services must adhere to this schema; changes require coordinated version bumps, doc updates, and redeployments across evaluators and consumers. **|**
**State:** Schema definitions live in `packages/udocket_core/guardian/contracts/payloads.py` and JSON examples under `docs/examples/lineage/`. **|**
**Failures & handling:** Schema drift or missing fields cause `SCHEMA_POLICY_BLOCK` errors and escalate via §5.2 and §8.3.3 RB-GUARD-QUAR. **|**
**Observability:** Schema validation metrics, docs lint, and synthetic jobs ensure examples stay current. **|**
**References:** §3.5 Detection & masking payloads, §4 State management, §8.3.3 RB-GUARD-QUAR. **|**
**Breadcrumbs:** Contracts module `packages/udocket_core/guardian/contracts/payloads.py`, fixtures `tests/platform/guardian/test_detection_payloads.py`, example manifests `docs/examples/lineage/guardian_payload.json`.

### B.1 Field definitions

**Purpose:** Document each detection payload field Guardian produces and consumes. **|**
**Contract:** Field names, types, and semantics remain stable across releases; new fields must be optional and documented. **|**
**State:** Stored alongside span evidence and manifests in Postgres (`guardian_span_detection`). **|**
**Failures & handling:** Missing required fields trigger `SCHEMA_POLICY_BLOCK` and escalate via §8.3.3 RB-GUARD-QUAR. **|**
**Observability:** Validation metrics and audit logs capture schema issues. **|**
**References:** §3.5 Detection & masking payloads, §4 State management, §8.3.3 RB-GUARD-QUAR. **|**
**Breadcrumbs:** Schema source `packages/udocket_core/guardian/contracts/payloads.py`, tests `tests/platform/guardian/test_detection_payloads.py`.

| Field                   | Type    | Required    | Description                                                                                |
| ----------------------- | ------- | ----------- | ------------------------------------------------------------------------------------------ |
| `span_id`               | UUIDv7  | Yes         | Deterministic identifier for the detected span.                                            |
| `type`                  | String  | Yes         | Guardian entity classification (for example, `PHI.MRN`, `SPI.BIOMETRIC`).                  |
| `offset_start`          | Integer | Yes         | Byte offset (UTF-8) marking span start.                                                    |
| `offset_end`            | Integer | Yes         | Byte offset marking span end (exclusive).                                                  |
| `source`                | Enum    | Yes         | Detection tier identifier (`TIER0_SCHEMA`, `TIER1_REGEX`, `TIER2_ML`, `TIER3_CONTEXTUAL`). |
| `confidence`            | Float   | Conditional | Present for probabilistic sources; omitted for deterministic hits.                         |
| `locale`                | String  | Yes         | BCP 47 locale for policy alignment.                                                        |
| `attributes`            | Object  | No          | Detector-specific metadata (checksum booleans, normalization hints).                       |
| `policy_context_digest` | String  | Yes         | SHA-256 digest tying the span to the evaluated policy context.                             |
| `masking_profile`       | String  | Conditional | Applied masking profile name when Guardian masked the span.                                |
| `restorable`            | Boolean | Conditional | Indicates whether detokenization is allowed under policy/waiver.                           |

### B.2 Reference JSON payload

**Purpose:** Provide a concrete example of the detection payload schema for tooling, tests, and cross-service documentation. **|**
**Contract:** Example must remain in sync with `packages/udocket_core/guardian/contracts/payloads.py`; update both together. **|**
**State:** Mirrors fixtures used in unit tests and docs CI. **|**
**Failures & handling:** Divergence between example and schema causes docs lint failures; update promptly. **|**
**Observability:** Docs CI and schema validation tests ensure the example parses. **|**
**References:** §3.5 Detection & masking payloads, §8.3.3 RB-GUARD-QUAR, §4 State management. **|**
**Breadcrumbs:** Fixture `tests/platform/guardian/test_detection_payloads.py::EXPECTED_PAYLOAD`, docs example `docs/examples/lineage/guardian_payload.json`.

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
