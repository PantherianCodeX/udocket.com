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
    - [C.1 `packages/common/`](#c1-packagescommon)
    - [C.2 `packages/core/`](#c2-packagescore)
    - [C.3 `packages/ai/`](#c3-packagesai)
    - [C.4 `packages/docs_tooling/`](#c4-packagesdocs_tooling)
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
├─ apps/ — Django/Channels apps and Celery task wrappers; no standalone services
├─ automation/ — LangGraph graphs + typed agents; no provider SDKs inline
├─ packages/ — reusable libraries + SDKs; no runtime configs
├─ services/ — deployable backends (FastAPI, workers); no UI
├─ config/ — environment + service configuration (app/infra/ai/communications)
├─ infra/ — Kubernetes, mesh, Terraform, CI; declarative only
├─ ops/ — runbooks, watchdogs, localization evidence, security reports
├─ tests/ — unit/integration/contract/e2e/load/localization suites; no prod code
├─ tooling/ — developer/test tooling, fixtures, plugins
├─ docs/ — documentation content + appendices; tooling lives in packages/docs_tooling
├─ out/ — generated artifacts (doc builds, bundles, packs, reports); ignored by VCS
└─ storage/ — runtime/dev media (per-tenant); ignored outside local dev
```

______________________________________________________________________

### A. Platform runtime & core services {#a-platform-runtime-core-services}

The platform runtime is split into web apps under `apps/` and independent services under
`services/`, making each deployable obvious and auditable.

```tree
apps/ — Django/Channels apps; no service backends
├─ platform/ — UI/API entrypoint (admin + client dashboards, DRF/GraphQL)
├─ web/ — shared UI routing, rate limits, presentation helpers
├─ assistants/ — conversational UIs, retrieval bridges, moderation UX
├─ channels/ — Channels routing, presence services
├─ portal/ — download guards, token validation, signed URL brokers
└─ jobs/ — job control APIs, upload finalize flows, SSE schemas

services/ — independently deployable backends; no UI (each keeps runtime in src/)
├─ communications/ — outbound orchestration (outbox, receipts, providers, templates)
├─ reference-manager/ — ingestion connectors, editorial tooling, bundle publisher
├─ llm-registry/ — service façade over packages.ai.providers; no prompt data
├─ speech-registry/ — speech provider parity controller, diarization assets
├─ storage-adapters/ — blob integrity checks, audio normalization, manifest sealing
├─ assistants-gateway/ — LangGraph SSE bridge for staff/client assistants
├─ guardian-quarantine/ — review console backend, waiver ledger APIs
├─ digital-signer/ — TSA/OCSP connectors, PDF/A pipelines; CA-only egress
├─ audit-ledger/ — immutable audit sinks + query tooling
├─ search-index/ — case search + vector shards with residency-aware storage
├─ artifact-store/ — media lifecycle, retention enforcement, hashing
├─ policy-residency/ — residency catalogs, waiver manifests, mesh integration
├─ worker-cluster/ — Celery deployment, queue topology, watchdog runner
├─ settings/ — hierarchical settings API, diff/activation engine
├─ lpe/ — localization + policy compiler (packs + OPA bundles)
└─ opa-bundle-server/ — optional bundle CDN façade for OPA agents
```

> **Service convention:** Every service directory keeps runtime Python code in `src/` so Dockerfiles, k8s manifests, and infra scripts can live alongside without polluting import paths. Apps and packages keep their modules at the root (no extra `src/`) to minimize import depth.

### B. Automation & agent pipelines {#b-automation-agent-pipelines}

Automation code is layered so LangGraph pipelines, agent implementations, and Celery task
modules remain isolated yet composable.

```tree
automation/ — agent pipelines + orchestration; no provider SDKs inline
├─ langgraph/ — canonical graphs (transcribe/analyze/compose/timeline/relationship)
├─ pipelines/ — stage metadata, QA gates, cost ceilings; deterministic
├─ agents/ — typed agent implementations; call packages.ai.api for AI
│  ├─ transcribe/ — Azure Speech (CA regions), ops/audit writers
│  ├─ analyze/ — summaries/outline/timeline/entity seeds via packages.ai.api.summarize
│  ├─ compose/ — client/lawyer deliverables, QA gating via packages.ai.api.compose
│  ├─ timeline/ — normalized events with speakers/offsets via packages.ai.api.extract_timeline
│  └─ relationship/ — entity/edge extraction via packages.ai.api.extract_entities
```

### C. Shared packages & SDKs {#c-shared-packages-sdks}

Packages house reusable primitives, policy-bound orchestration, AI tooling, docs helpers,
and customer SDKs.

```tree
packages/ — shared libraries; no runtime configs
├─ common/ — cross-cutting strictly typed utilities; pure helpers
├─ core/ — core domain + agent runtime libs; no web/DB/LLM SDKs
├─ ai/ — exportable AI runtime incl. providers/promptsets/safety; all AI deps live here
├─ docs_tooling/ — docs toolchain + structure validators; no docs content
└─ client_sdks/ — typed SDKs (Python/TS) generated from API schemas; public-only
```

#### C.1 `packages/common/`

```tree
packages/common/ — pure helpers; no network/DB/framework deps
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

#### C.2 `packages/core/`

```tree
packages/core/ — domain libs + agents; no Django/DB/LLM SDKs
├─ agents/ — typed agents + helpers (transcribe/analyze/compose; deterministic outputs)
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

#### C.3 `packages/ai/`

```tree
packages/ai/ — exportable AI runtime; all AI deps live here (LLM Registry +)
├─ py.typed — ensures downstream type safety
├─ api.py — stable surface (summarize/compose/extract/chat/embed) for other projects
├─ config.py — typed config (providers, routing, caps, locales); region-restricted egress guards
├─ providers/ — SDK adapters (Azure OpenAI, OpenAI, Bedrock, local_llm) with residency gates
├─ routing/ — model selection + fallback policy; deterministic + audited
├─ promptsets/ — locale/role packs + org overrides (absorbs legacy prompt assets)
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

#### C.4 `packages/docs_tooling/`

```tree
packages/docs_tooling/ — docs tooling only; no product docs
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

services/communications/ — outbound communications service; no UI
├─ src/ — orchestration, receipts API, digests, cost tracking
├─ providers/ — email/SMS/webhook adapters; residency guardrails
└─ templates/ — canonical notification templates + policy banners

config/communications/templates/ — per-org/per-environment template overrides

ops/localization/ — localization QA evidence (accessibility recordings, release logs)

config/localization/packs/ — locale pack sources, ICU inputs, pseudolocale toggles

out/localization/packs/ — compiled locale packs emitted by services/lpe
```

### E. Data, trust & compliance {#e-data-trust-compliance}

Data services bundle reference management, signing, search, artifact storage, and policy
residency to keep attestations and licensing consistent.

```tree
services/reference-manager/ — source ingestion, editorial tooling, bundle publisher
├─ src/ — APIs, ingestion workers, editorial tooling
└─ migrations/ — schema evolution, deterministic seeds

services/digital-signer/ — signing pipelines, TSA/OCSP connectors
├─ src/ — signing APIs + workers
└─ integrations/ — TSA/OCSP client configs

services/audit-ledger/ — immutable audit sinks + query tooling
services/search-index/ — case search + vector shards with residency-aware storage
services/artifact-store/ — media lifecycle, retention enforcement, hashing
services/policy-residency/ — residency catalogs, waiver manifests, mesh integration
services/lpe/ — localization + policy compiler; emits packs + OPA bundles

ops/policy/ — approvals, provenance logs, signer manifests
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

config/ — environment + service configuration
├─ app/ — Django/Celery/env defaults
├─ infra/ — environment overlays/values for Helm/Terraform/mesh
├─ ai/ — provider routing, promptset overrides
├─ communications/ — template overrides, provider knobs
└─ services/ — per-service value files (lpe, reference-manager, etc.)

ops/ — operational evidence; append-only
├─ runbooks/ — generated catalog + source sections
├─ watchdogs/ — automation evidence, heartbeat logs
├─ localization/ — LPE release checklists, QA evidence
└─ security/ — key rotation reports, waiver ledgers, incident templates

out/ — generated artifacts (gitignored)
├─ doc-builds/ — MkDocs/PDF outputs
├─ test-reports/ — coverage + junit
├─ ai/promptsets/ — compiled prompt bundles
├─ policy/bundles/ — signed OPA bundles
└─ localization/packs/ — compiled locale packs
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

tooling/ — developer/test tooling; no production dependencies
├─ pytest_plugins/ — repo-specific plugins/markers
├─ fixtures/ — shared fixtures/factories; typed helpers
└─ scripts/ — repo automation, generators, code mods
```

### H. Documentation system {#h-documentation-system}

Documentation follows the same taxonomy as the platform, with appendices mirroring the
tree definitions and tooling living in `packages/docs_tooling`.

```tree
docs/ — documentation content; tooling lives in packages/docs_tooling
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
