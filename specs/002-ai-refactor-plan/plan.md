# Implementation Plan: AI Refactor Implementation Delivery

**Branch**: `002-ai-refactor-plan` | **Date**: 2025-11-15 | **Spec**: `specs/002-ai-refactor-plan/spec.md`
**Input**: Feature specification from `/specs/002-ai-refactor-plan/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Execute Feature 001 by finishing the AI module refactor: restructure the repository layout, re-baseline `packages/common/` as a lightweight typed library, implement the LangGraph lanes/stages defined in the blueprint, publish automation dependency metadata, and wire telemetry/AI runtime enforcement with LangSmith + LangFuse evidence. The delivery also lands the Entity Relationship Graph pipeline so downstream automation has relational context without relying on readiness tooling. All changes stay within the existing automation stack—no new services or readiness dashboards—focusing purely on structure refactors plus AI module execution.

## Technical Context

**Language/Version**: Python 3.12 (monorepo automation standard).  
**Primary Dependencies**: LangGraph runtime, `packages.ai.api` + injected `AIClient`, LangSmith SDK, LangFuse client (R&D-only), structlog, OpenTelemetry, pytest/Hypothesis, uv tooling, Typewiz, Ruff/Pyright, repo-standard make targets.  
**Storage**: Append-only ops JSONL + audit JSONL under `storage/ops|audit/ai-refactor/`; entity-graph artifacts and manifests live under `specs/002-ai-refactor-plan/reports/` plus `storage/ops/ai-refactor/graphs/`; schemas in `schemas/automation/`; Postgres remains for existing dashboards only.  
**Testing**: `make typing.ai`, `make all.test`, Hypothesis suites for manifests/entity graphs, LangSmith eval runs, doc tooling checks, LangFuse-offline regression harness, and ops/audit verification scripts.  
**Target Platform**: Linux developer hosts/CI containers orchestrated by uv + make; no additional services beyond planned scope.  
**Project Type**: Monorepo automation agents plus supporting tooling; scope is structure cleanup + AI module refactor with telemetry layering.  
**Performance Goals**: Track only AI-lane execution health (deterministic outputs + instrumentation); no extra readiness runtime budgets.  
**Constraints**: Type-first contracts, zero `Any`, forward-only cleanup, LangSmith/LangFuse instrumentation on every lane run, residency enforcement via `packages.ai.api`, and maintaining ops/audit append-only logs.  
**Scale/Scope**: Apply blueprint coverage to every AI stage + entity graph; no readiness toolkit work, no new modules/services outside automation/ai packages.

## Constitution Check

- [x] **P1 – Type-First & Schema-Driven Guarantees**: Dataclasses/StrEnums for manifests, lanes, entity nodes/edges, and telemetry ledgers must land before logic; schemas ship under `schemas/automation/ai-refactor/` with Spectral + doc tooling gates.  
- [x] **P2 – AI Runtime Isolation**: All LangGraph and pipeline calls route through `packages.ai.api` / injected `AIClient`; LangSmith/LangFuse integrations rely on that runtime isolation.  
- [x] **P3 – Deterministic Pipelines & QA**: StageKeys follow LangGraph spec §2.5; `automation/pipelines/` StageMap definitions carry QA contracts and ops/audit hooks with no placeholders.  
- [x] **P4 – Testing & Coverage Discipline**: ≥90% coverage on touched modules, Hypothesis/property tests for manifests/entity graphs, LangSmith eval requirements, doc tooling, and CI targets (`make typing.ai`, `make all.test`).  
- [x] **P5 – Observability, Compliance & DR**: Structlog + OTLP spans, LangSmith eval IDs, LangFuse toggles, residency ledgers, and ops/audit trails capture every run; DR plan relies on nightly object storage sync.  
- [x] **P6 – Secure, Performant SaaS Delivery**: Threat model covers blueprint tampering + telemetry leakage, forward-only migrations document rollback, and LangFuse R&D hookups stay scoped with disconnect playbooks.

## Project Structure

```text
automation/
├── pipelines/                 # Stage metadata, StageMap, QA/cost ceilings restored per spec 001
├── langgraph/                 # Runtime helpers reused by pipelines
├── entity_graph/              # Entity graph builders, storage helpers, CLI hooks
└── task_modules/              # Task glue (no new services)

packages/
├── ai/                        # AI runtime + provider adapters (no direct SDK usage elsewhere)
├── common/                    # Shared typed helpers/value objects only (framework-agnostic)
├── core/                      # Domain-specific helpers (Django/LangGraph-aware) extracted from common
└── telemetry/                 # LangSmith/LangFuse wiring + config (if not already present)

schemas/
└── automation/ai-refactor/    # JSON Schemas for manifest, entity graph, telemetry ledger

storage/
├── ops/ai-refactor/           # ops JSONL outputs per lane + entity graph runs
└── audit/ai-refactor/         # audit JSONL + residency ledger entries

specs/
├── 001-ai-refactor-plan/      # Source artifacts/blueprints referenced by this feature
└── 002-ai-refactor-plan/      # Current implementation plan + research/data/contracts/quickstart

tests/
├── automation/                # Stage/lane acceptance + property tests
├── agents/                    # LangGraph agent suites referencing StageKeys
└── regression/                # End-to-end LangGraph + telemetry verification (LangSmith/LangFuse, entity graph)
```

**Structure Decision**: All changes stay within automation packages; no readiness toolkit refresh. Cross-cutting helpers either remain typed/pure in `packages/common/` or move into the domain-specific module that consumes them (e.g., `automation/entity_graph/`, `packages/telemetry/`).

### Root Baseline Map (Scope Guardrail)

Cleanup work MUST converge the repo root to the canonical set declared here. Anything outside this list is considered stray and must be relocated (e.g., into `out/`) or removed once its contents land in the sanctioned directories.

```text
# Canonical files (retain)
AGENTS.md
CHANGELOG.md
CONTRIBUTING.md
Makefile
README.md
bake.hcl
manage.py
mypy.ini
pyproject.toml
pyrightconfig.docs-scripts.json
pyrightconfig.json
pytest.ini
uv.lock
docker-compose.yml
docker-compose.dev.yml
docker-compose.prod.yml
docker-compose.cache.yml

# Canonical directories (retain)
apps/
automation/
config/
docs/
infra/
ops/
out/
packages/
schemas/            # renamed from spec/ per spec 001
scripts/
services/
specs/
storage/
tests/
tooling/

# Other approved roots
spec/                # temporary until schema rename completes
typings/             # shared stub definitions
.specify/            # tooling metadata (keep)
.codex/              # shared prompts (keep)
.github/             # CI definitions
.devcontainer/       # devcontainer configs
.docker/             # docker build context
deps/typewiz/        # vendor exception per spec 001 until upstream release

# To purge or relocate during cleanup (git-tracked copies only)
coverage.xml, requirements/ (legacy exports), db/, stray env files, and any other artifacts not listed above—move outputs under `out/`, move fixtures under `tooling/fixtures/`, and delete obsolete scripts after relocation evidence is captured. Developer-local directories such as `.venv/`, `.cache/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `.typewiz_cache/` remain ignored on disk but must not re-enter the tracked root tree.

**Packages/common guardrail**: `packages/common/` stays framework-independent. Any helper touching Django, LangGraph runtimes, or telemetry moves into the consuming domain module (automation pipelines, telemetry package, etc.) before logic changes land.
```

Jobs finish only when the top-level tree matches the canonical sections above (plus the deliberately temporary `spec/` entry until the schema rename lands). Any new top-level item requires a separate feature request and architectural approval so we avoid unintentional additions or removals.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Success Criteria *(mandatory)*

- **SC-001**: Repo structure cleanup completes—coverage/typewiz outputs live under `out/`, `db/` helpers relocate into domain modules, `requirements/` exports are removed, and packages/common passes the purity checker with CI enforcement.  
- **SC-002**: LangGraph lanes for the AI module execute end-to-end with deterministic manifest outputs, ops/audit entries, and staging QA contracts, all routed through `packages.ai.api`.  
- **SC-003**: Entity Relationship Graph runs emit typed node/edge artifacts plus provenance stored under `storage/ops/ai-refactor/graphs/`, and pipelines fail when mandatory relationships go missing.  
- **SC-004**: LangSmith eval suites and LangFuse telemetry capture every dry run, including an offline toggle test, with evidence stored under `specs/002-ai-refactor-plan/reports/` and references in ops/audit logs.
- **SC-005**: Automation package dependency metadata (pyproject/lock plus make targets) publishes alongside evidence that automation dry runs reuse the repo-root `.venv` via approved env vars.

## Assumptions

1. All artifacts under `specs/001-ai-refactor-plan/` remain the blueprint; no readiness toolkit work re-enters scope.  
2. LangSmith and LangFuse credentials/processes already exist from Feature 001 planning; this feature implements them without renegotiating access.  
3. No new services are provisioned; all telemetry flows through existing runtimes and logging infrastructure.  
4. Repo cleanup tasks can move or delete artifacts as long as evidence is captured under `specs/002-ai-refactor-plan/reports/` first.
