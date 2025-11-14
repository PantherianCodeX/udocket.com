# Implementation Plan: AI Module Migration Completion Plan

**Branch**: `001-ai-refactor-plan` | **Date**: 2025-11-14 | **Spec**: `specs/001-ai-refactor-plan/spec.md`
**Input**: Feature specification + research artifacts under `specs/001-ai-refactor-plan/`

## Summary

Execute the seven-phase modernization initiative: rename the canonical schema bundle to `schemas/`, clean the repo root
of stray artifacts, restore `automation/pipelines/` with stage metadata/QA/cost ceilings, return `packages/common/` to a
framework-free helper library, relocate coverage/Typewiz/requirements outputs into `out/`, document + enforce the Codex
workflow (scripts/codexhome.sh + VS Code bootstrap), and capture remaining confirmations (deps/typewiz vendor notice,
dev/stub directory boundaries, Docker refs). All phases reinforce LangGraph readiness, LangSmith/LangFuse governance,
ops JSONL + audit requirements, and the `docs/CONTRIBUTING-docs.md` workflow so doc lints pass alongside code changes.
Readiness datasets, capability gaps, LangSmith/LangFuse evidence, and activation playbooks stay co-located under
`specs/001-ai-refactor-plan/data|reports`, while a new `packages/devops/readiness/` toolkit ingests those artifacts to power developer-facing services (CLI + dashboard payloads) without touching production systems yet.

## Technical Context

**Language/Version**: Python 3.12 for agents/services, TypeScript (React) for readiness dashboards.  
**Primary Dependencies**: LangGraph runtime, `packages.ai.api` (AI runtime), LangSmith SDK, LangFuse client, structlog,
OpenTelemetry, pytest/Hypothesis, Ruff, Pyright, Spectral/doc_tools, Typewiz, uv.  
**Storage**: Feature datasets live under `specs/001-ai-refactor-plan/data|reports` and are ingested by `packages/devops/readiness/`, which can also sync normalized tables into the developer Postgres database for dashboard previews (production Postgres/ops JSONL remain untouched until implementation). Object storage still houses artifacts, docs live in `docs/`, and dev tooling continues referencing CONTRIBUTING.
docs in `docs/` governed by CONTRIBUTING guide.  
**Testing**: `make typing.ai`, `make all.test`, property tests for deterministic surfaces, prompt eval harnesses via
LangSmith, doc tooling (`doc_tools.manage_docs`, `doc_tools.check.links`), Spectral schema lint, Typewiz ratchet.  
**Target Platform**: Linux containers + developer hosts managed by uv; CI/CD pipelines run in containerized GitHub/GCP
runners.  
**Project Type**: Monorepo (automation agents + Django services + tooling).  
**Performance Goals**: Readiness inventory recompute <10 minutes; LangSmith evaluations complete <30 minutes p95;
LangFuse sampling overhead <5%; doc tooling, Typewiz, and coverage jobs stay within existing CI budgets.  
**Constraints**: Strict type-first development (no new `Any`), AI runtime isolation, forward-only migrations, doc edits must
follow `docs/CONTRIBUTING-docs.md` formatting/structure to satisfy aggressive lints.  
**Scale/Scope**: Repo-wide refactor touching automation/, packages/, docs/, schemas/, tooling/, storage/, ops/, scripts/.

## Constitution Check

- [x] **P1 – Type-First & Schema-Driven Guarantees**: Schema bundle rename keeps a single canonical source; typed
  models (MigrationStageReadiness, CapabilityGap, etc.) already defined; Spectral/doc tooling updates enforce schemas.
- [x] **P2 – AI Runtime Isolation**: All LangSmith/LangFuse usage continues through `packages.ai.api`/`AIClient`; no
  direct provider SDK imports are added.
- [x] **P3 – Deterministic Pipelines & QA**: Reintroducing `automation/pipelines/` re-aligns StagePlan metadata with the
  LangGraph TDD appendix and ensures manifests/ops JSONL remain deterministic.
- [x] **P4 – Testing & Coverage Discipline**: Plan reiterates ≥90 % coverage, property tests, Typewiz ratchet, and
  LangSmith prompt eval requirements before promotion.
- [x] **P5 – Observability, Compliance & DR**: OTLP spans, ops JSONL, LangFuse enable/disable evidence, residency notes,
  and DR documentation explicitly tracked in spec + quickstart.
- [x] **P6 – Secure, Performant SaaS Delivery**: Threat model, performance budgets, forward-only repo cleanup, and
  accessibility/localization obligations are covered; no DRY violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-refactor-plan/
├── plan.md          # /speckit.plan output (this file)
├── research.md      # Phase 0 decisions + rationale (complete)
├── data-model.md    # Phase 1 entity definitions (complete)
├── quickstart.md    # Phase 1 environment + workflow guide (complete)
├── contracts/
│   └── openapi.yaml # Phase 1 API/schema exports for readiness + tooling endpoints
└── spec.md          # Feature specification kept in sync with phases
```

All doc edits in `docs/` (e.g., `docs/overview/tdd/appendices/repository_trees.md`, `docs/automation/langgraph-agents.md`,
README changes) MUST follow `docs/CONTRIBUTING-docs.md`, including running `doc_tools.manage_docs`,
`doc_tools.check.links`, and the MkDocs build before PR submission.

```text
automation/
├── pipelines/                # New home for stage metadata, QA, cost ceilings
├── agents/
└── langgraph/

docs/
├── CONTRIBUTING-docs.md      # Mandatory reference for every docs change
├── overview/
│   └── tdd/appendices/repository_trees.md
└── automation/langgraph-agents.md

schemas/                      # Renamed from spec/
├── automation/
├── platform/
├── guardian/
├── ops/
└── shared/

packages/
├── common/                   # Refactored to pure helpers (paths/, json/, prompts/)
├── core/                     # Receives framework-aware helpers relocated from common
└── devops/                   # Advanced tooling (e.g., readiness service sourcing specs/<feature>/ data)

out/
├── test-reports/coverage.xml
├── typewiz/
└── requirements/

tooling/
├── fixtures/sqlalchemy/      # Receives former db/ helpers
├── doc_tools/
└── scripts/

tests/
├── agents/
├── automation/
└── regression/
```

**Structure Decision**: Maintain the existing monorepo layout while enforcing the canonical root set (apps/, automation/,
packages/, services/, config/, infra/, ops/, tests/, tooling/, docs/, schemas/, specs/, out/, storage/, scripts/). All doc
changes must reference `docs/CONTRIBUTING-docs.md` and run the doc lint targets before submission.

## Complexity Tracking

_No constitutional violations requiring justification._
