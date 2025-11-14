# Feature Specification: AI Module Migration Completion Plan

**Feature Branch**: `001-ai-refactor-plan`  
**Created**: 2025-11-14  
**Status**: Draft  
**Input**: User description: "Plan the completion of the re-engineering and refactor of the AI module. Parts have been migrated, determine where we are and chart a plan forward to full migration, modern LLM tooling and observability installed and configured, ready to dial in the pipeline." Additional directive: "we need to install depends for llm tooling - we want to add LangSmith for prototyping and evals and LangFuse for observability. LangFuse will only be connected for initial R&D of pipeline only and will not be a permanent feature."

## Clarifications

### Session 2025-11-14

- Q: How should we handle the existing `db/` test helpers during the Phase 2 root cleanup? → A: Relocate them into `tooling/fixtures/sqlalchemy/` and adjust import paths.
- Q: Should the seven refactor phases also appear as user stories? → A: Add a dedicated governance owner story covering all phases, keeping the detailed phase list under Functional Requirements.
- Q: Do documentation changes under `docs/` require following `docs/CONTRIBUTING-docs.md` and running doc lints? → A: Yes, every doc edit must follow that workflow so doc-specific linters pass.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assess Current Migration State (Priority: P1)

The AI program manager needs a single source of truth showing exactly which AI module components, environments, and controls have already migrated to the modern architecture so they can explain status and unblock stakeholders.

**Why this priority**: Without a factual baseline, the remaining refactor cannot be sequenced, funding cannot be justified, and dependent teams remain uncertain.

**Independent Test**: Run `python -m packages.devops.readiness.cli refresh --feature 001-ai-refactor-plan --lane modernization` so the toolkit ingests `specs/001-ai-refactor-plan/data/readiness/raw/`, emits normalized datasets to `specs/001-ai-refactor-plan/data/readiness/`, and writes ops/audit outputs into `specs/001-ai-refactor-plan/reports/readiness_ops.jsonl`. Confirm the resulting readiness dashboard JSON covers every surface with explicit state, owner, and evidence links.

**Acceptance Scenarios**:

1. **Given** existing partial migrations, **When** the manager loads the readiness inventory, **Then** all AI module components show source/target state, owning team, last validation date, and blocking issues.
2. **Given** a component with missing data, **When** the manager flags it, **Then** the system captures the gap with owner assignment and includes it in the migration risk log.

---

### User Story 2 - Plan Remaining Modernization (Priority: P2)

The staff engineer responsible for the AI module needs a sequenced plan that maps remaining refactor tasks to LangGraph pipeline stages, identifies dependencies, and provides estimates so the work can be scheduled.

**Why this priority**: A credible plan is necessary to commit to delivery dates and ensure modernization follows platform standards (type-first contracts, AI runtime layering, residency guards).

**Independent Test**: Review the migration backlog artifact and verify every remaining component has a target design summary, dependency list, effort sizing, and acceptance gates tied to LangGraph stages.

**Acceptance Scenarios**:

1. **Given** a partially migrated capability, **When** the engineer opens its task stack, **Then** they see target architecture notes, integration touchpoints, and required verification steps.
2. **Given** two tasks with ordering constraints, **When** the plan is generated, **Then** the dependencies are reflected in the roadmap with critical path flags.

---

### User Story 3 - Enable LLM Tooling & Observability (Priority: P3)

The AI operations lead needs to ensure modern LLM tooling—including LangSmith for prototyping/evaluations and a temporary LangFuse connection for R&D observability—is fully specified before pipeline dial-up, alongside baseline OTLP metrics, ops JSONL, and audit logs.

**Why this priority**: Dialing up the pipeline without governed evaluation tooling or scoped observability violates platform standards, prevents rapid tuning, and risks leaving the temporary LangFuse hookup in place longer than allowed.

**Independent Test**: Execute the tooling and observability checklist and confirm LangSmith workspaces, LangFuse dashboards, and native telemetry each meet governance rules, route calls through the approved AI runtime, and include activation/deactivation runbooks.

**Acceptance Scenarios**:

1. **Given** LangSmith access is provisioned, **When** the lead triggers a prototype evaluation from a LangGraph lane, **Then** the results sync to readiness artifacts with residency attestations and do not bypass AI runtime enforcement.
2. **Given** LangFuse is limited to R&D, **When** the lead executes the disconnect playbook, **Then** ingestion stops within the allowed window, credentials are revoked, and the plan records the teardown evidence for audits.


### User Story 4 - Govern Repository & Schema Refactors (Priority: P3)

The platform/repo governance lead needs a cohesive initiative that owns all seven refactor phases (schema bundle rename, root cleanup, automation tree restoration, `packages/common/` purity work, tooling output relayout, Codex workflow documentation, and the remaining confirmations) so structural standards are enforced consistently.

**Why this priority**: Treating the phases as disjoint tasks risks uneven enforcement and makes it harder to prove compliance with platform directives. A persona-focused journey ensures governance can measure completion and unblock dependencies.

**Independent Test**: Inspect the governance storyboard/checklist and confirm each phase lists owners, acceptance gates, CI/doc updates, and rollback checkpoints before sign-off.

**Acceptance Scenarios**:

1. **Given** the schema bundle rename is underway, **When** the governance lead executes their checklist, **Then** all tooling/tests reference `schemas/` and the repo tree appendix documents the directory purpose.
2. **Given** the root cleanup and automation tree restoration phases are scheduled, **When** the lead audits the repo root, **Then** only sanctioned directories remain and `automation/pipelines/` contains the stage metadata aligned to the TDD appendix.
3. **Given** `packages/common/` purity and tooling output relocations need enforcement, **When** the lead completes the phase, **Then** framework-aware helpers live outside `packages/common/`, Typewiz/coverage/requirements artifacts land under `out/`, AGENTS.md + TDD + README reflect the Codex workflow and `deps/typewiz/` exception, and Docker references to `spec/` are validated.

### Edge Cases

- Discovery shows a component without an identified owner; the plan must route it to governance for reassignment before migration continues.
- Legacy AI module paths carry data lacking residency metadata; specification must block promotion until residency fields are populated and verified.
- Telemetry backfills reveal missing historical data; plan must include compensating controls (synthetic traces or manual verification) before allowing cutover.
- LangSmith evaluation datasets inadvertently contain production PII; the plan must define redaction workflows and halt usage until data is purged.
- The "temporary" LangFuse integration remains connected past the R&D phase; governance must require automated kill switches and certification before any extension.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Provide a canonical AI module inventory that lists every service, workflow, model call, and storage touchpoint with current vs. target architecture mapping, owner, and last validation date.
- **FR-002**: Generate a migration readiness matrix that scores each component across architecture, data residency, testing, observability, and AI runtime compliance, highlighting blockers with mitigation owners.
- **FR-003**: Produce a prioritized backlog of remaining refactor tasks with effort ranges, dependencies, and LangGraph stage alignment so program planning can schedule the work. Critical path is defined as the longest dependency chain impacting a P1 readiness stage or any task whose slip would delay the LangGraph dial-up date; annotate these tasks with `critical_path=true` and reference blocking task IDs directly in the `dependencies` array so reporting tools can surface them consistently.
- **FR-004**: Define the modern LLM tooling toolkit—with LangSmith as the sanctioned prototyping/evaluation surface—covering dependency installs, workspace governance, prompt dataset policies, decision criteria, rollout sequencing, and integration checkpoints. Deliverables include workspace metadata, provisioning scripts, evaluation export schema, and ingestion blueprints (plus Quickstart updates) explaining how LangSmith flows through the AI runtime.
- **FR-005**: Specify observability requirements for every pipeline stage, including LangFuse-backed R&D dashboards, native metrics, traces, ops JSONL artifacts, and audit events needed to support runbooks and tuning sessions. Deliverables include the telemetry/evidence matrix, LangGraph spec §8.3 updates, required dashboard/alert definitions, and evidence files stored under `specs/001-ai-refactor-plan/reports/`.
- **FR-006**: Document the AI runtime enforcement plan ensuring all providers are accessed through `packages.ai.api` (or injected `AIClient`), with residency/egress guardrails, waiver handling, and fail-closed behaviors.
- **FR-007**: Outline the activation plan for dialing up the modernized pipeline in non-production environments, covering deterministic dry-runs, sampling strategies (even if single-lane), rollback triggers, and the solo developer’s sign-off evidence before sharing with stakeholders.
- **FR-009**: Establish temporary LangFuse activation/teardown controls (environment allow-list, sampling rules, kill-switch validation, post-R&D data purge) and the evidence requirements proving it is not a permanent feature. Deliverables include the enable/disable SOP, evidence logs, LangGraph spec §8.3 references, and documented teardown runbooks demonstrating credentials/data removal once the R&D window ends.
- **FR-010**: Deliver the schema-bundle refactor by renaming `spec/` to `schemas/`, organizing the canonical bundle by domain (automation/, platform/, guardian/, ops/, shared/, etc.), updating doc tooling, Spectral configs, tests, and scripts to the new path, documenting the directory in the repo tree appendix, and reiterating that generated models continue living in the relevant packages.
- **FR-011**: Execute the top-level root cleanup by deleting empty artifacts (e.g., `reading`, `udocket-starship.sh`), relocating coverage and Typewiz outputs into `out/` (e.g., `out/test-reports/coverage.xml`, `out/typewiz/...`), reconfiguring `scripts/dev/export_requirements.py` to emit into `out/requirements/` before removing the tracked `requirements/` directory, moving `db/` test helpers under `tooling/fixtures/sqlalchemy/`, and validating the root contains only the sanctioned directory set.
- **FR-012**: Recreate the automation tree expectations by introducing `automation/pipelines/` with stage metadata, QA requirements, and cost ceilings so the LangGraph directory structure matches the TDD appendix and the automation spec.
- **FR-013**: Restore `packages/common/` purity by relocating framework-aware helpers (`packages/common/django/`, jobs, operations, etc.) into `packages/core/` or the owning apps, grouping foundational helpers into explicit subpackages (paths/, config/, json/, prompts/, etc.), shipping temporary import shims, and documenting the “framework-free” rule within AGENTS.md.
- **FR-014**: Standardize tooling outputs and docs by configuring Typewiz via `typewiz.toml` to write manifests/dashboards into `out/typewiz/`, ensuring coverage configuration outputs to `out/test-reports/coverage.xml`, updating README + doc references so requirements exports land in `out/requirements/`, and reflecting the schemas + automation/pipelines directories plus Codex workflow expectations in `docs/overview/tdd/appendices/repository_trees.md`.
- **FR-015**: Canonicalize the Codex workflow by documenting `scripts/codexhome.sh .` usage, highlighting that `.vscode` auto-sources `.codex/.codexhome`, and explaining that prompts/configs stay in git while secrets/logs remain ignored, all within AGENTS.md’s appendix.
- **FR-016**: Capture the remaining confirmations: annotate `deps/typewiz/` in the README as a temporary vendor exception, reaffirm that only `tooling/` and `typings/` house dev/stub artifacts, and audit Docker stages for hard-coded `spec/` references following the rename.
- **FR-017**: Enforce the documentation workflow by requiring contributors to consult `docs/CONTRIBUTING-docs.md`, follow its formatting/structure rules for every `docs/` change, run the doc lint/format targets before submission, and archive the resulting logs/evidence under `specs/001-ai-refactor-plan/reports/`.

### Readiness Service Architecture

- A new `packages/devops/readiness/` module provides developer/ops tooling for the modernization program. It reads canonical datasets from `specs/001-ai-refactor-plan/data/` (inventory, gaps, LangSmith exports) and exposes typed accessors plus CLI utilities for future services.  
- The module owns aggregation logic, JSON/JSONL emitters, readiness dashboard payloads, and contracts for API layers to consume readiness state without duplicating storage. Feature-specific datasets remain versioned under `specs/<feature>/...` while the module provides reusable code ready for production adoption.  
- The toolkit may optionally persist normalized readiness tables into the developer Postgres database to preview future service integrations; no production databases are modified during this planning phase.  
- Activation notes, dry-run transcripts, rollback checklists, and sampling strategies remain stored under `specs/001-ai-refactor-plan/reports/activation_*` and are mirrored into LangGraph spec §8.3 runbooks so Ops documentation stays authoritative.

### Phased Refactor Roadmap

#### Phase 1 – Schema bundle (spec/ → schemas/)

- Rename the canonical bundle directory from `spec/` to `schemas/` while keeping a single source of truth.
- Reorganize the bundle by domain (automation/, platform/, guardian/, ops/, shared/, etc.) so schemas remain discoverable and not a catch-all.
- Update doc tooling (`doc_tools.manage_docs`, Spectral configs, lint scripts), verification utilities (`scripts/lpe/verify_policy_context.py`, `tests/agents/test_schema_consistency.py`, etc.), and any other references to point at `schemas/`.
- Document `schemas/` in the repository tree appendix as “shared machine-readable schemas consumed by services, tooling, and CI.”
- Keep generated Pydantic/dataclass models in their packages, with the canonical bundle remaining the single source for tooling.

#### Phase 2 – Top-level root cleanup

- Delete empty placeholder files such as `reading` and `udocket-starship.sh` or relocate them into docs if content ever appears.
- Repoint tooling so coverage and Typewiz outputs land under `out/` (`out/test-reports/coverage.xml`, `out/typewiz/...`) and remove the root-level artifacts.
- Update `scripts/dev/export_requirements.py` to write into `out/requirements/` (already gitignored) and delete the tracked `requirements/` directory.
- Move `db/` test helpers into `tooling/fixtures/sqlalchemy/`, updating imports accordingly, and verify nothing else lives at the repo root beyond the canonical directory set (apps/, automation/, packages/, services/, config/, infra/, ops/, tests/, tooling/, docs/, schemas/, specs/, out/, storage/, scripts/, etc.).

#### Phase 3 – Automation tree restoration

- Create `automation/pipelines/` and relocate stage metadata, QA policies, and cost ceilings there so the tree mirrors the LangGraph definitions described in the TDD appendix (current automation tree only contains `langgraph/`, `agents/`, `task_modules/`).

#### Phase 4 – `packages/common/` purity refactor

- Move framework-aware helpers (e.g., `packages/common/django/`, jobs, operations) into `packages/core/` or the relevant application packages.
- Introduce foundational helper subpackages such as `packages/common/paths/`, `packages/common/config/env.py`, `packages/common/json/`, and `packages/common/prompts/`, providing migration shims until consumers switch to the new layout.
- Update AGENTS.md/appendix to codify that `packages/common/` stays framework-free going forward.

#### Phase 5 – Tooling outputs & docs

- Configure Typewiz via `typewiz.toml` to emit manifest files, dashboards, and JSON into `out/typewiz/`.
- Point coverage settings (`.coveragerc`, CI commands) to produce reports in `out/test-reports/coverage.xml`.
- Ensure requirements exports flow to `out/requirements/`, update README/dev docs, and refresh `docs/overview/tdd/appendices/repository_trees.md` to mention `schemas/`, describe `automation/pipelines/`, and foreshadow the Codex workflow guidance.

#### Phase 6 – Codex workflow documentation

- Treat `scripts/codexhome.sh` as the blessed workflow: document running `scripts/codexhome.sh .` (plus `./scripts/codexhome.sh --print-export .`) to pin `CODEX_HOME`, clarifying that prompts/config remain in git while secrets/logs stay ignored.
- Explain that `.vscode` auto-sources `.codex/.codexhome`, so terminals already have `CODEX_HOME` set when opened via VS Code.

#### Phase 7 – Misc confirmations

- Keep `deps/typewiz/` as the temporary vendor drop until upstream publishes the needed release; annotate this exception in README.
- Reiterate that only `tooling/` and `typings/` may contain dev/stub artifacts, and future helpers must live there (not in root).
- Validate that Dockerfiles do not require updates for the schema rename/output relocation, but double-check every build stage that referenced `spec/`/`schemas/` to be safe.

### Key Entities

- **MigrationStageReadiness**: Represents a LangGraph stage (ingest, planner, executor, auditor, etc.) with fields for current status, evidence links, scoring across architecture/compliance/observability, and target cutoff date.
- **CapabilityGap**: A structured gap record containing component ID, deficiency category (architecture, tooling, telemetry, residency), severity, owner, mitigation plan, and due date.
- **ObservabilityControl**: Defines telemetry/control expectations per pipeline stage (metrics, traces, ops JSONL schema, alert routing), noting whether LangFuse is active, the environment scope, and the associated enable/disable evidence.
- **LLMToolingDecision**: Captures selected tooling (evaluation harness, guardrails, prompt registry) with LangSmith-specific governance data, comparison matrices, approvals, and rollout sequencing.

### Schema & Interface Contracts *(Constitution P1)*

- **Internal Models**: MigrationStageReadiness, CapabilityGap, ObservabilityControl, and LLMToolingDecision will be expressed as typed dataclasses or `TypedDict` structures within the agent package to ensure deterministic serialization when emitting ops/audit artifacts.
- **External Schemas**: Publish JSON schema revisions for the readiness matrix export, LangSmith evaluation evidence, and observability checklist so downstream tooling (dashboards, audit bots) can validate inputs; version identifiers must increment when fields or enumerations change.
- **Backward Compatibility**: Provide migration notes for consumers of legacy readiness exports; support a dual-write period where both old and new schema are emitted until downstream teams confirm cutover.

### Compliance, Observability & Residency *(Constitution P2 & P5)*

- **Telemetry**: Instrument each LangGraph stage with OTLP spans, latency/cost metrics, and structured ops JSONL entries; define dashboards covering migration velocity, blocker aging, LLM cost per run, prompt change frequency, plus LangFuse R&D dashboards with explicit enable/disable evidence.
- **Residency & Data Handling**: Specify residency classification for all AI module data (PII/regulated/unregulated), storage regions, retention periods, and redaction requirements for exported readiness data; document LangSmith dataset handling and ensure temporary LangFuse traces follow the same residency policies, blocking activation when metadata is missing.
- **AI Runtime Contract**: Confirm all LLM calls route through the centralized AI runtime (`packages.ai.api` or injected `AIClient`), enforce provider allow-lists, capture prompt/response metadata for audits, and describe expected prompt evaluation cadence before promoting new prompts.

### Security, Performance & Resilience *(Constitution P5 & P6)*

- **Threat Model**: Evaluate abuse cases including prompt injection into partially migrated stages, unauthorized access to migration dashboards, LangSmith credential leakage, and LangFuse trace exfiltration; require security review plus automated scanning of artifacts before release.
- **Performance Budgets**: Establish target budgets per pipeline stage (e.g., readiness computation completes in <10 minutes, observability export latency <2 minutes, LangFuse sampling adds <5% run overhead) and define escalation procedures if budgets exceed thresholds during ramp.
- **Migrations & DR**: Mandate forward-only migrations with snapshot backups of existing manifests, include rollback instructions for readiness data, ensure DR playbooks incorporate new telemetry and AI runtime dependencies, and document LangFuse teardown/recovery paths since it is temporary.
- **Frontend/UX**: Ensure readiness surfaces meet accessibility expectations (keyboard navigation, high-contrast views) and localization for stakeholder-facing summaries if required by governance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of AI module components and LangGraph stages are represented in the readiness inventory with verified ownership and evidence links.
- **SC-002**: At least 90% of remaining modernization tasks carry documented dependencies, estimates, and acceptance gates, enabling inclusion in the next two quarterly plans.
- **SC-003**: Observability coverage plan demonstrates metrics/traces/logging definitions for every pipeline stage, including LangFuse R&D dashboards, with at least 95% of required telemetry hooks validated in non-production dry-runs.
- **SC-004**: Document the solo activation sign-off, rollback rehearsal results, and the follow-on plan for executive approval in `specs/001-ai-refactor-plan/reports/activation_signoff.md`.
- **SC-005**: Produce an adoption readiness playbook (`specs/001-ai-refactor-plan/reports/adoption_playbook.md`) describing how LangSmith enablement will extend beyond this solo planning phase (no numerical coverage required during planning).
- **SC-006**: `schemas/` replaces `spec/` as the canonical schema bundle, passes doc tooling/tests linked to the new path, and the repository tree appendix documents the directory purpose.
- **SC-007**: Repository root audit confirms only the sanctioned directories remain, coverage/typewiz/reports/requirements outputs write under `out/`, and `automation/pipelines/` plus the packages/common refactor are reflected in docs and verified by CI tooling checks.

## Assumptions

1. All earlier partial migrations followed the LangGraph agent specification and any deviations will be surfaced in the readiness discovery workshops.
2. Modern LLM tooling selections must integrate with existing residency/egress guardrails; no provider outside the current compliance perimeter will be considered without a separate governance project.
3. Observability infrastructure (OTLP pipeline, ops JSONL storage, dashboarding stack) already exists; this effort configures and extends it for the AI module rather than building net-new infrastructure.
4. LangFuse access is restricted to R&D environments with pre-approved data boundaries, and stakeholders agree the integration will be removed once permanent observability reaches parity.
5. This migration completion plan is executed by a single developer, so formal cross-team communication cadences and multi-party approval workflows are out of scope.
6. The plan runs as the sole active workstream; dependency re-baselining for parallel initiatives is unnecessary because upstream systems remain unchanged during execution.
