# Backlog Generator Test Plan

Target script: `specs/001-ai-refactor-plan/scripts/migration_plan_generator.py` (prototype), later promoted into automation tooling.

## Objectives
- Verify dependency sorting, critical-path tagging, and LangGraph stage metadata produced for `/migrations/backlog`.
- Ensure generator enforces type-first contracts from `drafts/readiness_types.py` and `plan.md` FR-003/FR-012 requirements.

## Test Cases
| ID | Scenario | Assertions |
|----|----------|------------|
| BG-001 | Deterministic ordering with DAG input. | Output list sorted by topological order respecting dependencies; tasks without dependencies keep input order.
| BG-002 | Critical path detection. | Tasks whose dependencies form longest chain get `critical_path=true`; others remain false.
| BG-003 | Stage metadata hydration. | Each task carries `stage_key` matching `packages/common/agents/stage_map.StageKey` and includes `qa_gates`, `cost_ceiling` references from stage catalog.
| BG-004 | Effort range validation. | `effort_low`/`effort_high` remain positive and `low <= high` else generator raises `BacklogValidationError`.
| BG-005 | Dependency existence. | Missing dependency IDs trigger validation error naming offending ID.
| BG-006 | Serialization parity. | JSON output matches schema in `contracts/openapi.yaml#/components/schemas/MigrationTask`; property test compares to jsonschema validator.

## Tooling
- Unit tests in `tests/devops/backlog/test_generator.py` using fixed fixture graph.
- Property test with Hypothesis generating DAGs limited to 10 nodes to confirm topological ordering invariants.
- Spectral or jsonschema validation for final payload.

## Exit Criteria
- ≥90% coverage on generator module.
- Critical path logic proven via deterministic fixtures and Hypothesis.
