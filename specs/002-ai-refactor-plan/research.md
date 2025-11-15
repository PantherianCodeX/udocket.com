# Research Dossier — AI Refactor Implementation Delivery

All open questions from the spec have been resolved; no NEEDS CLARIFICATION markers remain.

## Decision 1: Implementation Manifest Workflow
- **Decision**: Build a signed JSON manifest that enumerates every artifact from `specs/001-ai-refactor-plan/` and links it to repository paths, owners, validation evidence, and ops/audit outputs using the existing readiness toolkit plus deterministic hashing.
- **Rationale**: A manifest gives program managers and auditors a single source of truth that bridges blueprint artifacts with live code, satisfying FR-001 and governance traceability without adding new services.
- **Alternatives Considered**:
  - *Ad-hoc spreadsheets*: rejected because they break determinism, lack hashing/audit, and violate P3.
  - *Standalone manifest service*: rejected per scope constraint (no new modules beyond `packages/devops/readiness/`).

## Decision 2: LangGraph Lane Materialization
- **Decision**: Materialize all LangGraph lanes and StageKeys directly in `automation/pipelines/` using typed `StageMap` modules that mirror the LangGraph spec (§2.5) and TDD appendix.
- **Rationale**: Keeps implementation aligned with approved diagrams while ensuring QA contracts, cost ceilings, and AI runtime hooks become real code rather than plan artifacts.
- **Alternatives Considered**:
  - *Leaving lanes conceptual until later*: rejected because success criteria require running lanes with deterministic telemetry before promotion.
  - *Creating new orchestration modules*: rejected to honor the “no extra modules/services” directive.

## Decision 3: Observability & Residency Instrumentation
- **Decision**: Reuse the shared observability config (structlog + OTLP exporters) plus LangSmith/LangFuse integrations, logging every dry run to `storage/ops|audit/ai-refactor/` and enforcing residency tags through `packages.ai.api`.
- **Rationale**: Meets P2/P5 requirements and keeps telemetry centralized; LangFuse remains R&D-only with explicit disconnect evidence.
- **Alternatives Considered**:
  - *New telemetry service or data sink*: rejected per scope control and to avoid compliance re-review.
  - *Minimal logging only*: rejected because success criteria demand OTLP + LangSmith evidence for every run.

## Decision 4: Automation UV Project Metadata
- **Decision**: Initialize an `automation/pyproject.toml` (project metadata) to track dependencies, but keep execution bound to the repo-root `.venv` using existing env vars/Makefile until automation warrants its own isolated environment.
- **Rationale**: Provides dependency clarity for readiness dry runs while preventing fragmented environments and fits the user’s directive about forcing the shared `.venv`.
- **Alternatives Considered**:
  - *Full isolated virtualenv immediately*: rejected because it complicates tooling and conflicts with current enforcement scripts.
  - *No automation project metadata*: rejected since we need a place to declare readiness make target deps and keep uv aware of the automation package.

## Decision 5: Entity Relationship Graph Coverage
- **Decision**: Expand Analyze pipeline entity extraction to persist a relational knowledge graph (nodes + edges) that links participants, institutions, events, and evidence objects, exposing it via readiness datasets and LangGraph lanes.
- **Rationale**: Relational context is foundational for downstream timeline/relationship agents; omitting it would make the modernization effort “garbage” per stakeholder feedback.
- **Alternatives Considered**:
  - *Flat entity lists only*: rejected for lacking relational fidelity.
  - *External graph service*: rejected to keep scope constrained and stay within approved storage locations.
