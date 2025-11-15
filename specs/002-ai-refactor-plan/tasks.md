---

description: "Task list for AI Refactor Implementation Delivery"
---

# Tasks: AI Refactor Implementation Delivery

**Input**: Design documents from `/specs/002-ai-refactor-plan/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Follow the quickstart testing checklist (`make typing.ai`, `make all.test`, LangSmith evals, LangFuse-offline regression, `uv run --project automation make ai-module.dry-run`). Telemetry/manifest verification commands are listed per user story so each phase can be validated independently.

**Organization**: Tasks follow the required phase structure with one phase per user story (US1..US3) plus setup/foundational/polish phases. Each user story phase includes an independent test command.

## Format: `[ID] [P?] [Story?] Description with file path`

- Checkbox + Task ID (T001..)
- [P] when a task can run in parallel (different files, no dependency)
- [Story] label only for user story phases (US1/US2/US3)
- Paths point to actual files/directories mentioned in plan/spec/data-model/contracts

---

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Configure Codex home and the shared `.venv` per `./scripts/codexhome.sh --print-export .` and capture the exported env in `specs/002-ai-refactor-plan/reports/baseline_env.log`.
- [x] T002 Install automation project dependencies by running `uv pip install -r automation/requirements.txt --python .venv/bin/python` and log success to `specs/002-ai-refactor-plan/reports/automation_install.log`.
- [x] T003 Run baseline gates (`make typing.ai`, `make all.test`, `make docs.check.links`, `make schema.lint`) and archive the output under `specs/002-ai-refactor-plan/reports/baseline_gates.log`.

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T004 Create the required reporting directories (`specs/002-ai-refactor-plan/reports/manifest.jsonl`, `specs/002-ai-refactor-plan/reports/manifest_gaps.json`, `specs/002-ai-refactor-plan/reports/automation_env.log`, `storage/ops/ai-refactor/graphs/`, `storage/audit/ai-refactor/`) and commit README placeholders describing their contents.
- [ ] T005 Implement a `scripts/check_common_guardrail.py` helper that scans `packages/common/` and fails if any module imports Django/LangGraph/telemetry packages, then call it from `make typing.ai` to enforce the framework-free guardrail.
- [x] T006 Capture the pre-cleanup root layout using `tree -L 1 > specs/002-ai-refactor-plan/reports/root_before.txt` so the repo baseline is documented before refactors.

---

## Phase 3: User Story 1 – Activate Blueprint Execution (Priority: P1)

**Goal**: Deliver a signed implementation manifest that links every artifact under `specs/001-ai-refactor-plan/` to repository surfaces, owners, and evidence so governance can trace each modernization item.

**Independent Test**: `python -m packages.devops.readiness.cli manifest --feature 002-ai-refactor-plan --out specs/002-ai-refactor-plan/reports/manifest.jsonl` plus `python -m packages.devops.readiness.cli verify --feature 002-ai-refactor-plan` should produce the manifest and surface gaps.

- [x] T007 [US1] Add typed dataclasses/StrEnums in `packages/common/types/ai_refactor.py` covering `ImplementationBlueprintRecord`, `StageExecutionRecord`, and telemetry ledger references per `data-model.md`.
- [x] T008 [US1] Publish JSON Schemas for the manifest and telemetry ledger under `schemas/automation/ai-refactor/manifest-v1alpha2.json` and `ledger-v1alpha0.json`, sourcing field definitions from the contracts and data model.
- [x] T009 [US1] Extend `packages/devops/readiness/cli.py` with the `manifest` subcommand that ingests `specs/001-ai-refactor-plan/` artifacts, hydrates the typed records, and writes `specs/002-ai-refactor-plan/reports/manifest.jsonl`.
- [x] T010 [US1] Implement manifest signing/verifier helpers in `packages/devops/readiness/manifest.py` that compute SHA256 per artifact, timestamp entries, and attach owner metadata.
- [x] T011 [US1] Add a manifest gap detector writing `specs/002-ai-refactor-plan/reports/manifest_gaps.json` when artifacts are unmapped, including dependency cycles flagged as blocked.
- [x] T012 [US1] Implement the `/ai-refactor/manifest` endpoint in `automation/langgraph/api_refactor.py` (per `contracts/ai-refactor-openapi.yaml`) that proxies `specs/002-ai-refactor-plan/reports/manifest.jsonl` and respects the OpsToken security scheme.
- [x] T013 [US1] Add property/regression tests in `tests/automation/test_manifest.py` that assert determinism/hashing and exercise the manifest endpoint with mocked tokens.
- [x] T014 [US1] Document the manifest workflow, API contract, and evidence expectations in `docs/automation/langgraph-agents.md` and `specs/002-ai-refactor-plan/quickstart.md` section 3.

---

## Phase 4: User Story 2 – Materialize LangGraph & AI Runtime Changes (Priority: P2)

**Goal**: Materialize typed LangGraph lanes, StageMaps, and AI runtime wiring so the automation pipelines defined in spec 001 execute deterministically with QA contracts and residency tagging.

**Independent Test**: `make automation.langgraph.plan` should instantiate every lane/stage, emit deterministic ops JSONL entries, and log QA contract satisfaction.

> **Doc check reminder:** Before editing LangGraph, LangSmith, or LangFuse wiring covered in this story, consult the official docs (LangGraph spec plus LangSmith/LangFuse documentation surfaced via the Archon knowledge base) to guarantee you’re implementing the latest runtime behaviors rather than relying on outdated training-data assumptions; capture the doc references you used in `specs/002-ai-refactor-plan/reports/`.

- [ ] T015 [US2] Expand `automation/pipelines/stage_map.py` with the lane definitions, StageKey sequences, QA contract IDs, and cost ceilings described in spec 001 while keeping stage metadata typed.
- [ ] T016 [US2] Create lane-value objects/StrEnums in `automation/pipelines/models.py` that mirror `LangGraphLanePackage` (lane_id, stage_keys, ai_runtime_profile) and expose validation helpers.
- [ ] T017 [US2] Update `automation/langgraph/runtime.py` to load the refreshed lane packages, enforce dependency ordering, and record ops/audit entries under `storage/ops/ai-refactor/` whenever a lane runs.
- [ ] T018 [US2] Register new AI runtime profiles/residency tags in `packages/ai/api.py` for the lanes added above so `AIClient` routing stays on the hardened runtime.
- [ ] T019 [US2] Publish QA/cost verification tests in `tests/automation/test_stage_contracts.py` (or similar) that compare StageMap entries against spec 001 QA metadata with zero placeholders.
- [ ] T020 [US2] Update `tests/automation/test_stage_graph.py` property suite to assert StageMap acyclicity and cost ceilings and rerun after each change.
- [ ] T021 [US2] Reflect the lane/QA updates in `docs/automation/langgraph-agents.md` and `docs/overview/tdd.md` with schema references plus plan linkages.
- [x] T015 [US2] Expand `automation/pipelines/stage_map.py` with the lane definitions, StageKey sequences, QA contract IDs, and cost ceilings described in spec 001 while keeping stage metadata typed.
- [x] T016 [US2] Create lane-value objects/StrEnums in `automation/pipelines/models.py` that mirror `LangGraphLanePackage` (lane_id, stage_keys, ai_runtime_profile) and expose validation helpers.
- [x] T017 [US2] Update `automation/langgraph/runtime.py` to load the refreshed lane packages, enforce dependency ordering, and record ops/audit entries under `storage/ops/ai-refactor/` whenever a lane runs.
- [x] T018 [US2] Register new AI runtime profiles/residency tags in `packages/ai/api.py` for the lanes added above so `AIClient` routing stays on the hardened runtime.
- [x] T019 [US2] Publish QA/cost verification tests in `tests/automation/test_stage_contracts.py` (or similar) that compare StageMap entries against spec 001 QA metadata with zero placeholders.
- [x] T020 [US2] Update `tests/automation/test_stage_graph.py` property suite to assert StageMap acyclicity and cost ceilings and rerun after each change.
- [x] T021 [US2] Reflect the lane/QA updates in `docs/automation/langgraph-agents.md` and `docs/overview/tdd.md` with schema references plus plan linkages.

---

## Phase 5: User Story 3 – Operationalize Observability, Residency, and Entity Graph (Priority: P3)

**Goal**: Ensure telemetry (OTLP, LangSmith, LangFuse), residency ledgers, and the Entity Relationship Graph persist alongside each automation dry run and expose readiness snapshots + ledger data via the documented contracts.

**Independent Test**: `uv run --project automation make ai-module.dry-run` should emit OTLP spans, LangSmith eval IDs, LangFuse evidence, ops JSONL, residency ledger entries, and write entity graph snapshots to `storage/ops/ai-refactor/graphs/`, then `uv run --project automation python -m packages.devops.readiness.cli verify --feature 002-ai-refactor-plan` should assert those outputs.

> **Doc check reminder:** Confirm the LangGraph, LangSmith, and LangFuse documentation referenced in your work reflects the current production guidance (use the Archon knowledge base to retrieve the latest sources) before modifying instrumentation or epidemiology surfaces, and log the doc versions cited in the appropriate `specs/002-ai-refactor-plan/reports/` artifact.

- [x] T022 [US3] Implement the telemetry configuration module in `packages/telemetry/config.py` that centralizes structlog/OTLP setup, LangSmith workspace routing, LangFuse toggles, and writes ledger rows to `storage/audit/ai-refactor/` per the contracts.
- [x] T023 [US3] Instrument LangGraph stages to append residency ledger entries (including `residency_tag`, `telemetry_bundle_path`, `langsmith_eval_ids`, `langfuse_session_id`, `disconnect_event`) handled by `packages/common/types/ai_refactor.py` and persisted under `storage/audit/ai-refactor/ledger.jsonl`.
- [x] T024 [US3] Build the entity graph service in `automation/entity_graph/service.py` that reads Analyze outputs, emits node/edge records (per `EntityRelationshipGraph`), and writes them to `storage/ops/ai-refactor/graphs/graph_<run_id>.json` with provenance references.
- [x] T025 [US3] Add `automation/entity_graph/cli.py` exposing `graph sync` and `graph verify` commands that validate mandatory relationships and block progress when edges/missing nodes occur, writing failures to `specs/002-ai-refactor-plan/reports/graph_failures.log`.
- [x] T026 [US3] Integrate entity graph snapshots into `automation/pipelines/entity_graph.py` helpers so StageMaps can pull relational context (e.g., component-to-artifact edges) when computing readiness signals.
- [x] T027 [US3] Implement the `/ai-refactor/readiness-snapshots` and `/ai-refactor/residency-ledger` endpoints in `automation/langgraph/api_refactor.py` per `contracts/ai-refactor-openapi.yaml`, returning structured data from `storage/ops/ai-refactor/graphs/` and `storage/audit/ai-refactor/`.
- [x] T028 [US3] Create regression tests (`tests/regression/test_langsmith_hooks.py`, `tests/regression/test_langfuse_offline.py`) that exercise LangSmith eval uploads, LangFuse disable toggles, and ledger immutability when LangFuse goes offline.
- [x] T029 [US3] Update telemetry/graph schema docs in `docs/automation/langgraph-agents.md` and `docs/overview/tdd.md` to cite the residency ledger schema, entity graph exports, and dry-run validation command.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T030 Update `specs/002-ai-refactor-plan/reports/manifest_gaps.json` and `specs/002-ai-refactor-plan/reports/evidence_index.json` with run-specific metadata after each dry run so auditors can correlate manifest entries, telemetry, and release evidence.
- [ ] T031 Run the final CI sweep (`make typing.ai`, `make all.test`, LangSmith eval suite, LangFuse-offline regression, `uv run --project automation make ai-module.dry-run`) and store logs under `specs/002-ai-refactor-plan/reports/final_ci.log`.
- [ ] T032 Archive LangSmith evaluation reports, Typewiz diffs, and Schema lint outputs in `specs/002-ai-refactor-plan/reports/telemetry_reports/` plus capture entity graph coverage metrics in `specs/002-ai-refactor-plan/reports/graph_coverage.md`.
- [ ] T033 Update `docs/automation/langgraph-agents.md`, `docs/overview/tdd.md`, and `specs/002-ai-refactor-plan/reports/release_notes.md` to summarize structure cleanup, automation metadata, manifest traceability, entity graph outputs, and telemetry evidence.

---

## Dependencies & Execution Order

- **Setup → Foundational**: Phase 2 blocks all user stories until Phase 1 completes.
- **Foundational → User Stories**: US1, US2, and US3 all require the guardrails (Phase 2) before starting. Stories can run in parallel once foundational work is done, but US1 (manifest) is the MVP and should prove the manifest/audit loop before the others.
- **Polish**: Depends on all user stories completing. Polish tasks can run in parallel with US3 regression cleanup if telemetry outputs are ready.

### User Story Dependency Graph

```
Phase 1 ✅
   ↳ Phase 2 ✅
        ↳ [US1] Manifest (MVP) → validates governance
        ↳ [US2] LangGraph lanes (can run in parallel with US1 after Phase 2)
        ↳ [US3] Telemetry + Entity Graph (runs once Phase 2 done; can overlap with US2)
Phase 6 → Polish (after all stories)
```

## Parallel Execution Examples

- **US1**: `T008`, `T009`, and `T010` can run in parallel (models, schemas, CLI) because they touch different modules; `T012` can run once manifest data exists.
- **US2**: `T015`, `T016`, and `T017` (StageMap, lane models, runtime loader) can be implemented concurrently by different engineers before QA tests begin.
- **US3**: `T022`, `T023`, `T024`, and `T025` are independent (telemetry config, instrumentation, entity graph service, CLI) and can proceed in parallel, with `T026` integrating their outputs afterward.

## Implementation Strategy

### MVP First (User Story 1 only)
1. Complete Phase 1 (setup) and Phase 2 (foundational guardrails).
2. Deliver US1 (manifest pipeline) with CLI, signing, API, and docs.
3. Run the independent manifest test (`python -m packages.devops.readiness.cli manifest ...`) and ensure auditors can read the manifest via the new endpoint.
4. Stop and validate before layering lanes or telemetry.

### Incremental Delivery
1. After US1, incrementally deliver US2 (LangGraph lanes) and US3 (telemetry/entity graph) while keeping each story independently testable.
2. Each story adds measurable capability: manifest traceability → deterministic pipelines → telemetry + relational context.
3. Polish (Phase 6) ties the stories together and documents evidence for release.

### Parallel Team Strategy
1. Team finishes Setup + Foundational together.
2. Parallel threads begin: Developer A owns US1, Developer B works on US2, Developer C tackles US3.
3. Story-specific tests and docs validate each increment before final polish.
