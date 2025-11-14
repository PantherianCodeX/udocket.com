---

description: "Task list for executing the AI Module Migration Completion Plan"
---

# Tasks: AI Module Migration Completion Plan

**Input**: Design documents from `/home/user/Code/udocket/specs/001-ai-refactor-plan/` (plan.md, spec.md, research.md, data-model.md, quickstart.md, `/home/user/Code/udocket/specs/001-ai-refactor-plan/contracts/openapi.yaml`)
**Prerequisites**: Follow `/home/user/Code/udocket/AGENTS.md`, run `/home/user/Code/udocket/.specify/scripts/bash/check-prerequisites.sh --json` (completed), and keep all feature artifacts within the `specs/001-ai-refactor-plan/` tree until implementation begins.

**Tests**: Story-specific contract/unit tests are captured as test plan documents under `specs/001-ai-refactor-plan/testplans/` so future implementation can execute them verbatim.

**Organization**: Phases follow setup → foundational → one phase per user story (priority order) → activation → polish. Every task records its deliverable inside the feature directory unless it updates an existing domain document (e.g., LangGraph spec §8.3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (touches different files, no unmet dependencies)
- **[Story]**: US1 (Assess Readiness), US2 (Plan Modernization), US3 (LLM Tooling & Observability), US4 (Governance & Schema Refactors)
- All feature-specific paths live under `/home/user/Code/udocket/specs/001-ai-refactor-plan/…`

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Capture Codex CLI home pinning steps (script invocation, expected output) in `/home/user/Code/udocket/specs/001-ai-refactor-plan/setup/codex_home.md` so future implementation can run the command confidently.
- [ ] T002 [P] Document required LangSmith/LangFuse `.env` variables and rotation notes in `/home/user/Code/udocket/specs/001-ai-refactor-plan/setup/env_placeholders.md`; no repo-level `.env.example` edits occur yet.
- [ ] T003 [P] Author `/home/user/Code/udocket/specs/001-ai-refactor-plan/reports/ops_audit_manifest.md` explaining how readiness ops JSONL/audit artifacts will be stored under the feature directory during this planning phase.

---

## Phase 2: Foundational (Blocking Prerequisites)

- [ ] T004 Draft typed primitives (`MigrationStageReadiness`, `CapabilityGap`, `ObservabilityControl`, `LLMToolingDecision`, `ToolingWorkspace`, `EvaluationEvidence`, `ObservabilitySession`, `VendorUsageBudget`) in `/home/user/Code/udocket/specs/001-ai-refactor-plan/drafts/readiness_types.py`, mapping each field to the eventual package locations.
- [ ] T005 [P] Record LangGraph stage catalog deltas in `/home/user/Code/udocket/specs/001-ai-refactor-plan/drafts/stage_catalog.md`, referencing the canonical entries in `packages/common/agents/stage_map.py` without editing production files.
- [ ] T006 [P] Create deterministic readiness fixture samples under `/home/user/Code/udocket/specs/001-ai-refactor-plan/data/readiness/examples/` and outline property-test expectations in `/home/user/Code/udocket/specs/001-ai-refactor-plan/drafts/test_plan.md`.

---

## Phase 3: User Story 1 - Assess Current Migration State (P1)

**Goal**: Maintain a feature-scoped readiness inventory and blockers list.

**Independent Test**: Run `python /home/user/Code/udocket/specs/001-ai-refactor-plan/scripts/refresh_readiness.py --lane modernization` and confirm it regenerates `data/readiness/inventory.json` + `reports/readiness_ops.jsonl` with owner/evidence coverage.

### Tests for User Story 1

- [ ] T007 [P] [US1] Write the API contract test plan in `/home/user/Code/udocket/specs/001-ai-refactor-plan/testplans/api_readiness_tests.md`, citing request/response payloads from `contracts/openapi.yaml`.
- [ ] T008 [P] [US1] Describe readiness snapshot unit/property tests in `/home/user/Code/udocket/specs/001-ai-refactor-plan/testplans/readiness_snapshot_tests.md`, covering scoring ranges, owner validation, and automated gap creation triggers.

### Implementation for User Story 1

- [ ] T009 [US1] Populate baseline readiness datasets (`inventory.json`, `gaps.json`) inside `/home/user/Code/udocket/specs/001-ai-refactor-plan/data/readiness/` using the drafted typed primitives.
- [ ] T010 [P] [US1] Build an aggregation notebook `/home/user/Code/udocket/specs/001-ai-refactor-plan/tools/readiness_aggregator.ipynb` that produces readiness matrices, blocker summaries, and export snippets for dashboards.
- [ ] T011 [US1] Implement `packages/devops/readiness/cli.py` with a `refresh` command that ingests raw inputs (CSV/Sheets) and regenerates readiness + ops JSONL artifacts into `specs/001-ai-refactor-plan/data|reports/`.
- [ ] T012 [US1] Build the underlying ingest/aggregation module in `packages/devops/readiness/service.py` plus a pyproject entry point; capture contract details in `blueprints/devops_readiness_module.md`.
- [ ] T013 [P] [US1] Draft the API blueprint in `/home/user/Code/udocket/specs/001-ai-refactor-plan/blueprints/readiness_api.md`, detailing serializers/views that will consume the devops module outputs.
- [ ] T014 [US1] Design the readiness dashboard UX in `/home/user/Code/udocket/specs/001-ai-refactor-plan/blueprints/readiness_dashboard.md`, including wireframes, accessibility notes, and data bindings drawing from the devops module.
- [ ] T015 [US1] Maintain a blockers/risk log at `/home/user/Code/udocket/specs/001-ai-refactor-plan/reports/risk_log.jsonl`, tagging each entry with owners, severity, and mitigation plan references.

---

## Phase 4: User Story 2 - Plan Remaining Modernization (P2)

**Goal**: Produce a sequenced backlog with dependencies and LangGraph stage alignment.

**Independent Test**: Verify `/home/user/Code/udocket/specs/001-ai-refactor-plan/data/backlog/migration_backlog.json` lists every component with stage key, effort range, dependencies, and acceptance gates; dependency narrative exists in `reports/dependency_story.md`.

### Tests for User Story 2

- [ ] T016 [P] [US2] Create `testplans/backlog_generator_tests.md` covering dependency sorting, critical-path flags (`critical_path=true`), and gate propagation rules.

### Implementation for User Story 2

- [ ] T017 [US2] Author `blueprints/migration_stage_plan.md` describing stage metadata, QA policies, and cost ceilings aligned to the LangGraph TDD appendix.
- [ ] T018 [US2] Prototype the backlog generator logic in `/home/user/Code/udocket/specs/001-ai-refactor-plan/scripts/migration_plan_generator.py`, consuming readiness datasets and emitting draft `MigrationTask` records.
- [ ] T019 [P] [US2] Document the `/migrations/backlog` API shape plus serializer expectations in `blueprints/migration_plan_api.md`, linking to `contracts/openapi.yaml`.
- [ ] T020 [US2] Generate `data/backlog/migration_backlog.json` and the narrative companion `reports/dependency_story.md`, noting critical path chains and sequencing rationale.

---

## Phase 5: User Story 3 - Enable LLM Tooling & Observability (P3)

**Goal**: Specify LangSmith/LangFuse enablement, telemetry, and temporary observability controls.

**Independent Test**: Execute the quickstart checklist in `/home/user/Code/udocket/specs/001-ai-refactor-plan/quickstart.md` and confirm the resulting evidence files (`reports/langsmith_smoke.jsonl`, `reports/langfuse_enable.md`, `reports/langfuse_disable.md`) exist.

### Tests for User Story 3

- [ ] T021 [P] [US3] Capture LangSmith ingestion test cases in `testplans/langsmith_ingestion.md`, including schema validation and AI runtime enforcement scenarios.
- [ ] T022 [P] [US3] Capture LangFuse enable/disable test cases in `testplans/langfuse_sessions.md`, covering sampling caps, TTL enforcement, and kill-switch timelines.

### Implementation for User Story 3

- [ ] T023 [US3] Document workspace metadata (env names, owners, rotation cadence, `.env` variable mapping) in `data/tooling/workspaces.yaml`.
- [ ] T024 [US3] Script LangSmith workspace provisioning under `scripts/langsmith/provision_workspace.py`, emitting logs/evidence into `reports/langsmith_workspace_records.jsonl`.
- [ ] T025 [US3] Script LangSmith evaluation runs under `scripts/langsmith/run_eval.py`, tagging prompts/datasets and producing `reports/langsmith_eval_results.json`.
- [ ] T026 [US3] Script LangSmith export processing under `scripts/langsmith/export_results.py` using the local schema `schemas/tooling/evaluation_evidence.schema.json` inside the feature directory.
- [ ] T027 [US3] Draft the tooling ingestion blueprint (`blueprints/langsmith_ingestion_api.md`) describing how `/tooling/langsmith/evaluations` will be implemented later.
- [ ] T028 [US3] Write the LangFuse enable/disable SOP in `reports/langfuse_enable_disable.md`, attaching screenshots/evidence references.
- [ ] T029 [US3] Update `docs/automation/langgraph-agents.md` §8.3 with LangSmith evaluation and LangFuse R&D activation steps, referencing the evidence files stored under `specs/001-ai-refactor-plan/reports/` (this is the only out-of-feature edit).
- [ ] T030 [P] [US3] Extend `quickstart.md` with the LangSmith/LangFuse operational checklist, noting evidence file locations.
- [ ] T031 [US3] Document vendor budget monitoring thresholds and alert hooks in `reports/vendor_budget_plan.md`, tying to the data-model’s `VendorUsageBudget` fields.
- [ ] T032 [US3] Map telemetry and audit evidence expectations to actual file outputs in `reports/tooling_evidence_matrix.md` to satisfy observability success criteria.

---

## Phase 6: User Story 4 - Govern Repository & Schema Refactors (P3)

**Goal**: Produce execution blueprints for schema rename, root cleanup, automation tree restoration, packages/common purity, tooling outputs, Codex workflow, and confirmations.

- [ ] T033 [US4] Draft the schema-bundle rename plan (`blueprints/schema_rename_playbook.md`) covering command sequence, doc updates, and verification steps before touching `/spec → /schemas` in a future implementation.
- [ ] T034 [P] [US4] Prepare the root-cleanup checklist (`blueprints/root_cleanup.md`) enumerating artifacts to remove/relocate, with before/after screenshots stored under `reports/root_cleanup_evidence/`.
- [ ] T035 [US4] Describe the automation tree restoration blueprint in `blueprints/automation_tree.md`, aligning `automation/pipelines/` structure with the TDD appendix without modifying the tree yet.
- [ ] T036 [US4] Draft the `packages/common/` purity migration plan (`blueprints/common_purity.md`), listing modules to relocate and shim strategy notes.
- [ ] T037 [P] [US4] Document the tooling output relocation plan (`blueprints/tooling_outputs.md`) for coverage/Typewiz/requirements, including updates needed in `.coveragerc`, `typewiz.toml`, and README when implementation occurs.
- [ ] T038 [US4] Summarize Codex workflow documentation changes in `blueprints/codex_workflow_docs.md`, referencing the sections of AGENTS.md and docs overview appendix that will need edits.
- [ ] T039 [P] [US4] Draft the confirmations/exception plan in `blueprints/remaining_confirmations.md`, covering `deps/typewiz/` annotation, dev/stub directory policy, and Docker reference audits.
- [ ] T040 [US4] Prepare patch-ready snippets for `docs/overview/tdd/appendices/repository_trees.md` and `docs/automation/langgraph-agents.md` inside `drafts/docs_updates/` so the documentation changes can be applied atomically when implementation proceeds.
- [ ] T041 [US4] Capture the governance acceptance checklist in `reports/governance_storyboard.md`, linking each FR (010–016) to the corresponding blueprint/evidence file.

---

## Phase 7: Activation Plan (FR-007)

- [ ] T042 Outline the activation playbook (dry-runs, sampling strategy—even if 100% local—rollback triggers, decision checkpoints) in `reports/activation_plan.md`.
- [ ] T043 [P] Script dry-run evidence generation in `scripts/activation/run_dry_run.py`, storing JSONL results in `reports/activation_dry_run.jsonl`.
- [ ] T044 Update `docs/automation/langgraph-agents.md` §8.3 to include the activation workflow (RB-AGENT-ACTIVATION) referencing the feature evidence files.
- [ ] T045 [P] Create `reports/activation_checklist.md` mapping each rollback command/toggle/verification step to the relevant readiness artifacts.
- [ ] T046 Record activation sign-off (even as a solo approval) and rollback rehearsal timestamps in `reports/activation_signoff.md`.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T047 Compile modernization release notes in `reports/release_notes.md` and stage the corresponding `docs/automation/langgraph-agents.md` updates for later merge.
- [ ] T048 [P] Summarize LangSmith/LangFuse telemetry and schema references in `reports/telemetry_summary.md`, mirroring the highlights that will eventually land in platform docs.
- [ ] T049 [P] Re-run the quickstart validation (documented in `quickstart.md`) and log timestamps/evidence links in `reports/quickstart_validation.md`.
- [ ] T050 [P] Execute the docs container workflow locally (via `make`/`uv` commands) and archive logs in `reports/docs/ai_module_migration.log`.
- [ ] T051 Record doc-workflow compliance evidence (commands, timestamps, links) in `reports/doc_workflow_checks.md` to satisfy FR-017.
- [ ] T052 Produce the LangSmith adoption readiness playbook in `reports/adoption_playbook.md`, outlining staged rollout steps and ownership handoff once implementation begins (supports SC-005).

---

## Dependencies & Execution Order

1. Setup (Phase 1) precedes Foundational (Phase 2); both must complete before any user story work.
2. US1 → US2 → US3 → US4 follow priority order but drafts can progress in parallel once their prerequisites exist.
3. Activation (Phase 7) depends on all user stories finishing; Polish (Phase 8) is the final consolidation.

## Implementation Strategy

1. Produce US1 readiness artifacts as the MVP deliverable for leadership visibility.
2. Layer US2 backlog planning immediately after to sequence the modernization tasks.
3. In parallel, complete US3 tooling specs and US4 governance blueprints so future implementation touches code with clear instructions.
4. Finalize activation docs and polished evidence before handing the plan off for execution.
