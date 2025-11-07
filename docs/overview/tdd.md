---
title: uDocket — Technical Design Document
subtitle: Platform Architecture & Compliance Specification
author:
  - uDocket Platform Architecture Team
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Architecture
  - Security Engineering
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

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | uDocket Platform Architecture Team |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Architecture; Security Engineering |
| Reviewers | QA Engineering Lead; SRE Manager |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by | |
| Approved date | |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

## Canonical vocabulary (binding)

**Breadcrumbs:** Implementation `packages/core/artifacts/status.py`, Tests `tests/platform/artifacts/test_status_vocab.py::test_all_statuses_linked`, Observability Grafana “Docs Quality – Vocabulary Drift”.

*Purpose: Provide single-source wording for artifact classes, statuses, and Guardian mappings so specs, code, and UI stay aligned.* *Contract: Any change to artifact classes, statuses, or Guardian judgment mappings MUST update §5.2.1–§5.2.3 and this section in the same patch; other sections link back instead of restating tables. See Appendices: Glossary and Status Mapping for single‑source definitions.* *State transitions: Defined exclusively in §5.2.2 (statuses) and §5.2.3 (Guardian mapping).* *Failure modes & retries: `python -m doc_tools.check_structure docs/overview docs/platform docs/automation docs/data docs/customer docs/experience` now fails when a normative section lacks Purpose/Breadcrumbs scaffolding; `scripts/db/lint_status_column.py` blocks unknown status strings; CI job `lint-artifact-vocabulary` scans diffs for stray status/judgment terms.* *Observability: Docs lint metrics (`docs_template_missing_total`, `docs_vocabulary_drift_total`) feed the Docs Quality dashboard; Guardian and approval metrics remain unchanged.* *References: §5.2, §5.4.1, §7.1, §10.3.2, App.A, App.I.*

### Artifact classes (authoritative definitions)

| Class | Key | Canonical definition | Visibility |
|---|---|---|---|
| Source Asset | **SA** | Raw, immutable inputs we ingest. | Staff (scoped) |
| Work Product | **WP** | Internal derived data never exposed to clients. | Staff only |
| Candidate Deliverable | **CD** | Human-readable draft that may be released after approval. | Staff reviewers/ops |
| Deliverable | **DL** | Approved, signed, client-visible document. | Staff + client |
| Auxiliary Record | **AR** | Attestations/receipts that prove what happened. | Auditors/admin |

### Canonical statuses (link to §5.2.2)

- `STORED → PROCESSING → PENDING_JUDGMENT` (SA → WP/CD) with deterministic transitions enumerated in §5.2.2.
- Guardian PASS/WARN moves WP → `CLEARED_FOR_USE` and CD → `OPERATOR_PREP`; review queue states (`APPROVAL_REQUESTED`, `QUEUED_FOR_REVIEW`, `CHANGES_REQUESTED`) apply only to CDs.
- Deliverables follow `APPROVED → SIGNED → RELEASED → REVOKED → ARCHIVED → DELETED` and are subject to the ExclusiveSwap invariant in §5.4.1; transitions into `ARCHIVED/DELETED` only occur through the retention/erasure gate.

### Guardian judgments → statuses (link to §5.2.3)

| Judgment | WP next | CD next | Notes |
|---|---|---|---|
| PASS | CLEARED_FOR_USE | OPERATOR_PREP | default |
| WARN | CLEARED_FOR_USE | OPERATOR_PREP | banners |
| BLOCK | QUARANTINED | QUARANTINED | remediation/waiver |
| WAIVED | as PASS | as PASS | dual approval |

Guardian policy, risk tiers, and remediation flows continue in §5.2.3 and §7.1; other sections cite these tables instead of rephrasing them.

### Definition locks

- No new status or judgment names appear outside §5.2.2–§5.2.3 without an ADR update and a matching lint rule update; CI job `lint-artifact-vocabulary` blocks unknown terms in diffs.
- APIs emit events whose values are exactly the canonical statuses/judgments; payload schemas MUST reference this section instead of inventing aliases.
- Mapping tables live only in §5.2.3. Other sections reference them with `See §5.2.3 (canonical mapping)`.
- Binding breadcrumbs are mandatory for every normative/binding subsection; missing breadcrumbs fail `python -m doc_tools.check_structure docs/overview docs/platform docs/automation docs/data docs/customer docs/experience`.

______________________________________________________________________

## Reading Guide

- **Scope:** Entire platform lifecycle (design → operations → governance).
- **Structure:** Numbered sections with ≤3 levels of depth; appendices mirror section numbers for reference artifacts.
- **Cross-references:** Use `§<number>` for sections and `App.<letter>` for appendices.
- **LLM hint:** Each subsection starts with a one-line purpose statement before implementation details.
- **Maintenance:** Run `python -m doc_tools.manage_docs --lint` (or see `docs/README.md`) before submitting edits to keep references, formatting, and settings keys synchronized with the codebase.
- **Audit integration (2025-10-19):** This draft incorporates audit items for CCPA/CPRA coverage (§2.2, §14.2.1), automated LLM moderation (§8.4), and model version pinning/replay rules (§8.1, §8.5). Settings key coverage and traceability now live in [`Settings Registry – Appendix A`](../platform/settings.md#appendix-a-settings-key-map-traceability-index); CI blocks releases if parity ever drifts.
- **Doc change protocol:** Every PR that modifies regulated behavior (policy, residency, approvals, agents) must link to the corresponding TDD diff; Architecture/Security reviewers block merges when code and spec diverge. Appendix automation (settings map, API snippets) continues to evolve—when feasible, replace manual tables with generated outputs to minimize churn.

**Role-based quick start (binding)**\
Use this checklist to jump to the right sections on a first read:

| Stakeholder role | Start here | Must-review highlights |
|---|---|---|
| Architecture / Security | §3 (platform architecture), §4 (tenancy & access), §7 (Guardian/Signer), §12 (observability/DR) | §3.8 residency, §4.4–§4.5 masking/RLS, §7.1 judgments, §12.5 resilience |
| Engineering (agents & API) | §6 (agent ecosystem), §10 (APIs), App.D (artifact schemas) | §6.2–§6.4 pipelines, §10.3 idempotency, Platform Runtime §3 (API contracts) |
| Product / Operations | §1 (executive summary), §11 (UX), §14 (retention & compliance) | §11.1 workspace/portal behaviors, §14.2 DSAR flows, §15 roadmap checkpoints |
| QA / Compliance | §5 (lifecycle), §13 (testing & governance), App.K (controls map) | §5.2 status vocabulary, §13.3 detection QA, §13.5 deployment gates |
| SRE / Platform Ops | §3 (infra context), §8 (LLM runtime), §12 (observability/DR), [Runbook catalog](../ops/runbooks.md) | §8.7 FinOps guard, §12.4–§12.6 DR & dashboards, `../ops/runbooks.md` |

### Diagram usage standard

To keep visuals helpful and consistent:

- Embed a rendered Mermaid diagram when a section introduces a **core control flow, deployment topology, or data lineage** that spans multiple services (sequence/flowchart).
- Use **ER diagrams** when we describe shared persistence contracts or artifacts that other teams must extend (for example, §9 core domain entities).
- Produce **class diagrams** when detailing important service classes or agent orchestration objects whose inheritance/composition relationships benefit from a visual (limit to high-signal surfaces such as Guardian, Settings activation engine, or core agents).
- Reserve diagrams for bounded topics—avoid trying to capture the entire platform in a single chart; favor appendix references for deep dives (App.A/App.G).
- When behavior changes, update the `.mmd` source under `overview/tdd/diagrams/`, regenerate SVGs via `uv run --project packages/docs_tooling python -m doc_tools.render_mermaid`, and ensure the affected TDD section still references the correct image.

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
- *Service specification:* [`Billing & Subscriptions`](../customer/billing-subscriptions.md) details plan catalog, usage metering, delinquency handling, and FinOps dashboards.
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

- **Availability:** 99.5 % rolling 30 day for staff UI/API; 99.0 % for client portal. Breaches trigger customer notice within 24 h and a public incident postmortem within 5 business days (`../ops/runbooks.md` templates).
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

- SOC 2 / ISO controls: change management, incident response, and logging mapped to specific sections (`§12`, `§12`, [`../platform/settings.md Appendix A`](../platform/settings.md#appendix-a-settings-key-map-traceability-index)); mappings extend to PCI DSS logging, FedRAMP Moderate, and audit retention requirements surfaced in Appendix K.

- Privacy frameworks in scope: GDPR/UK GDPR, CCPA/CPRA, HIPAA (US/BAA-backed workloads), PHIPA, PIPEDA, APP (Australia), LGPD (Brazil), and CPPA (federal). Reference Manager curates policy catalogues (`../data/ref-manager.md §1.2`); Localization & Policy Engine (LPE) compiles them for enforcement (see `../automation/lp-engine.md §2.1`).

- Sensitive Personal Information (SPI): covers CPRA “sensitive personal information”, GDPR Article 9 special categories, and analogous provincial/federal classifications (for example: biometric identifiers, precise geolocation, racial or ethnic origin, religious beliefs, sexual orientation, union membership, genetic data, immigration status, and government identifiers). SPI inherits the platform’s high-security baseline (encryption, residency controls, reviewer accountability). Guardian enforces SPI gating, detection, and waiver flows; see `../platform/guardian.md` for enforcement mechanics.

- CCPA/CPRA specifics: platform does not sell or share personal information; privacy notices and contracts state “no sale/no sharing.” DSAR timelines follow CCPA (45 days, one 45‑day extension with notice) and GDPR (30 days, extensions as allowed). Admin tooling exports DSAR evidence and timelines; audit seals reference the governing framework for each request.

- ISO/IEC 27701 (privacy extension) alignment: fully mapped and implemented. Appendix K lists the control crosswalk, evidence sources, and quarterly recertification cadence; deviations trigger `ISO27701_GAP` incidents and block releases until remediated.

- Compliance mapping (binding): traceable connection between regulation, platform controls, and evidence ensures auditors can verify posture without ad-hoc spreadsheets.

  | Regulation / Framework | Key platform controls & features | Canonical references |
  |---|---|---|
  | GDPR & UK GDPR | DSAR/erasure workflow (`ERASURE_JOURNAL`), data minimization, audit seals, residency enforcement | §2.2, §14.2.1, App.N, App.K |
  | CCPA / CPRA | “No sale/share” enforcement, notice ledgers, SPI routing and disclosure logging | §2.2 (SPI), §11.5, App.K |
  | HIPAA | HIPAA mode activation gates, Guardian PHI quarantine, evidence-store excerpt suppression, WebAuthn enforcement | §2.2, §7.1, §8.2, App.N |
  | SOC 2 (CC6 / CC7) | Audit logging, approvals workflows, change management, monitoring dashboards | §12, §14.5, Appendix H, App.K |
  | ISO/IEC 27001 & 27701 | Security management, retention schedules, risk assessments, policy bundles | §2.2, §12.6, §14, App.K |
  | PIPEDA / CPPA / PHIPA | Residency controls, consent logging, legal hold & retention automation | §2.2, §3.8, §14.2, App.N |

### 2.3 Engineering standards (binding)

*Purpose: codify the coding, typing, linting, and testing rules that keep the agent ecosystem deterministic and auditable.*\
*Contract: every change must satisfy these requirements before review. This section and [`AGENTS.md`](../AGENTS.md#engineering-standards-binding) form the canonical reference; deviations require Architecture approval.*

- **Type-first development.** When editing a module, define the strongly typed primitives upfront (dataclasses, `TypedDict`, `Protocol`, `StrEnum`, wrappers, helpers, stub packages). Provider payloads never travel as untyped dicts; add typed facades or stubs in the same patch.
- **Typing rules.** `typing.Any` is banned in new code and must be removed when touched. Casts are acceptable only to narrow third-party responses and must live inside helper functions with short invariant comments. `# type: ignore` (and lint ignores) are prohibited—fix the root cause or add a typed wrapper. Pyright and mypy run in `--strict` mode for touched packages; CI fails when they fail.
- **Language level.** The repository targets Python ≥3.12 exclusively. Delete compatibility shims, version guards, and legacy syntax when encountered. Prefer modern constructs (`match/case`, `contextlib.asynccontextmanager`, `zoneinfo`, `StrEnum`) and structural pattern matching.
- **Separation of concerns & helper placement.** Entry-point modules validate inputs, snapshot settings, and delegate to typed helpers. Business logic lives in dedicated helpers/models—not Django views or Celery tasks. Framework-agnostic helpers live in `packages/common`; package-scoped helpers live in `utils.py`; inline helpers stay under ten lines. Never mix HTTP, database, and LangGraph orchestration concerns inside one function.
- **Testing & coverage.** Every module maintains ≥90% line coverage (unit + property tests). Deterministic behaviors (UUIDs, manifests, approvals) require property-based tests. Integration suites cover Celery orchestration, Guardian/Signer flows, and settings activation. CI enforces coverage via `make common.test`, `make core.test`, `make platform.test`, `make docs.test.coverage`, and companion jobs.
- **Execution environment.** Run commands via the curated containers/venvs (`make …`, `uv run --project …`). Avoid ad-hoc `pip install`. Docs/spec changes must pass `doc_tools.check_links --strict` and MkDocs builds before merge.
- **Quality over speed.** Restructure when it reduces complexity. Keep functions <40 LOC, keep files cohesive, and remove dead code. No back-compat toggles or “temporary” fallbacks; migrations move forward only.
- **Logging, ops, and docs.** Changes that affect artifacts/logs/settings update manifests, this TDD, and `AGENTS.md`. Ops logging stays additive and deterministic. Guardian/Settings impacts appear in PR descriptions, and doc tooling (`doc_tools.manage_docs --lint`) must remain green.

- HIPAA mode: applies only to U.S. workloads with an executed BAA. Org activation (`privacy.hipaa.enabled=true`) requires dual approval (`org_admin` + platform `sysadmin`), verifies BAA-backed storage and compute, and enforces per-org field encryption (`security.field_encryption.enabled=true`, `security.field_encryption.key_scope='per_org'`) plus WebAuthn for privileged roles (`security.mfa.webauthn_required_roles` includes `org_admin|org_manager|org_operator|org_reviewer`). Settings expose `privacy.hipaa.enforcement_mode ∈ {optional, required}`—`required` is reserved for U.S. orgs under BAA, while `optional` allows voluntary adoption elsewhere. Outside the U.S. HIPAA stays optional; organizations may opt in for contractual reasons, but enforcement defaults to the general SPI/PHI controls unless HIPAA mode is explicitly enabled.

- Guardian-driven enforcement runs entirely within the service; see `../platform/guardian.md` for service-level procedures.

- Baseline enforcement: Reference Manager maintains jurisdiction-specific minimum controls for PII, SPI, and PHI (residency, retention, disclosure logging) as captured in `../data/ref-manager.md §1.4`. `PolicyContext` propagation and runtime policy evaluation live in `../automation/lp-engine.md`; Settings and Guardian rely on those compiled controls when validating or judging artifacts.

- Legal hold and destruction policies align with jurisdictional obligations captured in Appendix C.

- Audit linkage: DPIA/RoPA artifacts, CCPA notice ledgers, and HIPAA override activations are referenced in audit seals (`§14.2`, Appendix N); HIPAA activations require Compliance approval and manifest tagging.

#### 2.3.1 Repository composition decision tree (binding)

*Purpose: keep ownership clear so every module lands in the right home without orphan packages.*\
*LLM hint:* read this tree top-to-bottom before writing code; link back to the relevant bullet in design docs or AGENTS when describing the change.

##### Package placement rules

1. **Does it depend on Django, tenancy, Guardian, LPE, or case storage?**\
   → Keep it in the owning service (`apps/`, `services/…`) or `packages/core` (if it is reusable orchestration). Never move platform-bound logic into reusable packages.
2. **Is it cross-service, policy-aware, and orchestrates agents or runtime flows?**\
   → `packages/core` (LangGraph orchestration, Celery wrappers, ops logging, residency enforcement).
3. **Is it cross-service, provider-neutral, and safe to reuse outside uDocket?**\
   → `packages/ai` (prompt compilers, provider protocols, evaluation harnesses) or `client_sdks/*` for customer-facing APIs.
4. **Is it a low-level helper with zero policy or framework coupling?**\
   → `packages/common` (hashing, UUID derivation, JSON/path/time helpers).
5. **Is it UI-specific or HTTP-facing?**\
   → `apps/web`, `apps/assistants`, or the service directory under `services/…`—never inside agent packages.

##### AI vs core boundary

- `packages.ai` owns provider-agnostic building blocks: typed protocols, prompt registries, localization-aware prompt compilers, evaluation datasets, and adapters gated by optional extras (e.g., `[azure]`).
- `packages.core` wires those building blocks into the platform runtime: LangGraph flows, Celery tasks, Guardian/LPE hooks, ops logging, storage layout, and region guardrails.
- Provider prompts that require policy or tenancy context belong in `packages.core`. Base prompt templates and evaluation harnesses live in `packages.ai`.
- When retiring legacy packages (for example, `packages/ai/promptsets`), migrate reusable assets into `packages.ai` and platform-bound logic into `packages.core` within the same patch.

##### Do / Don’t

- **Do** keep helpers tiny and type-safe; promote them only when at least two services will reuse them within one release cycle.
- **Do** document every placement decision in the PR description (link back to this section) so reviewers can trace the reasoning.
- **Don’t** create micro-packages for single functions or move Django/persistence code into reusable packages.
- **Don’t** let `packages.ai` import Django, Celery, Guardian, or case storage modules—tests must run without the platform stack.
- **Don’t** add toggles for “old behavior.” Refactors are one-way; delete compatibility shims immediately.

#### 2.3.2 Non-functional requirements (SLOs, latency budgets, availability)

*Purpose: Capture performance and reliability expectations.*

- Guardian judgments ≤ 5 minutes P95; Compose jobs complete ≤ 45 minutes P95 under nominal load.
- Service availability: web/channels 99.5%, Guardian 99.9%, Settings API 99.9% (due to policy enforcement criticality).
- LPE availability, compiler latency targets, and deployment windows are defined in `../automation/lp-engine.md §1`; burn-rate policies there govern bundle activations and OPA discovery pushes.
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
  <img class="diagram" data-scale="0.5" src="../build/diagrams/platform/guardian/upload-guardian-approve-v1.svg" alt="Upload → Guardian → Approve happy path">
  <figcaption style="font-size: 0.9em; color: #555;">Upload → Guardian → Approve happy path</figcaption>
</figure>

### 3.1 High-level system context diagram

*Purpose: Orient readers to major components and trust boundaries before diving into detail.*

- Staff users, reviewers, and clients interact with the **Web App** (Django ASGI) via browser connections protected by TLS 1.3; SSE provides status streaming while Channels enables bidirectional collaboration. SSE payloads include only IDs and metadata already permitted by RLS—no raw PII or artifact bodies traverse the channel.
- Background processing occurs in the **Worker cluster** (Celery), which orchestrates agent pipelines, storage operations, notifications, and watchdog automation; see [`../automation/worker-cluster.md`](../automation/worker-cluster.md) for queue topology, failover, and scaling controls.
- Supporting services—**Guardian**, **Digital Signer**, **Settings**, **LLM Registry**, **Localization & Policy Engine (LPE)**, **Reference Manager (RM)**, and **Notifications**—communicate over mTLS within the cluster and persist state to Postgres with RLS. RM operates as the editorial/source-of-truth service for catalog bundles, while LPE is the runtime resolver that consumes those bundles.
- External dependencies (Azure Speech, LLM providers, TSA/OCSP authorities, email/SMS gateways) sit outside the trusted cluster and are accessed under strict egress policies.
- Visual: see `App.A` for the full context diagram and sequence overlays.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/diagrams/overview/tdd/system-context-v1.svg" alt="System context overview">
  <figcaption style="font-size: 0.9em; color: #555;">System context overview</figcaption>
</figure>

### 3.2 Deployment topology & guardrails (summary)

*Purpose: Point to the authoritative runtime policies without duplicating manifests in the TDD.*

- See [`../platform/runtime.md`](../platform/runtime.md) for the binding environment topology, mesh/TLS guardrails, reference manifests, and diagrams.
- This TDD links to that spec from Settings (§9) and identity (§4) whenever those guardrails are required. Runtime deviations require waivers recorded alongside the platform-runtime spec and App.O.

### 3.3 Service inventory (summary)

- The full first-party service catalog, provider notes, and observability anchors live in [`../platform/runtime.md §4`](../platform/runtime.md#4-state-management-binding).
- Individual service specifications (`../services/*.md`) remain authoritative for implementation details; the catalog simply collates responsibilities for onboarding and capacity planning.

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
  <img class="diagram" src="../build/diagrams/automation/lp-engine/residency-policy-enforcement-v1.svg" alt="Residency policy enforcement sequence">
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
- Evidence: App.L incorporates residency drift baselines; [Runbook RB-RES-ENDPOINT](../ops/runbooks.md#rb-res-endpoint) holds the detailed remediation steps referenced from alerts. App.O ledger links waivers to the specific findings they suppress.

#### 3.8.3 Triage & remediation workflow (binding)

**Breadcrumbs:** Implementation `apps/platform/operations/services/residency_triage.py`, Tests `tests/platform/operations/test_residency_triage.py::test_drives_remediation_plan`, Observability [Runbook RB-RES-ENDPOINT](../ops/runbooks.md#rb-res-endpoint) mapped to Grafana “Residency & Endpoint Posture”.

*Purpose: Provide a deterministic path from detection to resolution without violating residency guarantees.*

- First response (within 15 minutes): SRE validates the alert, confirms the endpoint is blocked, and checks whether production traffic attempted to reach it (audit search on `RESIDENCY_POLICY_BLOCK` + endpoint). Security triages provider announcements or CDN/autoscaling expansions.
- Remediation branches:
  - **Catalogue update:** Reference Manager on-call executes the ingestion and validation steps defined in `../data/ref-manager.md §4.3`, updating `provider_endpoints` and replaying Settings activation once residency attestations are verified.
  - **Waiver required:** Dual approval (Security + Architecture) recorded in App.O; Settings sets `cross_region_waiver` for the affected org/service, and Guardian stamps manifests until the provider delivers an in-region alternative.
  - **Misconfiguration:** When hosts resolve outside the allowlist because of DNS drift or cache poisoning, SRE flushes DNS caches (`scripts/residency/flush_dns_cache.py`) and, if necessary, overrides the mesh egress policy until the provider restores expected records.
- Closure: findings flip to `mitigated` once the scanner observes compliant endpoints for two consecutive runs. Incident retrospectives attach scanner evidence, Settings diffs, and Guardian waiver logs to the decision log (§15.3); preventive tickets capture backlog (provider engagement, automation gaps).

______________________________________________________________________

### 3.9 C4 containers & STRIDE dataflows (binding)

**Breadcrumbs:** Implementation `overview/tdd/diagrams/c4/container-platform-v1.mmd` + `overview/tdd/diagrams/threat/dfd-platform-stride-v1.mmd`, Tests `uv run --project packages/docs_tooling python -m doc_tools.render_mermaid` (CI job `docs-diagram-render`), Observability CI stage “docs-validate” with artifact drift alerts.

*Purpose: Provide an explicit container-level view with threat annotations that build on the context diagram.*

- Container and component diagrams live beside this document (`overview/tdd/diagrams/c4/container-platform-v1.mmd`, `overview/tdd/diagrams/c4/component-platform-v1.mmd`, and rendered SVG/PNG artifacts). Updates must ship with schema or service changes so reviewers can reason about new dataflows before approving agent or infra work.
- The platform threat DFD (`overview/tdd/diagrams/threat/dfd-platform-stride-v1.mmd`) applies STRIDE categories per dataflow: ingress/egress gateways, service-mesh mTLS, Guardian/Signer decision loops, and outbound provider calls. Appendix B enumerates the detailed scenarios; this subsection records the binding between the DFD and container view.
- Container threats and mitigations:

| Container / trust boundary | Primary dataflows & STRIDE focus | Key mitigations & references |
|---|---|---|
| Web & Channels (staff + portal) | Browser ↔ ASGI over TLS (`Spoofing`, `Tampering`, `Information disclosure`) | mTLS terminates at ingress; HSTS/CSP (§11.5); SSE token binding (§10.8); RLS GUC canaries (§4.4); App.B Spoofing mitigations |
| Worker cluster (Celery) | Jobs ↔ storage/LLM providers (`Tampering`, `Repudiation`, `DoS`) | Settings snapshots (§6.1), audit JSONL (§6.3/§6.4), advisory locks (§5.4/[Runbook RB-LOCK-006](../ops/runbooks.md#rb-lock-006)), FinOps guard (§8.7/§13.5) |
| Guardian & Signer services | Artifact promotion, digital seals (`Tampering`, `Repudiation`) | FOR SHARE parent guard (§7.1), immutable audit sink (§12.1), OCSP/TSA verification (§7.2), ADR-0001 (judgment & waiver scope) |
| Settings service + policy compiler | Config activation across tenants (`Spoofing`, `Elevation of privilege`) | HMAC-signed requests ([Platform Runtime §3.5](../platform/runtime.md#35-service-to-service-request-signing-binding)), dual approval (§9.3/§9.11), compiled RLS tables (§4.4), activation lock advisory key (§9.8) |
| External providers (Azure Speech/OpenAI/TSA) | Controlled egress (`Information disclosure`, `DoS`) | Mesh AuthorizationPolicy (§3.8), residency waivers (App.O), LLM safety harness (§8.4), provider circuit breakers (§8.1, [Runbook RB-LLM-003](../ops/runbooks.md#rb-llm-003)) |

- Threat reviews must reference both the container diagram and DFD; new services may not progress past **Provisional** until they document ingress/egress paths, STRIDE analysis, and mitigations in Appendix B.

______________________________________________________________________

## 4) Identity, tenancy & access control

**Purpose:** Highlight platform integration points with the identity stack without repeating the full policy surface.
**Contract:** The binding identity, authorization, masking, and break-glass details live in [`Identity`](../platform/identity.md); tenant provisioning, suspension, and offboarding lifecycles are owned by [`Accounts & Tenants`](../customer/accounts-tenants.md). This section summarises the dependencies other components must observe. **|**
**State:** Tokens, org/case membership, masking profiles, secure views, and break-glass events remain governed by the identity spec. **|**
**Failures & handling:** IdP failover, RLS GUC gaps, masking violations, and device-binding issues follow the runbooks catalogued there. **|**
**Observability:** Dashboards and metrics (`identity.md §8`) provide the authoritative signals; other services consume them via shared telemetry. **|**
**Breadcrumbs:** Identity spec, Settings (`security.*`, `identity.*`), Worker cluster watchdogs, Guardian policy integrations.

### 4.1 Integration highlights (informative)

- Services rely on Keycloak-issued tokens (`active_org_id`, `active_org_roles[]`) and must reject requests lacking those claims.
- API layers set and assert the database GUCs defined in the identity spec before issuing queries (`udocket.active_org`, `udocket.active_user`, `udocket.active_roles`, etc.).
- SSE/Channels enforce device binding and org scoping; token mismatches trigger the identity watchdogs (`device_fp_mismatch_total`).
- Masking and break-glass governance flow through the secure views and masking profiles described in the identity spec; consumers log `MASKING_EVENT`/`BREAK_GLASS_EVENT` for provenance.

## 5) Artifact data layer & storage integrity

*Service specification:* [`Artifact Store`](../data/artifact-store.md) details storage layout, hashing, retention gates, and operational runbooks referenced throughout this section.

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

  | Binding | Implementation | Test | Observability |
  |---|---|---|---|
  | Artifact immutability trigger | Implementation: `apps/platform/artifacts/migrations/0024_artifact_immutable_trigger.py` | Test: `tests/platform/artifacts/test_immutability.py::test_update_blocked_after_draft` | Observability: Audit event `ARTIFACT_IMMUTABILITY_VIOLATION` (Alert: “Artifact Immutable Breach”) |

### 5.2 Artifact lifecycle (authoritative)

**Purpose:** Define artifact classes, canonical statuses, and the only valid transitions.\
**Contract:** Agents, services, and APIs MUST emit statuses and judgments exactly as defined in this section; reruns produce additive versions without mutating prior outputs.\
**State transitions:** Governed by §5.2.2 (statuses), §5.2.3 (Guardian mapping), and §5.4.1 (ExclusiveSwap invariant); App.A.2 diagrams the same state machine.\
**Failure modes & retries:** Guardian `BLOCK` or reviewer quarantine follow remediation/waiver loops in §5.2.3–§5.2.5; watchdogs and approval conflicts escalate via RB-APPROVAL-001 and [Runbook RB-JOB-WATCHDOG](../ops/runbooks.md#rb-job-watchdog).\
**Observability:** `artifact.status`, `guardian_judgment_latency_seconds`, `approval_swap_conflict_total`, `portal_link_invalidated`, and `docs_template_missing_total`.\
**Breadcrumbs:** Implementation `packages/core/artifacts/status.py`, Tests `tests/platform/artifacts/test_status_vocab.py::test_all_statuses_linked`, Observability Grafana “Artifact Lifecycle” dashboard.\
**References:** §5.2.1–§5.2.8, §5.4.1, §7.1, §10.3.2, App.A, App.I.

**Invariants:**\
– No operator can view WP/CD prior to Guardian PASS/WARN (see §5.2.3).\
– Only one `RELEASED` DL exists per `(case_id, type)`; approvals atomically revoke the prior DL (ExclusiveSwap invariant, §5.4.1).\
– Append-only audit: every lifecycle action appends to `ops_<agent>.jsonl` and persists manifests with SHA-256 provenance.

<div style="display: flex; flex-wrap: wrap; gap: 1.5rem; margin: 1.25rem 0;">
  <figure style="flex: 1 1 18rem; text-align: center; margin: 0;">
    <img class="diagram" src="../build/diagrams/overview/tdd/artifact-lifecycle-overview-v1.svg" alt="Artifact lifecycle overview">
    <figcaption style="font-size: 0.9em; color: #555; margin-top: 0.5rem;">Overview — SA ➜ WP ➜ CD ➜ DL.RELEASED ➜ Retention gate</figcaption>
  </figure>
  <figure style="flex: 1 1 18rem; text-align: center; margin: 0;">
    <img class="diagram" src="../build/diagrams/overview/tdd/artifact-wp-lifecycle-v1.svg" alt="Work Product lifecycle">
    <figcaption style="font-size: 0.9em; color: #555; margin-top: 0.5rem;">Work Product — Guardian gating to <code>CLEARED_FOR_USE</code></figcaption>
  </figure>
  <figure style="flex: 1 1 18rem; text-align: center; margin: 0;">
    <img class="diagram" src="../build/diagrams/overview/tdd/artifact-cd-lifecycle-v1.svg" alt="Candidate Deliverable lifecycle">
    <figcaption style="font-size: 0.9em; color: #555; margin-top: 0.5rem;">Candidate Deliverable — operator and reviewer rail to release</figcaption>
  </figure>
</div>
<div style="font-size: 0.85em; color: #666; margin: -0.5em 0 1.5em 0;">
  Legacy diagrams labeled the post-Guardian handoff as <code>READY</code>; the canonical vocabulary is now <code>CLEARED_FOR_USE</code> (WP) and <code>OPERATOR_PREP</code> (CD). The overview’s diamond depicts the retention/erasure gate as a policy decision rather than a lifecycle status, while the detailed diagrams enumerate the class-specific states that feed that gate.
</div>

Work Product that reaches `CLEARED_FOR_USE` becomes selectable input for Analyze/Compose/Timeline lanes and may emit new CDs without re-submitting source assets. Candidate Deliverables inherit the prior Guardian verdict and either progress through operator/reviewer approval (`OPERATOR_PREP → APPROVAL_REQUESTED → QUEUED_FOR_REVIEW → APPROVED`) or loop for remediation. Signing and portal release convert an approved CD into the Deliverable class at status `RELEASED`; replacements revoke the previous release but retain manifests for audit. At any point, retention jobs or certified client erasure requests may invoke the gate, which records the tombstone metadata required in §5.2.2 and §14.2 before entering `ARCHIVED` or `DELETED`.

#### 5.2.1 Object classes (SA/WP/CD/DL/AR)

*Purpose: Classify artifact types and clarify their lifecycle boundaries.*

| Class | Key | Purpose | Examples | Visibility |
|---|---|---|---|---|
| **Source Asset** | **SA** | Raw inputs we ingest. Immutable post-write. | Uploaded audio/video, PDFs, exhibits, notes | Staff (scoped) |
| **Work Product** | **WP** | Internal derived data used to build deliverables; never client-facing. | Issues/timeline/entities/facts/gaps (JSON), interim LLM outputs, scores | Staff only |
| **Candidate Deliverable** | **CD** | Human-readable draft intended for potential external release. | Transcript draft, client summary draft, composed report draft | Staff reviewers/ops |
| **Deliverable** | **DL** | Approved, signed, releasable document (client-visible). | Transcript (final), client summary (final), bundle, signed report | Staff + client |
| **Auxiliary Record** | **AR** | Proofs/receipts/logs backing compliance. | Audit events, waiver records, hash manifests, job cancellation reports, TSA tokens, signature envelopes | Auditors/admin |

Separation of concerns: **WP** stays internal, **CD** is the curated draft surface operators work in, **DL** is the only client-visible output, and **AR** carries the attestations that prove what happened.

#### 5.2.2 Statuses

*Purpose: Define the status vocabulary and transitions for each artifact class.*

Status is scoped by object class and standardizes lifecycle semantics.

| Status | Applies to | Meaning | Entered by | Leaves when |
|---|---|---|---|---|
| **STORED** | SA | Source durably persisted and hashed. | System | Pipeline starts → **PROCESSING** |
| **PROCESSING** | WP, CD | System is generating/transforming. | System | Work done → **PENDING_JUDGMENT** or **FAILED** |
| **FAILED** | WP, CD | System error/missing dependency. | System | Retry/repair → **PROCESSING** |
| **PENDING_JUDGMENT** | WP, CD | Awaiting review judgment. | System | Guardian decides (see §5.2.3) |
| **CLEARED_FOR_USE** | WP | PASS/WARN unlocks internal use; downstream agents may spawn new CDs/deliverables. | Guardian | Consumed downstream or replaced |
| **OPERATOR_PREP** | CD | PASS/WARN, operator workspace to curate/edit. | Guardian | Operator requests review → **APPROVAL_REQUESTED** |
| **APPROVAL_REQUESTED** | CD | Operator submitted for review; awaiting queue assignment/triage. | Operator/System\* | Reviewer accepts assignment → **QUEUED_FOR_REVIEW** |
| **QUEUED_FOR_REVIEW** | CD | Reviewer actively evaluating the draft. | System | Reviewer acts (see §5.2.4) |
| **CHANGES_REQUESTED** | CD | Reviewer rejected with edit instructions. | Reviewer | New CD version → **OPERATOR_PREP** (then **APPROVAL_REQUESTED**/**QUEUED_FOR_REVIEW**) |
| **QUARANTINED** | WP, CD | Policy violation. | Guardian/Reviewer | Waiver or remediation → **OPERATOR_PREP**/**CLEARED_FOR_USE** |
| **APPROVED** | CD | Human-approved draft (or auto-approved). | Reviewer/System\* | Signing → **SIGNED** |
| **SIGNED** | DL | uDocket-signed, TSA timestamped. | Signer | Published → **RELEASED** |
| **RELEASED** | DL | Visible/downloadable in portal. | System | Replacement policy (see §5.2.6) |
| **REVOKED** | DL | Pullback due to approval swap, policy error, or compliance request. | System/Admin/Guardian | Retained, non-downloadable; archived via retention |
| **ARCHIVED** | SA/WP/CD/DL | Frozen under retention; content retained under legal/ops hold. | System | Retention clock expires or approved erasure → **DELETED** |
| **DELETED** | SA/WP/CD/DL/AR | Content removed; only tombstone + audit metadata remain. | System | Retention evidence window closes → purged tombstone (§14.2) |

Transitions into **ARCHIVED** or **DELETED** are mediated by the retention/erasure gate captured in App.A.2. The gate only opens when legal holds are clear *and* one of two triggers fires: (a) retention scheduler reaches the configured destruction window, or (b) a certified client erasure request is approved. Every call path MUST populate tombstone metadata before committing the status change:

- `deleted_at TIMESTAMPTZ`, `deleted_by UUID` (service or human actor), and `deletion_trigger TEXT` (`retention_expired` | `client_erasure`).
- `deletion_certificate_id UUID` pointing to the authoritative `DESTRUCTION_CERT` (case purge) or `deletion_request_id UUID` pointing to the DSAR request; both reference immutable `ERASURE_JOURNAL` manifests.
- `erasure_journal_id UUID`, `retention_schedule_version TEXT`, and `deletion_manifest_sha256 TEXT` so auditors can verify provenance even after payload removal.

Tombstones persist in primary storage until the retention evidence window in §14.2 elapses; pruning the tombstone emits an audit event (`ARTIFACT_TOMBSTONE_PURGED`) and updates the same metadata fields with `tombstone_pruned_at`.

`System*` denotes flows where org configuration auto-submits for review or permits skipping human review (see §5.2.5).

#### 5.2.3 Guardian judgment → status mapping (binding)

*Purpose: Summarize how Guardian judgments advance artifact states and reference `../platform/guardian.md` for detailed mechanics.* *Contract: Judgment vocabulary, policy enforcement, detection pipelines, and APIs live in `../platform/guardian.md`; this section covers the lifecycle impacts other services must honor.*

- `PASS` / `WARN` / `WAIVED` → **WP:** `CLEARED_FOR_USE`, **CD:** `OPERATOR_PREP`.
- `BLOCK` → **WP/CD:** `QUARANTINED` until remediation or waiver.
- Parent gating and HIPAA/SPI posture are resolved inside Guardian; manifests retain `guardian_judgment_id`, `guardian_policy_snapshot_id`, and waiver metadata for audit replay.

Full detection schemas, queue semantics, replay tooling, and manual quarantine workflows remain documented with the Guardian service. Events for these transitions remain enumerated in §10.3.

#### 5.2.4 Human review workflow (summary)

Guardian is the system of record for review outcomes. Candidate deliverables progress from **QUEUED_FOR_REVIEW** to one of three states (**APPROVED**, **CHANGES_REQUESTED**, **QUARANTINED**) and always record reviewer notes, reason codes, and audit evidence. See [`../platform/guardian.md §2.3`](../platform/guardian.md#23-review-reason-catalogs-binding) for the authoritative reason catalogs and workflow contracts; UI behaviour remains aligned with those enums.

#### 5.2.5 Review modes & overrides (summary)

Review automation is controlled by Settings (`review.mode`, `review.approval_type.default`, `review.risk_overrides[]`). Guardian evaluates these after PASS/WARN judgments and either advances the artifact automatically or requeues it for human review. Modes, override semantics, and telemetry live in [`../platform/guardian.md §2.4`](../platform/guardian.md#24-review-modes-risk-overrides-binding); stakeholders should consult that spec before altering review posture.

#### 5.2.6 Deliverable replacement policy

Exclusive deliverables continue to rely on the **ExclusiveSwap** invariant (§5.4.1). Promotion atomically revokes the prior **DL**, signs the new deliverable, and emits audit events. Detailed signer responsibilities and signature policies stay in [`../data/digital-signer.md`](../data/digital-signer.md).

#### 5.2.7 Cross-object controls and audit surface (summary)

Artifacts must retain deterministic hashes, Guardian judgments, and, for deliverables, signature metadata. The Digital Signer spec documents signature formats, TSA/OCSP requirements, and auxiliary artifacts; Guardian’s spec covers QA and quarantine signalling. Portal visibility rules map to `status` (`APPROVED` for CDs in staff surfaces, `RELEASED` for DLs in the portal). Refer to [`../data/digital-signer.md`](../data/digital-signer.md) and [`../platform/guardian.md`](../platform/guardian.md) for full control matrices and audit expectations.

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
- Path template: `storage/media/<ORG_ID>/cases/<CASE_ID>/artifacts/<ARTIFACT_ID>/content.bin|manifest.json`; case-level directories include `audio/`, `transcript/`, `analysis/`, `docs/`, `ops/`. Legacy `storage/media/tenants/<ORG_ID>/cases/<CASE_ID>/` layouts are deprecated and blocked in new deployments.
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
**Breadcrumbs:** Implementation `packages/core/approvals/service.py::approve_artifact`, Tests `tests/platform/artifacts/test_approval_swap.py::test_concurrent_approvals_single_winner`, Observability Grafana “Approvals” panel.\
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

  | Binding | Implementation | Test | Observability |
  |---|---|---|---|
  | Concurrent approval swap | `packages/core/approvals/service.py::approve_artifact` | `tests/platform/artifacts/test_approval_swap.py::test_concurrent_approvals_single_winner` | Alert `approval_swap_conflict_total` (Grafana “Approvals” panel) |
  | Deliverable release exclusivity | `packages/core/approvals/service.py::promote_deliverable` | `tests/platform/artifacts/test_deliverable_release.py::test_single_released_deliverable_enforced` | Metric `deliverable_release_retries_total`; alert `deliverable_release_uniqueness` |

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

All schema properties marked with `"format": "uuid"` expect UUIDv7 strings; generator tooling annotates each property with `"description": "UUIDv7"` and the non-enforcing extension `"x-udocket-uuid-version": 7`. Runtime validators (`packages.core.validators.uuid.ensure_v7`) reject non-v7 inputs on write. The `masking`, `security`, and `retry` sections bind manifests to the vault/HSM posture defined in §4.5.2 and capture the replay metadata consumed by the job lifecycle contract (§10.2, §6.2–§6.4). CI fixtures in `tests/spec/test_artifact_manifest_schema.py` assert the additional required fields for every artifact class.

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
    "tool_versions": {"packages.core": "0.9.0", "azure_speech": "1.38"},
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

**Purpose:** Provide a high-level view of the LangGraph-powered agent suite (Transcribe, Analyze, Compose, Timeline, Relationship) and show how they collaborate with Settings, Guardian, and Worker Cluster. **|**
**Contract:** Canonical pipelines, inputs/outputs, manifests, and QA guardrails are defined in [`../automation/langgraph-agents.md`](../automation/langgraph-agents.md); this section highlights integration edges and shared dependencies other services rely on. **|**
**State:** Agents persist transcript text + JSON, the internal Analyze `AtomsIndex`, discrete analysis artifacts (outline, timeline, entities, issues, gaps, flags, alerts, summary JSON, staff report MD, QA report JSON), compose deliverables, manifests, and audit streams under `storage/media/tenants/<ORG_ID>/cases/<case>/`. Settings stores pipeline/tool configuration and region allowlists; Worker Cluster orchestrates LangGraph jobs; Guardian verdicts gate promotion. **|**
**Failures & handling:** Failure taxonomy (`TRANSIENT`, `POLICY`, `INPUT`, `INTEGRITY`, `CONCURRENCY`, `REGION_POLICY`) is defined in the LangGraph agents spec; Worker Cluster retries and Guardian quarantines apply consistently across pipelines. **|**
**Observability:** Dashboards “Agent Pipelines – Activation”, “LangGraph QA”, and “Agent Shadow Runs”, lane-level metrics (`agent_lane_duration_seconds`, `agent_lane_queue_wait_seconds`, `agent_lane_schema_fail_total`, `atoms_extracted_total`), and audit JSONL streams provide traceability; quality targets remain anchored in the LangGraph agents spec. **|**
**Breadcrumbs:** Canonical design [`../automation/langgraph-agents.md`](../automation/langgraph-agents.md); runtime `packages/core/agents/langgraph_orchestrator.py`; analyze stages `packages/core/agents/analyze/stages/`; compose orchestrator `packages/core/agents/compose/orchestrator.py`; Celery tasks `apps/platform/operations/tasks/agents.py`; QA harness `tests/agents/test_langgraph_acceptance.py`. **|**
**References:** §3 (platform architecture), §5 (artifact lifecycle), §§7–8 (Guardian & Signer summaries), Appendices I & U, LangGraph agents spec §§1–10, spec schemas `spec/schemas/agents/`.

### 6.1 LangGraph orchestration (summary)

- *Primary spec:* [`LangGraph agents §3`](../automation/langgraph-agents.md#3-api-contract).
- GraphRunner (LangGraph `>=0.2,<0.3`) compiles the Transcribe → Analyze → Compose DAG with explicit fan-out/fan-in nodes: Analyze runs outline, timeline, entities, issues, gaps, and flags lanes in parallel before converging into summary, staff, and QA stages; Compose retains client/lawyer/bundle lanes with QA gating. Finalize nodes remain the sole writers for deterministic artifacts and share the same `StateGraph` idioms.
- Settings (`agents.pipeline.*`, `agents.tools.*`) declare pipelines, lane concurrency, region allowlists, and idempotency keys; activation lints enforce schema hashes and contract tests prior to rollout.
- LangGraph checkpoints persist in Postgres (shared DB) with per-node `idempotency_key = sha256(job_id || pipeline_id || node_id || graph_version || input_hash)` so retries + resumes stay deterministic. Resumes require matching settings snapshots and manifest hashes; divergences raise `E_INTEGRITY_MISMATCH`.
- Execution boundary: `packages/core` owns the LangGraph runtime, schemas, and job services; `apps/platform` invokes those services via Celery for orchestration + UX, preserving core/service separation for future deployment targets.
- Assistant pipelines reuse the same activation pathway, ensuring retrieval, moderation, and responder lanes inherit identical policy controls and manifest discipline.

### 6.2 Transcription pipeline (summary)

- *Primary spec:* [`LangGraph agents §2.1`](../automation/langgraph-agents.md#21-transcription-agent-binding).
- Modes: streaming and batch ingestion of local files or HTTPS SAS URLs. Inputs capture language, region (validated against Settings allowlists), diarisation flag (batch only), and provider choices.
- Outputs: transcript text `transcript/<job_id>__transcript.txt`, structured transcript JSON `transcript/<job_id>__transcript_v1.json` (segment UUIDs, speaker roster, hashes), per-run meta JSON `ops/<job_id>__transcription_log.json`, human log, and `ops/ops_transcription.jsonl` audit append.
- Capability negotiation ensures format/language support before dispatch; retries follow provider budgets with exponential backoff; conversion to PCM WAV (ffmpeg) is captured in manifest metadata for forensic review.

### 6.3 Analyze pipeline (summary)

- *Primary spec:* [`LangGraph agents §2.2`](../automation/langgraph-agents.md#22-analyze-agent-binding).
- Inputs: structured transcript JSON (text fallback only when JSON is unavailable), intake questionnaire artifacts, DOCX outline template headers, case metadata, Settings overrides for prompts and lane concurrency.
- Parallel lanes emit discrete artifacts: `analysis/<job_id>__outline_v1.json`, `timeline_v1.json`, `entities_v1.json`, `issues_v1.json`, `gaps_v1.json`, `flags_v1.json`, `alerts_v1.json`, summary JSON (`summary_v1.json`), staff report Markdown (`staff_report_v1.md`), QA report JSON (`qa_report_v1.json`). All records carry deterministic UUIDs (`uuid5` signatures) and schema_version headers.
- Lane QA & revisions: each lane produces an `AnalyzeLaneResult` payload consumed by `LaneQA`. Outcomes are `advance`, `revise`, or `quarantine`. Revision requests emit `AnalyzeRevisionDirective` schemas (targets + preserve spans) so reruns only rewrite failing slices; good data stays byte-identical across passes.
- Atom layer: transcript segments flow through an internal extraction pipeline that canonicalises statements, detects negation cues, assigns deterministic UUIDs, aggregates evidence, and produces an `AtomsIndex`. Downstream lanes consume the index to attach citations, detect conflicts, and populate `SummaryCheck` verdicts surfaced in `qa_report_v1.json`. Optional debug dumps (`analysis/<job_id>__atoms_v1.json`) remain feature-flagged (`ANALYZE_SAVE_ATOMS`).
- QA gates validate JSON Schema compliance, atom-backed evidence linking, and questionnaire coverage before finalize persists artifacts; reruns create `_v{n}` versions while preserving manifests and audit history (`ops/ops_summary.jsonl`).

### 6.4 Compose pipeline (summary)

- *Primary spec:* [`LangGraph agents §2.3`](../automation/langgraph-agents.md#23-compose-agent-binding).
- Inputs: canonical Analyze artifacts (`summary_v1.json|.md`, `timeline_v1.json`, `entities_v1.json`, `issues_v1.json`, `gaps_v1.json`, `flags_v1.json`, `alerts_v1.json`), intake data, deliverable templates (DOCX/Markdown), and policy settings. No dependence on Analyze Markdown since summary JSON is canonical.
- Dual deliverable lanes (client, lawyer) draft in parallel with dedicated editor passes and QA reviewers; optional bundle excerpt runs alongside. Outputs: client/lawyer deliverables (`docs/<job_id>__compose_client_v1.*`, `docs/<job_id>__compose_lawyer_v1.*`), bundle excerpt, QA/staff reports, manifests, and `ops/ops_compose.jsonl` audit lines.
- Policy lints and Guardian gating enforce forbidden content, required sections, link limits, and region compliance before promotion. Manual/agent edits produce new artifact versions subject to reviewer approval.
- Factuality guard relies on atom-derived citations embedded in canonical Analyze artifacts; sections must meet citation thresholds before delivery artifacts promote.

### 6.5 Timeline & relationship pipelines (summary)

- *Primary spec:* [`LangGraph agents §2.4`](../automation/langgraph-agents.md#24-timeline-relationship-agents-roadmap-informative).
- Roadmap agents consume Analyze timeline/events and entities JSON to build richer chronological views and relationship graphs, preserving UUID lineage and evidence pointers.
- Graduation to binding requires QA + shadow metrics to meet thresholds; roadmap tracked in LangGraph agents §10. Outputs will reuse the `analysis/<job_id>__timeline_v1.json` and `entities_v1.json` signatures to avoid duplication.

### 6.6 Manifests, lineage, and failure taxonomy (summary)

- *Primary spec:* [`LangGraph agents §4–§5`](../automation/langgraph-agents.md#4-state-management).
- Manifests capture input hashes, settings snapshot SHA, pipeline + graph versions, tool usage, region assignments, prompt provenance, and artifact checksums (including schema_version). Audit JSONL streams remain append-only.
- Failure classes map to error codes (`E_TRANSIENT_PROVIDER`, `E_POLICY_FORBIDDEN`, `E_INPUT_INVALID`, `E_INTEGRITY_MISMATCH`, `E_CONCURRENCY_LIMIT`, `E_REGION_POLICY`); Worker Cluster propagates retries/backoff and surfaces SSE updates to the UI.

### 6.7 Quality, security, and operations (summary)

- *Primary spec:* [`LangGraph agents §6–§9`](../automation/langgraph-agents.md#6-observability).
- Quality KPIs include transcription accuracy, timeline/entity coverage, issue/gap precision, deliverable QA pass rate, and cost/time budgets; results land in `analysis/<job_id>__qa_report_v1.json` and compose QA artifacts.
- Region enforcement is policy-driven—Settings allowlists gate providers and regions; Guardian audits waivers; manifests log region selections for every lane. HIPAA/SPI controls and Guardian policy integration ensure data handling remains compliant across regions.
- Operational procedures (pipeline activation, rollbacks, shadow runs) follow LangGraph spec; Ops runbooks `RB-AGENT-*` cover drills, cancellation, and incident playbooks referenced in §8–§9.

## 7) Digital signing & Guardian services

### 7.1 Guardian service (summary)

*Purpose: Highlight platform touchpoints with Guardian.*\
*Contract: Guardian architecture, policy, interfaces, and operations are defined in [`../platform/guardian.md`](../platform/guardian.md); this section lists the integration points.*

- Lifecycle gating: Guardian enforces SA/WP/CD transitions from `PENDING_JUDGMENT` to the statuses in §5.2.3 after PASS/WARN/WAIVED decisions. Queue semantics and detection tiers remain documented there.
- Policy & waivers: Policy bundles, waiver handling, and quarantine ownership stay with Guardian; approvals (§5.4) and retention (§14) depend on those controls.
- Operations: Guardian SLOs, runbooks, and manual review procedures stay with that team; review queue gating (§5.2) and portal invalidation (§11.2.1) represent the platform dependencies.
- Artifacts & manifests: Guardian judgment IDs, reason codes, and settings hashes persist in manifests consumed by Signer and Portal; schema and payload examples live there.

### 7.2 Digital signature service (summary)

*Purpose: Highlight signer touchpoints while delegating implementation detail to the canonical spec.*\
*Contract: Document Signer architecture, trust roots, TSA/OCSP integration, and FIPS enforcement live in [`../data/digital-signer.md`](../data/digital-signer.md); this section summarises dependencies.*

- Platform signatures: Document Signer converts canonical content to PDF/A (or COSE/JWS), applies platform signatures, and records signature manifests with TSA/OCSP evidence. Deliverables remain blocked until Guardian verifies the manifest.
- Signature policies & acknowledgements: Settings `sign.signature_policies[]` drive platform signatures and client acknowledgement flows. Portal prompts for countersignatures where required and stores auxiliary artifacts referenced in manifests. Full policy catalog, default mappings, and waiver handling appear in §2.2 of the signer spec.
- Trust roots & PKI: Managed HSM keys, offline/online certificate hierarchy, and rotation procedures are documented in [`../data/digital-signer.md §2.3`](../data/digital-signer.md#23-trust-roots-pki-and-hsm-integration-binding). Settings activation validates attestation (`sign.hsm.key_id`, `sign.trust_roots[]`) and records `SIGN_TRUST_ROOTS@<version>` artifacts.
- TSA/OCSP posture: Soft-fail windows, responder failover, and metrics (`ocsp_latency_seconds`, `tsa_time_drift_seconds`, `sign_verify_status_total`) are owned by the signer service (§2.4, §5.1). Portal quarantine behaviour after soft-fail windows inherits from that spec.
- FIPS compliance: `security.crypto.fips_requirement` and deliverable policies dictate FIPS mode. Startup attestation, algorithm enforcement, waiver governance, and monitoring live in §7.
- APIs: Signing, verification, and certificate retrieval endpoints plus acknowledgement flows are formalised in signer §3. Integrators MUST use HMAC headers and Idempotency keys per that contract.

### 7.3 Request signing and verification (summary)

*Purpose: Highlight the shared inter-service authentication contract without restating the gateway implementation.*\
*Contract: All privileged service-to-service calls adopt the HMAC request signing model documented in [`../platform/runtime.md §3.5`](../platform/runtime.md#35-service-to-service-request-signing-binding).*

- Guardian, Signer, Settings activation, worker control APIs, and other mutating surfaces sign requests with the headers defined there; receivers validate signatures, enforce timestamp skew, and reuse the shared idempotency store for replay protection.
- Key rotation (dual-publish → cutover → revoke), deny lists, and canary expectations follow [`../platform/runtime.md §3.5.1`](../platform/runtime.md#351-key-rotation-flows-binding) and the Security runbooks; Settings activation and alerting consume the same rotation events.

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

The canonical specification for registry, moderation, FinOps, and replay requirements lives in [`../automation/llm-registry.md`](../automation/llm-registry.md). This overview retains the intent and integration edges that other platform components rely on:

- **Provider registry & residency:** Compose/Analyze lanes must call the registry for every LLM invocation. Residency allowlists, failover parity, and waiver handling are enforced per §2.1 of the service spec; Guardian/Settings tests ensure policy drift pages the RB-LLM-003 responders.
- **Prompts, redaction, and evidence:** Prompt templates, masking rules, and reproducibility envelopes follow §2.2. Jobs record envelope IDs in manifests and depend on the evidence store for replay audits. HIPAA posture requires masked prompts everywhere outside the evidence store.
- **Safety harness & moderation:** Pre-call filters, multi-stage moderation, QA evaluators, and Guardian quarantine workflow are defined in [`../automation/llm-registry.md §2.3`](../automation/llm-registry.md#23-safety-harness-jailbreak-tests-policy-enforcement-binding). WARN-mode tuning is limited to non-production orgs and is time-bound.
- **FinOps guardrails:** Token ceilings, monthly caps, deploy gates, and budget hold workflows follow [`../automation/llm-registry.md §2.4`](../automation/llm-registry.md#24-cost-controls-finops-budgets-binding). Compose/Analyze workers surface `PAUSED_AWAITING_BUDGET` and SSE warnings when the FinOps controller halts spend; overrides require dual approval.
- **Replay & provenance:** Reproducibility envelopes, golden-set drills, and the illustrative provider matrix live in §§4.1–4.2. Job retry tooling must carry `envelope_id`/`retry_token` pairs so operators can execute RB-LLM-REPLAY without losing traceability.
- **Runbooks & dashboards:** Operational responders rely on RB-LLM-003 (circuit), RB-LLM-JB (moderation), RB-LLM-FINOPS (budgets), and RB-LLM-REPLAY (envelopes). Observability dashboards referenced in the service spec remain mandatory for SRE review.

Appendix I retains the shared glossary for LLM terminology referenced by both this overview and the service spec.

______________________________________________________________________

## 9) Configuration & settings platform (binding)

**Breadcrumbs:** See [`../platform/settings.md`](../platform/settings.md) for implementation, test, and observability anchors that govern the Settings Registry. *Purpose: Keep the platform TDD aligned with the dedicated Settings Registry specification while summarizing integration obligations.* *Contract: Platform services MUST consume Settings Registry snapshots, honor activation governance, and surface audit metadata per [`../platform/settings.md`](../platform/settings.md).* *State: Jobs, artifacts, and policy contexts record `settings_snapshot_sha256` and version identifiers supplied by the Settings Registry; activation history, waivers, and diff artifacts persist in the service tables described there.* *Failure modes & retries: When snapshot fetches fail or unsafe activations occur, platform workloads pause new jobs and follow the rollback/approval workflows referenced in [`../platform/settings.md §4`](../platform/settings.md#41-activation-pipeline-binding).* *Observability: Platform dashboards monitor `settings_snapshot_stale_total`, `settings_activation_total`, and governance alerts emitted by the Settings Registry; see [`../platform/settings.md Appendix B`](../platform/settings.md#appendix-b-metrics-alerts).*

- Service charter, APIs, activation workflow, caching, telemetry, and governance controls for the Settings Registry live in [`../platform/settings.md`](../platform/settings.md).
- Agent pipeline bundles, tool catalogs, LLM profiles, and seed bundle processes are defined in [`../platform/settings.md §5`](../platform/settings.md#5-failure-modes-binding); platform agent sections reference those contracts instead of re-describing keys here.
- Integration requirements for Guardian, Localization & Policy Engine, Reference Manager, portal, and worker pipelines are captured in [`../platform/settings.md §6`](../platform/settings.md#6-observability-binding).
- Residency controls, rate limits, FinOps guardrails, compliance toggles, and approval behaviour rely on settings enumerated in [`../platform/settings.md Appendix A`](../platform/settings.md#appendix-a-settings-key-map-traceability-index); platform sections cite that inventory for authoritative key coverage.

______________________________________________________________________

## 10) APIs & integration contracts

### 10.0 API contract & lifecycle governance

*Purpose: Anchor the narrative TDD to machine-readable contracts and a predictable change cadence.*

- Canonical OpenAPI 3.1 specifications live under `ops/openapi/` (`uDocket-platform.openapi.yaml` for staff/client surfaces, with service-specific overlays). Every PR that changes endpoints must update the spec and rerun `make lint-openapi` (`npx spectral lint ops/openapi/**/*.yaml --ruleset ops/openapi/spectral.yaml`); CI blocks merges when lint or diff checks fail. `make lint-schemas` validates `spec/schemas/*.json` (enforcing `additionalProperties=false` where required, string length caps, and enumerations) so generated models stay aligned with the OpenAPI components.
- Shared JSON Schemas live under `spec/schemas/` and are treated as the single source of truth for reusable components. Code generators (Python/TS) consume these schemas so no handwritten Pydantic model drifts from the published contract.
- Breaking or materially user-visible changes require an ADR (see `docs/adr/README.md` and linked entries such as `ADR-0002-api-versioning-and-sunset.md`) approved by Architecture + Security before the change can progress from **Provisional → Implementable → Implemented**.
- Versioning policy: monthly “compatible” releases roll on the first business Monday; clients may pin to older behaviour via `X-uDocket-API-Version: YYYY-MM`. Majors ship at most twice per year, demand 90-day notice, and use calendar-versioned prefixes (`2025-02`), while additive changes batch unless explicitly waived.
- Deprecations follow the cadence published in `docs/api/DEPRECATIONS.md`: announce, provide migration guides, emit `Sunset` headers 90 days before removal, and confirm monitors stay green before final removal (traceability captured in App.T).
- Deprecation headers follow RFC 9745 structured-field syntax (e.g., `Deprecation: @1780272000; sunset="Mon, 01 Jun 2026 00:00:00 GMT"`) and always pair with `Link: rel="deprecation"` to machine-readable migration notes plus RFC 8594 `Sunset` headers; Spectral rule `sunset-header` enforces the trio.
- Stripe-style public docs and code samples render directly from the OpenAPI bundle so that examples, schemas, and error contracts stay synchronized with the source of truth.

### 10.1 REST and WebSocket conventions (summary)

Platform runtime owns the authoritative REST, pagination, idempotency, and SSE/WebSocket contracts (see [`../platform/runtime.md §3.1.7`](../platform/runtime.md#317-rest-and-websocket-conventions-binding)). All API changes must reference that spec, reuse the shared middleware, and update OpenAPI components to keep generated clients in sync.

### 10.2 Artifact/job/review endpoints (summary)

Artifact CRUD semantics, download guards, and approval workflows live in [`../platform/runtime.md §3.1.8`](../platform/runtime.md#318-artifact-endpoints-binding) alongside Guardian/Digital Signer responsibilities. Job creation/control behaviour—including cancellation and retry contracts—is defined in [`../automation/worker-cluster.md §3.7`](../automation/worker-cluster.md#37-job-lifecycle-endpoints-binding). Review endpoints continue to defer to Guardian’s approval rules (`../platform/guardian.md §3`).

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

**Breadcrumbs:** Implementation `packages/core/idem/store.py::IdempotencyStore`, Tests `tests/platform/api/test_idempotency_store.py::test_replay_returns_cached`, Observability Grafana “API Idempotency” dashboard (metric `idempotency_replay_total`).

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
1. Normalise endpoint to `METHOD:/path` (path variables preserved) and compute `request_hash = sha256(canonical_request_bytes)` via `packages.core.idem.hash_request`.
1. Insert `(org, scope, key, endpoint, case_id, request_hash, result_ref, response_code, response_hash, status, expires_at)` on first execution with `expires_at = now() + make_interval(hours => :ttl_hours)`. Conflicts where `request_hash` differs MUST raise 409 `CONFLICT` with `details.reason="IDEMPOTENCY_SIGNATURE_MISMATCH"`; matching hashes update `last_seen_at` and return `result_ref`.
1. Optional overlapping-run guard per case/kind: `udlock.try_lock('jobkind', CONCAT(:case_id, '/', :kind))` → 409 `JOB_KIND_BUSY` if held.

- Canonical scopes (binding): `IDEMPOTENCY_SCOPES = {'job:create', 'job:checkpoint', 'artifact:approve', 'artifact:upload', 'upload:finalize'}` exported from `packages.core.idem.constants`. Services **MUST NOT** invent ad-hoc strings; CI lints specs and Python call sites to use the constant set.

- Response contract: any API that accepts `Idempotency-Key` **MUST** echo the exact value in the response headers for success and error paths (`Idempotency-Key: <value>`) and emit `Idempotency-Status: fresh|replay|conflict`. OpenAPI lint (`ops/openapi/rules/idempotency-echo.yaml`) enforces the headers on 2xx/4xx/5xx responses.

- Nightly janitor job `ops/idempotency/purge.py` deletes expired rows and runs `VACUUM (ANALYZE)` to keep the table bounded; `expires_at` is pinned to `api.idempotency.ttl_hours`.

  | Binding | Implementation | Test | Observability |
  |---|---|---|---|
  | Canonical scope constants | Implementation: `packages/core/idem/constants.py::IDEMPOTENCY_SCOPES` | Test: `tests/core/idempotency/test_scopes.py::test_scope_constant_matches_db` | Observability: Buildkite `lint-idempotency` step (scope diff) |
  | Response echo header | Implementation: `apps/platform/common/middleware/idempotency.py::IdempotencyHeaderMiddleware` | Test: `tests/platform/api/test_idempotency_header.py::test_response_echoes_header` | Observability: API metrics `idempotency_echo_missing_total` |
  | Replay semantics | Implementation: `packages/core/idem/service.py::upsert_key` | Test: `tests/platform/api/test_idempotency_replay.py::test_same_key_same_body_vs_conflict` | Observability: Audit event `IDEMPOTENCY_CONFLICT` |

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
- Reference Manager: REST, SSE, and automation surfaces documented in `../data/ref-manager.md §4.1`; this platform TDD defers detailed endpoint contracts to that specification.
- Digital Signer: `POST /api/v1/sign`, `POST /api/v1/sign/verify`, `GET /api/v1/sign/certificates/{artifact_id}`.
- Privacy & governance: `POST /api/v1/privacy/dpia`, `POST /api/v1/privacy/ropa`, list/read endpoints (`GET /api/v1/privacy/dpia`, `/api/v1/privacy/ropa`), entitlement history (`GET /api/v1/admin/entitlements/history`). All responses include `X-Request-ID` and follow the ApiError schema; OpenAPI specs tag operations with `privacy` and enforce auditor-only access.
- Security: HMAC signing required for all mutating operations; examples in Platform Runtime §3.1.4–§3.1.9. SSE under `/api/v1/jobs/{id}/events`.

### 10.5 OpenAPI governance, linting, and example requirements

*Purpose: Keep API documentation consistent and machine-validated.*

- Authoring rules (binding): new operations must reuse shared components (`ApiError`, pagination envelope, security schemes), declare response examples for 2xx/4xx, include tag + summary, document every required header, and map path parameters to UUID formats where applicable. Specs are edited via `ops/openapi/*.yaml`; commits must update corresponding changelog entries.
- Specs: OpenAPI 3.1 with `x-stability` tags (`stable|beta|experimental`); deprecations emit RFC 9745-compliant `Deprecation` headers (e.g., `Deprecation: @1780272000; sunset="Mon, 01 Jun 2026 00:00:00 GMT"`) alongside RFC 8594 `Sunset` headers (≥90 days) in accordance with §10.0 policy.
- Spectral rules (`ops/openapi/spectral.yaml`): enforce `oidc`, `hmacSignature` on mutating ops, error envelope on 4xx/5xx, shared pagination, forbid org/role spoof headers, and fail any spec whose `openapi` field is not `3.1.*` via the `openapi-version` rule.
- Examples must not include real PII; Spectral rule `no-pii-examples` enforces masking, and rate-limit responses (429) must include `Retry-After`/`X-RateLimit-*` headers as shown in Platform Runtime §3.1.4–§3.1.9.
- CORS exposure (binding): expose `X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After, ETag, Deprecation, Sunset`. Preflight MUST allow the header set defined in Platform Runtime §3.1.6 (`Authorization, Content-Type, Idempotency-Key, X-Request-Signature, X-Signature-Key-Id, X-Timestamp, If-Match, If-None-Match, If-Range, X-Style-Nonce, X-Script-Nonce`); update Platform Runtime §3.1.6 first and mirror it here to avoid drift. Add `Vary: Origin, Access-Control-Request-Method, Access-Control-Request-Headers`.
- Rate limits & antifraud: per-org and per-IP thresholds; portal download caps with anomaly trip expiring active links; 429 includes rate-limit headers and `Retry-After`. Binding defaults (`api.rate_limits.web.rpm_per_org=600`, `api.rate_limits.web.rpm_per_ip=300`, `portal.download.rate_limits.user_rpm=60`, `portal.download.rate_limits.org_rpm=200`) live in [`../platform/settings.md Appendix A`](../platform/settings.md#appendix-a-settings-key-map-traceability-index); overrides must stay within the 10-2000 RPM guardrails enforced by Settings validation.
- Idempotency TTL (binding): default 24h; reusing keys after TTL executes anew; conflicting reuse returns 409.
- CI: `spectral lint` and schema diff checks gate merges; examples validate. Platform Runtime §3.1.4–§3.1.9 hold the canonical payloads.

**Acceptance:**

- Unit: `make lint-openapi` (`npx spectral lint`) enforces Spectral rules (including `openapi-version`) and shared component usage.
- Integration: `tests/e2e/test_rate_limit_headers.py::test_429_headers` runs in staging to assert rate-limit/Retry-After headers match Platform Runtime §3.1.6.
- Security: `scripts/security/verify_cors_headers.py` validates the CORS exposure list in Platform Runtime §3.1.6 and fails on regressions; OWASP ZAP smoke confirms no over-exposed headers.

Binding breadcrumbs:

| Control | Implementation | Test | Observability |
|---|---|---|---|
| OpenAPI 3.1 enforcement | `ops/openapi/rules/openapi-version.yaml` | `make lint-openapi` (`npx spectral lint ops/openapi/**/*.yaml`) | Buildkite `lint-openapi` stage |
| Rate-limit header contract | `apps/platform/api/middleware/rate_limiting.py::append_rate_limit_headers` | `tests/e2e/test_rate_limit_headers.py::test_429_headers` | Metric `api_rate_limit_header_miss_total` |
| CORS exposure policy | `config/settings.py::CORS_EXPOSE_HEADERS` & Settings bundle `security.cors` | `scripts/security/verify_cors_headers.py` | CI job `security-headers` / Grafana “API Security Headers” panel |

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

  | Binding | Implementation | Test | Observability |
  |---|---|---|---|
  | `content_length` persistence | Implementation: Migration `apps/platform/artifacts/migrations/0023_add_content_length.py` & ORM `CaseArtifact.content_length` | Test: `tests/platform/artifacts/test_content_metadata.py::test_content_length_persisted` | Observability: Grafana “Artifact Metadata Drift” panel (alerts on mismatched lengths) |
  | Range/ETag staging test | Implementation: `tests/e2e/test_artifact_range_download.py` (GitHub Actions `deploy-gate`) | Test: `tests/e2e/test_artifact_range_download.py::test_range_and_conditional_gets` | Observability: Buildkite deploy gate log (`range-etag-contract`) |

### 10.7 Error model and codes (normative)

*Purpose: Keep service documentation aligned on a shared error envelope while delegating canonical code ownership to the Platform Runtime specification and per-service appendices.*

- Envelope (binding): HTTP error payloads MUST validate against `spec/schemas/api_error.schema.json`. Runtime code in Django/FastAPI imports Pydantic models generated from that schema during the build pipeline so the schema remains the single source of truth. Servers echo the `Idempotency-Key` header (if present) in responses to aid callers with safe retries.
- Code catalog: [`Platform Runtime §3.3`](../platform/runtime.md#33-api-error-codes-binding) owns the authoritative `ApiError.code` enumeration and retry guidance. Service documents list any additional codes in their `§3.3 API error codes` subsection; the consolidated appendix (`overview/tdd/appendices/api_error_codes.md`) is rebuilt with `make docs.sync.api_codes`.
- Headers: always emit `X-Request-ID`; add `Retry-After`, `Deprecation`, `Sunset`, and rate-limit headers when applicable. Error payloads are included in Spectral lint checks (§10.5).
- Client guidance: follow the retry/stop rules documented in each service spec’s API error section; SDKs surface the same behaviour via typed exceptions.

### 10.8 Stream events & replay (normative)

*Purpose: Summarize the streaming contract that keeps jobs, artifacts, and notifications in sync.*

- The Communications specification (Appendix A) owns the authoritative event catalog, envelope schema, and replay rules; the web app spec Appendix A documents the UI contract and accessibility pattern. Producers validate payloads against `spec/schemas/sse/event_envelope.schema.json`; consumers branch on `schema_version` and `emitted_at` during rollouts.
- Streams deliver at-least-once with monotonic IDs per scope (`case`, `job`). Clients send `If-None-Match` digests; servers respond with bounded snapshots before resuming live events whenever digests diverge. Redis retention remains 24 hours with quarterly load tests (`scripts/sse/load_test.py`) to prove capacity.
- Operational SLOs (`sse_client_delivery_lag_seconds`, `sse_snapshot_build_duration_seconds`, `sse_snapshot_size_bytes`) gate releases. Token binding and RLS keep events scoped to the active org/case; violations raise `SSE_DISCONNECT_TOKEN_MISMATCH`.

**Acceptance:** Contract tests (`tests/platform/realtime/test_sse_payloads.py`, `tests/e2e/test_sse_reconnect.py`, `tests/e2e/test_sse_token_binding.py`) run in CI; staging drills assert dashboard alerts and snapshot budgets before deploy.

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
- **Clock hygiene:** Services rely on chrony/NTP with ±100 ms drift budget (aligned with TSA requirements in [`platform-runtime §3.1`](../platform/runtime.md#31-external-interfaces-binding)). Health checks fail closed if drift exceeds 250 ms; alerts page SRE.
- **UI controls:** Date pickers default to case locale; portal displays timezone label on deliverables and approvals. Manual edits capture both UTC timestamp and operator-local zone for audit clarity.
- **Backfills/migrations:** Jobs ensure time arithmetic uses timezone-aware APIs; tests verify `created_at`/`decided_at` fields remain UTC during bulk updates.

### 10.11 Localization & Policy Engine APIs

*Purpose: Defer to the dedicated LPE API specification.*

See `../automation/lp-engine.md §4` for endpoint definitions, SDK responsibilities, legacy shim guidance, and error models. This section intentionally references that document to avoid divergence.

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

See [`../experience/web-app.md`](../experience/web-app.md) for the authoritative specification of the staff workspace, reviewer consoles, and client portal. Platform components depend on the following integration points:

- **Staff workspace & approvals:** Compose/Analyze outputs, Guardian verdicts, and job watchdog signals feed the operator UI; reviews must surface SSE status, backlog metrics, and RB-JOB-WATCHDOG links.
- **Client portal delivery:** Download tokens, invalidation flows, phishing reporting, and secure portal messaging reuse notifications service APIs (`portal.link_invalidated`, signed URLs, abuse logging) while enforcing RLS and masking policies.
- **Accessibility & localization:** LP Engine bundles (`i18n.*`) and accessibility evidence drive UI releases; pseudolocale checks and axe snapshots remain release gates referenced in the web-app spec.
- **Manual/agent edits & assembly:** Edit manifests, dual-approval rules, and document assembly pipelines coordinate with Guardian and Digital Signer before artifacts reach the portal.
- **Conversational assistants:** Staff and client assistants use the shared capability APIs (§10.12), respect LLM registry safety controls, and emit manifests for audit/Guardian review.

Notifications, Guardian, Settings, and LP Engine service docs enumerate the supporting keys and runbooks.

______________________________________________________________________

## 12) Observability, reliability & operations

- Glossary: Appendix I includes observability metrics, watchdog terminology, and quota concepts cited in §12.

### 12.1 Telemetry, logging & audit (binding)

**Purpose:** Summarize the platform-wide observability and evidence posture while delegating implementation details to dedicated specifications.\
**Contract:** All teams follow the Logging specification for runtime telemetry and the Audit specification for immutable evidence. This TDD calls out the expectations at a glance; consult the service docs for binding mechanics.\
**Observability & Logging spec:** [`../platform/observability.md`](../platform/observability.md) governs schema, pipeline topology, trace correlation, access controls, redaction, sampling and cost guardrails. Key platform metrics continue to include `logging_ingest_lag_seconds`, `logging_drop_rate_pct`, `trace_sampling_rate`, and `logging_volume_budget_violation_total`.
**Audit & Evidence spec:** [`../data/audit.md`](../data/audit.md) defines manifest formats, append-only stores, seal verification, waiver ledgers, DSAR journals, and immutable sink requirements. Critical indicators remain `audit_worm_lag_seconds`, `audit_seal_errors_total`, and `audit_manifest_missing_total`.
**Settings keys:** Telemetry and audit toggles surface under `logging.*`, `audit.*`, and `privacy.*`; changes require dual approvals and documentation in their respective specs.
**Runbooks:** Operational responses reference RB-LOG-007, RB-AUDIT-004, RB-MASK, RB-COST, and RB-TRACE-CORR in `../ops/runbooks.md`.
**Cross-links:** Guardian judgments embed audit IDs (§7), manifests live with artifact lifecycle (§5.2), and Settings activation snapshots (§6.1) ensure every job carries provenance.

### 12.2 Runbooks and synthetic monitors

*Purpose: Ensure operational readiness and quick diagnosis.*

- Synthetic checks: `/readyz` with RLS enforcement, settings cache validation, NTP drift. Guardian synthetic job ensures policy enforcement; Signer synthetic verifies TSA reachability.
- Logging pipeline synthetic monitors assert `logging_ingest_lag_seconds < 30s`, `logging_drop_rate_pct = 0`, and index freshness; alerts route to `../ops/runbooks.md (RB-LOG-007)`.
- Runbooks stored in ops repo (`../ops/runbooks.md`) cover Guardian quarantine handling, PgBouncer pooling misconfig, artifact integrity mismatch, SSE replay issues, and logging pipeline recovery.
- Automation: watchdog tasks auto-quarantine artifacts with integrity failures, restart pods on failed health checks, and rotate settings caches when invalidation fails. The `watchdog-runner` Celery beat process emits heartbeats (`watchdog_runner_lag_seconds`) and raises PagerDuty incidents if it misses two consecutive intervals; Kubernetes liveness/readiness probes restart the runner on failure.
- Fail-closed defaults: if Guardian is unavailable, artifacts remain `PENDING_JUDGMENT`; if Settings is unavailable, new jobs block on snapshot fetch while running jobs continue with embedded snapshots. These scenarios have dedicated alerts and runbooks in [../ops/runbooks.md](../ops/runbooks.md) and `../ops/runbooks.md`.

### 12.3 Incident response workflows & escalation paths

*Purpose: Define how the team reacts to outages or security events.*

- Incident severity levels with defined on-call rotations (Engineering, Security, Product). Playbooks for RBAC breaches, data residency violations, Guardian outages.
- Post-incident reviews required within 48h; actions tracked in ops backlog. Metrics `incident_count_total`, `mttr_minutes`, and `logging_incident_total`.
- Communication templates for customer notifications, regulators, and internal leadership included in `../ops/runbooks.md`; latest redlines stored as `INCIDENT_TEMPLATE` artifacts covering PII disclosure, residency breach, and major outage scenarios.
- Logging ingestion incidents (dropped events or ingest lag > 2 minutes) automatically raise Sev-2, reference RB-LOG-007, and block prod deploys until the pipeline stabilizes for two consecutive collection intervals.
- Upload scanning outages or sustained `upload_scan_error_total` spikes trigger security incidents with [Runbook RB-UPLOAD-SCAN](../ops/runbooks.md#rb-upload-scan); uploads remain disabled (`uploads.enabled=false`) until the pipeline clears and signatures are verified current.

### 12.4 Backup, DR objectives, and failover drills

*Purpose: Maintain data durability and disaster preparedness.*

- Postgres: daily full snapshots + continuous WAL shipping; target RPO ≤ 15 minutes, RTO ≤ 1 hour. Quarterly restore drills documented.
- Object storage: versioning + lifecycle rules; deletion requires dual confirmation. Immutable audit sinks operate under WORM retention policies.
- Redis: persistence optional; rely on recomputation for queues. For critical caches, use managed Redis with cross-zone replicas.
- DR exercises simulate region failure; cross-region read replicas considered once residency waivers approved. Settings and Guardian services replicate configuration backups.
- Region failover playbook (`../ops/runbooks.md (RB-DR-REGION)`): warm standby clusters remain idle but patched, with secrets/Settings snapshots synced hourly. On a primary-region outage the sequence is (1) freeze new job intake, (2) promote the standby Postgres instance with latest WAL, (3) swap object storage endpoints using pre-provisioned secondary containers, (4) update Azure Front Door/DNS records (TTL ≤ 60 seconds) to point to the secondary ingress, (5) run smoke tests (`ops/dr/run_region_cutover.py`) before re-opening job intake. Residency waivers govern whether an org may fail into the paired region; orgs without waivers stay paused until the primary returns.
- After action: once the primary recovers, traffic is rolled back via blue/green cutover, delta data is validated (checksum + manifest diff), and any DSAR/erasure entries executed during the failover are replayed to ensure consistency.
- Diagram: see `overview/tdd/diagrams/dr-region-failover-v1.mmd` for the runbook flow.

<figure class="full-width-diagram">
  <img class="diagram" src="../build/diagrams/overview/tdd/dr-region-failover-v1.svg" alt="Region failover runbook">
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
  <img class="diagram" src="../build/diagrams/overview/tdd/error-flows-v1.svg" alt="Error handling taxonomy">
  <figcaption style="font-size: 0.9em; color: #555;">Error handling taxonomy</figcaption>
</figure>

- Circuits and watchdogs:

  - LLM circuits: OPEN/HALF-OPEN/CLOSED; metrics `llm_circuit_state`, reason codes (`PRIMARY_DEGRADED`, `RATE_LIMIT`). Runbook [RB-LLM-003](../ops/runbooks.md#rb-llm-003).
  - Advisory lock watchdog: metrics `udlock_watchdog_stale_total`, `udlock_lock_age_seconds_p95`; defaults `udlock.max_session_hold_seconds=300`, `udlock.heartbeat.interval_seconds=5`. Runbook [RB-LOCK-006](../ops/runbooks.md#rb-lock-006). `kill_stale=false` in prod; remediation flows through the operator-only endpoint `POST /ops/v1/udlock/{scope}/{key}/mark` which tags the holder, adds trace attribute `lock.triage=manual_review`, and (when explicitly requested) issues `pg_terminate_backend` after human confirmation.
  - Job progress watchdog: metrics `job_watchdog_warning_total`, `job_watchdog_timeout_total`; thresholds driven by `jobs.watchdog.*` settings. Runbook [RB-JOB-WATCHDOG](../ops/runbooks.md#rb-job-watchdog) guides remediation.

- Queues and DLQ:

  - Outbox pattern for notifications with retries/backoff; poison messages routed to DLQ with capped replays and operator alerts.

- Integrity scan DLQ: dead-letter queue `q.integrity.deadletter` captures items exceeding retry budget (`last_error`, `attempts`, `cause`). DLQ processing emits on-call alerts and requires manual triage per `../ops/runbooks.md` runbook.

- Downstream propagation: when a source artifact is quarantined for integrity mismatch, workers walk `manifest.source_artifacts[]` and apply `integrity.downstream_action ∈ {mark_stale, quarantine}` to dependents so UI surfaces NEEDS_REVIEW banners; defaults are `quarantine` for legal deliverables (`COMPOSE_*`, `ATTACHMENT_*`) and `mark_stale` for Analyze outputs per Appendix D.

- SLO guardrails:

  - Guardian judgment P95 ≤ 5m; Compose ≤ 45m P95; upload finalize ≤ 5s. Alerts on burn rates and budget breaches; see §12.6 dashboards.

- **Source material:** `§12`, `§12`, `§10.8`, `../ops/runbooks.md`

- **Priority:** Medium (operational readiness)

______________________________________________________________________

### 12.6 Named dashboards & alert routing

*Purpose: Provide common observability views and bind alerts to runbooks.*

- Guardian SLO & Throughput (SRE): judgment latency P50/P95/P99, error rate, queue depth/backlog age (`guardian_pending_total`, `guardian_pending_oldest_seconds`), submission timeout rate (`guardian_submission_timeout_total`), false-positive ratio (`guardian_quarantine_false_positive_total / guardian_judgment_total`), synthetic success, SLO burn rate.
- Queues & KEDA (SRE): Celery queue depth per lane, replicas, scaling events, DLQ intake and drain, job cancellation spikes (`job_cancellation_total`), watchdog escalations (`job_watchdog_timeout_total`), and review backlog ageing (`review_queue_backlog_total`, `review_queue_oldest_seconds`).
- LLM Cost & Circuit (Platform): tokens in/out, estimated spend vs cap, circuit state per model/provider, fallback reason codes.
- Localization & Policy Engine (Platform/SRE): dashboards and alerting requirements defined in `../automation/lp-engine.md §5` (lookup latency, cache health, compiler cadence, adoption safety signals).
- Reference Manager – Ingestion & Quality (Content Ops/Legal Ops): dashboards and alert thresholds live in `../data/ref-manager.md §5.1` (harvest throughput, freshness, selector health, coverage).
- Reference Manager – Review & Publishing (Content Ops/Legal Ops): see `../data/ref-manager.md §5.1` for backlog, adoption, publish latency, and resource coverage monitors.
- Audit Seal & WORM (SecEng): seal cadence, seal errors, WORM lag, verification status.
- Portal Security (SecEng): download rate per org/user, anomaly triggers, link invalidations, adaptive MFA prompts.
- PHI Detection & HIPAA (SecEng/Compliance): `phi_detection_scan_total`, `phi_detection_positive_total{stage}`, `phi_detection_drift_total`, rescan latency, Guardian quarantines triggered; dashboards link to sampled artifacts for manual review.
- Advisory Locks (SRE): locks held by scope/kind, age percentiles, stale detections, terminations; tied to [Runbook RB-LOCK-006](../ops/runbooks.md#rb-lock-006).
- Logging Pipeline (SRE): ingest lag, drop rate, spool utilization, index health; alerts map to `../ops/runbooks.md (RB-LOG-007)`.
- Upload Scanning (Security): queue depth, scan duration, infected/errored totals, signature freshness metrics; alerts route to [Runbook RB-UPLOAD-SCAN](../ops/runbooks.md#rb-upload-scan).
- Unit Economics & Delivery (PM/SRE): cost per case/org; MoM deltas; top 10 expensive cases; delivery counts and failure rates.

Instrumentation rollout: All dashboards listed here are live in production with paging alerts. SRE and Platform teams control alert thresholds via Settings; when a team pauses ownership (for example, onboarding a new runbook), the associated dashboard can be switched to warning-only mode using the documented change process in `../ops/runbooks.md`.

Alert routing

- Sev-1 pages on: Guardian SLO burn > 2x target 15m; audit seal missed 2 intervals; queue depth > 3× budget 10m.
- All alerts include `dashboard_url`, `runbook_id` (when applicable), and last 5 relevant traces.

### 12.7 Synthetic monitors coverage

*Purpose: Continuously validate critical paths and assumptions.*

- Web: `/readyz` checks RLS GUCs; `/healthz` verifies DB connectivity and cache coherence.
- Guardian: submit synthetic artifacts for both a WP (expect PASS → CLEARED_FOR_USE) and a CD under `review.mode=MANUAL` (expect PASS → OPERATOR_PREP) with known inputs; verifies rule load; latency within SSE SLO.
- Signer: sign a synthetic document against test trust roots; verify TSA/OCSP reachability.
- Settings: activate a safe test bundle; diff preview matches expected; revert; validators pass.
- Watchdog runner: `watchdog-runner` Celery beat schedule fires every minute, invoking all watchdog tasks (Guardian backlog, job progress, advisory locks, integrity queue). A self-check endpoint `/ops/watchdog/status` reports the most recent execution timestamp and per-task durations; synthetic monitor verifies the timestamp delta stays \< 120s. Metrics `watchdog_runner_lag_seconds`, `watchdog_runner_missed_total`, and log-based alerts catch missed beats; if the runner stalls, [Runbook RB-JOB-WATCHDOG](../ops/runbooks.md#rb-job-watchdog) and Appendix B.3 prescribe manual invocation plus root-cause remediation before re-enabling automation.
- Portal: download approved synthetic artifact; ETag/Range behavior validated; portal invalidation simulated.
- Reference Manager (EU-REFERENCE tenant): synthetic monitoring, residency assertions, and escalation criteria are documented in `../data/ref-manager.md §5.3`.
- Alert thresholds: burn-rate SLO alerts and synthetic failures must page on-call with proper runbook IDs.

### 12.8 Quotas & metering

*Purpose: Enforce fair‑use and protect performance budgets.*

- Quotas: per‑org limits on uploads/day, concurrent jobs, portal downloads/min; Settings expose knobs and per-org overrides.
- Enforcement: API checks at submission and per request; friendly 429s with `Retry-After` + guidance; dashboards for sustained breaches.
- Metering: counters for usage; monthly exports; tie-in with FinOps budgets; anomaly detection.
- Source material: `§12.8`, `§12.9`

### 12.9 Cost dashboards & transparency (informative)

- LLM Registry §6 maintains the authoritative FinOps dashboards, alert thresholds, and staging drill requirements; platform teams ensure those dashboards stay green before release.
- Portal usage transparency and export workflows follow the web-app specification (§2.2); parity between staff and portal views is validated with synthetic monitors and feature flags gate exposure.

### 12.10 Business continuity & degraded operations

*Purpose: Outline how teams sustain service when automation or guardians fail.*

- **LLM outage:** The `ModelFailoverOrchestrator` automatically advances to the next healthy provider in the documented `fallback_chain`; envelopes capture the substitute model and parity hash. If every fallback is unhealthy the queue transitions to `PAUSED_AWAITING_PROVIDER`, workers stop launching new runs, and automation polls health every 60 seconds (three consecutive greens required) before resuming. Customer notifications only trigger if the pause exceeds 15 minutes or impacts SLA targets.
- **Guardian impairment:** Freeze approvals that rely on Guardian PASS/WARN judgments; manual reviewers follow Appendix B.1 in `../platform/guardian.md` and log judgments as `MANUAL_GUARDIAN_JUDGMENT` artifacts until the service recovers.
- **Transcription fallback:** The `SpeechFailoverController` retries against the next speech provider/region in `speech.jobs[].fallback_chain` with full equivalence logging. When the chain is exhausted jobs enter `PAUSED_AWAITING_PROVIDER` and automatically resume once health probes confirm recovery; no human transcription is used in the automated path.
- **Communication cadence:** Duty Manager sends initial update within SLA (§1.6) and hourly until resolved; final customer notice includes timeline, data impact, and remediation.
- **Drills:** Semi-annual BCP exercise simulating combined Guardian + LLM outage; evidence stored as `BCP_DRILL_REPORT` artifacts linked in `../ops/runbooks.md`.

### 12.11 Fail-closed behaviors matrix

*Purpose: Summarize safety defaults, their downstream impact, and where to find remediation guidance.*

| Subsystem | Fail-closed behavior | User impact | Runbook |
|---|---|---|---|
| Guardian | Rejects submissions; artifacts remain `PENDING_JUDGMENT` until service recovers | New approvals paused; portal shows OPERATOR_PREP backlog | Appendix B.1 |
| Settings Service | New jobs block on snapshot fetch; running jobs continue with embedded snapshots | Operators see queue backlog; activation UI disabled | [Runbook RB-GOV-008](../ops/runbooks.md#rb-gov-008) |
| Audit seal / WORM | Portal deliveries blocked if seal chain breaks for >1 interval | Reviewers cannot promote artifacts; portal download attempts 503 | `../ops/runbooks.md (RB-AUDIT-004)` |
| Residency policy guard | Jobs error with `RESIDENCY_POLICY_BLOCK` on drift | Org must adjust settings or seek waiver before resubmission | [Runbook RB-RES-BLOCK](../ops/runbooks.md#rb-res-block) |
| LLM provider circuit | Queue enters `PAUSED_AWAITING_PROVIDER`; health probes run every 60 s | Compose/Analyze jobs paused; auto-resume after consecutive green probes; manual drafting requires waiver | [Runbook RB-LLM-003](../ops/runbooks.md#rb-llm-003) |

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
- Coverage targets: ≥ 90% for every module (unit + property) as mandated by §2.3; CI fails when thresholds drop below that line.

### 13.3 Governance/privacy acceptance suites

*Purpose: Validate compliance requirements continuously.*

- DSAR/erasure flows, legal hold enforcement, field masking, and break-glass logging validated with synthetic cases.
- Residency matrix: activations that violate regional policies are rejected with `VALIDATION_ERROR`; runtime pre-flight blocks cross-jurisdiction runs (`RESIDENCY_POLICY_BLOCK`).
- Privacy API Spectral stubs warn until GA, then block; endpoints declare security and HMAC; examples avoid PII.

#### 13.3.1 Detection & masking controls (binding)

**Breadcrumbs:** Implementation `packages/core/privacy/detection_suite.py::run_quality_suite`, Tests `tests/privacy/test_detection_suite.py::test_golden_corpora_thresholds`, Observability Grafana “Privacy & Masking QA” panel (metric `phi_detection_drift_total`).

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

- **Source material:** `§12`, `§14.4`, `§12.9`, `§10.8`, [`../platform/settings.md Appendix A`](../platform/settings.md#appendix-a-settings-key-map-traceability-index)

- **Priority:** Medium (QA & compliance alignment)

______________________________________________________________________

## 14) Operations playbooks & lifecycle

- Glossary: Appendix I captures retention, legal hold, and governance terms referenced in this chapter.

### 14.1 Tenant provisioning & offboarding

*Purpose: Standardize customer lifecycle in ops tools.*

- Provisioning: create org in Keycloak, configure domains (SPF/DKIM), set residency allowlists, budgets, templates, rotate initial secrets. Onboard staff via invites with role assignments.
- Offboarding: disable logins, export data with tamper-evident bundles, revoke keys, enforce retention/erasure, archive audit seals. Checklist recorded in `../ops/runbooks.md`.

#### 14.1.1 Legacy case import (roadmap)

*Purpose: Provide an inbound migration path that mirrors export guarantees and preserves chain-of-custody evidence.*

- Legacy case import supports both ops-assisted and self-service flows. Ops-assisted imports use `scripts/import/validate_case_bundle.py` to verify manifest signatures, residency tags, and hashes before queueing the `case_import` Celery task; every run logs to `ops/<job_id>__case_import_log.json` and emits `CASE_IMPORT_ATTEMPT` audit events (see `../ops/runbooks.md` runbook). Self-service org admin workflows (`POST /ops/case-imports`, guarded by `import.legacy_cases.enabled`) apply deterministic ID mapping, replay Guardian review states, and produce reconciliation reports for reviewer confirmation. Portal visibility stays blocked until the service approves the imported artifacts.
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
  <img class="diagram" src="../build/diagrams/overview/tdd/dsar-erasure-v1.svg" alt="DSAR hard-purge workflow">
  <figcaption style="font-size: 0.9em; color: #555;">DSAR hard-purge workflow</figcaption>
</figure>

#### 14.2.1 DSAR/erasure mode (binding)

**Breadcrumbs:** Implementation `ops/dsar/erasure_job.py::run_erasure`, Tests `tests/privacy/test_dsar_erasure.py::test_hard_purge`, Observability Grafana “DSAR Fulfillment” dashboard (metric `dsar_erasure_completed_total`).

*Purpose: Support hard-purge erasure requests without compromising provenance.*

- Settings: `compliance.erasure_mode ∈ {'off', 'hard_purge'}` (ORG) toggles hard purge; `compliance.subject_hkdf_salt` (SYSTEM, KMS-backed) seeds deterministic subject hashes. See [`../platform/settings.md Appendix A`](../platform/settings.md#appendix-a-settings-key-map-traceability-index) for key traceability.

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
- Escape hatch: should KMS become unavailable, documented manual signing path (`../ops/runbooks.md (RB-SIGNER-HSM)`) allows temporary softkey use capped at 24 h with post-incident review.

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
- Spec/code parity gate: `docs/config/settings_key_skip.txt` must remain empty; CI and release pipelines fail immediately if any Appendix E key lacks implementation coverage or automated tests.
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
- Mitigations: continuous evals, rule dry-run/diff, automated waiver stamping, cross-training reviewers, dual runner fallback (`agents.langgraph.runner`), staged LangGraph upgrades with canary tests, plus dedicated DevOps enablement (Terraform/service-mesh training sprints, pairing during first three production releases, and annual certification of `../ops/runbooks.md` runbooks for infra owners).
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
- Milestone M1 (Analyze LangGraph GA) → Product epic `P-123`; depends on App.A diagrams, §6.7/§6.11 completion, [Runbook RB-LLM-003](../ops/runbooks.md#rb-llm-003) drill.
  - Milestone M2 (Portal messaging GA) → Product epic `P-207`; references §11.6 and Appendix J; depends on App.A A.8 flow and security review gates (§9.11).
- Milestone M3 (FinOps deploy guard) → SRE epic `SRE-88`; depends on §8.7, §12.9, FinOps dashboards wiring acceptance.
- Dependency notes: provider template updates (Appendix D) tracked in backlog; cross-team sequence captured in roadmap doc linking to this section.

______________________________________________________________________

### 15.9 Architectural decision records (binding)

**Breadcrumbs:** Implementation `docs/adr/README.md`, Tests `packages/docs_tooling/src/doc_tools/check_adr_index.py::main`, Observability CI job “docs-adr-lint” with badge in Docs Quality dashboard.

*Purpose: Ensure significant technical choices remain discoverable, immutable, and supersedable.*

- ADRs live under `docs/adr/` and follow GitLab’s lightweight template (`Title, Context, Decision, Consequences, Status`). `docs/adr/README.md` indexes active, superseded, and deprecated entries; this TDD’s front matter `related_adrs` highlights the decisions most tied to the current scope.
- Lifecycle: new ADRs start as **Draft**, graduate to **Accepted** once Architecture + Security approve, and move to **Superseded** when a follow-on ADR renders the prior decision obsolete. Status changes require PR review plus an update to the ADR index table.
- Integration points: breaking API or security changes cannot transition this TDD to **Implementable** or **Implemented** without a corresponding ADR (e.g., `ADR-0002-api-versioning-and-sunset.md` for the deprecation policy, `ADR-0001` covering Guardian judgments/waivers). Cross-reference IDs appear throughout the document (see §3.9, §7.1, §10.0) to keep provenance intact.
- Tooling: `make adr:new` scaffolds numbered ADRs; CI verifies headers/metadata and blocks merges when ADR titles, filenames, or statuses drift from the index. Quarterly governance reviews audit ADR freshness and ensure open decisions align with App.K controls.

______________________________________________________________________

## 16) Search & knowledge retrieval

*Service specification:* [`Search & Indexing`](../data/search-index.md) captures ingestion pipelines, vector enrichment, API surfaces, and operational posture for discovery features.

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

- **Source material:** `§16`, `§16`, `§16`, `§12.9`, [`../platform/settings.md Appendix A`](../platform/settings.md#appendix-a-settings-key-map-traceability-index) decision log

- **Priority:** Medium (keeps roadmap aligned)

______________________________________________________________________

## Appendices (link targets)

- **App.A** System context & sequence diagrams *(source: App.A)*
- **App.B** Threat model catalog *(source: §14.4, App.B)*
- **App.C** Data classification & retention matrices *(source: App.C, §15)*
- **App.D** Canonical artifact catalog *(source: App.F)*
- **See also:** `../automation/langgraph-agents.md#appendix-a-agent-schemas-error-taxonomy` *(agent schemas & error taxonomy)*
- **See also:** [`../platform/settings.md Appendix A`](../platform/settings.md#appendix-a-settings-key-map-traceability-index) *(source: §5.4)*
- **App.F** API reference snippets / example payloads *(source: §10.8)*
- **App.G** ERD and schema migrations history *(source: App.I)*
- **App.H** Ops runbooks & health check playbooks *(source: §12.2, Appendix H)*
- **App.I** Glossary and taxonomy *(source: Glossary, §16 taxonomy notes)*
- **App.J** SQL policy patterns *(source: §4.4, §11.6)*
- **App.K** Controls assurance map *(source: §2.2, §12, §14)*
- **App.L** Benchmark baselines *(source: [`platform-runtime §3`](../platform/runtime.md#3-api-contract-binding), §8, §12)*
- **App.M** Environment & dependency matrix *(source: [`platform-runtime §3`](../platform/runtime.md#3-api-contract-binding), §14.8)*
- **App.N** Privacy controls traceability *(source: §2.2, §14.2)*
- **App.O** Active waivers ledger *(source: §3.8, §7.1.1, §14.9)*
- **App.P** Third-party & OSS notices *(source: §13.6, App.P)*
- **App.Q** Sub-processors & DPAs *(source: §3.7, §8, §14.3)*
- **App.R** Data lineage maps *(source: §5.6, §6, §7)*
- **App.S** Ownership & RACI map *(source: §1.5, §15)*
- **App.T** Traceability matrix *(source: §3.8, §7, §10, §12.1, §12.6)*
- **See also:** `../experience/web-app.md#appendix-a-real-time-payloads-components` *(web app SSE payloads & job widget reference)*
- **See also:** `../customer/communications.md#appendix-a-event-catalog-streaming-contract` *(SSE event catalog & replay contract)*

______________________________________________________________________

## Appendix A — System context & sequence diagrams (normative)

*Purpose: Provide authoritative visuals of service boundaries and key workflows.*

### A.1 System context

- Updated diagram (`overview/tdd/diagrams/system-context-v1.mmd`) depicting web, workers, supporting services, external dependencies, and trust boundaries. Includes overlays for mTLS domains and network policies.

### A.2 Upload → Guardian → Approve

- Mermaid sequence source `platform/guardian/diagrams/upload-guardian-approve-v1.mmd`; shows client upload, staging, artifact creation, Guardian submission, reviewer approval, SSE notifications, and portal invalidation.

### A.3 Signing & delivery

- Mermaid sequence source `overview/tdd/diagrams/signing-delivery-v1.mmd`; covers signing request, TSA/OCSP validation, artifact promotion, link generation, and client download with ETag/If-Match.

### A.4 Error flows

- Diagram source `overview/tdd/diagrams/error-flows-v1.mmd`; illustrates TRANSIENT/POLICY/INPUT/INTEGRITY/CONCURRENCY paths with retries, quarantine, and user feedback.

### A.5 Approvals UX

- Flow source `platform/guardian/diagrams/approvals-ux-v1.mmd`; illustrates staff review, QA, approve/reject, and portal invalidation.

### A.6 Portal invalidation

- Sequence `platform/guardian/diagrams/portal-invalidation-v1.mmd`; shows invalidation path and 403 behavior.

### A.7 Analyze/Compose pipeline

- Sequence `automation/langgraph-agents/diagrams/analyze-compose-v1.mmd`; illustrates LangGraph lanes, artifact writes, and Guardian readiness.

### A.8 Manual/Agent Edit flows

- Flow `platform/guardian/diagrams/approvals-edit-flows-v1.mmd`; shows editor flows and promotion/demotion behavior.

### A.9 Residency & policy enforcement

- Sequence `automation/lp-engine/diagrams/residency-policy-enforcement-v1.mmd`; maps settings activation through LPE compile, OPA bundle reload, worker/Guardian checks, portal fetch-time validation, and waiver stamping.
- Diagrams maintained via `diagram:diff` CI job; PRs must include source updates (Mermaid/Draw.io) alongside exported SVG/PNG.

______________________________________________________________________

## Appendix B — Threat model catalog

*Purpose: Centralize high‑value threats, mitigations, and validations (STRIDE).*

### B.1 STRIDE summary (illustrative; see `../ops/runbooks.md` for runbooks)

- Spoofing (identity):
  - Vector: forged inter‑service calls
  - Mitigations: mTLS, HMAC signing ([Platform Runtime §3.5](../platform/runtime.md#35-service-to-service-request-signing-binding)), short‑lived tokens, audience scoping
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

- RLS bypass via pooling misconfig → AdmissionPolicy blocks statement pooling; fail‑closed canaries (§4.4, [Identity Appendix A (operational canaries)](../platform/identity.md#appendix-a-sql-policy-patterns-binding)).
- Residency leakage to non‑CA endpoints → mesh egress allowlist; region allowlist settings; Guardian waiver stamping (§3.8, §7.1.1).
- Prompt injection & policy drift → safety harness, golden‑set tests, QA gates, Guardian policy checks (§8.4, §7.1).
- SSE replay abuse → Last‑Event‑ID handling, snapshot rules, token‑bound streams (§10.8).
- Artifact integrity tamper → SHA‑256 ETag, WORM audit sink, integrity sweeps (§5.3, §12.1).

### B.3 Abuse controls (illustrative)

- Portal scraping → rate limits, anomaly triggers, forced invalidation, step-up MFA (§11.2.2, §12.8).
- Messaging misuse → content scanning, attachment limits, abuse reporting, audit trails (§11.6).
- Brute forcing APIs → global/org rate limits, IP throttles, 429 guidance, runbooks (§10.7, §12.6, `../ops/runbooks.md`). *Purpose: Document top risks, mitigations, and residual risk ratings.*
- **Threat tables:** Expanded STRIDE matrix covering RLS bypass, region leakage, LLM prompt exfiltration, Guardian rule poisoning, signature spoofing, SSE replay, and portal phishing.
- **Mitigation mapping:** For each threat, list preventive/detective controls (section references) and automation coverage (synthetics, alerts). Residual risk rated (Low/Medium/High) with owner.
- **Abuse cases:** Scenarios such as malicious reviewer approval, compromised client account, and mass download scraping with corresponding throttles and anomaly detection.
- **Updates:** Threat catalog reviewed quarterly by Security + Architecture; changes tracked in decision log and referenced in §15.3.

### B.4 Abuse prevention plan & fraud detection checks (normative)

- Governance: Abuse triad (Security Engineering Lead, Product Abuse PM, SRE) meets monthly to review abuse dashboards, App.T traceability rows, and new reports from Support. Action items flow into the security backlog with SLA tracking.
- Baseline detectors:
  - API anomaly detector: `api_abuse_scorer` job inspects rolling windows (IP/user/org) for unusual verb/method combinations and increments `api_suspect_request_total{reason}`. Score > threshold auto-enqueues an approval block pending human review.
  - Portal download sentinel: `portal_download.anomaly_score` (needs trend \< 1.5× baseline). 3 consecutive breaches trigger automatic `portal_link_invalidated` + step-up MFA requirement; `../ops/runbooks.md (RB-ETAG)` handles follow-up messaging.
  - Messaging fraud rules: heuristics for mass outbound, URL reputation hits, and attachment mismatch log to `messaging_abuse_detected_total` and quarantine threads until Guardian re-approves.
- Shadow/soak controls: High-risk pipeline changes (payment integrations, new export endpoints) must run in shadow mode (see §6.13) for ≥7 days with abuse detectors enabled; only after the review sign-off do we flip “serving” flags.
- Threshold waivers: temporary relaxations for shadow soaks or customer beta programs use `abuse.shadow.threshold_per_org` settings with explicit expiry (≤30 days) and are catalogued in App.O. Activation lints reject waivers without matching expiry and justification.
- For every new abuse vector, engineering must add: (1) detector metric + alert, (2) runbook entry (`../ops/runbooks.md`), (3) test fixture covering expected vs blocked flows, (4) traceability row in App.T.

______________________________________________________________________

## Appendix C — Data classification & retention matrices

*Purpose: Define classification, masking, storage location, and baseline retention.*

### C.1 Classification table

| Class | Examples | Masking | Storage | Default retention |
|---|---|---|---|---|
| PUBLIC | docs, marketing | none | object storage (public site) | n/a |
| INTERNAL | non‑PII ops logs | redact sensitive fields | object storage (private) | life of case + 2y |
| PII | names, contact info | REDACT/HASH in logs | object storage (private) | life of case + 2y |
| SENSITIVE_PII | health, minors | REDACT in UI logs; NULL in JSON | object storage (private, KMS) | case + 2y (HIPAA may override) |
| HIPAA_PH | medical | REDACT everywhere; no excerpts | object storage (private, KMS) | org policy (shorter) |

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
- PolicyContext retention metadata and override governance are defined in `../automation/lp-engine.md §2.3` and Appendix C; this appendix references those digests only when mapping artifact classes to residency and retention groups.

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

| Artifact type | Purpose | Notes |
|---|---|---|
| EXHIBIT_RAW | Original exhibit uploads (PDF/image/archive) | Stored under `docs/raw/`; Guardian enforces format allowlist prior to parsing. |
| EXHIBIT_TEXT | Parsed/ocr text companion for exhibits | Linked to `EXHIBIT_RAW` via `source.inputs[]`; feeds Analyze search. |
| COURT_DOC_RAW | Court filings or orders as uploaded | Similar handling to `EXHIBIT_RAW`; maintains original casing. |
| COURT_DOC_TEXT | Structured text extraction for court documents | Used for diffing, timeline extraction, and Compose references. |
| EMAIL_RFC822 | Raw RFC822 email payloads (including headers) | Stored encrypted; normalized to `EMAIL_TEXT` and attachments. |
| EMAIL_TEXT | Parsed email body (plaintext/HTML converted) | Preserves header metadata for Guardian/Compose citations. |
| EMAIL_ATTACHMENTS | Individual artifacts emitted per attachment | Guardian scans each attachment; retained under case `docs/attachments/`. |
| FINANCIALS_RAW | Spreadsheet or CSV financial uploads | Normalized before conversion; preserved for audit. |
| FINANCIALS_TABLE | Structured table representation of financial artifacts | Stored as JSON/CSV; downstream analytics consume. |
| MEMO_TEXT\_\* | Staff/comms memos with deterministic suffix per template | Used by Guardian to validate memo templates and approvals. |

Artifact table

| Artifact type | Directory / pattern | Exclusive | Manifest pointer | Notes |
|---|---|---|---|---|
| TRANSCRIPT | `transcript/<job_id>__transcript.txt` | **Yes** | `<transcript>.manifest.json` | Header includes case, source, language, hashes |
| AUDIO_NORMALIZED | `audio/<job_id>__<normalized_name>` | No | n/a | PCM 16 kHz mono copy for reproducibility |
| OUTLINE_JSON | `analysis/<job_id>__outline_v1.json` | No | `<outline>.manifest.json` | Hierarchical outline for Compose |
| TIMELINE_JSON | `timeline/<job_id>__timeline_v1.json` | No | `<timeline>.manifest.json` | Normalized timeline events (speakers, timestamps, UUID anchors) |
| ENTITIES_JSON | `analysis/<job_id>__entitIES_v1.json` | No | `<entities>.manifest.json` | Deterministic UUID per entity/relationship |
| ISSUES_JSON | `analysis/<job_id>__issues_v1.json` | No | `<issues>.manifest.json` | Issues presented or evident |
| FACTS_JSON | `analysis/<job_id>__facts_v1.md` | No | `<facts>.manifest.json` | Facts as they are presented |
| GAPS_JSON | `analysis/<job_id>__gaps_v1.md` | No | `<gaps>.manifest.json` | information gaps and other unknowns |
| REPORT_MD | `analysis/<job_id>__analyze_report_v1.md` | No | `<report>.manifest.json` | Human readable report containing internal notes, QA logs and run logs |
| COMPOSE_CLIENT_MD/DOCX | `docs/<job_id>__compose_client_v1.md\|docx`  | **Yes** | `<compose_client>.manifest.json` | |
| COMPOSE_LAWYER_MD/DOCX | `docs/<job_id>__compose_lawyer_v1.md\|docx`  | **Yes** | `<compose_lawyer>.manifest.json` | |
| COMPOSE_BUNDLE_EXCERPT_MD | `docs/<job_id>__compose_bundle_v1.md` | **Yes** | `<compose_bundle>.manifest.json` | Excerpt for bundle |
| COMPOSE_STAFF_REPORT_MD | `docs/<job_id>__compose_staff_report_v1.md` | No | `<compose_staff_report>.manifest.json` | QA staff notes |
| COMPOSE_QA_REPORT_MD | `docs/<job_id>__compose_qa_report_v1.md` | No | `<compose_qa_report>.manifest.json` | QA outcomes |
| DPIA_RECORD | `privacy/<job_id>__dpia_v1.json\|md`         | No | `<dpia>.manifest.json` | |
| ROPA_RECORD | `privacy/<job_id>__ropa_v1.json\|md`         | No | `<ropa>.manifest.json` | |
| AUDIT_SEAL | `ops/<timestamp>__audit_seal_v1.json` | No | `<audit_seal>.manifest.json` | Rolling Merkle root |
| SIGNATURE_CERT | `docs/<job_id>__signature_cert_v1.json` | No | `<signature_cert>.manifest.json` | Signer certificate bundle |
| ATTACHMENT_RAW | `docs/<job_id>__attachment_raw_v1.bin` | No | `<attachment_raw>.manifest.json` | Source binary for portal messaging/client uploads; Guardian-gated |
| ATTACHMENT_TEXT | `docs/<job_id>__attachment_text_v1.json\|md` | No | `<attachment_text>.manifest.json` | |
| ERASURE_JOURNAL | `privacy/<job_id>__erasure_journal_v1.json` | No | `<erasure_journal>.manifest.json` | Hard-purge DSAR evidence; subject hashed with HKDF salt |
| DESTRUCTION_CERT | `privacy/<job_id>__destruction_cert_v1.json` | No | `<destruction_cert>.manifest.json` | Case-level destruction attestation; links retention trigger + tombstone IDs |
| CHAT_SESSION_JSON | `ops/<session_id>__chat_staff.jsonl` | No | `<chat_session>.manifest.json` | Staff Copilot conversation log with citations + moderation metadata |
| CHAT_SESSION_CLIENT_JSON | `ops/<session_id>__chat_client.jsonl` | No | `<chat_client_session>.manifest.json` | Client portal chat conversation; portal-visible subset; Guardian-audited |
| CHAT_SUMMARY_JSON | `analysis/<job_id>__chat_summary_v1.json` | No | `<chat_summary>.manifest.json` | Optional summarization of chat session; includes references and moderation outcome |
| AGENT_EDIT_PROPOSAL_MD | `analysis/<job_id>__edit_proposal_v1.md` | No | `<agent_edit_proposal>.manifest.json` | AI-assisted edit proposal human-reviewed before promotion |
| AGENT_EDIT_DIFF_JSON | `analysis/<job_id>__edit_diff_v1.json` | No | `<agent_edit_diff>.manifest.json` | Machine-readable diff for Agent edit proposals |

- **NOTE:** Replace "v1" with v{n}

### D.1 Chat assistant artifacts (binding)

**Breadcrumbs:** Implementation `packages/core/assistants/artifacts/chat.py::ChatArtifactWriter`, Tests `tests/core/assistants/test_chat_artifacts.py::test_manifest_integrity`, Observability Grafana “Assistant Sessions” dashboard (metric `assistant_chat_artifact_total`).

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

**Breadcrumbs:** Implementation `packages/core/analysis/timeline.py::TimelineArtifactWriter`, Tests `tests/core/analysis/test_timeline_artifact.py::test_uuid_stability`, Observability Grafana “Timeline” panel (metric `timeline_artifact_total`).

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

See [`../platform/settings.md Appendix A`](../platform/settings.md#appendix-a-settings-key-map-traceability-index) for the complete key catalog, traceability matrix, and telemetry obligations.

______________________________________________________________________

## Appendix F — API reference pointers (informative)

*Purpose: Direct integrators to the canonical service specifications that now host API payloads, header contracts, and signing examples.*

- [Platform Runtime §3.1](../platform/runtime.md#31-external-interfaces-binding) keeps the authoritative `ApiError.code` catalog, rate-limit and deprecation response examples, and the required header matrices for REST and CORS interactions.
- [Platform Runtime §3.5](../platform/runtime.md#35-service-to-service-request-signing-binding) documents the HMAC request-signing contract (headers, canonical string, replay safeguards) and [§3.5.1](../platform/runtime.md#351-key-rotation-flows-binding) captures key rotation flows and denial procedures.
- [Worker Cluster §3.4–§3.7](../automation/worker-cluster.md#34-idempotency-store-replay-headers-binding) define the idempotency store, job SSE replay behaviour, and upload finalization schema used by SDKs and operators.
- [Guardian §3.6](../platform/guardian.md#36-review-rest-endpoints-binding) owns the review REST endpoints and associated optimistic-locking rules.
- [Digital Signer §3.1](../data/digital-signer.md#digital-signer-external-interfaces) provides the canonical signing and verification request examples.

## Appendix G — ERD & schema migrations history

*Purpose: Capture database structure evolution and reference diagrams.*

- **ERD:** `docs/erd/uDocket-erd-v1.svg` exported from Draw.io source with entity descriptions matching §5.1.
- **Migration ledger:** Table summarizing major migrations (ID, date, purpose, impacted tables). Highlights backward-compatibility considerations and deployment notes.
- **Schema policies:** Links to lint rules ensuring ORM uses secure views, triggers enforcing immutability, and migration templates for advisory locks or partitioning.
- **Tooling:** Instructions for generating ERD updates and running schema diff checks prior to migration PR merge.

______________________________________________________________________

## Appendix H — Runbook catalog references

*Purpose: Point platform teams to the maintained runbook library without duplicating procedures in this document.*\
*Contract: Operational playbooks reside under `docs/runbooks/` and service-specific specifications; this appendix links to those sources.*\
*State: Runbook owners track RB identifiers, alert bindings, and evidence requirements in the referenced documents.*\
*Failure modes & retries: `python -m doc_tools.manage_docs --lint` flags missing runbook links; update the runbook catalog when adding or retiring alerts.*\
*Observability: Docs lint metric `docs_runbook_missing_total` and OnCall drill analytics monitor coverage.*

- **Platform runbooks:** `../ops/runbooks.md`
- **Settings Registry runbooks:** [`../platform/settings.md Appendix D`](../ops/runbooks.md#settings-registry--83-runbooks--drills-binding)
- **Guardian runbooks:** [`../platform/guardian.md Appendix B`](../platform/guardian.md#83-runbooks-drills-binding)

## Appendix I — Glossary & taxonomy

This glossary has moved to a dedicated appendix page. See: tdd/appendices/glossary.md

## Appendix J — SQL policy patterns (normative)

*Purpose:* Provide quick references for cross-cutting SQL governance while directing readers to the owning specs.

- Identity & Access (`identity.md#appendix-a--sql-policy-patterns-binding`) owns RLS helpers, masking, and canary guards.
- Communications (`../customer/communications.md#appendix-b--database-enforcement-patterns`) documents download token and messaging RLS requirements.
- Guardian (`guardian.md#appendix-c--integrity-scan-queue`) covers quarantine workflows and integrity sweeps.
- Platform Runtime (`platform-runtime.md#4-state-management-binding`) tracks partition/retention governance.

______________________________________________________________________

## Appendix K — Controls assurance map

*Purpose: Link external controls (SOC 2, ISO 27001, internal policies) to evidence inside this TDD.*

Quick crosswalk (illustrative)

| Control family | See |
|---|---|
| SOC2 CC1 / ISO 5 | §2, §15.3, App.S |
| SOC2 CC6 / ISO 9 | §4, App.J |
| SOC2 CC7 / ISO 12 | §12, §14.5, Appendix H |
| SOC2 CC8 / ISO 14 | [`platform-runtime §3`](../platform/runtime.md#3-api-contract-binding), §12.5, App.L |
| SOC2 PI / ISO 18 | §2.2, §14.2, App.N |
| Vendor CUECs | §3.7, §8, App.Q |

HMAC key inventory

| Service → Service | Key ID | Last rotated (UTC) | Evidence bundle |
|---|---|---|---|
| web → guardian | `svc-web-guardian-v3` | 2025-09-12T14:30Z | `ops/security/key_rotation/guardian_2025-09-12.json` |
| worker → settings | `svc-worker-settings-v4` | 2025-08-01T09:00Z | `ops/security/key_rotation/settings_2025-08-01.json` |
| guardian → signer | `svc-guardian-signer-v2` | 2025-07-18T16:45Z | `ops/security/key_rotation/signer_2025-07-18.json` |

Key rotation calendar (rolling 90 days)

| Upcoming rotation | Owners | Window | Notes |
|---|---|---|---|
| `svc-web-guardian-v4` | Security Eng Lead, Platform SRE | 2025-12-05 → 2025-12-07 | Requires APP.SEC-117 approval; pre-stage secret in Key Vault |
| `svc-worker-settings-v5` | Settings Service TL, Security Eng Lead | 2026-01-08 → 2026-01-10 | Align with Settings deploy freeze lift |

| Control ID / Policy | Scope | Primary coverage (Section/App) | Evidence artifact(s) | Status |
|---|---|---|---|---|
| SOC2 CC1.1 / ISO 5.1 | Governance & principles | §2 Core principles; §15.3 Risks | App.K map, App.O waivers ledger, decision log exports | Pass |
| SOC2 CC6.x / ISO 9 | Access control | §4 Identity & RLS; App.J SQL policies | `case_secure`/`artifact_secure` views, Settings activation audit trail ([`../platform/settings.md Appendix A`](../platform/settings.md#appendix-a-settings-key-map-traceability-index)) | Pass |
| SOC2 CC7.x / ISO 12 | Operations & change | §12 Observability; §14.5 Change mgmt | `../ops/runbooks.md` runbooks, Guardian/Signer synthetics, deployment playbooks | Pass |
| SOC2 CC8.x / ISO 14 | Availability & resilience | [`platform-runtime §3`](../platform/runtime.md#3-api-contract-binding) topology; §12.5 capacity | App.L benchmarks, autoscaling dashboards, synthetic monitor reports | Pass |
| SOC2 PI1 / ISO 18 | Privacy & retention | §2.2 regulatory constraints; §14.2 retention | App.N privacy traceability matrix, DPIA/ROPA artifacts | Pass |
| SOC2 CUEC / Vendor reviews | Third-party oversight | §3.7 external integrations; §8 LLM governance | Provider registry health logs, evidence store envelopes, vendor reassessment checklist | Pass |
| Internal POL-SC-01 | Security incident response | §12.3 incident workflows; §14.9 disclosure | Incident register exports, security.txt contact, on-call rotation docs | Pass |
| Internal POL-DS-02 | Data residency | §3.8 region enforcement; §7.1 Guardian judgments | Egress AuthorizationPolicy manifests, App.O waiver entries, ops logs `RESIDENCY_POLICY_BLOCK` | Pass |
| Internal POL-AU-01 | Audit & approvals | §10 API contracts; §11 approvals UX | Guardian history, audit_event partitions, reviewer swap algorithm logs | Pass |
| Internal POL-BCP-03 | Business continuity | §12.10 BCP drills; `../ops/runbooks.md` runbooks | `BCP_DRILL_REPORT` artifacts, incident templates | Pass |

Controls mapped here drive quarterly evidence reviews. Each entry references runbooks, dashboards, or artifacts cited in the final column; missing evidence must be captured before release sign-off.

______________________________________________________________________

## Appendix L — Benchmark baselines

*Purpose: Capture recent performance and cost baselines that back the documented SLOs.*

| Workload | Date (UTC) | Load profile | P50 / P95 latency | Cost / tokens | Source |
|---|---|---|---|---|---|
| Web API (`GET /api/v1/cases`) | 2025-09-30 | 1k virtual users, 50 RPS step | 0.112 s / 0.238 s | n/a | k6 run `benchmarks/api_caselist.json`, Grafana `web_http_latency_seconds` |
| Guardian judgment decision | 2025-10-05 | 500 concurrent submissions, 5k/day | 48 s / 242 s | n/a | Synthetic job `guardian_slo.yaml`, `guardian_judgment_latency_seconds` |
| Compose client deliverable | 2025-10-11 | Transcript 9k tokens, default templates | 8.3 min / 21.4 min | 58k tokens | LangGraph harness `compose_benchmark.py`, `llm_cost_estimate_total` |
| Analyze summary lane | 2025-10-11 | Transcript 9k tokens, 4 exhibits | 6.1 min / 13.7 min | 42k tokens | LangGraph harness `analyze_benchmark.py`, `agent_lane_duration_seconds` |
| Portal DOCX download 25 MB | 2025-09-28 | 500 clients, CDN disabled | 310 ms / 480 ms TTFB | n/a | Locust scenario `portal_download.py`, Nginx access logs |

Benchmarks run at least quarterly and after significant infra upgrades using the dedicated synthetic suite (`tests/synthetic/perf/*`). Results update App.L and dashboards referenced in §12.6; deviations ≥10% trigger review prior to release, with raw outputs archived under `ops/perf/<date>/`.

______________________________________________________________________

## Appendix M — Environment & dependency matrix

*Purpose: Document supported platform versions per environment and upgrade cadence.*

| Component | Dev/Staging | Production | Upgrade policy | Notes |
|---|---|---|---|---|
| Kubernetes | 1.29 | 1.28 | Minor upgrades every 6 months; patch monthly | Managed AKS clusters with PodSecurity restricted profile; next prod upgrade Q1 2026; baseline CIS AKS v1.29 |
| Docker Compose (dev) | 2.24.x | n/a | Follow Docker Desktop GA; pin via `.docker/compose-version` | Required for local parity stack (`make stack.up`, wrapping the dev compose overlay); validated weekly via CI smoke; includes Postgres, Redis, Guardian, Signer, Settings, workers |
| Service mesh (Istio) | 1.21.1 | 1.20.4 | N-1 support; canary namespace before prod rollout | mTLS enforced cluster-wide; cert TTL 24h; last prod bump Jul 2025; next cadence review Apr 2026 |
| Postgres | 15.6 | 15.6 HA | Major every 18 months; logical replication for blue/green | Patroni-managed; statement pooling disabled; HA failover drills quarterly |
| Redis | 7.2 | 7.2 | Patch quarterly; persistence `aof` for broker, none for cache | Managed Azure Cache for Redis Enterprise; last review Aug 2025; next review Feb 2026 |
| Python runtime | 3.12.x | 3.12.x | Security releases within 30 days | Pinned in `Dockerfile` & dependency locks; min supported 3.11 for tooling; deprecation notice 90 days prior |
| Node.js (build) | 20.x LTS | 20.x LTS | Upgrade within 45 days of LTS patch | Build-time only; no runtime exposure; Node 18 blocked since 2025-07 |
| Terraform | 1.8.x | 1.8.x | Upgrade quarterly with module pin review | State stored in Terraform Cloud; nightly drift detection; drift incidents logged in Appendix H |
| Nginx ingress controller | 1.11.x | 1.10.x | Patch monthly; major with Kubernetes cadence | TLS 1.3 preferred; OCSP stapling enabled; Mar 2025 upgrade closed; next upgrade window Jan 2026 |
| Base OS images | Debian 12 | Debian 12 | Rebuild monthly or on critical CVE | Images signed; SBOM generated per build; CIS benchmark level 1 enforced |

Upgrade windows recorded in the change calendar; App.M supports audit inquiries regarding environment parity and upcoming rollouts.

______________________________________________________________________

## Appendix N — Privacy controls traceability

*Purpose: Provide a single view from regulatory obligations to settings, gates, and evidence.*

| Obligation (Reg / Article) | Settings / gates | Enforcement point | Evidence artifacts |
|---|---|---|---|
| Data residency (PIPEDA s.17, GDPR Art.44) | `regions.allowlist.*`, `integrity.downstream_action` | Guardian residency checks (§3.8, §7.1.1) | AuthorizationPolicy manifests, ops `RESIDENCY_POLICY_BLOCK` logs, App.O waivers |
| DPIA / RoPA maintenance (GDPR Art.35/30) | `privacy.dpia.*`, `privacy.ropa.*` | Privacy activation workflow (§9.3) | DPIA/ROPA artifacts, audit seals, App.K mapping |
| HIPAA override mode (HIPAA section 164.312) | `privacy.hipaa.enabled`, `security.mfa.webauthn_required_roles`, `evidence_store.redacted_excerpts.enabled` | Dual approval (§9.11), Guardian/portal guards | HIPAA manifest entries, audit events, QA logs |
| Legal hold & retention (GDPR Art.5, CPPA) | `privacy.legal.matrix_version`, `compliance.erasure_mode` | Destruction job approval (§14.2), DSAR scheduler (§14.2.1) | `DESTRUCTION_CERT`, `ERASURE_JOURNAL`, secure views showing masked reasons |
| DSAR / erasure fulfillment (GDPR Art.17) | `compliance.subject_hkdf_salt`, `compliance.erasure_mode` | DSAR operations runbook (§14.2.1) | Ops logs, audit events `DSAR_ERASURE_EXECUTED`, Appendix H drills |
| Masking & field protection (SOC2 CC6.6) | `field_mask_rule`, `security.field_encryption.*` | Secure views (§4.5) and encryption routines (§4.5) | Masking helper tests, encryption key rotation records |
| Client portal delivery (PIPEDA Safeguards) | `portal.download.rate_limits.*`, `compose.policy.forbidden_patterns[]` | Guardian readiness + portal invalidation (§11.2.1) | Portal invalidation SSE events, QA reports, `../ops/runbooks.md (RB-ETAG)` output |

Matrix reviewed quarterly with Privacy & Security; updates required whenever referenced settings or obligations change.

______________________________________________________________________

## Appendix O — Active waivers ledger

*Purpose: Track approved temporary deviations (residency, security, privacy) with expiry and owners.*

| Waiver ID | Category | Scope | Approved by | Effective / Expiry | Conditions | Status |
|---|---|---|---|---|---|---|
| (none) | — | — | — | — | — | No active waivers |

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

| Acceptance ID | Risk description | Owner | Mitigation / Monitoring | Accepted until | Status |
|---|---|---|---|---|---|
| (none) | — | — | — | — | No open risk acceptances |

Risk acceptances capture deviations such as pending CVE remediation or temporary SLO relaxations. Entries require Security + Product approval, explicit expiry, and linkage to incident/problem tickets. Items auto-escalate to leadership if not reviewed 7 days before expiry.

______________________________________________________________________

## Appendix P — Third-party & OSS notices

*Purpose: Centralize licensing, attribution, and notice obligations for distributed software.*

| Component / Package | License | Notice location | Additional obligations |
|---|---|---|---|
| Django | BSD-3-Clause | `licenses/django/LICENSE` | Include copyright notice in customer-facing docs |
| Celery | BSD-3-Clause | `licenses/celery/LICENSE` | Provide acknowledgement in operator manual |
| Azure SDKs | MIT | `licenses/azure-sdk/LICENSE` | No attribution required; note data use terms in App.Q |
| LangGraph | Apache-2.0 | `licenses/langgraph/LICENSE` | Preserve NOTICE text in redistributed binaries |
| ffmpeg | LGPL-2.1 | `licenses/ffmpeg/NOTICE` | Dynamic linking only; provide source offer on request |
| openpyxl | MIT | `licenses/openpyxl/LICENSE` | None |
| Company-specific scripts | Proprietary | `licenses/custom/README.md` | Internal use only; no redistribution without approval |

Process: SBOM generation (§13.6) cross-checks license metadata nightly; discrepancies raise `LICENSE_GAP` alerts. Updated notices shipped in `NOTICE.md` alongside release artifacts.

______________________________________________________________________

## Appendix Q — Sub-processors & DPAs

*Purpose: List sanctioned data processors, residency posture, and contractual guarantees.*

| Provider | Service | Region(s) in scope | Data classes processed | DPA/Terms highlights |
|---|---|---|---|---|
| Microsoft Azure Speech | Transcription (batch/on-demand) | Org allowlisted Azure regions (e.g., eu-west-2) | Audio uploads, transcript text | DPA §3 forbids training on customer data; residency pinned to selected region; 30-day deletion |
| Microsoft Azure OpenAI | LLM inference | Org allowlisted Azure regions (mirror Speech) | Prompt excerpts (redacted), generated text | Enterprise agreement disables logging & training; retention ≤ 24h; residency anchored to allowlist |
| Entrust TSA / OCSP | Timestamping & revocation | Global (per org trust bundle) | Hashes, certificate metadata | No content retention; logs retained 90 days for audits; trust roots mapped to Platform Runtime §3.4 |
| Twilio SendGrid (optional) | Email delivery | Org-selected sub-account region (NA/EU/APAC) | Notification metadata, recipient email | Data residency restriction via regional sub-account; logs 30 days |
| Telnyx | SMS delivery | Org-selected region (NA/EU/APAC) | Phone numbers, message metadata | Opt-out enforcement, no content mining; residency documented in waiver ledger |
| Speechmatics regional fallback | Automated transcription fallback | ca-central-1 (org allowlisted) | Audio uploads, transcript text | DPA mirrors Azure terms; retention ≤ 24 h; audited equivalence harness ensures WER/diarization parity with primary |

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

| Domain / Section | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Agent pipelines (§6) | Platform AI Lead | Director of Engineering | QA Lead, Product | Support, Customer Success |
| Guardian & Signer (§7) | Security Engineering Lead | CISO | Platform Architecture, Legal | Support, Customer Success |
| LLM governance (§8) | AI Governance Lead | CTO | Security, Privacy Officer | Product, Customer Success |
| Settings platform (§9) | Platform Architecture Lead | Director of Engineering | Security, QA | Support |
| APIs & Integrations (§10) | API Engineering Manager | Director of Engineering | Product, Support | Customers (release notes) |
| Frontend & Portal (§11) | UX Engineering Manager | VP Product | Accessibility SME, Support | Customer Success |
| Observability & Ops (§12) | SRE Manager | VP Engineering | Security, Product | Support, Customers |
| Quality & Compliance (§13) | QA Manager | VP Engineering | Security, Privacy | Product, Customers |
| Operations lifecycle (§14) | Operations Lead | COO | Security, Legal | Customer Success |
| Roadmap & governance (§15) | Product Strategy Lead | VP Product | Architecture, Security | All teams |

RACI reviewed every release train; updates recorded in decision log (§15.3) and mirrored in internal handbook.

- Mesh-controlled pods allow egress only to cluster DNS and the Istio egress gateway; the gateway enforces external destinations via the AuthorizationPolicy allowlist above. Namespaces without the mesh label can define their own policies, but production workloads inherit this baseline.

______________________________________________________________________

## Appendix T — Traceability matrix

*Purpose: Tie requirements to validation, observability, and operational response so audits stay frictionless.*

| Requirement (section) | Tests / validation artifacts | Monitors / alerts | Runbook / response |
|---|---|---|---|
| Guardian judgments deterministic & parent-aware (§7.1) | `tests/guardian/test_concurrent_parent_swap.py::test_child_blocks_on_parent_swap`; Guardian synthetic `guardian_slo.yaml` job | `guardian_cleared_ratio`, `guardian_judgment_latency_seconds`, `guardian_parent_block_total` | Appendix B.1, Appendix B.2 |
| API versioning & Sunset policy enforced (§10.0, §10.5) | `make lint-openapi` (`npx spectral lint ops/openapi/**/*.yaml`), Spectral `sunset-header` rule, ADR-0002 change review checklist | `api_sunset_header_missing_total`, `api_deprecation_notice_age_seconds` | `../ops/runbooks.md` standard runbook template → API Sunset (`docs/runbooks/api/sunset.md`, draft) |
| FinOps guardrails prevent runaway spend (§8.7, §12.9) | `scripts/finops/check_mom_guard.py`; `tests/core/finops/test_guard.py::test_regression_formula` | `finops_mom_regression_flag{org}`, `llm_cost_estimate_total` | [Runbook RB-LLM-003](../ops/runbooks.md#rb-llm-003) |
| Logging pipeline retains structured records (§12.1) | `tests/logging/test_redaction.py::test_forbidden_headers_masked`; `diagram:diff` for log schema | `logging_ingest_lag_seconds`, `logging_drop_rate_pct`, `logging_spool_utilization_pct` | `../ops/runbooks.md (RB-LOG-007)` |
| Advisory locks stay healthy during approvals (§5.4) | `tests/platform/artifacts/test_approval_swap.py::test_concurrent_approvals_single_winner`; `tests/platform/db/test_rls_guard.py::test_rls_context_asserts_missing_gucs` | `udlock_watchdog_stale_total`, `udlock_lock_age_seconds_p95` | [Runbook RB-LOCK-006](../ops/runbooks.md#rb-lock-006) |
| Portal downloads honor ETag / If-Match (§10.6, `../ops/runbooks.md (RB-ETAG)`) | `tests/e2e/test_artifact_range_download.py::test_range_and_conditional_gets` | `portal_412_precondition_total`, `alert_portal_412_spike` | `../ops/runbooks.md (RB-ETAG)` |
| Abuse-prevention detectors enforce throttles (§B.4, §6.13, §10.9) | `tests/security/test_abuse_checks.py::test_api_abuse_flagged`, `tests/security/test_portal_download_guard.py::test_anomaly_blocks`, shadow soak fixtures (`tests/platform/shadow/test_shadow_thresholds.py`) | `api_suspect_request_total`, `portal_download.anomaly_score`, `messaging_abuse_detected_total`, `abuse_shadow_threshold_expiring_total` | [Runbook RB-RES-BLOCK](../ops/runbooks.md#rb-res-block) (residency), `../ops/runbooks.md (RB-ETAG)`, `docs/runbooks/security/abuse_triage.md` |
| Masking profiles map to FORCE RLS policies (§4.4.1) | `tests/platform/db/test_mask_profiles.py::test_mask_profile_matches_policy`, `tests/platform/db/test_secure_view_usage.py::test_no_base_table_queries` | `rls_context_missing_total`, `mask_profile_mismatch_total` | [Runbook RB-GOV-008](../ops/runbooks.md#rb-gov-008) (settings rollback), [Runbook RB-LOCK-006](../ops/runbooks.md#rb-lock-006) |
| LLM/vector residency guard prevents out-of-region fallback (§8.1.1) | `tests/core/llm/test_residency_guard.py::test_block_disallowed_region`, `tests/core/vector/test_vector_residency.py::test_allowed_regions_only`, synthetic `synthetics/llm_residency.yaml` | `llm_region_fallback_total`, `vector_region_fallback_total` | [Runbook RB-LLM-003](../ops/runbooks.md#rb-llm-003), [Runbook RB-RES-BLOCK](../ops/runbooks.md#rb-res-block) |
| CSP nonce & HIPAA cache enforcement (§11.5, §10.6) | `tests/ui/test_csp_nonced.py::test_nonce_roundtrip`, synthetic `synthetics/csp_nonce_failure.yaml`, `synthetics/portal_hipaa_cache.yaml`, `tests/e2e/test_portal_policy_context.py::test_disclaimer_l10n` | `csp_nonce_mismatch_total`, `portal_cache_header_violation_total` | `../ops/runbooks.md (RB-PORTAL-005)`, Appendix H security headers checklist |

______________________________________________________________________
