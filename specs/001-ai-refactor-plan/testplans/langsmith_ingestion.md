# LangSmith Ingestion Test Plan

## Scope
Validate the flow for `/tooling/langsmith/evaluations` ingestion, including schema validation, residency enforcement via `packages.ai.api`, and export handling.

## Test Cases
| ID | Scenario | Assertions |
|----|----------|------------|
| LS-001 | Submit valid EvaluationEvidence payload. | HTTP 202; payload stored in readiness repo; ops JSONL entry created referencing evidence file.
| LS-002 | Missing mandatory field (prompt_bundle_id). | API returns 422 with field detail; no ops entry written.
| LS-003 | Invalid dataset hash format. | Validator rejects (not 64 hex chars) and logs warning.
| LS-004 | AI runtime bypass attempt. | Mock ensures ingestion uses `packages.ai.api`; direct provider call raises error and test asserts log message.
| LS-005 | Governance tags requirement. | Payload with `langfuse_enabled=true` must include governance tag `r&d`; absence yields 422.
| LS-006 | Attachments evidence persistence. | Endpoint writes attachments list into readiness data and includes in ops JSONL `evidence` array.

## Tooling
- `pytest` + `schemathesis` hitting local API.
- Use typed fixtures from `drafts/readiness_types.py`.
- Logs stored in `reports/langsmith_smoke.jsonl` for audit.
