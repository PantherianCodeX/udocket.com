# Automation Tree Restoration Blueprint

## Goal
Recreate `automation/pipelines/` with stage metadata/QA/cost ceilings matching LangGraph TDD appendix; ensure automation tree includes `pipelines/`, `agents/`, `langgraph/`, `task_modules/`.

## Tasks
1. Create directory skeleton:
```
automation/
  pipelines/
    analyze_modernization.yaml
    compose_release.yaml
```
2. Populate YAML manifest referencing stage specs from `drafts/stage_catalog.md` with fields: `stage_key`, `enabled`, `depends_on`, `qa_gates`, `cost_ceiling`.
3. Ensure manifests consumed by new readiness tooling (ReadinessService) and future CLI.
4. Update docs (`docs/overview/tdd/appendices/repository_trees.md`) to mention restored tree.
5. Add enforcement tests verifying all stage keys exist in pipelines manifest.

## Evidence
- Snapshot pipeline manifests under `specs/001-ai-refactor-plan/drafts` before moving into repo root.
- Document readiness in `reports/governance_storyboard.md`.
