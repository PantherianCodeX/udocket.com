# LangSmith/LangFuse Telemetry Summary

## LangSmith
- Metrics: pass_rate, latency_ms, cost_usd captured in `reports/langsmith_eval_export.json`.
- Ops JSONL entries planned under `reports/langsmith_smoke.jsonl` once ingestion tests run.
- Residency: data stays in readiness feature dir; ingestion via AI runtime ensures guardrails.

## LangFuse
- Sampling capped at 0.25; TTL 30 days.
- Enable/disable evidence logged in `reports/langfuse_enable_disable.md`.
- Observability: OTLP spans tracked via `agent_*` metrics, LangFuse usage limited to R&D.

## Schema References
- Evaluation evidence schema: `schemas/tooling/evaluation_evidence.schema.json`.
- Observability session schema planned in `drafts/readiness_types.py` (ObservabilitySession dataclass).
