---
title: "uDocket — Reference Manager Technical Design"
subtitle: "Reference Data Ingestion, Editorial Workflow, and Publishing Specification"
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
  - '<header class="page-header">uDocket — Reference Manager Technical Design <br> Reference Data Ingestion, Editorial Workflow, and Publishing Specification</header>'
  - '<footer class="page-footer">Confidential · Last updated 2025-10-23 · Page <span class="page-number"></span> of <span class="page-count"></span></footer>'
---

**Audience:** Reference Programs, Localization & Policy Engine, Settings, Guardian, SRE, QA, Product Operations\\
**Purpose:** Describe Reference Manager responsibilities, contracts, lifecycle workflows, and observability so downstream services consume consistent regulated data.

---

## Document controls

| Field           | Value |
| --------------- | ----- |
| Version         | 0.1-draft |
| Status          | Implementable (mirrors front matter `status`; KEP lifecycle applies: Provisional → Implementable → Implemented) |
| Last updated    | 2025-10-23 (source of truth is the front matter `last_updated`) |
| Primary owners  | Platform Architecture; Security Engineering; Reference Programs |
| Approvers       | Architecture Steering Committee; Security Review Board |
| Reviewers       | QA Engineering Lead; SRE Manager |
| ADR index       | `docs/adr/README.md` (immutable ADRs referenced in front matter `related_adrs`) |
| Migration plan  | Replaces legacy Reference Engine coverage in the platform TDD; `/reference/*` shims remain read-only until all clients complete the migration |
| Docs validation | `python scripts/docs/lint_docs.py` (see `docs/README.md` for tooling) |
| Link lint       | `python scripts/docs/link_check.py --strict` (CI `docs-link-check` stage blocks unresolved §/App./ADR refs) |

Body sections follow the Purpose/Contract/State/Failure/Observability/Breadcrumb scaffold enforced by `scripts/docs/lint_docs.py --check-template`. Section tags `(binding)` and `(normative)` align with the platform TDD.

---

## 0) Reading guide

- **Scope:** Service charter, source ingestion, editorial workflows, publishing, integrations, and observability for Reference Manager.
- **Structure:** Numbered sections limited to three levels of depth; shared diagrams remain in the platform TDD appendices (App.A state flows, App.G ERD).
- **Cross-references:** Use `§<number>` for this document, `TDD §<number>` for the platform TDD, and `App.<letter>` when pointing at shared appendices or runbooks.
- **Maintenance:** Run `python scripts/docs/lint_docs.py` before submitting edits. Schema snippets must match `spec/schemas/reference_*` fixtures; CI verifies locale coverage and bundle manifests.
- **Doc change protocol:** Any PR touching Reference Manager ingestion, bundles, or review workflows must update this document alongside linked ADRs. Architecture/Security reviewers block merges if services diverge from these contracts.

---

## 1) Service overview

### 1.1 Charter & mandate (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/service.py`, Tests `tests/specs/test_reference_manager_charter.py::test_scope_enforced`, Observability Grafana “Reference Manager – Ingestion & Quality” (metric `reference_manager_catalog_version`).
*Purpose: Define Reference Manager responsibilities and success criteria.*
*Contract: Reference Manager acquires regulated reference data, curates it with provenance and licensing, and publishes signed bundles that downstream services treat as authoritative.*
*State: Bundles, review queues, and adoption status persist in Postgres schemas `reference_harvest`, `reference_staging`, `reference_curated`, and `reference_bundle_registry`.*
*Failure modes & retries: Harvest retries exponential backoff with per-source quotas; publishing locks prevent concurrent conflicting releases; unsigned bundles are rejected.*
*Observability: Catalog version metrics, adoption lag histograms, and audit JSONL streams track lifecycle health.*

Reference Manager packages every regulated dataset required for downstream compliance. Each signed publish includes privacy and residency policy catalogues, court forms and filing instructions, questionnaires and intake scripts, localization packs, language coverage metadata, infrastructure footprints, and SPI tagging for sensitive sources. Localization & Policy Engine (LPE) consumes these bundles directly so `PolicyContext` mirrors the latest policies, supported languages, and court assets, keeping Guardian, Portal, and Settings aligned with the same data.

### 1.2 Assets & scope (normative)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/domains.py`, Tests `tests/specs/test_reference_domains.py::test_domain_registry`, Observability Grafana “Reference Manager – Review & Publishing” (metric `reference_manager_diff_backlog`).
*Purpose: Enumerate assets curated by Reference Manager.*
*Contract: RM covers jurisdictions, residency/privacy annotations, localization strings, questionnaires, court forms, identifier crosswalks, infrastructure catalogues, and provider endpoint metadata.*
*State: Domains register in `reference_domain` with required schema manifests (`spec/schemas/reference_bundle_manifest.schema.json`).*
*Failure modes & retries: Missing assets block publish and raise `reference_manager_domain_gap` alerts until editors remediate.*
*Observability: Diff backlog by domain, locale coverage heatmaps, and resource availability probes feed dashboards and reviewer workload metrics.*

Scope includes jurisdictions and court hierarchies, residency/privacy policy annotations, localization strings, questionnaires, court forms, identifiers and crosswalks, provider endpoints, and structured lookups used by Guardian, agents, Portal, or Settings. Infrastructure catalogues describe deployment footprints so downstream services share the same regional and compliance picture.

### 1.3 Separation from LPE & other services (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/events.py`, Tests `tests/specs/test_reference_lpe_contract.py::test_bundle_handshake`, Observability Grafana “Reference Adoption” (metric `reference_manager_bundle_adoption_seconds`).
*Purpose: Clarify boundaries between Reference Manager, LPE, and adjacent services.*
*Contract: RM is the editorial source; LPE is the runtime resolver. Settings, Guardian, and Portal consume LPE outputs that embed RM bundle versions.*
*State: `reference_manager.catalog.published` and `.updated` events capture bundle IDs, hashes, and `effective_at` timestamps; LPE stores adoption metadata alongside `PolicyContext` digests.*
*Failure modes & retries: If LPE detects unsigned or stale bundles, it halts compiles and emits `reference_bundle_stale_total`; RM must republish or roll back.*
*Observability: Adoption lag metrics, event delivery traces, and LPE digest comparisons highlight divergence.*

RM publishes immutable, signed bundles with manifests carrying SHA-256 digests, semantic versions, compatibility ranges, and license metadata. LPE treats bundles as read-only inputs; any override requires a new revision instead of runtime edits. `/reference/*` API shims remain read-only until migration completes.

### 1.4 Infrastructure catalogue & residency posture (normative)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/infra.py`, Tests `tests/specs/test_reference_infra_catalog.py::test_catalog_shape`, Observability Grafana “Residency & Endpoint Posture” overlay (metric `reference_manager_provider_endpoints`).
*Purpose: Describe infrastructure catalogue responsibilities.*
*Contract: RM tracks deployment footprints, residency attestations, provider endpoints, and related waivers for every supported region.*
*State: Bundles publish `infra_components[]` and `provider_endpoints[]` with compute/storage classes, approved CIDRs, SAN expectations, waivers, and attestation references.*
*Failure modes & retries: Missing attestation or invalid residency metadata blocks publish; drift triggers endpoint scan incidents.*
*Observability: Endpoint catalogue versions, residency scan findings, and waiver ledgers remain visible in dashboards and App.O reports.*

Dedicated SaaS tenants record deployment IDs, residency posture, and compliance attestations. Provider endpoints enumerated in RM bundles materialize Settings allowlists and power residency enforcement (`network.egress.allowed_hosts`).

### 1.5 Deliverables & rollout sequencing (binding)

**Breadcrumbs:** Implementation `ops/reference/rollout_checklist.md`, Tests `tests/specs/test_reference_rollout.py::test_exit_criteria`, Observability Release dashboard “deploy:reference-adoption”.
*Purpose: Outline launch deliverables and rollout gates.*
*Contract: RM launches with governance, bundle schema/signing automation, MediaWiki adapter, manual proposal workflow, operational dashboards, and integration tests that publish `courts@0.1.0`.*
*State: Rollout checklist artifacts track completion; `/reference/*` shims remain read-only until adoption metrics remain green for 30 days.*
*Failure modes & retries: Deploy gate `deploy:reference-adoption` blocks release when stale bundles persist; rollback cookbook must execute within SLA.*
*Observability: Adoption lag monitors, deploy gate status, and quarterly rollback drills feed release readiness.*

Harvesting includes court scraper framework, crosswalk schema, questionnaire/form ingestion, dual-approval enforcement, and synthetic monitors. Deprecation workflows, diff endpoints, locale coverage tooling, and FinOps dashboards operate continuously. Exit criteria require no direct writes outside RM, read-only shims for legacy APIs, adoption lag SLO adherence, golden snapshot validation, and quarterly rollback exercises.

---

## 2) Source acquisition & ingestion

### 2.1 Source connectors & acquisition (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/harvest.py`, Tests `tests/reference/test_harvest_sources.py::test_connector_contracts`, Observability Grafana “Reference Manager – Ingestion & Quality” (metrics `reference_manager_harvest_total{source,*}`).
*Purpose: Detail source acquisition patterns and controls.*
*Contract: Connectors honor per-source throttles, licensing, and provenance while capturing evidence for compliance review.*
*State: Raw payloads persist in `reference_harvest` with source URIs, hashes, attribution, and ingest timestamps.*
*Failure modes & retries: Connector failures exponential backoff; after three failures RM disables the source and pages Content Ops.*
*Observability: Harvest totals, selector failure counts, and ingest duration histograms feed dashboards and alerts.*

Connectors include:
- **MediaWiki/Wikidata adapters:** Delta pulls keyed by page IDs or QIDs, watchlists for change notifications, and license capture (Wikipedia → CC BY-SA 4.0 with attribution propagation, Wikidata structured data → CC0) so downstream surfaces render correct attribution automatically.
- **Court and tribunal websites:** Respectful scraping with robots compliance, per-domain rate limits, randomized user agents, selector health checks, and sanitized HTML parsing into structured metadata.
- **Government/open-data portals:** CSV/JSON/API feeds with schema version tracking and checksum validation across provincial datasets, justice ministry APIs, and federal open-data hubs.
- **Vendor feeds & authenticated sources:** Signed downloads or webhook-triggered updates with HMAC verification; API keys rotate via Vault and failures auto-disable connectors.
- **Internal editorial submissions:** UI/API for staff to propose corrections, additions, or emergency updates with justification and attachments.

### 2.2 ETL, normalization & entity resolution (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/normalize.py`, Tests `tests/reference/test_normalization.py::test_entity_resolution_thresholds`, Observability Grafana “Reference Manager – Ingestion & Quality” (metric `reference_manager_selector_failure_total`).
*Purpose: Explain normalization steps and entity resolution strategy.*
*Contract: RM enforces consistent identifiers, formatting, and locale coverage while routing ambiguous matches to review.*
*State: Normalized candidates live in `reference_staging`; review actions promote to `reference_curated` with version metadata.*
*Failure modes & retries: Confidence below threshold routes items to manual review; normalization errors raise `REFERENCE_NORMALIZATION_ERROR` events and halt publish for affected items.*
*Observability: Selector failure rates, normalization error counts, and review queue backlog highlight bottlenecks.*

Primary identifiers rely on ISO-3166, official court IDs, and Wikidata QIDs. Normalization enforces consistent casing, diacritics, street abbreviations, and URL validation. Optional geocoding uses jurisdiction-aware providers and stores coordinate precision separately. Entity resolution applies deterministic keys first, then fuzzy matching with confidence scores; low confidence requires manual approval. Localization strings carry locale, text, fallback locale, source attribution, and licensing; missing locales generate tasks for editorial follow-up.

### 2.3 Storage & schema layering (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/models.py`, Tests `tests/reference/test_schema_layering.py::test_lifecycle_tables`, Observability Grafana “Reference Manager – Storage Footprint” (metric `reference_manager_storage_bytes_total`).
*Purpose: Describe storage design and schema layering for catalog assets.*
*Contract: RM maintains logical schemas for harvest, staging, approved data, history, and bundle registry with immutable rollback paths.*
*State: Core tables (`jurisdiction`, `court`, `court_locale`, `identifier_crosswalk`, `residency_policy`, `localization_string`, `questionnaire`, `questionnaire_item`, `form`, `form_locale`, `reference_change_log`, `bundle`, `bundle_resource`) persist metadata including version, hashes, licenses, and effective windows.*
*Failure modes & retries: Schema migrations fail when required metadata missing; nightly integrity jobs ensure history snapshots exist before purge jobs execute.*
*Observability: Storage bytes, bundle counts, and retention job results recorded in ops JSONL streams.*

Raw harvest payloads purge after 30 days (unless an incident hold is active), staging tables roll to history after 90 days, and approved/history records follow Appendix C timelines. Immutable bundle registry entries persist for audit.

### 2.4 Pipelines & scheduling (normative)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/scheduler.py`, Tests `tests/reference/test_scheduler.py::test_job_windows`, Observability Grafana “Reference Manager – Pipelines” (metric `reference_manager_pipeline_lag_seconds`).
*Purpose: Summarize recurring and on-demand pipeline schedules.*
*Contract: Pipelines honor external rate policies, maintain freshness, and alert when SLAs slip.*
*State: Celery queues `reference-harvest`, `reference-validate`, and `reference-publish` track job status; schedule manifests document cadence.*
*Failure modes & retries: Missed runs trigger PagerDuty incidents and retry windows; emergency jobs require manual acknowledgement.*
*Observability: Pipeline lag metrics, job success ratios, and schedule audit logs feed operational dashboards.*

Daily jobs run MediaWiki delta sync, selector health checks, and localization completeness scans. Weekly jobs recrawl low-change domains, refresh license attestations, and produce string coverage reports. On-demand editorial hotfix pipelines publish `*-rc` bundles with short TTL, and emergency deprecations stage near-immediate effective dates while paging Legal Ops. Pipelines respect per-source concurrency limits.

---

## 3) Governance & publishing

### 3.1 Review workflows & approvals (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/review.py`, Tests `tests/reference/test_review_workflow.py::test_dual_control`, Observability Grafana “Reference Manager – Review & Publishing” (metric `reference_manager_pending_reviews`).
*Purpose: Define review checkpoints, approvals, and SLAs.*
*Contract: Changes traverse `DRAFT → REVIEW → APPROVED → PUBLISHED → DEPRECATED → ARCHIVED`, with dual approval for sensitive updates.*
*State: `reference_change_log` records proposer, reviewers, timestamps, diff hashes, citations, and SLA progress.*
*Failure modes & retries: SLA breaches trigger `reference_manager_review_sla_violation`; emergency hotfixes require retrospective approval within 48h.*
*Observability: Pending review counts, SLA timers, and emergency workflow usage appear on dashboards.*

Dual approval is mandatory for residency/privacy flags, HIPAA/PHIPA toggles, and identifier removals, with distinct roles (Content Ops + Legal Ops). Deprecations record replacement pointers, effective dates, and user guidance. Emergency guardrails require an incident captain, automated tickets, and completion of the adoption rollback checklist within 24h.

Governance RACI (binding):

| Change class                          | Responsible (R) | Accountable (A)   | Consulted (C)              | Informed (I)               | SLA |
| ------------------------------------- | --------------- | ----------------- | -------------------------- | -------------------------- | --- |
| Routine catalog update (name/address) | Content Ops     | RM Product Owner  | Legal Ops                  | Platform Support, Product  | Review ≤ 2 business days |
| Residency/privacy flag update         | Content Ops     | Security Eng Lead | Legal Ops, Architecture    | Compliance, Product        | Dual approval; publish ≤ 4 business hours after approval |
| Questionnaire/form change             | Legal Ops       | RM Product Owner  | Content Ops, UX            | Platform Support, Product  | Review ≤ 3 business days |
| Emergency hotfix (court closure)      | Content Ops     | RM Product Owner  | Legal Ops, Security (post) | All affected customers, Product | Publish ≤ 2 hours; retrospective review within 48 hours |

### 3.2 Catalog bundles & publishing pipeline (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/publish.py`, Tests `tests/reference/test_publish_pipeline.py::test_manifest_integrity`, Observability Grafana “Reference Manager – Review & Publishing” (metric `reference_manager_publish_total`).
*Purpose: Explain bundle construction, signing, and promotion.*
*Contract: Bundles follow semantic versioning, include manifests with hashes/licensing, and publish only after validation succeeds.*
*State: Bundle manifests stored in `reference_bundle_registry` with signatures, compatibility ranges, and license ledgers.*
*Failure modes & retries: Validation failures block signing; adoption lag alerts fire when LPE has not compiled within SLA.*
*Observability: Publish totals, adoption lag histograms, and bundle diff artifacts feed release dashboards.*

Bundles such as `courts@1.4.0`, `jurisdictions@2.1.3`, `localization@0.9.2`, and `questionnaires@0.5.0` include `effective_at` timestamps, signed SHA-256 hashes, provenance manifests, and compatibility notes. Payloads include deterministic JSON plus optional Parquet/CSV artifacts. Snapshot archives ship alongside deltas to support fast-forward with rollback hooks.

### 3.3 Questionnaires, forms, and auxiliary resources (normative)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/resources.py`, Tests `tests/reference/test_questionnaires.py::test_locale_completeness`, Observability Grafana “Reference Manager – Resource Coverage” (metric `reference_resource_missing_locale_total`).
*Purpose: Summarize questionnaire, form, and auxiliary resource management.*
*Contract: RM enforces locale completeness, scoring metadata, accessibility status, and license tracking across resources.*
*State: `questionnaire`, `questionnaire_item`, `form`, and `form_locale` tables persist metadata including hashes, coverage, and renewal cadence.*
*Failure modes & retries: Locale coverage validator blocks publish; resource availability monitors raise `reference_resource_unavailable` for stale endpoints.*
*Observability: Locale coverage metrics, accessibility probes, and resource update events visible via dashboards and SSE feeds.*

Questionnaires store hierarchical blocks, localized prompts, scoring rubrics, conditional logic, and deterministic UUIDs. Court forms capture download URIs, hashes, accessibility status, renewal cadence, and license terms; availability monitors run HEAD requests and raise alerts on failure. Resource bundles publish via `reference_manager.resource.updated` events so LPE and Compose/Analyze agents access consistent localization keys and metadata. Locale packs must satisfy `scripts/reference/verify_locale_coverage.py` before publish.

### 3.4 Deliverable templates & localization packs (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/templates.py`, Tests `tests/reference/test_templates.py::test_registry_contract`, Observability Grafana “Deliverable Catalog & Templates” (metric `reference_manager_template_staleness_seconds`).
*Purpose: Govern deliverable templates and localized assets used by Analyze/Compose pipelines.*
*Contract: Template registry entries originate in RM, carry provenance/licensing, and emit invalidation events consumed by downstream services.*
*State: Templates reside under `reference_manager.templates` (`templates/<deliverable_id>/<locale>/<version>.(md|docx|jinja)`) with manifest metadata `engine`, `locale`, `version`, `checksum_sha256`, `approved_by`, `effective_at`, and compatibility notes.*
*Failure modes & retries: Missing approvals or checksum drift blocks publish; invalidation events replay until GraphRunner acknowledges the updated digest.*
*Observability: Template freshness, coverage, and invalidation retry counters feed dashboards; cache reconciliation failures raise `reference_manager_template_cache_miss_total`.*

Deliverable definitions reference template UUIDs and locale coverage enforced here. Analyze and Compose pipelines resolve templates via signed bundle manifests; cache invalidations propagate through `reference_manager.template.updated` events and require downstream acknowledgment before adoption is marked complete. Organization overrides follow the same schema with dual approvals and linting against `DeliverableContext`; rejected overrides remain archived for audit. Localization packs share the registry, embedding locale fallback rules and attribution strings consumed by LPE.

### 3.5 Security, compliance & licensing (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/security.py`, Tests `tests/reference/test_license_ledger.py::test_required_metadata`, Observability Grafana “Reference Manager – Compliance” (metric `reference_manager_license_violation_total`).
*Purpose: Capture security posture, licensing obligations, and sensitive data controls.*
*Contract: Harvested content is sanitized, license metadata enforced, sensitive changes dual-approved, and audit trails immutable.*
*State: License ledger persists in `reference_license` tables; audit sinks append JSONL evidence for sensitive changes.*
*Failure modes & retries: Missing license metadata blocks publish; sanitation failures abort ingest with alerts.*
*Observability: License violation counters, sensitive change audits, and sanitation error logs feed compliance dashboards.*

Scraped HTML is sanitized before storage; allowed MIME types enforce TLS-only downloads. License ledger tracks source licenses and downstream attribution requirements; pipelines block bundles missing metadata. Rate limits and access controls guard adapters and APIs; scraping credentials rotate via Vault. Sensitive metadata changes trigger `REFERENCE_SENSITIVE_CHANGE` events. Attribution enforcement requires UI/API clients to display badges via `reference_attribution.render(metadata)`; Guardian rejects artifacts missing required attribution metadata.

### 3.6 Testing & safeguards (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/tests.py`, Tests `tests/reference/test_bundle_validation.py::test_validation_suite`, Observability CI job “reference-manager-validate”.
*Purpose: Enumerate automated protections for catalog integrity.*
*Contract: Golden snapshots, contract tests, semantic guards, and adoption drills run per publish.*
*State: Golden fixtures live under `tests/reference/golden/`; validation artifacts stored with bundle registry entries.*
*Failure modes & retries: Validation failures halt signing; adoption drills failing re-open incidents until resolved.*
*Observability: CI pipeline results, synthetic adoption checks, and rollback exercise reports track readiness.*

Golden snapshots enforce deterministic outputs; scraper contract tests use recorded fixtures. Semantic publish guard blocks breaking changes without replacements. Each publish runs `reference_manager.validate_bundle` to verify schema integrity, license metadata, and diff thresholds, then triggers staging adoption tests verifying LPE compiles and surfaces updates. Adoption rollback cookbook `ops/reference/rollback_bundle.py` reverses releases and records `BUNDLE_ROLLBACK_REPORT` artifacts within the 15 minute SLA.

### 3.7 Risks & mitigations (normative)

**Breadcrumbs:** Implementation `ops/reference/risk_register.md`, Tests `tests/reference/test_risk_controls.py::test_selector_monitoring`, Observability Risk dashboard “Reference Manager – Risk Register”.
*Purpose: Track key program risks and mitigations.*
*Contract: Selector churn, license drift, entity merges, and stale runtime scenarios map to explicit controls.*
*State: Risk register entries link to monitoring artifacts and mitigation playbooks.*
*Failure modes & retries: Missing mitigation evidence escalates to Program Leads; stale runtime triggers adoption lag incidents.*
*Observability: Risk dashboard surfaces status, last review date, and outstanding actions.*

Selector churn prompts automated tickets with last good HTML snapshots and temporarily holds bundles at the prior version. License drift is prevented via metadata enforcement and quarterly audits. Entity merges require manual approval and corrective bundles referencing prior hashes. Stale runtime is mitigated through adoption lag alerts, LPE staleness guards, and synthetic monitors for high-value jurisdictions.

---

## 4) Integration & APIs

### 4.1 API & automation surfaces (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/api.py`, Tests `tests/reference/test_api_surface.py::test_permissions`, Observability Grafana “Reference Manager – API Health” (metric `reference_manager_api_latency_seconds`).
*Purpose: Surface APIs and automation channels exposing catalog data.*
*Contract: REST, SSE, and GraphQL interfaces enforce scopes, MFA for high-risk actions, and signed bundle delivery.*
*State: API gateway routes under `/api/v1/reference_manager` with scope checks; SSE feeds stream review and publish events.*
*Failure modes & retries: Auth failures log audits and rate-limit clients; publish endpoints refuse unsigned manifests.*
*Observability: API latency histograms, error ratios, and SSE delivery metrics monitor health.*

REST surface includes:
- `POST /api/v1/reference_manager/sources/wikipedia/refresh?qid=`
- `POST /api/v1/reference_manager/sources/court_scrape`
- `PUT /api/v1/reference_manager/catalogs/:domain/proposals/:id`
- `POST /api/v1/reference_manager/catalogs/:domain/proposals/:id/{approve|reject}`
- `POST /api/v1/reference_manager/catalogs/:domain/publish`
- `GET /api/v1/reference_manager/bundles/:domain/:version`
- `GET /api/v1/reference_manager/diff/:domain/:from/:to`
- `GET /api/v1/reference_manager/metrics`

SSE/GraphQL feeds stream review queue counts, bundle publishes, selector health alerts, and locale coverage gaps. Mutating endpoints require Keycloak client credentials with `reference_manager.editor` or higher scopes and HMAC signatures; high-risk actions demand step-up MFA.

### 4.2 Events & downstream adoption (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/events.py`, Tests `tests/specs/test_reference_events.py::test_publish_flow`, Observability Grafana “Reference Adoption” (metric `reference_manager_bundle_adoption_seconds`).
*Purpose: Describe event contracts and adoption flow.*
*Contract: RM emits publish/update events consumed by LPE, Settings, Guardian, and agents; adoption lag budgets enforced.*
*State: Event payloads include `{domain, version, effective_at, hash, affected_keys[], bundle_uri}` and adoption records store in LPE caches.*
*Failure modes & retries: Missing downstream acknowledgement triggers retries and alerts; adoption lag beyond SLA pages on-call.*
*Observability: Adoption lag metrics, event retry counters, and SSE delivery stats feed dashboards.*

RM publishes `reference_manager.catalog.published`, `.updated`, and `reference_manager.resource.updated`. LPE invalidates cached compiles, records bundle versions, and updates `PolicyContext`. Settings activation merges provider endpoint catalogues into allowlists; Guardian observes version digests for attribution checks. Region allowlist enforcement (`TDD §3.8`) and residency endpoint scans rely on RM’s provider endpoint data.

### 4.3 Settings, Guardian, and Portal alignment (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/integration.py`, Tests `tests/specs/test_reference_settings_alignment.py::test_allowlist_materialization`, Observability Grafana “Residency & Endpoint Posture” and “Reference Adoption” combined view.
*Purpose: Capture integration points with Settings, Guardian, and Portal.*
*Contract: Settings activation validates against RM catalogues; Guardian enforces attribution/licensing using bundle metadata; Portal and agents consume localized assets keyed by RM UUIDs.*
*State: Settings snapshots embed `reference_catalog_version`; Guardian manifests record attribution arrays; Portal caches reference metadata keyed by bundle digest.*
*Failure modes & retries: Activation fails when catalog entries missing; Guardian blocks approvals when attribution metadata absent; Portal falls back to last adopted bundle if downloads fail.*
*Observability: Activation diff artifacts, Guardian attribution rejection counters, and portal cache hit ratios monitor integration health.*

Settings defines region allowlists and activation lints against RM catalogues, rejecting entries outside curated regions or missing DPAs. Guardian applies compiled policies and attribution metadata, while Portal surfaces questionnaires, forms, and localized copy with deterministic UUIDs from RM.

Residency and provider endpoint updates follow the runbook: ingest provider metadata, attach attestation references, publish an updated `provider_endpoints` bundle, and trigger Settings activation replay. Adoption completes only after residency scanners confirm SAN and GeoIP alignment and Guardian acknowledges the refreshed digests; failures raise `reference_manager_provider_endpoint_violation_total` and remain paged until remediation closes.

---

## 5) Observability & operations

### 5.1 SLOs, metrics & alerts (binding)

**Breadcrumbs:** Implementation `infra/monitoring/reference_manager/`, Tests `tests/specs/test_reference_slos.py::test_thresholds`, Observability Grafana “Reference Manager – Ingestion & Quality” and “Reference Manager – Review & Publishing”.
*Purpose: Establish observability anchors and SLOs.*
*Contract: Harvest success ≥99%/day, selector failure rate <2% rolling 7d, median review <48h, publish latency P95 <2h, adoption lag P95 <10m.*
*State: Prometheus metrics include `reference_manager_harvest_total`, `reference_manager_ingest_duration_seconds`, `reference_manager_selector_failure_total`, `reference_manager_diff_backlog`, `reference_manager_publish_total`, `reference_manager_bundle_adoption_seconds`, `reference_resource_missing_locale_total`, `reference_manager_license_violation_total`.*
*Failure modes & retries: Breached SLOs trigger PagerDuty incidents and freeze promotions until recovery; adoption lag gate halts deploys when stale bundles persist.*
*Observability: Dashboards visualize coverage %, freshness age, selector failures, backlog, review SLA burn-down, and adoption overlays.*

FinOps metrics (`reference_manager_ingest_cost_cents{source}`, `reference_manager_api_credit_total`, `reference_manager_storage_bytes_total`) track spend with alerts at 80% of monthly caps. Alerts fire on stalled harvests, selector failure spikes, diff backlog breaches, publish attempts without license metadata, adoption lag beyond SLA, or RM publish without LPE compile.

### 5.2 Editorial tooling & UX (normative)

**Breadcrumbs:** Implementation `apps/platform/reference_console/`, Tests `tests/ui/test_reference_console.py::test_diff_workflow`, Observability Product analytics dashboard “Reference Console Usage”.
*Purpose: Document tooling that enables editors to curate, review, and preview catalogs.*
*Contract: Console provides diff viewer, license badges, attribution preview, crosswalk inspector, deprecation wizard, locale coverage heatmap, and review queue filters.*
*State: UI persists reviewer comments, inline annotations, and workflow state tied to proposals.*
*Failure modes & retries: UI outages fall back to API-driven workflows; accessibility regressions trigger release blocks until resolved.*
*Observability: Usage analytics, review queue throughput, and locale coverage interactions inform staffing and UX changes.*

Locale coverage heatmap highlights missing translations; machine translation assistance allowed but requires reviewer confirmation. Review queue supports search and filters by jurisdiction, change type, source, or SLA, with inline comments preserved across revisions.

### 5.3 Rollback, on-call & incident readiness (binding)

**Breadcrumbs:** Implementation `ops/reference/rollback_bundle.py`, Tests `tests/reference/test_rollback.py::test_restores_previous_version`, Observability PagerDuty service “Reference Manager On-Call”.
*Purpose: Ensure rollback tooling and incident workflows meet SLAs.*
*Contract: On-call follows adoption rollback cookbook, executes within 15 minutes, and records evidence artifacts.*
*State: `BUNDLE_ROLLBACK_REPORT` artifacts capture timestamps, reason, and validation evidence; incident tickets reference cookbook steps.*
*Failure modes & retries: Rollback failures auto-page escalation path; unresolved incidents block further publishes.*
*Observability: Incident metrics, rollback execution times, and cookbook audit logs feed the on-call review cadence.*

Synthetic adoption tests run in staging after every publish; quarterly drills exercise rollback tooling. Incident retros attach scanner evidence, Settings diffs, and Guardian waiver logs to the decision log (`TDD §15.3`), with follow-up tickets capturing provider engagement or automation gaps.

The EU-REFERENCE synthetic tenant executes `synthetics/reference_eu_residency.yaml` nightly, authenticating against the EU deployment, downloading `/reference/*` shims, and verifying `Sunset`, `Deprecation`, and successor headers alongside residency-constrained storage locations. The monitor raises `reference_eu_residency_violation_total` and pages Content Ops plus Security Engineering when residency assertions fail or bundles fall back to non-EU storage.

---
