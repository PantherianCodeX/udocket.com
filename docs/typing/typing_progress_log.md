# Typing Progress Log

Last updated: 2025-10-05T15:41:06Z (UTC).

This log tracks the multi-wave typing rollout so work can resume from any context window. Update this file whenever a wave changes state or new blockers surface.

## Wave Overview

| Wave | Focus | Status | Notes |
| --- | --- | --- | --- |
| Wave 0 | Environment bootstrap, pyright snapshots, automation manifest hygiene | In progress | `just` missing; `bootstrap_env.py` failed on unavailable `pytest-stubs`; captured fresh `pyright --stats` (879 errors / 1914 warnings) |
| Wave 1 | Shared core libs (`packages/udocket_core` JSON/time/audio/llm, storage helpers) | Planned | Define shared typing aliases module; target strict promotion per module |
| Wave 2 | Agent orchestration (`agents/analyze`, `compose`, `guardian`, `langgraph`) | Planned | Replace ad-hoc dict payloads with frozen dataclasses/TypedDicts |
| Wave 3 | Operations runtime/tasks/payload protocols | Planned | Introduce `apps/platform/operations/typing.py` and typed websocket payloads |
| Wave 4 | UI views & presenters consumption of typed payloads | Planned | Migrate presenters to shared protocols; roll strict markers gradually |
| Wave 5 | Test suite fixtures & dictionaries | Planned | Run fixture annotator, stabilise `tests/_typing.py`, convert dict payloads |

## Immediate Next Steps

1. Resolve stub bootstrap failure (skip or replace `pytest-stubs`, or adjust helper) so Wave 0 can finish cleanly.
2. Draft shared typing alias modules (`packages/udocket_core/typing.py`, `apps/platform/typing.py`).
3. Schedule Wave 1 strictify work, starting with `packages/udocket_core/json_utils.py` and `time_utils.py` once Wave 0 wraps.

## Blockers & Risks

- Pyright snapshot data is stale; Wave 0 must capture current error counts before later waves start.
- Shared typing aliases do not exist yet; multiple modules repeat identical helper types.
- Presenter modules still consume loosely typed websocket payloads; operations work must land first to avoid churn.

## Completed Work

- 2025-10-05: Established five-wave rollout plan and logged focus areas.
- 2025-10-05: Attempted bootstrap (`just typing-bootstrap` missing, `bootstrap_env.py` failed on `pytest-stubs`); recorded pyright snapshot (879 errors / 1914 warnings).
