# LangFuse Enable/Disable SOP (R&D Only)

## Enable Flow
1. Provision workspace credentials from password manager; record public/secret key suffixes.
2. Run `python automation/observability/langfuse_enable.py --env dev --sampling 0.2 --ttl-days 30`.
3. Update `.env` with `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`; note rotation timestamp inline.
4. Record evidence:
   - Screenshot of LangFuse dashboard showing session id.
   - Append JSONL entry to this file detailing timestamp, actor, sampling rate, TTL.
5. Verify OTLP exporters streaming to LangFuse by tailing `logs/otlp-dev.log`.

## Disable Flow (within 15 min SLA)
1. Run `python automation/observability/langfuse_disable.py --env dev`.
2. Revoke credentials in LangFuse UI and remove keys from `.env`.
3. Export traces for archival and upload to object storage bucket referenced in `ops/runbooks/langfuse-rd.md`.
4. Append disable entry to this doc with timestamp + exported artifact path.
5. Notify governance channel with link to disable evidence.

## Evidence Log
| Timestamp (UTC) | Action | Actor | Sampling | TTL (days) | Notes |
|-----------------|--------|-------|----------|------------|-------|
| 2025-11-15T01:00:00Z | enable | user | 0.2 | 30 | session 8d95d4d1-2c88-4a1f-9aa3-5d8b0b191bbe |
| 2025-11-15T01:10:00Z | disable | user | 0.2 | 30 | exported traces to storage://langfuse/dev/2025-11-15 |
