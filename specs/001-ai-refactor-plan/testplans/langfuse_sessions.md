# LangFuse Sessions Test Plan

## Coverage
Temporary R&D-only observability sessions created via `/observability/langfuse/sessions` and deleted via `/observability/langfuse/sessions/{sessionId}`.

## Test Matrix
| ID | Scenario | Assertions |
|----|----------|------------|
| LF-001 | Enable session in dev env. | HTTP 201; response body matches schema; `sampling_rate <= 0.25`; kill switch reference required.
| LF-002 | Attempt to enable in prod. | API rejects with 403 + message referencing R&D-only policy.
| LF-003 | TTL enforcement. | Payload missing `retention_days` or exceeding 30 triggers validation error.
| LF-004 | Disable within SLA. | DELETE returns 204; evidence file `reports/langfuse_enable_disable.md` captures timestamps showing <15-minute turnaround.
| LF-005 | Double-disable idempotency. | Second DELETE returns 204 but logs warning; ensures no crash.
| LF-006 | Sampling rate property test. | Hypothesis-driven tests ensure generator never returns value >0.25.

## Tooling
- Use local mocks for LangFuse API; never call vendor directly.
- Evidence recorded in `reports/langfuse_enable_disable.md` per research constraints.
