# Feature Specification: AI Refactor Implementation Delivery

**Feature Branch**: `002-ai-refactor-plan`  
**Created**: 2025-11-15  
**Status**: Draft  
**Input**: User description: "create a new plan 002-ai-refactor and use the previous plan 001-ai-refactor-plan but this time we will use the artifacts, blueprints, plans, structures, schemas, etc in spec/001-ai-refactor-plan to speed things along. This is an implementation plan where all the planning becomes real in the codebase."

## Clarifications

### Session 2025-11-15

- Q: Should the Analyze pipeline’s entities extraction include relational graph outputs or just flat entity lists? → A: It must capture relational data links (entity-to-entity and entity-to-event relationships) because that structure is foundational for downstream agents.
- Q: What is the authoritative automation dry-run workflow and environment scope? → A: Initialize `automation/` as its own uv project for dependency tracking but keep execution pinned to the repo-root `.venv` (per existing env vars/Makefile) until the package fully splits; automation runs should use the automation project’s metadata while sharing the root environment.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Activate Blueprint Execution (Priority: P1)

The modernization program manager needs an implementation operating picture that links every artifact inside `specs/001-ai-refactor-plan/` (blueprints, backlog, and schema artifacts) to concrete repository actions so the team can move from planning to code delivery without losing governance coverage.

**Why this priority**: Without a traceable linkage between blueprint intent and real code surfaces, the refactor will stall, governance reporting will fail, and downstream teams cannot rely on the plan.

**Independent Test**: Run the implementation manifest generator (documented in `specs/002-ai-refactor-plan/scripts/manifest.md`) and verify it outputs a signed JSON manifest that enumerates each Phase 001 artifact, the owning repository path, success evidence, and the Ops/Audit entries produced when the work ships.

**Acceptance Scenarios**:

1. **Given** an artifact listed under `specs/001-ai-refactor-plan/blueprints/`, **When** the manifest sync runs, **Then** the artifact is mapped to a repository path, target branch, owner, and measurable completion evidence.
2. **Given** a blueprint entry that is already implemented, **When** stakeholders review the manifest, **Then** they see the code location, validation logs, and deployment timestamp that prove completion.

---

### User Story 2 - Materialize LangGraph & AI Runtime Changes (Priority: P2)

The lead engineer needs real LangGraph lanes, typed models, and AI runtime integrations that reflect the structures defined in spec 001 so that modernization is visible inside `automation/pipelines/` and `packages/ai/` rather than remaining conceptual.

**Why this priority**: The business value arrives only when the new lanes, type contracts, and runtime protections are merged; staying in planning mode blocks LangGraph adoption and AI runtime guardrails.

**Independent Test**: Execute `make automation.langgraph.plan` and confirm it instantiates every lane described in `specs/001-ai-refactor-plan/plan.md`, producing deterministic manifests, ops JSONL, and audit entries without importing provider SDKs directly.

**Acceptance Scenarios**:

1. **Given** a lane definition in the prior plan, **When** the automation command runs, **Then** the repository contains the lane’s typed stage models, orchestrator wiring, and QA contracts exactly as described.
2. **Given** an AI runtime call defined in the plan, **When** the new implementation executes, **Then** the call flows through `packages.ai.api` with residency tagging and structured logging per governance rules.

---

### User Story 3 - Operationalize Observability & Residency Controls (Priority: P3)

The AI operations lead must see OTLP spans, LangSmith/LangFuse evidence, ops JSONL, and residency attestations generated automatically during implementation so rollout can be audited and tuned immediately.

**Why this priority**: Telemetry and residency guardrails are constitutional requirements; without them, the modernization cannot reach production readiness.

**Independent Test**: Trigger the end-to-end automation dry run by invoking the automation package entry (`uv run --project automation make ai-module.dry-run`) which shares the repo-root `.venv` via the enforced environment variables, and verify the resulting telemetry bundle includes OTLP traces, LangSmith eval reports, LangFuse R&D-only evidence, and the residency ledger stored under `storage/audit/ai-refactor/`.

**Acceptance Scenarios**:

1. **Given** a modernization dry run, **When** telemetry exports finish, **Then** OTLP, LangSmith, LangFuse, and ops JSONL records are written with matching feature IDs and can be replayed for audits.
2. **Given** LangFuse is limited to R&D, **When** the disconnect playbook executes, **Then** the telemetry confirms LangFuse ingestion stops and the audit log records the decommission event.

---

### Edge Cases

- Blueprint artifacts missing or renamed in `specs/001-ai-refactor-plan/` must be detected, logged, and blocked until owners reconcile the gap.
- Implementation manifests must flag dependencies when blueprint tasks share files to avoid conflicting migrations.
- Automation runs must succeed even when LangFuse is offline (after R&D), falling back to native telemetry while preserving evidence.
- Entity-to-entity or entity-to-event relationships missing from the graph must block production sign-off until the gap is resolved or explicitly waived with audit evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The implementation plan MUST produce a versioned manifest that maps every artifact under `specs/001-ai-refactor-plan/` to concrete repository changes, ownership, and acceptance evidence stored in `specs/002-ai-refactor-plan/reports/manifest.jsonl`.
- **FR-002**: Each LangGraph lane, stage, and QA contract defined in `specs/001-ai-refactor-plan/plan.md` MUST be materialized as typed modules under `automation/pipelines/` with matching schema references in `schemas/automation/` and no residual placeholders.
- **FR-004**: All AI interactions introduced by this implementation MUST route through `packages.ai.api` (or an injected `AIClient`) with residency tags, ops JSONL events, and audit seals stored in `storage/ops/ai-refactor/` and `storage/audit/ai-refactor/`.
- **FR-005**: Repository reorganizations scheduled in Phase 001 (schema bundle rename, helper relocations, output consolidation) MUST be executed with forward-only migrations and tracked via tests exceeding 90% coverage on touched modules.
- **FR-006**: Observability requirements (LangSmith evaluations, temporary LangFuse hooking, OTLP spans, structlog metrics) MUST be codified as reusable configs so dry runs and CI jobs share the same instrumentation defaults.
- **FR-007**: Documentation and governance updates (TDD, LangGraph spec, quickstarts) MUST follow `docs/CONTRIBUTING-docs.md`, with doc tooling proofs captured in `specs/002-ai-refactor-plan/reports/docs.log`.
- **FR-009**: Analyze pipeline entity extraction MUST persist a relational knowledge graph that links entities to related entities, events, artifacts, and evidentiary sources, exposing that structure to downstream automation and LangGraph lanes.
- **FR-010**: The automation package MUST publish its own dependency metadata (pyproject/lock, make targets) while reusing the repo-root `.venv` via existing env vars so automation commands resolve consistently until a dedicated environment is warranted.

### Key Entities *(include if feature involves data)*

- **Implementation Blueprint Record**: Links source artifact (path, version hash) to destination repo surface, owner, target milestone, and completion evidence (tests, telemetry, audit ID).
- **LangGraph Lane Package**: Represents each modernization lane with typed stages, dependencies, QA contracts, and associated AI runtime hooks.
- **Residency & Observability Ledger**: Append-only log describing AI calls, residency tags, telemetry exports, LangSmith suites, LangFuse sessions, and decommission events tied to feature branches.
- **Entity Relationship Graph**: Stores node/edge data from Analyze pipelines, covering participants, institutions, events, evidentiary artifacts, and edge metadata (type, confidence, provenance) so downstream agents and dashboards can trace relational context.

### Schema & Interface Contracts *(Constitution P1)*

- **Internal Models**: Update/create dataclasses such as `ImplementationBlueprint`, `StageExecutionRecord`, `ResidencyLedgerEntry`, and `AutomationSnapshot` inside `packages/common` or agent-local `utils.py` to keep orchestration strongly typed.
- **External Schemas**: Publish JSON Schema definitions for the manifest, entity graph outputs, and residency ledger under `schemas/automation/ai-refactor/` with Spectral + doc_tools validation wired into CI.
- **Backward Compatibility**: Version every exported schema (`v1alpha2` for manifest, `v1beta0` for entity exports) and retain the previous `001` plan schema until downstream consumers confirm migration via the new audit logs.

### Compliance, Observability & Residency *(Constitution P2 & P5)*

- **Telemetry**: Instrument OTLP spans (`agent.ai_refactor.*`), structlog metrics, ops JSONL, LangSmith eval exports, and LangFuse (R&D only) runs triggered via the shared observability config with evidence stored under `storage/ops/ai-refactor/`.
- **Residency & Data Handling**: Classify LangSmith payloads as Restricted, LangFuse R&D traces as Confidential, and ensure storage remains in approved regions; redact prompts/responses before writing to shared artifacts and document retention in `specs/002-ai-refactor-plan/assumptions.md`.
- **AI Runtime Contract**: Enforce that automation agents call only `packages.ai.api` or the injected `AIClient`; provider SDK imports remain centralized under `packages/ai/` adapters to maintain residency/egress guards defined in spec 001.

### Security, Performance & Resilience *(Constitution P5 & P6)*

- **Threat Model**: Address blueprint tampering, telemetry leakage, and unauthorized LangFuse access via signed manifests, checksum validation of artifacts, RBAC-scoped tokens, and automated drift detection across specs.
- **Performance Budgets**: Keep LangGraph job execution under 10 minutes, lane activation under 5 minutes per lane, LangSmith eval suites under 30 minutes p95, and additional structlog/OTLP overhead <5% CPU compared to baseline.
- **Migrations & DR**: Apply forward-only migrations for directory refactors, document rollback plans in `specs/002-ai-refactor-plan/plan.md`, and ensure audit/ops logs replicate to object storage nightly.
- **Frontend/UX**: Automation dashboards and CLI outputs must stay WCAG AA compliant, localizable, and aligned with the design system references captured in spec 001.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of artifacts listed under `specs/001-ai-refactor-plan/` are linked to implemented code with passing validation evidence recorded in the manifest within two sprints.
- **SC-002**: At least 95% of modernization tasks complete with LangGraph lanes running end-to-end dry runs that emit deterministic ops JSONL, OTLP spans, and residency ledger entries on every CI execution.
- **SC-003**: Entity Relationship Graph snapshots cover ≥90% of AI module components, with provenance for each node/edge stored under `storage/ops/ai-refactor/graphs/`.
- **SC-004**: Telemetry and governance checks (LangSmith suites, LangFuse R&D capture, residency ledger) complete within 30 minutes end-to-end for each dry run, and any violation blocks deployment with documented remediation steps.
- **SC-005**: Automation package dependency metadata (pyproject/lock plus make targets) publishes alongside evidence that automation dry runs reuse the repo-root `.venv` via approved env vars.

## Assumptions

1. All artifacts under `specs/001-ai-refactor-plan/` remain the source of truth; no new blueprint sources will be introduced for this feature.
2. Developer tooling (uv, make targets, doc tools) is already installed per repo standards, so the implementation plan can rely on them without restating installation guides.
3. Feature 002 owns only the implementation of the existing plan; any new scope discovered during execution must spawn a future feature request rather than expanding this specification.
4. The automation uv project metadata will land alongside this feature, but developers continue using the enforced repo-root `.venv` so dependency isolation does not fragment the toolchain mid-refactor.
