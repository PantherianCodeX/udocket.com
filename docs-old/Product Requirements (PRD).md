# **uDocket — Product Requirements Document (PRD)**

**Audience:** Engineering, Security, QA, Ops, Product
**Date:** 2025‑10‑16

---

## 0) Executive summary

**uDocket** converts interviews and scattered records into **organized, referenceable case summaries and documents**. The platform is **multi‑tenant**, **region‑aware**, and driven by **agentic workflows** with a compliance posture aligned (voluntarily) to **PIPEDA**, **SOC 2**, and **ISO 27001**.

**How it works**

1. **Intake & Interview** capture case metadata and narratives via jurisdiction‑aware questionnaires.
2. **Transcribe** normalizes audio and produces transcripts with integrity controls.
3. **Analyze** builds a shared context including intake, questionnaire, transcription, and uploaded files (Exhibits, finincials, emails, court documents, memos, etc.), extracts **Events, Timeline, Issues, Entities, Facts**, and identifies **Gaps** through lane‑level QA and revision.
4. **Compose** writes **Client** and **Lawyer** documents by section with QA gates: **Structure, Policy, Factuality**.
5. **Assembly, Review, Delivery, Client Signoff**, and **Retention/Destruction** complete the lifecycle.
6. **Guardian** **gates artifact release**: an artifact is usable by downstream stages **only if released by Guardian**.
ntegrations, multilingual outputs.

---

## 1) Product goals & success metrics

### Goals

* Deliver **lawyer‑ready** and **client‑ready** documents with minimal staff effort.
* Guarantee end‑to‑end **traceability & integrity** (versioning, hashing, auditability).
* Enforce **per‑organization regional restrictions** across data processing and storage.

### Success metrics (tracked; no targets in PRD)

* Turnaround from audio upload to **Guardian‑released** artifacts.
* **Guardian** first‑pass rate at artifact release.
* Number of **correction loops** per case.
* Intake completion and jurisdiction‑validation pass rates.
* Review timeliness.
* Integrity issues detected (hash mismatches quarantined).
* Signature verification success rate.

---

## 2) Personas & roles (RBAC)

* **SysAdmin** (system‑wide): global tenancy configuration, policy templates, reference governance, regional restrictions, break‑glass.
* **Admin** (organization): tenant configuration (regions, providers, storage), policy authoring/approvals, quotas, branding.
* **Manager** (organization): workload management, assignments, escalations; approves reviews per org policy.
* **Operator** (organization): runs workflows (intake, interview, uploads, jobs), proposes edits.
* **Reviewer** (organization): approves edits, analysis outputs, composed documents, and assembled documents.
* **Auditor** (system, read‑only): can access artifacts, audit logs, and Guardian decisions.
* **Client** (organization): receives deliverables, requests corrections, provides signoff.
* **External Counsel** (organization): optional recipient for secure delivery.

**RBAC principles**

* Field‑ and object‑level permissions; strict per‑tenant data isolation.
* **Guardian may auto‑demote** roles for policy violations (with audit).
* **Break‑glass** actions require re‑authentication, justification, and are fully audited.

---

## 3) High‑level scope

Full lifecycle (Steps 1–11); versioning & hashing; artifact model; Guardian‑gated artifact release; audit logs; reference engine; questionnaire; transcription (batch); real-time transcription; exhibits, court documents, financials, emails, memo ingestion (for analyze); analyze (transcript/intake/questionnaire); compose; assembly; final review; delivery; client signoff; retention & destruction with signed certificates; settings; notifications; reporting; client portal, e-filing integrations, multilingual input/output.

**Non‑functional outcomes**

* **High availability** for staff‑facing journeys.
* **Horizontal scalability** for case volume and long‑running work.
* **Regional compliance:** all processing and storage honor per‑organization region allowlists and fail closed on non‑compliance.

---

## 4) End‑to‑end lifecycle & stage requirements

**Core release rule:** When any stage **creates an artifact**, that artifact must be **reviewed by Guardian**. Only **Released** artifacts can be consumed by downstream stages. Artifacts not released are **quarantined** and unavailable downstream.

### 4.1 Step 1 — Intake

* **Objective:** Capture parties, court, division, **representation type** (including **Legal Aid** and **Pro Bono** as first‑class types), deadlines; validate against jurisdiction rules.
* **Identifiers:** Case, Organization, User, Attachments receive **UUIDs** at creation.
* **Outputs:** Validated case record; intake artifacts; consent records when required.
* **Guardian:** Intake artifacts must be **Released** before use elsewhere.
* **Quality signals:** First‑pass validation rate; missing fields analysis.

### 4.2 Step 2 — Interview (Questionnaire workspace)

* **Objective:** Run jurisdiction‑aware questionnaire; capture notes; prepare audio inputs.
* **Questionnaire:** Layerable (global → jurisdiction → division → organization); human review for AI‑assisted edits.
* **Outputs:** Interview log artifacts; gap list.
* **Guardian:** Interview artifacts must be **Released** before use elsewhere.

### 4.3 Step 3 — Transcribe

* **Objective:** Normalize audio; produce transcript with speaker separation where possible; compute and store **SHA‑256** for all files.
* **Outputs:** Transcript text, speaker map (if available), operational metadata, file hashes.
* **Integrity:** Hashes re‑validated on read; mismatches → quarantine.
* **Guardian:** Transcription artifacts must be **Released** before analysis.

### 4.4 Step 4 — Analyze (agentic pipeline)

* **Objective:** From transcript + intake + questionnaire, produce structured **Events, Timeline, Issues, Entities, Facts**, and **Gaps** with QA report.
* **Process (outcome‑level):**

  * **Context Builder** compiles shared context.
  * Five **parallel lanes** produce artifacts.
  * Each lane runs **QA**; on fail, a **revision loop** executes up to an organization‑configured maximum.
  * **Final QA** checks cross‑lane cohesion; **Gaps** are recorded.
  * **Artifact creation** completes once QA passes.
* **IDs:** Derived analysis items use **deterministic IDs** stable across identical inputs.
* **Guardian:** Analyze artifacts must be **Released** before Compose can use them.
* **Outputs:**
  * **Lane artifacts:** Events, Timeline, Issues, Entities, Facts (artifacts).
  * **Gaps artifact:** Cross-lane gaps summary (artifact).
  * **QA_logs:** Human-readable Markdown plus machine-readable JSON listing lane QA findings and revision directives. Persisted with the Analyze job and linked to produced artifacts for reviewer visibility and auditability.

### 4.5 Step 5 — Compose (agentic pipeline)

* **Objective:** Generate **Client** and **Lawyer** documents by **sections**, in parallel, from **Released** Analyze artifacts.
* **Process (outcome‑level):**

  * **Context Builder** compiles inputs for writing.
  * **Parallel section writers** produce content.
  * Per‑section **QA**: **Structure**, **Policy**, **Factuality**; failing sections enter a **revision loop** up to an organization‑configured maximum.
  * **Artifact creation** completes when all sections pass QA.
* **Guardian:** Compose artifacts must be **Released** before Assembly can use them.
* **Outputs:**
  * **Section artifacts:** Per-section content in JSON for Client and Lawyer (artifacts).
  * **QA_logs:** Per-section QA results for Structure / Policy / Factuality in Markdown + JSON. Not an artifact; stored with the Compose job and linked to section artifacts.

### 4.6 Step 6 — Document Assembly

* **Objective:** Substitute **Released** Compose sections into jurisdiction/organization/brand templates; produce finalized document files; compute hashes.
* **Outputs:** Client and Lawyer documents (e.g., DOCX/PDF) with metadata and versions.
* **Guardian:** Assembled document artifacts must be **Released** before Final Review.

### 4.7 Step 7 — Final Review

* **Objective:** Human review of **Released** assembled documents; escalation rules as defined by organization policy.
* **Outputs:** Approve/reject with rationale; audit entries.

### 4.8 Step 8 — Delivery

* **Objective:** Deliver **Released** documents to Clients and Representatives via approved channels; record delivery receipts (views/downloads).
* **Regional compliance:** Delivery must honor region allowlists.

### 4.9 Step 9 — Corrections Loop (optional)

* **Objective:** Capture client factual corrections; re‑run Analyze/Compose as needed.
* **Traceability:** New versions and diffs recorded; replacement artifacts must be **Released** before they supersede prior versions.

### 4.10 Step 10 — Client Signoff

* **Objective:** Client reviews **Released** documents and **signs digitally**.
* **Artifact:** A **signature certificate** (PDF/A with embedded digital signature and machine‑readable manifest) is produced.
* **Guardian:** The signature certificate must be **Released** and linked to the case.

### 4.11 Step 11 — Retention & Data Destruction

* **Objective:** Enforce per‑organization retention (default **90 days**, adjustable), early‑destruction requests, and operational purges.
* **Artifact:** A **destruction certificate** (PDF/A with embedded digital signature and manifest) is produced; upon **Release**, deletion proceeds and deletion receipts are recorded.
* **Verification:** Hash manifest and deletion receipts are linked to the case record.

---

## 5) Domain & data model (product constraints)

* **Universal UUIDs:** Case, Organization, User, Artifact, Job, Transcript, Document, Event, TimelineItem, Entity, Issue, Fact, GuardianDecision, AuditEvent, Template, Questionnaire, ProviderCredential, Settings.
* **Deterministic derived IDs:** Analysis‑derived items must receive deterministic identifiers that remain stable for identical inputs.
* **Hashing:** **SHA‑256** for every file (inputs & outputs); re‑validate on load; mismatches are quarantined and not releasable.
* **Artifacts:** Immutable and versioned; each includes provenance (who/when, job/subtasks, inputs, hashes, approvals).
* **QA_logs**: Immutable, versioned job-scoped logs (Markdown + JSON) linked to their source job and the artifacts they assess. Discoverable in Review, exportable to staff, never delivered to clients.

---

## 6) Reference Engine & Questionnaire (international)

* **Catalog layering:** **Global → Country → Province/State → Court Level/Division → Organization overrides**, with versioning and effective/deprecation dates.
* **Provenance:** Source reference, fetch timestamp, and integrity checksum retained; **back‑compat mapping** for renamed courts.
* **Validation:** Jurisdiction‑specific validation rules applied during Intake and Interview.
* **Questionnaires:** Layered seeds; human‑in‑the‑loop for AI‑suggested edits; versioned per organization and per case when instantiated.
* **Maintenance:** Scheduled discovery of authoritative changes produces review tasks; region allowlists must be honored.

---

## 7) Transcription, Editing, Versioning

* **Transcription:** Audio normalization; transcript creation; optional speaker identification/separation; integrity hashing for all files.
* **Manual editing:** Side‑by‑side diffs; inline comments; **paragraph‑level playback**; new versions with review.
* **AI‑assisted editing:** Co‑editing suggestions recorded; human approval required.
* **Guardian:** Any new or edited transcription artifacts must be **Released** to be used downstream.
* **Versioning:** Version history and diffs available for text artifacts; quarantine dashboards for integrity violations.

---

## 8) Review & Guardian

* **Review module:** Work queues, escalations, delegation, rationale capture, and full auditability.
* **Guardian (scope in PRD):**

  * **Single responsibility:** **Gate artifact release**.
  * **Operation:** Each artifact is marked **Draft** when created; Guardian either **Releases** or **Quarantines** it.
  * **Downstream rule:** Only **Released artifacts** are eligible for consumption by subsequent stages.
  * **Review worklists** surface QA_logs alongside their related artifacts; filters by lane/section and severity.
  * **Guardian** continues to gate only artifacts. Presence of QA_logs is required for internal QA completeness but is not a release gate.

---

## 9) Unified lifecycle & states

**Draft → Guardian Review → Released → Consumed downstream → (optional) Superseded → Archived → Destruction Certificate Draft → Guardian Review → Released → Data Deleted.**

* All state changes create **auditable events**.
* Quarantined artifacts cannot be consumed; release requires Guardian approval (or break‑glass with justification).

---

## 10) Digital Signature Service

* **Purpose:** Client signoff, destruction certificates, consent records, and (optionally) reviewer approvals.
* **Format requirement:** **PDF/A** with embedded digital signature and machine‑readable **manifest** (signer identity binding, timestamp, case/artifact UUIDs, file hashes).
* **Verification:** In‑product verification and exportable verification report.
* **Durability:** Signatures must remain verifiable over time; secure key management and rotation supported.

---

## 11) Notifications & communications

* **Channels:** Email, SMS, and in‑app messaging permitted by the organization’s region allowlist; non‑compliant options are blocked.
* **Templates:** Localizable and tenant‑brandable; sensitive data redaction rules applied.
* **Evidence:** Delivery receipts (including view/download events) recorded for audit.

---

## 12) Security, privacy, and compliance

* **Framework alignment:** PIPEDA, SOC 2, ISO 27001 principles mapped to platform features and processes.
* **Access control:** Strong authentication, MFA for privileged roles, delegated administration, periodic access reviews.
* **Regional compliance:** Per‑organization **region allowlists** enforced for processing and storage; non‑allowed operations fail closed.
* **Integrity & confidentiality:** TLS in transit; encryption at rest; **SHA‑256** integrity for files; managed secret storage with rotation policy.
* **Breach response:** Severity classification and documented triage/contain/eradicate/recover/notify processes; jurisdictional notification timelines observed.
* **Auditing:** Append‑only design where feasible with PII redaction; retention at least equal to case retention; exportable audit packages.

---

## 13) Observability & logging

* **Requirements:**

  * Capture operational metrics for jobs and pipelines, Guardian decision latency/throughput, delivery success, and integrity incidents.
  * Provide tenant‑scoped and system‑wide dashboards.
  * Maintain actionable alerts and runbooks for common incidents (backlogs, provider degradation, integrity quarantines).
  * Use structured logs and correlation identifiers to trace work across stages.

---

## 14) Search & knowledge retrieval

* **Baseline:** Full‑text search across artifacts, transcripts, events, and timeline entries, strictly tenant‑scoped.
* **Discovery exports:** Authorized users can export search results with provenance for legal review.
* **Future‑ready:** Semantic search may be introduced after compliance evaluation (not in this PRD’s scope).

---

## 15) Reporting & analytics

* **Operational reports:** Throughput, backlogs, review timeliness, Guardian decisions, correction cycles.
* **Compliance reports:** Retention and destruction execution, access reviews, and policy changes.
* **Cost awareness:** Utilization summaries by organization for capacity planning.

---

## 16) Experience standards (UX)

* **Accessibility:** Conform to WCAG 2.2 AA for all staff‑ and client‑facing surfaces.
* **Real‑time feedback:** Users see live job progress and review states without manual refresh.
* **Editing ergonomics:** Rich diffing for text, time‑coded **paragraph playback** for transcripts, and clear approval workflows.
* **Error clarity:** Failures express impact, next steps, and links to remediation.

---

## 17) Job & workflow requirements

* **State visibility:** Jobs expose clear states (Queued, Running, Succeeded, Failed, Quarantined) and progress.
* **Resumability:** Long‑running work can pause/resume if dependencies degrade; automatic resumption once healthy.
* **Idempotency & partial re‑runs:** Re‑runs do not duplicate side effects; lanes/sections can re‑run independently when applicable.
* **Gating:** Transitions depend on availability of **Released artifacts** and required approvals.

---

## 18) APIs & integrations (product policy)

* **Programmatic access:** Provide documented interfaces to retrieve case status, artifacts, and audit extracts; event notifications for status changes.
* **Safety:** All programmatic access is tenant‑scoped and verifiable; event notifications are signed; rate limits protect system stability.
* **Evolution:** External access is versioned to avoid breaking existing consumers.

---

## 19) Testing & quality

* **Automated assurance:** Comprehensive automated tests across unit, integration, end‑to‑end flows (Intake → Delivery → **Client Signoff** → Destruction).
* **Agentic reliability:** Contracts for Analyze and Compose verify lane/section outputs, QA loops, revision limits, and **determinism** (same inputs → same outputs/IDs).
* **Performance & scale:** Load tests for high job concurrency and large audio volumes; backpressure handling validated.
* **Security:** Tests cover authorization boundaries, tenant isolation, integrity checks, and secret handling.

---

## 20) Acceptance summaries (by critical area)

* **Residency & internationalization:** All processing and storage honor per‑organization region allowlists; non‑permitted operations fail closed; court catalogs are layered and versioned with provenance.
* **Guardian (simple, required):** Artifacts are **Draft** until Guardian **Releases** them; only **Released** artifacts can be consumed downstream; quarantined artifacts are inaccessible to later stages.
* **Integrity & traceability:** Every file is **SHA‑256** hashed on creation and re‑validated on read; mismatches are quarantined; all edits create new versions linked by provenance.
* **Analyze/Compose pipelines:** Context building; five‑lane Analyze with QA/revision and Final QA; Compose with **Structure/Policy/Factuality** QA and revision; partial re‑runs supported; only **Released** outputs progress.
* **Representation model:** Self Representation, Lawyer, Legal Aid, Pro-bono, Paralegal, and Other. Representation influences questionnaires and document tone.
* **Client Signoff:** Signoff produces a **PDF/A** certificate with digital signature and manifest; verification is available in‑product and as an export.
* **Security & compliance:** Access controls, regional enforcement, encryption, breach processes, and auditable operations align to PIPEDA/SOC 2/ISO 27001 principles.
* **Quality:** The product is covered by automated tests across layers, with determinism checks for agentic outputs and complete end‑to‑end scenarios.

---

## 21) Stage‑level acceptance criteria (outcome‑focused)

**Intake**
    - Required fields pass jurisdiction validation; representation type captured; case UUID assigned; intake artifacts **Released**.

**Transcription**
    - Audio normalized; transcript and (if available) speaker separation produced; hashes stored; hash re‑validation passes; transcription artifacts **Released**.

**Analyze**
    - Lane artifacts + Gaps artifact created and submitted to Guardian. QA_logs recorded (Markdown + JSON) and linked to produced artifacts; all QA pass conditions satisfied..

**Compose**
    - All sections pass QA; section artifacts submitted to Guardian. QA_logs recorded per section and linked for review.

**Assembly**
    - Final documents render successfully; metadata and hashes present; assembled document artifacts **Released**.

**Final Review**
    - Reviewers approve **Released** documents with rationale; approvals are auditable.

**Delivery**
    - Only **Released** documents are delivered; delivery receipts are recorded.

**Client Signoff**
    - Digital signature captured; verification report available; signature certificate artifact **Released** and linked to the case.

**Destruction**
    - Eligibility confirmed; **destruction certificate** created and **Released**; deletion receipts stored; case marked accordingly.

---

## 22) Centralized Settings

**Purpose:** Single source of truth for system, organization, and case-scoped settings that control behavior across all modules. Settings are versioned, audited, and enforce per-org **region allowlists**. They are distinct from secrets.

**Scope**
    - **Hierarchy & precedence:** `System Defaults → Organization → Case (optional)` with explicit override rules. No user-level overrides.
    - **Domains:** Regions/Residency, Notifications (channels/providers/templates), Guardian policy selection, Analyze/Compose retry limits, LLM/provider knobs, Retention periods, Template selection defaults, Feature flags (enable/disable modules), Quotas (concurrency, storage), Client portal options, Signature policies.
    - **Change control:** Draft → Review → Activate, with effective date/time and rollback to prior version.
    - **Validation:** Type-safe (boolean, integer, enum, duration, region code, URL, JSON schema) with cross-field rules (e.g., if email is enabled, at least one provider must be configured).
    - **Auditability:** Every change captures who/when/where, old/new values, justification, and approval (if required).
    - **Discovery:** Read-only views for Operators and Reviewers showing effective values that impacted a job or artifact.

**RBAC**
    - **SysAdmin:** Define system defaults; manage global setting definitions.
    - **Admin:** Create/change organization settings; schedule activation; manage feature flags and quotas.
    - **Manager/Reviewer/Operator:** Read effective settings; cannot modify.
    - **Auditor:** Read all versions and change history.

**Behavior**
    - **Consistency:** Running jobs use a snapshot of effective settings at job start.
    - **Blocking:** Invalid settings fail closed (e.g., non-allowed region), surfacing clear errors.
    - **Export/Import:** Admin can export org settings bundle and import into another org (with validations).

**Acceptance**
    - Effective value resolution follows precedence.
    - Changes are versioned, auditable, and can be rolled back.
    - Jobs record the settings snapshot used.
    - Region allowlists are enforced platform-wide.

---

## 23) Document & Data Ingestion (non-audio)

**Purpose:** Intake non-audio materials (exhibits, court documents, financials, emails, memos) to produce **Released** artifacts consumable by Analyze.

**Inputs & Outputs**
    - **Inputs:** PDFs, images, office docs, emails (RFC 5322/EML), spreadsheets.
    - **Outputs (artifacts):**
        - `EXHIBIT_RAW`, `EXHIBIT_TEXT` (OCR/parse),
        - `COURT_DOC_RAW`, `COURT_DOC_TEXT`,
        - `EMAIL_RFC822`, `EMAIL_TEXT`, `EMAIL_ATTACHMENTS`,
        - `FINANCIALS_RAW`, `FINANCIALS_TABLE`,
        - `MEMO_TEXT`.

**Requirements**
    - OCR and layout retention for PDFs/images; table extraction for financials; email parsing with attachments; de-duplication by hash; chain-of-custody metadata.
    - Per-org file type allow/deny lists from **Centralized Settings**.
    - All outputs are **Guardian-gated**; only **Released** artifacts flow to Analyze.

**Acceptance**
    - Each upload yields hashed raw artifact and a parsed/text artifact.
    - Emails preserve headers/attachments and produce structured text/attachments artifacts.
    - Financial tables extracted to machine-readable form.
    - All artifacts pass Guardian to be available to Analyze.

---

## 24) Client Portal

**Purpose:** Client-facing experience for delivery, corrections, and signoff.

**Capabilities**
    - View **Released** deliverables; submit factual corrections; track status; perform digital signoff; download verification reports.
    - Device/browser fingerprint captured at signoff (stored in manifest).
    - Region compliance enforced by **Centralized Settings**.
    - Notifications route client back to portal for any actions.

**RBAC**
    - **Client:** Access own case artifacts and actions.
    - **External Counsel:** Access granted deliverables.
    - **Admin/Manager:** Configure portal preferences per org.

**Acceptance**
    - Only Released artifacts are visible.
    - Signoff produces a signature certificate artifact and links to the case.
    - Corrections create reviewable items and, once accepted, trigger new Analyze/Compose.

---

## 25) Legal Hold

**Purpose:** Prevent destruction for cases or artifacts under hold.

**Behavior**
    - Legal Hold flag at **case** and **artifact** levels.
    - Destruction workflows skip held items and surface rationale.
    - Hold requires reason, owner, and review cadence; all changes are audited.

**Acceptance**
    - Destruction jobs exclude held items.
    - Hold state and rationale are visible in case overview.

---

## 26) Quotas & Metering

**Purpose:** Enforce per-org limits and provide visibility.

**Quotas**
    - Concurrent jobs, daily transcription hours, storage footprint, notification volumes.

**Metering**
    - Counters and usage windows surfaced to Admin; overages block new submissions with clear errors.

**Acceptance**
    - Quotas enforced consistently across job types.
    - Usage metrics available per org.

---

### Appendix A — Data classification & retention defaults

* **Default retention:**
  * **90 days** per organization setting (case‑wide), with early destruction on request; audit logs retained at least as long as case data and designed to minimize personally identifiable information.
* **Certificates:**
  * No statutory format is required; uDocket standardizes on **PDF/A with embedded digital signature and manifest** for signoff and destruction certificates.

### Appendix B — Representative domain enums

```text
RepresentationType = {
  SELF,
  PRIVATE_COUNSEL,
  LEGAL_AID,
  PRO_BONO,
  PARALEGAL_OR_ADVOCATE,
  OTHER
}
```
