---
title: "uDocket — TDD Appendix: Repository Trees"
subtitle: "Canonical service and package layout vision"
authors:
  - "Platform Architecture Team"
version: "0.1-draft"
status: implementable
classification: Confidential
last_updated: "2025-10-30"
updated_by: "Documentation Team"
owners:
  - "Platform Architecture"
reviewers:
  - "Platform Engineering"
approvers:
  - "Architecture Steering Committee"
approved_by:
approved_date:
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Platform Architecture Team |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-30 |
| Updated by | Documentation Team |
| Owners | Platform Architecture |
| Reviewers | Platform Engineering |
| Approvers | Architecture Steering Committee |
| Approved by | |
| Approved date | |
<!-- END AUTO-GENERATED: document-controls -->

______________________________________________________________________

## Appendix overview

This appendix captures the canonical repository trees that each service area must target.
Treat these as the design north star during large refactors: the LangGraph agents, web
applications, and operational tooling all land under the directories listed here.
The sections are ordered from the shared platform runtime outward through automation,
packages, experience, data, infrastructure, testing, and documentation. Update this
appendix manually whenever the canonical structure changes.

**Tree Index**

- [Document Controls](#document-controls)
- [Appendix overview](#appendix-overview)
  - [Top-level layout {#top-level-layout}](#top-level-layout-top-level-layout)
  - [A. Platform runtime \& core services {#a-platform-runtime-core-services}](#a-platform-runtime--core-services-a-platform-runtime-core-services)
  - [B. Automation \& agent pipelines {#b-automation-agent-pipelines}](#b-automation--agent-pipelines-b-automation-agent-pipelines)
  - [C. Shared packages \& SDKs {#c-shared-packages-sdks}](#c-shared-packages--sdks-c-shared-packages-sdks)
    - [C.1 `packages/udocket_common/`](#c1-packagesudocket_common)
    - [C.2 `packages/udocket_core/`](#c2-packagesudocket_core)
    - [C.3 `packages/udocket_ai/`](#c3-packagesudocket_ai)
    - [C.4 `packages/udocket_docs/`](#c4-packagesudocket_docs)
    - [C.5 `packages/client_sdks/`](#c5-packagesclient_sdks)
  - [D. Experience \& communications {#d-experience-communications}](#d-experience--communications-d-experience-communications)
  - [E. Data, trust \& compliance {#e-data-trust-compliance}](#e-data-trust--compliance-e-data-trust-compliance)
  - [F. Infrastructure \& operations {#f-infrastructure-operations}](#f-infrastructure--operations-f-infrastructure-operations)
  - [G. Testing \& quality {#g-testing-quality}](#g-testing--quality-g-testing-quality)
  - [H. Documentation system {#h-documentation-system}](#h-documentation-system-h-documentation-system)

______________________________________________________________________

### Top-level layout {#top-level-layout}

The root keeps peers shallow so each concern stays obvious.

```tree
udocket/ — repo root
├─ apps/ — Django/Channels apps only; no standalone services
├─ services/ — deployable backends (FastAPI, workers); no UI
├─ automation/ — LangGraph, agents, Celery modules; no provider SDKs inline
├─ packages/ — reusable libraries + SDKs; no runtime configs
├─ communications/ — notification orchestration/templates; no product UI
├─ localization/ — locale packs + QA evidence; no runtime services
├─ data-services/ — reference/signing/audit/search stacks; no UI
├─ compliance/ — waivers/licensing evidence; no business logic
├─ infra/ — Kubernetes, mesh, Terraform, CI; declarative only
├─ ops/ — runbooks/watchdogs/security evidence; append-only artifacts
├─ tests/ — unit/integration/contract/e2e/load suites; no prod code
├─ tools/ — dev/test tooling + fixtures; no service logic
└─ docs/ — documentation content + appendices; tooling lives in packages
```

______________________________________________________________________

### A. Platform runtime & core services {#a-platform-runtime-core-services}

The platform runtime is split into web apps under `apps/` and independent services under
`services/`, making each deployable obvious and auditable.

```tree
apps/ — Django/Channels apps; no service backends
├─ web/ — DRF/GraphQL APIs, UI routing, rate limits
│  ├─ staff/ — operator UIs, review consoles; no client flows
│  ├─ client/ — client portal, secure downloads; no staff tooling
│  └─ shared_components/ — UI kit, i18n hooks; reusable only
├─ channels/ — Channels routing, presence services; no business rules
├─ portal/ — download guards, token validation; no signing logic
└─ jobs/ — job control APIs, upload finalize, SSE schemas; no Celery impl

services/ — independently deployable backends; no UI
├─ guardian/ — judgment engine, quarantine hooks; API-only
├─ digital-signer/ — TSA/OCSP connectors, PDF/A pipelines; CA-only egress
├─ settings/ — hierarchical settings API, diff/activation engine
├─ localization-policy-engine/ — locale/policy lookup + compiler workers
├─ reference-manager/ — ingestion connectors, editorial tooling, bundle publisher
├─ notifications/ — outbox orchestration, provider adapters, delivery receipts
├─ worker-cluster/ — Celery deployment, queue topology, watchdog runner
├─ llm-registry/ — service facade over udocket_ai.providers; no prompt data
├─ speech-registry/ — speech provider parity controller, diarization assets
├─ storage-adapters/ — blob integrity checks, audio normalization, manifest sealing
├─ assistants-gateway/ — LangGraph SSE bridge for staff/client assistants
└─ guardian-quarantine/ — review console backend, waiver ledger APIs
```

### B. Automation & agent pipelines {#b-automation-agent-pipelines}

Automation code is layered so LangGraph pipelines, agent implementations, and Celery task
modules remain isolated yet composable.

```tree
automation/ — agent pipelines + orchestration; no provider SDKs inline
├─ langgraph/ — canonical graphs (transcribe/analyze/compose/timeline/relationship)
├─ pipelines/ — stage metadata, QA gates, cost ceilings; deterministic
├─ agents/ — typed agent implementations; call udocket_ai.api for AI
│  ├─ transcribe/ — Azure Speech (CA regions), ops/audit writers
│  ├─ analyze/ — summaries/outline/timeline/entity seeds via udocket_ai.api.summarize
│  ├─ compose/ — client/lawyer deliverables, QA gating via udocket_ai.api.compose
│  ├─ timeline/ — normalized events with speakers/offsets via udocket_ai.api.extract_timeline
│  └─ relationship/ — entity/edge extraction via udocket_ai.api.extract_entities
└─ task-modules/ — Celery task modules, watchdog hooks, capability registry integration
```

### C. Shared packages & SDKs {#c-shared-packages-sdks}

Packages house reusable primitives, policy-bound orchestration, AI tooling, docs helpers,
and customer SDKs.

```tree
packages/ — shared libraries; no runtime configs
├─ udocket_common/ — cross-cutting strictly typed utilities; pure helpers
├─ udocket_core/ — core domain + agent runtime libs; no web/DB/LLM SDKs
├─ udocket_ai/ — exportable AI runtime incl. providers/prompts/safety; all AI deps live here
├─ udocket_docs/ — docs toolchain + structure validators; no docs content
└─ client_sdks/ — typed SDKs (Python/TS) generated from API schemas; public-only
```

#### C.1 `packages/udocket_common/`

```tree
packages/udocket_common/ — pure helpers; no network/DB/framework deps
├─ py.typed — marker for downstream type checking
├─ ids/ — deterministic UUID5 + unique title helpers; pure functions
├─ json/ — canonical encoders/decoders; no file I/O
├─ time/ — zoneinfo utilities, duration/interval types
├─ hashing/ — SHA-256/MD5 wrappers; pure
├─ agents/ — shared Result/Config Protocols/TypedDicts; zero Any
├─ types/ — dataclasses/StrEnum/Protocols reused across services
├─ testing/ — property strategies/fixtures; test-only helpers
└─ utils/ — small, single-purpose pure helpers; no side effects
```

#### C.2 `packages/udocket_core/`

```tree
packages/udocket_core/ — domain libs + agents; no Django/DB/LLM SDKs
├─ agents/ — typed agents + helpers (transcribe/analyze/compose, deterministic outputs)
├─ guardian/ — decision/policy adapters; API-layer agnostic
├─ lpe/ — localization/policy compilers; deterministic artifacts
├─ failover/ — retry + idempotency envelopes; no silent fallbacks
├─ reference_manager/ — ingestion/normalization primitives; typed payloads
├─ redaction/ — PII patterns + deterministic hashers
├─ logging/ — structured logging + ops JSONL writers; pyright-clean
├─ retry/ — shared retry/backoff helpers; deterministic
├─ idem/ — idempotency keys/manifests; stable schemas
├─ utils/ — package-specific shared helpers and utilities
└─ settings/ — typed config loaders, env snapshot helpers
```

#### C.3 `packages/udocket_ai/`

```tree
packages/udocket_ai/ — exportable AI runtime; all AI deps live here (LLM Registry +)
├─ py.typed — ensures downstream type safety
├─ api.py — stable surface (summarize/compose/extract/chat/embed) for other projects
├─ config.py — typed config (providers, routing, caps, locales); region-restricted egress guards
├─ providers/ — SDK adapters (Azure OpenAI, OpenAI, Bedrock, local_llm) with residency gates
├─ routing/ — model selection + fallback policy; deterministic + audited
├─ prompts/ — locale packs + org overrides absorbing legacy udocket_prompts assets
├─ compilers/ — localization-aware prompt builders producing hashed artifacts
├─ safety/ — moderation, redaction pre/post filters; deterministic
├─ embeddings/ — embedding clients (Azure/OpenAI/local) with typed outputs
├─ retrieval/ — RAG helpers (chunking, scoring); pure logic
├─ telemetry/ — request hashing, cost tracking, provenance; no PII leakage
├─ types/ — dataclasses/Protocols/StrEnum for AI payloads; zero Any
├─ errors/ — rich recoverable/non-recoverable exceptions; actionable messages
├─ utils/ — package-specific shared helpers and utilities
├─ packaging/ — build scripts emitting packaged prompt/artifact bundles for consumers
└─ settings/ — typed config loaders, env snapshot helpers
```

#### C.4 `packages/udocket_docs/`

```tree
packages/udocket_docs/ — docs tooling only; no product docs
├─ config/ — configuration files
├─ plugins/ — custom plugins
├─ src/doc_tools — tools source files
│  ├─ build/ — scripts for building documents
│  ├─ utils/ — package-specific shared helpers and utilities
│  ├─ config/ — configuration for the doc tools (paths, settings)
│  └─ sync/ — Scripts to keep documents in sync
└─ tests/ — Unit tests
```

#### C.5 `packages/client_sdks/`

```tree
packages/client_sdks/ — public SDKs; no private/admin APIs
├─ schemas/ — OpenAPI sources; single truth for codegen
├─ codegen/ — pinned templates/pipelines; reproducible outputs
├─ python/ — Python SDK (sync/async clients, typed models, residency-safe defaults)
├─ typescript/ — TypeScript SDK (fetch/axios clients, typed models, browser/node examples)
└─ utils/ — Package-specific shared helpers and utilities
```

### D. Experience & communications {#d-experience-communications}

Experience modules track staff and client UIs, assistants, communications pipelines, and
localization evidence so every touchpoint is localized and auditable.

```tree
apps/web/ — UI surfaces; no backend logic
├─ staff/ — operator workspace, review consoles, approvals
├─ client/ — client-facing flows, secure messaging/downloads
└─ shared_components/ — design system, localization hooks, accessibility widgets

apps/assistants/ — conversational UI, retrieval bridges, moderation UX; no provider keys stored

communications/ — notification system; no UI
├─ outbox/ — delivery orchestration, receipts, digests; auditable
├─ providers/ — email/SMS/webhook adapters; residency guardrails
└─ templates/ — localization-ready notification templates + policy banners

localization/ — LPE artifacts; no service code
├─ packs/ — compiled locale packs, ICU snapshots, pseudolocale outputs
└─ evidence/ — accessibility recordings, localization QA checklists, release logs
```

### E. Data, trust & compliance {#e-data-trust-compliance}

Data services bundle reference management, signing, search, artifact storage, and policy
residency to keep attestations and licensing consistent.

```tree
data-services/ — data-centric services; no product UI
├─ reference-manager/ — source ingestion, editorial tooling, bundle publisher
├─ digital-signer/ — signing pipelines, TSA/OCSP connectors
├─ audit-ledger/ — immutable audit sinks + query tooling
├─ search-index/ — case search + vector shards with residency-aware storage
├─ artifact-store/ — media lifecycle, retention enforcement, hashing
└─ policy-residency/ — residency catalogs, waiver manifests, mesh integration

compliance/ — governance artifacts; no runtime logic
├─ waivers/ — dual-approval waivers, expiry tracking
└─ licensing/ — licensing evidence from Reference Manager
```

### F. Infrastructure & operations {#f-infrastructure-operations}

Infrastructure directories surface Kubernetes manifests, service mesh policy, Terraform,
observability assets, runbooks, and security automation.

```tree
infra/ — declarative ops; no app code
├─ kubernetes/ — Helm/Flux per service, mesh policies, pod security baselines
├─ service-mesh/ — SPIFFE/SPIRE configs, AuthorizationPolicies, egress allowlists
├─ terraform/ — cloud infra, storage, databases, key vaults
├─ observability/ — dashboards, alerts, synthetic probes
└─ pipelines/ — CI/CD workflows, docs validation pipelines

ops/ — operational evidence; append-only
├─ runbooks/ — generated catalog + source sections
├─ watchdogs/ — automation evidence, heartbeat logs
├─ localization/ — LPE release checklists, QA evidence
└─ security/ — key rotation reports, waiver ledgers, incident templates
```

### G. Testing & quality {#g-testing-quality}

Testing assets cover unit, integration, contract, end-to-end, load, and localization
suites plus shared fixtures.

```tree
tests/ — quality gates; no prod code
├─ unit/ — per-module tests; ≥90% coverage maintained
├─ integration/ — service boundary tests, Celery flows
├─ contract/ — API/error schema enforcement, PolicyContext digests
├─ e2e/ — full-stack scenarios with hermetic data
├─ load/ — performance baselines with reproducible datasets
└─ localization/ — pseudolocale + accessibility suites; deterministic

tools/ — test tooling; no production dependencies
├─ pytest_plugins/ — repo-specific plugins/markers
└─ fixtures/ — shared fixtures/factories; typed helpers
```

### H. Documentation system {#h-documentation-system}

Documentation follows the same taxonomy as the platform, with appendices mirroring the
tree definitions and tooling living in `packages/udocket_docs`.

```tree
docs/ — documentation content; tooling lives in packages/udocket_docs
├─ overview/ — TDD + roadmap
│  └─ tdd/
│     └─ appendices/ — canonical appendix sources (incl. repository_trees)
├─ platform/ — runtime/service specs
├─ automation/ — agent + LangGraph specs
├─ data/ — reference/signing/audit/search specs
├─ experience/ — UI/assistants/communications docs
├─ customer/ — onboarding, tenancy, SLA
├─ ops/ — operational runbooks
├─ architecture/ — ADRs, diagrams
└─ typing/ — typing roadmap + refactor plan
```
