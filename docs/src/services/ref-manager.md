---
title: uDocket — Reference Manager Technical Design
subtitle: Reference Data Ingestion, Editorial Workflow, and Publishing Specification
author:
  - uDocket Platform Architecture Team
  - Reference Programs Leadership
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-23
owners:
  - Platform Architecture
  - Security Engineering
  - Reference Programs
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - QA Engineering Lead
  - SRE Manager
adr_index: docs/adr/README.md
related_adrs:
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
  - <header class="page-header">uDocket — Reference Manager Technical Design <br> Reference Data Ingestion, Editorial Workflow, and Publishing Specification</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

**Audience:** Reference Programs, Localization & Policy Engine, Settings, Guardian, Compose/Analyze, SRE, QA.

**Purpose:** Describe Reference Manager responsibilities, contracts, lifecycle workflows, and observability so downstream services consume consistent, licensed, and auditable reference data.

## Document controls

| Field           | Value                                                                                                                                         |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Version         | 0.1-draft                                                                                                                                     |
| Status          | Implementable (mirrors front matter `status`; KEP lifecycle applies: Provisional → Implementable → Implemented)                               |
| Last updated    | 2025-10-23 (source of truth is the front matter `last_updated`)                                                                               |
| Primary owners  | Platform Architecture; Security Engineering; Reference Programs                                                                               |
| Approvers       | Architecture Steering Committee; Security Review Board                                                                                        |
| Reviewers       | QA Engineering Lead; SRE Manager                                                                                                              |
| ADR index       | `docs/adr/README.md` (immutable ADRs referenced in front matter `related_adrs`)                                                               |
| Migration plan  | Replaces legacy Reference Engine coverage in the platform TDD; `/reference/*` shims remain read-only until all clients complete the migration |
| Docs validation | `python scripts/docs/lint_docs.py` (see `docs/README.md` for tooling)                                                                         |
| Link lint       | `python scripts/docs/link_check.py --strict` (CI `docs-link-check` stage blocks unresolved §/App./ADR refs)                                   |

Body sections follow the Purpose/Contract/State/Failure/Observability/References/Breadcrumbs scaffold enforced by `scripts/docs/lint_docs.py --check-template`. Section tags `(binding)` and `(normative)` align with the platform TDD.

______________________________________________________________________

## 0) Reading guide

- **Scope:** Service charter, source ingestion, editorial workflows, publishing, integrations, and observability for Reference Manager.
- **Structure:** Sections are limited to three levels of depth; cross-cutting diagrams live in the platform TDD appendices (App.A state flows, App.G ERD).
- **Cross-references:** Use `§<number>` for this document, `TDD §<number>` for the platform TDD, and `App.<letter>` for appendices or §8.3 entries.
- **Maintenance:** Run `python scripts/docs/lint_docs.py` before submitting edits. Schema snippets must match `spec/schemas/reference_*`; CI verifies locale coverage and bundle manifests.
- **Change protocol:** PRs changing Reference Manager ingestion, bundles, or review workflows must update this document and linked ADRs. Architecture/Security reviewers block merges when services diverge from these contracts.

______________________________________________________________________

## 1) Purpose

**Purpose:** Establish Reference Manager (RM) as the authoritative source for regulated reference data, templates, and localization assets that power downstream services. **|**
**Contract:** RM curates, validates, and publishes licensed bundles covering courts, jurisdictions, forms, questionnaires, deliverable templates, localization packs, and provider metadata. Downstream services (LPE, Settings, Guardian, Compose, Analyze, Portal) must consume signed RM bundles and record digests for provenance. **|**
**State:** Curated data resides in Postgres across raw, staging, curated, and published schemas; signed bundles live in object storage with manifests; adoption telemetry tracks service acknowledgements. **|**
**Failure modes & handling:** Validation guard failures or adoption lag freeze new publishes and trigger runbooks until bundles validate or roll back. **|**
**Observability:** Dashboards “Reference Manager – Availability”, “Harvest”, “Publish”, and “Adoption” monitor request volume, error rates, and adoption lag; events feed SIEM and audit sinks. **|**
**References:** TDD §6 Reference Data, ADR-0004, §8.3.2–§8.3.6 RB-RM-* runbooks. **|**
**Breadcrumbs:** Service entry `packages/udocket_core/reference_manager/service.py`, tests `tests/reference/test_charter.py`, telemetry `packages/udocket_core/reference_manager/telemetry.py`.

- RM governs acquisition, normalization, review, publishing, and downstream adoption tracking.
- RM publishes signed bundles and manifests; enforcement lives in Settings, Guardian, and downstream applications.
- Downstream workflows embed RM bundle digests in manifests, telemetry, and audit logs to prove provenance.

______________________________________________________________________

## 2) Responsibilities

### 2.1 Charter & scope (binding)

**Purpose:** Define RM’s mission and success criteria. **|**
**Contract:** RM is the single source of truth for regulated reference artifacts: courts/jurisdictions, filing rules, localization packs, deliverable templates, questionnaires, provider endpoints, and compliance matrices. **|**
**State:** Curated records live in `reference_*` tables with provenance hashes, license metadata, and effective timestamps; published bundles mirror these records in signed manifests. **|**
**Failure modes & handling:** Missing or stale records block publishes and raise `reference_manager_catalog_coverage_total{status="missing"}`; incidents route to Content Ops and Legal Ops. **|**
**Observability:** “Reference Manager – Catalog Coverage” dashboards track locale/domain completeness and freshness. **|**
**References:** §2.6 Bundles, §4 State management. **|**
**Breadcrumbs:** Models `packages/udocket_core/reference_manager/models.py`, tests `tests/reference/test_asset_registry.py`.

- Courts/jurisdictions include hierarchical metadata, filing fees, addresses, and codes.
- Forms/questionnaires capture localized prompts, scoring rubrics, conditional logic, and accessibility metadata.
- Templates/localization packs provide Markdown/DOCX/Jinja artifacts, locale fallback rules, and attribution strings.
- Provider metadata encodes residency endpoints, SAN expectations, and attestation cadence consumed by Settings and Guardian.

### 2.2 Source acquisition & connectors (binding)

**Purpose:** Describe how RM harvests authoritative sources. **|**
**Contract:** Connectors (SFTP, HTTP, SOAP/REST, GraphQL, manual upload) enforce rate limits, retries, TLS pinning, checksum validation, and licensing checks before data enters pipelines. **|**
**State:** Connector definitions live in `reference_connector` with credentials, schedule, and license terms; job metadata persists per harvest run. **|**
**Failure modes & handling:** Source errors trigger exponential backoff, alert `reference_manager_harvest_error_total`, and invoke §8.3.3 RB-RM-HARVEST when SLAs breach. **|**
**Observability:** “Reference Manager – Harvest” dashboard tracks success/error counts by source; stale-source monitors highlight overdue runs. **|**
**References:** §4.1 Pipelines, §8.3.3 RB-RM-HARVEST. **|**
**Breadcrumbs:** Connectors `packages/udocket_core/reference_manager/connectors.py`, tests `tests/reference/test_source_connectors.py`.

- Connectors sanitize HTML/JSON, enforce TLS 1.2+, and verify remote checksums and licenses.
- Manual uploads support emergency updates with dual approval and checksum validation.
- Licensing metadata logs upstream term changes and triggers Legal Ops review.

### 2.3 ETL & normalization (binding)

**Purpose:** Capture the ingestion pipeline from raw harvest to curated records. **|**
**Contract:** ETL stages parse, normalize, enrich, and resolve entities deterministically, producing machine and human diff artifacts for review. **|**
**State:** Raw data lands in JSONB staging tables; normalized records populate `reference_stage_*`; curated tables store approved, hashed records. **|**
**Failure modes & handling:** Schema drift or parsing failures raise alerts and enqueue manual review; persistent failures escalate via RB-RM-HARVEST. **|**
**Observability:** “Reference Manager – ETL” dashboard monitors `reference_manager_etl_duration_seconds`, error counts, and diff sizes. **|**
**References:** §4.2 Bundle registry, §8.3.4 RB-RM-PUBLISH. **|**
**Breadcrumbs:** ETL pipeline `packages/udocket_core/reference_manager/etl.py`, tests `tests/reference/test_etl_pipeline.py`.

- Entity resolution merges duplicates using canonical IDs and deterministic matching.
- Normalization enforces casing/diacritics and maps to internal taxonomies with provenance hashes.
- Diff artifacts feed editorial review queues with context and confidence scores.

### 2.4 Storage & schema layering (binding)

**Purpose:** Describe RM’s layered storage strategy. **|**
**Contract:** RM maintains raw, staging, curated, and published layers with strict constraints, provenance hashes, and license metadata; published bundles reflect curated data only. **|**
**State:** Raw/staging layers capture harvested content; curated layer (`reference_*`) enforces constraints; published bundles reside in object storage with SHA-256 digests. **|**
**Failure modes & handling:** Constraint violations block publishes and open incidents; schema migrations coordinate via `ops/reference/migrate.py`. **|**
**Observability:** “Reference Manager – Schema Health” dashboard tracks `reference_manager_schema_violation_total` and migration status. **|**
**References:** §4 State management, Appendix C seed bundles. **|**
**Breadcrumbs:** Schema definitions `packages/udocket_core/reference_manager/models.py`, tests `tests/reference/test_schema_layering.py`.

### 2.5 Editorial workflows & approvals (binding)

**Purpose:** Outline the human review process prior to publish. **|**
**Contract:** Harvested diffs enter review queues requiring dual approval (Content Ops + Legal Ops) for regulated changes; Localization and Product reviewers sign off on locale impacts; Security approves residency/licensing changes. **|**
**State:** Review queue records live in `reference_review_queue` and `reference_review_decision` with assignments, SLA timers, and diff metadata. **|**
**Failure modes & handling:** Queue latency beyond SLA pages editors and invokes RB-RM-PUBLISH; emergency changes follow hotfix policy with retrospective review. **|**
**Observability:** “Reference Manager – Review Queue” dashboard monitors `reference_manager_review_latency_seconds`, backlog counts, and diff aging. **|**
**References:** §2.6 Bundles, §8.3.4 RB-RM-PUBLISH. **|**
**Breadcrumbs:** Review workflow `packages/udocket_core/reference_manager/review.py`, tests `tests/reference/test_review_workflow.py`.

- Diff triage categorizes changes (regulated, customer commitment, internal improvement) with SLA and reviewer rules defined in `reference_review_policy.yaml`.
- Editorial UI provides diff context, dependency impact, and expedited workflows for court closures and emergency notices.

### 2.6 Bundles & publishing (binding)

**Purpose:** Explain bundle construction, signing, and promotion. **|**
**Contract:** Bundles follow semantic versioning, include manifests (hashes, licensing, compatibility notes), and publish only after validation succeeds; adoption SLAs: LPE/Settings ≤ 2 hours, Compose/Guardian ≤ 24 hours. **|**
**State:** Bundle manifests persist in `reference_bundle_registry` with signatures, compatibility ranges, and license ledger entries; adoption status tracked in `reference_bundle_adoption`. **|**
**Failure modes & handling:** Validation failures block signing and alert `reference_manager_publish_guard_failure`; adoption lag triggers RB-RM-ROLLBACK or RB-RM-PUBLISH. **|**
**Observability:** “Reference Manager – Review & Publishing” dashboard tracks publish totals, bundle diff sizes, and adoption lag histograms. **|**
**References:** §4.2 Bundle registry, §5.5 Adoption lag, §8.3.2 RB-RM-ROLLBACK. **|**
**Breadcrumbs:** Publisher `packages/udocket_core/reference_manager/publish.py`, tests `tests/reference/test_publish_pipeline.py`.

- Bundles (for example `courts@1.4.0`) ship deterministic JSON/Parquet assets with manifests containing SHA-256 digests, effective timestamps, license notes, and rollback metadata.
- Snapshot archives accompany deltas to support fast-forward and rollback workflows.

### 2.7 Templates, questionnaires & resources (binding)

**Purpose:** Govern questionnaires, forms, deliverable templates, and localization assets. **|**
**Contract:** RM enforces locale completeness, accessibility status, license tracking, and template provenance; invalidation events propagate until downstream caches acknowledge updates. **|**
**State:** Metadata lives in `questionnaire`, `form`, `reference_template`, and `reference_localization` tables with hashes, renewal cadence, and approvals. **|**
**Failure modes & handling:** Locale coverage or checksum drift blocks publish; resource monitors raise `reference_resource_unavailable` for stale endpoints. **|**
**Observability:** Dashboards “Reference Manager – Resource Coverage” and “Deliverable Catalog & Templates” monitor coverage gaps, invalidation retries, and template staleness. **|**
**References:** §4.3 Template repository, §5.3 Licensing incidents. **|**
**Breadcrumbs:** Resource handlers `packages/udocket_core/reference_manager/resources.py` and `templates.py`, tests `tests/reference/test_questionnaires.py`, `tests/reference/test_templates.py`.

### 2.8 Security, licensing & compliance (binding)

**Purpose:** Capture RM’s security posture, licensing obligations, and sensitive data controls. **|**
**Contract:** Harvested content is sanitized; license metadata enforced; sensitive changes require dual approval; immutable audit trails record provenance. **|**
**State:** License ledger persists in `reference_license` tables; sensitive-change audits append JSONL entries; sanitation configuration stored with connectors. **|**
**Failure modes & handling:** Missing license metadata or sanitation failures block publishes and trigger RB-RM-LICENSE; repeated violations escalate to Legal Ops and Security. **|**
**Observability:** “Reference Manager – Compliance” dashboard tracks `reference_manager_license_violation_total`, sanitation errors, and sensitive-change audits. **|**
**References:** §5.3 Licensing incidents, §8.3.5 RB-RM-LICENSE. **|**
**Breadcrumbs:** Security module `packages/udocket_core/reference_manager/security.py`, tests `tests/reference/test_license_ledger.py`.

### 2.9 Testing & safeguards (binding)

**Purpose:** Enumerate automated protections guarding catalog integrity. **|**
**Contract:** Golden snapshots, contract tests, semantic publish guards, and adoption drills run per publish before bundles sign. **|**
**State:** Golden fixtures live under `tests/reference/golden`; guard artifacts stored alongside bundle drafts with diff snapshots. **|**
**Failure modes & handling:** Guard failures halt the pipeline and invoke RB-RM-PUBLISH; adoption drills failing reopen incidents until resolved. **|**
**Observability:** CI job “reference-manager-validate” and adoption drills surface readiness metrics. **|**
**References:** §5.2 Publish guard failure, §8.3.4 RB-RM-PUBLISH / §8.3.2 RB-RM-ROLLBACK. **|**
**Breadcrumbs:** Validation suite `packages/udocket_core/reference_manager/tests.py`, tests `tests/reference/test_bundle_validation.py`.

### 2.10 Risks & mitigations (normative)

**Purpose:** Track major program risks and mitigation strategies. **|**
**Contract:** Risk register maps selector churn, license drift, entity merges, and stale runtime to explicit controls and owners. **|**
**State:** Risk entries live in `ops/reference/risk_register.md` with mitigation evidence, review cadence, and automation hooks. **|**
**Failure modes & handling:** Missing mitigation evidence escalates to Program Leads; unresolved stale runtime triggers adoption-lag incidents. **|**
**Observability:** Risk dashboard “Reference Manager – Risk Register” highlights status, last review date, and outstanding tasks. **|**
**References:** §5 Failure modes, §8.3 Runbooks & drills. **|**
**Breadcrumbs:** Risk register `ops/reference/risk_register.md`, tests `tests/reference/test_risk_controls.py`.

______________________________________________________________________

## 3) API contract

### 3.1 REST & automation surfaces (binding)

**Purpose:** Document APIs and automation surfaces exposing RM data. **|**
**Contract:** REST, GraphQL, CLI, and SSE interfaces enforce scopes, MFA for high-risk actions, and signed bundle delivery. **|**
**State:** API gateway routes under `/api/v1/reference_manager`; CLI commands leverage the same endpoints; SSE feeds stream review and publish events with bundle metadata. **|**
**Failure modes & handling:** Auth failures emit audit events and throttle abusive clients; sustained failures alert on-call via `reference_manager_api_error_total`. **|**
**Observability:** “Reference Manager – API Health” monitors `reference_manager_api_latency_seconds`, error rates, and SSE delivery counts. **|**
**References:** §3.2 Events, §4.2 Bundle registry. **|**
**Breadcrumbs:** API handlers `packages/udocket_core/reference_manager/api.py`, tests `tests/reference/test_api_surface.py`.

- REST endpoints: `/reference_manager/bundles`, `/catalog/<domain>`, `/templates`, `/questionnaires`, `/forms`.
- GraphQL queries support filtering, diff history, and search.
- CLI workflows (`reference bundle validate/publish/diff`) integrate with automation pipelines.

### 3.2 Events & downstream adoption (binding)

**Purpose:** Describe event payloads and adoption tracking. **|**
**Contract:** Publishes emit `reference_manager.bundle.ready` and `reference_manager.bundle.published`; downstream services acknowledge by recording bundle version/digest within SLA. **|**
**State:** `reference_bundle_adoption` stores `{service, bundle_id, status, acknowledged_at, digest}`; replay queue re-emits events until acknowledgement. **|**
**Failure modes & handling:** Missing acknowledgements trigger adoption lag incidents; RM replays events and coordinates with service owners. **|**
**Observability:** “Reference Manager – Adoption” dashboard tracks `reference_bundle_adoption_total` and lag histograms; alerts fire when SLA breached. **|**
**References:** §5.5 Adoption lag, §8.3.2 RB-RM-ROLLBACK. **|**
**Breadcrumbs:** Event definitions `packages/udocket_core/reference_manager/events.py`, tests `tests/reference/test_events.py`.

- Adoption statuses: `pending`, `in_progress`, `acknowledged`, `stale`.
- Adoption reports join LPE compile results, Settings activation diffs, and Guardian acknowledgements.

### 3.3 Alignment with Settings, Guardian, and Portal (binding)

**Purpose:** Ensure downstream services stay synchronized with RM releases. **|**
**Contract:** RM publishes alignment manifests summarizing residency changes, waivers, and impacted deliverables; Settings and Guardian verify digests before enabling downstream actions; Portal invalidates caches when bundles refresh. **|**
**State:** Alignment manifests store beside bundles; Settings activation replays cross-check digests; Guardian records waivers referencing RM IDs. **|**
**Failure modes & handling:** Alignment violations raise incidents and freeze dependent operations until resolved. **|**
**Observability:** “Reference Manager – Downstream Alignment” dashboard monitors `reference_manager_alignment_violation_total` and Settings activation replays. **|**
**References:** §2.4 Storage, §9 Dependencies. **|**
**Breadcrumbs:** Integration helpers `packages/udocket_core/reference_manager/integration.py`, tests `tests/reference/test_settings_guardian_alignment.py`.

______________________________________________________________________

## 4) State management

### 4.1 Pipelines & scheduling (normative)

**Purpose:** Outline job orchestration from harvest through publish. **|**
**Contract:** Dagster/Airflow pipelines orchestrate harvest → ETL → review → publish with cron schedules per source and manual triggers for urgent updates. **|**
**State:** Pipeline definitions live in `ops/reference/pipelines/*.yaml`; runtime metadata stored in scheduler tables and job history logs. **|**
**Failure modes & handling:** Scheduler delays raise alerts and allow manual failover; extended delays invoke RB-RM-HARVEST. **|**
**Observability:** “Reference Manager – Scheduler” dashboard tracks `reference_manager_scheduler_delay_seconds`, job success/failure counts, and run history. **|**
**References:** §2.2 ETL, §6.1 Metrics. **|**
**Breadcrumbs:** Scheduler `packages/udocket_core/reference_manager/scheduler.py`, tests `tests/reference/test_scheduler.py`.

### 4.2 Bundle registry & manifests (binding)

**Purpose:** Describe how RM stores, signs, and version-controls bundles. **|**
**Contract:** Bundles store in object storage with signed manifests, semantic versions, compatibility windows, and rollback metadata; registry ensures determinism and auditability. **|**
**State:** `reference_bundle_registry` tracks bundle metadata, signatures, license ledger IDs, and adoption counts; rollback checkpoints persist in `reference_bundle_checkpoint`. **|**
**Failure modes & handling:** Registry inconsistencies block publishes; rollback automation restores previous bundle and records `BUNDLE_ROLLBACK_REPORT`. **|**
**Observability:** Publish dashboards show bundle history, diff sizes, and rollback events. **|**
**References:** §2.6 Bundles, §8.3.2 RB-RM-ROLLBACK. **|**
**Breadcrumbs:** Registry implementation `packages/udocket_core/reference_manager/publish.py`, tests `tests/reference/test_publish_pipeline.py`.

### 4.3 Template & localization repository (binding)

**Purpose:** Manage deliverable templates, localization packs, and invalidation flow. **|**
**Contract:** Templates reside under `templates/<deliverable_id>/<locale>/<version>` with metadata (`engine`, `locale`, `checksum`, `approved_by`, `effective_at`); invalidation events propagate until downstream acknowledgment. **|**
**State:** Template manifests persist in `reference_template_manifest`; invalidation retries recorded in `reference_template_invalidation`. **|**
**Failure modes & handling:** Checksum drift or missing approvals block publishes; cache reconciliation failures alert RB-RM-PUBLISH. **|**
**Observability:** “Deliverable Catalog & Templates” dashboard tracks template staleness and invalidation retries. **|**
**References:** §2.7 Templates, §8.3.4 RB-RM-PUBLISH. **|**
**Breadcrumbs:** Template management `packages/udocket_core/reference_manager/templates.py`, tests `tests/reference/test_templates.py`.

### 4.4 Residency & infrastructure catalogue (binding)

**Purpose:** Maintain provider residency metadata and infrastructure footprint. **|**
**Contract:** RM curates provider endpoints, attested regions, TLS SAN expectations, and residency notes consumed by Settings and Guardian. **|**
**State:** Metadata stored in `reference_residency_profile` with attestation artifacts and waiver metadata. **|**
**Failure modes & handling:** Attestation drift raises `reference_manager_provider_endpoint_violation_total` and invokes RB-RM-RESIDENCY; publishes freeze until catalog updates propagate. **|**
**Observability:** “Residency & Endpoint Posture” dashboard tracks attestation age, violations, and Settings activation replays. **|**
**References:** §2.8 Security, §5.4 Residency incidents. **|**
**Breadcrumbs:** Residency catalogue `packages/udocket_core/reference_manager/residency.py`, tests `tests/reference/test_residency_catalogue.py`.

### 4.5 Rollout sequencing (binding)

**Purpose:** Coordinate rollout waves for deliverables and locale packs. **|**
**Contract:** Rollout plans schedule waves per deliverable/locale with blast-radius controls and adoption checkpoints before promoting to all tenants. **|**
**State:** `reference_rollout_wave` stores schedule, deliverables, and completion status; monitoring tracks per-org adoption. **|**
**Failure modes & handling:** Wave delays or failed smoke tests trigger rollback; RM coordinates with Settings/Compose teams to pause adoption. **|**
**Observability:** “Reference Manager – Rollout” dashboard monitors wave progress, adoption percentages, and open issues. **|**
**References:** §2.6 Bundles, §8.3.2 RB-RM-ROLLBACK. **|**
**Breadcrumbs:** Rollout planner `packages/udocket_core/reference_manager/rollout.py`, tests `tests/reference/test_rollout.py`.

______________________________________________________________________

## 5) Failure modes (binding)

**Purpose:** Summarize the critical failure scenarios RM prepares for and the required responses. **|**
**Contract:** RM freezes publishes, triggers incidents, and follows §8.3 Runbooks & drills whenever harvest, validation, licensing, residency, or adoption controls break. **|**
**State:** Incidents tracked in `ops/reference/incidents/` with linkage to bundle IDs, runbook execution logs, and remediation tickets. **|**
**Failure modes & handling:** Sections below detail the primary scenarios; responders follow the matching RB-RM runbooks. **|**
**Observability:** Alerts from harvest, validation, adoption, compliance, and residency dashboards route to on-call with severity mappings. **|**
**References:** §8.3.2–§8.3.6 RB-RM-* entries, §6 Observability, §8 Operational notes. **|**
**Breadcrumbs:** Incident automation `ops/reference/*.py`, runbooks `ops/reference/runbooks/`.

### 5.1 Harvest or source outage (binding)

**Purpose:** Handle upstream source failures or harvesting errors. **|**
**Contract:** Connector failures pause publishes for affected catalogs, retry with exponential backoff, and escalate via RB-RM-HARVEST when SLA exceeds thresholds. **|**
**State:** Harvest jobs log failures with source metadata, retry counts, and last successful snapshot. **|**
**Failure modes & handling:** Long outages trigger manual outreach to the source, enable manual upload workflows, and record waiver decisions. **|**
**Observability:** Alerts from `reference_manager_harvest_error_total` and stale-source monitors drive on-call response. **|**
**References:** §2.2 Source acquisition, §8.3.3 RB-RM-HARVEST. **|**
**Breadcrumbs:** Connector logs, incident tickets, runbook RB-RM-HARVEST.

### 5.2 Validation or publish guard failure (binding)

**Purpose:** Address schema, diff, or semantic guard failures that halt publishes. **|**
**Contract:** Guard failures remain blocking until validation diffs resolve, schema updates approve, and integration tests rerun per RB-RM-PUBLISH. **|**
**State:** Validation artifacts persist with bundle drafts; adoption replays pause until guard clears. **|**
**Failure modes & handling:** Ignoring guard signals risks inconsistent bundles; rollback to prior version if remediation exceeds 12 hours. **|**
**Observability:** Alert `reference_manager_publish_guard_failure` and CI status highlight failures. **|**
**References:** §2.9 Testing, §8.3.4 RB-RM-PUBLISH. **|**
**Breadcrumbs:** Guard logs, validation artifacts, runbook RB-RM-PUBLISH.

### 5.3 Licensing or attribution violation (binding)

**Purpose:** Resolve licensing or attribution issues before they reach customers. **|**
**Contract:** Violations stay open until offending content removed or relicensed, attribution updated, and Legal Ops approvals documented. **|**
**State:** License ledger entries capture violations, remediation steps, and waiver approvals. **|**
**Failure modes & handling:** Publishing without resolution risks contractual breaches; invoke RB-RM-LICENSE and freeze affected bundles. **|**
**Observability:** `reference_manager_license_violation_total` and compliance dashboards drive escalation. **|**
**References:** §2.8 Security, §8.3.5 RB-RM-LICENSE. **|**
**Breadcrumbs:** License ledger, compliance dashboards, runbook RB-RM-LICENSE.

### 5.4 Residency or infrastructure drift (binding)

**Purpose:** Manage residency endpoint misalignment or attestation drift. **|**
**Contract:** Findings remain open until providers update catalogues, Settings activations rerun, and residency scanners confirm remediation. **|**
**State:** Findings stored in `reference_provider_endpoint_finding` with attestation evidence and waiver metadata. **|**
**Failure modes & handling:** Waivers require dual approval and expiry; unresolved drift escalates to Security Engineering. **|**
**Observability:** Alert `reference_manager_provider_endpoint_violation_total`, residency dashboards, and Settings activation diffs confirm status. **|**
**References:** §4.4 Residency catalogue, §8.3.6 RB-RM-RESIDENCY. **|**
**Breadcrumbs:** Residency finding records, Settings activation logs, runbook RB-RM-RESIDENCY.

### 5.5 Downstream adoption lag (binding)

**Purpose:** Ensure downstream services consume bundles on schedule. **|**
**Contract:** Adoption lag beyond SLA freezes new publishes and triggers RB-RM-ROLLBACK or RB-RM-PUBLISH depending on severity. **|**
**State:** `reference_bundle_adoption` records lag metrics; incident tickets note impacted services. **|**
**Failure modes & handling:** Services failing to acknowledge bundles must provide remediation plans; RM may temporarily revert to previous bundles. **|**
**Observability:** Adoption lag alerts, LPE compile monitors, and Settings activation diffs highlight issues. **|**
**References:** §3.2 Events, §8.3.2 RB-RM-ROLLBACK. **|**
**Breadcrumbs:** Adoption tables, dashboards, runbook RB-RM-ROLLBACK.

______________________________________________________________________

## 6) Observability & SLOs (binding)

**Purpose:** Define the telemetry, dashboards, and synthetic coverage validating RM performance and compliance. **|**
**Contract:** Metrics, logs, and synthetic probes listed below must exist and remain accurate; removing signals requires Observability + Security approval. **|**
**State:** Metrics emit via OpenTelemetry; logs stream to immutable sinks; synthetic jobs exercise publish/adoption flows; audit trails persist in JSONL files. **|**
**Failure modes & handling:** Missing metrics or stale thresholds block release checklists and trigger on-call follow-ups. **|**
**Observability:** Dashboards for Availability, Harvest, Review, Publish, Adoption, Compliance, and Residency monitor SLOs; Alertmanager routes incidents to RM on-call. **|**
**References:** §5 Failure modes, Appendix B metrics, §8.3 Runbooks & drills. **|**
**Breadcrumbs:** Telemetry module `packages/udocket_core/reference_manager/telemetry.py`, dashboards `infra/grafana/reference_manager_*.json`.

### 6.1 Metrics

**Purpose:** Summarize key quantitative signals. **|**
**Contract:** Track metrics including `reference_manager_request_total`, `reference_manager_error_total`, `reference_manager_harvest_total`, `reference_manager_etl_duration_seconds`, `reference_manager_review_latency_seconds`, `reference_manager_publish_total`, `reference_bundle_adoption_total`, `reference_manager_license_violation_total`, and `reference_manager_provider_endpoint_violation_total`. **|**
**State:** Counters/histograms emit from service code, pipelines, and validation jobs. **|**
**Failure modes & handling:** Missing metrics or inaccurate thresholds trigger observability retrofits before releases proceed. **|**
**Observability:** Dashboards visualize trends and SLO burn; runbook RB-RM-PUBLISH references specific metrics. **|**
**References:** Appendix B metrics tables. **|**
**Breadcrumbs:** Metric exporters `packages/udocket_core/reference_manager/telemetry.py`, tests `tests/reference/test_metrics.py`.

### 6.2 Logs & audits

**Purpose:** Describe the audit footprint supporting regulatory review. **|**
**Contract:** Activations, validations, waivers, sensitive changes, and rollbacks must emit structured audit events stored immutably. **|**
**State:** Audit streams write to `ops/reference/ops_reference.jsonl`, warehouse tables, and incident evidence folders. **|**
**Failure modes & handling:** Missing audit entries block publishes; fallback sinks engage while triggering incidents. **|**
**Observability:** Audit completeness monitors verify ingestion; alerts fire when events lag beyond five minutes. **|**
**References:** §2.8 Security, §8.3.5 RB-RM-LICENSE. **|**
**Breadcrumbs:** Audit writer `packages/udocket_core/reference_manager/audit.py`, tests `tests/reference/test_audit_log.py`.

### 6.3 Synthetic monitoring & adoption drills

**Purpose:** Continuously exercise harvest, validation, publish, and adoption flows. **|**
**Contract:** Synthetic jobs verify connectors, guard rails, and adoption acknowledgements per deploy; failures block releases. **|**
**State:** Synthetic definitions live in `ops/reference/synthetics/*.yaml`; results archive alongside CI artifacts. **|**
**Failure modes & handling:** Failures invoke RB-RM-PUBLISH or RB-RM-ROLLBACK; publishes pause until synthetics pass. **|**
**Observability:** CI jobs and Grafana dashboards report synthetic status and adoption drill outcomes. **|**
**References:** §2.9 Testing, §8.3 Runbooks & drills. **|**
**Breadcrumbs:** Synthetic scripts `ops/reference/synthetics/`, tests `tests/reference/test_publish_guard.py`.

### 6.4 Editorial telemetry (normative)

**Purpose:** Monitor editorial productivity and queue health. **|**
**Contract:** Editorial tooling emits queue age, assignment counts, and throughput metrics; Content Ops reviews dashboards weekly. **|**
**State:** Telemetry captures UI events, reviewer assignments, and SLA timers. **|**
**Failure modes & handling:** Degraded throughput triggers operational review and potential staffing adjustments. **|**
**Observability:** “Reference Manager – Editorial” dashboards track `reference_editorial_queue_age_seconds` and assignment counts. **|**
**References:** §2.5 Editorial workflows, §8.1 Editorial tooling. **|**
**Breadcrumbs:** Editorial UI `apps/platform/reference_manager/ui`, tests `tests/reference/test_editorial_ui.py`.

______________________________________________________________________

## 7) Security & compliance (binding)

**Purpose:** Document RM’s controls for data sanitization, access management, licensing, and residency compliance. **|**
**Contract:** RM enforces least privilege roles, sanitizes harvested content, records license obligations, rotates credentials, and maintains immutable audit trails. **|**
**State:** Access policies define roles and RLS rules; sanitation policies stored alongside connectors; license ledger tracks obligations; audit sinks capture sensitive changes. **|**
**Failure modes & handling:** Security or licensing violations trigger RB-RM-LICENSE or RB-RM-RESIDENCY; remediations recorded with legal approvals. **|**
**Observability:** Compliance dashboards track license violations, sensitive change audits, and residency drift; SIEM correlates audit events. **|**
**References:** §2.8 Security, §5.3 Licensing incidents, §8.3.5 RB-RM-LICENSE / §8.3.6 RB-RM-RESIDENCY. **|**
**Breadcrumbs:** Security module `packages/udocket_core/reference_manager/security.py`, IAM config `infra/iam/reference_manager/`, tests `tests/reference/test_license_ledger.py`.

- Sanitization strips risky markup and enforces TLS-only downloads.
- Vault rotates connector credentials; accesses logged and audited.
- Attribution metadata ensures UI/API clients meet legal disclosure requirements.

______________________________________________________________________

## 8) Operational notes (normative)

**Purpose:** Capture day-to-day operational practices, staffing expectations, and tooling that keep Reference Manager reliable. **|**
**Contract:** Teams follow documented change control, runbook execution, and editorial workflows; deviations demand incident documentation and retro actions. **|**
**State:** Operational metadata lives in `ops/reference/runbooks/`, deployment scripts, and App.O decision logs. **|**
**Failure modes & handling:** Skipping change control or letting runbooks drift increases audit risk; leadership reviews incidents for corrective actions. **|**
**Observability:** Deployment dashboards, runbook completion records, and CI jobs surface operational hygiene. **|**
**References:** §4 State management, §5 Failure modes, §8.3 Runbooks & drills, Appendix B metrics. **|**
**Breadcrumbs:** Deployment scripts `ops/reference/deploy.py`, CI workflows `.github/workflows/reference-manager.yml`, runbooks `ops/reference/runbooks/`.

### 8.1 Operational posture (binding)

**Purpose:** Define staffing, editorial coverage, and escalation paths across time zones. **|**
**Contract:** RM maintains a 24/5 on-call rotation with escalation to Program Leads; incidents execute RB-RM-* runbooks with evidence stored in App.O. **|**
**State:** Roster recorded in `ops/reference/oncall.yaml`; editorial assignments tracked in UI audit tables. **|**
**Failure modes & handling:** Missing rota coverage or unattended editorial queues trigger management review and follow-up actions. **|**
**Observability:** Dashboards “Reference Manager – Incidents” and “Editorial Queue Health” plus PagerDuty metrics spotlight posture drift. **|**
**References:** §6 Observability, §8.3 Runbooks & drills, §8.5 Operational workflows. **|**
**Breadcrumbs:** On-call roster `ops/reference/oncall.yaml`, editorial UI `apps/platform/reference_manager/ui`, incident template `ops/reference/incident_template.md`.

- Editorial shifts overlap by at least one hour to prevent queue gaps; staffing reviews confirm coverage quarterly.
- Duty officers escalate to Architecture, Legal Ops, or Program Leads within 15 minutes of Severity 1 incidents.
- Shared change calendar captures freezes, harvest maintenance windows, and major provider events.

### 8.2 Incident triggers (binding)

**Purpose:** Map RM alerts to their playbooks so responders start with the correct context. **|**
**Contract:** Alert definitions in `infra/monitoring/reference_manager-prometheus-rules.yaml` embed RB-RM identifiers; responders gather evidence before clearing alerts. **|**
**State:** Alert payloads include runbook IDs, connector identifiers, and change-ticket references; incidents log under `ops/reference/incidents/<date>.jsonl`. **|**
**Failure modes & handling:** Misaligned alert→runbook mapping or suppressed routes require Ops sign-off and a backlog item to restore coverage. **|**
**Observability:** Grafana dashboards, Alertmanager routes, and post-incident reviews monitor trigger fidelity. **|**
**References:** §5 Failure modes, §8.3 Runbooks & drills, Appendix B metrics. **|**
**Breadcrumbs:** Alert rules `infra/monitoring/reference_manager-prometheus-rules.yaml`, PagerDuty “Reference Manager”, incident logs `ops/reference/incidents/`.

- `reference_bundle_adoption_total{status="stale"}` and `reference_manager_adoption_lag_seconds` invoke RB-RM-ROLLBACK.
- `reference_manager_harvest_error_total` and connector synthetic failures trigger RB-RM-HARVEST.
- `reference_manager_publish_guard_failure` routes to RB-RM-PUBLISH for schema/validation issues.
- `reference_manager_license_violation_total` escalates via RB-RM-LICENSE with Legal Ops coordination.
- `reference_manager_provider_endpoint_violation_total` invokes RB-RM-RESIDENCY to align Settings and provider catalogues.

### 8.3 Runbooks & drills (binding)

**Purpose:** Maintain authoritative RM recovery guides and drills executed during incidents. **|**
**Contract:** Alerts in §8.2 map to RB-RM identifiers documented here; responders update these runbooks after every incident or quarterly tabletop. **|**
**State:** Procedures live in `ops/reference/runbooks/`, with evidence logged under `ops/reference/incidents/<date>/`. **|**
**Failure modes & handling:** Missing or stale steps block deploy sign-off until the runbook is refreshed. **|**
**Observability:** Post-incident retros, docs lint, and runbook catalog builds verify coverage. **|**
**References:** §5 Failure modes, §8.1 Operational posture, Appendix B metrics. **|**
**Breadcrumbs:** Runbooks `ops/reference/runbooks/*.md`, automation `ops/reference/*.py`, tests `tests/reference/test_runbook_integrity.py`.

#### 8.3.1 Runbook index (informative)

**Purpose:** Provide a quick map from RM alerts to runbook identifiers. **|**
**Contract:** Every RM alert references one of these IDs; new alerts require index updates before merge. **|**
**State:** Index maintained in `ops/reference/runbooks/index.md` and mirrored here. **|**
**Failure modes & handling:** Docs lint fails when the index misses an alert. **|**
**Observability:** Weekly lint ensures index matches Alertmanager routes. **|**
**References:** §8.2 Incident triggers, §8.3.2–§8.3.6. **|**
**Breadcrumbs:** Runbook index `ops/reference/runbooks/index.md`, tests `tests/reference/test_runbook_index.py`.

- RB-RM-ROLLBACK — Reference bundle rollback & adoption freeze
- RB-RM-HARVEST — Source harvest incident triage
- RB-RM-PUBLISH — Publish guard failure response
- RB-RM-LICENSE — License violation remediation
- RB-RM-RESIDENCY — Residency endpoint alignment

#### 8.3.2 RB-RM-ROLLBACK — Reference bundle rollback & adoption freeze (binding)

**Purpose:** Restore catalog stability when published bundles must be reverted. **|**
**Contract:** Rollbacks execute within 15 minutes of decision, capture evidence, and freeze dependent publishes until adoption latency returns to baseline. **|**
**State:** Automation uses `ops/reference/rollback_bundle.py`; evidence stored under `ops/reference/incidents/<date>/rollback`. **|**
**Failure modes & handling:** Missing rollback evidence or lingering adoption lag triggers escalation to Architecture. **|**
**Observability:** Alert `reference_bundle_adoption_total{status="stale"}` clears when all services acknowledge the rollback. **|**
**References:** §4.2 Bundle registry, §5.5 Adoption lag, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/reference/runbooks/rollback.md`, tests `tests/reference/test_rollback.py`.

Execution checklist:

1. Pause new publishes and announce freeze in `#ref-manager-oncall`.
2. Run `reference rollback --bundle <previous_id>` capturing activation ID and diff artifacts.
3. Trigger adoption verification for LPE, Settings, Guardian, Compose/Analyze, and Portal.
4. Update change ticket and App.O decision log with rollback details, evidence links, and remediation tasks.
5. Resume publishes only after adoption lag returns below SLA and follow-up actions assigned.

#### 8.3.3 RB-RM-HARVEST — Source harvest incident triage (binding)

**Purpose:** Mitigate source outages or connector failures before catalog staleness accumulates. **|**
**Contract:** Incidents remain open until harvest resumes, manual uploads address backlog, and validation confirms no data loss. **|**
**State:** Incident records track source metadata, outage start, workaround steps, and licensing considerations. **|**
**Failure modes & handling:** Ignoring prolonged harvest outages risks stale catalog data; escalate to Program Leads and Legal Ops when SLAs breach. **|**
**Observability:** Alert `reference_manager_harvest_error_total` and stale-source monitors signal recovery. **|**
**References:** §2.2 Source acquisition, §5.1 Harvest outage, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/reference/runbooks/harvest_incident.md`, connectors `packages/udocket_core/reference_manager/connectors.py`.

Response checklist:

1. Review failing connector logs, capture last successful snapshot, and assess licensing implications.
2. Engage source owner (court/government contact) and record ETA; initiate manual upload if available.
3. Queue interim communications to stakeholders when outage exceeds SLA.
4. Resume scheduled harvest, validate ETL outputs, and confirm review queue impact.
5. Close incident with root cause, remediation summary, and preventive actions.

#### 8.3.4 RB-RM-PUBLISH — Publish guard failure response (binding)

**Purpose:** Triage schema or validation failures that block publish pipelines. **|**
**Contract:** Guard failures remain blocking until diffs resolve, schema updates approve, and integration tests rerun. **|**
**State:** Validation artifacts persist alongside bundle drafts in `reference_bundle_registry`; tickets track remediation. **|**
**Failure modes & handling:** Ignoring guard signals risks inconsistent bundles; escalate to Architecture if fixes exceed 12 hours. **|**
**Observability:** Alert `reference_manager_publish_guard_failure` clears when validation suite passes. **|**
**References:** §5.2 Publish guard failure, §2.9 Testing, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/reference/runbooks/publish_guard.md`, tests `tests/reference/test_publish_guard.py`.

Execution checklist:

1. Export failing validation artifacts (`reference validate --bundle <id> --export artifacts/guard/<id>`).
2. Categorize failure (schema, missing assets, licensing metadata, diff threshold) and assign owners.
3. Apply fixes in staging, rerun validation and unit/integration suites.
4. Secure approvals, document evidence, and resume publish pipeline.
5. Attach diff snapshots and validation logs to incident ticket and update risk register if needed.

#### 8.3.5 RB-RM-LICENSE — License violation remediation (binding)

**Purpose:** Resolve licensing or attribution violations before they propagate. **|**
**Contract:** Violations remain open until offending content removed or relicensed, attribution updates verified downstream, and Legal Ops approvals documented. **|**
**State:** License ledger entries store violation metadata, remediation steps, and waiver approvals. **|**
**Failure modes & handling:** Publishing without remediation risks contractual breaches; escalate to Legal Ops immediately. **|**
**Observability:** Alert `reference_manager_license_violation_total` clears when ledger marks violation mitigated and attribution scanners pass. **|**
**References:** §2.8 Security & licensing, §5.3 Licensing incidents, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/reference/runbooks/license_violation.md`, tests `tests/reference/test_license_ledger.py`.

Remediation checklist:

1. Review violation payload, freeze related publishes, and notify Legal Ops.
2. Remove or quarantine offending content from staging/curated schemas; note impacted bundle versions.
3. Coordinate relicensing or replacements; capture approvals in waiver ledger.
4. Regenerate bundles, validate Guardian/UI attribution, and resume adoption.
5. Close ledger entry with evidence links and communicate resolution to stakeholders.

#### 8.3.6 RB-RM-RESIDENCY — Residency endpoint alignment (binding)

**Purpose:** Restore residency compliance when provider endpoint catalogues drift. **|**
**Contract:** Findings stay open until catalogues update, Settings activations replay, and residency scanners confirm remediation. **|**
**State:** Findings tracked in `reference_provider_endpoint_finding` with attestation evidence and waiver metadata. **|**
**Failure modes & handling:** Allowing stale endpoints risks policy violations; escalate to Security Engineering if remediation exceeds SLA. **|**
**Observability:** Alert `reference_manager_provider_endpoint_violation_total` resolves after two clean scans and Settings activations match updated catalogues. **|**
**References:** §4.4 Residency catalogue, §5.4 Residency incidents, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/reference/runbooks/residency_alignment.md`, tests `tests/reference/test_provider_endpoints.py`.

Remediation checklist:

1. Inspect finding details, gather attestation or SAN mismatch evidence, and engage provider contacts.
2. Update RM catalogue entries (`provider_endpoints[]`) with new CIDRs, SAN expectations, and residency notes.
3. Publish refreshed bundle, replay Settings activation, and verify Guardian acknowledges new digest.
4. Archive evidence in incident folder and update waiver ledger for temporary exceptions.
5. Confirm residency monitors pass twice consecutively before closing the incident.

### 8.4 Migrations & backfills (binding)

**Purpose:** Capture schema migrations, backfills, and catalog replays needed to keep RM aligned with downstream systems. **|**
**Contract:** Migration scripts run with dry-run evidence, tagged change tickets, and rollback checkpoints; partial completion requires RB-RM-ROLLBACK coordination. **|**
**State:** Migration manifests stored in `ops/reference/migrations/`; adoption tables track bundle versions per consumer. **|**
**Failure modes & handling:** Partial migrations risk drift or duplicate publishes; responders must freeze adoption and rollback bundles until resolved. **|**
**Observability:** Dashboards “Reference Manager – Adoption” and CI migration smoke tests confirm health. **|**
**References:** §4.5 Rollout sequencing, §5 Failure modes, §8.3 Runbooks & drills. **|**
**Breadcrumbs:** Migration scripts `ops/reference/migrate.py`, adoption replay `ops/reference/replay_adoption.py`, change-control template `ops/reference/migrations/README.md`.

- Run migrations in staging with `--dry-run` and attach artifacts to the change ticket before production execution.
- Capture bundle digests before/after migration; verify Settings and Guardian adoption reports reconcile.
- Roll back via RB-RM-ROLLBACK when adoption lag fails to recover within SLA.

### 8.5 Operational workflows (normative)

**Purpose:** Describe recurring operational tasks that preserve RM readiness outside of incidents. **|**
**Contract:** Each workflow has an owner, cadence, and evidence requirement; skipped cadences block publish approvals until remediated. **|**
**State:** Checklists and automations live in `ops/reference/workflows/`; outputs append to `ops/reference/workflow_log.jsonl`. **|**
**Failure modes & handling:** Missed cadences surface in quarterly audits; owners must backfill evidence and update training materials. **|**
**Observability:** Workflow logs, editorial queue dashboards, and CI history provide signals. **|**
**References:** §8.1 Operational posture, §8.3 Runbooks & drills. **|**
**Breadcrumbs:** Workflow docs `ops/reference/workflows/*.md`, automation scripts `ops/reference/*.py`.

#### 8.5.1 Release cadence & change control (binding)

**Purpose:** Outline release planning and change management expectations. **|**
**Contract:** Reference releases follow blue/green cadence with change ticket linkage, reviewer approval, and rollout wave planning before production publish. **|**
**State:** Change tickets, rollout metadata, and validation evidence stored alongside bundle manifests under `ops/reference/releases/<date>/`. **|**
**Failure modes & handling:** Missing evidence or approvals blocks release; rolled-back bundles documented with remediation tasks. **|**
**Observability:** Release dashboards display upcoming waves, adoption status, and freeze windows. **|**
**References:** §4.5 Rollout sequencing, §8.3.2 RB-RM-ROLLBACK. **|**
**Breadcrumbs:** Release scripts `ops/reference/release.py`, change log `ops/reference/change_log.md`.

#### 8.5.2 Editorial tooling & UX (normative)

**Purpose:** Support content operations with efficient tooling. **|**
**Contract:** Editorial UI exposes diffs, validation status, dependency impacts, and quick actions; fallback CLI workflow documented for outages. **|**
**State:** UI events logged for audit; assignments persisted to maintain accountability. **|**
**Failure modes & handling:** UI downtime triggers CLI-based process and opens incidents per §8.3.4 RB-RM-PUBLISH. **|**
**Observability:** “Reference Manager – Editorial” dashboards track queue age, assignment counts, and throughput. **|**
**References:** §6.4 Editorial telemetry, §8.3.4 RB-RM-PUBLISH. **|**
**Breadcrumbs:** UI code `apps/platform/reference_manager/ui`, tests `tests/reference/test_editorial_ui.py`.

#### 8.5.3 Source harvest readiness (binding)

**Purpose:** Ensure connectors and manual upload fallbacks remain ready before outages occur. **|**
**Contract:** Quarterly drills exercise manual upload, credential rotation, and license verification workflows. **|**
**State:** Connector credentials, manual upload scripts, and licensing attestations live in `ops/reference/harvest/`. **|**
**Failure modes & handling:** Expired credentials or missing manual upload procedures delay harvest recovery; owners remediate during readiness reviews. **|**
**Observability:** Pre-harvest checklists and connector synthetic jobs track readiness. **|**
**References:** §2.2 Source acquisition, §8.3.3 RB-RM-HARVEST. **|**
**Breadcrumbs:** Manual upload tooling `ops/reference/manual_upload.py`, readiness checklist `ops/reference/harvest/readiness.md`.

______________________________________________________________________

## 9) Dependencies (informative)

**Purpose:** Map RM’s upstream sources and downstream consumers. **|**
**Contract:** RM depends on verified government/court sources; downstream services (LPE, Settings, Guardian, Compose, Analyze, Portal) must acknowledge bundles and honor alignment manifests. **|**
**State:** Dependency metadata lives in connector configs, adoption tables, and alignment manifests. **|**
**Failure modes & handling:** Source outages, adoption lag, or alignment violations trigger runbooks outlined in §5 and §8.3. **|**
**Observability:** Dashboards “Reference Manager – Adoption”, “Downstream Alignment”, and “Residency & Endpoint Posture” highlight dependency health. **|**
**References:** §2 Responsibilities, §3 API contract, §4 State management. **|**
**Breadcrumbs:** Integration code `packages/udocket_core/reference_manager/integration.py`, adoption tables `reference_bundle_adoption`.

- Upstream: official court/government portals, licensing agreements, provider attestations.
- Downstream: LPE compiles bundles into policy/localization; Settings activates residency/waiver metadata; Guardian enforces waivers/residency; Compose/Analyze fetch templates; Portal displays localized assets.

______________________________________________________________________

## 10) References (informative)

**Purpose:** Provide quick access to authoritative documents, ADRs, diagrams, and scripts supporting RM. **|**
**Contract:** Update this list whenever dependencies change; docs lint ensures referenced artifacts exist. **|**
**State:** References point to immutable ADRs, diagrams, runbooks, and tooling maintained elsewhere in the repo. **|**
**Failure modes & handling:** Broken references must be resolved before merging; CI highlights missing artifacts. **|**
**Observability:** `scripts/docs/lint_docs.py` validates references and link health. **|**
**References:** `docs/mkdocs.yml` navigation entries. **|**
**Breadcrumbs:** `scripts/docs/lint_docs.py`, `scripts/docs/build_runbook_catalog.py`.

- ADRs: ADR-0004 Localization & Policy Engine, ADR-0005 OPA Policy Plane. **|**
- TDD: TDD §6 Reference Data, TDD Appendix G ERD, TDD Appendix H Operational Guides. **|**
- Runbooks: §8.3.2 RB-RM-ROLLBACK, §8.3.3 RB-RM-HARVEST, §8.3.4 RB-RM-PUBLISH, §8.3.5 RB-RM-LICENSE, §8.3.6 RB-RM-RESIDENCY. **|**
- Diagrams: `docs/src/services/ref-manager/diagrams/*.mmd`, `docs/src/overview/tdd/diagrams/data-lineage-v1.mmd`. **|**
- Scripts & tooling: `ops/reference/rollback_bundle.py`, `scripts/reference/verify_locale_coverage.py`, `ops/reference/pipelines/*.yaml`. **|**
- Dashboards: `infra/grafana/reference_manager_availability.json`, `infra/grafana/reference_manager_adoption.json`, `infra/grafana/reference_manager_compliance.json`.

______________________________________________________________________
