# API Contract Test Plan – Readiness & Tooling Endpoints

Source contract: `specs/001-ai-refactor-plan/contracts/openapi.yaml` (AI Module Migration Readiness API, version 0.1.0).

## Strategy
- Validate request/response schemas via Spectral + jsonschema using fixtures derived from `drafts/readiness_types.py`.
- Exercise query parameter filters (`status`, `owner_team`) and path parameters (`componentId`, `sessionId`).
- Enforce residency/guardrail expectations: all server interactions pass through `packages.ai.api` mocks so no provider SDKs leak into tests.

## Test Matrix

| ID | Endpoint | Scenario | Assertions |
|----|----------|----------|------------|
| API-001 | `GET /readiness/components` | Happy path without filters. | HTTP 200; response body is list; every item validates against `MigrationStageReadiness` schema; `stage_key` matches enum; `cutoff_date` `>= today`. |
| API-002 | `GET /readiness/components?status=blocked` | Filtered query. | Only blocked records returned; invalid enum triggers 422 validation error. |
| API-003 | `GET /readiness/components?owner_team=ai-modernization` | Owner filter. | Response only contains entries with requested owner; absence returns empty list (still 200). |
| API-004 | `POST /readiness/components/{componentId}/gaps` | Create new gap with deterministic UUID. | HTTP 201; echoes request payload; ensures `gap_id` format UUIDv7; `componentId` path matches body `component_id`; missing required fields cause 422 with field-specific errors. |
| API-005 | `GET /migrations/backlog` | Retrieve backlog. | HTTP 200; array of `MigrationTask`; verify mandatory fields (stage key, dependencies). |
| API-006 | `POST /tooling/langsmith/evaluations` | Ingest evaluation evidence. | HTTP 202; body validated against `EvaluationEvidence`; ensures `run_completed_at >= run_started_at` and governance tags persisted. |
| API-007 | `POST /observability/langfuse/sessions` | Enable LangFuse session (dev env). | HTTP 201; `sampling_rate <= 0.25`; `environment` limited to dev/staging; response echoes kill-switch instructions. |
| API-008 | `DELETE /observability/langfuse/sessions/{sessionId}` | Disable session. | HTTP 204; ensures session id format validated; follow-up verification that session removed from readiness state. |

## Tooling
- Use `pytest` + `hypothesis` for payload generation; `schemathesis` for endpoint fuzzing against the OpenAPI doc.
- Run inside `uv run --project specs/001-ai-refactor-plan` to keep dependencies scoped.
- Capture results/logs in `reports/langsmith_smoke.jsonl` and `reports/langfuse_enable_disable.md` when applicable.

## Exit Criteria
- All endpoints pass happy-path + validation tests.
- Error scenarios (422, 404) explicitly asserted where schema demands.
- Contract test suite wired into `make all.test` future stage.
