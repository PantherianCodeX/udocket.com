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
- **Maintenance:** Run `python scripts/docs/lint_docs.py docs/src/services/search-index.md docs/src/overview/tdd.md docs/tdd_modularization.md`. Updates require sync with product PRDs and LLM Registry (embedding models).
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

## 3) API Contract (stub)

- REST endpoints to be finalized post-PRD freeze. Placeholder interface summary above; detailed schemas will live in Appendix once GA. **|**
- Websocket/SSE updates planned for live search filters; gating on performance validation. **|**
- Error codes will follow API appendix once defined (`search-index` section). **|**

______________________________________________________________________

## 4) State Management (stub)

- Index storage expected to use OpenSearch (Canada cluster) with alias per tenant; lexical index shards align with residency requirements. **|**
- Vector store options under evaluation (pgvector vs. managed). Decision tracked via ADR backlog. **|**
- Metadata tables in Postgres hold canonical mapping from artifact to index document to manage reindex and erasure. **|**

______________________________________________________________________

## 5) Failure modes & resiliency (stub)

- **Index lag:** Backlog monitors trigger scaling. **|**
- **Cross-tenant leak:** Automated integration tests ensure ACL enforcement; any detection triggers immediate incident. **|**
- **Embedding provider failure:** Fallback to lexical search with user-visible banner. **|**
- **Search relevancy regressions:** A/B guardrails in PRD; manual rollback path documented in runbook skeleton. **|**

______________________________________________________________________

## 6) Observability (stub)

- Planned metrics: `search_index_backlog_total`, `search_query_latency_seconds`, `search_embedding_staleness_minutes`. **|**
- Dashboards to include ingestion lag, query latency distribution, error breakdown. **|**
- Logging: Structured events per query with anonymized search terms hashed using `compliance.search_hash_salt`. **|**

______________________________________________________________________

## 7) Security & compliance (stub)

- Residency: Index & embeddings stored in Canada regions only. **|**
- Access: Enforce Identity service RBAC + Guardian decisions; vector queries masked to avoid leaking sensitive text. **|**
- Privacy: Queries hashed, stored for 30 days max; DSAR removal cascades to logs. **|**
- Compliance: Search features behind approvals; new release requires Privacy review. **|**

______________________________________________________________________

## 8) Operations & runbooks (stub)

- Placeholder runbooks: `RB-SEARCH-INGEST`, `RB-SEARCH-ERASURE`, `RB-SEARCH-RELEVANCY`. Drafts live under `docs/src/ops/runbooks/search/` (to-be-created). **|**
- Drills: Planned quarterly ingestion/backlog tabletop. **|**
- On-call: `search-oncall@` (to be staffed before GA). **|**

______________________________________________________________________

## 9) Dependencies (stub)

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
- LLM Registry specification — `../services/llm-registry.md`.
- Artifact Store specification — `../services/artifact-store.md`.
- Accounts & Tenants specification — `../services/accounts-tenants.md`.
- Product PRD: Search Discovery (link pending).

