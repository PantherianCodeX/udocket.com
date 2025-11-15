# LangSmith Ingestion API Blueprint

## Endpoint
- `POST /tooling/langsmith/evaluations`
- Consumes `EvaluationEvidence` schema (see `schemas/tooling/evaluation_evidence.schema.json`).

## Flow
1. Request hits DRF view `LangSmithEvaluationView`.
2. Serializer validates payload using typed dataclass + JSON schema; ensures dataset hash format, run timestamps order, governance tags.
3. View delegates to `packages/devops/readiness/service.ReadinessService` to register the evidence (update datasets + ops JSONL).
4. Response returns 202 Accepted with reference to ops record + artifact hash.

## Validation Rules
- `dataset_hash` must be SHA256 hex (64 chars).
- `langfuse_enabled` tags require governance tag `r&d` (enforced at serializer layer).
- Attachments validated as URIs.
- If `run_completed_at < run_started_at`, 422 with detailed error.

## Observability
- Each ingestion logs `tooling.langsmith.ingest` event containing workspace, experiment_id, dataset hash, artifact hash.
- Metrics: success/failure counts, latency, payload size.
- Evidence pointers appended to `reports/langsmith_eval_export.json` + ops JSONL.

## Security/Residency
- No direct LangSmith API calls; ingestion writes exported results already stored locally.
- Enforce AI runtime layering: any attempt to specify raw provider references triggers validation error referencing AGENTS.md policy.
