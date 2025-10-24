---
title: "uDocket — Guardian Service Specification"
subtitle: "Canonical design, policy, and operational reference"
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
  - '<base href="..">'
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
  - '<header class="page-header">uDocket — Guardian Service Specification <br> Canonical design, policy, and operational reference</header>'
  - '<footer class="page-footer">Confidential · Last updated 2025-10-23 · Page <span class="page-number"></span> of <span class="page-count"></span></footer>'
---

**Audience:** Guardian engineers, operators, reviewers, policy authors, and dependent service owners.\\
**Purpose:** Establish Guardian as a standalone, authoritative specification that consolidates all judgments, policy integration, API, observability, and operational guidance previously dispersed through the TDD.

---

## Document controls

| Field           | Value |
| --------------- | ----- |
| Version         | 0.1-draft |
| Status          | Implementable |
| Last updated    | 2025-10-23 |
| Primary owners  | Security Engineering; Platform Architecture |
| Approvers       | Architecture Steering Committee; Security Review Board |
| Reviewers       | QA Engineering Lead; SRE Manager |
| ADR index       | `docs/adr/README.md` |
| Migration plan  | Establishes this specification as the canonical Guardian reference, absorbing the former TDD Guardian sections and Appendix H runbooks; platform TDD now links here for service-level details. |
| Docs validation | `python scripts/docs/lint_docs.py` |
| Link lint       | `python scripts/docs/link_check.py --strict` |

---

## 1) Service overview (binding)

*Purpose: Define Guardian responsibilities, posture, and success criteria as the authoritative source for dependent teams.*\\
*Contract: Any change to Guardian behavior, judgment vocabulary, queue semantics, or SLOs MUST be reflected here and linked from PRs touching Guardian code.*\\
*State transitions: Guardian gates the `SA → WP/CD → DL` lifecycle using the canonical statuses in §3.2.*\\
*Failure modes & retries: Covered in §6.3 (queue) and §7 (runbooks).*\\
*Observability: Dashboard “Guardian SLO” tracks `guardian_judgment_latency_seconds`, `guardian_cleared_ratio`, and queue backlog metrics.*\\
*References: §2, §3, §4, §5, §6, §7.*

- **Mission:** Issue deterministic PASS/WARN/BLOCK/WAIVED judgments before artifacts advance to review or client delivery, enforcing policy, residency, and safety controls.
- **Interfaces:** Internal RPC enqueue API, REST read APIs (`/readyz`, `/synthetic/status`, `/api/v1/guardian/...`), detection helpers (`/guardian/detect-and-mask`, `/guardian/quarantine`), and Postgres persistence with RLS.
- **Submission fabric:** Any SA/WP/CD creation or version bump transitions the artifact to `PENDING_JUDGMENT`; workers submit the payload to the regional Guardian queue (`guardian_submission_queue`). Guardian hydrates manifests, PolicyContext, waiver state, and classifier telemetry before emitting its judgment.
- **Event model:** Guardian emits SSE/audit events `GUARDIAN.JUDGMENT.{PASS|WARN|BLOCK|WAIVED}` with `guardian_judgment_id`, reason codes, policy snapshot hashes, and pointers to upstream findings. Reviewer-initiated quarantines round-trip through `POST /guardian/quarantine` so Guardian remains the canonical history.
- **Criticality:** 99.9% availability SLO with P95 judgment latency ≤ 5 minutes and queue backlog alert threshold of 5 minutes (`guardian.queue.backlog_alert_minutes`). Submit-time SLO is ≤ 1 second P95 from enqueue to first evaluation attempt under nominal load.
- **Region isolation:** Every residency boundary maintains an isolated Guardian deployment and queue; judgments never cross regions. HPAs keep ≥ 2 replicas per region (≤ 70 % CPU) and synthetic monitoring (`guardian_slo.yaml`) probes each cluster.
- **Dependencies:** Policy context from Localization & Policy Engine (LPE), Settings service (including `guardian.rules.version` bundles), Postgres, Redis/queue fabric, and OPA sidecars for rule evaluation.

---

## 2) Judgment vocabulary & lifecycle integration (binding)

### 2.1 Canonical judgments

| Judgment | Description | Default actions |
| -------- | ----------- | --------------- |
| PASS     | Requirements satisfied; artifact is safe to proceed. | Unlocks WP → `CLEARED_FOR_USE`, CD → `OPERATOR_PREP`. |
| WARN     | Minor issues; proceed with operator banners. | Same transitions as PASS; UI surfaces warnings. |
| BLOCK    | Artifact violates policy, integrity, or residency. | Sets status to `QUARANTINED`; requires remediation or waiver. |
| WAIVED   | Dual-approved override to treat as PASS. | Same transitions as PASS; records waiver manifest entry. |

### 2.2 Status mapping

*Purpose: Provide deterministic mapping from Guardian judgments to artifact statuses.*\\
*Contract: Tables below are the single source of truth; dependent services MUST reference them instead of duplicating logic.*

| Artifact class | Prior status          | Guardian outcome | Next status        | Notes |
| -------------- | --------------------- | ---------------- | ------------------ | ----- |
| Work Product   | `PENDING_JUDGMENT`    | PASS/WARN/WAIVED | `CLEARED_FOR_USE`  | WARN adds operator banner. |
| Work Product   | `PENDING_JUDGMENT`    | BLOCK            | `QUARANTINED`      | Remediation tracked via manifest. |
| Candidate Deliverable | `PENDING_JUDGMENT` | PASS/WARN/WAIVED | `OPERATOR_PREP` | Entry point into review workflow. |
| Candidate Deliverable | `PENDING_JUDGMENT` | BLOCK            | `QUARANTINED`      | Prevents review queue admission. |

| Condition | Org policy posture | Guardian judgment | Artifact status impact | Notes |
| --------- | ------------------ | ----------------- | ---------------------- | ----- |
| PHI present while HIPAA mode **off** | Forbid PHI | BLOCK (`HIPAA_REQUIRED`) | `QUARANTINED` | Requires enabling HIPAA mode or removing PHI before progression. |
| PHI present, HIPAA mode **on**, spans masked | Allow masked | PASS/WARN | `CLEARED_FOR_USE` (WP) / `OPERATOR_PREP` (CD) | WARN adds reviewer banner with span highlights. |
| PHI present, HIPAA mode **on**, restoration requested | Allow full | PASS | `APPROVED → SIGNED` | Compose detokenizes spans under vault policy; manifest records restoration intent. |
| Detector low confidence on high-risk entity | Any | WARN (`CLASSIFIER_LOW_CONFIDENCE`) | Normal flow with banner | Reviewers verify spans before approval. |
| Provider flags category Guardian tiers missed | Any | WARN (`PROVIDER_CRITICAL_HINT`) | Normal flow | Advisory only; also files detector gap ticket. |
| Parent artifact not cleared | Enforce parent gating | BLOCK (`PARENT_NOT_APPROVED`) | `QUARANTINED` | Deterministic parent locking prevents stale approvals. |

Guardian respects downstream approval invariants (ExclusiveSwap) and ensures deliverables only advance from `APPROVED` onward once Guardian history marks the latest edit as cleared.

### 2.3 Waiver & quarantine policies

- Waivers require dual approval (Security + Architecture) and manifest stamping (`guardian.manifest.waiver_id`).
- Quarantined artifacts block dependent artifacts (for example, timeline events referencing a quarantined transcript).
- HIPAA/SPI triggers escalate to Security and enable enhanced review requirements (`spi_review_required=true`).
- Org settings `org.guardian.pre_operator_gates[]` enumerate artifact classes (typically `SA`, `WP`, `CD`) that remain hidden from operators until Guardian returns PASS/WARN. Reviewer-triggered quarantines route through Guardian so the canonical log records `quarantined_by`, `quarantine_reason`, and waiver metadata.

---

## 3) Architecture & deployment (normative)

*Purpose: Document Guardian topology, runtime stack, and scaling model.*

- **Runtime:** FastAPI application deployed on AKS (production) and Docker Compose (local parity).
- **Security:** mTLS between Guardian and internal clients; OPA sidecars enforce policy bundles signed by Managed HSM keys (dual Ed25519 + ECDSA when `security.tls.fips_mode=true`).
- **Persistence:** Postgres with RLS enforcing org isolation; audit history stored in `guardian_judgment_history` monthly partitions and surfaced through secure views (`guardian_judgment_history_secure`, `guardian_judgment`). Span evidence lives in `guardian_span_detection` (RLS protected).
- **Queue fabric:** Kafka (production) or Azure Service Bus (regulated tenants) backs `guardian_submission_queue`; workers publish submission metrics (`guardian_pending_total`, `guardian_pending_oldest_seconds`) from the materialized view. Replay tooling (`POST /guardian/judgments:enqueue`) reuses the same bus for deterministic behavior.
- **Scalability:** Horizontal Pod Autoscaler based on latency; queue throughput sized for 5k/day with 500 concurrent submissions (validated via synthetic job `guardian_slo.yaml`). HPAs maintain ≥ 2 replicas per region and scale when `guardian_judgment_latency_seconds` P95 approaches the 5-minute SLO.
- **Dependencies:**
  - Settings API for configuration snapshots (`guardian.settings_snapshot_sha256`, `guardian.rules.version`).
  - Localization & Policy Engine (LPE) for policy bundles and residency baselines.
  - Reference Manager for jurisdictional catalogs.
  - Digital Signer and Portal consume Guardian outputs as gating signals.

---

## 4) Interfaces & contracts (binding)

### 4.1 Enqueue API

- Internal clients call `apps/platform/operations/guardian.py::enqueue_with_idempotency` to submit artifacts.
- Requests include `artifact_id`, `artifact_class`, `payload_sha256`, `policy_context`, and `source_artifacts[]`.
- Idempotency key: `sha256(case_id + artifact_id + payload_sha256 + policy_context_hash)`; conflicts increment `guardian_enqueue_conflict_total`.
- Queue timeout: 300 seconds (`guardian.queue.submission_timeout_seconds`); exceeded timeouts emit `GUARDIAN_SUBMISSION_TIMEOUT` events.
- Guardian submissions are HMAC-authenticated service accounts; audit trail recorded in `ops/guardian/batch_submit.jsonl`.

### 4.2 Evaluation pipeline

1. Validate schema and policy context.
2. Execute policy checks (residency, HIPAA, forbidden patterns, waiver state) via LPE/OPA.
3. Run content classifiers (Azure Content Safety PHI classifier, in-house transformer, deterministic regex heuristics).
4. Aggregate results with deterministic decision tree; on PASS/WARN produce banners; on BLOCK escalate reason codes (for example, `POLICY_FORBIDDEN_PATTERN`, `INTEGRITY_HASH_MISMATCH`).
5. Persist judgment, manifest snapshot, and emit events for workflow, portal, and analytics.

Guardian enforces parent-child integrity by locking upstream artifacts (`SELECT ... FOR SHARE`) and re-reading manifests before finalizing a decision; if a parent demotes mid-flight the child returns `BLOCK (PARENT_NOT_APPROVED)`. Judgments are idempotent per `{artifact_id, content_sha256}`—replays with the same hash reuse the prior verdict while new hashes create fresh history rows.

#### 4.2.1 Detection tiers (binding)

1. **Tier-0 — schema & field guards:** Validates known slots (`dob`, `mrn`, `ssn`, etc.) and emits `SCHEMA_POLICY_BLOCK` (`INVALID_FIELD_FORMAT`) when data fails canonical formatting.
2. **Tier-1 — pattern + checksum:** Jurisdiction-specific regex packs and checksum validators (Luhn, Verhoeff, ABA routing, ICD/HCPCS/CPT shape, Rx BIN/PCN length) emit `PATTERN_MATCH` evidence.
3. **Tier-2 — ML/NLP detectors:** Locale-scoped NER models sourced from the LLM Provider Exchange (LPE) contribute spans with model IDs and confidence; sub-threshold spans log telemetry for drift analysis.
4. **Tier-3 — contextual verifier:** A constrained LLM re-scores contentious spans (`{"confirm": true|false, "confidence": float}`) and applies reason `CONTEXTUAL_VERIFIER`.
5. **Normalization & fusion:** Overlapping spans merge deterministically (higher confidence, stricter policy). Provenance retains contributing tiers/detectors.
6. **Masking & tokenization:** Applies masking profiles to a working copy, references vault namespace, and records whether spans are restorable before judgment.
7. **Guardian judgment:** Aggregates detections, policy context, provider telemetry, and waiver state to emit PASS/WARN/BLOCK/WAIVED with reason codes such as `HIPAA_REQUIRED`, `PII_DETECTED`, `SPI_DETECTED`, `DLP_VIOLATION`, `CLASSIFIER_LOW_CONFIDENCE`, and `PARENT_NOT_APPROVED`.

Guardian persists span evidence in `guardian_span_detection` (deterministic UUIDv7 IDs) and summarizes annotations for reviewer consoles; advisory provider hints land in `guardian_provider_flags[]` and may promote WARN (`PROVIDER_CRITICAL_HINT`) without overriding Guardian’s final decision.

### 4.3 Read APIs & health checks

| Endpoint                   | Purpose | Notes |
| -------------------------- | ------- | ----- |
| `GET /readyz`              | Liveness/readiness | Used by HPA and incident playbooks. |
| `GET /synthetic/status`    | Synthetic probing | Called by `guardian_slo.yaml`. |
| `GET /api/v1/guardian/<id>`| Retrieve judgment + manifest | Requires service-to-service mTLS + RLS. |
| `POST /api/v1/guardian/quarantine` | Manual quarantine/unquarantine | Workers call to quarantine dependent artifacts. |
| `POST /guardian/detect-and-mask` | Span detection + masking | Returns `{detected_entities[], masked_spans[], provider_flags[], judgment}` with deterministic UUIDv7 span IDs. |
| `GET /guardian/policy`     | Retrieve effective policy bundle metadata | Outputs `{policy_bundle_id, masking_defaults[], restoration_intents[]}` for UI/workers. |
| `POST /guardian/judgments:enqueue` | Administrative replay (internal tooling) | Idempotent on `{resource_urn, reason}`; reuses submission bus; audited under `ops/guardian/batch_submit.jsonl`. |
| `POST /vault/detokenize`   | Restore masked spans (Compose/Signer only) | Requires `guardian_judgment_id`, purpose, and mTLS; never logs plaintext. |

### 4.4 Detection & masking payloads (binding)

- Guardian records span-level evidence and masking metadata using deterministic UUIDv7 identifiers so reruns reconcile reliably.
- Canonical field definitions, validation rules, and the reference JSON example reside in Appendix C (binding) to keep this section focused on contract highlights.
- Payloads always link to policy context (`policy_context_digest`), masking profiles, and vault namespaces so Compose/Signer can restore spans when policy allows (`POST /vault/detokenize`). Guardian persists the evidence in `guardian_span_detection`, emits summarized annotations for reviewers, and stores the full manifest snapshot with `guardian_judgment_history` rows.

### 4.5 Advisory signals & SSE events (informative)

- Provider telemetry (speech/LLM safety APIs) lands in `guardian_provider_flags[]`; severe categories Guardian missed elevate the outcome to WARN (`PROVIDER_CRITICAL_HINT`) and auto-file detector gap tickets.
- SSE/Audit events `GUARDIAN.JUDGMENT.{PASS|WARN|BLOCK|WAIVED}` carry `guardian_judgment_id`, reason codes, waiver IDs, `settings_snapshot_sha256`, and references to upstream findings. Portals invalidate deliverables when Guardian revokes or quarantines an artifact.
- Manual review mode (RB-GUARD-001) pauses submissions; staff record interim decisions as `MANUAL_GUARDIAN_JUDGMENT` artifacts that Guardian reconciles once service health returns.

### 4.6 Review integration & audit writes (binding)

- Reviewer actions (`approve`, `changes`, `quarantine`, `waive`) round-trip through Guardian so the service remains the canonical history authority. Platform APIs call `POST /guardian/quarantine`, `POST /guardian/review-actions`, and `POST /guardian/judgments:enqueue` on behalf of reviewers to persist `{guardian_judgment_id, artifact_id, org_id, actor_id, action, reason_codes[], waiver_id?, notes}` entries.
- Guardian writes every decision to `guardian_judgment_history` with deterministic UUIDv7 IDs, preserving prior verdicts even when artifacts re-enter `PENDING_JUDGMENT`. Replays with matching `{artifact_id, content_sha256}` reuse the latest record, while new hashes create a fresh entry so history stays append-only.
- Manual and automated decisions both emit SSE/audit events (`GUARDIAN.JUDGMENT.*`) containing the same identifiers the workflow service uses for manifests, approval UIs, and downstream runbooks. Client code MUST rely on these IDs instead of synthesizing review metadata.
- Reviewer console integrations (`/guardian/review-actions`) attach structured comments and span references to history rows; Guardian enforces that the referenced artifact version matches the submitted `expected_version` before accepting the action.
- Guardian exposes read-only helpers (`GET /api/v1/guardian/<id>`, `GET /api/v1/guardian?artifact_id=`) guarded by service-to-service RLS so downstream analytics and runbooks can surface the latest review outcome without bypassing the canonical store.

---

## 5) Policy context & configuration (binding)

- **PolicyContext:** Guardian requires deterministic inputs describing residency, HIPAA, SPI, waiver flags, allowed regions (`regions.allowlist.compute|storage|vector`), retention settings, and forbidden pattern catalogs.
- **Settings keys:**
  - `guardian.queue.backlog_alert_minutes` (default 5).
  - `guardian.queue.submission_timeout_seconds` (default 300).
  - `guardian.judgment_slo_ms` (default 300000) — docs/ops dashboards track adherence; manual overrides require Architecture/Security sign-off.
  - `guardian.rules.version` — identifies the active policy bundle version evaluated per judgment.
  - `privacy.hipaa.enabled`, `privacy.hipaa.phi_detection.strict_mode`, `privacy.hipaa.phi_detection.rescan_hours`.
  - `privacy.spi.retention_days`, `privacy.spi.residency`.
  - `compose.policy.forbidden_patterns[]` (consumed during deliverable checks).
  - `org.guardian.pre_operator_gates[]` — artifact classes hidden from operators until Guardian PASS/WARN.
  - `review.mode` / `review.approval_type.default` — Guardian honors skip modes by promoting CDs to `QUEUED_FOR_REVIEW`/`APPROVED` only when skip toggles active; defaults require human approval.
- **Residency enforcement:** Guardian rejects submissions outside org allowlists and stamps `RESIDENCY_POLICY_BLOCK` audit events; waivers recorded via App.O workflow.
- **HIPAA mode:** Requires WebAuthn enforcement, Guardian PHI quarantine, and evidence-store redaction toggles. Guardian blocks PHI artifacts until HIPAA policies confirm enablement.
- **Pipeline defaults:** System scope bundle `config/guardian_defaults.json` seeds Guardian/Settings defaults during environment bootstrap; `agents.pipeline.definitions[]` enumerates agent pipelines Guardian expects to gate (`transcription`, `analyze`, `compose`, assistants, etc.).

---

## 6) Observability & SLOs (binding)

### 6.1 Metrics

| Metric                               | Description |
| ------------------------------------ | ----------- |
| `guardian_judgment_latency_seconds`  | Distribution of evaluation latency; SLO ≤ 5 minutes P95. |
| `guardian_cleared_ratio`             | Ratio of PASS/WARN/WAIVED to total judgments. |
| `guardian_pending_total`             | Queue depth derived from `guardian_submission_queue`. |
| `guardian_pending_oldest_seconds`    | Age of oldest pending submission; alerts at `guardian.queue.backlog_alert_minutes`. |
| `guardian_submission_timeout_total`  | Worker watchdog count when Guardian exceeds `submission_timeout_seconds`. |
| `guardian_enqueue_conflict_total`    | Idempotency conflict counter. |
| `guardian_policy_block_total`        | BLOCK outcomes by reason code. |
| `guardian_parent_block_total`        | Child artifacts blocked due to parent quarantine. |
| `guardian_quarantine_false_positive_total` | Recovered quarantines with same hash; governance tracks ≤ 5 % objective. |
| `review_queue_backlog_total` / `review_queue_oldest_seconds` | Downstream readiness; alerts coordinate with Guardian backlog. |

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

---

## 7) Operations & runbooks (binding)

*Purpose: Summarize Guardian operational posture and direct responders to the canonical runbooks that govern action.*\\
*Contract: Any edit to Guardian runbooks or incident triggers MUST update Appendix B to keep this document authoritative.*\\
*Observability: Guardian SLO dashboards (metrics in §6.1) and audit streams (§6.2) remain the single source for responder context.*

- Primary runbooks — RB-GUARD-001 (SLO breach), RB-GUARD-QUAR (quarantine spike), RB-GUARD-QUEUE (submission backlog) — are maintained in Appendix B (binding). Step-by-step triage and decision trees live there to keep the main flow concise.
- Manual review checklists live in Appendix B.1; responders reference them alongside this specification.

### 7.1 Operational posture

- Guardian on-call rotations monitor `guardian_judgment_latency_seconds`, `guardian_pending_total`, and `guardian_policy_block_total` to confirm the 99.9% availability / ≤ 5 minute P95 latency commitments.
- Queue submission health depends on Celery worker heartbeats and Settings/LPE dependencies; Appendix B.3 describes how to remediate backlog growth while preserving auditability.
- Quarantine volume and waiver approvals follow Appendix B.2, keeping manifests and waiver artifacts in lockstep with Security/Architecture approvals.

### 7.2 Incident triggers

- `alert_guardian_queue_stale` (Grafana) fires when backlog age exceeds `guardian.queue.backlog_alert_minutes`; responders follow Appendix B.3.
- `guardian_policy_block_total` spikes or synthetic job failures (`guardian_slo.yaml`) escalate via Appendix B.1 and Appendix B.2, depending on whether latency or policy regression drives the alert.
- `PHI_DETECTION_DRIFT` incidents originate from classifier sampling (§6.3); Appendix B.2 covers containment and follow-up requirements.

### 7.3 Manual review mode

- When Guardian automation is paused, operations invoke Appendix B.1 to route artifacts through manual review queues and capture `MANUAL_GUARDIAN_JUDGMENT` records.
- Reconciliation jobs replay queued artifacts once health recovers; responders document the waiver/incident outcomes according to Appendix B.1 post-remediation notes.

---

## 8) Security & compliance (binding)

- **Residency:** Enforce allowlists defined per organization; cross-region waivers require dual approval and manifest stamping (`RESIDENCY_WAIVER_USED`).
- **HIPAA & SPI:** SPI inherits HIPAA-grade safeguards; Guardian enforces dual-review for SPI deliverables and immediate quarantine on PHI detection.
- **Auditability:** All judgments, waivers, and policy decisions stored immutably; exposures logged to `SPI_ACCESS_EVENT` when SPI artifacts accessed.
- **Tamper resistance:** Images signed via cosign; Guardian verifies provenance before enabling new releases.
- **Threat model coverage:** STRIDE scenarios include RLS bypass, policy poisoning, egress leakage, and SSE replay. Mitigations rely on OPA enforcement, signature verification, and synthetic monitors.

---

## 9) Dependencies & integration points (informative)

- **Agent pipeline:** Transcribe → Analyze → Compose; each stage parks outputs in `PENDING_JUDGMENT` until Guardian clears.
- **Portal & Notifications:** Client delivery blocked until Guardian PASS/WAIVED; WARN results add banners to portal artifacts.
- **Workers:** Celery workers enforce Guardian readiness before submitting to review or releasing deliverables; they also call `/api/v1/guardian/quarantine` for downstream cleanup.
- **Signer:** Digital signatures only attach to deliverables with latest Guardian PASS/WAIVED judgment.

---

## 10) Change management (binding)

- PRs modifying Guardian code or policy bundles MUST link to this document’s diff.
- Docs lint verifies Purpose/Breadcrumb scaffolding for every binding section; vocabulary lint ensures only canonical judgments appear in diffs.
- Architecture & Security approvals required before deploying policy changes affecting residency, HIPAA, or waiver behavior.

---

## Appendix A — Reference artifacts (informative)

- **Diagrams:**
  - `docs/diagrams/upload-guardian-approve-v1.mmd` (sequence of upload → Guardian → approval).
  - `docs/diagrams/residency-policy-enforcement-v1.mmd` (policy propagation and Guardian enforcement).
  - `docs/diagrams/data-lineage-v1.mmd` (artifact lineage through Guardian and Signer).
- **Examples:**
  - `docs/examples/lineage/transcript_to_compose.json` demonstrating manifest linkage with Guardian judgment IDs.
  - `docs/examples/lineage/compose_client.json` showing deliverable provenance.

This specification is the canonical source for Guardian behavior. Sections in the broader TDD now link here; future updates MUST originate here and propagate outward.

---

## Appendix B — Operations runbooks (binding)

*Purpose: Preserve the authoritative, step-by-step response guides referenced in §7 without overloading the main flow.*

### B.1 RB-GUARD-001 — Guardian SLO breach (binding)

- **Purpose:** Restore Guardian availability and route artifacts through manual review when automated judgments breach SLO.
- **Signals:** `guardian_judgment_latency_seconds` P95 > SLO, `guardian_submission_timeout_total` increasing, synthetic job failure (`guardian_slo.yaml`).
- **Triage (≤5 minutes):**
  1. Check `/readyz` and `/synthetic/status`; capture latency panels in Grafana (“Guardian SLO”).
  2. Confirm queue depth (`guardian_pending_total`, `guardian_pending_oldest_seconds`) and worker health (Celery heartbeat, pod restarts).
  3. Inspect recent deploys/settings (`guardian.rules.version`, Helm releases) for regressions.
- **Decision tree:**
  - *Service unhealthy*: place Guardian in manual review mode (pause submissions, notify ops). Operators record `MANUAL_GUARDIAN_JUDGMENT` artifacts while following the Appendix B.1 checklist.
  - *Compute exhaustion*: scale deployment (`kubectl -n platform scale deploy/guardian --replicas=<n>`), update HPA floor post-incident.
  - *Upstream dependency slowdown*: coordinate with LPE/Settings owners; consider throttling new submissions until latency stabilizes.
- **Post-remediation:**
  - Ensure `guardian_judgment_latency_seconds` P95 ≤ SLO for 2 consecutive scrapes and `guardian_submission_timeout_total` plateaued.
  - Clear manual review backlog by replaying queued artifacts once service healthy; annotate incident log with root cause and follow-ups.

### B.2 RB-GUARD-QUAR — Guardian quarantine handling (binding)

- **Purpose:** Diagnose QUARANTINED spikes without bypassing policy controls.
- **Linked alert:** `alert_guardian_quarantine_spike` (Grafana: Guardian SLO dashboard).
- **Signals:** Increased `guardian_policy_block_total{reason=...}` (e.g., `POLICY_FORBIDDEN_PATTERN`, `INTEGRITY_HASH_MISMATCH`, `SOURCE_NOT_APPROVED`); drop in `OPERATOR_PREP`/`QUEUED_FOR_REVIEW` backlog throughput.
- **Triage:**
  1. Filter Guardian dashboard by `reason_codes[]` and `org_id` to locate affected cohorts.
  2. Sample judgments from `guardian_judgment_history_secure`; confirm `guardian.rules.version` and `settings_snapshot_sha256` alignment.
  3. For `INTEGRITY_HASH_MISMATCH`, verify upload finalize and recompute hashes; for `SOURCE_NOT_APPROVED`, ensure upstream artifacts cleared.
- **Decision:**
  - `POLICY_FORBIDDEN_PATTERN`: engage Product/QA; adjust templates or policies; consider waiver only with dual approval.
  - `SOURCE_NOT_APPROVED`: instruct operators to remediate upstream artifacts or rebind inputs; Guardian enforces parent gating.
  - Region/debug issues: enforce settings fix, resubmit, and confirm waiver stamping (`RESIDENCY_WAIVER_USED`) where applicable.
- **Post-remediation:** track `guardian_cleared_ratio` recovery, log incident with counts per reason, and file rule-tuning tasks if false positives exceed thresholds.

### B.3 RB-GUARD-QUEUE — Guardian backlog watchdog (binding)

- **Purpose:** Restore submission throughput before `PENDING_JUDGMENT` artifacts stall.
- **Linked alert:** `alert_guardian_queue_stale` (Grafana: Guardian SLO dashboard).
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

### B.4 Manual review reconciliation (informative)

- Operators record manual decisions with manifest annotations while Guardian automation is paused.
- Reconciliation job replays queued artifacts once health recovers; incident owners capture waiver IDs, policy bundle hashes, and remediation tasks in the postmortem per Appendix B.1.

---

## Appendix C — Detection payload schema (binding)

*Purpose: Provide the canonical span-level schema and examples referenced in §4.4.*

### C.1 Field definitions

| Field              | Type        | Required | Description |
| ------------------ | ----------- | -------- | ----------- |
| `span_id`          | UUIDv7      | Yes      | Deterministic identifier for the detected span. |
| `type`             | String      | Yes      | Guardian entity classification (for example, `PHI.MRN`, `SPI.BIOMETRIC`). |
| `offset_start`     | Integer     | Yes      | Byte offset (UTF-8) marking span start. |
| `offset_end`       | Integer     | Yes      | Byte offset marking span end (exclusive). |
| `source`           | Enum        | Yes      | Detection tier identifier (`TIER0_SCHEMA`, `TIER1_REGEX`, `TIER2_ML`, `TIER3_CONTEXTUAL`). |
| `confidence`       | Float       | Conditional | Present for probabilistic sources; `null` omitted for deterministic hits. |
| `locale`           | String      | Yes      | BCP 47 locale for policy alignment. |
| `attributes`       | Object      | No       | Detector-specific metadata (checksum booleans, normalization hints). |
| `policy_context_digest` | String | Yes      | SHA-256 digest tying the span to the evaluated policy context. |
| `masking_profile`  | String      | Conditional | Applied masking profile name when Guardian masked the span. |
| `restorable`       | Boolean     | Conditional | Indicates whether detokenization is allowed under policy/waiver. |

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
