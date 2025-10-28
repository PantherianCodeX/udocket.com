---
title: uDocket — Technical Design Document
subtitle: Platform Architecture & Compliance Specification
author:
  - uDocket Platform Architecture Team
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-25
owners:
  - Platform Architecture
  - Security Engineering
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
      .md-typeset figure.full-width-diagram {
        display: block;              /* no longer a table */
        width: 100%;
        margin: 2rem 0;
        text-align: left;
      }

      .md-typeset figure.full-width-diagram img {
        display: inline-block;
        max-width: 95vw;             /* cap it to the viewport */
        width: auto;                 /* honor the SVG’s intrinsic size */
        height: auto;
      }

      .md-typeset figure.full-width-diagram figcaption {
        display: block;              /* regular block, not a caption */
        margin-top: 0.75rem;
        text-align: left;
      }
    </style>
  - <header class="page-header">uDocket — Technical Design Document <br> 
    Platform Architecture & Compliance Specification</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page 
    <span class="page-number"></span> of <span 
    class="page-count"></span></footer>
---

______________________________________________________________________

## Document controls

| Field          | Value |
| -------------- | ----- |
| Version        | 0.1-draft |
| Status         | Implementable |
| Last updated   | 2025-10-28 |
| Primary owners | Platform Architecture, Security Engineering |
| Approvers      | Architecture Steering Committee; Security Review Board |
| Reviewers      | QA Engineering Lead; SRE Manager |
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

## Canonical vocabulary (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/artifacts/status.py`, Tests `tests/platform/artifacts/test_status_vocab.py::test_all_statuses_linked`, Observability Grafana “Docs Quality – Vocabulary Drift”.

*Purpose: Provide single-source wording for artifact classes, statuses, and Guardian mappings so specs, code, and UI stay aligned.* *Contract: Any change to artifact classes, statuses, or Guardian judgment mappings MUST update §5.2.1–§5.2.3 and this section in the same patch; other sections link back instead of restating tables. See Appendices: Glossary and Status Mapping for single‑source definitions.* *State transitions: Defined exclusively in §5.2.2 (statuses) and §5.2.3 (Guardian mapping).* *Failure modes & retries: `scripts/docs/lint_docs.py --check-template` now fails when a normative section lacks Purpose/Breadcrumbs scaffolding; `scripts/db/lint_status_column.py` blocks unknown status strings; CI job `lint-artifact-vocabulary` scans diffs for stray status/judgment terms.* *Observability: Docs lint metrics (`docs_template_missing_total`, `docs_vocabulary_drift_total`) feed the Docs Quality dashboard; Guardian and approval metrics remain unchanged.* *References: §5.2, §5.4.1, §7.1, §10.3.2, App.A, App.I.*

### Artifact classes (authoritative definitions)

| Class                 | Key    | Canonical definition                                      | Visibility          |
| --------------------- | ------ | --------------------------------------------------------- | ------------------- |
| Source Asset          | **SA** | Raw, immutable inputs we ingest.                          | Staff (scoped)      |
| Work Product          | **WP** | Internal derived data never exposed to clients.           | Staff only          |
| Candidate Deliverable | **CD** | Human-readable draft that may be released after approval. | Staff reviewers/ops |
| Deliverable           | **DL** | Approved, signed, client-visible document.                | Staff + client      |
| Auxiliary Record      | **AR** | Attestations/receipts that prove what happened.           | Auditors/admin      |

### Canonical statuses (link to §5.2.2)

- `STORED → PROCESSING → PENDING_JUDGMENT` (SA → WP/CD) with deterministic transitions enumerated in §5.2.2.
- Guardian PASS/WARN moves WP → `CLEARED_FOR_USE` and CD → `OPERATOR_PREP`; review queue states (`APPROVAL_REQUESTED`, `QUEUED_FOR_REVIEW`, `CHANGES_REQUESTED`) apply only to CDs.
- Deliverables follow `APPROVED → SIGNED → RELEASED → REVOKED → ARCHIVED → DELETED` and are subject to the ExclusiveSwap invariant in §5.4.1; transitions into `ARCHIVED/DELETED` only occur through the retention/erasure gate.

### Guardian judgments → statuses (link to §5.2.3)

| Judgment | WP next         | CD next       | Notes              |
| -------- | --------------- | ------------- | ------------------ |
| PASS     | CLEARED_FOR_USE | OPERATOR_PREP | default            |
| WARN     | CLEARED_FOR_USE | OPERATOR_PREP | banners            |
| BLOCK    | QUARANTINED     | QUARANTINED   | remediation/waiver |
| WAIVED   | as PASS         | as PASS       | dual approval      |

Guardian policy, risk tiers, and remediation flows continue in §5.2.3 and §7.1; other sections cite these tables instead of rephrasing them.

### Definition locks

- No new status or judgment names appear outside §5.2.2–§5.2.3 without an ADR update and a matching lint rule update; CI job `lint-artifact-vocabulary` blocks unknown terms in diffs.
- APIs emit events whose values are exactly the canonical statuses/judgments; payload schemas MUST reference this section instead of inventing aliases.
- Mapping tables live only in §5.2.3. Other sections reference them with `See §5.2.3 (canonical mapping)`.
- Binding breadcrumbs are mandatory for every normative/binding subsection; missing breadcrumbs fail `scripts/docs/lint_docs.py --check-template`.

______________________________________________________________________

## 0) Reading guide

- **Scope:** Entire platform lifecycle (design → operations → governance).
- **Structure:** Numbered sections with ≤3 levels of depth; appendices mirror section numbers for reference artifacts.
- **Cross-references:** Use `§<number>` for sections and `App.<letter>` for appendices.
- **LLM hint:** Each subsection starts with a one-line purpose statement before implementation details.
- **Maintenance:** Run `python scripts/docs/lint_docs.py` (or see `docs/README.md`) before submitting edits to keep references, formatting, and settings keys synchronized with the codebase.
- **Audit integration (2025-10-19):** This draft incorporates audit items for CCPA/CPRA coverage (§2.2, §14.2.1), automated LLM moderation (§8.4), and model version pinning/replay rules (§8.1, §8.5). Settings key coverage and traceability now live in [`../services/settings-registry.md Appendix A`](../services/settings.md#appendix-a-settings-key-map-traceability-index); CI blocks releases if parity ever drifts.
- **Doc change protocol:** Every PR that modifies regulated behavior (policy, residency, approvals, agents) must link to the corresponding TDD diff; Architecture/Security reviewers block merges when code and spec diverge. Appendix automation (settings map, API snippets) continues to evolve—when feasible, replace manual tables with generated outputs to minimize churn.

**Role-based quick start (binding)**\
Use this checklist to jump to the right sections on a first read:

| Stakeholder role           | Start here                                                                                                | Must-review highlights                                                      |
| -------------------------- | --------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Architecture / Security    | §3 (platform architecture), §4 (tenancy & access), §7 (Guardian/Signer), §12 (observability/DR)           | §3.8 residency, §4.4–§4.5 masking/RLS, §7.1 judgments, §12.5 resilience     |
| Engineering (agents & API) | §6 (agent ecosystem), §10 (APIs), App.D (artifact schemas)                                                | §6.2–§6.4 pipelines, §10.3 idempotency, Appendix F API contracts            |
| Product / Operations       | §1 (executive summary), §11 (UX), §14 (retention & compliance)                                            | §11.1 workspace/portal behaviors, §14.2 DSAR flows, §15 roadmap checkpoints |
| QA / Compliance            | §5 (lifecycle), §13 (testing & governance), App.K (controls map)                                          | §5.2 status vocabulary, §13.3 detection QA, §13.5 deployment gates          |
| SRE / Platform Ops         | §3 (infra context), §8 (LLM runtime), §12 (observability/DR), [Runbook catalog](../ops/runbooks/index.md) | §8.7 FinOps guard, §12.4–§12.6 DR & dashboards, `../ops/runbooks/index.md`  |

### Diagram usage standard

To keep visuals helpful and consistent:

- Embed a rendered Mermaid diagram when a section introduces a **core control flow, deployment topology, or data lineage** that spans multiple services (sequence/flowchart).
- Use **ER diagrams** when we describe shared persistence contracts or artifacts that other teams must extend (for example, §9 core domain entities).
- Produce **class diagrams** when detailing important service classes or agent orchestration objects whose inheritance/composition relationships benefit from a visual (limit to high-signal surfaces such as Guardian, Settings activation engine, or core agents).
- Reserve diagrams for bounded topics—avoid trying to capture the entire platform in a single chart; favor appendix references for deep dives (App.A/App.G).
- When behavior changes, update the `.mmd` source under `overview/tdd/diagrams/`, regenerate SVGs via `scripts/docs/render_mermaid.sh`, and ensure the affected TDD section still references the correct image.

## 1) Executive summary

### 1.1 Mission & problem statement

*Purpose: State why uDocket exists and which pain points it solves.*

- Deliver a secure, auditable case automation platform that converts unstructured inputs (audio, exhibits, staff notes) into consumable legal artifacts without sacrificing compliance.
- Replace ad hoc transcription and summarization processes that lack residency controls, approval gating, or defensible audit trails.
- Empower multidisciplinary users (intake, operators, reviewers, counsel) with coordinated workflows backed by deterministic settings and artifacts.

### 1.2 Solution overview

*Purpose: Summarize the end-to-end approach at one glance.*

- Web platform (Django + Channels) for staff/clients, Celery workers for long-running jobs, and dedicated Guardian & Signing services enforcing PASS/WARN/BLOCK/WAIVED judgments, OPERATOR_PREP gating, and digital seal policies.
- Agent pipeline: Transcribe → Analyze → Compose, each producing immutable artifacts under Guardian review, enriched with manifests and ops telemetry.
- Zero-trust foundation: mTLS between services, Postgres RLS with policy-driven RBAC, object storage with SHA-256 integrity, and centralized Settings snapshots for every job.
- Launch scale assumptions: first cohort targets ≈25 organizations with 3–5 active cases each, ~40 concurrent staff sessions, and ~150 queued jobs/hour across agents. The design budgets the web tier for 250 ms P95 read latency, Guardian judgments ≤5 minutes P95, Compose cycle time ≤45 minutes P95, and transcription throughput supporting 20 hours of audio per hour of wall-clock time under burst loads. Capacity reviews (see §12.5) validate these numbers and grow quotas linearly toward the 10× volume target called out in App.L benchmarks.

### 1.3 Out-of-scope items

*Purpose: Clarify boundaries to prevent scope creep.*

- No generic e-discovery, enterprise DMS migration tooling, or third-party redaction services; integrations focus on Azure Speech, selected LLM providers, and in-house signing.
- Hardware devices, telephony capture, and in-person interview tooling remain outside MVP scope (ingest assumes digital uploads).
- Bring-your-own model endpoints remain out of scope for this revision; platform-supported providers must be onboarded through the registry with residency and policy reviews documented in Appendix O.

### 1.4 Success metrics & KPIs

*Purpose: Define measurable signals for program health.*

- `transcription_cycle_time` ≤ 30 minutes P95 for batch jobs (case-ready transcript).
- ≥ 95% Guardian pass rate on first submission with \< 1% false negatives per quarter.
- FinOps: LLM spend per case maintained within org-defined monthly caps; ≥ 90% forecast accuracy.
- Platform reliability: Web/worker availability ≥ 99.5%, no Sev-1 incidents triggered by residency or RBAC violations.

### 1.5 Document readers & decision checkpoints

*Purpose: Identify stakeholders and when they must engage.*

- **Architecture & Security:** approve changes to principles, Guardian rules, and Settings service contracts.

- **Engineering leads:** align sprint plans with agent, API, and storage sections; sign off before major releases.

- **Product & Ops:** review executive summary and operations sections before customer onboarding waves.

- Trigger checkpoints: pre-production launch, regulator readiness reviews, significant provider changes, or artifact schema revisions.

- RACI assignments for each domain live in App.S and govern who signs off on changes or exceptions.

- **Source material:** `§1`, `§16` overview blurbs

- **Priority:** High (front-matter defines narrative used by PRD/TDD consumers)

### 1.6 Customer-facing SLAs

*Purpose: Publish external commitments distinct from internal SLOs and make escalation paths obvious to buyers and auditors.*

- **Availability:** 99.5 % rolling 30 day for staff UI/API; 99.0 % for client portal. Breaches trigger customer notice within 24 h and a public incident postmortem within 5 business days (`../ops/runbooks/index.md` templates).
- **Support response:** Severity 1 (production outage/legal exposure) acknowledged ≤ 1 hour, mitigated or workaround shared ≤ 4 hours; Sev 2 ≤ 4 hour acknowledgement, Sev 3/4 within one business day. Support queue owned by Platform Support with SRE on-call backup.
- **Restore targets:** RTO ≤ 1 hour for Postgres/object storage (see §12.4) and ≤ 4 hours for Guardian/Signer; RPO ≤ 15 minutes. Manual fallback playbooks in §12.10 describe degraded operations while restoration proceeds.
- **Escalation:** Customer SLA breaches escalate to Duty Manager + SRE on-call + Product within 30 minutes; regulators and contractual stakeholders notified per §12.3 templates. Decision log entries capture SLA breaches and remediation commitments (§15.3).

______________________________________________________________________

## 2) Core principles & constraints

### 2.1 Guiding principles (immutability, determinism, zero-trust)

*Purpose: Anchor architecture decisions to explicit tenets.*

- Artifacts are immutable, content-addressed, and versioned; objects flow deterministically from `STORED` → `PROCESSING` → `PENDING_JUDGMENT` → review.mode-dependent hops (`OPERATOR_PREP → APPROVAL_REQUESTED → QUEUED_FOR_REVIEW` when review is required) → `APPROVED`/`RELEASED` without mutating prior versions (see §5.2.5).
- Guardian gating: the service issues PASS/WARN/BLOCK/WAIVED judgments that gate operator visibility and drive the workflow service to move WP/CD out of `PENDING_JUDGMENT` into `CLEARED_FOR_USE`, `OPERATOR_PREP`, or `QUARANTINED`; downstream stages accept only `APPROVED` (or stronger) artifacts.
- Deterministic controls over non-deterministic LLM output: UUIDv7 row IDs, content fingerprints, namespace UUIDv5 derived IDs per §6.7.1, Settings snapshots, prompt/version capture.
- Zero-trust for every hop: deny-by-default RBAC, workload identities, enforced mTLS, and per-request DB GUC binding.
- Observability and auditability as first-class: every job/action emits structured telemetry with correlation IDs.
- Settings as a platform: a centralized Settings Service defines effective configuration (system/org/case), is versioned/audited, and snapshots embed into every job.
- Operational safety defaults: database sessions pin `search_path`, enforce timeouts, and fail closed when required RLS GUCs are missing.
- Real-time transport policy: SSE for one-way server→client status, Channels for bidirectional collaboration and controls.

### 2.2 Regulatory & contractual constraints (global residency, SOC2, privacy)

*Purpose: Spell out compliance rails enforced across the stack.*

- Data residency: compute, storage, and vector workloads must execute inside the region sets declared by each organization (`regions.allowlist.compute|storage|vector`). Defaults provide paired primary/secondary regions per jurisdiction (for example, `na-us-1` + `na-us-2`, `eu-central-1` + `eu-west-2`). Cross-region replication or failover outside the allowlist requires dual-approved waivers stamped in manifests and surfaced to Guardian.

- SOC 2 / ISO controls: change management, incident response, and logging mapped to specific sections (`§12`, `§12`, [`../services/settings-registry.md Appendix A`](../services/settings.md#appendix-a-settings-key-map-traceability-index)); mappings extend to PCI DSS logging, FedRAMP Moderate, and audit retention requirements surfaced in Appendix K.

- Privacy frameworks in scope: GDPR/UK GDPR, CCPA/CPRA, HIPAA (US/BAA-backed workloads), PHIPA, PIPEDA, APP (Australia), LGPD (Brazil), and CPPA (Canada). Reference Manager curates policy catalogues (`../services/reference-manager.md §1.2`); Localization & Policy Engine (LPE) compiles them for enforcement (see `../services/lp-engine.md §2.1`).

- Sensitive Personal Information (SPI): covers CPRA “sensitive personal information”, GDPR Article 9 special categories, and analogous provincial/federal classifications (for example: biometric identifiers, precise geolocation, racial or ethnic origin, religious beliefs, sexual orientation, union membership, genetic data, immigration status, and government identifiers). SPI inherits the platform’s high-security baseline (encryption, residency controls, reviewer accountability). Guardian enforces SPI gating, detection, and waiver flows; see `../services/guardian.md` for enforcement mechanics.

- CCPA/CPRA specifics: platform does not sell or share personal information; privacy notices and contracts state “no sale/no sharing.” DSAR timelines follow CCPA (45 days, one 45‑day extension with notice) and GDPR (30 days, extensions as allowed). Admin tooling exports DSAR evidence and timelines; audit seals reference the governing framework for each request.

- ISO/IEC 27701 (privacy extension) alignment: fully mapped and implemented. Appendix K lists the control crosswalk, evidence sources, and quarterly recertification cadence; deviations trigger `ISO27701_GAP` incidents and block releases until remediated.

- Compliance mapping (binding): traceable connection between regulation, platform controls, and evidence ensures auditors can verify posture without ad-hoc spreadsheets.

  | Regulation / Framework | Key platform controls & features                                                                               | Canonical references          |
  | ---------------------- | -------------------------------------------------------------------------------------------------------------- | ----------------------------- |
  | GDPR & UK GDPR         | DSAR/erasure workflow (`ERASURE_JOURNAL`), data minimization, audit seals, residency enforcement               | §2.2, §14.2.1, App.N, App.K   |
  | CCPA / CPRA            | “No sale/share” enforcement, notice ledgers, SPI routing and disclosure logging                                | §2.2 (SPI), §11.5, App.K      |
  | HIPAA                  | HIPAA mode activation gates, Guardian PHI quarantine, evidence-store excerpt suppression, WebAuthn enforcement | §2.2, §7.1, §8.2, App.N       |
  | SOC 2 (CC6 / CC7)      | Audit logging, approvals workflows, change management, monitoring dashboards                                   | §12, §14.5, Appendix H, App.K |
  | ISO/IEC 27001 & 27701  | Security management, retention schedules, risk assessments, policy bundles                                     | §2.2, §12.6, §14, App.K       |
  | PIPEDA / CPPA / PHIPA  | Residency controls, consent logging, legal hold & retention automation                                         | §2.2, §3.8, §14.2, App.N      |

- HIPAA mode: applies only to U.S. workloads with an executed BAA. Org activation (`privacy.hipaa.enabled=true`) requires dual approval (`org_admin` + platform `sysadmin`), verifies BAA-backed storage and compute, and enforces per-org field encryption (`security.field_encryption.enabled=true`, `security.field_encryption.key_scope='per_org'`) plus WebAuthn for privileged roles (`security.mfa.webauthn_required_roles` includes `org_admin|org_manager|org_operator|org_reviewer`). Settings expose `privacy.hipaa.enforcement_mode ∈ {optional, required}`—`required` is reserved for U.S. orgs under BAA, while `optional` allows voluntary adoption elsewhere. Outside the U.S. HIPAA stays optional; organizations may opt in for contractual reasons, but enforcement defaults to the general SPI/PHI controls unless HIPAA mode is explicitly enabled.

- Guardian-driven enforcement runs entirely within the service; see `../services/guardian.md` for service-level procedures.

- Baseline enforcement: Reference Manager maintains jurisdiction-specific minimum controls for PII, SPI, and PHI (residency, retention, disclosure logging) as captured in `../services/reference-manager.md §1.4`. `PolicyContext` propagation and runtime policy evaluation live in `../services/lp-engine.md`; Settings and Guardian rely on those compiled controls when validating or judging artifacts.

- Legal hold and destruction policies align with jurisdictional obligations captured in Appendix C.

- Audit linkage: DPIA/RoPA artifacts, CCPA notice ledgers, and HIPAA override activations are referenced in audit seals (`§14.2`, Appendix N); HIPAA activations require Compliance approval and manifest tagging.

### 2.3 Non-functional requirements (SLOs, latency budgets, availability)

*Purpose: Capture performance and reliability expectations.*

- Guardian judgments ≤ 5 minutes P95; Compose jobs complete ≤ 45 minutes P95 under nominal load.
- Service availability: web/channels 99.5%, Guardian 99.9%, Settings API 99.9% (due to policy enforcement criticality).
- LPE availability, compiler latency targets, and deployment windows are defined in `../services/lp-engine.md §1`; burn-rate policies there govern bundle activations and OPA discovery pushes.
- Latency targets: SSE job progress updates P95 \< 2s (P99 \< 5s); artifact download start \< 500 ms for approved documents.
- Error budgets tie directly to deploy gates (`§10.8`)—breaches block releases until burn rate stabilizes.

### 2.4 Assumptions & dependencies

*Purpose: Make explicit the foundational inputs the solution relies on.*

- Identity provider: Keycloak remains the reference IdP, deployed as an HA, multi-region cluster with database replication and automated failover. Multi-tenant SaaS customers receive dedicated realms/clients in the uDocket control plane; dedicated and customer-perimeter deployments can run their own Keycloak instance while synchronizing configuration via the management API. The Access service layer supports bring-your-own IdP via OIDC/SAML federation (Azure Entra ID, Okta, Ping), with Keycloak acting as broker or synchronization target and break-glass accounts retained for uDocket support.

- Cloud dependencies: Azure Speech, Azure OpenAI, Azure Blob/S3-compatible storage with versioning, managed Redis/Postgres—each instantiated in the regions declared per org policy bundle or waiver.

- DevOps baseline: Kubernetes with mesh or workload identity capable of enforcing strict mTLS and egress controls.

- Client orgs commit to providing language/region selections that map to policy allowlists; Settings activation enforces this.

- **Source material:** `§1.1`, `§2`, `§14`, `§16`, `§10.8`

- **Priority:** High (feeds platform policies, approval reviews)

______________________________________________________________________

## 3) Platform architecture overview

### 3.0 Golden path sequence (binding)

**Purpose:** Surface the end-to-end happy path so readers can anchor the deeper sections that follow.\
**Contract:** Describes the canonical SA → WP/CD → DL progression; detailed mechanics live in §5.2 (lifecycle), §5.4 (approvals), §7.1 (Guardian), and §10.3 (APIs).\
**State transitions:** Uses the status vocabulary in §5.2.2 and Guardian mappings in §5.2.3; App.A.2 visualizes the same sequence.\
**Failure modes & retries:** Guardian `BLOCK` diverts to remediation/waiver workflows; approval conflicts leverage RB-APPROVAL-001; job watchdogs apply per §6.2 if heartbeats stall.\
**Observability:** Sequence relies on `job.update`, `guardian_judgment_latency_seconds`, `approval_swap_conflict_total`, and portal invalidation events (`portal_link_invalidated`).\
**Breadcrumbs:** Implementation `apps/platform/operations/tasks/upload.py`, Tests `tests/platform/e2e/test_happy_path.py::test_upload_guardian_approval_flow`, Observability dashboard “Golden Path (Upload→Release)”.\
**References:** §5.2, §5.4.1, §7.1, §10.3, App.A.2.

1. Upload lands in staging (`POST /uploads`), persists the SA (`status='STORED'`) and emits the initial `job.accepted` event (§10.3, App.A.1).
2. Workers derive WP/CD artifacts, run transforms, and park them in `PROCESSING → PENDING_JUDGMENT` while Guardian evaluates (§5.2.2, §7.1). Outcome mapping is canonical in §5.2.3.
3. Guardian PASS/WARN unlocks operator access (`CLEARED_FOR_USE` / `OPERATOR_PREP`); operators or automation advance to review entry (`APPROVAL_REQUESTED → QUEUED_FOR_REVIEW`) (§5.2.4–§5.2.5).
4. Reviewers invoke the Reviews API which applies the ExclusiveSwap invariant from §5.4.1, atomically approving the CD and promoting the new DL (`RELEASED`) while revoking prior deliverables (§10.3.2).
5. Portal invalidation notifies clients of the new deliverable and blocks any revoked link; downstream analytics and audit trails attach Guardian judgment IDs, manifests, and settings hashes (§11.2.1, App.A.2).

<figure class="full-width-diagram">
  <img class="diagram" src="../build/mermaid/services/guardian/diagrams/upload-guardian-approve-v1.png" alt="Upload → Guardian → Approve happy path">
  <figcaption style="font-size: 0.9em; color: #555;">Upload → Guardian → Approve happy path</figcaption>
</figure>

### 3.1 High-level system context diagram

*Purpose: Orient readers to major components and trust boundaries before diving into detail.*

- Staff users, reviewers, and clients interact with the **Web App** (Django ASGI) via browser connections protected by TLS 1.3; SSE provides status streaming while Channels enables bidirectional collaboration. SSE payloads include only IDs and metadata already permitted by RLS—no raw PII or artifact bodies traverse the channel.
- Background processing occurs in the **Worker cluster** (Celery), which orchestrates agent pipelines, storage operations, notifications, and watchdog automation; see [`../services/worker-cluster.md`](../services/worker-cluster.md) for queue topology, failover, and scaling controls.
- Supporting services—**Guardian**, **Digital Signer**, **Settings**, **LLM Registry**, **Localization & Policy Engine (LPE)**, **Reference Manager (RM)**, and **Notifications**—communicate over mTLS within the cluster and persist state to Postgres with RLS. RM operates as the editorial/source-of-truth service for catalog bundles, while LPE is the runtime resolver that consumes those bundles.
- External dependencies (Azure Speech, LLM providers, TSA/OCSP authorities, email/SMS gateways) sit outside the trusted cluster and are accessed under strict egress policies.
- Visual: see `App.A` for the full context diagram and sequence overlays.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/mermaid/overview/tdd/diagrams/system-context-v1.png" alt="System context overview">
  <figcaption style="font-size: 0.9em; color: #555;">System context overview</figcaption>
</figure>

### 3.2 Deployment topology (environments, Kubernetes primitives)

*Purpose: Capture the runtime footprint and security guardrails applied per environment.*

- Kubernetes namespaces per environment (`dev`, `staging`, `prod`, `audit`) host Deployments for `web`, `channels`, `workers`, `guardian`, `signer`, `llm-registry`, `reference`, `notifications`, `settings`, ingress controllers, Redis broker/cache, and object-storage sidecars.
- Service mesh or SPIFFE/SPIRE workload identity enforces strict mTLS; certificates rotate with TTL ≤ 24h and SLO of 99.9% renewals within five minutes of expiry. Certificates that exceed `security.tls.cert_ttl_minutes + 5` minutes trigger a hard fail (traffic denied) and page on-call; soft warnings fire 30 minutes before TTL expiry to allow proactive rotation. Mutating RPCs must satisfy both mutual TLS **and** HMAC headers: the mesh validates SANs against SPIFFE IDs (`spiffe://uDocket/<service>`) or an allowlisted CN, and the receiving service reconstructs the shared-secret signature (Appendix F). Calls missing either layer are rejected with `401 AUTH_ERROR` and recorded via `auth_layer_violation_total`.
- Network policy: ingress terminates TLS (TLS 1.3 preferred; limited TLS 1.2 fallback). Egress is default-deny aside from kube-dns and the Istio egress gateway; the gateway enforces the region-scoped allowlists rendered from the `network.egress.allowed_hosts` Settings bundle, and drift detection nightly resolves each FQDN (for example `*.blob.core.windows.net`, `*.table.core.windows.net`, `*.queue.core.windows.net`, TSA/OCSP hosts) to compare against SAN lists.
- TLS details: TLS 1.3 remains the platform default. When `security.tls.fips_mode=true`, only FIPS-approved AES-GCM ciphers are permitted (`TLS_AES_128_GCM_SHA256`, `TLS_AES_256_GCM_SHA384`) and ChaCha20 suites are rejected at validation time (mirrors OpenSSL FIPS provider guidance). Non-FIPS environments (explicit `security.tls.performance_mode=true`) MAY allow `TLS_CHACHA20_POLY1305_SHA256` to improve mobile performance but must record the exception in the release checklist. TLS 1.2 fallback suites remain explicit (`{'ECDHE-ECDSA-AES128-GCM-SHA256', 'ECDHE-RSA-AES128-GCM-SHA256', 'ECDHE-ECDSA-AES256-GCM-SHA384', 'ECDHE-RSA-AES256-GCM-SHA384'}`). OCSP stapling stays enabled on ingress. Fallback may be enabled via `security.tls.legacy_exceptions[]` entries that include endpoint name, justification, and an expiry ≤ 30 days out; Settings activation validator rejects longer windows, and an alert fires seven days before expiry to force review. Production ingress treats TLS 1.3 (`security.tls.min_version=TLSv1.3`) as the control surface; downgrades require Security approval plus updated attestation for the impacted environment. A synthetic handshake job (`scripts/security/check_tls_ciphers.py`) runs per environment on each deploy and as part of nightly CI, failing the build if CHACHA20 handshakes succeed while FIPS mode is enabled or if AES-GCM suites disappear from the non-FIPS profile.
- Platform services leverage managed secrets (Vault or Azure Key Vault). Nodes run chrony/NTP with ±100 ms drift to support TSA validation. Redis handles broker/cache needs; Postgres (regional HA) stores relational data.
- Object storage: Azure Blob (prod) or S3-compatible (dev) buckets configured for versioning, SSE-KMS, and immutable retention for audit sinks. Residency isolation is enforced via dedicated containers per data-residency cohort with no cross-region replication; replication is permitted only within the region boundary declared in `regions.allowlist.storage`, and manifests record the container + key vault backing each cohort so compliance teams can attest to zero-copy guarantees.
- Database encryption at rest: managed Postgres clusters rely on cloud Transparent Data Encryption; storage, WAL archives, and snapshots are encrypted with Azure-managed keys by default and can swap to customer-managed keys (`security.db.cmk_id`) when an org or regulator requires attestation. Key rotation flows through Key Vault, produces `DB_TDE_ROTATION` artifacts, and triggers automated smoke tests that verify new keys before swaps propagate to replicas.
- Container runtime: all workloads ship as OCI images. Production deployments run on AKS-managed Kubernetes with Flux CD applying Helm releases per environment; PodSecurity is set to the restricted baseline (no privileged pods, read-only root FS where feasible), and image provenance is enforced via cosign attestations validated by an admission webhook. Local developer workflows use `docker compose` (`docker-compose.yml` + override) to mirror the full stack—web, workers, Guardian, Signer, Settings, Redis, Postgres, object storage emulator, and supporting queues. Compose wiring reuses the same `.env` schema and health checks; developers run `docker compose up --build` to start the stack, while integration tests spin subsets of services (for example, `docker compose -f docker-compose.tests.yml up web worker guardian`) to reproduce production behaviour before pushing changes.
- Multi-region posture: each environment operates within a primary/secondary region pair; database replicas, blob replication, and queue failover respect the org-specific allowlists. Disaster recovery runbooks document region cutover and data rehydration using only approved regions per §3.8.

#### 3.2.1 Policy manifests (illustrative)

*Purpose: Show concrete Kubernetes/service-mesh policies to enforce topology constraints.*

AuthorizationPolicy (Istio)

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata: { name: mesh-egress-allowlist, namespace: platform }
spec:
  action: ALLOW
  rules:
    - to:
        - operation:
            hosts:
              - "na-us-1.api.cognitive.microsoft.com"
              - "eu-west-2.api.cognitive.microsoft.com"
              - "na-us-1.ocsp.msocsp.com"
              - "tsa.partner.example.com"
    - to:
        - operation:
            hosts: ["signing-root.example.com"]
```

- Illustrative host list; production values are rendered from the `network.egress.allowed_hosts` Settings bundle (SYSTEM scope) and materialized as `ServiceEntry` resources with exact SNI/authority matches. Istio AuthorizationPolicy host matching is literal—wildcards are rejected—so the helper renders the fully qualified domains for each approved endpoint.

NetworkPolicy (Kubernetes)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: mesh-egress-baseline, namespace: platform }
spec:
  podSelector: { matchLabels: { mesh: enabled } }
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector: { matchLabels: { kube-system: "true" } }
          podSelector: { matchLabels: { k8s-app: kube-dns } }
      ports:
        - protocol: UDP
          port: 53
    - to:
        - namespaceSelector: { matchLabels: { istio: control-plane } }
          podSelector: { matchLabels: { app: istio-egressgateway } }
    # External destinations are mediated by the service mesh AuthorizationPolicy allowlist.
```

AdmissionPolicy (prevent PgBouncer statement pooling)

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata: { name: deny-statement-pooling }
spec:
  rules:
    - name: block-statement-pooling
      match: { resources: { kinds: ["Deployment"], namespaces: ["platform"] } }
      validate:
        message: "PgBouncer must not use statement pooling"
        foreach:
          - list: "spec/template/spec/containers"
            preconditions:
              - key: "{{ element.name }}"
                operator: Equals
                value: pgbouncer
            deny:
              conditions:
                - key: "{{ element.env[?name=='POOL_MODE'].value | default('session') }}"
                  operator: Equals
                  value: statement
```

- PgBouncer is permitted to run only in `transaction` (default) or `session` pooling modes as published through the `db.pgbouncer.pool_mode` Setting; statement pooling remains blocked to preserve per-request GUCs. Workers and web pods expose a `/healthz/pgbouncer-mode` probe that executes `SHOW pool_mode` via PgBouncer admin and fails closed if the reported mode drifts from the allowlist, aligning with §4.4 RLS guarantees.

Ingress TLS policy (snippet)

*TLS 1.3 is the platform default (`security.tls.min_version=TLSv1.3`). TLS 1.2 appears only when a `security.tls.legacy_exceptions[]` entry is active with Security-approved justification and an expiry of 30 days or less.*

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: platform
  annotations:
    nginx.ingress.kubernetes.io/ssl-protocols: "TLSv1.3 TLSv1.2"
    nginx.ingress.kubernetes.io/ssl-ciphers: "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
```

- TLS 1.3 cipher suites are implicit; the annotation lists only the TLS 1.2 fallback suites the gateway permits.
- Authoritative TLS policy is driven by `security.tls.min_version` (default `TLSv1.3`) and `security.tls.cipher_profile` Settings bundles; any TLS 1.2 exposure must be explicitly listed in `security.tls.legacy_exceptions[]` with documented review and expiry. Mesh and ingress templates consume the same settings so routing surfaces stay consistent.

Pod Security Admission (namespace labels)

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: platform
  labels:
    pod-security.kubernetes.io/enforce: "restricted"
    pod-security.kubernetes.io/enforce-version: "latest"
```

### 3.3 Service inventory table (role, tech stack, scaling)

*Purpose: Provide a tabular summary for capacity planning and onboarding.*

| Service                            | Runtime                                     | Responsibilities                                                                                                 | Scaling & notes                                                                           | Observability anchors                                                                                         |
| ---------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Web                                | Django ASGI (uvicorn + gunicorn)            | REST APIs, staff UI, client portal, SSE endpoints, approval workflows                                            | HPA on CPU+request latency; sticky sessions avoided                                       | `web_http_*`, `frontend_latency_seconds`, `audit_event_total`                                                 |
| Channels                           | Django Channels (Redis-backed)              | Real-time editors, approvals, QA feedback                                                                        | Separate Deployment with autoscale on WS connections                                      | `channels_active_connections`, `channels_msg_latency_seconds`                                                 |
| Workers                            | Celery (prefork)                            | Media normalization, agent orchestration, notifications, ingestion, destruction                                  | Queue length auto-scaling; dedicated queues per agent class                               | `celery_queue_depth`, `job_duration_seconds`, `task_retry_total`                                              |
| Guardian                           | FastAPI                                     | PASS/WARN/BLOCK/WAIVED judgments, policy evaluation, audit history                                               | Pod HPA on latency; 99.9% SLO                                                             | `guardian_judgment_latency_seconds`, `guardian_cleared_ratio`                                                 |
| Digital Signer                     | FastAPI                                     | PDF/A signing, OCSP/CRL/TSA validation, bundle creation                                                          | Scales with signing queues; relies on KMS/TSA connectors                                  | `signer_request_latency_seconds`, `tsa_drift_seconds`                                                         |
| LLM Registry                       | FastAPI                                     | Provider catalog, health probes, token accounting, fallback logic                                                | Low QPS; run ≥2 replicas                                                                  | `llm_provider_health`, `llm_circuit_state`                                                                    |
| Settings Service                   | FastAPI                                     | Hierarchical settings APIs, bundle activation, diff previews                                                     | Autoscale on QPS; Redis pub/sub for cache invalidation                                    | `settings_activation_total`, `settings_cache_hit_ratio`                                                       |
| Localization & Policy Engine (LPE) | FastAPI + worker cron + compiler jobs       | Localization (locale/i18n packs), policy contexts (privacy/residency), court catalogs                            | Compiler pods scale on activation; lookup API horizontally replicated                     | `lpe_lookup_latency_seconds`, `lpe_policy_context_version`, `lpe_cache_hit_ratio`                             |
| Reference Manager                  | FastAPI + Celery ingest workers + review UI | Source connectors (Wikipedia, court sites, vendor feeds), catalog lifecycle, questionnaires/forms administration | Ingest workers autoscale on harvest queues; reviewer workload tracked via task backlog    | `reference_manager_ingest_duration_seconds`, `reference_manager_pending_reviews`, `reference_catalog_version` |
| Notification Service               | Celery beat + worker                        | Outbox delivery (email/SMS/in-app), receipt tracking                                                             | Scales with delivery volume; provider specific adapters                                   | `delivery_success_ratio`, `delivery_retry_total`                                                              |
| Storage adapters                   | Sidecar / init jobs                         | Object storage integrity checks, audio normalization caching                                                     | Scoped per namespace                                                                      | `storage_hash_mismatch_total`, `object_store_latency_seconds`                                                 |

- **Stack note:** Web and Channels services run on Django 5.2.x (ASGI via uvicorn + gunicorn) and Django Channels 4.1.x, both pinned in `apps/platform/requirements.txt`; SBOM gates block implicit minor upgrades.

### 3.3 Deployment models (SaaS, dedicated, customer-perimeter)

*Purpose: Describe supported hosting patterns, required controls, and identity integrations.*

- **Multi-tenant SaaS (default):** uDocket operates shared regional clusters; org isolation relies on RLS, tenancy-aware storage, and Guardian/LPE policy enforcement. A uDocket-hosted Keycloak instance provides identity with per-org clients/realms that federate to customer IdPs via brokers.
- **Dedicated SaaS tenant:** Regulated or high-volume customers receive an isolated Kubernetes footprint (separate cluster or namespace boundary) with dedicated storage accounts and Keycloak realm. Reference Manager’s infrastructure catalogue records the deployment ID, residency posture, and compliance attestations so LPE/Settings enforce appropriate defaults.
- **Customer-perimeter managed:** Large firms may require the stack inside their own security perimeter. uDocket supplies hardened Helm/Terraform bundles, handles release governance, and retains read-only observability. Keycloak can run in the customer environment (synchronized via management APIs) or connect to a uDocket-managed realm through secure outbound tunnels. uDocket maintains a break-glass service account while day-to-day auth flows against the customer’s IdP.
- **Identity considerations:** Each deployment model maps to a Keycloak realm strategy—shared SaaS realms with per-org clients, dedicated realms for isolated tenants, or customer-hosted realms federated to their IdP. Realm provisioning enforces MFA policies and audit logging aligned with Appendix H.
- **Configuration surface:** Settings expose `infrastructure.deployment_type ∈ {saas_multi, saas_dedicated, customer_managed}` and `infrastructure.realm_id`. PolicyContext includes the deployment type so Guardian, portal, and automation respect residency, logging, and support boundaries. Infrastructure catalogue entries list optional provider stacks (HIPAA storage, FedRAMP tiers, on-prem references) curated by RM to streamline future cutovers.

### 3.4 Localization & Policy Engine (LPE)

*Purpose: Point to the dedicated LPE specification that governs localization, residency, and policy enforcement.*

The full service charter, compiler pipeline, PolicyContext contract, integrations, APIs, observability, and rollout plan now live in `../services/lp-engine.md`. Refer to that document for normative requirements, examples, testing matrices, and migration milestones. This platform TDD cites LPE outputs (PolicyContext digests, localization packs, waiver metadata) where needed but does not duplicate their definitions.

### 3.5 Reference Manager (catalog ingestion & lifecycle)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/`, Tests `tests/reference/`, Observability Grafana “Reference Manager – Ingestion & Quality” / “Reference Manager – Review & Publishing”. *Purpose: Point to the dedicated Reference Manager specification governing ingestion, review, publishing, and rollout.* *Contract: `../services/reference-manager.md` defines binding behaviour for source acquisition, normalization, governance, bundles, APIs, and incident response; platform services must align with that specification.* *State: RM persists harvest, staging, curated, history, and bundle registry data in Postgres and publishes signed bundles referenced by downstream services.* *Failure modes & retries: Publishing, adoption, and rollback controls are enforced per `../services/reference-manager.md`; breaches of adoption lag or validation SLAs block promotion until resolved.* *Observability: Dashboards and metrics listed in `../services/reference-manager.md §5.1` monitor harvest health, review backlog, publish cadence, and adoption lag.*

All normative requirements for Reference Manager—including connectors, governance, questionnaires/forms, publishing pipeline, testing, risks, APIs, and observability—now live in `../services/reference-manager.md`. This platform TDD references that document when describing Residency enforcement (§3.8), Settings activation (§4), LPE integration (§6), and artifact attribution (§7). Key integration hooks:

- RM publishes signed catalog and resource bundles consumed by LPE, Settings, Guardian, Portal, and agents. See `../services/reference-manager.md §1.3` and §4 for event flows and adoption guarantees.
- Provider endpoint catalogues from RM populate Settings residency allowlists and power enforcement jobs described in §3.8 and `../services/reference-manager.md §4.3`.
- Questionnaires, forms, localization packs, and attribution metadata surface in staff/portal UI and Compose/Analyze agents via deterministic identifiers maintained by RM (`../services/reference-manager.md §3.3`).
- Incident readiness, rollback tooling, and deploy gates remain aligned with `../services/reference-manager.md §5.3`; production reviews should consult that specification before approving bundle or adapter changes.

### 3.6 Data flows between services

*Purpose: Describe the critical sequences that tie services together.*

- **Upload → Guardian → Approval:** Web accepts uploads, stages to object storage, inserts `class=SA` artifacts (`status='STORED'`), workers derive WP/CD entries (`PROCESSING → PENDING_JUDGMENT`), Guardian issues PASS/WARN/BLOCK judgments (→ `CLEARED_FOR_USE` / `OPERATOR_PREP` / `QUARANTINED`), operators submit from `OPERATOR_PREP` (→ `APPROVAL_REQUESTED`) and queue routing moves the draft into `QUEUED_FOR_REVIEW` before any reviewer touches it (sequence in `App.A.2`).
- **Agent pipeline:** Workers fetch inputs (audio/transcripts), execute Transcribe/Analyze/Compose stages, write artifacts + manifests, and notify Guardian & SSE. Settings snapshots travel alongside each job to guarantee reproducibility.
- **Reference curation loop:** Reference Manager harvests, reviews, and publishes regulated catalog bundles consumed by LPE, Settings, Guardian, Portal, and agents; integration and adoption guarantees live in `../services/reference-manager.md §4`.
- **Notification loop:** Worker pushes delivery requests to Notification Service; receipts update artifact manifests and audit events. Portal fetches approved deliverables via signed URLs with guardian-enforced readiness.
- **Telemetry stream:** All services emit logs/metrics/traces to the Observability Fabric (Elastic/OTel stack). Guardian judgments and settings activations append to ops audit JSONL under each case.
- **Settings change propagation:** Activations in Settings Service publish invalidation events; consuming services flush caches and rehydrate GUC policies on next request/task.

### 3.7 External integrations (Azure Speech, LLM providers, TSA/OCSP)

*Purpose: Catalog regulated touchpoints subject to policy and audit.*

- **Azure Speech (per-org allowlisted regions):** Batch transcription via SAS URLs and on-demand streaming; operations include hashing uploads, enforcing PCM normalization, and monitoring quotas. Regional endpoints are provisioned according to `regions.allowlist.compute`.

- **Speech fallback providers (processor-agnostic):** Speechmatics Canada (primary fallback) and any additional providers must expose REST APIs with parity guarantees (WER/diarization deltas within policy thresholds) and identical residency attestations. Workers consume them through the same `TranscriptionAgent` interface so jobs remain provider-agnostic.

- **LLM providers:** Restricted to org-approved regions and models; selection algorithm honors `fallback_priority`/`fallback_chain` and records equivalence evidence for every switchover. Evidence store records prompts, redaction metrics, and envelope metadata per call.

- **Digital trust services:** TSA and OCSP/CRL endpoints defined in settings (`sign.trust_roots[]`); signer enforces drift ≤ ±5s and caches responses ≤12h.

- **Notification channels:** Email/SMS providers configured per organization; webhook adapters log request/response pairs with PII masking.

- **Localization & Policy Engine (LPE):** Runtime resolver for localization and policy bundles; refer to `../services/lp-engine.md` for compilation, adoption, and API contracts.

- **Reference Manager sources:** Managed per `../services/reference-manager.md §2.1`, which documents approved connectors, throttles, and evidence capture requirements.

- **Optional analytics sinks:** Metrics exported to Grafana/Prometheus; FinOps dashboards consume cost metrics for monthly guardrails.

- Sub-processor directory: see App.Q for approved vendors, residency posture, and DPA commitments.

______________________________________________________________________

### 3.8 Region allowlist enforcement & egress policies (binding)

**Breadcrumbs:** Implementation `apps/platform/operations/services/residency.py::enforce_allowlists`, Tests `tests/platform/operations/test_residency_allowlist.py::test_denies_unapproved_host`, Observability Grafana “Residency & Endpoint Posture”.

*Purpose: Enforce multi-region residency controls and govern outbound traffic to providers.*

- Settings define allowlists per org: `regions.allowlist.compute|storage|vector` accept ISO-like region identifiers (for example, `na-us-1`, `na-us-2`, `eu-west-2`). Activation lints reject entries outside the curated Reference Manager region catalogue or without matching data-processing agreements.
- Network layer: Kubernetes `NetworkPolicy`/service mesh `AuthorizationPolicy` denies egress to non-allowlisted CIDRs/hostnames; provider endpoints are pinned by FQDN, SAN match, and residency metadata sourced from RM bundles.
- Providers: Azure Speech/OpenAI selection honors the allowlist; the LLM runtime filters models by approved regions before selection. Cross-region failover requires a dual-approved waiver stamped into manifests and logged by Guardian.
- Availability posture: compliance trumps uptime—jobs pause when all in-region providers are unhealthy rather than spilling into non-compliant regions. To mitigate downtime, every residency bundle must approve at least two providers per region for core services (speech, LLMs); health monitors rotate across the in-region pool and Guardian raises `REGION_PROVIDER_DEGRADED` alerts when redundancy is at risk.
- Storage: object buckets created in approved regions; replication outside the allowlist stays disabled unless a waiver is present. Manifests record the storage topology (`primary_region`, optional `replica_region`, waiver reference).
- Drift detection: nightly job resolves each configured host, validates SAN entries against `network.egress.allowed_hosts`, compares resulting CIDRs to the allowlist, and pages when drift is detected. The job also verifies that provider metadata still advertises the approved residency posture.
- Telemetry: `residency_block_total` increments on blocks; audit records include `RESIDENCY_POLICY_BLOCK` reason and settings snapshot hash; dashboards highlight block rates per org/region.
- Expansion posture: RM catalogs enumerate global regions (NA/EU/APAC). New jurisdictions enable by adding allowlist entries plus waiver or DPA references; App.O ledger tracks approvals. Synthetic tenant “EU-REFERENCE” exercises EU-only paths quarterly to confirm Azure EU endpoints, storage buckets, vector shards, and TSA integrations honor EU residency before production onboarding.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/mermaid/services/lp-engine/diagrams/residency-policy-enforcement-v1.png" alt="Residency policy enforcement sequence">
  <figcaption style="font-size: 0.9em; color: #555;">Residency policy enforcement sequence</figcaption>
</figure>

#### 3.8.1 Residency endpoint posture detection (binding)

**Breadcrumbs:** Implementation `apps/platform/operations/task_modules/residency_endpoint_scan.py`, Tests `tests/platform/operations/test_residency_endpoint_scan.py::test_blocks_drift`, Observability Grafana “Residency & Endpoint Posture”.

*Purpose: Continuously verify that every outbound endpoint honors the declared residency posture before traffic is permitted.*

- Source-of-truth: Reference Manager publishes a `provider_endpoints` catalogue (`region`, `provider`, `purpose`, `approved_cidrs`, `san`, `dpa_ref`). Settings activation merges this catalogue with org-scoped allowlists and materializes `network.egress.allowed_hosts`.
- Scanner: the `residency_endpoint_scan` Celery job runs hourly (per environment) and on activation events. It resolves each hostname, expands CNAME chains, and maps IPs to jurisdictions using provider APIs (Azure Resource Graph, MS Peering) plus the GeoIP2 offline database (`data/privacy/geoip.mmdb`, refreshed weekly). SAN and certificate-chain validation confirms that TLS endpoints still advertise the expected region/service pair.
- Drift & gaps: hosts missing from the catalogue, SAN mismatches, or GeoIP jurisdiction drift record findings in `residency_endpoint_findings` (`state ∈ {open, mitigated, waived}`) and append JSONL evidence under `ops/residency/endpoint_scan.jsonl`. The mesh deny list blocks endpoints whose findings remain `open` for ≥ 5 minutes.
- Change detection: new endpoints discovered in provider SDKs or Azure/AWS service updates trigger `RESIDENCY_ENDPOINT_NEW` audit events, open a Security Jira ticket (template `SEC-RESIDENCY-ENDPOINT`), and require catalogue ingestion before the Settings activation may proceed (`unsafe_reason="missing_endpoint_catalog_entry"`).

#### 3.8.2 Reporting & escalation (binding)

**Breadcrumbs:** Implementation `apps/platform/operations/services/residency_reporting.py`, Tests `tests/platform/operations/test_residency_reporting.py::test_alert_routing`, Observability PagerDuty service “Residency Drift” / Grafana “Residency & Endpoint Posture”.

*Purpose: Ensure residency drift is observable and actioned quickly across teams.*

- Metrics: `residency_endpoint_scan_duration_seconds`, `residency_endpoint_drift_total{reason=...}`, and `residency_endpoint_blocks_total` feed the Residency dashboard (Grafana → “Residency & Endpoint Posture”). Alert `alert_residency_endpoint_drift` fires when new `open` findings exist for 10 minutes or a scan fails twice consecutively.
- Notifications: the scanner emits structured PagerDuty incidents tagged `RESIDENCY_DRIFT`, posts to `#residency-alerts`, and attaches the latest JSONL snippet plus catalogue diff. Weekly digest reports aggregate findings, waivers, and remediation SLAs; digests store under `ops/residency/digest_<iso_week>.json`.
- Evidence: App.L incorporates residency drift baselines; [Runbook RB-RES-ENDPOINT](../ops/runbooks/index.md#rb-res-endpoint) holds the detailed remediation steps referenced from alerts. App.O ledger links waivers to the specific findings they suppress.

#### 3.8.3 Triage & remediation workflow (binding)

**Breadcrumbs:** Implementation `apps/platform/operations/services/residency_triage.py`, Tests `tests/platform/operations/test_residency_triage.py::test_drives_remediation_plan`, Observability [Runbook RB-RES-ENDPOINT](../ops/runbooks/index.md#rb-res-endpoint) mapped to Grafana “Residency & Endpoint Posture”.

*Purpose: Provide a deterministic path from detection to resolution without violating residency guarantees.*

- First response (within 15 minutes): SRE validates the alert, confirms the endpoint is blocked, and checks whether production traffic attempted to reach it (audit search on `RESIDENCY_POLICY_BLOCK` + endpoint). Security triages provider announcements or CDN/autoscaling expansions.
- Remediation branches:
  - **Catalogue update:** Reference Manager on-call executes the ingestion and validation steps defined in `../services/reference-manager.md §4.3`, updating `provider_endpoints` and replaying Settings activation once residency attestations are verified.
  - **Waiver required:** Dual approval (Security + Architecture) recorded in App.O; Settings sets `cross_region_waiver` for the affected org/service, and Guardian stamps manifests until the provider delivers an in-region alternative.
  - **Misconfiguration:** When hosts resolve outside the allowlist because of DNS drift or cache poisoning, SRE flushes DNS caches (`scripts/residency/flush_dns_cache.py`) and, if necessary, overrides the mesh egress policy until the provider restores expected records.
- Closure: findings flip to `mitigated` once the scanner observes compliant endpoints for two consecutive runs. Incident retrospectives attach scanner evidence, Settings diffs, and Guardian waiver logs to the decision log (§15.3); preventive tickets capture backlog (provider engagement, automation gaps).

______________________________________________________________________

### 3.9 C4 containers & STRIDE dataflows (binding)

**Breadcrumbs:** Implementation `overview/tdd/diagrams/c4/container-platform-v1.mmd` + `overview/tdd/diagrams/threat/dfd-platform-stride-v1.mmd`, Tests `scripts/docs/render_mermaid.sh` (CI job `docs-diagram-render`), Observability CI stage “docs-validate” with artifact drift alerts.

*Purpose: Provide an explicit container-level view with threat annotations that build on the context diagram.*

- Container and component diagrams live beside this document (`overview/tdd/diagrams/c4/container-platform-v1.mmd`, `overview/tdd/diagrams/c4/component-platform-v1.mmd`, and rendered SVG/PNG artifacts). Updates must ship with schema or service changes so reviewers can reason about new dataflows before approving agent or infra work.
- The platform threat DFD (`overview/tdd/diagrams/threat/dfd-platform-stride-v1.mmd`) applies STRIDE categories per dataflow: ingress/egress gateways, service-mesh mTLS, Guardian/Signer decision loops, and outbound provider calls. Appendix B enumerates the detailed scenarios; this subsection records the binding between the DFD and container view.
- Container threats and mitigations:

| Container / trust boundary                   | Primary dataflows & STRIDE focus                                            | Key mitigations & references                                                                                                                                                       |
| -------------------------------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Web & Channels (staff + portal)              | Browser ↔ ASGI over TLS (`Spoofing`, `Tampering`, `Information disclosure`) | mTLS terminates at ingress; HSTS/CSP (§11.5); SSE token binding (§10.8); RLS GUC canaries (§4.4); App.B Spoofing mitigations                                                       |
| Worker cluster (Celery)                      | Jobs ↔ storage/LLM providers (`Tampering`, `Repudiation`, `DoS`)            | Settings snapshots (§6.1), audit JSONL (§6.3/§6.4), advisory locks (§5.4/[Runbook RB-LOCK-006](../ops/runbooks/index.md#rb-lock-006)), FinOps guard (§8.7/§13.5)                   |
| Guardian & Signer services                   | Artifact promotion, digital seals (`Tampering`, `Repudiation`)              | FOR SHARE parent guard (§7.1), immutable audit sink (§12.1), OCSP/TSA verification (§7.2), ADR-0001 (judgment & waiver scope)                                                      |
| Settings service + policy compiler           | Config activation across tenants (`Spoofing`, `Elevation of privilege`)     | HMAC-signed requests (§7.3), dual approval (§9.3/§9.11), compiled RLS tables (§4.4), activation lock advisory key (§9.8)                                                           |
| External providers (Azure Speech/OpenAI/TSA) | Controlled egress (`Information disclosure`, `DoS`)                         | Mesh AuthorizationPolicy (§3.8), residency waivers (App.O), LLM safety harness (§8.4), provider circuit breakers (§8.1, [Runbook RB-LLM-003](../ops/runbooks/index.md#rb-llm-003)) |

- Threat reviews must reference both the container diagram and DFD; new services may not progress past **Provisional** until they document ingress/egress paths, STRIDE analysis, and mitigations in Appendix B.

______________________________________________________________________

## 4) Identity, tenancy & access control

### 4.1 AuthN provider (Keycloak) and realm configuration

*Purpose: Define the identity backbone and token contract consumed by all services.*

- Realm `uDocket` with clients `staff-ui`, `client-portal`, `service-api`, `guardian`, `signer`, `settings`, `notifications`, `llm-registry`, `reference-manager`, `lpe` (former `reference` client retained temporarily as read-only shim until the migration window in `../services/lp-engine.md §8.4`).
- Roles split into realm (`sysadmin`, `auditor`) and organization scope (`org_admin`, `org_manager`, `org_operator`, `org_reviewer`, `org_external_counsel`, `org_client`).
- Tokens include `org_ids[]`, `active_org_id`, `active_org_roles[]`, optional `org_directory[]`. Middleware rejects any request where `active_org_id ∉ org_ids[]`.
- Access tokens ≤15 minutes, refresh tokens 12h (staff) / 2h (portal); offline tokens disabled unless security approves exceptions. Step-up MFA signaled via OIDC `acr` claim for sensitive endpoints.
- Login flow for org switching triggers re-authentication to mint new tokens bound to the selected organization—no custom headers for impersonation allowed.
- High availability: Keycloak runs as an active-active cluster across at least two zones per permitted region with Galera-backed MariaDB or Aurora Postgres, sticky session disabled. Ingress health probing and Envoy failover drain unhealthy pods. Backup realm exports run hourly; disaster recovery rehydrates a warm standby in the paired region identified in `regions.allowlist.compute`.
- IdP federation: organizations can register external IdPs (Azure Entra ID, Okta, Ping, ADFS) through Keycloak identity brokering. Each federation mapping undergoes automated policy linting (MFA enforcement, group-to-role mapping) before activation. Tokens always originate from Keycloak, so revocation/audit remain centralized even when primary credential verification happens upstream.
- Emergency access: if an external IdP fails, operators flip the org to Keycloak-native credentials via a feature flag (`identity.org.{org_id}.primary_idp=keycloak`) with dual approval. Runbook `../ops/runbooks/index.md (RB-IDP-FAILOVER)` covers rollback. Conversely, if the Keycloak control plane is degraded, traffic fails over to the warm standby while orgs using external IdPs continue authenticating directly with their provider, minimizing downtime.
- Federation flows: Keycloak brokers both OIDC (`authorization_code+PKCE`, signed JWT access tokens, enforced `acr` claims) and SAML 2.0 integrations. Each org-specific IdP registration supplies metadata (JWKS endpoint or SAML metadata URL), required MFA assurance levels, group-to-role mappers, and SCIM provisioning endpoints. SCIM sync (see §14.6) keeps org membership aligned; onboarding rejects providers that cannot assert MFA or pass signed-response validation. All tokens ultimately originate from Keycloak so audit, revocation, and Guardian controls remain centralized.

### 4.2 Org/case membership model and RBAC lattice

*Purpose: Explain how authorization decisions resolve across org and case scopes.*

- `organization` table is the root tenant; `case` rows reference `org_id`. Users gain visibility through Keycloak Organizations; the platform mirrors minimal metadata for labels.
- `case_member(user_id, case_id, role)` narrows access within an organization; default operator scope is “own cases.” Org settings can widen to “all org cases” with policy approval.
- Effective permissions compile from Settings bundles into `effective_permission` (resource/action/role/field). `udocket_can(...)` function enforces deny-by-default, with only `sysadmin` realm role as hardcoded bypass.
- Policies drive field-level allowances (`field_mask_rule`) and exclusivity (e.g., artifact types). Settings activation pipeline validates coverage before publishing changes.

### 4.3 Session management & token binding

*Purpose: Prevent token misuse and session fixation across services and clients.*

- Middleware sets per-request context (`active_org_id`, `active_user`, roles) and stores them via `set_config(..., true)` to bind DB sessions. Missing context triggers 403 with `RLS_CONTEXT_MISSING`.
- Access tokens bind to device fingerprint hashes; switching orgs invalidates active SSE/WebSocket connections to prevent cross-org leakage.
- Device fingerprint derivation (binding): `ua_hash = sha256(lower(user-agent))`, IP normalized (`IPv4 /24`, `IPv6 /48`), `device_fp = sha256(f\"{ua_hash}:{ip_prefix}\")`; tokens carry `device_fp` claim and mismatches trigger re-auth/step-up flows.
- Org settings `security.session.device_bind.ip_prefix_len_v4|ip_prefix_len_v6` control those prefix lengths (defaults `/24` and `/48`); mobile-heavy orgs may widen prefixes to reduce unnecessary prompts while retaining auditability. `security.session.device_bind.mode` selects `\"soft\"` (default) or `\"hard\"`: soft mode logs mismatches as `DEVICE_FP_MISMATCH_SOFT` audit events and prompts step-up only after three events within 24h, while hard mode terminates sessions immediately with `code=\"AUTH_ERROR\"`, records `DEVICE_FP_MISMATCH_HARD`, and requires privileged WebAuthn re-auth before retry. Behind trusted corporate NATs or CDN proxies the IP prefix remains a soft signal, and ingress trusts `X-Forwarded-For` only from mesh-managed gateway CIDRs declared in `security.session.trusted_proxy_cidrs[]`.
- Refresh tokens are device-bound when enabled per org policy; defaults disable long-lived offline tokens except where Security approves exceptions.
- Break-glass endpoints require step-up MFA at activation **and** closure, justification, and explicit expiry (configurable 5-60 minutes); generated `BreakGlassEvent` entries follow `spec/schemas/break_glass_event.schema.json` (`{schema_version:'break_glass_event@1.0', event_id, actor_id, approvers[], justification, opened_at, expires_at, closed_at?, retrospective_artifact_id?}`) and include approver IDs. Weekly job `ops/security/audit_break_glass.py` verifies every open/closed event is linked to a retrospective artifact; failures block the deployment pipeline and raise `break_glass_event_missing_retrospective_total` alerts.
- Org switch to higher privileges defaults to requiring step-up MFA (`security.org_switch.step_up_required=true`), overridable only with documented risk acceptance.
- HIPAA mode extends step-up MFA by enforcing WebAuthn for privileged roles (`security.mfa.webauthn_required_roles`) before approvals or portal deliveries touching HIPAA-classed artifacts.

### 4.4 Database RLS and GUC enforcement

*Purpose: Describe how data-layer access rules enforce the same contract as the API tier.*

- All tenant tables carry `org_id`; Postgres RLS policies require per-connection GUCs (`udocket.active_org`, `active_user`, `active_roles`, `realm_roles`, `operator_scope`).

- Helper functions (`udocket_has_realm_role`, `udocket_is_case_member`, `udocket_can`) centralize policy evaluation. Any query without GUC setup is denied; the `/healthz/pgbouncer-mode` probe confirms PgBouncer stays in approved `transaction` or `session` pooling modes (statement pooling remains blocked) so per-request GUCs remain intact.

- Runtime guard (binding): every connection must satisfy `rls_context_ok()` immediately after checkout. Web middleware and Celery task bootstrap call `SELECT rls_context_assert();` which wraps `rls_context_ok()` and raises when `active_org`, `active_user`, `active_roles`, `realm_roles`, `operator_scope`, or `search_path` are unset or contain unexpected values. Violations emit a structured log with code `RLS_CONTEXT_MISSING`, record the offending connection id, and hard-fail the request with HTTP 500. The guard also confirms `current_setting('search_path') = 'pg_catalog, public'::text` to prevent implicit table access.

- Secure views (`*_secure`) act as the only read surfaces; application role lacks direct SELECT on base tables. CI lints ensure ORM queries reference views, and production deployments rely on compiled helper tables (e.g., `field_mask_rule_effective`) to avoid per-row subqueries inside those views.

- CI guardrails (binding): `pytest -k test_secure_view_usage` runs a static query-inspection test that fails if any Django queryset or raw SQL in `apps/platform` references base tables instead of `*_secure` views. The lint feeds the release gate and prevents regressions when new endpoints are added.

- Advisory locks (`udlock` schema) encapsulate concurrency primitives with heartbeat registries and GC routines.

#### 4.4.1 Masking profile mapping (binding)

**Breadcrumbs:** Implementation `db/migrations/tenant/002_masking_profile_policies.sql`, Tests `tests/platform/db/test_mask_profiles.py::test_mask_profile_matches_policy`, Observability Grafana “Postgres RLS & Masking” with alert `rls_context_missing_total`.

*Purpose: Map PolicyContext masking profiles onto database enforcement artifacts.*

- Masking profiles in `PolicyContext` (see `../services/lp-engine.md §2.1`) compile into `field_mask_rule` rows that parameterize the SQL policies below. Activation fails if any required profile lacks entries for `CASE`, `ARTIFACT`, `QA_LOG`, `GUARDIAN_JUDGMENT`, or `DELIVERY_RECEIPT`.

- Normative enforcement DDL (excerpt; see Appendix J for full catalog):

  ```sql
  ALTER TABLE "case"                  FORCE ROW LEVEL SECURITY;
  ALTER TABLE artifact                FORCE ROW LEVEL SECURITY;
  ALTER TABLE qa_log                  FORCE ROW LEVEL SECURITY;
  ALTER TABLE delivery_receipt        FORCE ROW LEVEL SECURITY;

  CREATE POLICY case_visibility ON "case"
  USING (
    org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
    AND udocket_can('CASE', 'read', "case".id, NULL, NULL)
  )
  WITH CHECK (
    org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
    AND udocket_can('CASE', 'write', "case".id, NULL, NULL)
  );
  ```

- Masked columns rely on `udocket_mask`/`udocket_mask_json`; the compiler injects `field_mask_rule` rows such as `('{org_uuid}', 'default', 'ARTIFACT', 'content_uri', 'REDACT', ARRAY['reviewer', 'auditor'])` and `('{org_uuid}', 'hipaa_strict', 'QA_LOG', 'notes_md', 'HASH', ARRAY['auditor'])`. Test `tests/platform/db/test_mask_profiles.py::test_mask_profile_matches_policy` verifies each profile masks the expected columns, while `tests/platform/db/test_rls_guard.py` and `tests/platform/db/test_secure_view_usage.py` assert that FORCE RLS remains active and base tables stay inaccessible.

- Normative SQL (binding):

```sql
-- Policy tables (compiled by Settings activation job)
-- effective_permission(org_id, resource, action, role, field NULLABLE)
-- field_mask_rule(org_id, profile, resource, field, mask, allowed_roles text[])

-- Central allow function (deny-by-default; sysadmin bypass)
CREATE OR REPLACE FUNCTION udocket_can(
  p_resource text,
  p_action   text,
  p_case     uuid,
  p_artifact uuid,
  p_field    text DEFAULT NULL
)
RETURNS boolean
LANGUAGE plpgsql STABLE AS $$
DECLARE v_org   uuid := NULLIF(current_setting('udocket.active_org',   true), '')::uuid;
DECLARE v_roles text := coalesce(current_setting('udocket.active_roles', true), '');
DECLARE v_scope text := coalesce(current_setting('udocket.operator_scope', true), 'own_cases');
DECLARE r text;
BEGIN
  IF udocket_has_realm_role('sysadmin') THEN RETURN true; END IF;
  IF v_org IS NULL THEN RETURN false; END IF;

  -- Enforce operator scope: when scoped to own_cases and a case is in play,
  -- deny if caller is not a member (realm sysadmin already handled above)
  IF p_case IS NOT NULL AND v_scope <> 'all_org_cases' THEN
    IF NOT udocket_is_case_member(p_case) THEN
      RETURN false;
    END IF;
  END IF;

  FOR r IN SELECT regexp_split_to_table(v_roles, ',') LOOP
    IF EXISTS (
      SELECT 1
        FROM effective_permission ep
       WHERE ep.org_id = v_org
         AND ep.resource = p_resource
         AND ep.action   = p_action
         AND ep.role     = r
         AND (
              (ep.field IS NULL AND p_field IS NULL)
           OR (ep.field IS NOT NULL AND ep.field = p_field)
         )
    ) THEN
      RETURN true;
    END IF;
  END LOOP;
  RETURN false;
END $$;

-- RLS policies rewritten to use settings-driven `udocket_can`
DROP POLICY IF EXISTS case_visibility ON "case";
CREATE POLICY case_visibility ON "case"
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('CASE', 'read', "case".id, NULL, NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('CASE', 'write', "case".id, NULL, NULL)
);

DROP POLICY IF EXISTS artifact_visibility ON artifact;
CREATE POLICY artifact_visibility ON artifact
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND EXISTS (SELECT 1 FROM "case" c WHERE c.id = artifact.case_id)
  AND udocket_can('ARTIFACT', 'read', artifact.case_id, artifact.id, NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('ARTIFACT', 'write', artifact.case_id, artifact.id, NULL)
);

DROP POLICY IF EXISTS job_vis ON job;
CREATE POLICY job_vis ON job
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND EXISTS (SELECT 1 FROM "case" c WHERE c.id = job.case_id)
  AND udocket_can('JOB', 'read', job.case_id, NULL, NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('JOB', 'write', job.case_id, NULL, NULL)
);

DROP POLICY IF EXISTS qa_vis ON qa_log;
CREATE POLICY qa_vis ON qa_log
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND EXISTS (SELECT 1 FROM "case" c WHERE c.id = qa_log.case_id)
  AND udocket_can('QA_LOG', 'read', qa_log.case_id, NULL, NULL)
);


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

-- Enforce RLS even for table owners (unchanged)
ALTER TABLE "case"                  FORCE ROW LEVEL SECURITY;
ALTER TABLE artifact                FORCE ROW LEVEL SECURITY;
ALTER TABLE job                     FORCE ROW LEVEL SECURITY;
ALTER TABLE qa_log                  FORCE ROW LEVEL SECURITY;
ALTER TABLE delivery_receipt        FORCE ROW LEVEL SECURITY;
```

| Binding                      | Implementation                                                                            | Test                                                                               | Observability                                                                     |
| ---------------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `rls_context_assert()` guard | Implementation: `apps/platform/db/guards.py::assert_rls_context`                          | Test: `tests/platform/db/test_rls_guard.py::test_rls_context_asserts_missing_gucs` | Grafana “DB Session Guards” panel — metric `rls_context_missing_total`            |
| Secure-view only access      | Implementation: `scripts/staticlint/enforce_secure_views.py` (invoked via `make lint-db`) | Test: `tests/platform/db/test_secure_view_usage.py::test_no_base_table_queries`    | Buildkite Release job output (`lint-db` step) for policy validation observability |

- Guardian table secure views, RLS bindings, and partition rotation requirements are maintained within the service; this section keeps the shared database contract concise.

- Session hardening (binding):

  - `SET LOCAL search_path = pg_catalog, public;` (prevent implicit resolution)
  - `SET LOCAL statement_timeout = '30s';`
  - `SET LOCAL idle_in_transaction_session_timeout = '15s';`
  - `SET LOCAL lock_timeout = '5s';`
  - `SET LOCAL deadlock_timeout = '200ms';`
  - Enforce `ALTER DEFAULT PRIVILEGES` for the application role to prevent accidental base table grants.

- Priority: High (security gating and policy determinism)

- RLS and masking policies enforced even for table owners via `ALTER TABLE ... FORCE ROW LEVEL SECURITY`, ensuring administrative sessions respect policies.

- Operational canaries verify GUC presence and pooling mode; see `App.J` for SQL snippets (`rls_context_ok` check, boot probe, search_path/timeout guard).

### 4.5 Field-level masking, auditing, and break-glass procedures

*Purpose: Explain the masking controls, audit logging, and emergency procedures for sensitive data.*

- `udocket_mask` / `udocket_mask_json` apply redaction, hashing, or nulling per `field_mask_rule`; JSON fields accept only REDACT/NULL so the compiler cannot emit unsupported modes.
- Masked secure views (`case_secure`, `artifact_secure`, `qa_log_secure`, etc.) are the only read surfaces granted to the application role. Sysadmin remains the sole bypass for investigations, and break-glass events are dual-approved and watermarked.
- Audit trail essentials: `audit_event` logs every significant read/write; `entitlement_snapshot` records token issuance with device fingerprints; `guardian_span_detection` stores PHI/PII evidence under RLS.
- Break-glass usage logs justification, duration, reviewer acknowledgement, and triggers watchdogs that terminate sessions on expiry. Post-event review queues ensure accountability.
- Structured logs (case/job correlated) and anomaly detectors watch for unusual read patterns or mass token reveals; alerts map to Guardian Appendix B runbooks (RB-GUARD-\*) and RB-MASK (`../ops/runbooks/index.md`).

#### 4.5.1 Transformation modes & operator view (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/masking/profiles.py::render_transformation_modes`, Tests `tests/security/test_masking_profiles.py::test_mode_rendering`, Observability Grafana “Masking Vault & Profiles” dashboard.

*Purpose: Define masking modes, operator experience, and deliverable implications.*

| Mode                                    | When to use                                                             | Operator view                                            | Deliverable                   |
| --------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------- | ----------------------------- |
| **Redaction** (irreversible)            | Value must never be stored or restored (for example, API credentials).  | `████` or `REDACTED`.                                    | Remains redacted permanently. |
| **Pseudonymization** (reversible token) | Value needed for analytics/ops but must stay masked during preparation. | Deterministic alias such as `[NAME-1]`, `SSN{•-•-1234}`. | Restored when policy allows.  |
| **Format-Preserving Encryption (FPE)**  | Structured identifiers requiring valid shape (SSN, MRN, phone).         | Appears syntactically valid, e.g., `***-**-1A92`.        | Restored when policy allows.  |

- Masking metadata captures `{span_id, mode, token_id?, vault_namespace, policy, restorable}` and is stored alongside Guardian detections (§7.1.0) using `uuidv7` identifiers.
- Operators and reviewers receive masked drafts by default; restoration requires explicit policy intents (§4.5.4) or a break-glass workflow.
- Organization policies decide the default mode per entity type. Profiles ship with HIPAA-safe defaults; Reference Manager entries add jurisdiction-specific overrides.

#### 4.5.2 Token vault & reversible masking (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/masking/vault.py`, Tests `tests/security/test_fpe_tokenization.py::test_round_trip`, Observability Grafana “Masking Vault & Profiles” with metric `masking_vault_token_total`.

*Purpose: Describe token vault design, cryptography, and access controls.*

- Design: replace sensitive spans with deterministic tokens stored in an isolated Token Vault. Namespaces segment by `{org}:{case}` to prevent cross-case collisions.
- Envelope encryption: each record stores `{token, hash(original|salt), entity_type, format_meta, created_at, created_by, uses[]}`. A per-record DEK encrypts the plaintext; the DEK is wrapped by a KEK in Managed HSM (FIPS mode). Rotation evidence lives in `ops/security/masking_key_rotation/<timestamp>.json`.
- Determinism: repeated occurrences derive the same token within a namespace. Salts rotate with KEK rotation and are versioned so replay jobs remain deterministic.
- Access controls: only Compose/Signing services and a tightly scoped “reveal” flow may detokenize. Break-glass requires dual approval, emits `TOKEN_REVEAL_REQUEST` artifacts, and watermarks the reviewer session. Operators never receive detokenize privileges without explicit policy + waiver.
- Settings: `security.masking.vault_profile ∈ {fpe_v1, aes_gcm_v1}` selects the algorithm (FF3-1 for identifiers, AES-256-GCM for free-form values). `security.masking.vault_key_id` references the active KEK; rotations follow dual-publish (`current`, `next`) with 24-hour overlap.
- Observability: manifests include `{masking_profile_id, token_vault_version, masking_hash_algorithm, fips_mode, fips_module_cert_id}`. Vault events append to `ops/security/masking_vault.jsonl`; metrics (`masking_vault_token_total`, `masking_vault_reveal_total`, `masking_vault_latency_seconds`) back dashboards.
- Quality gates: `tests/security/test_fpe_tokenization.py` verifies format preservation; `tests/security/test_masking_restore_flow.py` enforces approval semantics; synthetic `synthetics/masking_vault_health.yaml` checks HSM availability, determinism, and attestation.

#### 4.5.3 Masking rule catalogue (normative)

*Purpose: Catalog masking rules for common data types and how policies apply them.*

- **Names:** `[PATIENT-#]`, `[PROVIDER-#]` with case-wide stable numbering derived from span UUID.
- **Addresses:** `[ADDR-#]`; policy may keep city/state/ZIP visible, masking street-level detail.
- **Emails / phones:** FPE with final characters visible (`•••••@example.com`, `(***) ***-1234`); `format_meta` retains domain/country metadata.
- **Identifiers (SSN/MRN/Insurance):** FF1/FF3 FPE with domain constraints; expose last four digits when policy allows.
- **Dates:** generalized to month/year unless restoration intent is declared.
- **Free text PHI/SPI:** segmented spans replaced with tokens; token records accumulate `uses[]` entries for each artifact/job referencing them.

#### 4.5.4 Restoration & deliverable policy (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/masking/restoration.py`, Tests `tests/platform/compose/test_restoration_policy.py::test_restoration_requires_policy_intent`, Observability Grafana “Compose Restoration & Vault” with alert `token_reveal_total`.

*Purpose: Specify restoration scenarios and deliverable policies governed by masking intents.*

- Compose requests `POST /vault/detokenize` with `{object_urn, token_ids[], purpose ∈ {CLIENT_DL, LEGAL_DL, INTERNAL}}` once a CD reaches APPROVED and policy requires restoration. Vault enforces purpose-based allowlists and expiry windows.
- Policy intents (for example, `privacy.masking.intent = deidentified` vs `full_record`) decide which entity types restore. “De-identify client copy” keeps tokens; “Full legal record” restores identifiers required for filings.
- Restoration responses stream plaintext spans directly to Compose; plaintext never hits logs. Deliverables embed an auxiliary record summarizing `{token_count, masking_profile_id, vault_namespace, restored_types[], policy_intent, hsm_key_id}`.
- Manual/Agent edit flows create new CD versions with inherited tokens; restoration repeats only after Guardian clears the edited version, preserving deterministic lineage.

#### 4.5.5 Masking helpers & enforcement (normative)

*Purpose: Provide helper functions and enforcement patterns that implement masking.*

Masking helpers (normative)

```sql
CREATE OR REPLACE FUNCTION udocket_mask(value text, mask text)
RETURNS text LANGUAGE plpgsql STABLE AS $$
BEGIN
  CASE mask
    WHEN 'REDACT' THEN RETURN '[REDACTED]';
    WHEN 'HASH' THEN RETURN encode(digest(coalesce(value, ''), 'sha256'), 'hex');
    WHEN 'NULL' THEN RETURN NULL;
    ELSE RAISE EXCEPTION 'Invalid mask %', mask;
  END CASE;
END $$;

CREATE OR REPLACE FUNCTION udocket_mask_json(value jsonb, mask text)
RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
BEGIN
  CASE mask
    WHEN 'REDACT' THEN RETURN '"[REDACTED]"'::jsonb;
    WHEN 'NULL' THEN RETURN 'null'::jsonb;
    ELSE RAISE EXCEPTION 'Invalid JSON mask %', mask;
  END CASE;
END $$;
```

Secure view example (security barrier)

```sql
CREATE VIEW artifact_secure WITH (security_barrier=true) AS
SELECT id, org_id, case_id, type, status, content_sha256,
       CASE
         WHEN udocket_can('ARTIFACT', 'read', artifact.case_id, artifact.id, 'content_uri') THEN content_uri
         ELSE udocket_mask(
                content_uri,
                COALESCE(
                  (
                    SELECT r.mask
                      FROM field_mask_rule r
                     WHERE r.org_id = artifact.org_id
                       AND r.profile = COALESCE(
                             NULLIF(current_setting('udocket.mask_profile', true), ''),
                             'default'
                           )
                       AND r.resource = 'ARTIFACT'
                       AND r.field = 'content_uri'
                     LIMIT 1
                  ),
                  'REDACT'
                )
              )
       END AS content_uri,
       manifest
  FROM artifact;
```

- `artifact` stores tombstone metadata columns (`deleted_at`, `deleted_by`, `deletion_trigger`, `deletion_certificate_id`, `deletion_request_id`, `erasure_journal_id`, `retention_schedule_version`, `deletion_manifest_sha256`, `tombstone_pruned_at`). Populating them is mandatory whenever `status IN ('ARCHIVED', 'DELETED')`; retention automation records its service principal in `deleted_by`.
- Settings activation maintains `CREATE INDEX field_mask_rule_org_profile_resource_field ON field_mask_rule(org_id, profile, resource, field)` and precomputes effective allowlists into helper tables so hot paths avoid repeated subqueries; helpers refresh atomically with each activation.
- Lint guard: `scripts/db/lint_status_column.py` scans generated DDL and ORM migrations to block accidental reintroduction of a `state` column name; CI job `lint-db-state-column` fails on violations and points to §5.2 for the canonical `status` vocabulary.
- Vault tables mirror database RLS policies and honor the active masking profile; quarterly audits replay detokenization requests to confirm least-privilege enforcement.

## 5) Artifact data layer & storage integrity

### 5.1 Relational schema overview

*Purpose: Summarize the durable tables, helpers, and invariants that back artifact storage.*

- **user_account:** UUIDv7 `id`, `keycloak_sub`, contact fields, optional `default_org_id`. Keeps reference integrity without duplicating org membership logic.

- **case:** UUIDv7 `id`, `org_id` FK, `title`, `representation_type`, `status`, legal hold fields, audit columns. Write-once invariants enforced via triggers (legal hold reason mask applied via secure view).

- **case_member:** Composite PK `(user_id, case_id)` storing per-case role; informs `udocket_is_case_member`.

- **artifact:** UUIDv7 `id`, `org_id`, `case_id`, `type`, `class` (`SA|WP|CD|DL|AR`), `status`, `content_uri`, `content_sha256`, JSONB `manifest`, OCC `version`, review metadata (`approval_type`, `approved_at/by`, reviewer notes). Trigger `artifact_immutable_check` blocks changes to immutable fields; a view projects `status` into reviewer-facing phases.

- Immutability trigger (binding):

  ```sql
  CREATE OR REPLACE FUNCTION artifact_immutable_check()
  RETURNS trigger LANGUAGE plpgsql AS $$
  BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.status NOT IN ('PROCESSING', 'OPERATOR_PREP', 'CHANGES_REQUESTED') THEN
      IF NEW.org_id <> OLD.org_id
         OR NEW.case_id <> OLD.case_id
         OR NEW.type <> OLD.type
         OR NEW.content_uri <> OLD.content_uri
         OR NEW.content_sha256 <> OLD.content_sha256
         OR NEW.manifest <> OLD.manifest THEN
        RAISE EXCEPTION 'Immutable artifact fields cannot change once promoted';
      END IF;
    END IF;
    RETURN NEW;
  END;
  $$;
  CREATE TRIGGER artifact_immutable_trg
    BEFORE UPDATE ON artifact
    FOR EACH ROW EXECUTE FUNCTION artifact_immutable_check();
  ```

- **job**, **job_task**, **job_checkpoint:** Track orchestration progress, settings snapshot hashes, checkpoint JSONB, and OCC versions to support retries.

- **qa_log**, **delivery_receipt**, **audit_event**, **entitlement_snapshot** provide governance history with RLS and secure views.

- **settings bundles:** Stored via Settings Service (see §9) but referenced in jobs (`settings_snapshot_sha256`) and manifests for traceability.

- ERD lives in `App.G`; state diagrams in `App.A` illustrate artifact/job lifecycles.

- Binding breadcrumbs:

  | Binding                       | Implementation                                                                          | Test                                                                                   | Observability                                                                                     |
  | ----------------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
  | Artifact immutability trigger | Implementation: `apps/platform/artifacts/migrations/0024_artifact_immutable_trigger.py` | Test: `tests/platform/artifacts/test_immutability.py::test_update_blocked_after_draft` | Observability: Audit event `ARTIFACT_IMMUTABILITY_VIOLATION` (Alert: “Artifact Immutable Breach”) |

### 5.2 Artifact lifecycle (authoritative)

**Purpose:** Define artifact classes, canonical statuses, and the only valid transitions.\
**Contract:** Agents, services, and APIs MUST emit statuses and judgments exactly as defined in this section; reruns produce additive versions without mutating prior outputs.\
**State transitions:** Governed by §5.2.2 (statuses), §5.2.3 (Guardian mapping), and §5.4.1 (ExclusiveSwap invariant); App.A.2 diagrams the same state machine.\
**Failure modes & retries:** Guardian `BLOCK` or reviewer quarantine follow remediation/waiver loops in §5.2.3–§5.2.5; watchdogs and approval conflicts escalate via RB-APPROVAL-001 and [Runbook RB-JOB-WATCHDOG](../ops/runbooks/index.md#rb-job-watchdog).\
**Observability:** `artifact.status`, `guardian_judgment_latency_seconds`, `approval_swap_conflict_total`, `portal_link_invalidated`, and `docs_template_missing_total`.\
**Breadcrumbs:** Implementation `packages/udocket_core/artifacts/status.py`, Tests `tests/platform/artifacts/test_status_vocab.py::test_all_statuses_linked`, Observability Grafana “Artifact Lifecycle” dashboard.\
**References:** §5.2.1–§5.2.8, §5.4.1, §7.1, §10.3.2, App.A, App.I.

**Invariants:**\
– No operator can view WP/CD prior to Guardian PASS/WARN (see §5.2.3).\
– Only one `RELEASED` DL exists per `(case_id, type)`; approvals atomically revoke the prior DL (ExclusiveSwap invariant, §5.4.1).\
– Append-only audit: every lifecycle action appends to `ops_<agent>.jsonl` and persists manifests with SHA-256 provenance.

<div style="display: flex; flex-wrap: wrap; gap: 1.5rem; margin: 1.25rem 0;">
  <figure style="flex: 1 1 18rem; text-align: center; margin: 0;">
    <img class="diagram" src="../build/mermaid/overview/tdd/diagrams/artifact-lifecycle-overview-v1.png" alt="Artifact lifecycle overview">
    <figcaption style="font-size: 0.9em; color: #555; margin-top: 0.5rem;">Overview — SA ➜ WP ➜ CD ➜ DL.RELEASED ➜ Retention gate</figcaption>
  </figure>
  <figure style="flex: 1 1 18rem; text-align: center; margin: 0;">
    <img class="diagram" src="../build/mermaid/overview/tdd/diagrams/artifact-wp-lifecycle-v1.png" alt="Work Product lifecycle">
    <figcaption style="font-size: 0.9em; color: #555; margin-top: 0.5rem;">Work Product — Guardian gating to <code>CLEARED_FOR_USE</code></figcaption>
  </figure>
  <figure style="flex: 1 1 18rem; text-align: center; margin: 0;">
    <img class="diagram" src="../build/mermaid/overview/tdd/diagrams/artifact-cd-lifecycle-v1.png" alt="Candidate Deliverable lifecycle">
    <figcaption style="font-size: 0.9em; color: #555; margin-top: 0.5rem;">Candidate Deliverable — operator and reviewer rail to release</figcaption>
  </figure>
</div>
<div style="font-size: 0.85em; color: #666; margin: -0.5em 0 1.5em 0;">
  Legacy diagrams labeled the post-Guardian handoff as <code>READY</code>; the canonical vocabulary is now <code>CLEARED_FOR_USE</code> (WP) and <code>OPERATOR_PREP</code> (CD). The overview’s diamond depicts the retention/erasure gate as a policy decision rather than a lifecycle status, while the detailed diagrams enumerate the class-specific states that feed that gate.
</div>

Work Product that reaches `CLEARED_FOR_USE` becomes selectable input for Analyze/Compose/Timeline lanes and may emit new CDs without re-submitting source assets. Candidate Deliverables inherit the prior Guardian verdict and either progress through operator/reviewer approval (`OPERATOR_PREP → APPROVAL_REQUESTED → QUEUED_FOR_REVIEW → APPROVED`) or loop for remediation. Signing and portal release convert an approved CD into the Deliverable class at status `RELEASED`; replacements revoke the previous release but retain manifests for audit. At any point, retention jobs or certified client erasure requests may invoke the gate, which records the tombstone metadata required in §5.2.2 and §14.2 before entering `ARCHIVED` or `DELETED`.

#### 5.2.1 Object classes (SA/WP/CD/DL/AR)

*Purpose: Classify artifact types and clarify their lifecycle boundaries.*

| Class                     | Key    | Purpose                                                                | Examples                                                                                                | Visibility          |
| ------------------------- | ------ | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------- |
| **Source Asset**          | **SA** | Raw inputs we ingest. Immutable post-write.                            | Uploaded audio/video, PDFs, exhibits, notes                                                             | Staff (scoped)      |
| **Work Product**          | **WP** | Internal derived data used to build deliverables; never client-facing. | Issues/timeline/entities/facts/gaps (JSON), interim LLM outputs, scores                                 | Staff only          |
| **Candidate Deliverable** | **CD** | Human-readable draft intended for potential external release.          | Transcript draft, client summary draft, composed report draft                                           | Staff reviewers/ops |
| **Deliverable**           | **DL** | Approved, signed, releasable document (client-visible).                | Transcript (final), client summary (final), bundle, signed report                                       | Staff + client      |
| **Auxiliary Record**      | **AR** | Proofs/receipts/logs backing compliance.                               | Audit events, waiver records, hash manifests, job cancellation reports, TSA tokens, signature envelopes | Auditors/admin      |

Separation of concerns: **WP** stays internal, **CD** is the curated draft surface operators work in, **DL** is the only client-visible output, and **AR** carries the attestations that prove what happened.

#### 5.2.2 Statuses

*Purpose: Define the status vocabulary and transitions for each artifact class.*

Status is scoped by object class and standardizes lifecycle semantics.

| Status                 | Applies to     | Meaning                                                                           | Entered by            | Leaves when                                                                            |
| ---------------------- | -------------- | --------------------------------------------------------------------------------- | --------------------- | -------------------------------------------------------------------------------------- |
| **STORED**             | SA             | Source durably persisted and hashed.                                              | System                | Pipeline starts → **PROCESSING**                                                       |
| **PROCESSING**         | WP, CD         | System is generating/transforming.                                                | System                | Work done → **PENDING_JUDGMENT** or **FAILED**                                         |
| **FAILED**             | WP, CD         | System error/missing dependency.                                                  | System                | Retry/repair → **PROCESSING**                                                          |
| **PENDING_JUDGMENT**   | WP, CD         | Awaiting review judgment.                                                         | System                | Guardian decides (see §5.2.3)                                                          |
| **CLEARED_FOR_USE**    | WP             | PASS/WARN unlocks internal use; downstream agents may spawn new CDs/deliverables. | Guardian              | Consumed downstream or replaced                                                        |
| **OPERATOR_PREP**      | CD             | PASS/WARN, operator workspace to curate/edit.                                     | Guardian              | Operator requests review → **APPROVAL_REQUESTED**                                      |
| **APPROVAL_REQUESTED** | CD             | Operator submitted for review; awaiting queue assignment/triage.                  | Operator/System\*     | Reviewer accepts assignment → **QUEUED_FOR_REVIEW**                                    |
| **QUEUED_FOR_REVIEW**  | CD             | Reviewer actively evaluating the draft.                                           | System                | Reviewer acts (see §5.2.4)                                                             |
| **CHANGES_REQUESTED**  | CD             | Reviewer rejected with edit instructions.                                         | Reviewer              | New CD version → **OPERATOR_PREP** (then **APPROVAL_REQUESTED**/**QUEUED_FOR_REVIEW**) |
| **QUARANTINED**        | WP, CD         | Policy violation.                                                                 | Guardian/Reviewer     | Waiver or remediation → **OPERATOR_PREP**/**CLEARED_FOR_USE**                          |
| **APPROVED**           | CD             | Human-approved draft (or auto-approved).                                          | Reviewer/System\*     | Signing → **SIGNED**                                                                   |
| **SIGNED**             | DL             | uDocket-signed, TSA timestamped.                                                  | Signer                | Published → **RELEASED**                                                               |
| **RELEASED**           | DL             | Visible/downloadable in portal.                                                   | System                | Replacement policy (see §5.2.6)                                                        |
| **REVOKED**            | DL             | Pullback due to approval swap, policy error, or compliance request.               | System/Admin/Guardian | Retained, non-downloadable; archived via retention                                     |
| **ARCHIVED**           | SA/WP/CD/DL    | Frozen under retention; content retained under legal/ops hold.                    | System                | Retention clock expires or approved erasure → **DELETED**                              |
| **DELETED**            | SA/WP/CD/DL/AR | Content removed; only tombstone + audit metadata remain.                          | System                | Retention evidence window closes → purged tombstone (§14.2)                            |

Transitions into **ARCHIVED** or **DELETED** are mediated by the retention/erasure gate captured in App.A.2. The gate only opens when legal holds are clear *and* one of two triggers fires: (a) retention scheduler reaches the configured destruction window, or (b) a certified client erasure request is approved. Every call path MUST populate tombstone metadata before committing the status change:

- `deleted_at TIMESTAMPTZ`, `deleted_by UUID` (service or human actor), and `deletion_trigger TEXT` (`retention_expired` | `client_erasure`).
- `deletion_certificate_id UUID` pointing to the authoritative `DESTRUCTION_CERT` (case purge) or `deletion_request_id UUID` pointing to the DSAR request; both reference immutable `ERASURE_JOURNAL` manifests.
- `erasure_journal_id UUID`, `retention_schedule_version TEXT`, and `deletion_manifest_sha256 TEXT` so auditors can verify provenance even after payload removal.

Tombstones persist in primary storage until the retention evidence window in §14.2 elapses; pruning the tombstone emits an audit event (`ARTIFACT_TOMBSTONE_PURGED`) and updates the same metadata fields with `tombstone_pruned_at`.

`System*` denotes flows where org configuration auto-submits for review or permits skipping human review (see §5.2.5).

#### 5.2.3 Guardian judgment → status mapping (binding)

*Purpose: Summarize how Guardian judgments advance artifact states and reference `../services/guardian.md` for detailed mechanics.* *Contract: Judgment vocabulary, policy enforcement, detection pipelines, and APIs live in `../services/guardian.md`; this section covers the lifecycle impacts other services must honor.*

- `PASS` / `WARN` / `WAIVED` → **WP:** `CLEARED_FOR_USE`, **CD:** `OPERATOR_PREP`.
- `BLOCK` → **WP/CD:** `QUARANTINED` until remediation or waiver.
- Parent gating and HIPAA/SPI posture are resolved inside Guardian; manifests retain `guardian_judgment_id`, `guardian_policy_snapshot_id`, and waiver metadata for audit replay.

Full detection schemas, queue semantics, replay tooling, and manual quarantine workflows remain documented with the Guardian service. Events for these transitions remain enumerated in §10.3.

#### 5.2.4 Human review (tri-outcome) with enumerated reasons

*Purpose: Outline human review states, reasons, and queue behavior.*

When a **CD** is **QUEUED_FOR_REVIEW**, reviewers must pick exactly one outcome:

1. **APPROVE** → status **APPROVED** (optional comment).
1. **REJECT (CHANGES_REQUESTED)** → status **CHANGES_REQUESTED**, mandatory `reject_reason` + free text.
1. **QUARANTINE** → status **QUARANTINED**, mandatory `quarantine_reason` + free text; routed via Guardian for single source of record.

`RejectReason` enum:

{ ACCURACY_ISSUE, INCOMPLETE_CONTENT, FORMATTING_LAYOUT, TONE_STYLE_QUALITY, SCOPE_MISMATCH, SOURCE_MISMATCH, REDACTION_REQUIRED, DUPLICATE_OBSOLETE, DATA_QUALITY_INPUT, POLICY_CONCERN, OTHER }

`QuarantineReason` enum:

{ RESIDENCY_POLICY_BLOCK, HIPAA_REQUIRED, PII_UNMASKED, DLP_VIOLATION, SAFETY_CONTENT, MALWARE_DETECTED, LEGAL_HOLD, FINOPS_BUDGET_EXCEEDED, HASH_MISMATCH_TAMPER, PROVIDER_REGION_UNVERIFIED, CLASSIFIER_LOW_CONFIDENCE, REQUESTED_BY_ADMIN, OTHER, }

“OTHER” selections require `*_other_text` payloads and feed a weekly clustering job (`ops/reference/suggest_reason_enum.py`). The job publishes candidate enum additions to Reference Manager; accepted values propagate through the LPE bundle workflow. Operations uphold an SLO to triage new candidates within 14 calendar days and either promote or close them (with rationale) within 30 days, with status tracked in the Reference Manager queue dashboard. When a candidate is promoted, Guardian ships the new enum in the next release, bumps the SSE/event schema version noted in §10.3, and publishes an upgrade notice so API consumers can deploy the updated enum set before enforcement.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/mermaid/services/guardian/diagrams/approvals-edit-flows-v1.png" alt="Manual and agent edit approval flows">
  <figcaption style="font-size: 0.9em; color: #555;">Manual and agent edit approval flows</figcaption>
</figure>

#### 5.2.5 Review modes & risk overrides

*Purpose: Compare review modes and document when risk overrides are permitted.*

Settings surface the following:

```pseudocode
review.mode ∈ {
  MANUAL,             # PASS/WARN → OPERATOR_PREP → APPROVAL_REQUESTED (operator submits)
  SKIP_OPERATOR_PREP, # PASS/WARN → QUEUED_FOR_REVIEW (system enqueues immediately)
  SKIP_REVIEW,        # PASS/WARN → APPROVED (record REVIEW.SKIPPED if no overrides apply)
  SKIP_ALL            # PASS/WARN → APPROVED (operator workspace optional; REVIEW.SKIPPED emitted)
}

review.risk_overrides:
  - PHI_DETECTED
  - LEGAL_HOLD
  - CLASSIFIER_LOW_CONFIDENCE
  - NEW_MODEL_OR_PROMPT
  - QUARANTINE_HISTORY
```

Guardian judgments always run **before** these modes and gate whether operators can access the artifact. `review.mode` defaults to `MANUAL` per organization (case overrides allowed) and determines the deterministic state transitions after a PASS/WARN judgment:

| Mode                   | After Guardian PASS/WARN                                             | Next transitions                                                                         |
| ---------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **MANUAL**             | **OPERATOR_PREP**                                                    | Operator requests review → **APPROVAL_REQUESTED → QUEUED_FOR_REVIEW** → reviewer outcome |
| **SKIP_OPERATOR_PREP** | **QUEUED_FOR_REVIEW**                                                | Reviewer outcome (**APPROVED** / **CHANGES_REQUESTED** / **QUARANTINED**)                |
| **SKIP_REVIEW**        | **APPROVED** (`approval_type=SKIPPED_REVIEW`, emit `REVIEW.SKIPPED`) | Sign → **SIGNED** → **RELEASED**                                                         |
| **SKIP_ALL**           | **APPROVED** (`approval_type=SKIPPED_REVIEW`, emit `REVIEW.SKIPPED`) | Sign → **SIGNED** → **RELEASED**                                                         |

PASS/WARN transitions follow the table above: WP always enters **CLEARED_FOR_USE** while CD jumps to the next state dictated by `review.mode` (OPERATOR_PREP, QUEUED_FOR_REVIEW, or APPROVED).

Risk overrides force the artifact back through human review regardless of mode: if any listed condition is true, the system transitions to **APPROVAL_REQUESTED → QUEUED_FOR_REVIEW** even when the configured mode would skip the queue. `REVIEW.SKIPPED` events include `{review_mode, overrides_applied}` so auditors can confirm when automation made the decision versus when overrides intervened. App.A’s state diagrams annotate each branch so the default, queue-first, and skip flows remain visually distinct. Portal fetch-time checks continue to block revoked deliverables regardless of mode.

Guardian enforces `org.guardian.pre_operator_gates[]` by blocking operator visibility until PASS/WARN occurs for each listed class (commonly `SA`, `WP`, and `CD` in regulated orgs); UI surfaces a “Guardian pending” banner when operators attempt to open gated artifacts.

#### 5.2.6 Deliverable replacement policy

*Purpose: Define replacement rules when new deliverables supersede prior approvals.*

Exclusive deliverables use **approval swap** semantics:

- Promoting a new **APPROVED** candidate deliverable of an exclusive type automatically revokes the previously released **DL** (`status → REVOKED`) and invalidates portal links/ETags.
- Revoked deliverables remain retained for audit, replay, and manifest comparison; retention jobs eventually archive per policy.
- Compliance-driven takedowns still use explicit revocations (`revocation_reason` records initiator + rationale).

#### 5.2.7 Cross-object controls and audit surface

*Purpose: Summarize cross-object controls and audit signals tied to each artifact.*

- Hashing: `content_hash` is SHA-256 for every object; multi-file bundles publish Merkle roots as **AR** “hash manifest” records (JWS signed).
- Signatures: **DL** (and signature-bearing **AR**) require PAdES B-LTA for PDF, JWS RS256 or COSE_Sign1 for JSON, plus RFC-3161 TSA tokens. Metadata includes signer chain, TSA info, `content_hash`, `model_run_id`, `guardian_judgment_id`, settings snapshot hash, `approval_type`, `approved_by`, `fips_mode` (`true|false`), and when true the `{fips_module_cert_id, fips_validation_level, fips_drbg_source}` reported by the performing module.
- Optional client counter-signatures produce linked **AR** records.
- Policy & controls matrix (excerpt):

| Control                   |         SA |            WP |                            CD |                       DL |                         AR |
| ------------------------- | ---------: | ------------: | ----------------------------: | -----------------------: | -------------------------: |
| SHA-256 on create         |          ✓ |             ✓ |                             ✓ |                        ✓ |                          ✓ |
| Content-addressed storage |          ✓ |             ✓ |                             ✓ |                        ✓ |                          ✓ |
| Guardian judgment         |  (limited) | **Selective** |                 **Mandatory** |  **Fetch-time re-check** |                          — |
| Operator prep workspace   |          — |             — |                   **Default** |                        — |                          — |
| Human review              |          — |             — | per `review.mode` / overrides |                        — |                          — |
| Digital signature + TSA   |          — |             — |                             — |                    **✓** | **✓** (manifests/receipts) |
| Client counter-sign       |          — |             — |                             — |             **Optional** |                          — |
| Residency enforcement     | **Strict** |    **Strict** |                    **Strict** |               **Strict** |                 **Strict** |
| Portal visibility         |          ✗ |             ✗ |                             ✗ | **Only latest RELEASED** |                          ✗ |

#### 5.2.8 Schema & configuration guardrails

*Purpose: Keep database schema, Settings, and manifests aligned with the authoritative lifecycle.*

- Shared schema fields:
  - `id` (UUIDv7), `class ∈ {SA, WP, CD, DL, AR}`, `status`, `version` (OCC)
  - `org_id`, `case_id`, `created_by`, `created_at`, `updated_at`
  - `content_hash`, `size_bytes`, `mime`, `storage_key`, `labels[]`
  - `depends_on_canceled_job` (bool, nullable; set when rerun is required after cancellation)
  - `guardian_judgment`, `guardian_reason_codes[]`, `guardian_judgment_id`, `judged_at`
  - `qa_assessments[]` (`type`, `score`, `notes`, `model_id`, `threshold_result`)
  - CD-only review metadata: `approval_type ∈ {HUMAN, SKIPPED_REVIEW}`, `approved_by`, `reviewed_at`, `reject_reason`, `reject_note`, `reject_reason_other_text?`, `quarantine_reason`, `quarantine_note`, `quarantine_reason_other_text?`
  - DL-specific fields: `signature_type`, `signature_ref`, `tsa_ref`, `released_at`, `revoked_at?`, `revocation_reason?`, `revoked_by_artifact_id?` (links successor created by ExclusiveSwap)
- Settings knobs (managed via Settings Service; defaults enforced in §9):

```pseudocode
review.mode: MANUAL | SKIP_OPERATOR_PREP | SKIP_REVIEW | SKIP_ALL
review.risk_overrides: [PHI_DETECTED, LEGAL_HOLD, CLASSIFIER_LOW_CONFIDENCE, NEW_MODEL_OR_PROMPT, QUARANTINE_HISTORY]
review.approval_type.default: HUMAN | SKIPPED_REVIEW
org.guardian.pre_operator_gates[]: ["SA", "WP", "CD"]
security.masking.vault_profile: fpe_v1 | aes_gcm_v1
security.masking.vault_key_id: kv://.../keys/masking-default
i18n.fallback_chain: { "fr-CA": ["fr", "en"], "es-MX": ["es", "en"] }
i18n.required_rtl_locales[]: ["ar-SA", "he-IL"]
enums.reject_reason: managed via Reference Manager (list in §5.2.4)
enums.quarantine_reason: managed via Reference Manager (list in §5.2.4)
```

- Settings behaviour: `review.mode` defaults at the org scope (case overrides permitted). Guardian PASS/WARN always set **WP → CLEARED_FOR_USE** and then choose the **CD** next state per `review.mode` (OPERATOR_PREP for `MANUAL`, QUEUED_FOR_REVIEW for `SKIP_OPERATOR_PREP`, APPROVED for the `SKIP_*` family). `review.approval_type.default` MUST remain `HUMAN` whenever a skip mode is inactive. `org.guardian.pre_operator_gates[]` lists classes that require PASS/WARN before operators see content. Masking and i18n settings bind to the vault (§4.5.2) and localization contract tests (§11.3). Settings edits follow dual approval (§9) and emit `SETTINGS_CHANGE_REQUESTED` audit events.
- API exposure: §10.4 documents REST/GraphQL surfaces for these fields; UI uses derived view `artifact_review_phase` to avoid duplicating status logic.
- Manifests remain the provenance source (schema/graph versions, input lineage, settings snapshot hash, computed SHA-256, regions, template versions, dependency SHAs). Each agent appends `.log`, `.json`, and `ops_<agent>.jsonl` entries; data lineage diagrams in App.R visualize the same relationships.

### 5.3 Object storage layout & integrity guarantees

*Purpose: Define paths, hashing, and security controls for artifacts and media.*

- Case root: `storage/media/<ORG_ID>/cases/<CASE_ID>/` with categories:
  - `audio/<job_id>__<original>` — original uploads and normalized audio
  - `transcript/<job_id>__transcript.txt` — primary transcripts
  - `analysis/` — Analyze outputs (summaries, outlines, seeds, hints, staff reports)
  - `docs/` — Compose deliverables (client/lawyer, bundle, QA/staff reports) and portal messaging attachments (`ATTACHMENT_*`)
  - `ops/` — human logs, per-run JSON, and append-only `ops_<agent>.jsonl` audit streams
- Integrity: compute and persist `content_sha256` for all immutable artifacts; manifests include SHA-256 of outputs and `settings_snapshot_sha256` for provenance. Batch mode may record remote hashes (`BATCH_HASH_REMOTE=1`, `BATCH_HASH_MAX_MB`).
- Versioning: reruns must not overwrite prior outputs; suffix filenames with `_v{n}` and update manifests. Object storage buckets enable versioning for rollback and audit defense.
- Security: buckets are private by default with server-side encryption (SSE-KMS). Access via short-lived signed URLs; range requests supported for large downloads. Egress and region policies enforce the per-org residency allowlist.
- Normalization: audio inputs normalized to PCM 16 kHz mono when feasible (ffmpeg); normalized copies stored with job-prefixed names for reproducibility and reprocessing.
- Immutability: artifacts are treated as write-once; update attempts to immutable fields are rejected by database triggers. Deletions rely on retention/legal-hold settings (see §14.2).
- Telemetry: object storage latency and hash mismatch counters exported; nightly integrity sweeps sample-verify SHA-256 and bucket versioning state.
- Path template: `storage/media/<ORG_ID>/cases/<CASE_ID>/artifacts/<ARTIFACT_ID>/content.bin|manifest.json`; case-level directories include `audio/`, `transcript/`, `analysis/`, `docs/`, `ops/`. Legacy `storage/media/cases/<CASE_ID>/` layouts are deprecated and blocked in new deployments.
- Ingest sequence: uploads land in an encrypted staging container per residency region (`storage.staging.<region>`). Malware/PII scanners, checksum verification, and optional format normalization operate on the staging copy. Only once Guardian returns `PASS` or `WARN` does the finalize step promote the asset into the permanent case directory; `BLOCK` or failed scans trigger `storage.purge_blocked_uploads` so unreviewed data never persists beyond the staging SLA defined by `storage.staging.retention_hours`. Redaction jobs write sanitized derivatives back into staging; the promoted artifact always references the redacted output, preserving zero-copy residency guarantees.
- Upload staging uses `upload_session` records with expected hashes and single-use tokens; finalize promotes staged object into artifact storage.
- `upload_session` (transient) table persists resumable upload metadata and scan status: `{id UUID PK, org_id, case_id, status ENUM('PENDING', 'UPLOADED', 'SCANNING', 'FINALIZED', 'ABORTED'), staging_uri, expected_sha256, expires_at, created_at}`. Workers purge expired rows hourly and hard-delete the corresponding staging objects.
- SHA-256 computed at write; persisted in `artifact.content_sha256`. Reads recompute and quarantine inconsistencies (`ARTIFACT_INTEGRITY_MISMATCH`).
- Buckets enable versioning + object lock for immutable audit sinks (per §14.2). KMS keys scoped per org when configured (`storage.kms.key_scoping='per_org'`).
- QA diagnostics stored separately under `/job/{job}/qa_logs/{qa_log}/` to keep non-artifact notes; reviewer-visible QA reports remain Guardian-gated artifacts under `docs/`.

### 5.4 Advisory locking & concurrency controls

*Purpose: Prevent double-processing and ensure idempotent behavior across workers.*

- `udlock` schema implements hashed advisory locks (`scope:key`) with helpers for session and transaction locks, plus registry tables capturing holder PIDs, node IDs, and heartbeat timestamps.
- Instrumented wrappers (`udlock.try_lock_i`, `udlock.xact_lock_i`) update registry for observability; `udlock.gc_registry()` cleans orphaned entries by cross-referencing `pg_locks`.
- Job orchestration acquires locks before emitting artifacts (`analyze:lifecycle:{job_id}`, `compose:section:{job_id}:{section}`) to avoid duplicates on retries.
- Upload finalization and approval flows use OCC versions to guarantee single-writer semantics; concurrent approval attempts fail with version mismatch requiring refresh.

#### 5.4.1 ExclusiveSwap invariant (binding)

**Purpose:** Enforce single-winner semantics for CDs and DLs and make approvals/release idempotent and race-free.\
**Contract:** The ExclusiveSwap invariant governs every approval or release path; all call sites MUST invoke this procedure rather than reimplementing it.\
**State transitions:** Applies when moving a CD from `QUEUED_FOR_REVIEW` to `APPROVED` and when promoting the corresponding DL to `RELEASED`; App.A.2 visualizes the swap.\
**Failure modes & retries:** OCC mismatches surface `409` conflicts, advisory locks prevent duplicate winners, and signer timeouts trigger retryable errors before any DL is promoted.\
**Observability:** `approval_swap_conflict_total`, `deliverable_release_retries_total`, `portal_link_invalidated`, audit events `APPROVAL_SWAP_APPLIED`.\
**Breadcrumbs:** Implementation `packages/udocket_core/approvals/service.py::approve_artifact`, Tests `tests/platform/artifacts/test_approval_swap.py::test_concurrent_approvals_single_winner`, Observability Grafana “Approvals” panel.\
**References:** §5.2.6, §5.2.8, §10.3.2, App.A.2.

This invariant is authoritative; downstream APIs (for example, §10.3.2 Reviews API) and docs MUST reference it instead of restating the algorithm.

- Unique indexes (binding):

  ```sql
  CREATE UNIQUE INDEX one_approved_per_case_type
      ON artifact (case_id, type)
   WHERE status='APPROVED' AND archived=false;

  CREATE UNIQUE INDEX one_released_dl_per_case_type
      ON artifact (case_id, type)
   WHERE class='DL' AND status='RELEASED' AND archived=false;
  ```

- Approval + release algorithm (single transaction; READ COMMITTED):

  1. Acquire case/type lock: `udlock.xact_lock('case-approval', CONCAT(:org_id, '/', :case_id, '/', :type))`.
  1. Archive any existing `APPROVED` CD for `(org_id, case_id, type)` (`UPDATE ... SET status='ARCHIVED', archived=true, version=version+1 WHERE status='APPROVED' AND archived=false`).
  1. Approve target only if `status='QUEUED_FOR_REVIEW'` and `version=:expected_version`; set `status='APPROVED'`, populate `approved_by`, `approved_at`, increment `version`.
  1. Revoke the prior deliverable, if present: `UPDATE artifact SET status='REVOKED', revoked_at=now(), revoked_by_artifact_id=:new_cd WHERE class='DL' AND status='RELEASED' AND case_id=:case_id AND type=:type`.
  1. Mint/sign new deliverable row referencing the approved CD (`class='DL'`, `status='SIGNED'`, signature metadata, OCC `version=0`), perform signing/TSA operations, then promote to `status='RELEASED'` within the same transaction. Each step includes OCC assertions on the new DL row to prevent double-release.
  1. Emit audit + SSE (`artifact.status`, `portal_link_invalidated`). If no row updated in step 3 but the target already satisfies `status='APPROVED'` with the expected version, treat as idempotent success; otherwise raise 409 conflict.

Notes

- Prefer OCC columns (`version INT NOT NULL DEFAULT 0`) on hot rows; use advisory locks only for cross-row invariants like the exclusive swap. The DL creation uses the same OCC guard to catch stale retries.

- Settings may define additional exclusive types; the baseline indexes above remain in place, with settings activation validating coverage.

- Signing happens synchronously inside the approval transaction; long-running signers return signed blobs via in-memory channels with deadlines enforced by `sign.approval.timeout_seconds`. If the signer exceeds the deadline the transaction aborts and the reviewer sees a retryable error, preventing partially promoted DLs.

- This procedure is normative; API behaviours in §10.3.2 defer to it to avoid divergence. App.A.2 sequence depicts the event-driven judgment followed by the approval/release swap.

- Binding breadcrumbs:

  | Binding                         | Implementation                                                    | Test                                                                                              | Observability                                                                      |
  | ------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
  | Concurrent approval swap        | `packages/udocket_core/approvals/service.py::approve_artifact`    | `tests/platform/artifacts/test_approval_swap.py::test_concurrent_approvals_single_winner`         | Alert `approval_swap_conflict_total` (Grafana “Approvals” panel)                   |
  | Deliverable release exclusivity | `packages/udocket_core/approvals/service.py::promote_deliverable` | `tests/platform/artifacts/test_deliverable_release.py::test_single_released_deliverable_enforced` | Metric `deliverable_release_retries_total`; alert `deliverable_release_uniqueness` |

### 5.5 Partitioning, indexing, and performance considerations

*Purpose: Ensure data scale aligns with operational SLOs.*

- Time-series tables (`audit_event`, `delivery_receipt`) partitioned by month (`created_at`).

- Targeted indexes support hot paths: `artifact_consumable`, `job_org_case_kind_status`, GIN on `qa_log.issues_json`, etc. Guardian history unique index prevents duplicate idempotency keys.

- Autovacuum tuned for high-churn partitions (`vacuum_scale_factor=0.05`, `analyze_scale_factor=0.02`, `naptime=30s`). Monitoring alerts on `pg_stat_all_tables.n_dead_tup` spikes.

- Search path locked to `pg_catalog, public` per session; statement/lock/idle timeouts enforced (`30s`, `5s`, `15s`, `200ms` deadlock).

- Capacity planning uses metrics from §12 to size Postgres/Redis; cross-region replicas considered only for read-heavy analytics with strict RLS enforcement.

- **Source material:** `§3`, `§4`, `§10.3`, `§5.5`, `App.J`, `App.G`

- **Priority:** High (feeds DB migrations, data governance)

### 5.6 Artifact manifest schema (normative)

*Purpose: Define a consistent, verifiable manifest format for artifacts.* Schema (JSON Schema draft 2020-12)\*

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://udocket.ca/schemas/artifact_manifest_v1.json",
  "type": "object",
  "required": ["schema_version", "source", "provenance", "hashes", "settings_snapshot_sha256", "masking", "security", "retry"],
  "properties": {
    "schema_version": {"type":"string", "const":"1"},
    "type": {"type":"string"},
    "source": {
      "type": "object",
      "properties": {
        "case_id": {"type":"string", "format":"uuid"},
        "job_id": {"type":"string", "format":"uuid"},
        "inputs": {"type":"array", "items": {"type":"string", "format":"uuid"}}
      },
      "required":["case_id", "job_id"]
    },
    "provenance": {
      "type": "object",
      "properties": {
        "compute_region": {"type":"string"},
        "storage_region": {"type":"string"},
        "tool_versions": {"type":"object"},
        "template_version": {"type":["string", "null"]}
      },
      "required":["compute_region", "storage_region", "tool_versions"]
    },
    "hashes": {
      "type":"object",
      "properties": {"content_sha256": {"type":"string"}},
      "required":["content_sha256"]
    },
    "settings_snapshot_sha256": {"type":"string"},
    "masking": {
      "type":"object",
      "properties": {
        "masking_profile_id": {"type":"string"},
        "token_vault_version": {"type":"string"},
        "masking_hash_algorithm": {"type":"string"}
      },
      "required":["masking_profile_id", "token_vault_version", "masking_hash_algorithm"]
    },
    "security": {
      "type":"object",
      "properties": {
        "fips_mode": {"type":"boolean"},
        "fips_module_cert_id": {"type":["string", "null"]},
        "signing_profile_id": {"type":["string", "null"]}
      },
      "required":["fips_mode", "fips_module_cert_id"]
    },
    "retry": {
      "type":"object",
      "properties": {
        "retry_token": {"type":["string", "null"]},
        "retry_generation": {"type":"integer", "minimum":0}
      },
      "required":["retry_generation"]
    }
  }
}
```

All schema properties marked with `"format": "uuid"` expect UUIDv7 strings; generator tooling annotates each property with `"description": "UUIDv7"` and the non-enforcing extension `"x-udocket-uuid-version": 7`. Runtime validators (`packages.udocket_core.validators.uuid.ensure_v7`) reject non-v7 inputs on write. The `masking`, `security`, and `retry` sections bind manifests to the vault/HSM posture defined in §4.5.2 and capture the replay metadata consumed by the job lifecycle contract (§10.2, §6.2–§6.4). CI fixtures in `tests/spec/test_artifact_manifest_schema.py` assert the additional required fields for every artifact class.

### 5.7 Ingestion pipelines & malware/archives defenses

*Purpose: Secure intake against malicious payloads while preserving evidence integrity.*

- Pipeline: raw uploads (`EXHIBIT_RAW`, `COURT_DOC_RAW`, `EMAIL_RFC822`, `FINANCIALS_RAW`, audio) land in staging, run through normalization/OCR/parsers to emit structured counterparts (`*_TEXT`, `EMAIL_ATTACHMENTS`, `FINANCIALS_TABLE`, `TRANSCRIPT`, `DIARIZATION`). Derived artifacts progress `PROCESSING → PENDING_JUDGMENT`; Guardian PASS/WARN moves WP to `CLEARED_FOR_USE` and CDs to `OPERATOR_PREP`, operators submit (`APPROVAL_REQUESTED`) and queue assignment advances CDs into `QUEUED_FOR_REVIEW → APPROVED`.
- Malware scanning: scan on upload/finalize with signatures and heuristics; block/quarantine positive hits; log details to `audit_event`.
- Archive defenses: enforce archive type allowlist, depth/ratio caps; detect zip bombs and path traversal (Zip Slip) in extractors.
- MIME & size policies: allowlist content types; settings define max size per type; reject suspicious double extensions.
- Evidence: record original filenames, sizes, and content hashes; store normalization provenance for audio.
- Source material: `§5.7`, `§4.1-4.3`

Example

```json
{
  "schema_version": "1",
  "type": "TRANSCRIPT",
  "source": {"case_id": "...", "job_id": "...", "inputs": ["..."]},
  "provenance": {
    "compute_region": "na-us-1",
    "storage_region": "na-us-1",
    "tool_versions": {"udocket_core": "0.9.0", "azure_speech": "1.38"},
    "template_version": null
  },
  "hashes": {
    "content_sha256": "sha256-..."
  },
  "settings_snapshot_sha256": "sha256-...",
  "masking": {
    "masking_profile_id": "default_phispi_v1",
    "token_vault_version": "2025-10-18T05:22:11Z",
    "masking_hash_algorithm": "SHA256",
    "fips_mode": true,
    "fips_module_cert_id": "FIPS-140-3-udocket-001"
  },
  "security": {
    "policy_bundle_id": "policycontext@2025.10.18",
    "guardian_judgment_id": "0192c8dc-3f31-7b2c-bbb4-5a7c94f62a10",
    "signed_by": "signer@udocket.io",
    "tsa_token_hash": "sha256-timestamp",
    "ocsp_status": "GOOD"
  },
  "retry": {
    "retry_token": "rty_0192c8dc3f31",
    "retry_generation": 2,
    "last_retry_reason": "NETWORK_RETRY"
  }
}
```

## 6) Agent ecosystem

### 6.1 Agent contract (inputs, outputs, manifests, ops logging)

*Purpose: Define the shared behavior that keeps agents composable and observable.*

- Terminology: Appendix I covers lane names, artifact states, and failure classes referenced throughout this section.
- Agents implement the `TranscriptionAgent`-style interface: accept structured config (`TranscriptionConfig` family), pull secrets from Settings service.
- Provider-agnostic planning: agents consult the shared `TranscriptionCapabilityMap` (speech) or equivalent planners to negotiate supported features, pick an execution flow, and guarantee outputs conform to the normalized schema the downstream stages expect.
- Return value encapsulates success data (`TranscriptionResult`/agent-specific models) and raises rich exceptions with machine-actionable codes; Celery tasks capture and surface to UI.
- Filesystem layout: artifacts saved under `storage/media/<org_id>/cases/<case_id>/<category>/` with `job_id` prefixes; ops logs in `ops/` with per-run JSON + human-readable log, plus append-only `ops_<agent>.jsonl`.
- Deterministic naming/versioning: reruns append `_v{n}` suffix; manifests store `settings_snapshot_sha256`, model/provider versions, compute/storage regions, and SHA-256 of outputs.
- Audit & telemetry: each run logs structured metadata (duration, attempts, cost envelope) and writes SSE updates; metrics exported for `job_duration_seconds`, `agent_retry_total`, etc.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/mermaid/overview/tdd/diagrams/analyze-compose-v1.png" alt="Analyze and Compose pipeline overview">
  <figcaption style="font-size: 0.9em; color: #555;">Analyze and Compose pipeline overview</figcaption>
</figure>

<figure class="full-width-diagram">
  <img class="diagram" src="../build/mermaid/overview/tdd/diagrams/agent-orchestration-classes-v1.png" alt="Agent orchestration classes">
  <figcaption style="font-size: 0.9em; color: #555;">Agent orchestration classes</figcaption>
</figure>

### 6.1.1 Configurable pipeline definitions & stage catalog (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/agents/pipeline_catalog.py::PipelineCatalog`, Tests `tests/udocket_core/agents/test_pipeline_catalog.py::test_activation_contract`, Observability Grafana “Agent Pipelines – Activation” dashboard.

*Purpose: Let sysadmins compose and adjust LangGraph-driven pipelines without redeploying code.*

- System scope Settings key `agents.pipeline.definitions[]` enumerates every agent pipeline variant (`transcription`, `analyze`, `compose`, `assistant.staff`, `assistant.client`, and future agent types). Each entry tracks `pipeline_id`, `graph_version`, `graph_schema_sha256`, default runner (`langgraph` or `linear`), and an ordered `stages[]` array so GraphRunner can hydrate LangGraph graphs directly from configuration. System defaults seed from JSON bundles in `config/*.json` (for example, `config/bootstrap_defaults.json`, `config/guardian_defaults.json`, `config/analyze_defaults.json`) so fresh deployments or sandboxes bootstrap without writing code; subsequent edits reuse the same bundle loader as Settings activations.
- Stage objects declare `stage_id`, `langgraph_node_id`, `enabled`, `llm_profile_id`, `prompt_template_id`, `tool_ids[]`, retry budgets, token/cost ceilings, and optional `depends_on[]`. Metadata mirrors the LangGraph `NodeSpec` contract, ensuring node composition, input schemas, and tool wiring stay in sync with the runtime.
- Org/case overrides live in `agents.pipeline.assignments[]` and `agents.pipeline.overrides[]`. Overrides permit toggling stage enablement, swapping prompt or LLM profile references, or tightening budgets within validator bounds; structural edits (adding/removing stages or changing order) require SYSTEM-scope activation to preserve deterministic manifests.
- Activation diffs run the LangGraph contract tests from §13.4 against the candidate graph, validate schema hashes, and refuse definitions that break the `TranscriptionAgent`/`AnalyzeAgent`/`ComposeAgent` interfaces. Successful activation snapshots `{graph_version, settings_snapshot_sha256}` into the pipeline manifest so replays remain reproducible.
- Every pipeline activation is labeled `change_class="system"` and must follow the blue/green rollout path in §14.5. Traffic migrates org-by-org with automatic rollback to the prior pipeline when health probes, QA acceptance, or Guardian readiness fail; manifests record which orgs completed cutover.
- Stage definitions are additive and versioned. Prior versions stay callable for queued jobs and replays until Guardian signs off on the new version and the rollout window closes; deletion is blocked until no active job references the stage and archival manifests exist under `ops/pipeline_manifests/`.

### 6.1.2 LangGraph tool registry & custom tool onboarding (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/agents/tool_registry.py`, Tests `tests/udocket_core/agents/test_tool_registry.py::test_schema_validation`, Observability CI job “agents-tool-registry-lint” plus Grafana “Agent Tooling” panel.

*Purpose: Provide a configurable, auditable catalog of LangGraph tools for agents and editors.*

- Settings `agents.tools.catalog[]` (SYSTEM scope with ORG allowlists) mirrors the LangGraph `Tool` specification: each entry defines `tool_id`, `description`, `input_schema` (JSON Schema Draft 2020-12), `output_schema`, `binding` (Python module path, gRPC target, or HTTP service), `timeout_seconds`, `cost_profile_id`, residency/PII classification, and `idempotent` (`true|false`). When `idempotent=true` the catalog must also include `tool_idempotency_key` (stable across retries) so GraphRunner can deduplicate invocations during job restarts; non-idempotent tools are fenced behind retry guards (`max_attempts=1`) and require human inspection before re-run.
- Tool bindings reuse adapters in `packages/udocket_core/agents/common/factories.py` and follow the LangGraph `Tool` interface. GraphRunner resolves the `binding` at runtime and injects shared dependencies (Settings client, PolicyContext, Guardian client) through the adapter so tools stay portable across pipelines.
- Org/case overrides are expressed via `agents.tools.allowlist[]`, enabling or disabling tools per tenant without redefining the base catalog. Overrides can also tune per-tool budgets and concurrency caps inside validator limits; policy validation blocks overrides that widen residency or PII scopes beyond the SYSTEM baseline.
- Activation lints validate schemas, execute dry-run LangGraph graphs that exercise the tool, and confirm telemetry registration (`tool_invocation_total`, `tool_cost_estimate_total`). Failures surface actionable errors and block promotion until fixed.
- Tool catalog activations are treated as system-level changes and must follow the blue/green rollout pipeline (§14.5). JSON seeds under `config/` (for example, `config/llm_assignments.json`, `config/llm_providers.json`) preload the baseline catalog; operators extend it by uploading updated JSON bundles or using the Settings UI without touching code. During rollout both blue and green environments load the catalog, but only green advertises new tools; on rollback GraphRunner falls back to the previous allowlist without redeploying workers.
- Evidence manifests capture `{tool_id, tool_version, binding_sha256}` for every invocation so Guardian, Privacy, and FinOps teams can audit side effects and cost. Tools handling sensitive data must declare `data_classification` and pass Privacy/Architecture review before activation.

### 6.1.3 Conversational assistant pipelines (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/assistants/orchestrator.py::AssistantOrchestrator`, Tests `tests/udocket_core/assistants/test_pipeline_manifest.py::test_chat_pipeline_roundtrip`, Observability Grafana “Assistant Sessions” dashboard.

*Purpose: Apply the same managed pipeline controls to chat assistants that power staff and client surfaces.*

- Assistant pipelines (`assistant.staff`, `assistant.client`, and future chat variants) are LangGraph graphs composed through `agents.pipeline.definitions[]` with lane metadata mirroring other agents: retrieval nodes, guardrails, responder nodes, moderation gates, and post-processing writers. Stages reference shared tools (retrieval search, citation builder, policy explainer) declared in `agents.tools.catalog[]`.
- Runtime orchestration lives in `packages/udocket_core/assistants/orchestrator.py::AssistantOrchestrator`, which wraps GraphRunner, handles conversation state checkpoints, and routes telemetry to chat-specific metrics. The orchestrator consumes the same `pipeline_definition_version` manifest as batch agents so replays and rollbacks remain deterministic.
- Conversation manifests capture `{pipeline_definition_version, llm_profile_id, prompt_template_id, tool_invocations[], moderation_outcomes[]}`. Storage layout mirrors ops logs (`ops/<session_id>__chat_*.jsonl`).
- Settings overrides allow orgs to adjust retrieval scope (`assistant.retrieval.sources[]`), citation verbosity, or moderation strictness within validator limits. Structural edits (adding/removing lanes, reordering stages) remain SYSTEM-only and must pass LangGraph contract tests plus conversational replay harnesses (§13.4) before rollout.
- Assistant pipelines participate in the same blue/green rollout flows as other agents. Rollout plans can target staff-only, client-only, or mixed cohorts, with auto-rollback triggered by moderation overruns, SLA breaches, FinOps budget violations, or quarantines captured in telemetry.

### 6.2 Transcription agent (batch/on-demand modes)

*Purpose: Summarize ingestion flow from audio to transcript artifacts.*

- Modes: `on-demand` streaming for shorter recordings (local processing), `batch` for longer files via Azure Batch Transcription (HTTPS SAS URL). Region allowlists from Settings are enforced at job dispatch.
- Input processing: audio uploads hashed, normalized via ffmpeg (PCM 16 kHz mono). Artifacts created: `TRANSCRIPT_INPUT`, `AUDIO_NORMALIZED`.
- Malware & format validation: every upload (audio, documents, exhibits) routes through the `upload_scan` pipeline—an isolated Kubernetes job running ClamAV with daily `freshclam` updates plus org-specific YARA rules (`packages/security/yara/`). Files are scanned before workers access them; positive hits set `upload_session.status='SCANNING_FAILED'`, quarantine the staging object, emit `MALWARE_DETECTED` audit events, and notify Security (remediation flow in [Runbook RB-UPLOAD-SCAN](../ops/runbooks/index.md#rb-upload-scan)). Format validators (mediainfo/ffprobe, pdfcpu, tika) run in the same sandbox to confirm claimed MIME/codec; malformed files are rejected with actionable error codes and attached diagnostic logs.
- Capability-aware ingestion: workers inspect `speech.providers[].capabilities` (for example `multi_track`, `speaker_diarization`, `punctuation_normalization`, `numerical_normalization`) to select an execution plan. Multi-track inputs trigger track-aware pipelines; single-track jobs fall back to diarization when providers expose that capability.
- Capability gates & planning: before dispatch, the `TranscriptionCapabilityMap` evaluates requested features (multi-track, diarization, locale) against provider claims. Unsupported combinations fail fast with `CAPABILITY_UNAVAILABLE`, SSE guidance, and no provider calls. When multiple flows are viable, planners prefer native multi-track, then synthetic track merge, then diarization-only as the final option.
- Multi-track support: batch mode splits per-channel audio when `multi_track` is available; otherwise the Track Merge sub-task (see §6.2.2) generates per-speaker transcripts by splitting channels, running parallel jobs, and merging on precise timestamps. Single-track jobs without diarization support return policy errors rather than emitting unlabelled transcripts.
- Outputs: normalized transcript (`transcript/<job_id>__transcript.txt`) with header metadata (case, source name, hashes, language, region, duration) and body rewritten via the shared normalizer (see §6.2.2) so downstream agents receive consistent punctuation, casing, and numeric treatment; optional `DIARIZATION` JSON for batch mode.
- Ops artifacts: `ops/<job_id>__transcription.log`, `ops/<job_id>__transcription_log.json`, case-level `ops_transcription.jsonl` append.
- Stdout contract: single JSON line `{status, transcript_file, region, language, attempts, duration_s}` enabling CLI automation.
- See App.D for canonical artifact types and filenames (TRANSCRIPT, AUDIO_NORMALIZED) and versioning rules.

#### 6.2.1 Provider fallback & health-governed resume (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/agents/transcribe_planner.py::plan_with_health_resume`, Tests `tests/udocket_core/transcription/test_fallback_resume.py::test_health_governed_routing`, Observability Grafana “Transcription Health & Retry” dashboard.

*Purpose: Define fallback chains and health checks that govern provider selection and resumption.*

- Provider catalog: `speech.providers[]` mirrors the LLM registry, capturing API endpoints, residency, pricing, and `health_check.url`. Each `speech.jobs[]` entry defines a `fallback_chain` where every hop is validated against an equivalence harness (`tests/udocket_core/agents/test_transcribe_fallback.py`) demonstrating WER delta ≤ 1.5 % and diarization accuracy within tolerance on the golden corpus.
- Orchestration helper: `packages/udocket_core/failover/speech.py::SpeechFailoverController` applies the fallback chain uniformly across batch/on-demand workers. It shares telemetry/event naming with the LLM orchestrator and exposes `speech.failover.for_request(...)` so Celery tasks and new speech processors remain provider-agnostic.
- Automated retries: when Azure Speech (primary) degrades or breaches SLA thresholds, workers emit `TRANSCRIBE_FALLBACK_TRIGGERED`, replay the batch against the next healthy provider/region pair, and annotate manifests with `fallback_source_provider_id` and `fallback_attempt`. Retries respect org budgets and residency settings; no human transcription path exists in the automated flow.
- Pause semantics: if the chain exhausts without a healthy provider, the job enters `PAUSED_AWAITING_PROVIDER`, preserving the queue order. Health monitors run every 60 seconds, requiring three consecutive successes before the job automatically resumes from the point of failure. UI surfaces status with next probe ETA; operators can trigger an on-demand probe via `POST /ops/transcription/{job}/probe`.
- Observability: metrics `transcribe_fallback_total{provider, reason}`, `transcribe_pause_total`, and `transcribe_paused_jobs` feed dashboards. Audit events capture provider transitions and parity evidence hash; ops logs include health snapshots for every pause/resume cycle.
- Testing: `tests/udocket_core/failover/test_speech_orchestrator.py` exercises controller parity checks, health-driven pauses, and auto-resume, while `synthetics/transcribe_failover.yaml` validates staging behavior.

#### 6.2.2 Capability negotiation & track merge pipeline (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/audio/track_merge.py::plan_capabilities`, Tests `tests/udocket_core/audio/test_track_merge.py::test_capability_negotiation`, Observability Grafana “Transcription Track Merge” panel.

*Purpose: Explain capability negotiation, normalization, and track-merge flows for transcripts.*

- Capability registry: `speech.providers[].capabilities` declares booleans + enums (`multi_track`, `diarization`, `dominant_speaker`, `timestamp_precision_ms`, `max_parallel_channels`). Settings validators ensure advertised capabilities match integration tests before activation. Workers resolve execution plans through `TranscriptionCapabilityMap` (new module) that maps provider capability sets to supported processing flows and emits a provider-agnostic plan contract consumed by every `TranscriptionAgent` implementation.
- Normalization contract: regardless of provider, outputs conform to `NormalizedTranscript@1.1` (Appendix D) with segments shaped as `{start_ms, end_ms, speaker_label, text_norm, raw_text}` plus optional diarization/confidence metadata. The `TranscriptionNormalizer` layer applies shared transforms (numeral expansion, capitalization policy, punctuation smoothing, profanity masking) so Analyze/Compose receive consistent text.
- Track Merge sub-task: when an audio upload contains ≥2 channels but the active provider lacks native multi-track support, the Track Merge controller (Celery chord) performs:
  1. `SplitTracks` (ffmpeg) emits isolated WAVs per channel with preserved timestamps and writes `AUDIO_TRACK_SPLIT` artifacts.
  1. Parallel `TranscriptionAgent` invocations per track using provider capabilities (single-track diarization toggled off).
  1. `MergeTracks` reconciles segments using timestamp offsets, ordering by `start_ms` and applying deterministic speaker labels (`Speaker A/B/...`). Overlaps trigger merge heuristics (highest confidence wins; otherwise interleave by start time). The merged transcript re-runs normalization to ensure downstream parity.
  1. Controller persists merge provenance (`track_merge_manifest.json`) capturing channel counts, offsets, and chosen heuristics.
- Diarization policy: if both `multi_track` and `diarization` exist, multi-track takes precedence (channel identity is more reliable). If neither is available, the job fails fast with `CAPABILITY_UNAVAILABLE` and SSE guidance to select a provider with required capabilities.
- Testing & drills: `tests/udocket_core/transcription/test_capability_map.py` validates routing, `tests/udocket_core/transcription/test_track_merge.py` verifies merge ordering/conflict resolution, and synthetic `synthetics/transcribe_capabilities.yaml` asserts capability negotiation in staging. Ops drill `../ops/runbooks/index.md (RB-TRANSCRIBE-CAP)` ensures runbooks cover channel splits and merge artifact inspection.

#### 6.2.3 Speech capability registry & audio format policy (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/audio/policy.py::SpeechCapabilityRegistry`, Tests `tests/udocket_core/audio/test_format_policy.py::test_enforces_policy`, Observability CI job “audio-policy-lint” with ffprobe synthetic monitor.

*Purpose: Record registry fields and policies that govern audio formats and provider capabilities.*

- Registry source of truth: `speech.providers[]` (Settings Service) defines each adapter’s declared capabilities, with overrides allowed per organization/case. Activation validators cross-check declarations against integration fixtures (`tests/udocket_core/transcription/providers/fixtures/*.json`) to prevent drift.
- Capability groups (all required unless noted):
  - `ingest`: `supported_containers[]` (e.g., `["wav", "mp3", "m4a", "ogg"]`), `preferred_audio_format` (`"wav/pcm16"` default), `max_channels` (int), `max_duration_minutes`, `max_file_mb`, `requires_conversion` (bool) when provider enforces PCM inputs, `streaming_modes[]` (`"on_demand"`, `"batch"`).
  - `analysis`: `diarization` (`none|provider|external`), `speaker_labels` (bool), `dominant_speaker` (bool), `word_timestamps` (`none|per_word|per_token`), `timestamp_precision_ms` (int), `channel_separation` (bool).
  - `normalization`: `punctuation_normalization` (enum), `numerical_normalization` (enum), `capitalization` (enum), `profanity_filters` (enum), `locale_support[]` (BCP-47 codes) indicating verified language/localization coverage, `preferred_locale_fallback` (BCP-47).
  - `translation` (optional): `supports_translation` (`none|provider|external`), `translation_modes[]` (for example `["source_to_target", "source_to_many"]`), `verified_target_locales[]` (BCP-47), `verified_language_pairs[]` (array of `{source, target[], mode}` records), `max_parallel_targets` (int), `pivot_locale` (BCP-47) when the provider requires an intermediate locale, `requires_custom_glossary` (bool), `supports_glossary` (bool), `supports_formality_tone` (enum), and `fallback_translation_strategy` (`"pivot"`, `"reject"`, `"external"`) for unsupported pairs.
  - `operational`: `billing_unit` (`"minute"`, `"second"`, `"character"`), `max_parallel_jobs`, `region_allowlist[]` (subset of Settings region catalog), `requires_data_residency_attestation` (bool), `sla_compliant` (bool), `health_check.url`.
- Execution planning best practices:
- Agents always normalize inputs to `preferred_audio_format`; if the source already matches (e.g., PCM 16 kHz mono) conversion is skipped; otherwise ffmpeg converts to PCM 16-bit little-endian WAV at the provider’s highest verified sample rate ≤ 32 kHz to balance accuracy and cost. Conversion artifacts are saved (`AUDIO_NORMALIZED`) with SHA-256 so replays share a stable baseline.
- When `supported_containers` excludes the upload type, the pipeline re-muxes into WAV before plan evaluation, logs the operation in `compile_notes`, and retains original audio under `audio/` for audit parity.
- `max_channels` governs whether the pipeline attempts native multi-channel; when the input exceeds this value, the registry can declare `fallback_channel_strategy` (`"synthetic_merge"` or `"reject"`). Synthetic merges are only attempted if integration tests demonstrate \<1.5% WER regression compared to provider multi-channel output.
- `max_duration_minutes` and `max_file_mb` gate plan selection; exceeding either triggers preflight chunking (feature-flagged) or a policy failure with actionable guidance in SSE and ops logs.
- Language/locale negotiation respects `locale_support[]`: if the requested locale is missing, the planner either downgrades to `preferred_locale_fallback` (noting the downgrade in manifest) or fails fast depending on Settings (`speech.require_locale_match`).
- Combined transcribe+translate providers (`supports_translation="provider"`) still follow the plan pipeline: planners request both source and target locales explicitly, set `dual_output=true`, and verify capabilities for diarization/timestamps on both outputs. Providers must return a structured payload containing source and translated segments; normalized transcripts split these outputs into discrete artifacts while sharing provenance metadata.
- Translation coverage guardrails: the registry’s `verified_language_pairs[]` enumerates source→target combinations that have passed integration tests. The planner refuses to dispatch pairs absent from the list unless `speech.translation.allow_unverified_pairs=true` (waiver-only). Per-org overrides may remove pairs for contractual reasons; removals are stored in Settings activation history for audit.
  - Residency redundancy: each residency bundle must approve at least two speech providers per allowed region; nightly health checks validate coverage and raise `SPEECH_REGION_PROVIDER_DEGRADED` alerts if redundancy drops below two active providers, prompting immediate remediation before new jobs are accepted.
  - Audio optimization guidance (binding):
    - Prefer lossless PCM WAV at 16 kHz mono for dialog; escalate to 24 kHz stereo only when the provider’s accuracy materially improves for music-heavy or courtroom recordings (documented per provider in Appendix Q notes). The planner records any higher sample rate conversions in manifest metadata (`normalization.sample_rate_hz`).
    - Apply loudness normalization (`-16 LUFS` target, ±1 LU tolerance) and dynamic range compression (light preset) before transcription only when `speech.allow_preprocessing=true`; defaults preserve raw audio aside from format conversion to maintain evidentiary integrity.
    - Size optimization uses ffmpeg `-ar` (sample rate) and `-ac` (channels) parameters, never applying lossy codecs; storage deduplicates normalized outputs via content hash.
  - Provider capability validation: nightly job `scripts/agents/validate_speech_capabilities.py` runs golden audio fixtures against each provider, verifies declared fields (diarization, timestamps, normalization behaviors, translation language pairs), and writes results to `ops/speech_capability_report.json` per org. Failures block new activations and trigger `../ops/runbooks/index.md (RB-TRANSCRIBE-CAP)` escalation; translation pair regressions additionally file `TRANSLATION_PAIR_REGRESSION` incidents and remove the affected pair from `verified_language_pairs[]` until retested.
  - Documentation & SDK alignment: OpenAPI schemas expose the negotiated capability plan in `GET /api/v1/speech/providers` for UI/SDK consumers. SDK samples in `docs/examples/api/speech_capabilities/*.md` stay synchronized with Settings keys and the registry schema.

#### 6.2.5 Cancellation & retry semantics (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/transcription/runner.py::handle_cancel_retry`, Tests `tests/udocket_core/transcription/test_cancel_retry.py::test_provider_cleanup`, Observability Grafana “Transcription Health & Retry” dashboard (metric `transcription_retry_total`).

*Purpose: Specify cancellation hooks, retry tokens, and validation for speech jobs.*

- Provider hooks: each speech adapter implements `cancel(job_id, retry_token)` and `cleanup(job_id, retry_token)`; `cleanup` executes irrespective of provider success so SAS uploads, staging blobs, and stream leases are always revoked. Both hooks MUST remain idempotent.
- Azure Batch transcription:
  - Cancellation deletes the Batch job via Azure Cognitive Services, revokes SAS upload URLs, and purges staging containers (`storage.staging.<region>`). The adapter records `provider_outcome` (`azure_batch:deleted`, `azure_batch:not_found`, or `azure_batch:timeout_force_cancel`) in the job tombstone for audit.
  - Retries reuse normalized audio artifacts and only submit a fresh Batch job after verifying the stored `retry_token` (`{provider_job_id, audio_sha256, diarization_enabled}`) still matches the source artifact. Hash drift blocks the retry and surfaces `RETRY_INPUT_DIVERGED`.
- Streaming transcription:
  - Cancellation closes the streaming session, discards buffered audio, revokes session SAS grants, and commits partial transcripts to the tombstone artifact for operator review.
  - Retries resume from the last committed segment index contained in `retry_token.segments[]`; adapters skip already confirmed segments so replaying remains safe even if the worker crashed mid-stream.
- Manifest requirements: speech artifacts append `{retry_token, retry_generation, masking_profile_id, token_vault_version, fips_mode, fips_module_cert_id}` (see §4.5.2 and §5.6) to preserve vault provenance and cryptographic attestation.
- Validation: `tests/udocket_core/transcription/test_cancel_retry.py` exercises cancellation and replay flows; synthetic job `synthetics/transcription_cancel.yaml` confirms provider cleanup in staging. Failures block deploys until remediation.

#### 6.2.4 Multilingual speech & translation pipeline (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/transcription/multilingual.py`, Tests `tests/udocket_core/transcription/test_multilingual_pipeline.py::test_locale_negotiation`, Observability Grafana “Transcription Multilingual” dashboard with alert `speech_translation_glossary_miss_total`.

*Purpose: Describe multilingual detection, negotiation, and translation workflows.*

- Scope: captures language detection, multi-locale transcription, and optional translation flows, ensuring downstream artifacts remain deterministic and policy compliant across locales.
- Locale negotiation:
  - Inputs declare `source_language` (BCP-47) and optional `requested_locales[]`. If `source_language` is omitted and `speech.detect_language.enabled=true`, the `LanguageProbe` step samples audio snippets (≤30 seconds) using CLD3 + provider hints to produce a ranked list with confidence. Detections below confidence threshold (default 0.75) require human confirmation before dispatch (SSE `LANGUAGE_CONFIRMATION_REQUIRED`).
  - Providers must have the requested locale in `locale_support[]`; otherwise the planner either downgrades to `preferred_locale_fallback` (recorded in manifest `locale_resolution`) or blocks execution when `speech.require_locale_match=true`.
- Native multilingual transcription:
  - When a provider supports direct transcription into the source language (`supports_translation in {"none", "external"}` but `locale_support` includes the source), the agent emits a single normalized transcript tagged with `language`/`locale` fields. Multi-language sessions (code-switching) use diarization segments to attach `segment.language` metadata; transcripts remain in the predominant locale unless `speech.multilingual_segments.enabled=true`, which produces language-tagged segments and writes `compile_notes` describing each language span.
  - Segment-level metadata stores `language_confidence` (0-1) and optional `transliteration` for scripts requiring romanization (provider capability `supports_transliteration=true`). Transliteration is stored separately from the normalized text to preserve original script in downstream artifacts.
- Translation workflow:
  - Translation requests create derivative artifacts `transcript/<job_id>__transcript_<locale>.txt` alongside JSON manifests referencing the source transcript ID, translation provider, glossary version, and pivot locale (if used). The base transcript remains the source of truth; translated transcripts carry `schema_version: "speech_translation@1.0"` with fields `{source_locale, target_locale, translation_mode, glossary_ids[], segments[]}`.
  - Translation providers declare `translation_modes[]`; the planner batches target locales up to `max_parallel_targets`, respecting rate limits and cost envelopes. During planning the agent filters requested locales against `verified_language_pairs[]`, logging `TRANSLATION_PAIR_BLOCKED` when a combination is unsupported and surfacing actionable guidance (`try_pivot_locale`, `choose_different_provider`). Providers advertising `supports_translation="provider"` can execute transcription and translation in a single call; the planner still writes two artifacts: the primary transcript (source locale) and each translated transcript, both derived from a single provider response with provenance recorded in manifests (`translation_bundle_id`, `provider_job_id`, `source_transcript_offset`).
  - When `supports_translation="provider"` and the provider lacks word-level timestamps or diarization for translated text, the agent backfills alignments by projecting source timestamps, storing alignment confidence (`alignment_confidence`) per segment. Providers that emit both transcribed and translated text with distinct timestamps must pass integration tests (`tests/udocket_core/transcription/test_dual_output_alignment.py`) to ensure timestamp drift stays under 100 ms.
  - If the provider requires separate translation calls (`supports_translation="external"`), the planner first generates the normalized source-language transcript and then fans out translation jobs per target locale. Each target locale job inherits Guardian gating and writes ops logs (`ops/<job_id>__translation_<locale>.log`), JSON metadata (`..._log.json`), and case-level audit entries (`ops_transcription_translation.jsonl`).
  - Glossary management integrates with Reference Manager: settings key `speech.translation.glossary_set` references immutable glossary bundles. Providers advertising `requires_custom_glossary=true` block activation until a glossary is configured and parity tests (`tests/udocket_core/transcription/test_translation_glossary.py`) pass.
- Accessibility & locale formatting:
  - Normalize punctuation/casing per target locale using LPE formatters. Number/date normalization respects locale-specific rules (for example, decimal separators). Each translated transcript includes `normalization.locale_pack_version` linking back to the LPE bundle used for formatting.
  - Right-to-left scripts store `direction: "rtl"` in metadata; UI renderers consume this flag to adjust layout without altering stored content.
- Policy & compliance:
  - Residency rules mirror primary transcription; translation providers must belong to the same (or stricter) region allowlist. Manifest fields record `translation_provider_region` and `waiver_id` when applicable.
  - HIPAA/PHI rules apply identically: translations inherit PHI tags from the source transcript. If a translation provider lacks HIPAA attestation, the planner blocks translation when HIPAA mode is on.
  - Never-log still applies; raw translated text is confined to artifacts. Audit logs capture only identifiers, locale codes, provider IDs, and hashes.
- Observability:
  - Metrics: `speech_language_detect_total{result}`, `speech_translation_jobs_total{locale, provider}`, `speech_translation_duration_seconds`, `speech_locale_downgrade_total`, `speech_translation_glossary_miss_total`.
  - Dashboards correlate translation costs with FinOps budgets; alerts fire when translation error rates exceed thresholds or when locale downgrades occur repeatedly for an org.
- Testing & fixtures:
  - Golden audio/translation pairs stored under `tests/udocket_core/transcription/multilingual/`; CI asserts locale negotiation, glossary application, and parity between provider-native translation and fallback external translation within documented tolerance.
  - Synthetic tenant `GLOBAL-MULTI` exercises quarterly drills covering multilingual flows, ensuring Guardian judgments, portal rendering, and downstream Analyze/Compose consumption remain stable across locales.

### 6.3 Analyze agent (LangGraph lanes, QA, artifacts)

*Purpose: Capture the multi-lane analysis pipeline that feeds Compose and downstream tooling.*

- Graph built with LangGraph; lanes include `Events`, `Timeline`, `Issues`, `Entities`, `Facts`, plus staff report generation. Each lane produces typed Pydantic outputs.
- Inputs: latest transcript (`TRANSCRIPT`), optional `DIARIZATION`, approved exhibits (`EXHIBIT_TEXT`, etc.), and settings snapshot. Retrieval uses chunking + embeddings constrained to allowed regions.
- Deterministic IDs: row IDs rely on UUIDv7; cross-lane references include a `content_fingerprint_sha256` and a namespace UUIDv5 derived from `{org_id, case_id, lane_scope, canonical_anchor}` so reruns reuse the same identity when anchors match.
- QA stages: per-lane validation (schema, references, policy lint, token bounds) with `qa_log` entries; final QA ensures cross-lane consistency before Guardian submission.
- Cross-lane integration tests: `tests/udocket_core/agents/test_analyze_graph.py::test_cross_lane_consistency` executes the full graph with synthetic transcripts to assert lane ordering, data dependencies, and deterministic fingerprints before Compose consumes outputs.
- Artifacts: Follow the pattern `analysis/<job_id>__<title>_v<version>.json` where title=\[timeline_seeds, entity_hints, issues, facts, gaps, staff_report(.md)\]; plus ops JSON + JSONL audit. Failures surface via SSE with actionable errors.
- See App.D for artifact schemas, filenames, and versioning.

#### 6.3.1 Cancellation & retry semantics (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/agents/analyze_runner.py::cancel_and_retry`, Tests `tests/udocket_core/agents/test_analyze_cancel_retry.py::test_lane_resume`, Observability Grafana “Analyze Pipeline Health” dashboard.

*Purpose: Define cancellation handling and retry behavior for Analyze lanes.*

- `GraphRunner.cancel(job_id, retry_token)` stops active lanes, drains tool queues, and guarantees `cleanup()` executes for every registered tool adapter. Tool adapters marked `idempotent=true` in `agents.tools.catalog[]` MAY be re-run during retries; non-idempotent tools log `RETRY_DISALLOWED_NON_IDEMPOTENT`.
- Cancellation transitions Analyze jobs through the shared lifecycle (§10.2) and emits `job.blocked` when Guardian/FinOps halts processing; `job.quarantined` surfaces service-triggered policy holds.
- Retry behavior:
  - Analyze manifests store `{retry_token, retry_generation, lane_progress}`; `lane_progress` records the last successful node per lane so replays resume deterministically without re-invoking completed steps.
  - LangGraph nodes persist checkpoint digests; `GraphRunner.retry(job_id, retry_token)` compares the stored digest to the queued inputs before resuming.
  - Tool invocations include `tool_idempotency_key` (when supplied) so GraphRunner can dedupe HTTP/gRPC calls after a worker crash. Replays lacking idempotency data block with `RETRY_IDEMPOTENCY_UNKNOWN`.
- Cleanup obligations: cancellation purges intermediate artifacts (`analysis/<job_id>__*_tmp.json`) and closes vector search cursors to avoid leaking residency-scoped handles.
- Contract tests: `tests/udocket_core/agents/test_analyze_cancel_retry.py` exercises cancellation across representative transcripts; synthetic `synthetics/analyze_cancel.yaml` validates SSE emissions and manifest deltas.

### 6.4 Compose agent (deliverables, QA loops, templates)

*Purpose: Describe final deliverable generation and QA gating.*

- LangGraph pipeline with `OutlineBuilder`, parallel `SectionWriter` nodes (client/lawyer lanes), `SectionQA`, and `FinalWeave`. Inputs include Analyze outputs, intake data, templates.
- Templates resolved via Settings + organization-specific overrides; `unique_title` helper prevents collisions. Manifest stores template version, language, document type.
- QA loops enforce forbidden patterns (`compose.policy.forbidden_patterns[]`), required sections, link counts, and reference integrity. `SectionQA` runs per lane before `FinalWeave`; a final QA pass checks cross-lane coherence. Lane retries limited by `compose.max_retries`.
- Safety contracts: Compose `JobContext` separates agent directives (`instructions[]`) from evidentiary payloads (`source_content[]`, transcripts, manifests). Lane runtimes treat instructions as immutable policy input; attempts to promote transcript text to directives are rejected with `E_POLICY_FORBIDDEN`. Envelope schema `spec/schemas/llm_envelope.schema.json` codifies the separation (`instructions[]`, `source_content[]`, `system_policies[]`, `safety_tags[]`) and LangGraph adapters verify that directives reference only policy-registered instruction IDs. Per-model policy manifests declare the maximum instruction scope; Guardian rejects runs whose envelope attempts to merge instructions with evidentiary content or bypass policy tags. Each LangGraph node registers an `opa_policy_id` enforced server-side; tool invocations must appear on the per-node allowlist, and escalation attempts emit `OPA_TOOL_ESCALATION_DENIED` audit events.
- Outputs written to `docs/`: `compose_client_v1.md|docx`, `compose_lawyer_v1.md|docx`, bundle excerpt, QA/staff reports. Guardian ensures readiness before reviewer approval.
- Envelopes capture LLM metadata (model, prompt version, region) for reproducibility; FinOps counters track token usage per section.
- See App.D for compose deliverables and QA artifacts and their canonical filenames.
- Model selection: stage-specific profiles defined in `config/llm_assignments.json` map Analyze/Compose lanes to settings keys (`analyze.model.id`, `compose.model.id`) so org/case overrides stay deterministic.

#### 6.4.0 Cancellation & retry semantics (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/agents/compose_runner.py::cancel_and_retry`, Tests `tests/udocket_core/agents/test_compose_cancel_retry.py::test_checkpoint_resume`, Observability Grafana “Compose Pipeline Health” dashboard.

*Purpose: Explain how Compose manages cancellation, checkpoints, and replay safety.*

- `GraphRunner.cancel(job_id, retry_token)` stops all active lanes, requests `cancel()` on outstanding tool invocations, and records per-lane status snapshots (`{lane_id, node_id, state}`) in the tombstone artifact.
- Compose retries depend on persistent checkpoints:
  - Manifests append `{retry_token, retry_generation, lane_progress, weaver_state_digest}`. `lane_progress` records the last committed section per lane; `weaver_state_digest` protects against template drift mid-retry.
  - Section writers marked `idempotent=true` rerun automatically; others require operator acknowledgement (`RETRY_REQUIRES_OPERATOR`) before resubmission.
  - QA nodes re-evaluate only sections that changed in the replay; unchanged sections reference their prior fingerprints, preventing double-counting FinOps metrics.
- Cancellation ensures Document Signer work has not been emitted. If cancellation occurs after signing kicked off, the workflow revokes signatures, deletes draft deliverables, and sets `signing_revoked=true` in the tombstone.
- SSE events follow the contract defined in §10.8: Compose jobs emit `job.running` per lane, `job.blocked` on policy holds (for example, FinOps budget exhaustion), `job.quarantined` when Guardian intervenes, and `job.completed` once deliverables are stored.
- Test coverage: `tests/udocket_core/agents/test_compose_cancel_retry.py` exercises lane-level cancellation, replay from checkpoints, and signature revocation. Synthetic monitor `synthetics/compose_cancel.yaml` validates SSE sequencing and manifest updates in staging.

#### 6.4.1 Deliverable catalog & template registry (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/deliverables/catalog.py::DeliverableCatalog`, Tests `tests/udocket_core/deliverables/test_catalog_activation.py::test_registry_contract`, Observability Grafana “Deliverable Catalog & Templates” dashboard with alert `deliverable_catalog_drift_total`.

*Purpose: Guarantee deliverables stay extensible while remaining policy-gated.*

- System-scope Settings key `deliverables.catalog[]` enumerates every deliverable produced across Transcribe/Analyze/Compose. Each `DeliverableDefinition` captures `deliverable_id`, `stage` (`transcribe|analyze|compose`), `artifact_type`, `default_formats[]` (`txt`, `md`, `pdf`, `docx`), `template_id`, `signature_policy_id`, `client_visibility`, `requires_client_ack`, `default_state` (`enabled|disabled|shadow`), and `implementation_tier` (minor|major) so GraphRunner, Guardian, and the portal share a single source of truth.
- Base catalog entries ship for `TRANSCRIPT_CANONICAL` (Transcribe: `.txt` + PDF wrapper for signing), `SUMMARY_STANDARD` (Analyze summary deliverable), and `SUMMARY_LAWYER` (Compose lawyer document). Future deliverables—`SUMMARY_BRIEF`, `TIMELINE_ONLY`, `TIMELINE_WITH_EVIDENCE`, etc.—are pre-declared with `default_state=disabled` and `implementation_tier=major`; enabling them requires Architecture/Product sign-off and a recorded Implementation Strategy milestone before Settings activation succeeds.
- Template registry, localization packs, and template invalidation events are curated by Reference Manager; see `../services/reference-manager.md §3.4` for schema, approval, and cache contract.
- Organization overrides follow the same schema: uploads enter Guardian review, must pass placeholder linting against the corresponding `DeliverableContext` Pydantic model, and create `TEMPLATE_OVERRIDE_PROPOSAL` artifacts before promotion. Rollback keeps prior versions addressable; CI fixtures under `tests/udocket_core/agents/` validate compatibility end-to-end.
- Every deliverable definition links to a `signature_policy_id` (§7.2.2). Transcripts and summaries default to `SIGN_POLICY_PLATFORM_REQUIRED`; Compose deliverables default to `SIGN_POLICY_PLATFORM_REQUIRED_CLIENT_OPTIONAL`. Pipelines hydrate signature policies when queuing Document Signer work so platform signatures and client attestations stay declarative rather than hard-coded.
- Feature toggles (`deliverables.features.short_summary`, `deliverables.features.timeline_pdf`, etc.) guard UI/API exposure. Guardian rejects enabling toggles tagged `implementation_tier=major` unless the linked Implementation Strategy artifact is `status=approved`, ensuring large-impact additions follow the agreed rollout path.
- Appendix D documents artifact schemas keyed by `deliverable_id`; [`../services/settings-registry.md Appendix A`](../services/settings.md#appendix-a-settings-key-map-traceability-index) cross-references catalog entries with settings/tests/runbooks so auditors can trace coverage for any newly activated deliverable.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/mermaid/overview/tdd/diagrams/data-lineage-v1.png" alt="Artifact data lineage">
  <figcaption style="font-size: 0.9em; color: #555;">Artifact data lineage</figcaption>
</figure>

### 6.5 Timeline and relationship graph agents integration checklist

*Purpose: Define integration requirements for the timeline and relationship graph agents.*

- Both agents adhere to the common contract: deterministic IDs, manifest provenance, Guardian gating, ops logging, and Settings-driven configuration.
- Checklist: define artifact types (Appendix D), extend manifests, register Celery task + SSE events, add ops JSON/JSONL schema, wire Settings keys, update QA/approval flows, and document review UX impacts.
- Integration tests (settings dry-run/diff, policy linting, cross-artifact dependency validation—for example, timeline referencing approved transcripts) run in CI.
- Agents expose FinOps metrics, honor region allowlists, and update the Appendix E traceability map prior to activation.
- **Source material:** `§5`, `§9`, `§10`, `§11`, `§16`, `AGENTS.md`
- **Priority:** High (core agent pipeline)

### 6.6 Agent failure handling & resilience

*Purpose: Standardize failure classes, retries, and safeguards to avoid duplication and policy drift.*

- Failure taxonomy (binding):
  - `TRANSIENT`: upstream 429/5xx/timeouts/network. Action → exponential backoff with jitter; respect `Retry-After`; bounded attempts; trip provider circuit on threshold.
  - `POLICY`: forbidden pattern, redaction breach, region disallow. Action → fail lane; emit Guardian quarantine if applicable; surface actionable reason codes.
  - `INPUT`: bad media/schema. Action → fail lane; no auto-retry; record validation details in ops JSON.
  - `INTEGRITY`: hash mismatch/content drift. Action → block downstream; require resubmit with corrected input; log `ARTIFACT_INTEGRITY_MISMATCH`.
  - `CONCURRENCY`: OCC/version conflicts or lock contention. Action → short jittered retry; escalate if repeated; surface conflict to UI.
  - `REGION_POLICY`: residency disallowance. Action → block and log `RESIDENCY_POLICY_BLOCK`; waivers per §3.8.
- Retries & budgets: default 5 attempts; `backoff_factor=2`; jitter 10-20%; max delay 120s; per-agent overrides allowed via Settings.
- Node idempotency (binding): rerunning a completed lane issues zero new provider calls; outputs identical or schema-equivalent.
- Single-flight: use `udlock` advisory locks for job/lane scopes; hold \< `udlock.max_session_hold_seconds` with heartbeats every `udlock.heartbeat.interval_seconds`.
- Telemetry: export `agent_retry_total`, `agent_lane_fail_total{reason}`, and duration histograms; write ops logs with `attempt`, `final_state`, `reasons[]`.

### 6.7 LangGraph implementation spec (normative)

*Purpose: Standardize graph runtime behavior for Analyze/Compose.*

- Graph state: typed payloads; immutable inputs; explicit checkpoints.
- Nodes & contracts: input/output schemas; side‑effect boundaries; reproducibility requirements.
- Concurrency & ordering: deterministic ordering where needed; fan‑out/fan‑in patterns documented.
- Checkpointing & idempotency: resume from last good node; no duplicate provider calls after success.
- LLM call wrapper (mandatory): consistent logging, redaction, retry, and cost accounting.
- Memory & retrieval policy: bounded context, chunking, embeddings restricted to allowed regions.
- Error classes & actions: per §6.6 taxonomy mapped to node behaviors.
- Source material: `§6.6-§6.10`, `§6.10`

#### 6.7.1 Deterministic identity & fingerprints (normative)

*Purpose: Maintain stable cross-run identifiers without relying on experimental UUID versions.*

- Row identifiers (`artifact.id`, `qa_log.id`, etc.) use UUIDv7 for temporal ordering and compatibility with existing tooling.
- Each lane computes a canonical anchor dictionary (sorted keys, normalized transcript spans, referenced IDs, outline offsets) and hashes it to `content_fingerprint_sha256`.
- Deterministic reference IDs use UUIDv5 with an org-scoped namespace: `namespace_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"uDocket:{org_id}:{case_id}")`; `stable_id = uuid.uuid5(namespace_uuid, content_fingerprint_sha256)`. This keeps IDs stable when anchors match while avoiding disclosure of the raw anchor payload.
- Because LLM outputs are inherently non-deterministic, downstream comparisons rely on the `content_fingerprint_sha256` rather than byte-for-byte equality; replays that diverge mark artifacts for review while preserving the original UUIDv7 identifiers.
- Manifests and JSON artifacts include both `uuid` (UUIDv7) and `content_fingerprint_sha256`; downstream tools prefer the fingerprint for drift detection.
- Per-org secret rotation updates only the namespace seed; historical UUIDv5 values remain valid because manifests treat IDs as immutable once published.
- Test vectors live in `spec/vectors/uuid_fingerprints.json`; CI test `tests/spec/test_uuid_fingerprints.py` asserts canonicalization and UUIDv5 output stability.

Node catalog (illustrative)

| Node                   | Purpose                   | Inputs                       | Outputs                 |
| ---------------------- | ------------------------- | ---------------------------- | ----------------------- |
| OutlineBuilder         | produce narrative outline | transcript, settings         | outline JSON            |
| SectionWriter (client) | draft client section(s)   | outline, settings, templates | section text + metadata |
| SectionWriter (lawyer) | draft lawyer section(s)   | outline, settings, templates | section text + metadata |
| SectionQA              | enforce policy gates      | section text, policies       | QA notes, status        |
| FinalWeave             | assemble deliverable      | sections, templates          | composed MD/DOCX        |

#### 6.7.2 Adoption guardrails & fallback plan

*Purpose: Establish guardrails and rollback paths for LangGraph adoption.*

- Framework encapsulation: LangGraph graphs execute behind `packages.udocket_core.agents.graph_runner.GraphRunner`. Settings key `agents.langgraph.runner ∈ {'langgraph', 'linear'}` plus a CLI override allow swapping to the linear runner for smoke tests or incident mitigation. Contract tests run against both runners to ensure parity.
- Training & SOP: engineering onboarding includes LangGraph workshops, code walkthroughs, and pairing sessions; a living playbook in `docs/runbooks/langgraph-adoption.md` captures patterns, anti-patterns, and upgrade notes.
- Upgrade cadence: LangGraph pinned via Poetry with weekly review of upstream releases; canary staging job (`synthetics/langgraph_canary.yaml`) executes against new versions before upgrade PRs. Major version bumps require ADR review.
- UUID safeguards: default UUIDv7/UUIDv5 strategy (see §6.7.1) is mandatory; no experimental UUID versions are permitted in manifests or identifiers.
- Automated failover: lanes invoke the shared `ModelFailoverOrchestrator` (§8.1.2) so `llm.models[].fallback_chain` is applied consistently across Analyze/Compose/Audit tasks. Each allowed residency region must have at least two approved providers/models in the chain; health probes cycle through providers without leaving the region. The orchestrator surfaces `LLM_FALLBACK_TRIGGERED` events, records parity hashes, and continues processing without human drafting. When the chain is exhausted the queue marks `PAUSED_AWAITING_PROVIDER`; on-call focuses on restoring provider health rather than producing manual content. Manual drafting is not an availability strategy and remains a break-glass SOP only under an executive waiver recorded in Appendix O.

### 6.8 Compose/Policy lint settings (declarative)

*Purpose: Enforce structural and policy rules via settings instead of code.*

- Settings: `compose.policy.*` (forbidden patterns, required sections, link limits) and `analyze.policy.*` for lane checks.
- Lint flow: pre‑publish checks at node and final weave; failures produce QA logs and block Guardian submission.
- Extensibility: org overrides constrained by safety validators in Settings activation.
- Source material: `§6.8`, `§6.4`

### 6.9 Graph versioning & migrations

*Purpose: Allow safe evolution of graphs across versions.*

- Version pins: manifests include graph version; upgrades supported via migration plan per change.
- Compatibility: nodes may support multiple versions; deprecations follow the API deprecation policy.
- Acceptance: migration tests verifying schema equivalence or documented deviations.
- Source material: `§6.9`, `§6.10`

### 6.10 Compose Graph details (parallels Analyze)

*Purpose: Provide deeper detail on Compose graph structure and gates.*

- Lanes: client and lawyer lanes in parallel; optional bundle excerpt lane; shared OutlineBuilder and FinalWeave.
- Concurrency: SectionWriter nodes run in parallel with bounded concurrency; OCC on artifact writes; udlock on section scopes.
- Retries: per‑section retry budgets; failures summarized in QA; forbidden patterns and missing sections block FinalWeave.
- Provenance: per section envelope logged with model/prompt versions; manifests include graph_version and template versions.
- QA gates: enforce required sections, link counts, references, and forbidden patterns (`compose.policy.*`).
- Source material: `§6.10`

### 6.11 Agent schemas and error codes

*Purpose: Provide typed outputs per lane and a canonical error taxonomy mapping.*

- Schemas (illustrative Pydantic models):
  - Analyze: `SummaryJSON`, `OutlineJSON`, `TimelineSeed`, `EntityHint`, `StaffReport` with `uuid`, `source_span`, `evidence_refs[]`.
  - Compose: `SectionOutput { section_id, role: client|lawyer, text_md, envelope_id, issues[] }`.
  - QA: `QAIssue { code, level, message, ref?, location? }`.
- Example Pydantic models (Analyze extract): see App.U.1 for the canonical typed definitions including source-span handling and deterministic enums.
- Compose JSON example: App.U.2 captures the Compose document/section models with default factories and typed references.
- Error codes (binding):
  - `E_TRANSIENT_PROVIDER` (TRANSIENT): wrap 429/5xx/timeouts; retry per §6.6.
  - `E_POLICY_FORBIDDEN` (POLICY): forbidden pattern redaction failure; fail lane.
  - `E_INPUT_INVALID` (INPUT): schema/media invalid; fail lane with details.
  - `E_INTEGRITY_MISMATCH` (INTEGRITY): hash/content drift; quarantine and halt.
  - `E_CONFLICT` (CONCURRENCY): OCC/lock conflict; short retry then surface.
  - `E_REGION_BLOCK` (REGION_POLICY): residency disallow; block with remediation.
- Mapping: All error codes must map to §6.6 failure taxonomy; ops JSON must include `{ code, class, message, attempt, final }`.

### 6.12 Quality KPIs & monitoring

*Purpose: Make analysis, transcription, and Guardian quality targets measurable and auditable.*

- **Speech accuracy:** Word Error Rate (WER) target ≤ 8 % for on-demand, ≤ 6 % for batch transcripts measured against quarterly golden sets; dashboards plot WER trend per language with alerts when ≥ 2 % regression (`metrics: transcription_wer_pct{mode, language}`).
- **Guardian effectiveness:** False-negative rate (quarantined after customer exposure) ≤ 0.5 % per quarter, false-positive (unjustified quarantine) ≤ 5 % with remediation documented in Appendix B.2 review log. Weekly sampling validates judgment reasons against the policy matrix using `guardian_quarantine_false_positive_total` vs `guardian_judgment_total` to quantify drift and trigger tuning.
- **Review delta:** Reviewer change rate for Analyze/Compose deliverables \< 15 % of sections (measured via `qa_log` issue density and Manual/Agent edit diffs). Exceeding thresholds triggers regression analysis in LangGraph acceptance tests (§13.3).
- **QA defect density:** `qa_issue_density` metric targets ≤ 0.2 blocking defects per artifact; Compose/Analyze QA lanes surface severity distribution for release gates.
- **FinOps + quality blend:** Track tokens-per-approved artifact and rejection counts to ensure budget adherence does not degrade quality; anomalies produce decision-log entries (§15.3).
- Quality KPIs feed quarterly leadership reviews; results archived as `QUALITY_KPI_REPORT` artifacts in Appendix D catalog.

### 6.13 Shadow mode deployments (binding)

**Breadcrumbs:** Implementation `apps/platform/operations/shadow.py::run_shadow_pipeline`, Tests `tests/platform/operations/test_shadow_mode.py::test_divergence_reporting`, Observability Grafana “Agent Shadow Runs” dashboard with metric `agent_shadow_divergence_total`.

*Purpose: Let new agent behaviours soak in production safely before they become user-visible.*

- Activation: flip `agents.shadow_mode.enabled=true` (ORG/CASE scope) to run the new lane/pipeline against live inputs while suppressing downstream writes. Shadow executions read the same settings snapshot as production jobs and log outputs under `ops/<job_id>__shadow_<agent>_log.json` plus case-level JSONL streams (`ops_shadow_<agent>.jsonl`).
- Evaluation metrics: compare shadow vs primary outputs using divergence counters (`shadow_match_rate`, `shadow_token_delta`, `shadow_runtime_ratio`) and reviewer sampling tasks. An alert (`agent_shadow_divergence_total`) fires when divergence exceeds configured tolerances.
- Promotion checklist: (1) shadow match rate ≥ 98% over the agreed soak period, (2) no open Sev-2/3 incidents attributed to the shadow agent, (3) Product/Security sign-off recorded in the decision log, and (4) App.T traceability row updated with tests/monitors/runbooks.
- Rollback: disable via settings toggle; purge shadow outputs with `ops/scripts/agents/cleanup_shadow.py` to avoid confusing reviewers.
- Isolation guarantee: shadow artifacts never transition beyond `DRAFT_SHADOW` and are excluded from Guardian submission, portal listings, or cost/billing tallies; only divergence metrics and audit trails are surfaced to staff for analysis.
- Abuse coverage: shadow runs feed the abuse prevention detectors (§B.4) so fraud heuristics see the same traffic profile before we expose new flows to customers. Per-org thresholds for shadow soak (`abuse.shadow.threshold_per_org`) require dual approval at activation, expire automatically with the soak window, and are linted by `settings:lint-keys` so relaxed thresholds cannot persist once the feature goes live.

______________________________________________________________________

## 7) Digital signing & Guardian services

### 7.1 Guardian service (summary)

*Purpose: Highlight platform touchpoints with Guardian.*\
*Contract: Guardian architecture, policy, interfaces, and operations are defined in [`../services/guardian.md`](../services/guardian.md); this section lists the integration points.*

- Lifecycle gating: Guardian enforces SA/WP/CD transitions from `PENDING_JUDGMENT` to the statuses in §5.2.3 after PASS/WARN/WAIVED decisions. Queue semantics and detection tiers remain documented there.
- Policy & waivers: Policy bundles, waiver handling, and quarantine ownership stay with Guardian; approvals (§5.4) and retention (§14) depend on those controls.
- Operations: Guardian SLOs, runbooks, and manual review procedures stay with that team; review queue gating (§5.2) and portal invalidation (§11.2.1) represent the platform dependencies.
- Artifacts & manifests: Guardian judgment IDs, reason codes, and settings hashes persist in manifests consumed by Signer and Portal; schema and payload examples live there.

### 7.2 Digital signature service (summary)

*Purpose: Highlight signer touchpoints while delegating implementation detail to the canonical spec.*\
*Contract: Document Signer architecture, trust roots, TSA/OCSP integration, and FIPS enforcement live in [`../services/digital-signer.md`](../services/digital-signer.md); this section summarises dependencies.*

- Platform signatures: Document Signer converts canonical content to PDF/A (or COSE/JWS), applies platform signatures, and records signature manifests with TSA/OCSP evidence. Deliverables remain blocked until Guardian verifies the manifest.
- Signature policies & acknowledgements: Settings `sign.signature_policies[]` drive platform signatures and client acknowledgement flows. Portal prompts for countersignatures where required and stores auxiliary artifacts referenced in manifests. Full policy catalog, default mappings, and waiver handling appear in §2.2 of the signer spec.
- Trust roots & PKI: Managed HSM keys, offline/online certificate hierarchy, and rotation procedures are documented in §2.3. Settings activation validates attestation (`sign.hsm.key_id`, `sign.trust_roots[]`) and records `SIGN_TRUST_ROOTS@<version>` artifacts.
- TSA/OCSP posture: Soft-fail windows, responder failover, and metrics (`ocsp_latency_seconds`, `tsa_time_drift_seconds`, `sign_verify_status_total`) are owned by the signer service (§2.4, §5.1). Portal quarantine behaviour after soft-fail windows inherits from that spec.
- FIPS compliance: `security.crypto.fips_requirement` and deliverable policies dictate FIPS mode. Startup attestation, algorithm enforcement, waiver governance, and monitoring live in §7.
- APIs: Signing, verification, and certificate retrieval endpoints plus acknowledgement flows are formalised in signer §3. Integrators MUST use HMAC headers and Idempotency keys per that contract.

### 7.3 Request signing and verification (HMAC)

*Purpose: Authenticate inter-service calls crossing trust boundaries.*

- All mutating APIs (Guardian, Signer, Settings activation) require HMAC headers: `X-Signature-Key-Id`, `X-Timestamp` (RFC3339), `X-Request-Signature`, plus `Idempotency-Key` when supported.
- Signature computed over canonical request components (`method`, `path`, `timestamp`, `body hash`) with org/service-specific shared keys stored in managed secrets.
- Receiver validates timestamp skew (absolute difference ≤ 120 seconds configurable via `security.hmac.max_clock_skew_seconds`), looks up key ID, recomputes signature, and rejects mismatches with `401 AUTH_CLOCK_SKEW` when the timestamp is out of range or `401 AUTH_SIGNATURE_INVALID` for digest mismatch. Clients should keep system clocks within ±60 seconds; retries near the boundary add ±30 seconds random jitter to avoid flapping. Replay protection uses `Idempotency-Key` + short-lived cache.
- Rotation handled via dual-publish of keys; clients send new key ID with overlap window. Appendix F includes request/response examples.

#### 7.3.1 Key rotation flows (normative)

*Purpose: Ensure safe rollovers without request loss.*

- Dual-publish: maintain `{current, next}` keys; announce rotation window; accept both for N days.
- Cutover: flip `current=next`; generate new `next`; revoke old with grace; update service configs via Settings activation.
- Audit: record rotation events; correlate with error spikes; roll back if verification failures increase.
- Emergency revoke: push denylist for compromised key IDs; page on-call; rotate immediately; verify traffic returns to normal.

### 7.4 Audit trails and judgment history models

*Purpose: Provide tamper-evident records for regulators and incident response.*

- Guardian judgment history schema, retention, and secure view exposure are owned by the service; this section focuses on signing/audit integrations that cross services.

- Signing operations append to `audit_event` with actor metadata, IP, UA, and payload referencing trust-root version and TSA token hash.

- Ops JSONL streams (`ops_transcription.jsonl`, `ops_summary.jsonl`, `ops_compose.jsonl`) capture agent-level context used by Guardian during investigation.

- Break-glass events, waiver usage (cross-region), and trust-root updates require dual approval and generate dedicated audit artifacts per §14 / Appendix D.

- Observability dashboards highlight Guardian judgment rates, backlog age (`guardian_pending_oldest_seconds`), quarantine reason codes, and signature verification outcomes for compliance teams.

- **Source material:** `§5.2`, `§6`, `§7.4`, `App.A` sequence

- **Priority:** High (legal compliance)

______________________________________________________________________

## 8) LLM governance & runtime

The canonical specification for registry, moderation, FinOps, and replay requirements lives in [`../services/llm-registry.md`](../services/llm-registry.md). This overview retains the intent and integration edges that other platform components rely on:

- **Provider registry & residency:** Compose/Analyze lanes must call the registry for every LLM invocation. Residency allowlists, failover parity, and waiver handling are enforced per §2.1 of the service spec; Guardian/Settings tests ensure policy drift pages the RB-LLM-003 responders.
- **Prompts, redaction, and evidence:** Prompt templates, masking rules, and reproducibility envelopes follow §2.2. Jobs record envelope IDs in manifests and depend on the evidence store for replay audits. HIPAA posture requires masked prompts everywhere outside the evidence store.
- **Safety harness & moderation:** Pre-call filters, multi-stage moderation, QA evaluators, and Guardian quarantine workflow are defined in §2.3 with ops playbooks RB-LLM-JB/Jailbreak. WARN-mode tuning is limited to non-production orgs and is time-bound.
- **FinOps guardrails:** Token ceilings, monthly caps, deploy gates, and budget hold workflows follow §2.4. Compose/Analyze workers surface `PAUSED_AWAITING_BUDGET` and SSE warnings when the FinOps controller halts spend; overrides require dual approval.
- **Replay & provenance:** Reproducibility envelopes, golden-set drills, and the illustrative provider matrix live in §§4.1–4.2. Job retry tooling must carry `envelope_id`/`retry_token` pairs so operators can execute RB-LLM-REPLAY without losing traceability.
- **Runbooks & dashboards:** Operational responders rely on RB-LLM-003 (circuit), RB-LLM-JB (moderation), RB-LLM-FINOPS (budgets), and RB-LLM-REPLAY (envelopes). Observability dashboards referenced in the service spec remain mandatory for SRE review.

Appendix I retains the shared glossary for LLM terminology referenced by both this overview and the service spec.

______________________________________________________________________

## 9) Configuration & settings platform (binding)

**Breadcrumbs:** See [`../services/settings-registry.md`](../services/settings.md) for implementation, test, and observability anchors that govern the Settings Registry. *Purpose: Keep the platform TDD aligned with the dedicated Settings Registry specification while summarizing integration obligations.* *Contract: Platform services MUST consume Settings Registry snapshots, honor activation governance, and surface audit metadata per [`../services/settings-registry.md`](../services/settings.md).* *State: Jobs, artifacts, and policy contexts record `settings_snapshot_sha256` and version identifiers supplied by the Settings Registry; activation history, waivers, and diff artifacts persist in the service tables described there.* *Failure modes & retries: When snapshot fetches fail or unsafe activations occur, platform workloads pause new jobs and follow the rollback/approval workflows referenced in [`../services/settings-registry.md §4`](../services/settings.md#4-activation-workflow-governance).* *Observability: Platform dashboards monitor `settings_snapshot_stale_total`, `settings_activation_total`, and governance alerts emitted by the Settings Registry; see [`../services/settings-registry.md Appendix B`](../services/settings.md#appendix-b-metrics-alerts).*

- Service charter, APIs, activation workflow, caching, telemetry, and governance controls for the Settings Registry live in [`../services/settings-registry.md`](../services/settings.md).
- Agent pipeline bundles, tool catalogs, LLM profiles, and seed bundle processes are defined in [`../services/settings-registry.md §5`](../services/settings.md#5-agent-automation-configuration); platform agent sections reference those contracts instead of re-describing keys here.
- Integration requirements for Guardian, Localization & Policy Engine, Reference Manager, portal, and worker pipelines are captured in [`../services/settings-registry.md §6`](../services/settings.md#6-integrations-enforcement-points).
- Residency controls, rate limits, FinOps guardrails, compliance toggles, and approval behaviour rely on settings enumerated in [`../services/settings-registry.md Appendix A`](../services/settings.md#appendix-a-settings-key-map-traceability-index); platform sections cite that inventory for authoritative key coverage.

______________________________________________________________________

## 10) APIs & integration contracts

### 10.0 API contract & lifecycle governance

*Purpose: Anchor the narrative TDD to machine-readable contracts and a predictable change cadence.*

- Canonical OpenAPI 3.1 specifications live under `ops/openapi/` (`uDocket-platform.openapi.yaml` for staff/client surfaces, with service-specific overlays). Every PR that changes endpoints must update the spec and rerun `make lint-openapi` (`npx spectral lint ops/openapi/**/*.yaml --ruleset ops/openapi/spectral.yaml`); CI blocks merges when lint or diff checks fail. `make lint-schemas` validates `spec/schemas/*.json` (enforcing `additionalProperties=false` where required, string length caps, and enumerations) so generated models stay aligned with the OpenAPI components.
- Shared JSON Schemas live under `spec/schemas/` and are treated as the single source of truth for reusable components. Code generators (Python/TS) consume these schemas so no handwritten Pydantic model drifts from the published contract.
- Breaking or materially user-visible changes require an ADR (see `docs/adr/README.md` and linked entries such as `ADR-0003-api-versioning-and-sunset.md`) approved by Architecture + Security before the change can progress from **Provisional → Implementable → Implemented**.
- Versioning policy: monthly “compatible” releases roll on the first business Monday; clients may pin to older behaviour via `X-uDocket-API-Version: YYYY-MM`. Majors ship at most twice per year, demand 90-day notice, and use calendar-versioned prefixes (`2025-02`), while additive changes batch unless explicitly waived.
- Deprecations follow the cadence published in `docs/api/DEPRECATIONS.md`: announce, provide migration guides, emit `Sunset` headers 90 days before removal, and confirm monitors stay green before final removal (traceability captured in App.T).
- Deprecation headers follow RFC 9745 structured-field syntax (e.g., `Deprecation: @1780272000; sunset="Mon, 01 Jun 2026 00:00:00 GMT"`) and always pair with `Link: rel="deprecation"` to machine-readable migration notes plus RFC 8594 `Sunset` headers; Spectral rule `sunset-header` enforces the trio.
- Stripe-style public docs and code samples render directly from the OpenAPI bundle so that examples, schemas, and error contracts stay synchronized with the source of truth.

### 10.1 REST and WebSocket conventions (naming, pagination, errors)

*Purpose: Standardize interface behavior across services for ease of integration.*

- REST base path `/api/v1/` per service; plural resources (`/cases`, `/artifacts`). Mutations use optimistic concurrency (`version`) for idempotent semantics.

- Mutating operations (`POST`, `PUT`, `PATCH`, `DELETE`) require an `Idempotency-Key` header (UUIDv7, 24h TTL minimum) so retries remain side-effect free across deployments; servers reject missing or replayed keys with `409 CONFLICT` (`details.reason="IDEMPOTENCY_SIGNATURE_MISMATCH"`) and surface the original response payload when possible.

- Pagination envelope `{items, page, page_size, total, next_page}`; sorting `?sort=field:asc`. Invalid sort or masked fields → 400.

- Error envelope conforms to `spec/schemas/api_error.schema.json`; servers always include `X-Request-ID` and reuse the schema-generated models in runtime code. Rate-limit headers exposed to browsers (see §10.5 CORS contract).

  ```json
  {
    "error": {
      "code": "CASE_NOT_FOUND",
      "message": "Case 22222222-2222-2222-2222-222222222222 is archived",
      "details": [{"field": "case_id", "message": "archived cases are read-only"}]
    },
    "trace_id": "4f4c9f7d09e141d8be6d1f8d0d6d88e4"
  }
  ```

- Real-time:

  - SSE for jobs/cases; every payload includes `schema_version` (string) and `emitted_at` (RFC3339). Servers emit `progress|status|error|artifact_status` only after committing DB transactions. Monotonic event IDs via Redis `sse:case:{case_id}:seq`. Breaking changes bump `schema_version`; clients must branch on the value, and CI fixtures cover each schema version (App.U).
  - Channels (WebSocket) for collaborative editing and controls; OIDC-authenticated; topics namespaced per case/job.

- RBAC/masking: all reads select from `*_secure` views; serializers never “unmask” redacted fields. Gateway rejects spoof headers (`X-Org-ID`, `X-Active-Roles`); authorization derives solely from OIDC claims.

List contracts (normative)

- Sorting: only on whitelisted fields; multiple fields separated by comma; direction with `:asc|:desc` (default asc). Invalid field/direction → 400.
- Filtering: query params match exact fields; masked fields are not filterable; server may return 400 if filter would breach masking.
- Examples: `?sort=created_at:desc, type:asc&page=2&page_size=50`; `?case_id=<uuid>&type=SUMMARY_MD`.

### 10.2 Artifact/job/review endpoints

*Purpose: Document key CRUD operations and state transitions.*

- Artifacts

  - List: `GET /api/v1/artifacts?case_id=&type=&class=&status=&archived=&page=&page_size=` (RLS-scoped). Org-wide listing via `scope=org` uses token `active_org_id`; `org_id` param not supported.
  - Create: `POST /api/v1/cases/{case_id}/artifacts` with `{type, class?, file|json, manifest}`. Source uploads finalize to `status='STORED'`; derived outputs enter `status='PROCESSING'` until workers flush content and set `status='PENDING_JUDGMENT'`.
  - Get: `GET /api/v1/artifacts/{artifact_id}`; Download: `GET /api/v1/artifacts/{artifact_id}/download` (requires `status='APPROVED'` for CDs or `status='RELEASED'` for DLs; other classes are never exposed to portal clients).

- Jobs

  - Create: `POST /api/v1/cases/{case_id}/jobs/{kind}` with `Idempotency-Key` (TTL default 24h) → returns job id. Responses embed a stable `retry_token` that replays the same run when passed to `POST /api/v1/jobs/{id}:retry` after remediation.
  - Get: `GET /api/v1/jobs/{id}`; Control endpoints use RPC-style suffixes: `POST /api/v1/jobs/{id}:pause`, `POST /api/v1/jobs/{id}:resume`, `POST /api/v1/jobs/{id}:cancel`, `POST /api/v1/jobs/{id}:retry`. Each call requires OCC on `version` plus an `Idempotency-Key` header (and optional payload `idempotency_key` for provider propagation). Cancellation is a three-step contract shared across producers:
    1. Transition `PENDING|QUEUED|RUNNING|PAUSED|PAUSED_AWAITING_BUDGET|PAUSED_AWAITING_PROVIDER → CANCELING`, emit SSE `job.accepted` (if the job was queued) followed immediately by `job.canceling` `{schema_version, emitted_at, job_id, actor_id, reason}` so clients cease optimistic progress polling.
    1. Invoke provider-specific aborts (Azure Speech Batch delete, Azure Speech streaming stop, LangGraph lane abort). Azure Speech/SAS uploads revoke signed URLs, purge staging containers, and log `azure_batch_job_deleted`; LangGraph lanes cancel tool execution and release advisory locks. Providers have a 60-second grace period before the platform force-marks them canceled.
    1. Finalize `CANCELING → CANCELED`, emit SSE `job.canceled` and `artifact.status` updates for affected artifacts, append audit event `JOB_CANCELED` (`reason`, `actor_id`, `provider_outcome`), and write a tombstone auxiliary record (`class='AR'`, `type='JOB_CANCELLATION_REPORT'`) capturing checkpoints, partial outputs, and cleanup actions. Downstream artifact creation halts; any partially staged artifacts persist with `depends_on_canceled_job=true` so operators can inspect context before retrying. Repeated cancels are idempotent; only the states enumerated above accept the transition.
  - Provider-specific retry semantics: each manifest stores `retry_token` and `retry_generation`. Workers MUST include that token when re-queuing failed runs so at-least-once retries remain idempotent. Tool invocations obtained through `agents.tools.catalog[]` declare `idempotent=true|false` and expose an optional `tool_idempotency_key` so GraphRunner can dedupe external calls when recovering from job restarts.
  - Progress SSE: clients subscribe to `GET /api/v1/jobs/{id}/events` with `If-None-Match` (digest of last processed manifest). Servers respond with `ETag` headers and emit the event grammar defined in §10.8 (`job.accepted`, `job.running`, progress updates, policy holds, completion, cancellation).
  - Provider progress normalization: `ProviderProgressAdapter` implementations wrap Azure Speech Batch, Azure OpenAI, and future providers to emit `{phase, percent_complete, estimated_remaining_seconds}` snapshots. Workers surface these snapshots via `job.update` SSE payloads (`provider_progress` field) and persist them in `job_checkpoint.progress_meta`. Pause/resume/cancel commands call into the adapters to ensure idempotent provider control; a failed provider-side pause never advances the internal state machine. Each adapter implements the `cleanup()` hook invoked during cancellation step 2 above (revoke SAS URLs, purge temporary blobs, finalize manifests). Tests live in `tests/platform/jobs/test_provider_progress_adapter.py`.
  - Provider health endpoint: `GET /api/v1/providers/health` aggregates the latest adapter heartbeats per `{provider, region}`. Responses are cacheable for 10 s, include `status`, `latency_ms_p95`, `error_rate`, and the timestamp of the freshest signal, and drive the `provider.health` SSE tick for operator dashboards. Health degradation raises `provider.health` events even when no jobs are active.
  - Progress watchdog (binding): the `job_progress_heartbeat` table records `{job_id, last_heartbeat_at, progress_pct}` updates from workers. A dedicated watchdog task scans for `RUNNING` jobs whose heartbeat age exceeds `jobs.watchdog.no_progress_minutes`; it emits `job_watchdog_warning_total`, raises SSE `job.update` with `status="RUNNING"`, `warning="NO_PROGRESS"`, and annotates the job record. If the heartbeat age exceeds `jobs.watchdog.timeout_minutes`, the watchdog transitions the job to `FAILED`, increments `job_watchdog_timeout_total`, files audit event `JOB_WATCHDOG_TIMEOUT`, and invokes [Runbook RB-JOB-WATCHDOG](../ops/runbooks/index.md#rb-job-watchdog). Watchdog actions never mutate jobs already `COMPLETED|FAILED|CANCELING|CANCELED`; recoverable jobs remain resumable thanks to checkpoint metadata (§6.2, §6.3, §6.4).
  - Overlap guard: advisory lock `jobkind:{case_id}/{kind}`; conflicts → 409 `JOB_KIND_BUSY`.

- Reviews (OCC + swap lock)

  - Approve: `POST /api/v1/reviews/{artifact_id}/approve {note?, expected_version}`; acquires `case-approval:{org}/{case}/{type}`, archives prior `APPROVED` CDs, and transitions `QUEUED_FOR_REVIEW → APPROVED`. Returns 200 idempotent when already approved with matching version.
  - Request changes: `POST /api/v1/reviews/{artifact_id}/changes {reject_reason, note, expected_version}`; sets `status='CHANGES_REQUESTED'` and records reviewer metadata. Mandatory `reject_reason` enumerated in §5.2.4.
  - Quarantine: `POST /api/v1/reviews/{artifact_id}/quarantine {quarantine_reason, note, expected_version}`; records reviewer choice, routes through Guardian for logging, and sets `status='QUARANTINED'`. UI-facing “review phase” filters are derived from `status` only.
  - Resubmit: `POST /api/v1/artifacts/{artifact_id}:resubmit {retry_token}` re-queues a `CHANGES_REQUESTED` or policy-unblocked `QUARANTINED` artifact. The endpoint requires matching `retry_token` from the prior manifest to guarantee idempotent retries and transitions the artifact back to `PROCESSING → PENDING_JUDGMENT` with a new version.

### 10.3 Upload lifecycle & idempotency model

*Purpose: Ensure uploads remain tamper-evident and recoverable.*

- Flow: `POST /api/v1/cases/{case_id}/uploads` creates staging record; client uploads to SAS URL; `POST /api/v1/uploads/{id}/finalize` with `Idempotency-Key` + HMAC promotes to artifact.
- Finalize transaction:
  1. Acquire advisory lock via `udlock.xact_lock('uploadsession', upload_session_id)` (helper `with_idempotency_lock`).
  1. Validate session (`status='PENDING'`, not expired) and presence of staging object.
  1. Verify provided hash/size/type against policy.
  1. Server-side COPY staging object to `/org/{org}/case/{case}/artifact/{artifact_id}/content.bin`.
  1. Insert artifact row (`class='SA'`, `status='STORED'`, immutable fields set) with new UUIDv7 and manifest payload.
  1. Update session `status='FINALIZED'`; downstream workers automatically transition derived artifacts to `PENDING_JUDGMENT` and enqueue Guardian evaluation.
- `upload_session` rows remain short-lived; antivirus and content scanners transition `status` through `UPLOADED` and `SCANNING` before finalize. A janitor task clears `EXPIRED`/`ABORTED` sessions and deletes orphan staging blobs.
- Idempotency: reuse key within TTL returns the same `artifact_id`; reuse with different payload → 409 `CONFLICT` (`details.reason="IDEMPOTENCY_SIGNATURE_MISMATCH"`). TTL default 24h (`api.idempotency.ttl_hours`).
- Retention: expired keys are purged nightly (and opportunistically on insert) so the table stays bounded; retries beyond TTL must supply a fresh key.
- Session expiry via janitor; stale sessions cleaned with `EXPIRED`. Range requests supported; all downloads require `APPROVED` state.

#### 10.3.1 Idempotency keys store (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/idem/store.py::IdempotencyStore`, Tests `tests/platform/api/test_idempotency_store.py::test_replay_returns_cached`, Observability Grafana “API Idempotency” dashboard (metric `idempotency_replay_total`).

*Purpose: Provide a generic mechanism for safe retries across create/approve flows.*

```sql
CREATE TABLE idempotency_keys (
  org_id UUID NOT NULL,
  scope  TEXT NOT NULL,                -- e.g., 'job:create'
  key    TEXT NOT NULL,
  endpoint TEXT NOT NULL,              -- canonical "METHOD:/api/v1/..." string
  case_id UUID NULL,
  request_hash BYTEA NOT NULL,         -- sha256 of canonicalised body+query payload
  status TEXT NOT NULL DEFAULT 'in_progress', -- {'in_progress', 'succeeded', 'conflict'}
  result_ref TEXT NULL,                -- e.g., job_id
  response_code INTEGER NULL,
  response_hash BYTEA NULL,            -- sha256 of JSON response/body when persisted
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (org_id, scope, key)
);
CREATE INDEX idempotency_keys_expiry_idx
    ON idempotency_keys (expires_at);
CREATE UNIQUE INDEX idempotency_request_dedupe_idx
    ON idempotency_keys (org_id, scope, endpoint, request_hash);
```

Handler pattern

1. `udlock.xact_lock(scope, CONCAT(:org_id, '/', :key))`.
1. Normalise endpoint to `METHOD:/path` (path variables preserved) and compute `request_hash = sha256(canonical_request_bytes)` via `packages.udocket_core.idem.hash_request`.
1. Insert `(org, scope, key, endpoint, case_id, request_hash, result_ref, response_code, response_hash, status, expires_at)` on first execution with `expires_at = now() + make_interval(hours => :ttl_hours)`. Conflicts where `request_hash` differs MUST raise 409 `CONFLICT` with `details.reason="IDEMPOTENCY_SIGNATURE_MISMATCH"`; matching hashes update `last_seen_at` and return `result_ref`.
1. Optional overlapping-run guard per case/kind: `udlock.try_lock('jobkind', CONCAT(:case_id, '/', :kind))` → 409 `JOB_KIND_BUSY` if held.

- Canonical scopes (binding): `IDEMPOTENCY_SCOPES = {'job:create', 'job:checkpoint', 'artifact:approve', 'artifact:upload', 'upload:finalize'}` exported from `packages.udocket_core.idem.constants`. Services **MUST NOT** invent ad-hoc strings; CI lints specs and Python call sites to use the constant set.

- Response contract: any API that accepts `Idempotency-Key` **MUST** echo the exact value in the response headers for success and error paths (`Idempotency-Key: <value>`) and emit `Idempotency-Status: fresh|replay|conflict`. OpenAPI lint (`ops/openapi/rules/idempotency-echo.yaml`) enforces the headers on 2xx/4xx/5xx responses.

- Nightly janitor job `ops/idempotency/purge.py` deletes expired rows and runs `VACUUM (ANALYZE)` to keep the table bounded; `expires_at` is pinned to `api.idempotency.ttl_hours`.

  | Binding                   | Implementation                                                                                | Test                                                                                       | Observability                                                 |
  | ------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------- |
  | Canonical scope constants | Implementation: `packages/udocket_core/idem/constants.py::IDEMPOTENCY_SCOPES`                 | Test: `tests/udocket_core/idempotency/test_scopes.py::test_scope_constant_matches_db`      | Observability: Buildkite `lint-idempotency` step (scope diff) |
  | Response echo header      | Implementation: `apps/platform/common/middleware/idempotency.py::IdempotencyHeaderMiddleware` | Test: `tests/platform/api/test_idempotency_header.py::test_response_echoes_header`         | Observability: API metrics `idempotency_echo_missing_total`   |
  | Replay semantics          | Implementation: `packages/udocket_core/idem/service.py::upsert_key`                           | Test: `tests/platform/api/test_idempotency_replay.py::test_same_key_same_body_vs_conflict` | Observability: Audit event `IDEMPOTENCY_CONFLICT`             |

#### 10.3.2 Reviews API (binding)

**Purpose:** Provide the REST surface for reviewer actions without duplicating lifecycle logic.\
**Contract:** All approval paths defer to the ExclusiveSwap invariant in §5.4.1; this API performs validation, parameter handling, and audit fan-out only.\
**State transitions:** `approve` drives `QUEUED_FOR_REVIEW → APPROVED` and promotes the DL via §5.4.1; `changes` sets `CHANGES_REQUESTED`; `quarantine` routes through Guardian and lands in `QUARANTINED`. App.A.2 depicts the same transitions.\
**Failure modes & retries:** Stale versions raise `409 CONFLICT`, signer timeouts bubble as retryable errors, Guardian unavailability triggers Appendix B.1 manual mode, and portal invalidation runs idempotently.\
**Observability:** `reviews_api_requests_total`, `approval_swap_conflict_total`, `review_decision_latency_seconds`, audit events `REVIEW.APPROVED|CHANGES_REQUESTED|QUARANTINED`.\
**Breadcrumbs:** Implementation `apps/platform/api/reviews.py`, Tests `tests/platform/api/test_reviews.py::test_review_endpoints_require_exclusive_swap`, Observability Grafana “Reviews API” panel.\
**References:** §5.2.4–§5.2.6, §5.4.1, §7.1, App.A.2.

- `POST /api/v1/reviews/{artifact_id}/approve {note?, expected_version}` — Validates payload, verifies OCC, and invokes the Shared approval service that applies the ExclusiveSwap invariant. Success returns the promoted artifact envelope; replays (`Idempotency-Key`) surface `Idempotency-Status: replay`.
- `POST /api/v1/reviews/{artifact_id}/changes {reject_reason, note, expected_version}` — Requires enums from §5.2.4, persists reviewer metadata, emits `REVIEW.CHANGES_REQUESTED`, and returns the updated artifact snapshot.
- `POST /api/v1/reviews/{artifact_id}/quarantine {quarantine_reason, note, expected_version}` — Registers the decision with Guardian (`POST /guardian/quarantine`) so the canonical record remains in its history store, updates the artifact to `QUARANTINED`, and invalidates dependent deliverables.

### 10.4 Guardian, Settings, Reference Manager, and Signature APIs

*Purpose: Enumerate service-specific endpoints integrations rely on.*

- Guardian: judgment submissions flow through the worker RPC queue automatically; only health/synthetic endpoints (`/healthz`, `/readyz`, `/rulesz`, `/synthetic/status`) remain exposed for observability. Administrative tooling uses `POST /guardian/judgments:enqueue` for drift corrections, `POST /guardian/quarantine` for reviewer-initiated actions, and the public REST helper `POST /api/v1/judgments` (see §5.2.3.1) for recording human decisions—each requires HMAC service tokens and reuses the same async bus/metrics as production traffic. Per-object “submit” routes are forbidden.
- Settings: `GET /api/v1/settings/<scope>`, `POST /api/v1/settings/bundles`, `/api/v1/settings/validate/*` for regions/privacy, `GET /api/v1/settings/changelog`.
- Reference Manager: REST, SSE, and automation surfaces documented in `../services/reference-manager.md §4.1`; this platform TDD defers detailed endpoint contracts to that specification.
- Digital Signer: `POST /api/v1/sign`, `POST /api/v1/sign/verify`, `GET /api/v1/sign/certificates/{artifact_id}`.
- Privacy & governance: `POST /api/v1/privacy/dpia`, `POST /api/v1/privacy/ropa`, list/read endpoints (`GET /api/v1/privacy/dpia`, `/api/v1/privacy/ropa`), entitlement history (`GET /api/v1/admin/entitlements/history`). All responses include `X-Request-ID` and follow the ApiError schema; OpenAPI specs tag operations with `privacy` and enforce auditor-only access.
- Security: HMAC signing required for all mutating operations; examples in Appendix F. SSE under `/api/v1/jobs/{id}/events`.

### 10.5 OpenAPI governance, linting, and example requirements

*Purpose: Keep API documentation consistent and machine-validated.*

- Authoring rules (binding): new operations must reuse shared components (`ApiError`, pagination envelope, security schemes), declare response examples for 2xx/4xx, include tag + summary, document every required header, and map path parameters to UUID formats where applicable. Specs are edited via `ops/openapi/*.yaml`; commits must update corresponding changelog entries.
- Specs: OpenAPI 3.1 with `x-stability` tags (`stable|beta|experimental`); deprecations emit RFC 9745-compliant `Deprecation` headers (e.g., `Deprecation: @1780272000; sunset="Mon, 01 Jun 2026 00:00:00 GMT"`) alongside RFC 8594 `Sunset` headers (≥90 days) in accordance with §10.0 policy.
- Spectral rules (`ops/openapi/spectral.yaml`): enforce `oidc`, `hmacSignature` on mutating ops, error envelope on 4xx/5xx, shared pagination, forbid org/role spoof headers, and fail any spec whose `openapi` field is not `3.1.*` via the `openapi-version` rule.
- Examples must not include real PII; Spectral rule `no-pii-examples` enforces masking, and rate-limit responses (429) must include `Retry-After`/`X-RateLimit-*` headers as shown in Appendix F.
- CORS exposure (binding): expose `X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After, ETag, Deprecation, Sunset`. Preflight MUST allow the header set defined in Appendix F.11 (`Authorization, Content-Type, Idempotency-Key, X-Request-Signature, X-Signature-Key-Id, X-Timestamp, If-Match, If-None-Match, If-Range, X-Style-Nonce, X-Script-Nonce`); update Appendix F.11 first and mirror it here to avoid drift. Add `Vary: Origin, Access-Control-Request-Method, Access-Control-Request-Headers`.
- Rate limits & antifraud: per-org and per-IP thresholds; portal download caps with anomaly trip expiring active links; 429 includes rate-limit headers and `Retry-After`. Binding defaults (`api.rate_limits.web.rpm_per_org=600`, `api.rate_limits.web.rpm_per_ip=300`, `portal.download.rate_limits.user_rpm=60`, `portal.download.rate_limits.org_rpm=200`) live in [`../services/settings-registry.md Appendix A`](../services/settings.md#appendix-a-settings-key-map-traceability-index); overrides must stay within the 10-2000 RPM guardrails enforced by Settings validation.
- Idempotency TTL (binding): default 24h; reusing keys after TTL executes anew; conflicting reuse returns 409.
- CI: `spectral lint` and schema diff checks gate merges; examples validate. Appendix F holds canonical payloads.

**Acceptance:**

- Unit: `make lint-openapi` (`npx spectral lint`) enforces Spectral rules (including `openapi-version`) and shared component usage.
- Integration: `tests/e2e/test_rate_limit_headers.py::test_429_headers` runs in staging to assert rate-limit/Retry-After headers match Appendix F.11.
- Security: `scripts/security/verify_cors_headers.py` validates the CORS exposure list in Appendix F.11 and fails on regressions; OWASP ZAP smoke confirms no over-exposed headers.

Binding breadcrumbs:

| Control                    | Implementation                                                              | Test                                                            | Observability                                                    |
| -------------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------- |
| OpenAPI 3.1 enforcement    | `ops/openapi/rules/openapi-version.yaml`                                    | `make lint-openapi` (`npx spectral lint ops/openapi/**/*.yaml`) | Buildkite `lint-openapi` stage                                   |
| Rate-limit header contract | `apps/platform/api/middleware/rate_limiting.py::append_rate_limit_headers`  | `tests/e2e/test_rate_limit_headers.py::test_429_headers`        | Metric `api_rate_limit_header_miss_total`                        |
| CORS exposure policy       | `config/settings.py::CORS_EXPOSE_HEADERS` & Settings bundle `security.cors` | `scripts/security/verify_cors_headers.py`                       | CI job `security-headers` / Grafana “API Security Headers” panel |

- **Source material:** `§10`, `§10.5`, `§10.5`, `§10.8`, `§10.6`

- **Priority:** High (interfaces for downstream tooling & partners)

### 10.6 HTTP caching & range behavior (binding)

**Breadcrumbs:** Implementation `apps/platform/portal/downloads.py::ArtifactDownloadService`, Tests `tests/e2e/test_artifact_range_download.py::test_range_and_conditional_gets`, Observability Grafana “Artifact Downloads” dashboard (metric `artifact_download_range_total`).

*Purpose: Standardize safe and efficient delivery semantics for approved artifacts.*

- Preconditions: downloads require `status='APPROVED'`; token or signed URL must authorize access to the case/org.
- ETag: responses include a strong validator derived from `artifact.content_sha256` and encoded as a quoted base16 string with a `sha256:` prefix (e.g., `"sha256:0123abcd..."`). The value stays stable across full and ranged requests. Clients may use `If-None-Match` for conditional GETs (304) and `If-Range` for resumable downloads; weak validators are forbidden.
- Range requests: support `Range: bytes=...`; respond with `206 Partial Content`, include `Content-Range`, `Accept-Ranges: bytes`, and correct `Content-Length` for the segment. Full responses remain `200 OK`.
- Headers: include `Content-Disposition` with a safe filename; expose `ETag` via CORS (see §10.5). Signed URLs include short TTLs; servers reject expired or mismatched signatures.
- Caching policy: emit explicit cache directives (e.g., `Cache-Control: private, no-cache` for non-PII, `private, no-store` for PHI/HIPAA artifacts) per org policy. Prefer conditional requests with ETag over long-lived caches for PII.
- Integrity: optional segment integrity checks via store MD5/CRC when available; canonical integrity remains SHA-256 at artifact creation.
- HEAD: support `HEAD` to return metadata (ETag, length) so clients can plan range requests.
- Token enforcement: single-use signed URLs rely on `download_token` rows; fetching requires successful token consumption and verifies artifact hash/state plus current residency allowlists (deny with 403 `POLICY_BLOCK` if regions drift).
- Content metadata (binding): `artifact.content_length` stores the byte length computed at write time; release tests compare it against the object store’s metadata after every deploy to catch silent truncation.
- Contract test: staging job `tests/e2e/test_artifact_range_download.py::test_range_and_conditional_gets` performs full GET → captures the strong ETag → issues an `If-Range` request and verifies partial content → retries with `If-None-Match` expecting 304. The deploy pipeline blocks if any step fails.
- ETag invariance: the download service recomputes SHA-256 after fulfilling range requests and compares it to `artifact.content_sha256`; mismatches raise `INTEGRITY_ERROR` and quarantine the artifact.
- HIPAA cache directives: when `privacy.hipaa.enabled=true`, responses must emit `Cache-Control: private, no-store` and `Pragma: no-cache` regardless of artifact type. Synthetic monitor `synthetics/portal_hipaa_cache.yaml` toggles HIPAA mode in staging, downloads a PHI-tagged artifact, and asserts the cache headers plus 403 behavior for disabled orgs; failure blocks production deploys.

**Acceptance:**

- Unit: `tests/platform/artifacts/test_content_metadata.py::test_content_length_persisted` verifies metadata persistence and ETag helpers.

- Integration: `tests/e2e/test_artifact_range_download.py::test_range_and_conditional_gets` exercises range/conditional flows across staging object storage.

- Security: `scripts/security/verify_download_tokens.py` validates download-token expiry, residency guards, and HIPAA cache directives prior to release.

  | Binding                      | Implementation                                                                                                                | Test                                                                                     | Observability                                                                         |
  | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
  | `content_length` persistence | Implementation: Migration `apps/platform/artifacts/migrations/0023_add_content_length.py` & ORM `CaseArtifact.content_length` | Test: `tests/platform/artifacts/test_content_metadata.py::test_content_length_persisted` | Observability: Grafana “Artifact Metadata Drift” panel (alerts on mismatched lengths) |
  | Range/ETag staging test      | Implementation: `tests/e2e/test_artifact_range_download.py` (GitHub Actions `deploy-gate`)                                    | Test: `tests/e2e/test_artifact_range_download.py::test_range_and_conditional_gets`       | Observability: Buildkite deploy gate log (`range-etag-contract`)                      |

### 10.7 Error model and codes (normative)

*Purpose: Provide a consistent envelope and code semantics across services.*

- Envelope (binding):
- Envelope (binding): HTTP error payloads MUST validate against `spec/schemas/api_error.schema.json`. Runtime code in Django/FastAPI imports Pydantic models generated from that schema during the build pipeline so the schema remains the single source of truth. Servers echo the `Idempotency-Key` header (if present) in responses to aid callers with safe retries.
- HTTP mapping examples:
  - `409 CONFLICT`: `code="CONFLICT"` (idempotency mismatch, stale OCC version, job kind busy).
  - `412 PRECONDITION_FAILED`: `code="INTEGRITY_ERROR"` (hash mismatch) or `code="POLICY_BLOCK"` (portal invalidation).
  - `429 TOO_MANY_REQUESTS`: `code="RATE_LIMIT"` (rate ceilings, token budgets); include `Retry-After`, rate-limit headers per §10.5 and `details.retry_after_ms` when known.
  - `503 SERVICE_UNAVAILABLE`: `code="PROVIDER_DEGRADED"` (circuit open, dependency outage).
- Headers: always emit `X-Request-ID`; add `Retry-After`, `Deprecation`, `Sunset`, and rate-limit headers when applicable. Error payloads are included in Spectral lint checks (§10.5).

Client retry guidance (normative)

| Error code                        | Typical cause                       | Client action                                                                |
| --------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------- |
| `CONFLICT` + stale `version`      | Optimistic concurrency failure      | Re-fetch resource, apply latest state, retry with updated `expected_version` |
| `CONFLICT` + idempotency mismatch | Replayed key with different payload | Generate a new `Idempotency-Key`; ensure request body matches original       |
| `RATE_LIMIT`                      | Per-org/IP quota exceeded           | Honor `Retry-After` header; exponential backoff                              |
| `POLICY_BLOCK`                    | Guardian/portal policy violation    | Surface message to operator; resolve underlying policy issue before retrying |
| `QUARANTINED`                     | Guardian rejected artifact          | Present remediation reasons; require manual fix                              |
| `INTEGRITY_ERROR`                 | Hash/ETag mismatch                  | Re-upload/file new hash; do not retry blindly                                |
| `AUTH_CLOCK_SKEW` (401)           | Request timestamp outside ±120 s    | Re-sync clock; retry with corrected time                                     |

### 10.8 SSE event schema & sync snapshot (normative)

*Purpose: Define canonical SSE events and replay behavior.*

- Event types: `job.accepted`, `job.update`, `job.running`, `job.blocked`, `job.quarantined`, `job.completed`, `job.canceling`, `job.canceled`, `artifact.status`, `qa.notes`, `provider.health`, `portal_link_invalidated`, `settings.activated`, plus lifecycle events emitted for the status model (`OBJECT.STORED`, `OBJECT.PROCESSING.START|END`, `OBJECT.FAILED`, `OBJECT.PENDING_JUDGMENT`, `GUARDIAN.JUDGMENT.PASS|WARN|BLOCK|WAIVED`, `OBJECT.CLEARED_FOR_USE`, `OBJECT.OPERATOR_PREP`, `REVIEW.REQUESTED`, `REVIEW.QUEUED`, `REVIEW.SKIPPED`, `REVIEW.APPROVED`, `REVIEW.CHANGES_REQUESTED`, `REVIEW.QUARANTINED`, `SIGNATURE.APPLIED`, `DELIVERABLE.RELEASED`, `DELIVERABLE.REVOKED`, `OBJECT.ARCHIVED`). `job.accepted` emits once per enqueue, `job.running` and `job.completed` bracket successful execution, and `job.blocked`/`job.quarantined` surface policy holds (FinOps, Guardian) that require human action before resumption.
- Every payload includes `schema_version` (string, currently `"1"`) and `emitted_at` (RFC3339 with timezone) so clients can branch logic during future revisions without breaking older deployments or relying on local clocks.
- Envelope: `id` (monotonic), `event`, `data` (JSON), `retry` (ms). `data` for snapshot payloads includes `watermark_ts` to indicate the newest event timestamp included. Requests to `/api/v1/jobs/{id}/events` and `/api/v1/cases/{id}/events` MUST send `If-None-Match` with the caller’s cached digest (initially `*`). Servers respond with `ETag: sse:{scope}:{digest_sha256}` so reconnecting clients can prove they have processed the latest PolicyContext and artifact manifests; mismatched digests trigger a synthetic snapshot replay before live tailing. The envelope and payloads validate against `spec/schemas/sse/event_envelope.schema.json`; SSE producers deserialize generated Pydantic models before emit. Schema constraints encode `maxLength`/`maxItems` limits (e.g., snapshot ≤ 500 events, messages ≤ 2 KiB) so the 8 KiB payload budget is enforced mechanically. `id` echoes in `Last-Event-ID`.
- Payload hints: `data.meta` may include `{phase, percent, next_action, badges[]}` to align with UI progress widgets (e.g., `phase="Judgment"`, `badges=["WARN:PII detector"]`).
- Sequencing: IDs are monotonic per stream (`sse:case:{case_id}` and `sse:job:{job_id}`) and minted via Redis `INCR`, ensuring ordered delivery across multiple web pods without requiring cross-stream ordering.
- Sync snapshot: if `Last-Event-ID` predates the 15-minute/500-event replay window (whichever comes first), the server emits a snapshot (RLS‑scoped) containing the last 500 events and `watermark_ts` before tailing live updates.
- Delivery: at‑least‑once; clients de‑dupe via `id`. Snapshots include a bounded window and `watermark_ts` so consumers know when they are live. Individual events are capped at 8 KiB payloads (post-JSON encoding) and Redis stream memory budgets target ≤ 256 MiB per environment; SREs size `stream.maxlen` accordingly.
- Operational SLOs: 95th percentile client-perceived delivery latency (`sse_client_delivery_lag_seconds`) stays \< 2 s and 99th percentile \< 5 s; alert `alert_sse_delivery_lag_high` pages when either threshold is exceeded for five consecutive minutes.
- Replay guardrails: snapshot builds MUST complete within 2 s and stay \< 5 MiB serialized (`sse_snapshot_build_duration_seconds`, `sse_snapshot_size_bytes`). Alert `alert_sse_snapshot_regression` fires and blocks deploys when limits are exceeded.
- Security: events enforced by RLS; tokens bound to org/case; portal receives a subset.
- Settings Service emits identical payloads via SSE (`settings.activated`) and Redis `settings.changed` events so workers and browser clients observe the same activation metadata.
- Retention: SSE replay buffers keep 24 hours of events; reconnects beyond that window receive a snapshot plus the latest live tail.
- Load testing: quarterly chaos runs (`scripts/sse/load_test.py`) fan 5k concurrent tails at 1 Hz updates to validate Redis memory ceilings and event-size caps; results feed App.L baselines.
- Source material: `§10.8`, `§10.8`

**Acceptance:**

- Unit: `tests/platform/realtime/test_sse_payloads.py::test_event_schema` validates canonical event envelopes and size limits.
- Integration: `tests/e2e/test_sse_reconnect.py::test_last_event_snapshot` asserts Last-Event-ID replay + snapshot delivery in staging.
- Security: `tests/e2e/test_sse_token_binding.py::test_disconnect_on_org_switch` confirms token expiry/org switch closes connections and emits audit events.

Binding breadcrumbs:

| Control                | Implementation                                          | Test                                                                 | Observability                                                      |
| ---------------------- | ------------------------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------ |
| SSE stream contract    | `apps/platform/realtime/sse.py::StreamPublisher`        | `tests/platform/realtime/test_sse_payloads.py::test_event_schema`    | Metric `sse_payload_size_bytes` / Grafana “Realtime Streams” panel |
| Snapshot replay        | `apps/platform/realtime/sse.py::snapshot_payload`       | `tests/e2e/test_sse_reconnect.py::test_last_event_snapshot`          | Metric `sse_snapshot_gap_seconds`                                  |
| Token-bound disconnect | `apps/platform/realtime/auth.py::enforce_token_binding` | `tests/e2e/test_sse_token_binding.py::test_disconnect_on_org_switch` | Audit event `SSE_DISCONNECT_TOKEN_MISMATCH`                        |

Payloads (illustrative)

| Event                   | data fields                                                                                        | Notes                                                                                                                                                                                                                    |
| ----------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| job.accepted            | `{ schema_version, emitted_at, job_id, case_id, org_id }`                                          | Emitted once when a queued job is accepted onto a worker.                                                                                                                                                                |
| job.running             | `{ schema_version, emitted_at, job_id, case_id, org_id, phase }`                                   | Signifies active execution; `phase` mirrors `provider_progress.phase`.                                                                                                                                                   |
| job.update              | `{ schema_version, emitted_at, job_id, case_id, org_id, status, progress?, warning?, error? }`     | `status ∈ {PENDING, RUNNING, PAUSED, PAUSED_AWAITING_PROVIDER, PAUSED_AWAITING_BUDGET, CANCELING, FAILED, COMPLETED, CANCELED}`                                                                                          |
| job.blocked             | `{ schema_version, emitted_at, job_id, case_id, org_id, reason }`                                  | Signals policy or budget block; clients surface remediation guidance.                                                                                                                                                    |
| job.quarantined         | `{ schema_version, emitted_at, job_id, case_id, org_id, reason }`                                  | Guardian-enforced quarantine; operators must resubmit with fixes/waivers.                                                                                                                                                |
| job.completed           | `{ schema_version, emitted_at, job_id, case_id, org_id }`                                          | Successful terminal state; emitted before downstream artifact.status updates.                                                                                                                                            |
| job.canceling           | `{ schema_version, emitted_at, job_id, case_id, org_id, actor_id, reason }`                        | Emitted once per cancel request; clients stop polling progress UI.                                                                                                                                                       |
| job.canceled            | `{ schema_version, emitted_at, job_id, case_id, org_id, actor_id, reason, provider_outcome }`      | Emitted after providers acknowledge abort; pairs with AR `JOB_CANCELLATION_REPORT`.                                                                                                                                      |
| artifact.status         | `{ schema_version, emitted_at, artifact_id, case_id, org_id, type, status, previous_status? }`     | `status ∈ {STORED, PROCESSING, FAILED, PENDING_JUDGMENT, CLEARED_FOR_USE, OPERATOR_PREP, APPROVAL_REQUESTED, QUEUED_FOR_REVIEW, CHANGES_REQUESTED, QUARANTINED, APPROVED, SIGNED, RELEASED, REVOKED, ARCHIVED, DELETED}` |
| qa.notes                | `{ schema_version, emitted_at, job_id?, artifact_id?, case_id, notes:[{level, msg, emitted_at}] }` | Levels: INFO                                                                                                                                                                                                             |
| portal_link_invalidated | `{ schema_version, emitted_at, artifact_id, case_id, reason }`                                     | Portal consumes to revoke stale links                                                                                                                                                                                    |
| settings.activated      | `{ schema_version, emitted_at, scope, org_id?, case_id?, bundle_id, version_id }`                  | Triggers cache invalidation on clients                                                                                                                                                                                   |

- Canonical payloads: App.U.4 contains the reference JSON for `job.update`, `artifact.status`, `portal_link_invalidated`, and snapshot bootstrap messages. Examples are generated from the shared schema test fixtures so they stay aligned with validation logic and SSE contracts.

### 10.9 Rate limits & antifraud controls

*Purpose: Prevent abusive usage while providing clear backoff guidance.*

- Global throttles: `api.rate_limits.web.rpm_per_org`, `api.rate_limits.web.rpm_per_ip`; 429 responses include `Retry-After`, `X-RateLimit-*`, and support exponential backoff guidance.
- Portal downloads: per-user/org caps (`portal.download.rate_limits.*`) with anomaly detection; exceeding triggers `portal_link_invalidated` and optional step-up MFA.
- SSE/Channels: server disconnects on org switch or token expiry; reconnects honor backoff (`retry` field), enforce token binding, and must respect the 8 KiB per-event payload cap defined in §10.8.
- Fraud signals: repeated 4xx from a single IP escalate to security incident workflow; rate-limit spikes logged via `API_RATE_ALERT` audit events.
- Source material: `§10.9`, `§10.8`

### 10.10 Timezone & clock policy

*Purpose: Guarantee consistent timestamps across APIs, UI, and downstream systems.*

- **Storage:** All persisted timestamps use UTC (`TIMESTAMP WITH TIME ZONE`) with millisecond precision; APIs return ISO 8601 UTC (`Z`) strings. Case/portal locale rendering converts at presentation time only.
- **Client hints:** Requests may include `X-Client-Timezone` for UX personalization; server never trusts it for persistence or policy enforcement.
- **Clock hygiene:** Services rely on chrony/NTP with ±100 ms drift budget (aligned with TSA requirements in §3.2). Health checks fail closed if drift exceeds 250 ms; alerts page SRE.
- **UI controls:** Date pickers default to case locale; portal displays timezone label on deliverables and approvals. Manual edits capture both UTC timestamp and operator-local zone for audit clarity.
- **Backfills/migrations:** Jobs ensure time arithmetic uses timezone-aware APIs; tests verify `created_at`/`decided_at` fields remain UTC during bulk updates.

### 10.11 Localization & Policy Engine APIs

*Purpose: Defer to the dedicated LPE API specification.*

See `../services/lp-engine.md §4` for endpoint definitions, SDK responsibilities, legacy shim guidance, and error models. This section intentionally references that document to avoid divergence.

### 10.12 Assistant capability & settings APIs

*Purpose: Give staff and portal clients a consistent interface to discover assistant availability, rate limits, and disclaimers without exposing raw conversations.*

- `GET /api/v1/chat/assistants` (audience-scoped)
  - Returns metadata for assistants the caller may invoke. Response envelope includes `assistants[]`, each with `{id, audience, enabled, capabilities, rate_limits, moderation, guardian, disclaimer}`.
  - `capabilities` captures retrieval sources (`transcript|analysis|compose|portal_messages`), supported actions (`summarize`, `suggest_tasks`, `link_to_edit`, `answer_questions`), citation policy, and HIPAA posture.
  - `rate_limits` mirrors Settings (`chat.*`) and surfaces current ceilings; UI uses it to render limit pickers and warnings.
  - `moderation` flags whether prompt/response filters are enforced and lists supported reason codes (documentation derived from §11.11).
  - `guardian` includes `state` (`ok|quarantined|disabled`) plus `last_reviewed_at` so operators know when Guardian last sampled the assistant.
  - `disclaimer` references localization keys and acknowledgement requirements (`must_acknowledge=true` for client assistants).
  - Responses set `Cache-Control: private, max-age=120` and `ETag`; SSE event `chat.assistant.updated` carries the new ETag so clients refresh lazily.
- `GET /api/v1/chat/assistants/{assistant_id}/settings`
  - Provides localized disclaimers, enabled locales, and effective Settings values (rate limits, HIPAA allowances) after policy evaluation. Portal callers receive only fields marked `portal_visible=true`.
  - Includes `rate_limit_status` so the UI can show remaining RPM/token budget without creating a session.
- `GET /api/v1/chat/rate-limit-status`
  - Optional helper returning `{assistant_id, remaining, resets_at}` per active assistant. Enforced via the same role checks as the assistants endpoint; staff may query for multiple cases by passing `case_id`.
- `GET /api/v1/chat/manifest/{session_id}`
  - Fetches the manifest for a completed session (metadata, Guardian judgment, citations) without returning message content. Requires artifact read permission and `status='APPROVED'`. Intended for UI review panels and auditors.

Contract requirements (binding)

- Authentication mirror artifact APIs: staff endpoints require `org_operator` (or higher); client endpoints require `org_client` membership for the case. All responses log `CHAT_ASSISTANT_API` audit events with `{assistant_id, audience, org_id, case_id?}`.
- Chat session creation/execution endpoints remain documented in the application API references; this section focuses on capability discovery so frontends stay aligned with policy changes.
- OpenAPI: `ops/openapi/chat_assistants.yaml` defines shared schemas (`ChatAssistant`, `ChatAssistantCapabilities`, `ChatAssistantRateLimits`, `ChatAssistantDisclaimer`). Spectral rules enforce example coverage and forbid exposing conversation payloads.
- Errors: `403` with `code="CHAT_DISABLED"` when assistants are toggled off; `404` when an assistant ID is unknown in the caller’s scope; `409` for stale ETags on `If-Match` guarded settings fetches.
- Tests: `tests/e2e/test_chat_api.py` covers role requirements, ETag/If-Match behavior, guardian-state propagation, and ensures rate-limit status mirrors Settings. Load tests in `synthetics/chat_assistant_status.yaml` verify latency stays \<200 ms P95.
- Observability: metrics `chat_assistant_metadata_requests_total{audience}`, `chat_rate_limit_status_requests_total`, and `chat_assistant_etag_miss_total` feed the “Assistant API” dashboard; anomalies page Platform SRE.

______________________________________________________________________

## 11) Frontend & client experience

See [`../services/web-app.md`](../services/web-app.md) for the authoritative specification of the staff workspace, reviewer consoles, and client portal. Platform components depend on the following integration points:

- **Staff workspace & approvals:** Compose/Analyze outputs, Guardian verdicts, and job watchdog signals feed the operator UI; reviews must surface SSE status, backlog metrics, and RB-JOB-WATCHDOG links.
- **Client portal delivery:** Download tokens, invalidation flows, phishing reporting, and secure portal messaging reuse notifications service APIs (`portal.link_invalidated`, signed URLs, abuse logging) while enforcing RLS and masking policies.
- **Accessibility & localization:** LP Engine bundles (`i18n.*`) and accessibility evidence drive UI releases; pseudolocale checks and axe snapshots remain release gates referenced in the web-app spec.
- **Manual/agent edits & assembly:** Edit manifests, dual-approval rules, and document assembly pipelines coordinate with Guardian and Digital Signer before artifacts reach the portal.
- **Conversational assistants:** Staff and client assistants use the shared capability APIs (§10.12), respect LLM registry safety controls, and emit manifests for audit/Guardian review.

Notifications, Guardian, Settings, and LP Engine service docs enumerate the supporting keys and runbooks.

______________________________________________________________________

## 12) Observability, reliability & operations

- Glossary: Appendix I includes observability metrics, watchdog terminology, and quota concepts cited in §12.

### 12.1 Telemetry stack (logs, metrics, traces)

*Purpose: Ensure platform-wide visibility, SLOs, and actionable alerts.*

- Structured logs: `ts, trace_id, span_id, service, level, message, correlation_id, org_id, case_id, user_id, job_id, artifact_id, route, action, result, latency_ms, ip_prefix, ua_hash, settings_bundle_id` with PII redaction.

- Canonical schema (binding): every log event serializes to newline-delimited JSON validating against `spec/schemas/log_record.schema.json` (`log_schema@1`). Example:

  ```json
  {
    "ts":"2025-10-20T03:12:45.183Z",
    "level":"INFO",
    "service":"platform-web",
    "src":"apps.platform.jobs:update_status:142",
    "message":"job status update",
    "trace_id":"4f4c9f7d09e141d8be6d1f8d0d6d88e4",
    "span_id":"5f9c48de71b2a36d",
    "correlation_id":"req-6d4be3e4",
    "org_id":"11111111-1111-1111-1111-111111111111",
    "case_id":"22222222-2222-2222-2222-222222222222",
    "job_id":"33333333-3333-3333-3333-333333333333",
    "action":"JOB_PROGRESS",
    "result":"ok",
    "latency_ms":142,
    "stream":"stdout",
    "extras":{"queue":"compose-high"}
  }
  ```

- Judgment telemetry (binding): Guardian, QA automation, and human reviewers emit a unified event envelope (`spec/schemas/judgment_event.schema.json`) so telemetry, analytics, and audit surfaces align.

  ```json
  {
    "type": "QA_ASSESSMENT",
    "event_id": "b0dd2f2b-0b6e-4a4e-a429-0640b6a0e6d9",
    "case_id": "22222222-2222-2222-2222-222222222222",
    "artifact_id": "33333333-3333-3333-3333-333333333333",
    "job_id": "44444444-4444-4444-4444-444444444444",
    "score": 0.82,
    "judgment": "WARN",
    "reason_codes": ["FACT_MISMATCH", "MISSING_CITATION"],
    "actor_type": "AUTOMATED_QA",
    "qa_model_id": "qa-v5-canadacentral",
    "qa_confidence_score": 0.82,
    "guardian_judgment_id": null,
    "created_at": "2025-10-20T03:12:45.183Z",
    "trace_id": "4f4c9f7d09e141d8be6d1f8d0d6d88e4"
  }
  ```

- Emission & formatting (binding): All services emit newline-delimited JSON to stdout for levels `DEBUG` through `ERROR`; only `ERROR` and higher duplicate to stderr so container runtimes and `kubectl logs`/`docker logs` tail a single canonical stream. The `src` field records the compact source location as `package.module:function:line` (max 80 characters) and extended diagnostics belong in structured keys under `extras`. Messages must remain ≤ 160 characters—richer context should be captured in dedicated fields to avoid terminal noise. Local pretty printing is opt-in via `LOG_PRETTY=1`, keeping production streams strict JSON with no ANSI colour or stacktrace spam.

- Forbidden fields (binding): log scrubber removes `Authorization`, `Cookie`, `Set-Cookie`, `X-Request-Signature`, `X-Signature-Key-Id`, raw signed URLs, and any header matching `*-Token` before serialization. CI test `tests/logging/test_redaction.py::test_forbidden_headers_masked` asserts the mask list, and runtime metrics `logging_redaction_dropped_total` surface any attempt to log a banned key.

- Metrics: queue depth, job durations, review-service latency/throughput (`guardian_judgment_latency_seconds`, `guardian_cleared_ratio`, `guardian_pending_total`, `guardian_pending_oldest_seconds`, `guardian_submission_timeout_total`), Signer verify latency (including `sign_verify_status_total`, `ocsp_latency_seconds`, `ocsp_staple_age_seconds`, `tsa_latency_seconds`, `tsa_time_drift_seconds`), LLM health/circuit state, delivery rates, integrity incidents (`integrity_scan_queue_depth`, `integrity_quarantine_total`), review queue health (`review_queue_backlog_total`, `review_queue_oldest_seconds`), false-positive sampling (`guardian_quarantine_false_positive_total`), job lifecycle signals (`job_stalled_total`, `job_watchdog_warning_total`, `job_watchdog_timeout_total`, `job_cancellation_total`), watchdog runner health (`watchdog_runner_lag_seconds`, `watchdog_runner_missed_total`), upload scanning (`upload_scan_duration_seconds`, `upload_scan_infected_total`, `upload_scan_error_total`), Reference Manager dashboards per `../services/reference-manager.md §5.1`, SSE reconnect rate, `artifacts_cleared_total`, `artifacts_approved_total`, `time_to_approval_seconds`. LPE runtime metrics live in `../services/lp-engine.md §5`. All Prometheus metrics use seconds for duration histograms and `_total` counters for events; legacy `*_ms` signals are deprecated and scheduled for removal in v7 GA (§12.6).

- FinOps metrics: `llm_cost_estimate_total{org, case, job, model}`, `finops_cost_per_case_usd{org, case}`, `finops_cost_per_org_usd{org, month}`, `delivery_events_total{org, channel, status}`, `finops_mom_regression_flag{org}`.

- Privacy/Governance: `residency_block_total`, `dpia_records_total{status}`, `ropa_records_total`, `entitlement_snapshots_total`, `policy_unsafe_activations_blocked_total`.

- Advisory locks: `udlock_locks_held{scope, kind}`, `udlock_lock_age_seconds_p95{scope, kind}`, `udlock_watchdog_stale_total{action}`, `udlock_registry_gc_total`.

- Traces correlate web → workers → Guardian/Signer/LLM; ingress injects `X-Request-ID` on missing. API SLOs: Availability ≥ 99.9%/30d; P95: reads 250 ms, writes 500 ms; Portal TTFB ≤ 400 ms in-region, calculated over rolling 5-minute windows.

- Immutable audit sink + logging immutability: dual-stream `audit_event` to DB + WORM storage and, when `logging.immutable_sink.enabled=true`, mirror structured logs to an immutable store. Hourly `AUDIT_SEAL` artifacts with rolling Merkle roots validate chain continuity. Metrics `audit_worm_lag_seconds` and `audit_seal_errors_total` back alerts; if verification fails for more than one interval, the release pipeline blocks new approvals and portal deliveries until the seal returns to green and Security signs off.

#### 12.1.1 Centralized logging architecture (binding)

**Breadcrumbs:** Implementation `infra/logging/helm/values.yaml::logging`, Tests `tests/logging/test_registration.py::test_service_template_registered`, Observability Grafana “Logging Pipeline” dashboard (metric `logging_queue_depth`).

*Purpose: Lay out the logging pipeline components and data flow.*

- Services emit OpenTelemetry logs to a sidecar collector (`otel-collector`) which fans out to Fluent Bit daemons. Fluent Bit ships into the Observability Fabric (Kafka → Elasticsearch), writing indices named `logs.<env>.<service>-YYYY.MM.DD`.
- Collectors persist local queues for at least 12 hours; `logging_queue_depth` and `logging_spool_utilization_pct` metrics guard against drops. Back-pressure alerts trigger before buffers exceed 80% utilization.
- Records carry `tenant_hash` (HMAC of `org_id`) to drive per-tenant filters. Index lifecycle policies roll hot indices to warm/cold tiers and archive to WORM storage when cold retention lapses.
- New services register via `ops/logging/register_service.py` so CI can enforce schema compliance and index templates.
- Immutable pipeline: when `logging.immutable_sink.enabled=true`, collectors fork a second stream to the immutable log sink (WORM object store) with the same canonical schema so audit seals can cover operational logs as well as audit events.

#### 12.1.2 Log access control & auditing (binding)

**Breadcrumbs:** Implementation `apps/platform/logging/access.py::authorize_log_access`, Tests `tests/logging/test_access_control.py::test_requires_step_up`, Observability Audit event `LOG_QUERY` aggregated in Grafana “Log Access” panel.

*Purpose: State who can access logs and how access is audited.*

- Access roles: `observability.reader` (read-only dashboards), `observability.engineer` (debug queries, pipeline tuning), and `observability.auditor` (auditor-only views). Roles map through Settings `logging.access.roles[]` and require Security + Platform approval to change.
- Interactive queries enforce WebAuthn step-up and justification prompts; every search emits `LOG_QUERY` audit events `{actor_id, scopes, query_hash, purpose, rows_returned}`.
- Bulk exports need dual approval, generate `LOG_EXPORT` artifacts with SHA-256 manifests, and respect per-org daily export quotas.

#### 12.1.3 Data minimization & banned fields (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/logging/redaction.py::scrub_forbidden_fields`, Tests `tests/logging/test_neverlog_fuzz.py::test_scrubber_blocks_forbidden_tokens`, Observability Grafana “Log Redaction” dashboard (metric `logging_neverlog_violation_total`).

*Purpose: Enumerate log scrubbing rules and prohibited fields.*

- The “never log” list extends the scrubber to bearer/API/refresh tokens, session cookies, raw request/response bodies, entire transcript or exhibit text, PHI unless HIPAA waiver enabled, full customer email addresses/phone numbers, secrets/keys, signed URLs, and Guardian waiver IDs. Canonical HIPAA identifiers blocked from logs include (non-exhaustive) `patient_name`, `patient_dob`, `medical_record_number`, `diagnosis_codes`, `insurance_member_id`, and `provider_npi`. Violations increment `logging_neverlog_violation_total`; in production they raise Sev-1 incidents. Property-based test `tests/logging/test_neverlog_fuzz.py::test_scrubber_blocks_forbidden_tokens` fuzzes representative payloads to ensure the denylist is enforced.
- Commit checklist: structured logging only, no f-string interpolation, message templates validated with `scripts/logging/check_neverlog.py`. Large payloads move to artifacts referenced by ID (`log_ref_id`) rather than inline content.
- HIPAA mode enforces collector-side redaction; attempts to emit PHI trigger automatic portal invalidation and Guardian quarantine of dependent artifacts.

#### 12.1.4 Trace correlation & sampling (binding)

**Breadcrumbs:** Implementation `apps/platform/logging/tracing.py::inject_trace_context`, Tests `tests/logging/test_trace_correlation.py::test_traceparent_propagation`, Observability Grafana “Trace Correlation” dashboard (metric `trace_sampling_rate`).

*Purpose: Define trace sampling strategy and correlation requirements.*

- Logs, traces, and metrics share `trace_id` and `span_id` using W3C Trace Context propagated via HTTP (`traceparent`) and Celery headers. Default sampling: 15% baseline, 100% for error spans, 100% for Guardian/Signer spans; overrides require SRE approval and Settings activation.
- `correlation_id` mirrors `X-Request-ID` for web/API traffic and `job_id` for worker spans so operators can drill from case timelines to traces.
- Trace retention: 72 hours hot storage; dashboards alert when sampled error rate deviates by >5% from aggregate error rate.

#### 12.1.5 Client & portal logging posture

*Purpose: Describe logging expectations for client-facing surfaces.*

- Browser telemetry captures anonymized WebVitals (LCP, FID, CLS) and `error_code` aggregates only; no raw request payloads or user-entered text is shipped. Portal telemetry produces `CLIENT_TELEMETRY` artifacts gated by Guardian before reviewers can inspect.
- Console log shipping stays disabled in production; temporary incident capture requires ticket references and must be removed within 24 hours.

#### 12.1.6 Log volume & cost controls (binding)

**Breadcrumbs:** Implementation `apps/platform/logging/cost_controller.py::enforce_budget`, Tests `tests/logging/test_cost_controls.py::test_budget_enforcement`, Observability Grafana “Logging Cost” panel (metric `logging_volume_budget_violation_total`).

*Purpose: Capture quotas, budgets, and guardrails controlling log volume.*

- Settings `logging.cost.daily_budget_mb_per_service` and `logging.cost.alert_threshold_pct` enforce daily budgets; collectors raise `LOG_VOLUME_BUDGET` alerts and dynamically increase sampling when projected volume exceeds 80% of budget.

- Verbosity toggles: production defaults to `INFO`, non-prod to `DEBUG`; overrides live in `logging.level.overrides[service]` and surface via `/healthz/log-level`. Unauthorized runtime changes raise audit events and revert to the stored setting.

- Log retention & sampling:

  - Staff/API request logs retained 90 days hot, 365 days cold (object storage) with 10 % sampling for successful 2xx responses; 4xx/5xx retained in full with sensitive fields masked via `logging.redaction.enabled`.
  - LLM evidence logs retained 365 days with `train_on_data=false` confirmation; HIPAA mode reduces retention to 180 days and forces excerpt suppression (§8.2).
  - Masking tests run in CI (`tests/logging/test_redaction.py`) to prevent PII leakage; failures block merges (§13.7).

#### 12.1.7 Stdout ergonomics & operator experience (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/logging/jsonlog.py::StructuredJSONFormatter`, Tests `tests/logging/test_stdout_format.py::test_json_stdout`, Observability CI job “logging-format-lint” with alert `logging_plaintext_detected_total`.

*Purpose: Specify stdout formatting that keeps logs machine- and human-friendly.*

- Container images default `LOG_STDOUT_FORMAT=json` and rely solely on process stdout/stderr rather than file sinks so Kubernetes, systemd, and serverless runtimes ingest logs without extra sidecars. Setting `LOG_STDOUT_FORMAT=pretty` is allowed only for local development and surfaces annotated (but still redacted) human-friendly output without changing the structured payload.
- Stack traces are limited to the first five frames in the top-level `stack` field, with the full trace stored under `extras.stack_full`; this keeps terminal tails compact while preserving deep diagnostics in Elasticsearch/OpenSearch.
- Health probes and CLI utilities must emit at most one structured line per invocation—multi-line `print` statements or ad-hoc `repr(...)` dumps are prohibited. Library loggers (Python `logging`, Django, Celery) are wrapped to route through the structured adapter and to honor the stdout/stderr split above; teams must not call `print()` or write arbitrary bytes to stdout.

### 12.2 Runbooks and synthetic monitors

*Purpose: Ensure operational readiness and quick diagnosis.*

- Synthetic checks: `/readyz` with RLS enforcement, settings cache validation, NTP drift. Guardian synthetic job ensures policy enforcement; Signer synthetic verifies TSA reachability.
- Logging pipeline synthetic monitors assert `logging_ingest_lag_seconds < 30s`, `logging_drop_rate_pct = 0`, and index freshness; alerts route to `../ops/runbooks/index.md (RB-LOG-007)`.
- Runbooks stored in ops repo (`../ops/runbooks/index.md`) cover Guardian quarantine handling, PgBouncer pooling misconfig, artifact integrity mismatch, SSE replay issues, and logging pipeline recovery.
- Automation: watchdog tasks auto-quarantine artifacts with integrity failures, restart pods on failed health checks, and rotate settings caches when invalidation fails. The `watchdog-runner` Celery beat process emits heartbeats (`watchdog_runner_lag_seconds`) and raises PagerDuty incidents if it misses two consecutive intervals; Kubernetes liveness/readiness probes restart the runner on failure.
- Fail-closed defaults: if Guardian is unavailable, artifacts remain `PENDING_JUDGMENT`; if Settings is unavailable, new jobs block on snapshot fetch while running jobs continue with embedded snapshots. These scenarios have dedicated alerts and runbooks in [../ops/runbooks/index.md](../ops/runbooks/index.md) and `../ops/runbooks/index.md`.

### 12.3 Incident response workflows & escalation paths

*Purpose: Define how the team reacts to outages or security events.*

- Incident severity levels with defined on-call rotations (Engineering, Security, Product). Playbooks for RBAC breaches, data residency violations, Guardian outages.
- Post-incident reviews required within 48h; actions tracked in ops backlog. Metrics `incident_count_total`, `mttr_minutes`, and `logging_incident_total`.
- Communication templates for customer notifications, regulators, and internal leadership included in `../ops/runbooks/index.md`; latest redlines stored as `INCIDENT_TEMPLATE` artifacts covering PII disclosure, residency breach, and major outage scenarios.
- Logging ingestion incidents (dropped events or ingest lag > 2 minutes) automatically raise Sev-2, reference RB-LOG-007, and block prod deploys until the pipeline stabilizes for two consecutive collection intervals.
- Upload scanning outages or sustained `upload_scan_error_total` spikes trigger security incidents with [Runbook RB-UPLOAD-SCAN](../ops/runbooks/index.md#rb-upload-scan); uploads remain disabled (`uploads.enabled=false`) until the pipeline clears and signatures are verified current.

### 12.4 Backup, DR objectives, and failover drills

*Purpose: Maintain data durability and disaster preparedness.*

- Postgres: daily full snapshots + continuous WAL shipping; target RPO ≤ 15 minutes, RTO ≤ 1 hour. Quarterly restore drills documented.
- Object storage: versioning + lifecycle rules; deletion requires dual confirmation. Immutable audit sinks operate under WORM retention policies.
- Redis: persistence optional; rely on recomputation for queues. For critical caches, use managed Redis with cross-zone replicas.
- DR exercises simulate region failure; cross-region read replicas considered once residency waivers approved. Settings and Guardian services replicate configuration backups.
- Region failover playbook (`../ops/runbooks/index.md (RB-DR-REGION)`): warm standby clusters remain idle but patched, with secrets/Settings snapshots synced hourly. On a primary-region outage the sequence is (1) freeze new job intake, (2) promote the standby Postgres instance with latest WAL, (3) swap object storage endpoints using pre-provisioned secondary containers, (4) update Azure Front Door/DNS records (TTL ≤ 60 seconds) to point to the secondary ingress, (5) run smoke tests (`ops/dr/run_region_cutover.py`) before re-opening job intake. Residency waivers govern whether an org may fail into the paired region; orgs without waivers stay paused until the primary returns.
- After action: once the primary recovers, traffic is rolled back via blue/green cutover, delta data is validated (checksum + manifest diff), and any DSAR/erasure entries executed during the failover are replayed to ensure consistency.
- Diagram: see `overview/tdd/diagrams/dr-region-failover-v1.mmd` for the runbook flow.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/mermaid/overview/tdd/diagrams/dr-region-failover-v1.png" alt="Region failover runbook">
  <figcaption style="font-size: 0.9em; color: #555;">Region failover runbook</figcaption>
</figure>

### 12.5 Capacity planning, autoscaling, and performance budgets

*Purpose: Keep services within latency/cost budgets as usage grows.*

- Autoscaling policies: HPAs for web/channels (CPU + request latency), workers (queue depth), Guardian, Compose, and Signer tiers (p95 latency). Each deployment keeps `minReplicas=2`, `maxReplicas=10`, and targets 70 % CPU unless a service-specific metric overrides it (for example, review-service latency-based scaling). Compose lanes scale independently from Guardian so summarization surges never starve policy enforcement; KEDA bindings monitor queue depth per lane to add burst capacity without violating residency budgets.
- Capacity reviews quarterly: evaluate job volume, LLM spend, storage growth. Provide forecasts to FinOps (link to §12.9).
- Performance budgets tracked via dashboards: upload finalize ≤ 5s, SSE lag P95 \< 2s (P99 \< 5s), LLM lane runtime budgets (5-15 minutes per lane depending on complexity).
- Benchmark snapshots in App.L capture the latest measured baselines feeding these budgets; deviations trigger escalation before release.

#### 12.5.1 Failure taxonomy & resilience (binding)

**Breadcrumbs:** Implementation `apps/platform/operations/watchdogs.py::classify_failure`, Tests `tests/platform/operations/test_failure_taxonomy.py::test_failure_mapping`, Observability Grafana “Resilience & Watchdogs” dashboard (metric `job_watchdog_timeout_total`).

*Purpose: Define platform-wide recovery behavior and safety nets.*

- Classes and remedies:

  - `TRANSIENT` (429/5xx/timeouts): exponential backoff + jitter; respect `Retry-After`; bounded attempts. Trip per-model/provider circuit on threshold; half-open probes every 60s.
  - `POLICY` (forbidden/region): no auto-retry; Guardian quarantine when applicable; actionable errors surfaced.
  - `INPUT` (validation/media): no auto-retry; clear user-facing error; link to docs.
  - `INTEGRITY` (hash mismatch): block pipeline; quarantine; require resubmit; audit `ARTIFACT_INTEGRITY_MISMATCH`.
  - `CONCURRENCY` (OCC/locks): short jittered retries; escalate after N attempts; ensure OCC versions in APIs.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/mermaid/overview/tdd/diagrams/error-flows-v1.png" alt="Error handling taxonomy">
  <figcaption style="font-size: 0.9em; color: #555;">Error handling taxonomy</figcaption>
</figure>

- Circuits and watchdogs:

  - LLM circuits: OPEN/HALF-OPEN/CLOSED; metrics `llm_circuit_state`, reason codes (`PRIMARY_DEGRADED`, `RATE_LIMIT`). Runbook [RB-LLM-003](../ops/runbooks/index.md#rb-llm-003).
  - Advisory lock watchdog: metrics `udlock_watchdog_stale_total`, `udlock_lock_age_seconds_p95`; defaults `udlock.max_session_hold_seconds=300`, `udlock.heartbeat.interval_seconds=5`. Runbook [RB-LOCK-006](../ops/runbooks/index.md#rb-lock-006). `kill_stale=false` in prod; remediation flows through the operator-only endpoint `POST /ops/v1/udlock/{scope}/{key}/mark` which tags the holder, adds trace attribute `lock.triage=manual_review`, and (when explicitly requested) issues `pg_terminate_backend` after human confirmation.
  - Job progress watchdog: metrics `job_watchdog_warning_total`, `job_watchdog_timeout_total`; thresholds driven by `jobs.watchdog.*` settings. Runbook [RB-JOB-WATCHDOG](../ops/runbooks/index.md#rb-job-watchdog) guides remediation.

- Queues and DLQ:

  - Outbox pattern for notifications with retries/backoff; poison messages routed to DLQ with capped replays and operator alerts.

- Integrity scan DLQ: dead-letter queue `q.integrity.deadletter` captures items exceeding retry budget (`last_error`, `attempts`, `cause`). DLQ processing emits on-call alerts and requires manual triage per `../ops/runbooks/index.md` runbook.

- Downstream propagation: when a source artifact is quarantined for integrity mismatch, workers walk `manifest.source_artifacts[]` and apply `integrity.downstream_action ∈ {mark_stale, quarantine}` to dependents so UI surfaces NEEDS_REVIEW banners; defaults are `quarantine` for legal deliverables (`COMPOSE_*`, `ATTACHMENT_*`) and `mark_stale` for Analyze outputs per Appendix D.

- SLO guardrails:

  - Guardian judgment P95 ≤ 5m; Compose ≤ 45m P95; upload finalize ≤ 5s. Alerts on burn rates and budget breaches; see §12.6 dashboards.

- **Source material:** `§12`, `§12`, `§10.8`, `../ops/runbooks/index.md`

- **Priority:** Medium (operational readiness)

______________________________________________________________________

### 12.6 Named dashboards & alert routing

*Purpose: Provide common observability views and bind alerts to runbooks.*

- Guardian SLO & Throughput (SRE): judgment latency P50/P95/P99, error rate, queue depth/backlog age (`guardian_pending_total`, `guardian_pending_oldest_seconds`), submission timeout rate (`guardian_submission_timeout_total`), false-positive ratio (`guardian_quarantine_false_positive_total / guardian_judgment_total`), synthetic success, SLO burn rate.
- Queues & KEDA (SRE): Celery queue depth per lane, replicas, scaling events, DLQ intake and drain, job cancellation spikes (`job_cancellation_total`), watchdog escalations (`job_watchdog_timeout_total`), and review backlog ageing (`review_queue_backlog_total`, `review_queue_oldest_seconds`).
- LLM Cost & Circuit (Platform): tokens in/out, estimated spend vs cap, circuit state per model/provider, fallback reason codes.
- Localization & Policy Engine (Platform/SRE): dashboards and alerting requirements defined in `../services/lp-engine.md §5` (lookup latency, cache health, compiler cadence, adoption safety signals).
- Reference Manager – Ingestion & Quality (Content Ops/Legal Ops): dashboards and alert thresholds live in `../services/reference-manager.md §5.1` (harvest throughput, freshness, selector health, coverage).
- Reference Manager – Review & Publishing (Content Ops/Legal Ops): see `../services/reference-manager.md §5.1` for backlog, adoption, publish latency, and resource coverage monitors.
- Audit Seal & WORM (SecEng): seal cadence, seal errors, WORM lag, verification status.
- Portal Security (SecEng): download rate per org/user, anomaly triggers, link invalidations, adaptive MFA prompts.
- PHI Detection & HIPAA (SecEng/Compliance): `phi_detection_scan_total`, `phi_detection_positive_total{stage}`, `phi_detection_drift_total`, rescan latency, Guardian quarantines triggered; dashboards link to sampled artifacts for manual review.
- Advisory Locks (SRE): locks held by scope/kind, age percentiles, stale detections, terminations; tied to [Runbook RB-LOCK-006](../ops/runbooks/index.md#rb-lock-006).
- Logging Pipeline (SRE): ingest lag, drop rate, spool utilization, index health; alerts map to `../ops/runbooks/index.md (RB-LOG-007)`.
- Upload Scanning (Security): queue depth, scan duration, infected/errored totals, signature freshness metrics; alerts route to [Runbook RB-UPLOAD-SCAN](../ops/runbooks/index.md#rb-upload-scan).
- Unit Economics & Delivery (PM/SRE): cost per case/org; MoM deltas; top 10 expensive cases; delivery counts and failure rates.

Instrumentation rollout: All dashboards listed here are live in production with paging alerts. SRE and Platform teams control alert thresholds via Settings; when a team pauses ownership (for example, onboarding a new runbook), the associated dashboard can be switched to warning-only mode using the documented change process in `../ops/runbooks/index.md`.

Alert routing

- Sev-1 pages on: Guardian SLO burn > 2x target 15m; audit seal missed 2 intervals; queue depth > 3× budget 10m.
- All alerts include `dashboard_url`, `runbook_id` (when applicable), and last 5 relevant traces.

### 12.7 Synthetic monitors coverage

*Purpose: Continuously validate critical paths and assumptions.*

- Web: `/readyz` checks RLS GUCs; `/healthz` verifies DB connectivity and cache coherence.
- Guardian: submit synthetic artifacts for both a WP (expect PASS → CLEARED_FOR_USE) and a CD under `review.mode=MANUAL` (expect PASS → OPERATOR_PREP) with known inputs; verifies rule load; latency within SSE SLO.
- Signer: sign a synthetic document against test trust roots; verify TSA/OCSP reachability.
- Settings: activate a safe test bundle; diff preview matches expected; revert; validators pass.
- Watchdog runner: `watchdog-runner` Celery beat schedule fires every minute, invoking all watchdog tasks (Guardian backlog, job progress, advisory locks, integrity queue). A self-check endpoint `/ops/watchdog/status` reports the most recent execution timestamp and per-task durations; synthetic monitor verifies the timestamp delta stays \< 120s. Metrics `watchdog_runner_lag_seconds`, `watchdog_runner_missed_total`, and log-based alerts catch missed beats; if the runner stalls, [Runbook RB-JOB-WATCHDOG](../ops/runbooks/index.md#rb-job-watchdog) and Appendix B.3 prescribe manual invocation plus root-cause remediation before re-enabling automation.
- Portal: download approved synthetic artifact; ETag/Range behavior validated; portal invalidation simulated.
- Reference Manager (EU-REFERENCE tenant): synthetic monitoring, residency assertions, and escalation criteria are documented in `../services/reference-manager.md §5.3`.
- Alert thresholds: burn-rate SLO alerts and synthetic failures must page on-call with proper runbook IDs.

### 12.8 Quotas & metering

*Purpose: Enforce fair‑use and protect performance budgets.*

- Quotas: per‑org limits on uploads/day, concurrent jobs, portal downloads/min; Settings expose knobs and per-org overrides.
- Enforcement: API checks at submission and per request; friendly 429s with `Retry-After` + guidance; dashboards for sustained breaches.
- Metering: counters for usage; monthly exports; tie-in with FinOps budgets; anomaly detection.
- Source material: `§12.8`, `§12.9`

### 12.9 FinOps dashboards & alert wiring

*Purpose: Ensure cost signals are visible and actionable.*

- Dashboards: `llm_cost_estimate_total`, `finops_cost_per_case_usd`, MoM regression panel, top N expensive cases, budget forecasts, and logging volume views (`logging_bytes_ingested_total`, budget vs actual per service).
- Alerts: regression > threshold (default 10%); monthly cap risk > X%; route to Product/SRE with runbooks; annotate releases.
- Acceptance: dashboards exist and alerts fire in staging drill before enabling in prod, including `LOG_VOLUME_BUDGET` alerts tied to `../ops/runbooks/index.md (RB-LOG-007)`.

#### 12.9.1 Portal-facing usage transparency

*Purpose: Explain how portal surfaces expose usage, alerts, and audit notices to clients.*

- *Purpose: Extend FinOps visibility to customers while keeping controls consistent with internal reporting.*
- Admin usage dashboard (`portal.usage_dashboard.enabled`, default `true`): portal `Org Admin` view surfaces rolling 7/30-day spend, token consumption, job counts, and export volumes using the same metrics powering internal FinOps dashboards (`llm_cost_estimate_total`, `finops_cost_per_case_usd`, `case_jobs_total`). CSV exports mirror the monthly reports for finance; APIs provide `GET /portal/org/{org_id}/usage` with pagination and granular filters.
- Guardrails: data is scoped by org and adheres to residency/privacy policies enforced via secure views (§4.3). Rate limits protect against scraping; anomalies raise `PORTAL_USAGE_EXPORT_ANOMALY` events and notify support.
- Acceptance: feature flag stays limited to pilot orgs until (1) UX copy passes localization review, (2) support playbooks for billing inquiries are published, and (3) synthetic monitors validate parity between staff and portal dashboards for representative orgs.

### 12.10 Business continuity & degraded operations

*Purpose: Outline how teams sustain service when automation or guardians fail.*

- **LLM outage:** The `ModelFailoverOrchestrator` automatically advances to the next healthy provider in the documented `fallback_chain`; envelopes capture the substitute model and parity hash. If every fallback is unhealthy the queue transitions to `PAUSED_AWAITING_PROVIDER`, workers stop launching new runs, and automation polls health every 60 seconds (three consecutive greens required) before resuming. Customer notifications only trigger if the pause exceeds 15 minutes or impacts SLA targets.
- **Guardian impairment:** Freeze approvals that rely on Guardian PASS/WARN judgments; manual reviewers follow Appendix B.1 in `../services/guardian.md` and log judgments as `MANUAL_GUARDIAN_JUDGMENT` artifacts until the service recovers.
- **Transcription fallback:** The `SpeechFailoverController` retries against the next speech provider/region in `speech.jobs[].fallback_chain` with full equivalence logging. When the chain is exhausted jobs enter `PAUSED_AWAITING_PROVIDER` and automatically resume once health probes confirm recovery; no human transcription is used in the automated path.
- **Communication cadence:** Duty Manager sends initial update within SLA (§1.6) and hourly until resolved; final customer notice includes timeline, data impact, and remediation.
- **Drills:** Semi-annual BCP exercise simulating combined Guardian + LLM outage; evidence stored as `BCP_DRILL_REPORT` artifacts linked in `../ops/runbooks/index.md`.

### 12.11 Fail-closed behaviors matrix

*Purpose: Summarize safety defaults, their downstream impact, and where to find remediation guidance.*

| Subsystem              | Fail-closed behavior                                                            | User impact                                                                                              | Runbook                                                       |
| ---------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Guardian               | Rejects submissions; artifacts remain `PENDING_JUDGMENT` until service recovers | New approvals paused; portal shows OPERATOR_PREP backlog                                                 | Appendix B.1                                                  |
| Settings Service       | New jobs block on snapshot fetch; running jobs continue with embedded snapshots | Operators see queue backlog; activation UI disabled                                                      | [Runbook RB-GOV-008](../ops/runbooks/index.md#rb-gov-008)     |
| Audit seal / WORM      | Portal deliveries blocked if seal chain breaks for >1 interval                  | Reviewers cannot promote artifacts; portal download attempts 503                                         | `../ops/runbooks/index.md (RB-AUDIT-004)`                     |
| Residency policy guard | Jobs error with `RESIDENCY_POLICY_BLOCK` on drift                               | Org must adjust settings or seek waiver before resubmission                                              | [Runbook RB-RES-BLOCK](../ops/runbooks/index.md#rb-res-block) |
| LLM provider circuit   | Queue enters `PAUSED_AWAITING_PROVIDER`; health probes run every 60 s           | Compose/Analyze jobs paused; auto-resume after consecutive green probes; manual drafting requires waiver | [Runbook RB-LLM-003](../ops/runbooks/index.md#rb-llm-003)     |

______________________________________________________________________

## 13) Quality, testing & compliance validation

### 13.1 Test strategy tiers (unit, integration, end-to-end, property)

*Purpose: Provide a holistic testing framework for engineering teams.*

- Unit tests cover models, services, and policies with high type coverage (pyright/mypy). Integration tests simulate agent flows, Guardian judgments, settings activation.
- End-to-end tests orchestrate uploads → Guardian → approval → portal delivery with stubbed providers; nightly in staging.

### 13.2 Property tests & fixtures

*Purpose: Increase confidence in critical invariants and edge cases.*

- Property tests: settings precedence (SYSTEM≺ORG≺CASE), RLS denials without GUCs, idempotency store uniqueness, approval swap exclusivity.
- Fixtures: synthetic audio for long/short transcripts, redaction payloads with seeded PII, sample manifests, judgment history rows with varied reasons.
- Test gates: required to pass in CI before promoting settings or rules changes; failure blocks deploy.
- Property-based tests validate fingerprint/UUIDv5 determinism, manifest integrity, and advisory locks across edge cases.
- Fingerprint vectors from `spec/vectors/uuid_fingerprints.json` feed analyze/compose determinism tests ensuring helper outputs remain stable across refactors.
- Coverage targets: ≥ 90% for critical modules (agents, Guardian, Settings) per AGENTS guides.

### 13.3 Governance/privacy acceptance suites

*Purpose: Validate compliance requirements continuously.*

- DSAR/erasure flows, legal hold enforcement, field masking, and break-glass logging validated with synthetic cases.
- Residency matrix: activations that violate regional policies are rejected with `VALIDATION_ERROR`; runtime pre-flight blocks cross-jurisdiction runs (`RESIDENCY_POLICY_BLOCK`).
- Privacy API Spectral stubs warn until GA, then block; endpoints declare security and HMAC; examples avoid PII.

#### 13.3.1 Detection & masking controls (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/privacy/detection_suite.py::run_quality_suite`, Tests `tests/privacy/test_detection_suite.py::test_golden_corpora_thresholds`, Observability Grafana “Privacy & Masking QA” panel (metric `phi_detection_drift_total`).

*Purpose: Summarize automated detection and masking checks verified by QA.*

- **Detector parity suites:** locale-specific golden corpora (`tests/privacy/golden/<locale>`) must meet ≥ target recall/precision; regressions block deployment. CI reports include confusion matrices and drift deltas vs previous release.
- **Vault round-trip tests:** nightly jobs run `mask → detokenize → compare` for each restorable entity type and vault profile. Failures page Security Engineering and open a Sev-2 incident.
- **Never-log fuzzing:** property-based tests (`tests/privacy/test_log_scrubbing.py`) generate random PHI/PII payloads and assert logs/traces remain scrubbed. Failures gate merges and trigger lint suggestions for offending modules.
- **FIPS attestation enforcement:** masking vault and signer services log `fips_module_id` into manifests and auxiliary records; CI verifies module IDs against allowlisted certificates and fails when modules fall out of validation.
- **Break-glass audits:** weekly job (`ops/audits/break_glass_audit.py`) fails if any reveal lacks justification, dual approval, or linked retrospective ticket. Results land in `audit_event` (`BREAK_GLASS_AUDIT_FAILED`) and block releases until resolved.
- **Policy drift sampling:** Guardian samples ≥5% (or ≥20) artifacts weekly, recomputes detections, and compares to production runs. Divergence beyond tolerance increments `phi_detection_drift_total` and halts promotion until mitigated.

### 13.4 LangGraph contract tests and replay harnesses

*Purpose: Prevent regressions in agent graph behavior and reproducibility.*

- Node idempotency: re-run a completed lane → zero new LLM calls; outputs identical or schema-equivalent.
- Checkpoint resume: kill between Lane QA and Final QA → resume at Final QA without re-calling LLM.
- Cross-lane integrity: conflicting entity/event refs cause Final QA rejection with actionable QA log.
- Fallback correctness: force primary model OPEN circuit → fallback chosen; evidence records circuit state.
- Deterministic IDs: same anchors yield the same UUIDv5-derived reference; changed spans produce new IDs while preserving prior fingerprints in manifests.
- Policy block: simulate region disallowance → `POLICY_BLOCK` in ContextBuilder; token ceilings truncate prompts within bounds.
- SDK/OpenAPI alignment: `scripts/sdk/check_openapi_alignment.py` verifies generated client types remain in lock-step with OpenAPI bundles (Guardian, Settings, Jobs, Agents). The check fails when SDK model diffs do not accompany OpenAPI changes, preventing stale DX artifacts.

### 13.5 Deployment gates (FinOps, error budgets, security scans)

*Purpose: Enforce release safety and cost controls.*

- CI gates: type-checks, lint/format, unit/integration, OpenAPI lint, SBOM, image signing; nightly DAST on staging before promotion.
- Golden-set jailbreak gate: the release pipeline halts unless the `golden_set:jailbreak` job passes on the candidate build within the last staging run; failures require product/security sign-off and a fresh run before deploy.
- FinOps: CI step `scripts/finops/check_mom_guard.py` blocks releases when the MoM regression exceeds `llm.finops.guard.threshold_pct` (default 10%) or any org’s trailing 7-day burn surpasses `llm.finops.guard.trailing7d_pct` (default 25% of the monthly cap); both thresholds are configurable per org within approved bounds.
- Error budgets: breaches block releases until burn rate stabilizes; dashboards link from alerts.
- Vulnerability policy: SCA/SAST/secret scanning on every PR; Criticals block unless risk-accepted.

### 13.6 SBOM & build provenance

*Purpose: Guarantee supply-chain transparency and tamper-evident releases.*

- Builds emit CycloneDX SBOMs (`build/sbom/*.json`) via Syft/Grype; artifacts stored in object storage (`ops/artifacts/sbom/<commit>.json`) with SHA-256 recorded in release manifest.
- Container images signed with Cosign + Sigstore keyless flow; attestations include SLSA provenance (`predicateType: https://slsa.dev/provenance/v1`) capturing git commit, builder, and build inputs. Verification runs in deployment pipelines and documented in App.K evidence.
- SBOM retention: minimum 2 years or life of supported release, whichever longer. Access requires Security or Compliance role; auditors receive read-only bucket link during assessments.
- Third-party dependency diffs reviewed weekly; high-risk packages flagged in `DEPENDENCY_RISK_REPORT` artifacts referenced in App.P.
- OSS licenses and notices shipped with releases are catalogued in App.P.

### 13.7 Secure coding standard & scanning

*Purpose: Establish mandatory guardrails for code quality and vulnerability prevention.*

- Standards: OWASP ASVS L2/L3 controls where relevant; banned APIs list (`docs/security/banned_apis.md`) enforced via custom ruff rules and pyright plugins; secret-scanning (detect-secrets + trufflehog) runs on every PR.
- Coverage targets: unit coverage ≥ 80 % per critical service, integration coverage ≥ 60 %; failing to meet thresholds blocks merge without approved exception logged in App.O risk register.
- Tooling: ruff, mypy, pyright, bandit, semgrep, gitleaks, dependency-review. Critical/High findings must be resolved or explicitly risk-accepted with expiry.
- KPI dashboard tracks open vulns by severity, mean remediation time, and SLA compliance (Critical ≤ 7 days, High ≤ 14 days). Breaches escalate to Security leadership and appear in §15.3 decision log.

### 13.8 Compliance evidence generation (SOC2, privacy records)

*Purpose: Automate artifacts required for audits and regulator reviews.*

- Generate quarterly `SYSADMIN_RECERT_REPORT` artifacts; contract tests assert creation, audit trail, and dual-approval gates.

- Publish DPIA/RoPA record references in audit seals; retain evidence of settings activations and Guardian judgments.

- Diagram drift checks: fail build when diagrams change without source updates; ensure traceability.

- Diagram drift check (binding): CI job `diagram:diff` ensures exported ERD/service-map assets only change alongside their `.mmd`/`.drawio` sources and associated commit notes.

- **Source material:** `§12`, `§14.4`, `§12.9`, `§10.8`, [`../services/settings-registry.md Appendix A`](../services/settings.md#appendix-a-settings-key-map-traceability-index)

- **Priority:** Medium (QA & compliance alignment)

______________________________________________________________________

## 14) Operations playbooks & lifecycle

- Glossary: Appendix I captures retention, legal hold, and governance terms referenced in this chapter.

### 14.1 Tenant provisioning & offboarding

*Purpose: Standardize customer lifecycle in ops tools.*

- Provisioning: create org in Keycloak, configure domains (SPF/DKIM), set residency allowlists, budgets, templates, rotate initial secrets. Onboard staff via invites with role assignments.
- Offboarding: disable logins, export data with tamper-evident bundles, revoke keys, enforce retention/erasure, archive audit seals. Checklist recorded in `../ops/runbooks/index.md`.

#### 14.1.1 Legacy case import (roadmap)

*Purpose: Provide an inbound migration path that mirrors export guarantees and preserves chain-of-custody evidence.*

- Legacy case import supports both ops-assisted and self-service flows. Ops-assisted imports use `scripts/import/validate_case_bundle.py` to verify manifest signatures, residency tags, and hashes before queueing the `case_import` Celery task; every run logs to `ops/<job_id>__case_import_log.json` and emits `CASE_IMPORT_ATTEMPT` audit events (see `../ops/runbooks/index.md` runbook). Self-service org admin workflows (`POST /ops/case-imports`, guarded by `import.legacy_cases.enabled`) apply deterministic ID mapping, replay Guardian review states, and produce reconciliation reports for reviewer confirmation. Portal visibility stays blocked until the service approves the imported artifacts.
- Observability & guardrails: metrics `case_import_duration_seconds`, `case_import_artifacts_total{status}`, and drift checks comparing imported hashes to manifest expectations. Synthetic drill runs quarterly to confirm import tooling keeps parity with export schema revisions; failures block expanding the feature flag beyond pilot orgs.

### 14.2 Artifact retention, legal hold, and destruction flows

*Purpose: Align document lifecycle with policy and legal requirements.*

- Retention defaults: artifacts ≥ 365 days, audit logs ≥ case retention, privacy artifacts ≥ 730 days (Appendix N). HIPAA mode shortens certain retention and disables excerpt artifacts.
- Legal hold: `case.legal_hold = true` prevents destruction and surfaces reason (masked in secure view). Releases require approvals and audit log entries.
- Destruction: queued jobs with Guardian oversight produce `DESTRUCTION_CERT` artifacts; double-check via manifest before final delete.
- Object lock: production buckets enforce versioning + Object Lock (compliance mode) for audit sinks; destroy operations require dual approval and manifest verification.
- Ops scripts: `ops/scripts/destroy_case.py` (dry-run + execute) logs intended artifacts, checks legal hold, and writes `DESTRUCTION_CERT`; references recorded in Appendix N.
- Status & metadata: Retention and erasure jobs move artifacts through the `ARCHIVED → DELETED` path in §5.2.2 only after populating tombstone fields (`deleted_at`, `deleted_by`, `deletion_trigger`, `deletion_certificate_id`, `erasure_journal_id`, `retention_schedule_version`, `deletion_manifest_sha256`). Deletion certs reference the same IDs, and automation emits `ARTIFACT_TOMBSTONE_PURGED` when retention evidence is pruned.
- HIPAA mode enforcement: when `privacy.hipaa.enabled=true`, retention jobs honor shortened schedules, approvals for HIPAA-classed artifacts require WebAuthn step-up, evidence-store excerpts stay disabled (confirmed via the purge job above), and portal delivery of PHI-tagged attachments is rejected unless a security waiver is recorded.
- Diagram: DSAR/erasure hard-purge flow lives in `overview/tdd/diagrams/dsar-erasure-v1.mmd`.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/mermaid/overview/tdd/diagrams/dsar-erasure-v1.png" alt="DSAR hard-purge workflow">
  <figcaption style="font-size: 0.9em; color: #555;">DSAR hard-purge workflow</figcaption>
</figure>

#### 14.2.1 DSAR/erasure mode (binding)

**Breadcrumbs:** Implementation `ops/dsar/erasure_job.py::run_erasure`, Tests `tests/privacy/test_dsar_erasure.py::test_hard_purge`, Observability Grafana “DSAR Fulfillment” dashboard (metric `dsar_erasure_completed_total`).

*Purpose: Support hard-purge erasure requests without compromising provenance.*

- Settings: `compliance.erasure_mode ∈ {'off', 'hard_purge'}` (ORG) toggles hard purge; `compliance.subject_hkdf_salt` (SYSTEM, KMS-backed) seeds deterministic subject hashes. See [`../services/settings-registry.md Appendix A`](../services/settings.md#appendix-a-settings-key-map-traceability-index) for key traceability.

- Scope: Hard purge deletes artifacts, QA logs, evidence, and prompts tied to the subject; legal hold supersedes erasure requests and blocks purge.

- Artifact proof: Every purge emits an `ERASURE_JOURNAL` artifact capturing minimal evidence (subject hash, scope, approvals) and referencing the job manifest hash. Guardian review ensures readiness before portal exposure.

- Approval: Dual approval when policy requires (`privacy.dpia.reviewers.roles`), with audit records referencing erasure justification and timestamps. Waivers recorded when residency/retention conflicts arise.

- Process: Scheduler selects eligible records, acquires locks to avoid concurrent purges, performs deletion, writes `ERASURE_JOURNAL`, and appends ops log entry (`ops/<job_id>__erasure_log.json`).

- Framework timelines & notices: GDPR responses within 30 days (extendable per Article 12); CCPA/CPRA within 45 days (one 45‑day extension with notice). The platform records framework, deadline, extensions, and notices in the `ERASURE_JOURNAL` manifest and surfaces countdowns in the Admin UI. “Do Not Sell/Share” posture is enforced globally (no sale/sharing), and DSAR exports include an attestation of this posture for CCPA audits.

- Restores: Backup restore jobs must replay all applicable `ERASURE_JOURNAL` entries before the recovered case or subject is re-exposed to reviewers or clients.

- Manifest schema (normative):

  ```json
  {
    "schema_version": "erasure@1.0",
    "org_id": "22222222-2222-2222-2222-222222222222",
    "case_id": "33333333-3333-3333-3333-333333333333|null",
    "subject_hash": "sha256-hex",
    "scope": ["ARTIFACTS", "QA_LOGS", "EVIDENCE", "PROMPTS"],
    "requested_by_user_id": "44444444-4444-4444-4444-444444444444",
    "approved_by_user_ids": [
      "55555555-5555-5555-5555-555555555555",
      "66666666-6666-6666-6666-666666666666"
    ],
    "justification": "string",
    "executed_at": "RFC3339",
    "settings_snapshot_sha256": "sha256-hex"
  }
  ```

- Audit: Tombstone audit links preserve chain integrity without retaining content; purge actions emit `audit_event('DSAR_ERASURE_EXECUTED', {...})` with scope, actors, and manifest hash.

- Backups exception: immutable backups are not altered in-place. Instead, restore-point catalogue retains entries ≤ 35 days; if restoration is required, operators immediately re-run DSAR purge on recovered data before bringing case online. Evidence (backup set IDs, purge confirmation) appended to the initiating `ERASURE_JOURNAL`.

### 14.3 Key management & secret rotation

*Purpose: Maintain cryptographic hygiene across services.*

- Secrets stored in Vault/Key Vault; rotation schedule documented (e.g., API HMAC keys quarterly, TLS certs ≤24h TTL). Rotation triggers service reload and Settings activation updates.
- Guardian and Signer keys require dual control. Audit events record rotation actor, key scope, and previous expiration.
- Client-provided keys (email, SMS) stored per org with restricted access; rotation process includes verification with provider.
- Root key material (Vault transit master, signing HSM keys) operates under two-person integrity: no single operator can export or rotate without co-approval. Break-glass escrow requires Security + Platform VP sign-off and generates `KEY_ESCROW_EVENT` artifacts.
- Hardware-backed keys: production signing keys live in cloud HSM (Azure Key Vault HSM) with policy `KV-Policy-Prod-001`; audit logs exported nightly and referenced in App.K evidence.
- Rotation automation pipelines: TLS certs rotate via GitHub Action `secops/rotate-certs.yml`, which writes attestations to `ops/security/cert_rotation/<date>.json` and updates `azure-key-vault://platform-secrets/certs/*`; Guardian/Signer HMAC keys rotate with `ops/security/rotate_guardian_keys.py`. A quarterly drill exercises the dual-publish → canary → cutover flow: enable the `svc-*-next` secret, replay synthetic signed requests (`scripts/security/key_rotation_canary.py`) across staging and a prod shadow job, observe `key_rotation_canary_success_total`, then revoke the old key. Rollback cue: if error rate or canary metric deviates >1%, revert `current` pointer and reissue the previous key bundle. Evidence bundles are attached to App.K control entries.
- Rotation cadence summary: TLS certs ≤24h TTL, API HMAC quarterly, Guardian/Signer keys semi-annually, customer-supplied keys per contract or ≤90 days. Upcoming rotations tracked in change calendar; overdue keys page SecEng.
- Escape hatch: should KMS become unavailable, documented manual signing path (`../ops/runbooks/index.md (RB-SIGNER-HSM)`) allows temporary softkey use capped at 24 h with post-incident review.

### 14.4 Vulnerability management & supply chain updates

*Purpose: Keep dependencies secure and up-to-date.*

- Monthly dependency audits using SCA tools; critical CVEs patched within 48h. `ops/security` backlog tracks remediation.
- Infrastructure scanning (container, cluster) integrated with security triage. Penetration testing results stored as artifacts (`PENTEST_REPORT`).
- Supply chain safeguards: pin dependencies, use checksums, enable SBOM generation. Build pipeline signs artifacts and release images.

### 14.5 Change management, versioning, and rollout plans

*Purpose: Ensure coordinated releases across services.*

- Versioning: semantic for APIs, semver-like for settings bundles and `agents.pipeline.definitions`, `graph_version` for agents. Releases require change tickets referencing TDD sections and pipeline definition IDs.
- Release topology & blue/green (binding): every deployable (web, workers, Guardian, Settings, LangGraph pipelines) maintains paired blue/green environments managed by Flux + Argo. Green receives the candidate build plus staged settings bundles; health, perf, and review-service synthetics run before any traffic cutover. Green only becomes canonical once success criteria hold for ≥30 minutes; failure auto-reverts traffic, settings, and manifests to blue.
- Rollout orchestrator & tenant migration (binding): `deploy.rollout_plan` consumes `agents.pipeline.rollouts[]` and infrastructure cohorts to move orgs through pilot → cohort → fleet. Cutovers happen in waves with automatic pauses when QA, FinOps, or residency monitors deviate. Migration state records `{org_id, rollout_wave, prior_definition_version}` so support can trace exposure and revert specific cohorts if needed.
- Automated rollback & overrides (binding): rollback scripts snapshot DB schema, settings bundles, and object storage manifests before cutover. Snapshots include data-plane validation (logical replication health, storage versioning, LangGraph state) so enterprise data/infra controls stay satisfied during revert. Configuration bundle rollback is deterministic: Flux re-applies the last good bundle version, settings service invalidates caches, and Guardian/LPE pods purge bundle caches before resuming traffic. On failure, orchestrator restores the prior snapshot, rebinds traffic to blue, and replays queued jobs against the previous pipeline. Emergency overrides (`deploy hold`, `deploy resume`, `deploy skip`) are audited, require dual approval, and expire automatically to prevent “forgotten” freezes.
- Communication: notify stakeholders (Product, Support, Security) with release notes summarizing changes, risk, and mitigation.
- Spec/code parity gate: `docs/settings_key_skip.txt` must remain empty; CI and release pipelines fail immediately if any Appendix E key lacks implementation coverage or automated tests.
- Case enum migration playbook: settings introduce new `case.status`/`representation_type` values first; DB adds `CHECK ... NOT VALID` constraints, validates post-backfill, and only then removes deprecated values. Deprecations flow through Settings/UI; final removal requires data migration and constraint regeneration.

### 14.6 Organization directory sync (Ops)

*Purpose: Keep org users and roles aligned with upstream IdP/Directory without breaking tenancy or RLS.*

- Scope: sync users, org membership, and role mappings; avoid storing PII beyond required identifiers.
- Integration: Keycloak/SCIM connectors; scheduled and on‑demand sync; diff‑based updates; conflict resolution rules.
- Safety: deny‑by‑default; degraded mode on sync failure; audit changes with actor/source; dry‑run mode for large updates.
- Observability: metrics (`dirsync_changes_total{kind}`, `dirsync_errors_total`), dashboards and alerts for failures.
- Source material: `§10.5`, roadmap §15.2

### 14.7 Admin governance & recertification

*Purpose: Periodically verify entitlements, policies, and exceptions.*

- Cadence: quarterly recertification; dual approvals for exceptions; step‑up MFA required.
- Artifacts: `SYSADMIN_RECERT_REPORT` and decision logs; surfaced to auditors; retention aligns with §14.2.
- Enforcement: block unsafe policy activations pending recert; alerts on overdue reviews; SSE events for recert windows.
- Automation: scheduled job (`0 3 1 */3 *`) enumerates principals with realm `sysadmin` or elevated org roles and produces structured reports `{principal_id, roles[], last_login, justification?, reviewer_ids[], attested_at}`; Security/Architecture must attest or revoke within 14 days or access is suspended until resolved.
- Source material: `§14.8`

### 14.8 Data migration & seeding operations

*Purpose: Keep schema changes, backfills, and seed data predictable and auditable.*

- Migration pipeline: every schema change ships with forward/backward-safe Alembic migrations plus dry-run artifacts (`migrations/README.md`) enumerating pre/post conditions. When mutating hot tables we execute a formal dual-write plan: (1) enable feature-flagged writes to the new table alongside the legacy path, (2) emit divergence metrics (`dualwrite_divergence_total`, `dualwrite_lag_seconds`) from a background reconciler, (3) block promotion until divergence remains 0 for ≥ 24h, (4) cut traffic by flipping the settings toggle, and (5) retire legacy writes only after snapshot/backups are captured. Rollback instructions and toggles live under Settings bundles so releases can revert without code changes.
- Seed data strategy: baseline organizations, roles, settings bundles, and Guardian rules install via `ops/scripts/bootstrap_platform.py` (idempotent) by loading the curated JSON bundles in `config/*.json` (and any environment-specific `config/seeds/*.json`). Seed updates run through the same approval flow as settings activations, with diff previews captured in App.K controls evidence and provenance hashes recorded alongside the bundle metadata.
- Backfills: long-running data backfills execute in Celery workers with OCC guards, chunked pagination, and advisory locks (`udlock.xact_lock('backfill', ...)`) to prevent overlap. Progress metrics and human logs land in `ops/<job_id>__backfill_log.json`.
- Smoke checks: migrations must register probes (`tests/migrations/test_<id>.py`) verifying secure views, RLS policies, and settings compilers post-upgrade. A staging cutover drill is mandatory before production rollout and recorded in App.M.
- Rollback: documented `down_revision` paths plus data snapshots for destructive changes; rollback playbooks include verification of recompiled policies, rehydrated caches, and SSE stream health.

### 14.9 Security disclosure & penetration testing

*Purpose: Formalize external vulnerability reporting, pentest cadence, and fix SLAs.*

- Vulnerability disclosure: publish `security.txt` at `/.well-known/security.txt` with `Contact: mailto:security@udocket.ca` and `Encryption: https://udocket.ca/pgp/security.asc`. Inbound reports acknowledge within 24h, provide triage results within 3 business days, and target remediation per severity SLA below. Disclosures tracked in the security incident register and mapped to App.K controls.

- Penetration testing: annual third-party assessments at minimum, with additional tests after major architecture changes (new data flows, agent classes, residency waivers). Findings log as `PENTEST_REPORT` artifacts, feed triage dashboards, and require verification of remediation evidence prior to closure.

- Severity SLAs: Critical fixes within 7 days, High within 14 days, Medium within 45 days, Low within 90 days unless risk accepted by Security and Architecture. Exceptions require waiver entries in App.O and Security leadership approval.

- Coordination: bug bounty pilots leverage the disclosure inbox; sanitized findings shared with Product/Ops for customer messaging when impact crosses multi-tenant boundaries.

- Monitoring: security backlog reviewed in weekly governance sync; outstanding high/critical items block releases per §13.4 deployment gates.

- **Source material:** `§14.2`, `§14.5–§14.9`, `§14.9`, `§5.7`, `§14.5`, `App.D`, `App.K–App.O`

- **Priority:** Medium (Ops + Security)

______________________________________________________________________

## 15) Roadmap alignment & open questions

- Glossary: Appendix I defines non-functional constraint terminology and deliverable acceptance vocabulary used below.

### 15.1 Capability alignment (feature gates, migrations)

*Purpose: Keep engineering/program leadership aligned with platform capabilities and enablement controls.*

- Capabilities include Analyze/Compose LangGraph execution, Guardian v2 rules, FinOps deploy gates, timeline/relationship agents, Settings self-service diff preview, SSE replay guard, portal messaging, and analytics dashboards. Feature flags in Settings bundles control org-level exposure; gating decisions are logged in the decision log with Appendix references.
- Release scope comprises secure ingest → Guardian → approval → portal delivery; dual-lane LangGraph runner; observability dashboards (review-service SLO, Queue/KEDA, LLM cost, logging); residency enforcement; DSAR/retention jobs; manual/agent edit workflows; analytics dashboards; ROPA automation; and portal messaging.
- Enablement guardrail: maintain the feature gating matrix (Appendix T) mapping each optional service (Localization bundles beyond en/fr, advanced Guardian heuristics, configurable policy catalogs) to explicit criteria—Ops runbook sign-off, load/perf evidence, owner bandwidth confirmation. Architecture council reviews the matrix quarterly to ensure previously gated capabilities re-enter scope only after criteria are satisfied.

### 15.2 Dependencies on external programs (IAM overhaul, infra upgrades)

*Purpose: Highlight work reliant on other teams or vendors.*

- IAM roadmap: Keycloak upgrade, org directory sync integration, potential SSO for enterprise clients (requires Settings and portal changes).
- Infra upgrades: Kubernetes version bump, service mesh migration, storage cost optimization.
- Provider dependencies: Azure Speech SLA adjustments, new LLM providers pending security review.

### 15.3 Risks, mitigations, and decision log

*Purpose: Surface known risks and capture resolution context.*

- Risks: LLM policy drift, Guardian false negatives, residency waiver backlog, staffing for manual reviews, LangGraph framework maturity, infrastructure/IaC complexity outpacing SRE capacity.
- Mitigations: continuous evals, rule dry-run/diff, automated waiver stamping, cross-training reviewers, dual runner fallback (`agents.langgraph.runner`), staged LangGraph upgrades with canary tests, plus dedicated DevOps enablement (Terraform/service-mesh training sprints, pairing during first three production releases, and annual certification of `../ops/runbooks/index.md` runbooks for infra owners).
- Decision log entries include change rationale, date, owners, references to sections impacted.

### 15.4 Outstanding research spikes

*Purpose: Track unresolved technical investigations.*

- Evaluate on-device speech normalization fallback, cross-region replication strategy, privacy-preserving analytics, automated QA suggestions for manual edits.
- Each spike records hypothesis, owner, expected completion, linked documents.

### 15.5 Sunset plan for legacy behaviors and documents

*Purpose: Plan deprecation steps for obsolete flows.*

- Retire prior TDD versions (v6 and earlier) once approvals complete; archive older docs with version tags.

### 15.6 Non-functional constraints (consolidated)

*Purpose: Centralize cross-cutting constraints and SLOs.*

- SLOs: API availability ≥ 99.9%/30d; read P95 ≤ 250 ms; write P95 ≤ 500 ms; decision P95 ≤ 5m; Compose P95 ≤ 45m.
- Security: TLS 1.3 preferred; mTLS for service‑to‑service; HSTS; CSP; signed images and SBOM.
- Residency: workloads remain within each org’s allowlisted regions; waivers recorded per §3.8 and surfaced in manifests.
- Privacy: masking, secure views, field‑level encryption (§4.5) for sensitive classes.
- Performance: backpressure via rate limits and quotas; bounded memory for LLM contexts; capped retries.

### 15.7 Deliverables acceptance

*Purpose: Define acceptance gates for major outputs of this program.*

- Platform: end-to-end path (upload→Guardian→approval→portal) passes in staging with synthetic data.
- Governance: runbooks executed; audits verified; settings validators enforce unsafe rules.

### 15.8 Roadmap alignment hooks

*Purpose: Link roadmap milestones to owners and dependencies so this TDD stays actionable.*

- Milestones → Epics:
- Milestone M1 (Analyze LangGraph GA) → Product epic `P-123`; depends on App.A diagrams, §6.7/§6.11 completion, [Runbook RB-LLM-003](../ops/runbooks/index.md#rb-llm-003) drill.
  - Milestone M2 (Portal messaging GA) → Product epic `P-207`; references §11.6 and Appendix J; depends on App.A A.8 flow and security review gates (§9.11).
- Milestone M3 (FinOps deploy guard) → SRE epic `SRE-88`; depends on §8.7, §12.9, FinOps dashboards wiring acceptance.
- Dependency notes: provider template updates (Appendix D) tracked in backlog; cross-team sequence captured in roadmap doc linking to this section.

______________________________________________________________________

### 15.9 Architectural decision records (binding)

**Breadcrumbs:** Implementation `docs/adr/README.md`, Tests `scripts/docs/check_adr_index.py::main`, Observability CI job “docs-adr-lint” with badge in Docs Quality dashboard.

*Purpose: Ensure significant technical choices remain discoverable, immutable, and supersedable.*

- ADRs live under `docs/adr/` and follow GitLab’s lightweight template (`Title, Context, Decision, Consequences, Status`). `docs/adr/README.md` indexes active, superseded, and deprecated entries; this TDD’s front matter `related_adrs` highlights the decisions most tied to the current scope.
- Lifecycle: new ADRs start as **Draft**, graduate to **Accepted** once Architecture + Security approve, and move to **Superseded** when a follow-on ADR renders the prior decision obsolete. Status changes require PR review plus an update to the ADR index table.
- Integration points: breaking API or security changes cannot transition this TDD to **Implementable** or **Implemented** without a corresponding ADR (e.g., `ADR-0003-api-versioning-and-sunset.md` for the deprecation policy, `ADR-0001` covering Guardian judgments/waivers). Cross-reference IDs appear throughout the document (see §3.9, §7.1, §10.0) to keep provenance intact.
- Tooling: `make adr:new` scaffolds numbered ADRs; CI verifies headers/metadata and blocks merges when ADR titles, filenames, or statuses drift from the index. Quarterly governance reviews audit ADR freshness and ensure open decisions align with App.K controls.

______________________________________________________________________

## 16) Search & knowledge retrieval

### 16.1 Indexing model and sources

*Purpose: Provide cross-layer search over artifacts while honoring residency and RBAC.*

- Sources: transcripts (latest approved or job-scoped), Analyze outputs (summaries, outlines, timeline seeds, entity hints), Compose deliverables, QA logs, and selected metadata fields; exclude sensitive raw attachments unless policy allows.
- Indices: full-text (Postgres/ES/OpenSearch) for keyword search; optional vector index for semantic search. Embeddings providers must respect `regions.allowlist.compute`.
- Document identity: each indexed record carries `artifact_id` (and lane/section for Analyze/Compose) to enable deep-linking; titles via shared `unique_title` helper.
- Update policy: on artifact APPROVED, indexers upsert records; on demotion/archival, records are hidden. Index jobs emit ops logs and metrics.
- Locale awareness: analyzers respect document language metadata; cross-language toggle exposes translated artifacts when available with fallbacks.

### 16.2 Retrieval APIs and results

*Purpose: Standardize how clients and agents query and consume results.*

- API: `GET /api/v1/search?case_id&q=&k=&type=` with filters for artifact types. Responses include snippets, highlights, and stable refs (`artifact_id`, lane/section IDs).
- Agents: Analyze/Compose retrieval uses case-scoped search with token ceilings and redaction; results include canonical refs to App.D artifact entries and transcript timestamps when applicable.
- Caching: per-query cache keyed by `(case_id, q, filters)` with short TTL; eviction on artifact state changes.

### 16.3 Security, residency, and RBAC enforcement

*Purpose: Ensure search respects the same deny-by-default policy as reads.*

- Index-time filters store `org_id`, `case_id`, and visibility state; query-time adds RLS-like constraints using the token’s `active_org_id` and case membership. Masked fields remain masked in results.
- Residency: embedding/vector stores must be deployed in allowed regions; vector shards run exclusively in the org’s approved regions (for example, `na-us-1`, `eu-west-2`) backed by object storage in the same geography. Cross-region restores are blocked by policy unless a waiver exists, manifests reflect the waiver, and the index bootstrap pipeline verifies residency before serving queries.
- Audit: log `SEARCH_QUERY_EXECUTED` with hashed query, `case_id`, and filters; redact content; metrics `search_qps`, `search_latency_seconds`, `search_results_per_query_p95`.

### 16.4 Cost, performance, and quality budgets

*Purpose: Keep retrieval affordable and responsive.*

- Budgets: target P95 search latency ≤ 400 ms; vector queries capped at `search.vector.max_top_k` with backpressure on sustained load.
- FinOps: track `search_cost_estimate_total` (if using paid vector providers). Circuit open if budget exceeded.
- Quality: relevance evaluated with curated queries and golden answers; dashboards show precision/recall trends.

### 16.5 UI integration and relevance feedback

*Purpose: Close the loop between users and ranking signals.*

- Staff UI: unified search in case workspace with filters; excerpts link to transcript timestamps and Analyze entities/events.

- Feedback: click/expand signals logged (privacy-safe) and fed to relevance tuning jobs. Feature flags control exposure.

- See App.D for searchable artifact types and field maps; §11 for UX constraints; §8 for LLM-powered retrieval compliance.

- Sunset manual artifact upload flow once new staging pipeline fully vetted.

- Plan retirement for non-Settings-based configuration files; ensure agents rely solely on Settings service.

- **Source material:** `§16`, `§16`, `§16`, `§12.9`, [`../services/settings-registry.md Appendix A`](../services/settings.md#appendix-a-settings-key-map-traceability-index) decision log

- **Priority:** Medium (keeps roadmap aligned)

______________________________________________________________________

## Appendices (link targets)

- **App.A** System context & sequence diagrams *(source: App.A)*
- **App.B** Threat model catalog *(source: §14.4, App.B)*
- **App.C** Data classification & retention matrices *(source: App.C, §15)*
- **App.D** Canonical artifact catalog *(source: App.F)*
- **See also:** [`../services/settings-registry.md Appendix A`](../services/settings.md#appendix-a-settings-key-map-traceability-index) *(source: §5.4)*
- **App.F** API reference snippets / example payloads *(source: §10.8)*
- **App.G** ERD and schema migrations history *(source: App.I)*
- **App.H** Ops runbooks & health check playbooks *(source: §12.2, Appendix H)*
- **App.I** Glossary and taxonomy *(source: Glossary, §16 taxonomy notes)*
- **App.J** SQL policy patterns *(source: §4.4, §11.6)*
- **App.K** Controls assurance map *(source: §2.2, §12, §14)*
- **App.L** Benchmark baselines *(source: §3.2, §8, §12)*
- **App.M** Environment & dependency matrix *(source: §3.2, §14.8)*
- **App.N** Privacy controls traceability *(source: §2.2, §14.2)*
- **App.O** Active waivers ledger *(source: §3.8, §7.1.1, §14.9)*
- **App.P** Third-party & OSS notices *(source: §13.6, App.P)*
- **App.Q** Sub-processors & DPAs *(source: §3.7, §8, §14.3)*
- **App.R** Data lineage maps *(source: §5.6, §6, §7)*
- **App.S** Ownership & RACI map *(source: §1.5, §15)*
- **App.T** Traceability matrix *(source: §3.8, §7, §10, §12.1, §12.6)*
- **App.U** Reference code snippets *(source: §6.11, §9.2, §10.8, §11.1.1)*

______________________________________________________________________

## Appendix A — System context & sequence diagrams (normative)

*Purpose: Provide authoritative visuals of service boundaries and key workflows.*

### A.1 System context

- Updated diagram (`overview/tdd/diagrams/system-context-v1.mmd`) depicting web, workers, supporting services, external dependencies, and trust boundaries. Includes overlays for mTLS domains and network policies.

### A.2 Upload → Guardian → Approve

- Mermaid sequence source `services/guardian/diagrams/upload-guardian-approve-v1.mmd`; shows client upload, staging, artifact creation, Guardian submission, reviewer approval, SSE notifications, and portal invalidation.

### A.3 Signing & delivery

- Mermaid sequence source `overview/tdd/diagrams/signing-delivery-v1.mmd`; covers signing request, TSA/OCSP validation, artifact promotion, link generation, and client download with ETag/If-Match.

### A.4 Error flows

- Diagram source `overview/tdd/diagrams/error-flows-v1.mmd`; illustrates TRANSIENT/POLICY/INPUT/INTEGRITY/CONCURRENCY paths with retries, quarantine, and user feedback.

### A.5 Approvals UX

- Flow source `services/guardian/diagrams/approvals-ux-v1.mmd`; illustrates staff review, QA, approve/reject, and portal invalidation.

### A.6 Portal invalidation

- Sequence `services/guardian/diagrams/portal-invalidation-v1.mmd`; shows invalidation path and 403 behavior.

### A.7 Analyze/Compose pipeline

- Sequence `overview/tdd/diagrams/analyze-compose-v1.mmd`; illustrates LangGraph lanes, artifact writes, and Guardian readiness.

### A.8 Manual/Agent Edit flows

- Flow `services/guardian/diagrams/approvals-edit-flows-v1.mmd`; shows editor flows and promotion/demotion behavior.

### A.9 Residency & policy enforcement

- Sequence `services/lp-engine/diagrams/residency-policy-enforcement-v1.mmd`; maps settings activation through LPE compile, OPA bundle reload, worker/Guardian checks, portal fetch-time validation, and waiver stamping.
- Diagrams maintained via `diagram:diff` CI job; PRs must include source updates (Mermaid/Draw.io) alongside exported SVG/PNG.

______________________________________________________________________

## Appendix B — Threat model catalog

*Purpose: Centralize high‑value threats, mitigations, and validations (STRIDE).*

### B.1 STRIDE summary (illustrative; see `../ops/runbooks/index.md` for runbooks)

- Spoofing (identity):
  - Vector: forged inter‑service calls
  - Mitigations: mTLS, HMAC signing (§7.3), short‑lived tokens, audience scoping
  - Validation: synthetic signed/unsigned request tests in staging
- Tampering (data at rest/in transit):
  - Vector: object storage overwrite or man‑in‑the‑middle
  - Mitigations: SSE‑KMS, bucket versioning, strong ETag from SHA‑256, TLS 1.3, WORM audit sink
  - Validation: integrity sweeps, WORM verification
- Repudiation:
  - Vector: missing audit trail of approvals/decisions
  - Mitigations: `audit_event`, Guardian history store, `delivery_receipt`, SSE correlation IDs
  - Validation: runbook drills; dashboards for decision rates and audit seals
- Information disclosure:
  - Vector: field leakage, portal stale links
  - Mitigations: secure views/masking (§4.5), portal invalidation (§11.2.1), strict CORS/ETag
  - Validation: unit/integration tests, staging drills
- Denial of service:
  - Vector: provider throttling, queue saturation
  - Mitigations: rate limits, circuit breakers, autoscaling, DLQ
  - Validation: synthetics and alert burn‑rate
- Elevation of privilege:
  - Vector: RLS bypass, unsafe settings activation
  - Mitigations: RLS GUC canaries (§4.4), deny‑by‑default policies, dual approval for unsafe changes
  - Validation: activation dry‑run/diff; fail‑closed probes

### B.2 Top threats & mitigations (illustrative)

- RLS bypass via pooling misconfig → AdmissionPolicy blocks statement pooling; fail‑closed canaries (§4.4, App.J.6).
- Residency leakage to non‑CA endpoints → mesh egress allowlist; region allowlist settings; Guardian waiver stamping (§3.8, §7.1.1).
- Prompt injection & policy drift → safety harness, golden‑set tests, QA gates, Guardian policy checks (§8.4, §7.1).
- SSE replay abuse → Last‑Event‑ID handling, snapshot rules, token‑bound streams (§10.8).
- Artifact integrity tamper → SHA‑256 ETag, WORM audit sink, integrity sweeps (§5.3, §12.1).

### B.3 Abuse controls (illustrative)

- Portal scraping → rate limits, anomaly triggers, forced invalidation, step-up MFA (§11.2.2, §12.8).
- Messaging misuse → content scanning, attachment limits, abuse reporting, audit trails (§11.6).
- Brute forcing APIs → global/org rate limits, IP throttles, 429 guidance, runbooks (§10.7, §12.6, `../ops/runbooks/index.md`). *Purpose: Document top risks, mitigations, and residual risk ratings.*
- **Threat tables:** Expanded STRIDE matrix covering RLS bypass, region leakage, LLM prompt exfiltration, Guardian rule poisoning, signature spoofing, SSE replay, and portal phishing.
- **Mitigation mapping:** For each threat, list preventive/detective controls (section references) and automation coverage (synthetics, alerts). Residual risk rated (Low/Medium/High) with owner.
- **Abuse cases:** Scenarios such as malicious reviewer approval, compromised client account, and mass download scraping with corresponding throttles and anomaly detection.
- **Updates:** Threat catalog reviewed quarterly by Security + Architecture; changes tracked in decision log and referenced in §15.3.

### B.4 Abuse prevention plan & fraud detection checks (normative)

- Governance: Abuse triad (Security Engineering Lead, Product Abuse PM, SRE) meets monthly to review abuse dashboards, App.T traceability rows, and new reports from Support. Action items flow into the security backlog with SLA tracking.
- Baseline detectors:
  - API anomaly detector: `api_abuse_scorer` job inspects rolling windows (IP/user/org) for unusual verb/method combinations and increments `api_suspect_request_total{reason}`. Score > threshold auto-enqueues an approval block pending human review.
  - Portal download sentinel: `portal_download.anomaly_score` (needs trend \< 1.5× baseline). 3 consecutive breaches trigger automatic `portal_link_invalidated` + step-up MFA requirement; `../ops/runbooks/index.md (RB-ETAG)` handles follow-up messaging.
  - Messaging fraud rules: heuristics for mass outbound, URL reputation hits, and attachment mismatch log to `messaging_abuse_detected_total` and quarantine threads until Guardian re-approves.
- Shadow/soak controls: High-risk pipeline changes (payment integrations, new export endpoints) must run in shadow mode (see §6.13) for ≥7 days with abuse detectors enabled; only after the review sign-off do we flip “serving” flags.
- Threshold waivers: temporary relaxations for shadow soaks or customer beta programs use `abuse.shadow.threshold_per_org` settings with explicit expiry (≤30 days) and are catalogued in App.O. Activation lints reject waivers without matching expiry and justification.
- For every new abuse vector, engineering must add: (1) detector metric + alert, (2) runbook entry (`../ops/runbooks/index.md`), (3) test fixture covering expected vs blocked flows, (4) traceability row in App.T.

______________________________________________________________________

## Appendix C — Data classification & retention matrices

*Purpose: Define classification, masking, storage location, and baseline retention.*

### C.1 Classification table

| Class         | Examples            | Masking                         | Storage                       | Default retention              |
| ------------- | ------------------- | ------------------------------- | ----------------------------- | ------------------------------ |
| PUBLIC        | docs, marketing     | none                            | object storage (public site)  | n/a                            |
| INTERNAL      | non‑PII ops logs    | redact sensitive fields         | object storage (private)      | life of case + 2y              |
| PII           | names, contact info | REDACT/HASH in logs             | object storage (private)      | life of case + 2y              |
| SENSITIVE_PII | health, minors      | REDACT in UI logs; NULL in JSON | object storage (private, KMS) | case + 2y (HIPAA may override) |
| HIPAA_PH      | medical             | REDACT everywhere; no excerpts  | object storage (private, KMS) | org policy (shorter)           |

### C.2 Retention mapping

- Map artifact types to retention groups (see §14.2 baseline and overrides). HIPAA override mode shortens Compose deliverables and disables excerpts. *Purpose: Align information handling with policy and jurisdictional requirements.*
- **Classification table:** Data classes (PUBLIC, INTERNAL, PII, SENSITIVE_PII, HIPAA_PH) with storage locations, at-rest/in-transit protections, masking requirements, default retention, permitted roles.
- **Residency matrix:** Mapping of `region_tag` to jurisdictions, residency/transfer rules, breach notification SLA (ties into §8.2). Specifies waiver requirements and Guardian stamping expectations.
- **Retention schedules:** Baseline retention for each artifact type (transcripts, analysis outputs, compose deliverables, audit logs, DPIA/ROPA). Includes HIPAA overrides and cross-reference to Appendix N.
- **Compliance dependencies:** Links to legal counsel sign-off and policy documents; updates require dual approval and version bump in Settings (`privacy.legal.matrix_version`).

Retention schedule (baseline; orgs may set stricter)

- Transcripts (TRANSCRIPT): ≥ 365 days from approval or case closure, whichever is later.
- Analyze outputs (SUMMARY/OUTLINE/TIMELINE/ENTITIES): ≥ 365 days; align with transcript retention to preserve traceability.
- Compose deliverables (CLIENT/LAWYER/BUNDLE/QA reports): ≥ 365 days; promoters may archive older versions when a newer APPROVED version exists.
- Ops logs (ops\_\*.jsonl, per-run JSON): retained for life of case + 2 years in the operational store; dual-streamed to WORM object storage with bucket-level retention locks per audit policy.
- Privacy artifacts (DPIA_RECORD, ROPA_RECORD): ≥ 730 days; listed in audit seals; access limited to `auditor|sysadmin`.
- QA logs: retained for life of case; hidden from portal; included in WORM audit scope.
- Entitlement snapshots and audit events: life of case + 2 years; WORM copies per audit policy.
- Legal hold: any hold on the case supersedes retention timers; destruction jobs must check hold state and emit `DESTRUCTION_CERT` artifacts upon completion.
- PolicyContext retention metadata and override governance are defined in `../services/lp-engine.md §2.3` and Appendix C; this appendix references those digests only when mapping artifact classes to residency and retention groups.

HIPAA override mode

- Shortens certain retentions (e.g., Compose deliverables) and disables excerpt artifacts; requires explicit activation in Settings with dual approval and audit trail.

______________________________________________________________________

## Appendix D — Artifact catalog

*Purpose: Define stable artifact types, filenames, directories, and versioning rules consumed by UI, agents, and Guardian.*

General rules

- Filenames are prefixed with `job_id` when tied to a run, and use `_v{n}` suffixes for regenerated versions without overwrite.
- All artifacts persist content SHA-256 in `artifact.content_sha256` and again in the manifest.
- Ops logs are per-run JSON + human-readable `.log`, plus append-only `ops_<agent>.jsonl` at the case level.

Ingestion inputs (binding)

| Artifact type     | Purpose                                                  | Notes                                                                          |
| ----------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------ |
| EXHIBIT_RAW       | Original exhibit uploads (PDF/image/archive)             | Stored under `docs/raw/`; Guardian enforces format allowlist prior to parsing. |
| EXHIBIT_TEXT      | Parsed/ocr text companion for exhibits                   | Linked to `EXHIBIT_RAW` via `source.inputs[]`; feeds Analyze search.           |
| COURT_DOC_RAW     | Court filings or orders as uploaded                      | Similar handling to `EXHIBIT_RAW`; maintains original casing.                  |
| COURT_DOC_TEXT    | Structured text extraction for court documents           | Used for diffing, timeline extraction, and Compose references.                 |
| EMAIL_RFC822      | Raw RFC822 email payloads (including headers)            | Stored encrypted; normalized to `EMAIL_TEXT` and attachments.                  |
| EMAIL_TEXT        | Parsed email body (plaintext/HTML converted)             | Preserves header metadata for Guardian/Compose citations.                      |
| EMAIL_ATTACHMENTS | Individual artifacts emitted per attachment              | Guardian scans each attachment; retained under case `docs/attachments/`.       |
| FINANCIALS_RAW    | Spreadsheet or CSV financial uploads                     | Normalized before conversion; preserved for audit.                             |
| FINANCIALS_TABLE  | Structured table representation of financial artifacts   | Stored as JSON/CSV; downstream analytics consume.                              |
| MEMO_TEXT\_\*     | Staff/comms memos with deterministic suffix per template | Used by Guardian to validate memo templates and approvals.                     |

Artifact table

| Artifact type             | Directory / pattern                          | Exclusive | Manifest pointer                       | Notes                                                                              |
| ------------------------- | -------------------------------------------- | --------- | -------------------------------------- | ---------------------------------------------------------------------------------- |
| TRANSCRIPT                | `transcript/<job_id>__transcript.txt`        | **Yes**   | `<transcript>.manifest.json`           | Header includes case, source, language, hashes                                     |
| AUDIO_NORMALIZED          | `audio/<job_id>__<normalized_name>`          | No        | n/a                                    | PCM 16 kHz mono copy for reproducibility                                           |
| OUTLINE_JSON              | `analysis/<job_id>__outline_v1.json`         | No        | `<outline>.manifest.json`              | Hierarchical outline for Compose                                                   |
| TIMELINE_JSON             | `timeline/<job_id>__timeline_v1.json`        | No        | `<timeline>.manifest.json`             | Normalized timeline events (speakers, timestamps, UUID anchors)                    |
| ENTITIES_JSON             | `analysis/<job_id>__entitIES_v1.json`        | No        | `<entities>.manifest.json`             | Deterministic UUID per entity/relationship                                         |
| ISSUES_JSON               | `analysis/<job_id>__issues_v1.json`          | No        | `<issues>.manifest.json`               | Issues presented or evident                                                        |
| FACTS_JSON                | `analysis/<job_id>__facts_v1.md`             | No        | `<facts>.manifest.json`                | Facts as they are presented                                                        |
| GAPS_JSON                 | `analysis/<job_id>__gaps_v1.md`              | No        | `<gaps>.manifest.json`                 | information gaps and other unknowns                                                |
| REPORT_MD                 | `analysis/<job_id>__analyze_report_v1.md`    | No        | `<report>.manifest.json`               | Human readable report containing internal notes, QA logs and run logs              |
| COMPOSE_CLIENT_MD/DOCX    | `docs/<job_id>__compose_client_v1.md\|docx`  | **Yes**   | `<compose_client>.manifest.json`       |                                                                                    |
| COMPOSE_LAWYER_MD/DOCX    | `docs/<job_id>__compose_lawyer_v1.md\|docx`  | **Yes**   | `<compose_lawyer>.manifest.json`       |                                                                                    |
| COMPOSE_BUNDLE_EXCERPT_MD | `docs/<job_id>__compose_bundle_v1.md`        | **Yes**   | `<compose_bundle>.manifest.json`       | Excerpt for bundle                                                                 |
| COMPOSE_STAFF_REPORT_MD   | `docs/<job_id>__compose_staff_report_v1.md`  | No        | `<compose_staff_report>.manifest.json` | QA staff notes                                                                     |
| COMPOSE_QA_REPORT_MD      | `docs/<job_id>__compose_qa_report_v1.md`     | No        | `<compose_qa_report>.manifest.json`    | QA outcomes                                                                        |
| DPIA_RECORD               | `privacy/<job_id>__dpia_v1.json\|md`         | No        | `<dpia>.manifest.json`                 |                                                                                    |
| ROPA_RECORD               | `privacy/<job_id>__ropa_v1.json\|md`         | No        | `<ropa>.manifest.json`                 |                                                                                    |
| AUDIT_SEAL                | `ops/<timestamp>__audit_seal_v1.json`        | No        | `<audit_seal>.manifest.json`           | Rolling Merkle root                                                                |
| SIGNATURE_CERT            | `docs/<job_id>__signature_cert_v1.json`      | No        | `<signature_cert>.manifest.json`       | Signer certificate bundle                                                          |
| ATTACHMENT_RAW            | `docs/<job_id>__attachment_raw_v1.bin`       | No        | `<attachment_raw>.manifest.json`       | Source binary for portal messaging/client uploads; Guardian-gated                  |
| ATTACHMENT_TEXT           | `docs/<job_id>__attachment_text_v1.json\|md` | No        | `<attachment_text>.manifest.json`      |                                                                                    |
| ERASURE_JOURNAL           | `privacy/<job_id>__erasure_journal_v1.json`  | No        | `<erasure_journal>.manifest.json`      | Hard-purge DSAR evidence; subject hashed with HKDF salt                            |
| DESTRUCTION_CERT          | `privacy/<job_id>__destruction_cert_v1.json` | No        | `<destruction_cert>.manifest.json`     | Case-level destruction attestation; links retention trigger + tombstone IDs        |
| CHAT_SESSION_JSON         | `ops/<session_id>__chat_staff.jsonl`         | No        | `<chat_session>.manifest.json`         | Staff Copilot conversation log with citations + moderation metadata                |
| CHAT_SESSION_CLIENT_JSON  | `ops/<session_id>__chat_client.jsonl`        | No        | `<chat_client_session>.manifest.json`  | Client portal chat conversation; portal-visible subset; Guardian-audited           |
| CHAT_SUMMARY_JSON         | `analysis/<job_id>__chat_summary_v1.json`    | No        | `<chat_summary>.manifest.json`         | Optional summarization of chat session; includes references and moderation outcome |
| AGENT_EDIT_PROPOSAL_MD    | `analysis/<job_id>__edit_proposal_v1.md`     | No        | `<agent_edit_proposal>.manifest.json`  | AI-assisted edit proposal human-reviewed before promotion                          |
| AGENT_EDIT_DIFF_JSON      | `analysis/<job_id>__edit_diff_v1.json`       | No        | `<agent_edit_diff>.manifest.json`      | Machine-readable diff for Agent edit proposals                                     |

- **NOTE:** Replace "v1" with v{n}

### D.1 Chat assistant artifacts (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/assistants/artifacts/chat.py::ChatArtifactWriter`, Tests `tests/udocket_core/assistants/test_chat_artifacts.py::test_manifest_integrity`, Observability Grafana “Assistant Sessions” dashboard (metric `assistant_chat_artifact_total`).

*Purpose: Enumerate chat assistant artifact types, manifests, and retention rules.*

- `CHAT_SESSION_JSON` (staff) and `CHAT_SESSION_CLIENT_JSON` (portal) share schema version `chat_session@1.0`:

  ```json
  {
    "schema_version": "chat_session@1.0",
    "session_id": "77777777-7777-7777-7777-777777777777",
    "audience": "staff|client",
    "case_id": "88888888-8888-8888-8888-888888888888",
    "org_id": "99999999-9999-9999-9999-999999999999",
    "started_at": "RFC3339",
    "ended_at": "RFC3339|null",
    "model_id": "string",
    "prompt_version": "string",
    "guardian_judgment": "PASS|WARN|BLOCK|WAIVED",
    "messages": [
      {
        "id": "uuid",
        "role": "user|assistant|system",
        "created_at": "RFC3339",
        "content": [
          {"type": "text", "text": "..." }
        ],
        "citations": [
          {
            "artifact_id": "uuid",
            "source_path": "transcript/<job_id>__transcript.txt",
            "start_offset_ms": 1234,
            "end_offset_ms": 5678
          }
        ],
        "moderation": {
          "status": "allowed|blocked|redacted",
          "reason_codes": ["INJECTION_ATTEMPT"]
        }
      }
    ],
    "metrics": {
      "prompt_tokens": 123,
      "completion_tokens": 456,
      "latency_ms": 789
    }
  }
  ```

- Staff transcripts retain full conversation (with masked snippets); client transcripts redact internal-only system prompts and any content hidden by moderation for the client audience. Both run through the redaction pipeline before persistence.

- `CHAT_SUMMARY_JSON` (`chat_summary@1.0`) stores structured summaries for downstream analytics: `{ "schema_version": "chat_summary@1.0", "session_id": "...", "summaries": [{ "audience": "staff|client", "locale": "en-CA", "text_md": "...", "citations": [...] }], "generated_at": "RFC3339", "model_id": "string" }`. Summaries always link back to the source session via `manifest.source_artifacts`.

### D.2 Agent edit artifacts (binding)

**Breadcrumbs:** Implementation `apps/platform/operations/agent_edit.py::persist_agent_edit_artifact`, Tests `tests/platform/operations/test_agent_edit_artifacts.py::test_append_only`, Observability Grafana “Agent Edit” panel (metric `agent_edit_artifact_total`).

*Purpose: Define artifacts emitted by agent-assisted edits and their approval flow.*

- `AGENT_EDIT_PROPOSAL_MD` contains the assistant-generated proposal rendered in Markdown with front-matter capturing `{edit_id, parent_artifact_id, locale, model_id, prompt_id, moderation_status}`. Content includes inline citation markers referencing the source artifact segments.

- `AGENT_EDIT_DIFF_JSON` (`agent_edit_diff@1.0`) delivers structured patches for programmatic diffing:

  ```json
  {
    "schema_version": "agent_edit_diff@1.0",
    "edit_id": "uuid",
    "base_artifact_id": "uuid",
    "operations": [
      {"op": "replace", "path": "/sections/3", "old": "...", "new": "...", "citations": ["artifact://..."]}
    ],
    "moderation": {"status": "allowed|blocked", "reason_codes": []}
  }
  ```

### D.3 Timeline artifacts (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/analysis/timeline.py::TimelineArtifactWriter`, Tests `tests/udocket_core/analysis/test_timeline_artifact.py::test_uuid_stability`, Observability Grafana “Timeline” panel (metric `timeline_artifact_total`).

*Purpose: Describe timeline artifact structure, identity, and promotion rules.*

- `TIMELINE_JSON` uses schema `timeline_v2@1.0`:

  ```json
  {
    "schema_version": "timeline_v2@1.0",
    "case_id": "uuid",
    "job_id": "uuid",
    "generated_at": "RFC3339",
    "events": [
      {
        "uuid": "uuid",
        "start_ms": 1250,
        "end_ms": 2380,
        "speaker": "Speaker A",
        "channel": 0,
        "label": "Initial consultation",
        "summary": "Client describes the accident at 5th Street.",
        "source": {
          "artifact_id": "uuid",
          "path": "transcript/<job_id>__transcript.txt",
          "start_offset_ms": 1250,
          "end_offset_ms": 2380
        },
        "tags": ["incident", "client_statement"],
        "confidence": 0.93
      }
    ],
    "normalization": {
      "speaker_strategy": "deterministic_channel",
      "timezone": "UTC"
    }
  }
  ```

- Events reference upstream transcript segments (Appendix D `TRANSCRIPT`) via deterministic UUIDv5 anchored on `{case_id, start_ms, end_ms, speaker, summary}`. Replays regenerate the same UUID when content matches, ensuring cross-agent linkage.

- Analyze and downstream tooling (timeline UI, Compose timeline sections) consume this artifact; modifications run through Manual/Agent edit flows, producing new timeline artifacts with `_v{n}` suffixes.

Ops logs

- Transcription: `ops/<job_id>__transcription_log.json`, `ops/<job_id>__transcription.log`, case-level `ops_transcription.jsonl`.
- Analyze: `ops/<job_id>__summary_log.json`, case-level `ops_summary.jsonl`.
- Compose: `ops/<job_id>__compose_log.json`, case-level `ops_compose.jsonl`.
- QA diagnostics: `ops/<job_id>__qa_log.json` (internal diagnostics only); reviewer-facing QA outputs stay Guardian-gated artifacts per the table above.

Exclusive types (binding)

- At most one APPROVED per case for `SUMMARY_MD`, `SUMMARY_JSON`, `COMPOSE_CLIENT_*`, `COMPOSE_LAWYER_*`, `COMPOSE_BUNDLE_EXCERPT_MD`.
- Settings may extend `artifact.exclusive_types[]`; Guardian enforces readiness; approval swap logic in §5.4.1.

Sample manifest pointers

- Each artifact includes a manifest conforming to §5.6; examples should be stored beside artifacts as `<filename>.manifest.json` for debugging.

Notes

- Replace `_v1` with `_v{n}` on regenerated artifacts; prior versions remain on disk. UI promotes only approved versions per type exclusivity rules.
- For any new artifact, add a distinct type constant, filename template, directory, and ops logging pattern here before implementation.
- Default downstream integrity action (`integrity.downstream_action`) is `quarantine` for legal deliverables (`COMPOSE_*`, `ATTACHMENT_*`) and `mark_stale` for Analyze narrative artifacts; overrides must be explicitly justified during Settings activation.

______________________________________________________________________

## Appendix E — Settings key map & traceability index

See [`../services/settings-registry.md Appendix A`](../services/settings.md#appendix-a-settings-key-map-traceability-index) for the complete key catalog, traceability matrix, and telemetry obligations.

______________________________________________________________________

## Appendix F — API reference snippets & examples (normative)

*Purpose: Provide signed, idempotent examples to guide integrations.*

### F.0 `ApiError.code` values

| Code                     | Description                                       |
| ------------------------ | ------------------------------------------------- |
| `POLICY_BLOCK`           | Guardian or settings policy prevented the action. |
| `QUARANTINED`            | Artifact is quarantined and unavailable.          |
| `INTEGRITY_ERROR`        | Hash or integrity validation failed.              |
| `VALIDATION_ERROR`       | Input payload failed validation.                  |
| `AUTH_ERROR`             | Authentication error (legacy umbrella code).      |
| `AUTH_CLOCK_SKEW`        | HMAC timestamp outside allowed skew window.       |
| `AUTH_SIGNATURE_INVALID` | HMAC digest or key mismatch.                      |
| `NOT_FOUND`              | Resource not found or not visible.                |
| `CONFLICT`               | Optimistic concurrency or idempotency conflict.   |
| `RATE_LIMIT`             | Rate, quota, or budget exceeded.                  |
| `PROVIDER_DEGRADED`      | Downstream provider degraded/unavailable.         |

The authoritative schema for these payloads lives at `spec/schemas/api_error.schema.json`. Spectral rule `ops/openapi/rules/apierror-enum.yaml` lints OpenAPI specs to keep responses aligned with this list.

### F.1 Idempotency contract & Guardian enqueue (binding)

**Breadcrumbs:** Implementation `apps/platform/operations/guardian.py::enqueue_with_idempotency`, Tests `tests/platform/operations/test_guardian_enqueue.py::test_idempotent_submit`, Observability Grafana “Guardian Queue” dashboard (metric `guardian_enqueue_conflict_total`).

Idempotency store schema (restated from §10.3.1 for quick reference)

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
CREATE INDEX idempotency_keys_expiry_idx
    ON idempotency_keys (expires_at);
CREATE UNIQUE INDEX idempotency_request_dedupe_idx
    ON idempotency_keys (org_id, scope, endpoint, request_hash);
```

Scope dimensions

| Column                      | Description                                                                                                                 |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `scope`                     | Logical action bucket (`job:create`, `artifact:approve`, etc.); shared constants in `packages.udocket_core.idem.constants`. |
| `endpoint`                  | Canonical `METHOD:/api/...` string preventing cross-route collisions.                                                       |
| `case_id`                   | Optional discriminator for case-scoped flows (null for global jobs).                                                        |
| `request_hash`              | `sha256` of the canonicalised request payload (body + sorted query + idempotency key).                                      |
| `status`                    | `in_progress` during execution, `succeeded` after persistence, `conflict` when a mismatched replay occurs.                  |
| `result_ref`                | Identifier returned to the caller (artifact ID, job ID, etc.).                                                              |
| `response_hash`             | `sha256` of the serialized response body for auditability.                                                                  |
| `response_code`             | HTTP status associated with the stored response (used for `Idempotency-Status`).                                            |
| `last_seen_at`/`expires_at` | Replay window accounting (default TTL = `api.idempotency.ttl_hours`).                                                       |

Collision handling & headers

- Services MUST compute `request_hash` using the shared helper and raise `409 CONFLICT` with `details.reason="IDEMPOTENCY_SIGNATURE_MISMATCH"` when an existing `(scope, key)` stores a different hash.
- Replay successes update `last_seen_at`, return the stored `result_ref`, and echo `Idempotency-Key` plus `Idempotency-Status: replay`. First-run success emits `Idempotency-Status: fresh`; conflicts return 409 with `Idempotency-Status: conflict`.
- `Idempotency-Status` joins structured logging (`idempotency_status` field) so SREs can track replay rates; metrics `idempotency_replay_total` and `idempotency_conflict_total` back deploy gates.

Header example (success replay)

```http
HTTP/1.1 200 OK
Content-Type: application/json
Idempotency-Key: 6d2fdc4c-483f-4f5b-9f4d-0f514c214766
Idempotency-Status: replay
X-Request-ID: 4f1a9c8c-0da5-4b27-9acd-6b6ddfd402c2

{ "artifact_id": "a7b9495c-4a5c-4e3b-91c6-5adef1d22264" }
```

Idempotency scopes

```js
IDEMPOTENCY_SCOPES = {
  "job:create",
  "job:checkpoint",
  "artifact:approve",
  "artifact:upload",
  "upload:finalize"
}
```

Guardian submissions now route through internal RPC queues; external clients never call the service directly. Admin tooling reuses the same RPC helpers with HMAC-authenticated service accounts and records evidence under `ops/guardian/batch_submit.jsonl`.

### F.2 Reviews approve (OCC lock implied)

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  https://platform.local/api/v1/reviews/$ARTIFACT_ID/approve \
  -d '{"note":"Looks good", "expected_version":3}'
```

### F.3 Signing request (HMAC)

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Signature-Key-Id: $KEY_ID" \
  -H "X-Timestamp: $(date -u +%FT%TZ)" \
  -H "X-Request-Signature: $(./scripts/sign.sh body.json)" \
  https://platform.local/api/v1/sign \
  -d '{"artifact_id":"...", "content_uri":"..."}'
```

### F.4 SSE events with Last-Event-ID

```bash
curl -N -H "Authorization: Bearer $TOKEN" \
  -H "Last-Event-ID: $LAST_ID" \
  https://platform.local/api/v1/jobs/$JOB_ID/events
```

Notes

- Headers exposed to browsers per §10.5 CORS; examples avoid PII.
- OpenAPI snippets below are normative; service implementations must keep them in sync with Spectral rules.

### F.5 Conditional GET with ETag and range

```bash
curl -I -H "Authorization: Bearer $TOKEN" \
  https://platform.local/api/v1/artifacts/$A/download

curl -L -H "Authorization: Bearer $TOKEN" \
  -H "If-None-Match: \"$ETAG\"" \
  -H "Range: bytes=0-1048575" \
  https://platform.local/api/v1/artifacts/$A/download
```

### F.6 CORS preflight

```bash
curl -i -X OPTIONS \
  -H "Origin: https://portal.local" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization, Idempotency-Key, X-Request-Signature, X-Signature-Key-Id, X-Timestamp, If-Match" \
  https://platform.local/api/v1/artifacts/$A/download
```

### F.7 Upload Finalize

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

### F.8 Review Approve (OCC)

```yaml
openapi: 3.1.0
paths:
  /api/v1/reviews/{artifact_id}/approve:
    post:
      parameters:
        - in: path
          name: artifact_id
          required: true
          schema: { type: string, format: uuid }
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [expected_version]
              properties:
                note: { type: string }
                expected_version: { type: integer, minimum: 0 }
      responses:
        "200":
          description: Approved
          content:
            application/json:
              schema:
                type: object
                required: [artifact_id, state]
                properties:
                  artifact_id: { type: string, format: uuid }
                  state: { type: string, enum: [APPROVED] }
                  version: { type: integer, minimum: 0 }
        "409":
          description: Conflict (stale version or illegal state)
```

### F.9 Rate limit response example (normative)

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 60
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 2025-10-19T21:15:00Z
X-Request-ID: 09c2d6c0-2bdc-4f8e-9f2d-4f64cb9f2e30
{
  "code": "RATE_LIMIT",
  "message": "Per-organization API request ceiling reached.",
  "details": {"retry_after_ms": 60000},
  "correlation_id": "09c2d6c0-2bdc-4f8e-9f2d-4f64cb9f2e30"
}
```

Illustrative payload; redact or mask as needed to comply with §10.5 rules prohibiting PII in examples.

Notes

- Headers exposed to browsers per §10.5 CORS; examples avoid PII.
- Full components (security schemes, shared headers/params) live in service-local specs; CI lints enforce shared rules.

### F.10 Deprecation response with `Sunset` header (normative)

```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Request-ID: 7d1f1dba-1d6f-4f6a-a7ef-2d2f1c2e9bd3
Deprecation: @1780272000; sunset="Mon, 01 Jun 2026 00:00:00 GMT"
Sunset: Mon, 01 Jun 2026 00:00:00 GMT
Link: </api/v1/migrations/2026-06-case-export>; rel="deprecation"; type="text/html"
X-uDocket-API-Version: 2025-01

{ "id": "...", "status": "deprecated", "sunset_at": "2026-06-01T00:00:00Z" }
```

- Every response advertises the scheduled removal date via `Sunset` and links to migration notes under `/api/v1/migrations/<version>`. Clients pinned to older versions receive the same headers; monitoring (`api_sunset_header_missing_total`) ensures deprecations remain compliant with §10.0.

### F.11 Header obligations (normative)

*Purpose: Record mandatory HTTP headers and deprecation signals for external APIs.*

| Category                  | Header(s)                                                                                                                                                                                  | Enforcement & reference                                                                                                                           | Notes                                                                       |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Exposed response headers  | `X-Request-ID`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`, `ETag`, `Deprecation`, `Sunset`                                                          | `config/settings.py::CORS_EXPOSE_HEADERS`; Settings bundle `security.cors.expose_headers`; validated by `scripts/security/verify_cors_headers.py` | Aligns with §10.5 acceptance; deviations require dual approval.             |
| Allowed preflight headers | `Authorization`, `Content-Type`, `Idempotency-Key`, `X-Request-Signature`, `X-Signature-Key-Id`, `X-Timestamp`, `If-Match`, `If-None-Match`, `If-Range`, `X-Style-Nonce`, `X-Script-Nonce` | Settings bundle `security.cors.allowed_headers`; test `scripts/security/verify_cors_headers.py`                                                   | Nonce headers support CSP enforcement per §11.5.                            |
| Security baseline         | `Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`                                                                         | Generated by `apps/platform/ui/security/csp.py` + middleware; asserted in `tests/e2e/test_security_headers.py::test_csp_header_enforced`          | CSP requires per-response script/style nonces; see §11.5.                   |
| Download guard contract   | `If-Match`, `If-None-Match`, `Range`, `If-Range`                                                                                                                                           | `apps/platform/portal/downloads.py::enforce_if_match`; tests in §10.6 acceptance                                                                  | Clients must echo `If-Match` ETag; violations return 412 `INTEGRITY_ERROR`. |
| Rate-limit headers        | `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`                                                                                                           | `apps/platform/api/middleware/rate_limiting.py::append_rate_limit_headers`; monitored via `api_rate_limit_header_miss_total`                      | Contract referenced in §10.5 acceptance and Appendix F.9.                   |

Refer to §10.5, §10.6, §11.2.2, and §11.5 for narrative requirements tied to these headers.

______________________________________________________________________

## Appendix G — ERD & schema migrations history

*Purpose: Capture database structure evolution and reference diagrams.*

- **ERD:** `docs/erd/uDocket-erd-v1.png` exported from Draw.io source with entity descriptions matching §5.1.
- **Migration ledger:** Table summarizing major migrations (ID, date, purpose, impacted tables). Highlights backward-compatibility considerations and deployment notes.
- **Schema policies:** Links to lint rules ensuring ORM uses secure views, triggers enforcing immutability, and migration templates for advisory locks or partitioning.
- **Tooling:** Instructions for generating ERD updates and running schema diff checks prior to migration PR merge.

______________________________________________________________________

## Appendix H — Runbook catalog references

*Purpose: Point platform teams to the maintained runbook library without duplicating procedures in this document.*\
*Contract: Operational playbooks reside under `docs/runbooks/` and service-specific specifications; this appendix links to those sources.*\
*State: Runbook owners track RB identifiers, alert bindings, and evidence requirements in the referenced documents.*\
*Failure modes & retries: `scripts/docs/lint_docs.py` flags missing runbook links; update the runbook catalog when adding or retiring alerts.*\
*Observability: Docs lint metric `docs_runbook_missing_total` and OnCall drill analytics monitor coverage.*

- **Platform runbooks:** `../ops/runbooks/index.md`
- **Settings Registry runbooks:** [`../services/settings-registry.md Appendix D`](../ops/runbooks/index.md#settings-appendix-r-runbooks-drills)
- **Guardian runbooks:** [`../services/guardian.md Appendix B`](../services/guardian.md#appendix-r-runbooks-drills-binding)

## Appendix I — Glossary & taxonomy

This glossary has moved to a dedicated appendix page. See: tdd/appendices/glossary.md

## Appendix J — SQL policy patterns (normative)

### J.1 Per-request GUC setup

```sql
SELECT set_config('udocket.active_org',    :active_org_uuid::text, true);
SELECT set_config('udocket.active_user',   :active_user_uuid::text, true);
SELECT set_config('udocket.active_roles',  :active_roles_csv, true);
SELECT set_config('udocket.realm_roles',   :realm_roles_csv, true);
SELECT set_config('udocket.operator_scope', :operator_scope, true); -- 'own_cases' | 'all_org_cases'
```

### J.2 Helpers (realm role, case membership)

```sql
CREATE OR REPLACE FUNCTION udocket_has_realm_role(role text)
RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT position(', ' || role || ', ' IN ', ' || coalesce(current_setting('udocket.realm_roles', true), '') || ', ') > 0
$$;

CREATE OR REPLACE FUNCTION udocket_is_case_member(p_case uuid)
RETURNS boolean LANGUAGE sql STABLE AS $$
  WITH v_user AS (
    SELECT NULLIF(current_setting('udocket.active_user', true), '')::uuid AS uid
  )
  SELECT EXISTS (
    SELECT 1 FROM case_member cm, v_user u
     WHERE cm.case_id = p_case AND cm.user_id = u.uid
  );
$$;
```

### J.3 Secure portal messaging RLS (binding)

**Breadcrumbs:** Implementation `db/migrations/portal/003_secure_messaging_rls.sql`, Tests `tests/platform/portal/test_secure_messaging_rls.py::test_rls_enforced`, Observability Grafana “Portal Messaging” panel (metric `portal_message_rls_violation_total`).

```sql
-- Threads visible to case members per policy
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

### J.4 Messaging tables (illustrative DDL)

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

### J.5 Central allow function (deny-by-default; sysadmin bypass)

```sql
CREATE OR REPLACE FUNCTION udocket_can(p_resource text, p_action text, p_case uuid, p_artifact uuid, p_field text DEFAULT NULL)
RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE v_org uuid := NULLIF(current_setting('udocket.active_org', true), '')::uuid;
DECLARE v_roles text := coalesce(current_setting('udocket.active_roles', true), '');
DECLARE v_scope text := coalesce(current_setting('udocket.operator_scope', true), 'own_cases');
DECLARE r text;
BEGIN
  IF udocket_has_realm_role('sysadmin') THEN RETURN true; END IF;
  IF v_org IS NULL THEN RETURN false; END IF;
  IF p_case IS NOT NULL AND v_scope <> 'all_org_cases' AND NOT udocket_is_case_member(p_case) THEN
    RETURN false;
  END IF;
  FOR r IN SELECT regexp_split_to_table(v_roles, ',') LOOP
    IF EXISTS (
      SELECT 1 FROM effective_permission ep
       WHERE ep.org_id = v_org AND ep.resource = p_resource AND ep.action = p_action AND ep.role = r
         AND ((ep.field IS NULL AND p_field IS NULL) OR (ep.field IS NOT NULL AND ep.field = p_field))
    ) THEN RETURN true; END IF;
  END LOOP;
  RETURN false;
END $$;
```

### J.6 RLS policy bindings (selected)

```sql
CREATE POLICY case_visibility ON "case"
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('CASE', 'read', "case".id, NULL, NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('CASE', 'write', "case".id, NULL, NULL)
);

CREATE POLICY artifact_visibility ON artifact
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND EXISTS (SELECT 1 FROM "case" c WHERE c.id=artifact.case_id)
  AND udocket_can('ARTIFACT', 'read', artifact.case_id, artifact.id, NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('ARTIFACT', 'write', artifact.case_id, artifact.id, NULL)
);

CREATE POLICY ent_hist_vis ON entitlement_snapshot
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('ENTITLEMENT_HISTORY', 'read', NULL, NULL, NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('ENTITLEMENT_HISTORY', 'write', NULL, NULL, NULL)
);

CREATE POLICY audit_vis ON audit_event
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('AUDIT_EVENT', 'read', NULL, NULL, NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('AUDIT_EVENT', 'write', NULL, NULL, NULL)
);

-- Guardian history RLS bindings documented in `../services/guardian.md`.
```

### J.7 Secure views and privileges (binding)

**Breadcrumbs:** Implementation `db/migrations/security/010_secure_views.sql`, Tests `tests/platform/db/test_secure_view_usage.py::test_only_secure_views`, Observability Grafana “Postgres RLS & Masking” dashboard (metric `secure_view_violation_total`).

```sql
CREATE VIEW case_secure WITH (security_barrier=true) AS
SELECT
  id,
  org_id,
  title,
  representation_type,
  status,
  legal_hold,
  udocket_mask('CASE', 'legal_hold_reason', legal_hold_reason) AS legal_hold_reason,
  legal_hold_since,
  created_at
FROM "case";

CREATE VIEW artifact_secure WITH (security_barrier=true) AS
SELECT id,
       org_id,
       case_id,
       type,
       status,
       content_sha256,
       CASE
         WHEN (SELECT 1
                 FROM field_mask_rule r
                WHERE r.org_id = artifact.org_id
                  AND r.resource='ARTIFACT'
                  AND r.field='content_uri'
                  AND NOT udocket_can('ARTIFACT', 'read', artifact.case_id, artifact.id, 'content_uri')
              ) IS NULL
         THEN content_uri
         ELSE udocket_mask(content_uri, 'REDACT')
       END AS content_uri,
       manifest,
       created_by,
       created_at,
       approved_at,
       approved_by,
       rejected_at,
       rejected_by,
       review_reason,
       version
  FROM artifact;

CREATE VIEW qa_log_secure WITH (security_barrier=true) AS
SELECT id, org_id, case_id, job_id, scope, lane_or_section, notes_md, issues_json, source_artifacts,
       created_by, created_at
  FROM qa_log;

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

CREATE VIEW entitlement_snapshot_secure WITH (security_barrier=true) AS
SELECT id,
       org_id,
       user_id,
       token_id,
       active_org_roles,
       realm_roles,
       device_fp,
       ip,
       ua_hash,
       minted_at
  FROM entitlement_snapshot;

REVOKE SELECT ON TABLE "case", artifact, qa_log, delivery_receipt FROM udocket_app;
GRANT  SELECT ON case_secure, artifact_secure,
                  qa_log_secure, delivery_receipt_secure,
                  entitlement_snapshot_secure
       TO udocket_app;
GRANT USAGE ON SCHEMA public TO udocket_app;

-- Guardian secure view exposure defined in `../services/guardian.md`.
```

### J.8 Partitioning and rotation (illustrative)

```sql
ALTER TABLE audit_event PARTITION BY RANGE (created_at);
CREATE TABLE audit_event_2025_01 PARTITION OF audit_event
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE delivery_receipt_2025_01 PARTITION OF delivery_receipt
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

- Ops job `ops/db/rotate_partitions.py` creates upcoming partitions and seals older ones; indexes remain local to each partition to limit bloat.

- Guardian judgment history partitioning and rotations are defined in `../services/guardian.md`.

### J.9 Operational canaries (fail-closed)

```sql
-- Connect guard: verify all GUCs present
SELECT current_setting('udocket.active_org', true) IS NOT NULL
   AND current_setting('udocket.active_user', true) IS NOT NULL
   AND current_setting('udocket.active_roles', true) IS NOT NULL AS rls_context_ok;

-- Boot probe for PgBouncer pooling
-- Expect ERROR unless transaction/session pooling is in use
SELECT 1 FROM "case" WHERE org_id = current_setting('udocket.active_org', true)::uuid;

-- Search-path and timeout guard
SHOW search_path;   -- expect exactly: pg_catalog, public
SHOW statement_timeout; -- expect >= 30s
```

- Integrity queue health probe ensures rows do not accumulate faster than workers drain; alerts fire on backlog age breaches.

### J.10 Integrity scan queue (artifact sweep)

```sql
CREATE TABLE integrity_scan_queue (
  org_id UUID NOT NULL,
  artifact_id UUID NOT NULL,
  enqueued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, artifact_id)
);

INSERT INTO integrity_scan_queue (org_id, artifact_id)
VALUES (:org_id, :artifact_id)
ON CONFLICT DO NOTHING;

SELECT artifact_id
  FROM integrity_scan_queue
 FOR UPDATE SKIP LOCKED
 LIMIT :batch;
```

- Workers quarantine via Guardian (`/api/v1/guardian/quarantine`) and remove rows once reconciled; metrics track backlog size and age.

### J.11 Download tokens (signed URL guard)

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

- Fetch logic requires this update to succeed before streaming, then validates artifact status (`APPROVED` or `RELEASED` as appropriate), SHA match, region allowlists, and audit logging.

______________________________________________________________________

## Appendix K — Controls assurance map

*Purpose: Link external controls (SOC 2, ISO 27001, internal policies) to evidence inside this TDD.*

Quick crosswalk (illustrative)

| Control family    | See                    |
| ----------------- | ---------------------- |
| SOC2 CC1 / ISO 5  | §2, §15.3, App.S       |
| SOC2 CC6 / ISO 9  | §4, App.J              |
| SOC2 CC7 / ISO 12 | §12, §14.5, Appendix H |
| SOC2 CC8 / ISO 14 | §3.2, §12.5, App.L     |
| SOC2 PI / ISO 18  | §2.2, §14.2, App.N     |
| Vendor CUECs      | §3.7, §8, App.Q        |

HMAC key inventory

| Service → Service | Key ID                   | Last rotated (UTC) | Evidence bundle                                      |
| ----------------- | ------------------------ | ------------------ | ---------------------------------------------------- |
| web → guardian    | `svc-web-guardian-v3`    | 2025-09-12T14:30Z  | `ops/security/key_rotation/guardian_2025-09-12.json` |
| worker → settings | `svc-worker-settings-v4` | 2025-08-01T09:00Z  | `ops/security/key_rotation/settings_2025-08-01.json` |
| guardian → signer | `svc-guardian-signer-v2` | 2025-07-18T16:45Z  | `ops/security/key_rotation/signer_2025-07-18.json`   |

Key rotation calendar (rolling 90 days)

| Upcoming rotation        | Owners                                 | Window                  | Notes                                                        |
| ------------------------ | -------------------------------------- | ----------------------- | ------------------------------------------------------------ |
| `svc-web-guardian-v4`    | Security Eng Lead, Platform SRE        | 2025-12-05 → 2025-12-07 | Requires APP.SEC-117 approval; pre-stage secret in Key Vault |
| `svc-worker-settings-v5` | Settings Service TL, Security Eng Lead | 2026-01-08 → 2026-01-10 | Align with Settings deploy freeze lift                       |

| Control ID / Policy        | Scope                      | Primary coverage (Section/App)                         | Evidence artifact(s)                                                                                                                                                                             | Status |
| -------------------------- | -------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| SOC2 CC1.1 / ISO 5.1       | Governance & principles    | §2 Core principles; §15.3 Risks                        | App.K map, App.O waivers ledger, decision log exports                                                                                                                                            | Pass   |
| SOC2 CC6.x / ISO 9         | Access control             | §4 Identity & RLS; App.J SQL policies                  | `case_secure`/`artifact_secure` views, Settings activation audit trail ([`../services/settings-registry.md Appendix A`](../services/settings.md#appendix-a-settings-key-map-traceability-index)) | Pass   |
| SOC2 CC7.x / ISO 12        | Operations & change        | §12 Observability; §14.5 Change mgmt                   | `../ops/runbooks/index.md` runbooks, Guardian/Signer synthetics, deployment playbooks                                                                                                            | Pass   |
| SOC2 CC8.x / ISO 14        | Availability & resilience  | §3.2 topology; §12.5 capacity                          | App.L benchmarks, autoscaling dashboards, synthetic monitor reports                                                                                                                              | Pass   |
| SOC2 PI1 / ISO 18          | Privacy & retention        | §2.2 regulatory constraints; §14.2 retention           | App.N privacy traceability matrix, DPIA/ROPA artifacts                                                                                                                                           | Pass   |
| SOC2 CUEC / Vendor reviews | Third-party oversight      | §3.7 external integrations; §8 LLM governance          | Provider registry health logs, evidence store envelopes, vendor reassessment checklist                                                                                                           | Pass   |
| Internal POL-SC-01         | Security incident response | §12.3 incident workflows; §14.9 disclosure             | Incident register exports, security.txt contact, on-call rotation docs                                                                                                                           | Pass   |
| Internal POL-DS-02         | Data residency             | §3.8 region enforcement; §7.1 Guardian judgments       | Egress AuthorizationPolicy manifests, App.O waiver entries, ops logs `RESIDENCY_POLICY_BLOCK`                                                                                                    | Pass   |
| Internal POL-AU-01         | Audit & approvals          | §10 API contracts; §11 approvals UX                    | Guardian history, audit_event partitions, reviewer swap algorithm logs                                                                                                                           | Pass   |
| Internal POL-BCP-03        | Business continuity        | §12.10 BCP drills; `../ops/runbooks/index.md` runbooks | `BCP_DRILL_REPORT` artifacts, incident templates                                                                                                                                                 | Pass   |

Controls mapped here drive quarterly evidence reviews. Each entry references runbooks, dashboards, or artifacts cited in the final column; missing evidence must be captured before release sign-off.

______________________________________________________________________

## Appendix L — Benchmark baselines

*Purpose: Capture recent performance and cost baselines that back the documented SLOs.*

| Workload                      | Date (UTC) | Load profile                            | P50 / P95 latency    | Cost / tokens | Source                                                                    |
| ----------------------------- | ---------- | --------------------------------------- | -------------------- | ------------- | ------------------------------------------------------------------------- |
| Web API (`GET /api/v1/cases`) | 2025-09-30 | 1k virtual users, 50 RPS step           | 0.112 s / 0.238 s    | n/a           | k6 run `benchmarks/api_caselist.json`, Grafana `web_http_latency_seconds` |
| Guardian judgment decision    | 2025-10-05 | 500 concurrent submissions, 5k/day      | 48 s / 242 s         | n/a           | Synthetic job `guardian_slo.yaml`, `guardian_judgment_latency_seconds`    |
| Compose client deliverable    | 2025-10-11 | Transcript 9k tokens, default templates | 8.3 min / 21.4 min   | 58k tokens    | LangGraph harness `compose_benchmark.py`, `llm_cost_estimate_total`       |
| Analyze summary lane          | 2025-10-11 | Transcript 9k tokens, 4 exhibits        | 6.1 min / 13.7 min   | 42k tokens    | LangGraph harness `analyze_benchmark.py`, `agent_lane_duration_seconds`   |
| Portal DOCX download 25 MB    | 2025-09-28 | 500 clients, CDN disabled               | 310 ms / 480 ms TTFB | n/a           | Locust scenario `portal_download.py`, Nginx access logs                   |

Benchmarks run at least quarterly and after significant infra upgrades using the dedicated synthetic suite (`tests/synthetic/perf/*`). Results update App.L and dashboards referenced in §12.6; deviations ≥10% trigger review prior to release, with raw outputs archived under `ops/perf/<date>/`.

______________________________________________________________________

## Appendix M — Environment & dependency matrix

*Purpose: Document supported platform versions per environment and upgrade cadence.*

| Component                | Dev/Staging | Production | Upgrade policy                                                | Notes                                                                                                                                                       |
| ------------------------ | ----------- | ---------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Kubernetes               | 1.29        | 1.28       | Minor upgrades every 6 months; patch monthly                  | Managed AKS clusters with PodSecurity restricted profile; next prod upgrade Q1 2026; baseline CIS AKS v1.29                                                 |
| Docker Compose (dev)     | 2.24.x      | n/a        | Follow Docker Desktop GA; pin via `.docker/compose-version`   | Required for local parity stack (`docker compose up --build`); validated weekly via CI smoke; includes Postgres, Redis, Guardian, Signer, Settings, workers |
| Service mesh (Istio)     | 1.21.1      | 1.20.4     | N-1 support; canary namespace before prod rollout             | mTLS enforced cluster-wide; cert TTL 24h; last prod bump Jul 2025; next cadence review Apr 2026                                                             |
| Postgres                 | 15.6        | 15.6 HA    | Major every 18 months; logical replication for blue/green     | Patroni-managed; statement pooling disabled; HA failover drills quarterly                                                                                   |
| Redis                    | 7.2         | 7.2        | Patch quarterly; persistence `aof` for broker, none for cache | Managed Azure Cache for Redis Enterprise; last review Aug 2025; next review Feb 2026                                                                        |
| Python runtime           | 3.12.x      | 3.12.x     | Security releases within 30 days                              | Pinned in `Dockerfile` & dependency locks; min supported 3.11 for tooling; deprecation notice 90 days prior                                                 |
| Node.js (build)          | 20.x LTS    | 20.x LTS   | Upgrade within 45 days of LTS patch                           | Build-time only; no runtime exposure; Node 18 blocked since 2025-07                                                                                         |
| Terraform                | 1.8.x       | 1.8.x      | Upgrade quarterly with module pin review                      | State stored in Terraform Cloud; nightly drift detection; drift incidents logged in Appendix H                                                              |
| Nginx ingress controller | 1.11.x      | 1.10.x     | Patch monthly; major with Kubernetes cadence                  | TLS 1.3 preferred; OCSP stapling enabled; Mar 2025 upgrade closed; next upgrade window Jan 2026                                                             |
| Base OS images           | Debian 12   | Debian 12  | Rebuild monthly or on critical CVE                            | Images signed; SBOM generated per build; CIS benchmark level 1 enforced                                                                                     |

Upgrade windows recorded in the change calendar; App.M supports audit inquiries regarding environment parity and upcoming rollouts.

______________________________________________________________________

## Appendix N — Privacy controls traceability

*Purpose: Provide a single view from regulatory obligations to settings, gates, and evidence.*

| Obligation (Reg / Article)                  | Settings / gates                                                                                            | Enforcement point                                          | Evidence artifacts                                                                      |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Data residency (PIPEDA s.17, GDPR Art.44)   | `regions.allowlist.*`, `integrity.downstream_action`                                                        | Guardian residency checks (§3.8, §7.1.1)                   | AuthorizationPolicy manifests, ops `RESIDENCY_POLICY_BLOCK` logs, App.O waivers         |
| DPIA / RoPA maintenance (GDPR Art.35/30)    | `privacy.dpia.*`, `privacy.ropa.*`                                                                          | Privacy activation workflow (§9.3)                         | DPIA/ROPA artifacts, audit seals, App.K mapping                                         |
| HIPAA override mode (HIPAA section 164.312) | `privacy.hipaa.enabled`, `security.mfa.webauthn_required_roles`, `evidence_store.redacted_excerpts.enabled` | Dual approval (§9.11), Guardian/portal guards              | HIPAA manifest entries, audit events, QA logs                                           |
| Legal hold & retention (GDPR Art.5, CPPA)   | `privacy.legal.matrix_version`, `compliance.erasure_mode`                                                   | Destruction job approval (§14.2), DSAR scheduler (§14.2.1) | `DESTRUCTION_CERT`, `ERASURE_JOURNAL`, secure views showing masked reasons              |
| DSAR / erasure fulfillment (GDPR Art.17)    | `compliance.subject_hkdf_salt`, `compliance.erasure_mode`                                                   | DSAR operations runbook (§14.2.1)                          | Ops logs, audit events `DSAR_ERASURE_EXECUTED`, Appendix H drills                       |
| Masking & field protection (SOC2 CC6.6)     | `field_mask_rule`, `security.field_encryption.*`                                                            | Secure views (§4.5) and encryption routines (§4.5)         | Masking helper tests, encryption key rotation records                                   |
| Client portal delivery (PIPEDA Safeguards)  | `portal.download.rate_limits.*`, `compose.policy.forbidden_patterns[]`                                      | Guardian readiness + portal invalidation (§11.2.1)         | Portal invalidation SSE events, QA reports, `../ops/runbooks/index.md (RB-ETAG)` output |

Matrix reviewed quarterly with Privacy & Security; updates required whenever referenced settings or obligations change.

______________________________________________________________________

## Appendix O — Active waivers ledger

*Purpose: Track approved temporary deviations (residency, security, privacy) with expiry and owners.*

| Waiver ID | Category | Scope | Approved by | Effective / Expiry | Conditions | Status            |
| --------- | -------- | ----- | ----------- | ------------------ | ---------- | ----------------- |
| (none)    | —        | —     | —           | —                  | —          | No active waivers |

Process: waiver requests originate via Settings activation metadata or incident response; Security + Architecture approvals required. Entries mirror App.K controls evidence and must include remediation plans before expiry. Stale waivers trigger §12.3 incident workflow.

Waiver template (JSON, all fields required)

```json
{
  "waiver_id": "WAIVER-0001",
  "category": "residency",
  "scope": {
    "org_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "case_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb|null",
    "settings_key": "regions.allowlist.compute"
  },
  "justification": "string",
  "approved_by": ["Security Engineering Lead", "Architecture Lead"],
  "effective_at": "RFC3339",
  "expires_at": "RFC3339",
  "conditions": ["Weekly review", "Guardian manifest flag"],
  "evidence_bundle": "ops/waivers/WAIVER-0001.json"
}
```

### Risk acceptances (time-boxed)

*Purpose: Track temporary risk acceptances, owners, and expiry dates.*

| Acceptance ID | Risk description | Owner | Mitigation / Monitoring | Accepted until | Status                   |
| ------------- | ---------------- | ----- | ----------------------- | -------------- | ------------------------ |
| (none)        | —                | —     | —                       | —              | No open risk acceptances |

Risk acceptances capture deviations such as pending CVE remediation or temporary SLO relaxations. Entries require Security + Product approval, explicit expiry, and linkage to incident/problem tickets. Items auto-escalate to leadership if not reviewed 7 days before expiry.

______________________________________________________________________

## Appendix P — Third-party & OSS notices

*Purpose: Centralize licensing, attribution, and notice obligations for distributed software.*

| Component / Package      | License      | Notice location              | Additional obligations                                |
| ------------------------ | ------------ | ---------------------------- | ----------------------------------------------------- |
| Django                   | BSD-3-Clause | `licenses/django/LICENSE`    | Include copyright notice in customer-facing docs      |
| Celery                   | BSD-3-Clause | `licenses/celery/LICENSE`    | Provide acknowledgement in operator manual            |
| Azure SDKs               | MIT          | `licenses/azure-sdk/LICENSE` | No attribution required; note data use terms in App.Q |
| LangGraph                | Apache-2.0   | `licenses/langgraph/LICENSE` | Preserve NOTICE text in redistributed binaries        |
| ffmpeg                   | LGPL-2.1     | `licenses/ffmpeg/NOTICE`     | Dynamic linking only; provide source offer on request |
| openpyxl                 | MIT          | `licenses/openpyxl/LICENSE`  | None                                                  |
| Company-specific scripts | Proprietary  | `licenses/custom/README.md`  | Internal use only; no redistribution without approval |

Process: SBOM generation (§13.6) cross-checks license metadata nightly; discrepancies raise `LICENSE_GAP` alerts. Updated notices shipped in `NOTICE.md` alongside release artifacts.

______________________________________________________________________

## Appendix Q — Sub-processors & DPAs

*Purpose: List sanctioned data processors, residency posture, and contractual guarantees.*

| Provider                       | Service                          | Region(s) in scope                              | Data classes processed                     | DPA/Terms highlights                                                                                               |
| ------------------------------ | -------------------------------- | ----------------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| Microsoft Azure Speech         | Transcription (batch/on-demand)  | Org allowlisted Azure regions (e.g., eu-west-2) | Audio uploads, transcript text             | DPA §3 forbids training on customer data; residency pinned to selected region; 30-day deletion                     |
| Microsoft Azure OpenAI         | LLM inference                    | Org allowlisted Azure regions (mirror Speech)   | Prompt excerpts (redacted), generated text | Enterprise agreement disables logging & training; retention ≤ 24h; residency anchored to allowlist                 |
| Entrust TSA / OCSP             | Timestamping & revocation        | Global (per org trust bundle)                   | Hashes, certificate metadata               | No content retention; logs retained 90 days for audits; trust roots mapped to Appendix F                           |
| Twilio SendGrid (optional)     | Email delivery                   | Org-selected sub-account region (NA/EU/APAC)    | Notification metadata, recipient email     | Data residency restriction via regional sub-account; logs 30 days                                                  |
| Telnyx                         | SMS delivery                     | Org-selected region (NA/EU/APAC)                | Phone numbers, message metadata            | Opt-out enforcement, no content mining; residency documented in waiver ledger                                      |
| Speechmatics Canada (fallback) | Automated transcription fallback | ca-central-1 (org allowlisted)                  | Audio uploads, transcript text             | DPA mirrors Azure terms; retention ≤ 24 h; audited equivalence harness ensures WER/diarization parity with primary |

All sub-processors contractually commit to “no training on customer prompts/outputs” clauses. Annual review ensures residency alignment; updates trigger customer notification per §12.3.

Vendor monitoring: Compliance subscribes to provider trust-center feeds (Azure, SendGrid, Telnyx) and maintains a quarterly calendar reminder to review policy updates. Appendix Q entries include `last_reviewed_at` metadata in the waiver ledger; deviations raise `VENDOR_POLICY_CHANGE` audit events and prompt Architecture/Security sign-off before continuing usage.

______________________________________________________________________

## Appendix R — Data lineage maps

*Purpose: Provide visual traceability from inputs to signed deliverables.*

### R.1 Artifact lineage overview

- Mermaid diagram `overview/tdd/diagrams/data-lineage-v1.mmd` showing flow from audio/exhibits → Transcribe artifacts → Analyze outputs → Compose deliverables → Guardian → Signer → Portal.

### R.2 UUID provenance

- Table mapping deterministic UUID anchors (transcript spans, timeline events) to downstream artifacts; generated via `scripts/lineage/export_uuid_map.py`.

### R.3 Audit linkage

- Describes how manifests reference `settings_snapshot_sha256`, upstream artifact IDs, and Guardian judgment IDs; includes example JSON in `docs/examples/lineage/compose_client.json`.

### R.4 Worked example

- `docs/examples/lineage/transcript_to_compose.json` shows `TRANSCRIPT` → `SUMMARY_MD` → `COMPOSE_CLIENT_DOCX` lineage with manifest snippets (`source.inputs`, `provenance.tool_versions`, Guardian judgment ID) and matching audit events.
- Lineage diagrams must be regenerated with each schema/manifest change; CI `diagram:diff` gate (§13.8) verifies updates. Auditors can cross-check lineage by loading `LINEAGE_REPORT` artifacts produced during quarterly controls testing.

______________________________________________________________________

## Appendix S — Ownership & RACI map

*Purpose: Clarify accountability for each major area documented in this TDD.*

| Domain / Section           | Responsible                | Accountable             | Consulted                    | Informed                  |
| -------------------------- | -------------------------- | ----------------------- | ---------------------------- | ------------------------- |
| Agent pipelines (§6)       | Platform AI Lead           | Director of Engineering | QA Lead, Product             | Support, Customer Success |
| Guardian & Signer (§7)     | Security Engineering Lead  | CISO                    | Platform Architecture, Legal | Support, Customer Success |
| LLM governance (§8)        | AI Governance Lead         | CTO                     | Security, Privacy Officer    | Product, Customer Success |
| Settings platform (§9)     | Platform Architecture Lead | Director of Engineering | Security, QA                 | Support                   |
| APIs & Integrations (§10)  | API Engineering Manager    | Director of Engineering | Product, Support             | Customers (release notes) |
| Frontend & Portal (§11)    | UX Engineering Manager     | VP Product              | Accessibility SME, Support   | Customer Success          |
| Observability & Ops (§12)  | SRE Manager                | VP Engineering          | Security, Product            | Support, Customers        |
| Quality & Compliance (§13) | QA Manager                 | VP Engineering          | Security, Privacy            | Product, Customers        |
| Operations lifecycle (§14) | Operations Lead            | COO                     | Security, Legal              | Customer Success          |
| Roadmap & governance (§15) | Product Strategy Lead      | VP Product              | Architecture, Security       | All teams                 |

RACI reviewed every release train; updates recorded in decision log (§15.3) and mirrored in internal handbook.

- Mesh-controlled pods allow egress only to cluster DNS and the Istio egress gateway; the gateway enforces external destinations via the AuthorizationPolicy allowlist above. Namespaces without the mesh label can define their own policies, but production workloads inherit this baseline.

______________________________________________________________________

## Appendix T — Traceability matrix

*Purpose: Tie requirements to validation, observability, and operational response so audits stay frictionless.*

| Requirement (section)                                                                | Tests / validation artifacts                                                                                                                                                                                 | Monitors / alerts                                                                                                                       | Runbook / response                                                                                                                                        |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Guardian judgments deterministic & parent-aware (§7.1)                               | `tests/guardian/test_concurrent_parent_swap.py::test_child_blocks_on_parent_swap`; Guardian synthetic `guardian_slo.yaml` job                                                                                | `guardian_cleared_ratio`, `guardian_judgment_latency_seconds`, `guardian_parent_block_total`                                            | Appendix B.1, Appendix B.2                                                                                                                                |
| API versioning & Sunset policy enforced (§10.0, §10.5)                               | `make lint-openapi` (`npx spectral lint ops/openapi/**/*.yaml`), Spectral `sunset-header` rule, ADR-0003 change review checklist                                                                             | `api_sunset_header_missing_total`, `api_deprecation_notice_age_seconds`                                                                 | `../ops/runbooks/index.md` standard runbook template → API Sunset (`docs/runbooks/api/sunset.md`, draft)                                                  |
| FinOps guardrails prevent runaway spend (§8.7, §12.9)                                | `scripts/finops/check_mom_guard.py`; `tests/udocket_core/finops/test_guard.py::test_regression_formula`                                                                                                      | `finops_mom_regression_flag{org}`, `llm_cost_estimate_total`                                                                            | [Runbook RB-LLM-003](../ops/runbooks/index.md#rb-llm-003)                                                                                                 |
| Logging pipeline retains structured records (§12.1)                                  | `tests/logging/test_redaction.py::test_forbidden_headers_masked`; `diagram:diff` for log schema                                                                                                              | `logging_ingest_lag_seconds`, `logging_drop_rate_pct`, `logging_spool_utilization_pct`                                                  | `../ops/runbooks/index.md (RB-LOG-007)`                                                                                                                   |
| Advisory locks stay healthy during approvals (§5.4)                                  | `tests/platform/artifacts/test_approval_swap.py::test_concurrent_approvals_single_winner`; `tests/platform/db/test_rls_guard.py::test_rls_context_asserts_missing_gucs`                                      | `udlock_watchdog_stale_total`, `udlock_lock_age_seconds_p95`                                                                            | [Runbook RB-LOCK-006](../ops/runbooks/index.md#rb-lock-006)                                                                                               |
| Portal downloads honor ETag / If-Match (§10.6, `../ops/runbooks/index.md (RB-ETAG)`) | `tests/e2e/test_artifact_range_download.py::test_range_and_conditional_gets`                                                                                                                                 | `portal_412_precondition_total`, `alert_portal_412_spike`                                                                               | `../ops/runbooks/index.md (RB-ETAG)`                                                                                                                      |
| Abuse-prevention detectors enforce throttles (§B.4, §6.13, §10.9)                    | `tests/security/test_abuse_checks.py::test_api_abuse_flagged`, `tests/security/test_portal_download_guard.py::test_anomaly_blocks`, shadow soak fixtures (`tests/platform/shadow/test_shadow_thresholds.py`) | `api_suspect_request_total`, `portal_download.anomaly_score`, `messaging_abuse_detected_total`, `abuse_shadow_threshold_expiring_total` | [Runbook RB-RES-BLOCK](../ops/runbooks/index.md#rb-res-block) (residency), `../ops/runbooks/index.md (RB-ETAG)`, `docs/runbooks/security/abuse_triage.md` |
| Masking profiles map to FORCE RLS policies (§4.4.1)                                  | `tests/platform/db/test_mask_profiles.py::test_mask_profile_matches_policy`, `tests/platform/db/test_secure_view_usage.py::test_no_base_table_queries`                                                       | `rls_context_missing_total`, `mask_profile_mismatch_total`                                                                              | [Runbook RB-GOV-008](../ops/runbooks/index.md#rb-gov-008) (settings rollback), [Runbook RB-LOCK-006](../ops/runbooks/index.md#rb-lock-006)                |
| LLM/vector residency guard prevents out-of-region fallback (§8.1.1)                  | `tests/udocket_core/llm/test_residency_guard.py::test_block_disallowed_region`, `tests/udocket_core/vector/test_vector_residency.py::test_allowed_regions_only`, synthetic `synthetics/llm_residency.yaml`   | `llm_region_fallback_total`, `vector_region_fallback_total`                                                                             | [Runbook RB-LLM-003](../ops/runbooks/index.md#rb-llm-003), [Runbook RB-RES-BLOCK](../ops/runbooks/index.md#rb-res-block)                                  |
| CSP nonce & HIPAA cache enforcement (§11.5, §10.6)                                   | `tests/ui/test_csp_nonced.py::test_nonce_roundtrip`, synthetic `synthetics/csp_nonce_failure.yaml`, `synthetics/portal_hipaa_cache.yaml`, `tests/e2e/test_portal_policy_context.py::test_disclaimer_l10n`    | `csp_nonce_mismatch_total`, `portal_cache_header_violation_total`                                                                       | `../ops/runbooks/index.md (RB-PORTAL-005)`, Appendix H security headers checklist                                                                         |

______________________________________________________________________

## Appendix U — Reference code snippets (normative)

*Purpose: Centralise authoritative code examples so sections can reference stable, linted artifacts without duplicating snippets.*

### U.1 Analyze agent schema (Pydantic)

*Purpose: Show the canonical Analyze agent schema that downstream code must satisfy.*

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SourceSpan(BaseModel):
    start_ms: int
    end_ms: int


class AnalyzeEvent(BaseModel):
    id: UUID
    title: str
    datetime: datetime | None = None
    participants: list[UUID] = Field(default_factory=list)
    source_spans: list[SourceSpan] = Field(default_factory=list)
    notes: str | None = None


class AnalyzeIssue(BaseModel):
    id: UUID
    label: str
    description: str
    related_events: list[UUID] = Field(default_factory=list)
    risk: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
```

### U.2 Compose agent schema (Pydantic)

*Purpose: Present the Pydantic model governing Compose artifacts.*

```python
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ComposeSection(BaseModel):
    key: str
    title: str
    body_md: str
    references: list[UUID] = Field(default_factory=list)


class ComposeDocument(BaseModel):
    doc_type: Literal["CLIENT", "LAWYER"]
    language: str | None = None
    sections: list[ComposeSection]
    outline: list[str]
    analyze_refs: dict[str, list[UUID]] = Field(default_factory=dict)
```

### U.3 Settings definition model (Pydantic)

*Purpose: Document the schema used to validate Settings definitions.*

```python
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class SettingDefinition(BaseModel):
    key: str
    datatype: Literal["BOOL", "INT", "FLOAT", "STRING", "DURATION", "ENUM", "JSON", "REGION", "PERCENT"]
    enum_values: list[str] | None = None
    default_value: Any
    mutable_scope: list[Literal["SYSTEM", "ORG", "CASE"]]
    validation_schema: dict[str, Any] | None = None
```

### U.4 SSE event payloads (JSON)

*Purpose: Provide reference payloads for SSE topics used across the platform.*

- `job.update`

  ```json
  {
    "id": "1024",
    "event": "job.update",
    "data": {
      "schema_version": "1",
      "emitted_at": "2025-10-19T21:11:58Z",
      "job_id": "...",
      "case_id": "...",
      "org_id": "...",
      "status": "RUNNING",
      "progress": 64,
      "warning": null
    }
  }
  ```

- `job.canceling`

  ```json
  {
    "id": "1025",
    "event": "job.canceling",
    "data": {
      "schema_version": "1",
      "emitted_at": "2025-10-19T21:12:02Z",
      "job_id": "...",
      "case_id": "...",
      "org_id": "...",
      "actor_id": "...",
      "reason": "Operator requested cancel"
    }
  }
  ```

- `job.canceled`

  ```json
  {
    "id": "1026",
    "event": "job.canceled",
    "data": {
      "schema_version": "1",
      "emitted_at": "2025-10-19T21:12:08Z",
      "job_id": "...",
      "case_id": "...",
      "org_id": "...",
      "actor_id": "...",
      "reason": "Operator requested cancel",
      "provider_outcome": "azure_speech:deleted"
    }
  }
  ```

- Optional fields include `progress` (0-100), `warning` (`"NO_PROGRESS"`, `"CAPACITY_THROTTLED"`, `"BUDGET_HELD"`, etc.), and `provider_progress` (`{ "phase": "transcribing", "percent_complete": 42, "estimated_remaining_seconds": 310 }`) when adapters surface granular provider telemetry.

- `artifact.status`

  ```json
  {
    "id": "1030",
    "event": "artifact.status",
    "data": {
      "schema_version": "1",
      "emitted_at": "2025-10-19T21:12:00Z",
      "artifact_id": "...",
      "case_id": "...",
      "org_id": "...",
      "type": "SUMMARY_MD",
      "status": "APPROVED",
      "previous_status": "APPROVAL_REQUESTED"
    }
  }
  ```

- `portal_link_invalidated`

  ```json
  {
    "id": "1035",
    "event": "portal_link_invalidated",
    "data": {
      "schema_version": "1",
      "emitted_at": "2025-10-19T21:14:00Z",
      "artifact_id": "...",
      "case_id": "...",
      "reason": "APPROVAL_SWAP"
    }
  }
  ```

- Snapshot bootstrap payload (truncated)

  ```json
  {
    "id": "snapshot",
    "event": "artifact.snapshot",
    "data": {
      "schema_version": "1",
      "emitted_at": "2025-10-19T21:14:00Z",
      "watermark_ts": "2025-10-19T21:14:00Z",
      "events": [
        { "schema_version": "1", "emitted_at": "2025-10-19T21:10:00Z", "artifact_id": "...", "status": "OPERATOR_PREP" },
        { "schema_version": "1", "emitted_at": "2025-10-19T21:11:00Z", "artifact_id": "...", "status": "APPROVAL_REQUESTED" },
        { "schema_version": "1", "emitted_at": "2025-10-19T21:11:30Z", "artifact_id": "...", "status": "QUEUED_FOR_REVIEW" },
        { "schema_version": "1", "emitted_at": "2025-10-19T21:12:00Z", "artifact_id": "...", "status": "APPROVED" }
      ]
    }
  }
  ```

### U.5 Staff UI job status widget (TypeScript/React)

*Purpose: Illustrate the canonical React implementation of the job status ticker.*

```tsx
import { useEffect, useState } from "react";

type JobStatus =
  | "PENDING"
  | "RUNNING"
  | "PAUSED"
  | "PAUSED_AWAITING_PROVIDER"
  | "PAUSED_AWAITING_BUDGET"
  | "CANCELING"
  | "FAILED"
  | "COMPLETED"
  | "CANCELED";

interface JobUpdatePayload {
  schema_version: string;
  emitted_at: string;
  job_id: string;
  status: JobStatus;
  progress?: number;
  warning?: string | null;
}

interface JobCancelPayload {
  schema_version: string;
  emitted_at: string;
  job_id: string;
  actor_id?: string;
  reason: string;
}

export function JobStatusTicker({ jobId }: { jobId: string }) {
  const [status, setStatus] = useState<JobStatus>("PENDING");
  const [progress, setProgress] = useState<number | null>(null);

  useEffect(() => {
    const source = new EventSource(`/api/v1/jobs/${jobId}/events`, { withCredentials: true });

    const onEvent = (event: MessageEvent<string>) => {
      const payload = JSON.parse(event.data) as Partial<JobUpdatePayload & JobCancelPayload>;
      if (payload.job_id !== jobId) return;

      switch (event.type) {
        case "job.update": {
          const update = payload as JobUpdatePayload;
          setStatus(update.status);
          setProgress(typeof update.progress === "number" ? update.progress : null);
          break;
        }
        case "job.canceling": {
          setStatus("CANCELING");
          setProgress(null);
          break;
        }
        case "job.canceled": {
          setStatus("CANCELED");
          setProgress(null);
          break;
        }
        default:
          break;
      }
    };

    source.addEventListener("job.update", onEvent);
    source.addEventListener("job.canceling", onEvent);
    source.addEventListener("job.canceled", onEvent);
    source.onerror = () => source.close();

    return () => {
      source.removeEventListener("job.update", onEvent);
      source.removeEventListener("job.canceling", onEvent);
      source.removeEventListener("job.canceled", onEvent);
      source.close();
    };
  }, [jobId]);

  return (
    <output role="status" aria-live="polite" data-status={status.toLowerCase()}>
      <strong>{status}</strong>
      {progress !== null ? ` — ${progress}%` : ""}
    </output>
  );
}
```

- `provider.health`

  ```json
  { "id": "1040", "event": "provider.health", "data": { "schema_version": "1", "provider": "azure_speech", "region": "canadacentral", "status": "HEALTHY", "latency_ms_p95": 2100, "last_heartbeat": "2025-10-19T21:13:00Z" } }
  ```

  Aggregates `ProviderProgressAdapter` heartbeats so operators see upstream availability next to job progress.
