---
title: uDocket — Search & Indexing Service Specification
subtitle: Case Discovery, Vector Enrichment, and Query APIs
author:
  - Discovery Platform Working Group
version: 0.1-draft
status: provisional
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Engineering
  - Knowledge Systems
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - Compliance Lead
  - Product Discovery Lead
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
  - <header class="page-header">uDocket — Search & Indexing Service Specification <br>
    Case Discovery, Vector Enrichment, and Query APIs</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Discovery Platform Working Group |
| Version | 0.1-draft |
| Status | provisional |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Engineering; Knowledge Systems |
| Reviewers | Compliance Lead; Product Discovery Lead |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Captures the emerging Search & Indexing service providing full-text search, semantic/vector retrieval, and case discovery APIs referenced in TDD §6.5 (analysis consumers) and §11 (portal discovery). Document serves as stub until full implementation lands; where behaviour is TBD the section references product requirements.
- **Structure:** Standard sections with emphasis on ingestion pipelines, index lifecycle, query APIs, and compliance guardrails (residency, confidentiality).
- **Maintenance:** Run `python -m doc_tools.manage_docs --lint docs/data/search-index.md docs/overview/tdd.md docs/tdd_modularization.md`. Updates require sync with product PRDs and LLM Registry (embedding models).
- **Change protocol:** Any change enabling cross-tenant discovery, new vector providers, or schema modifications must reference ADR backlog and receive Privacy + Architecture approval. Production rollout gated by readiness checklist (Appendix TBD).
- **References:** TDD §6.5, §11.3, LLM Registry §3 (embedding profiles), Artifact Store §2.3 (promotion signals), Ops runbooks `RB-SEARCH-*`.
- **Contacts:** Knowledge Systems (implementation), Product Discovery (requirements), escalation `#ops-search`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Deliver secure, tenant-scoped search across transcripts, artifacts, and metadata with both lexical and vector retrieval, enabling portal discovery and agent prompts. **|**
**Contract:** Maintains per-tenant indexes, enforces residency, honours artifact visibility (ExclusiveSwap), and surfaces deterministic ranking signals. Vector enrichment uses approved embedding models with deterministic UUIDs. **|**
**State:** Planned ownership of `search_index`, `search_document`, `search_embedding`, ingestion jobs, and query caches. **|**
**Failures & handling:** Index drift, embedding backlog, or unauthorized cross-tenant exposure must trigger immediate rollback (`RB-SEARCH-ISOLATION`). **|**
**Observability:** Metrics `search_index_backlog_total`, `search_query_latency_seconds`, `search_embedding_staleness_minutes`; stub dashboards “Search Health” and “Embedding Pipeline”. **|**
**Breadcrumbs:** Implementation landing in `apps/platform/search/` (in progress), ingestion tasks `apps/platform/search/tasks.py`, tests `tests/platform/search/` (placeholder). **|**
**References:** Product PRD (Search discovery), TDD §6.5, Artifact Store §2, Accounts & Tenants §2.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Define responsibilities for search ingestion, indexing, and querying even while implementation matures. **|**
**Contract:** Guarantee per-tenant isolation, deterministic ingestion, timely updates, and compliance with retention/erasure policies. **|**
**State:** Document ingestion pipelines, embedding stores, ranking metadata. **|**
**Failures & handling:** Outline fallback behaviours and escalations. **|**
**Observability:** Metrics/dashboards verifying responsibilities. **|**
**Breadcrumbs:** Placeholder modules referencing planned packages. **|**
**References:** TDD §6.5, Artifact Store §2, Accounts §2.

### 2.1 Ingestion pipeline (binding once GA)

- **Contract:** Consume artifact promotions, transcripts, and analysis outputs to build lexical index documents within 5 minutes P95. Ingestion uses append-only change feed from Artifact Store ops logs. **|**
- **State:** `search_document` rows track artifact UUID, version, hash, and tenant. **|**
- **Observability:** `search_index_backlog_total`, ingestion lag metrics. **|**
- **Failures & handling:** Backpressure triggers slowdown of optional features and pages `RB-SEARCH-INGEST`. **|**
- **Breadcrumbs:** Planned task `apps/platform/search/tasks.py::ingest_artifact`, tests placeholder `tests/platform/search/test_ingest.py`. **|**

### 2.2 Vector enrichment (binding once GA)

- **Contract:** Selected artifacts/transcripts receive embeddings using LLM Registry embedding profiles (`embedding.profile_id`). Shifts require deterministic UUIDv5 seeded by artifact+profile to maintain stable references. Residency enforced (Canada models only). **|**
- **State:** `search_embedding` table referencing `search_document`. **|**
- **Observability:** `search_embedding_staleness_minutes`, queue depth metrics. **|**
- **Failures & handling:** Embedding service degradation triggers fallback to lexical search. **|**
- **Breadcrumbs:** Planned module `apps/platform/search/embedding.py`, tests placeholder `tests/platform/search/test_embeddings.py`. **|**

### 2.3 Query APIs (binding once GA)

- **Contract:** Provide `/api/search/` for lexical queries and `/api/search/vector/` for semantic retrieval. Enforce tenant isolation, user permissions (Guardian judgments, artifact visibility), and paging. **|**
- **State:** Query cache `search_query_cache` (optional) for repeated analytics queries. **|**
- **Observability:** `search_query_latency_seconds`, `search_query_error_total`. **|**
- **Failures & handling:** Query errors return `POLICY_BLOCK`, `VALIDATION_ERROR`, or `PROVIDER_DEGRADED` for embedding fallback. **|**
- **Breadcrumbs:** Planned view `apps/platform/search/views.py`, tests placeholder `tests/platform/search/test_api.py`. **|**

### 2.4 Retention & erasure coupling (binding)

- **Contract:** Respect artifact retention and DSAR erasure; removal events propagate to search indexes within 24 hours. **|**
- **State:** Tombstone records `search_tombstone` ensure deletion audit. **|**
- **Observability:** `search_tombstone_backlog_total`. **|**
- **Failures & handling:** Missed erasure triggers compliance escalation `RB-SEARCH-ERASURE`. **|**
- **Breadcrumbs:** Planned job `apps/platform/search/tasks.py::apply_tombstones`. **|**

______________________________________________________________________

## 3) API Contract (binding)

**Purpose:** Capture emerging external and internal interfaces for search. **|**
**Contract:** Document planned REST/SSE endpoints, internal ingestion hooks, and error code expectations even before GA. **|**
**State:** API definitions tracked in PRD, OpenAPI drafts, and search service prototypes. **|**
**Failures & handling:** Until GA, failures fall back to lexical search or return platform defaults; future updates will tighten contracts. **|**
**Observability:** Planned metrics include request latency, error totals, and SSE health. **|**
**Breadcrumbs:** Prototype modules `apps/platform/search/api.py`, design docs `docs/product/search/*.md`. **|**
**References:** TDD §6.5, Platform Runtime §3.3, Artifact Store §3.

### 3.1 External Interfaces (binding)

- REST queries (`GET /api/search/`) return lexical results scoped to tenant and permissions. **|**
- Semantic queries (`POST /api/search/vector`) accept embedding vectors or text, returning scored matches. **|**
- Future SSE endpoint streams re-ranking updates when new artifacts arrive; pending performance validation. **|**

### 3.2 Internal Interfaces (binding)

- Ingestion workers consume Artifact Store ops logs and Guardian events via `search.ingest` queue. **|**
- Embedding pipeline integrates with LLM Registry; deterministic UUID seeds stored in `search_embedding`. **|**
- Tombstone processor applies DSAR deletions within 24 h using `search.tombstone` queue. **|**

### 3.3 API Error Codes (binding)

**Purpose:** Track search-specific error codes once defined. **|**
**Contract:** Currently no search-specific codes exist; the catalog remains empty until GA. **|**
**State:** YAML placeholder `docs/data/search-index/error_codes.yaml`. **|**
**Failures & handling:** Platform codes (`POLICY_BLOCK`, `VALIDATION_ERROR`, `PROVIDER_DEGRADED`) cover initial rollout. **|**
**Observability:** Unknown codes will emit `search_api_error_unknown_total`. **|**
**Breadcrumbs:** Planned API middleware `apps/platform/search/api_errors.py`. **|**
**References:** Platform Runtime §3.3, Accounts & Tenants §3.

> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#search-indexing-service)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `POLICY_BLOCK` | Access policy, Guardian verdict, or tenant residency rule forbids returning requested results. | Confirm caller permissions, review Guardian verdicts, or adjust residency scope before retrying. |
| `PROVIDER_DEGRADED` | Underlying search index or embedding service is unavailable or lagging beyond thresholds. | Retry after backoff; system falls back to lexical only. Escalate using RB-SEARCH-INGEST if the incident persists. |
| `VALIDATION_ERROR` | Query payload or filter parameters failed validation (unsupported field, malformed vector, or tenant scope missing). | Correct the query parameters using the published schema and retry. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `POLICY_BLOCK` | 403 | Yes | search_api_error_total<br>search_acl_violation_total |
| `PROVIDER_DEGRADED` | 503 | Yes | search_api_error_total<br>search_index_backlog_total |
| `VALIDATION_ERROR` | 400 | No | search_api_error_total<br>search_query_validation_total |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

### 3.4 Events & Integrations (binding)

- Emits search readiness events (`SEARCH_INDEX_READY`, `SEARCH_EMBEDDING_READY`) to notify UI and agents when indexing completes. **|**
- Integrates with FinOps / telemetry exporters for query analytics once GA. **|**

______________________________________________________________________

## 4) State Management (binding)

**Purpose:** Describe planned storage model for search indexes and embeddings. **|**
**Contract:** Maintain per-tenant indexes, deterministic document identifiers, and tombstones supporting DSAR propagation. **|**
**State:** Proposed OpenSearch clusters, Postgres metadata tables (`search_document`, `search_embedding`, `search_tombstone`), Redis caches. **|**
**Failures & handling:** Reindex jobs restore drift; tombstone processor enforces deletions within 24 h. **|**
**Observability:** Metrics `search_index_backlog_total`, `search_tombstone_backlog_total`; dashboards “Search State Health”. **|**
**Breadcrumbs:** Design doc `docs/product/search/indexing.md`, migrations draft `apps/platform/search/migrations/`. **|**
**References:** TDD §6.5, Appendix J SQL policies, Settings keys `search.*`.

- Index storage expected to use OpenSearch (Canada cluster) with alias per tenant; lexical index shards align with residency requirements. **|**
- Vector store options under evaluation (pgvector vs. managed). Decision tracked via ADR backlog. **|**
- Metadata tables in Postgres hold canonical mapping from artifact to index document to manage reindex and erasure. **|**

______________________________________________________________________

## 5) Failure Modes (binding)

**Purpose:** Outline resiliency expectations for search as it matures. **|**
**Contract:** Detect and remediate index lag, prevent cross-tenant leaks, and fallback gracefully when embeddings unavailable. **|**
**State:** Ingestion backlog monitors, access control tests, embedding pipeline controllers. **|**
**Failures & handling:** Runbooks `RB-SEARCH-INGEST`, `RB-SEARCH-ERASURE`, and `RB-SEARCH-RELEVANCY` govern response; cross-tenant leaks trigger immediate incident and feature rollback. **|**
**Observability:** Metrics `search_index_backlog_total`, `search_embedding_staleness_minutes`, `search_query_error_total`; dashboards “Search Health” and “Embedding Pipeline”. **|**
**Breadcrumbs:** Draft runbooks `docs/ops/runbooks/search/*.md`, incident templates `ops/search/incidents/*.md`, PRD resiliency section. **|**
**References:** TDD §6.5, Appendix I controls map.

- **Index lag:** Backlog monitors trigger scaling. **|**
- **Cross-tenant leak:** Automated integration tests ensure ACL enforcement; any detection triggers immediate incident. **|**
- **Embedding provider failure:** Fallback to lexical search with user-visible banner. **|**
- **Search relevancy regressions:** A/B guardrails in PRD; manual rollback path documented in runbook skeleton. **|**

______________________________________________________________________

## 6) Observability (binding)

**Purpose:** Define telemetry required for search readiness. **|**
**Contract:** Instrument ingestion lag, query latency, embedding staleness, and error breakdowns before GA. **|**
**State:** Planned Prometheus metrics, Grafana dashboards, structured logs with hashed queries. **|**
**Failures & handling:** Missing telemetry blocks feature rollout; dashboards validated in staging before enablement. **|**
**Observability:** Metrics `search_index_backlog_total`, `search_query_latency_seconds`, `search_embedding_staleness_minutes`. **|**
**Breadcrumbs:** Monitoring design `docs/product/search/observability.md`, synthetic tests `scripts/search/run_synthetics.py`. **|**
**References:** Observability spec §4, Settings keys `search.telemetry.*`.

- Planned metrics: `search_index_backlog_total`, `search_query_latency_seconds`, `search_embedding_staleness_minutes`. **|**
- Dashboards to include ingestion lag, query latency distribution, error breakdown. **|**
- Logging: Structured events per query with anonymized search terms hashed using `compliance.search_hash_salt`. **|**

### 6.1 SLOs & Targets (binding)

**Purpose:** Establish provisional targets for launch gating. **|**
**Contract:** Index updates applied within 5 minutes P95, query latency ≤ 500 ms P95, cross-tenant violations remain zero. **|**
**State:** SLO drafts `infra/monitoring/search-slo-rules.yaml`, Grafana board “Search SLO (draft)”. **|**
**Failures & handling:** Breaches halt rollout; reopen feature flag only after incident review. **|**
**Observability:** Burn-rate alerts `search_ingest_slo_burn`, `search_latency_slo_burn`. **|**
**Breadcrumbs:** SLO design doc `docs/product/search/slo.md`. **|**
**References:** TDD §6.5, FinOps dashboards.

______________________________________________________________________

## 7) Security & Compliance (binding)

**Purpose:** Capture security posture and privacy obligations for search. **|**
**Contract:** Enforce Canadian residency, tenant-level isolation, Guardian filtering, and DSAR propagation across indexes and logs. **|**
**State:** Planned IAM policies, residency configurations, hashed query logs, waiver ledgers. **|**
**Failures & handling:** Cross-tenant access or residency drift triggers RB-SEARCH-ISOLATION; DSAR failures escalate to Compliance. **|**
**Observability:** Security alerts `search_residency_violation_total`, `search_acl_violation_total`; audit logs hashed for tamper evidence. **|**
**Breadcrumbs:** Security design `docs/product/search/security.md`, compliance checklist `ops/search/checklists/compliance.md`. **|**
**References:** Settings keys `search.*`, Guardian §5, Accounts & Tenants §7.

- Residency: Index & embeddings stored in Canada regions only. **|**
- Access: Enforce Identity service RBAC + Guardian decisions; vector queries masked to avoid leaking sensitive text. **|**
- Privacy: Queries hashed, stored for 30 days max; DSAR removal cascades to logs. **|**
- Compliance: Search features behind approvals; new release requires Privacy review. **|**

______________________________________________________________________

## 8) Operational Notes (binding)

**Purpose:** Summarize operational readiness for search rollout. **|**
**Contract:** Define on-call staffing, runbook ownership, and drill cadence before GA. **|**
**State:** Draft runbooks, drill plans, staffing proposals. **|**
**Failures & handling:** Production enablement only after runbooks and drills validated; gaps block feature flag. **|**
**Observability:** Runbook catalog checks, drill scheduler metrics. **|**
**Breadcrumbs:** Runbooks `docs/ops/runbooks/search/`, staffing plan `ops/search/rota.md`. **|**
**References:** Ops catalog, Appendix S roles.

- Placeholder runbooks: `RB-SEARCH-INGEST`, `RB-SEARCH-ERASURE`, `RB-SEARCH-RELEVANCY`. Drafts live under `docs/ops/runbooks/search/` (to-be-created). **|**
- Drills: Planned quarterly ingestion/backlog tabletop. **|**
- On-call: `search-oncall@` (to be staffed before GA). **|**

### 8.1 Operational Posture (binding)

**Purpose:** Define staffing assumptions leading up to GA. **|**
**Contract:** Knowledge Systems primary on-call during beta; formal rotation established before GA with 5 min acknowledge targets. **|**
**State:** Staffing draft `ops/search/rota.md`, readiness checklist `ops/search/checklists/posture.md`. **|**
**Failures & handling:** Coverage gaps escalate to Platform Operations; feature flag remains off until roster confirmed. **|**
**Observability:** PagerDuty sandbox metrics, docs lint ensuring checklist completion. **|**
**Breadcrumbs:** Staffing plan `ops/search/rota.md`, rollout checklist `ops/search/checklists/posture.md`. **|**
**References:** Ops catalog, Appendix S roles.

### 8.2 Incident Triggers (binding)

**Purpose:** List alerts that will declare search incidents once live. **|**
**Contract:** Alerts on index backlog, query errors, residency violations, and embedding latency must page on-call. **|**
**State:** Alert definitions `infra/monitoring/search-alerts.yaml` (draft), synthetic monitors `scripts/search/run_synthetics.py`. **|**
**Failures & handling:** Alert tuning documented in incident retros; false positives adjusted before GA. **|**
**Observability:** Grafana “Search Incident Triggers”, docs metric `search_alert_suppressed_total`. **|**
**Breadcrumbs:** Alert definitions `infra/monitoring/search-alerts.yaml`, PagerDuty sandbox service, synthetic monitors. **|**
**References:** §6 Observability, RB-SEARCH-INGEST, RB-SEARCH-ERASURE.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Keep emergent runbooks aligned with rollout. **|**
**Contract:** Draft runbooks for ingestion, erasure, and relevancy must exist before beta; drills executed quarterly. **|**
**State:** Runbooks `docs/ops/runbooks/search/*.md`, drill evidence `ops/search/drills/<date>/`. **|**
**Failures & handling:** Missing runbooks or evidence blocks feature promotion. **|**
**Observability:** Runbook catalog report, drill scheduler metrics. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler docs, Slack `#ops-search`. **|**
**References:** RB-SEARCH-INGEST, RB-SEARCH-ERASURE, RB-SEARCH-RELEVANCY.

#### 8.3.1 Runbook Index (informative)

| Runbook code | Scenario | Notes |
| --- | --- | --- |
| `RB-SEARCH-INGEST` | Ingestion backlog or index staleness | Validates replay tooling and scaling plan |
| `RB-SEARCH-ERASURE` | DSAR propagation failure | Confirms tombstone application and evidence capture |
| `RB-SEARCH-RELEVANCY` | Relevancy regression or model rollout | Coordinates rollback to prior embeddings/models |

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarize core playbooks executed during incidents. **|**
**Contract:** Keep runbooks versioned, linked to alerts, and reviewed quarterly. **|**
**State:** Markdown in `docs/ops/runbooks/search/*.md`, automation scripts `scripts/ops/search/*.py`. **|**
**Failures & handling:** Stale runbooks flagged by docs lint `runbook_catalog_stale_total`. **|**
**Observability:** Governance dashboard, runbook catalog output. **|**
**Breadcrumbs:** Runbook files, automation scripts, incident templates. **|**
**References:** RB-SEARCH-INGEST, RB-SEARCH-ERASURE, RB-SEARCH-RELEVANCY.

#### 8.3.3 Drill Cadence & Evidence (binding)

Drills rehearse ingestion, erasure, and relevancy scenarios with evidence stored for governance review. **|**

- Quarterly ingestion backlog tabletop; evidence stored in `ops/search/drills/<date>/ingest.md`. **|**
- Semi-annual DSAR replay drill verifying tombstone propagation. **|**
- Relevancy regression simulation after major model changes with evidence archived in `ops/sear../data/<date>/`. **|**
- Compliance reviews track `search_evidence_gap_total`; gaps block GA until resolved. **|**

See Ops catalog and Appendix O decision log for templates and evidence requirements.

### 8.4 Migrations & Backfills (binding)

**Purpose:** Capture planned migrations and backfills for search indexes. **|**
**Contract:** Perform reindex/backfill jobs via `scripts/search/reindex.py`, record before/after hashes, and coordinate with Artifact Store events. **|**
**State:** Migration manifests `ops/search/migrations/`, backlog replays, change tickets. **|**
**Failures & handling:** Failed reindex jobs roll back aliases; incidents logged with evidence. **|**
**Observability:** Reindex dashboard “Search Migrations”, alerts `search_reindex_failure_total`. **|**
**Breadcrumbs:** Migration scripts, change calendar, PRD rollout checklist. **|**
**References:** TDD §6.5, Appendix J SQL policies.

### 8.5 Operational Workflows (binding)

**Purpose:** Describe recurring tasks such as relevancy sampling and query audits. **|**
**Contract:** Weekly relevancy sampling, monthly ACL audit, quarterly DSAR verification executed before expanding rollout. **|**
**State:** Workflow checklists `ops/search/workflows/*.md`, automation outputs `ops/search/reports/*.csv`. **|**
**Failures & handling:** Missed workflows trigger `search_workflow_overdue_total` and halt rollout until resolved. **|**
**Observability:** Workflow dashboard, docs lint, analytics reports. **|**
**Breadcrumbs:** Workflow docs, automation scripts, staffing rosters. **|**
**References:** Compliance playbooks, Ops catalog.

## 9) Dependencies (binding)

**Purpose:** Identify critical integrations search relies on. **|**
**Contract:** Maintain isolation and event contracts with upstream/downstream services. **|**
**State:** Dependency metadata documented in Platform Runtime catalog and search rollout plan. **|**
**Failures & handling:** Dependency incidents coordinated via referenced runbooks. **|**
**Observability:** Dependency dashboards overlay health metrics for Artifact Store, Guardian, and LLM Registry. **|**
**Breadcrumbs:** Platform Runtime catalog, Ops runbook index, Settings `search.*` keys. **|**
**References:** Platform Runtime §3, Settings §5 (`search.*`), Guardian §5, LLM Registry §3.

| Dependency | Responsibility | Notes |
| --- | --- | --- |
| Artifact Store | Source documents, retention signals | Ops log feed drives ingestion |
| Accounts & Tenants | Access control, residency | Tenant state informs index visibility |
| Guardian | Eligibility filtering (quarantine, masked content) | Quarantined artifacts excluded |
| LLM Registry | Embedding profiles, moderation | Embedding models configured here |
| Settings Registry | Feature flags (`search.*`), throttles | Controls GA rollout and per-tenant enablement |

______________________________________________________________________

## 10) References

- TDD §6.5 Agent consumers of search outputs.
- TDD §11 Portal discovery roadmap.
- LLM Registry specification — `../automation/llm-registry.md`.
- Artifact Store specification — `../data/artifact-store.md`.
- Accounts & Tenants specification — `../customer/accounts-tenants.md`.
- Product PRD: Search Discovery (link pending).
