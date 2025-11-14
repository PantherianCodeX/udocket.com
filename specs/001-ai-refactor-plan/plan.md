# Implementation Plan: AI Module Migration Completion Plan

**Branch**: `001-ai-refactor-plan` | **Date**: 2025-11-14 | **Spec**: `/home/user/Code/udocket/specs/001-ai-refactor-plan/spec.md`
**Input**: Feature specification + directives recorded in `specs/001-ai-refactor-plan/spec.md`

## Summary

Create the authoritative modernization blueprint for the AI module: capture the full readiness inventory, codify the modernization backlog against LangGraph stages, and land LangSmith (evaluations) plus temporary LangFuse (observability) enablement so the pipeline can dial up with governed telemetry. Execution leans on Python 3.12 services orchestrated through LangGraph, uv-managed environments, and ops JSONL/audit artifacts defined in the TDD. Local workflows must operate outside the deprecated dev container, so the plan documents uv sync flows, pytest + typing targets, and `.env`-backed key storage while we work toward the future secrets service described in the TDD.

## Technical Context

**Language/Version**: Python 3.12 for agents/services, TypeScript (React) for readiness dashboards.  
**Primary Dependencies**: LangGraph runtime, LangSmith SDK (`langsmith`), LangFuse client, structlog, OpenTelemetry, Postgres drivers (`asyncpg`/`psycopg`), uv-managed tooling, pytest/Hypothesis, Typewiz, Ruff, Pyright.  
**Storage**: Postgres (`services/readiness`), append-only ops JSONL/audit JSONL in `storage/`, object storage for artifacts, `.env` for local secrets until secrets service lands.  
**Testing**: `make typing.ai`, `make all.test`, targeted `pytest` modules (`services/readiness`, `packages/ai`), Hypothesis property suites for UUIDs/manifests, LangSmith eval harness (prompt regressions), doc tooling (`make docs.check.*`).  
**Target Platform**: Linux containers + GitHub Actions runners; local developers run on macOS/Linux without a dev container.  
**Project Type**: Multi-service backend (Django + Celery) plus LangGraph agents, automation scripts, and supporting docs/spec artifacts.  
**Performance Goals**: Readiness recompute <10 minutes; observability exports <2 minutes; LangSmith eval turnaround <30 minutes p95; LangFuse sampling overhead <5% runtime; readiness dashboards P95 render <250 ms; LangFuse disablement SLA ≤15 minutes.  
**Constraints**: All LLM traffic routed through `packages.ai.api`; LangFuse limited to dev/staging with capped sampling (≤25%) and automatic teardown; residency metadata required before promotion; keys managed via checked-in `.env` template until centralized secrets ship; no dev-container-specific tooling; uv/pyproject is source of truth for dependencies.  
**Scale/Scope**: Entire AI module estate (every LangGraph stage, readiness component, and LangSmith evaluation workspace) plus cross-cutting telemetry and governance touchpoints.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **P1 – Type-First & Schema-Driven Guarantees**: Data models (MigrationStageReadiness, CapabilityGap, ObservabilityControl, LLMToolingDecision, ToolingWorkspace, EvaluationEvidence, ObservabilitySession, VendorUsageBudget) will be maintained as typed dataclasses/StrEnums with JSON Schema exports before logic ships.
- [x] **P2 – AI Runtime Isolation**: Plan enforces exclusive use of `packages.ai.api`/`AIClient` for provider access; LangSmith/LangFuse integrations plug into the runtime and inherit residency/egress guards defined in the TDD.
- [x] **P3 – Deterministic Pipelines & QA**: StageKeys sourced from `packages/common/agents/stage_map.py`; readiness + backlog artifacts emit ops JSONL/audit hashes per run; LangSmith eval exports versioned via EvaluationEvidence schema.
- [x] **P4 – Testing & Coverage Discipline**: ≥90 % coverage enforced through `make all.test`, targeted pytest modules, Hypothesis property tests for manifests/UUIDs, and LangSmith prompt evals gated via automation scripts; typing gates (`make typing.ai`, pyright/mypy/ruff) codified.
- [x] **P5 – Observability, Compliance & DR**: OTLP spans + structlog instrumentation defined per stage, LangFuse enable/disable evidence captured in `ops/runbooks/langfuse-rd.md`, ops JSONL/audit JSONL appended for every job, DR runbooks updated with LangFuse teardown/residency notes.
- [x] **P6 – Secure, Performant SaaS Delivery**: Threat model covers prompt injection, dashboard access, LangSmith/LangFuse key leakage; load budgets + kill-switch automation defined; `.env` handling documented with rotation cadence until secrets service exists; no backward-compat shims added.

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-refactor-plan/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
└── tasks.md   # generated during /speckit.tasks later
```

### Source Code (repository root)

```text
apps/platform/                # Django + Celery entrypoints and tests
automation/pipelines/         # LangSmith + LangFuse automation scripts
packages/ai/                  # AI runtime adapters, LangGraph orchestration
packages/common/              # Shared enums, schemas, stage maps
services/readiness/           # Inventory + backlog services
ops/runbooks/                 # Telemetry + governance runbooks (LangFuse R&D, etc.)
docs/overview,tdd.md          # Platform blueprint + residency/secrets expectations
tests/langgraph/, tests/core/ # Property + integration tests (readiness, telemetry)
```

**Structure Decision**: Multi-service backend/automation repo—work spans documentation (`specs/...`), shared packages (`packages/ai`, `packages/common`), service code (`services/readiness`, `apps/platform`), automation scripts, and ops runbooks. No separate frontend/mobile projects are added.

## Complexity Tracking

*No violations to record.*
