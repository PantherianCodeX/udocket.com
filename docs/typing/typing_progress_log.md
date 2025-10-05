# Typing Progress Log

Last updated: 2025-10-05T17:38:29Z (UTC).

This log tracks the multi-wave typing rollout so work can resume from any context window. Update this file whenever a wave changes state or new blockers surface.

## Wave Overview

| Wave | Focus | Status | Notes |
| --- | --- | --- | --- |
| Wave 0 | Environment bootstrap, pyright snapshots, automation manifest hygiene | In progress | Bootstrap helper `ok`; vendored stub helper copies pip stubs (now includes docstring-rich `mozilla_django_oidc-stubs`); latest checks: `mypy .` (1185 errors) and `pyright --stats` (982 errors / 2051 warnings) flagged remaining third-party + project debt |
| Wave 1 | Shared core libs (`packages/udocket_core` JSON/time/audio/llm, storage helpers) | Planned | Define shared typing aliases module; target strict promotion per module |
| Wave 2 | Agent orchestration (`agents/analyze`, `compose`, `guardian`, `langgraph`) | Planned | Replace ad-hoc dict payloads with frozen dataclasses/TypedDicts |
| Wave 3 | Operations runtime/tasks/payload protocols | Planned | Introduce `apps/platform/operations/typing.py` and typed websocket payloads |
| Wave 4 | UI views & presenters consumption of typed payloads | Planned | Migrate presenters to shared protocols; roll strict markers gradually |
| Wave 5 | Test suite fixtures & dictionaries | Planned | Run fixture annotator, stabilise `tests/_typing.py`, convert dict payloads |

## Immediate Next Steps

1. Decide on long-term pytest typing strategy (vend local stubs vs keep optional skip) ahead of Wave 5 test cleanup.
2. Draft shared typing alias modules (`packages/udocket_core/typing.py`, `apps/platform/typing.py`).
3. Cull vendor stub diagnostics (setuptools/DRF) or carve them out of type runs so Wave 1 strictify work can focus on first-party modules.

## Blockers & Risks

- Pyright snapshot data is stale; Wave 0 must capture current error counts before later waves start.
- Shared typing aliases do not exist yet; multiple modules repeat identical helper types.
- Presenter modules still consume loosely typed websocket payloads; operations work must land first to avoid churn.

## Completed Work

- 2025-10-05: Established five-wave rollout plan and logged focus areas.
- 2025-10-05: Attempted bootstrap (`just typing-bootstrap` missing, `bootstrap_env.py` failed on `pytest-stubs`); recorded pyright snapshot (879 errors / 1914 warnings).
- 2025-10-05: Updated bootstrap helper to skip missing pytest stub packages; run completes with warnings and records stub gap.
- 2025-10-05: Re-ran bootstrap with optional skips ignored for hashing; helper now records status `ok` without reattempting missing packages.
- 2025-10-05: Added `scripts/typing/vendor_stubs.py` and vendored pip stubs into `typings/vendor` with pyright-suppression headers.
- 2025-10-05: Vendor helper now pulls docstring-inclusive stubs for `mozilla_django_oidc`; captured `mypy .` (1185 errors) and `pyright --stats` (982 errors / 2051 warnings) snapshots for tracking.
- 2025-10-05: Expanded `scripts/typing/check_strict.py` to target manifest modules, focus on single-module diagnostics, and run pyright/mypy independently.
