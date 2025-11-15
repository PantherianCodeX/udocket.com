<!--
Sync Impact Report
- Version: 1.2.0 → 1.3.0
- Modified Principles: P2, P5, P6 updated for Rapid Development Suspension (RDS-1)
- Added Sections: Rapid Development Suspension clause, Workflow guidance for suspension tracking
- Removed Sections: none
- Templates: .specify/templates/plan-template.md ✅; .specify/templates/spec-template.md ✅; .specify/templates/tasks-template.md ✅; Commands templates N/A
- Follow-up TODOs: Add RATIFICATION_HISTORY entry citing RDS-1 approval evidence
-->

# uDocket Constitution

## Core Principles

### Type-First & Schema-Driven Guarantees (P1)
Every module must define dataclasses, `TypedDict`/`Protocol`, `StrEnum`, and Pydantic `BaseModel` wrappers before
logic. No new `typing.Any`, unchecked dicts, or stringly typed flags may enter the codebase; legacy `Any` is removed
when touched. Provider payloads require typed shims in `packages/common` before usage. Internal models standardize on
Pydantic for validation and serialization; external interfaces publish JSON Schema generated from those models (or
native JSON Schema with equal coverage when conversion blockers arise). Schemas are versioned with code to keep the
system verifiable and DRY.

### AI Runtime Isolation (P2)
All LLM or embedding calls route through the hardened AI runtime (`packages.ai.api`, Portkey integration when
enabled). Automation code MUST NOT import provider SDKs, bypass residency/egress checks, or implement bespoke retry
loops. The runtime enforces redaction, token budgets, deterministic prompt templates, and audit logging so we can
prove compliance for PII/SPI/PHI workloads. During Rapid Development Suspension (RDS-1), residency/egress guardrails
may be deferred for the scoped initiative if interim safeguards are documented and full enforcement is scheduled
before the stable-product declaration.

### Deterministic Pipelines & QA (P3)
Stage catalogs (`StageKey`, `StagePlan`) govern LangGraph flows. Nodes respect the capability-first contract
(GENERATE, EXTRACT, EVAL, EMBED, ATOMS) and persist deterministic manifests, ops JSONL, and audit hashes per job.
Revision loops, QA joins, and finalize stages remain pure and replayable via fixtures, ensuring parity with the TDD.

### Testing & Coverage Discipline (P4)
Touched modules MUST sustain ≥90 % coverage with pytest, Hypothesis property tests for deterministic surfaces, and
fixture-driven LangGraph acceptance suites. Prompt evaluations (promptfoo, LangSmith, or equivalent) are mandatory for
prompt or model changes. CI gates block merges unless plan/spec/tasks artifacts honor the Constitution Check and all
typing targets (mypy, pyright, Typewiz ratchet) succeed.

### Observability, Compliance & Disaster Readiness (P5)
Every stage emits structured logs via structlog, OpenTelemetry spans/metrics via OTLP exporters, and append-only ops
JSONL. SLO dashboards track latency, retries, token cost, QA outcomes, and declared RTO/RPO targets. Sentry may capture
exceptions only with scrubbed payloads. Any new datastore or SaaS (Langfuse, Graphiti, Memgraph) requires documented
residency controls, DR playbooks, and approved data-flow reviews before ingestion. When RDS-1 applies, OTLP/span
instrumentation and residency attestations may trail implementation if interim logging exists and the catch-up plan is
documented with owners/dates.

### Secure, Performant SaaS Delivery (P6)
Full-stack work (backend, frontend, data, infra) must follow threat models (STRIDE/abuse cases), static + dynamic
security scans, and least-privilege secrets management. Features declare performance budgets (p95 latency, throughput,
cost ceilings) per StageKey and prove them with load or chaos tests. We are in rapid dev mode: no backwards-compatible
shims or reversible migrations are required, but every forward-only migration must document demolition/cleanup steps
before GA. Frontend/UX contributions respect the design system, WCAG AA accessibility, and localization hooks. DRY is
enforced via shared libraries and design tokens—duplicated logic requires documented justification. Incident/chaos
drills with audited runbooks precede GA. RDS-1 allows performance-budget tests to trail implementation so long as the
target metrics and remediation plan are tracked and completed prior to the stable-product milestone.

### Rapid Development Suspension (RDS-1)
RDS-1 is a temporary carve-out for initiatives that explicitly set `rapid_dev_mode=true` in their spec and plan. While
the suspension is active:

- Residency/egress guardrails, OTLP instrumentation, and p95 performance proofs referenced in P2, P5, and P6 may be
  deferred to a later milestone.
- Teams must document interim safety measures plus backlog tasks with owners/dates to restore the deferred controls.
- The suspension ends once the initiative declares a "stable product" in its success criteria; deferred controls must
  be implemented before further promotion.
- Architecture or Security may revoke RDS-1 early if risk posture shifts.

## Execution Constraints & Tooling

- Capability catalog ownership lives in `packages/common/agents/stage_map.py`; diagrams/specs must match that file
  before implementation begins.
- AI client integrations (Portkey, fake providers, shadow deployments) sit behind the `AIClient` interface with
  deterministic prompt IDs, retention windows, and audit hashes.
- Fixture libraries (transcripts, Atoms, manifests, QA directives) reside in `tests/fixtures/agents/`. Pipelines without
  fixtures cannot ship.
- Prompt evaluation tooling stays source-controlled; results enter CI artifacts and monitoring to validate regressions
  before rollout.
- Graph stores or analytics services (Graphiti, Memgraph, vector DBs) are pluggable repositories. Production workloads
  remain on approved storage until compliance signs off on new engines.
- Schema governance: Internal representations use Pydantic models that emit canonical JSON Schemas for external
  consumers. REST/gRPC/async APIs MUST publish those schemas, version them, and validate payloads against them.
  Divergence between internal/external schemas demands Architecture approval.

## Workflow & Quality Gates

- Implementation plans MUST document Constitution Check outcomes referencing Principles P1–P6. Any violation requires
  justification in the plan’s Complexity Tracking table.
- Specs capture user journeys plus telemetry/compliance edge cases; requirements call out QA artifacts, ops JSONL
  expectations, residency rules, performance budgets, accessibility, and security constraints.
- Task lists organize work by user story, explicitly include fixture creation, OTLP instrumentation, forward-only schema
  migrations, performance tests, security reviews, and compliance verification tasks before feature work begins. RDS-1
  initiatives may defer these items only if the deferral rationale and reinstatement plan are recorded in spec/plan/tasks.
- Doc-tooling (`make docs-diagrams`, `doc_tools.check.links`) and typing targets (`make typing.ai`, Typewiz dashboards)
  run before PR review. Shadow→production promotion requires recorded replay runs, DR playbooks, and monitoring sign-off.

## Governance

1. **Authority**: This constitution supersedes conflicting guidance. The LangGraph spec and TDD remain authoritative for
   capability behavior; deviations require dual approval from Applied AI Engineering and Platform Architecture.
2. **Amendments**: Changes demand an RFC + implementation plan, CI evidence (tests, prompt evals, telemetry, load/security
   proofs), and semantic version bumps. Ratified amendments log their rationale in the PR description and ops runbook.
3. **Versioning**: Semantic rules apply—MAJOR when principles/governance change incompatibly; MINOR for new sections or
   expanded scope; PATCH for clarifications. Version metadata updates alongside the Sync Impact Report.
4. **Compliance Reviews**: Quarterly audits confirm residency, telemetry, ops JSONL integrity, security posture, and DR
   readiness. TODO placeholders must resolve before release or track owners/dates plus mitigation steps.

**Version**: 1.3.0 | **Ratified**: 2025-11-15 | **Last Amended**: 2025-11-15
