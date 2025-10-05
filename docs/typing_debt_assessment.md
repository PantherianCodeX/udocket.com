# Typing Debt Assessment

Last updated: 2025-10-05.

## Snapshot

- **Pyright diagnostics**: running `pyright --stats` with missing Django/pytest stubs still reports thousands of errors; once the bootstrapper installs those stubs the count falls toward ~700 errors and ~3,500 warnings.
- **Primary pain points**: untyped pytest fixtures (`monkeypatch`, `db`, `settings`), presenter dictionaries that index `object`, and auth helpers that accept arbitrary `*args` / `**kwargs` without protocols.
- **Third-party stub gaps**: upstream coverage for Azure SDK packages and HTMX helpers remains incomplete; track open issues and patch locally when needed.

## Hotspots to Tackle Next

1. **Shared pytest fixtures** – introduce a typed fixture module (`tests/_typing.py`) so individual tests import annotated fixtures instead of duplicating annotations.
2. **Operations pipeline** – migrate runtime helpers (`operations/utils.py`, `runtime.py`) to precise payload objects and adopt the new manager helpers.
3. **UI presenters** – extract shared `TypedDict` structures for job rows, telemetry, and websocket messages to avoid ad-hoc dictionaries.
4. **Accounts/auth variadics** – replace bare `*args` / `**kwargs` signatures with protocols to stop propagating `Unknown` types into authentication flows.

## Action Items

- [ ] Re-run mypy/pyright weekly (with stubs installed) and append the `--stats` output, date, and environment notes to this document.
- [ ] Land the helper backlog from the idempotency playbook (bootstrapper, strict pragma fixer, typed fixtures) and link each helper here once merged.
- [ ] When touching any hotspot module, remove at least one legacy ignore or replace one `Any` usage.
- [ ] File issues for dependencies that still need stub packages or additional annotations.

## Recent Progress

- Agent overrides now flow through frozen dataclasses and mapping proxies, ensuring repeated normalisation produces deterministic inputs.
- Core agent helpers run under `# pyright: strict`, so expanding provider support no longer relies on `Any` payloads.
- Cases, jobs, and artifacts models expose `typed_objects()` and `scoped()` helpers, reducing the cost of migrating call sites to typed querysets.

Keeping this document current helps the team understand where typing debt still lives and which areas should be prioritised in upcoming sprints.
