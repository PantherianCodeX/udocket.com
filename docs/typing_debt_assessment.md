# Typing Debt Assessment

Last updated: 2025-10-05.

## Snapshot

- **Pyright diagnostics**: running `pyright --stats` with missing Django/pytest stubs still reports thousands of errors; once the bootstrapper installs those stubs the count falls toward ~700 errors and ~3,500 warnings.
- **Primary pain points**: untyped pytest fixtures (`monkeypatch`, `db`, `settings`), presenter dictionaries that index `object`, and auth helpers that accept arbitrary `*args` / `**kwargs` without protocols.
- **Third-party stub gaps**: upstream coverage for Azure SDK packages and HTMX helpers remains incomplete; track open issues and patch locally when needed.
- **Automation state**: populate `docs/typing/automation_manifest.json` using the template and keep it in sync via `scripts/typing/sync_docs.py` so this document always reflects the latest helper runs.

### Latest Pyright Run
- 2025-10-05T17:38Z — `pyright --stats` → 982 errors, 2051 warnings (vendored stubs now include docstring-rich `mozilla_django_oidc`; remaining errors mostly third-party stub drift plus long-standing project debt).
- 2025-10-05T16:20Z — `pyright --stats` → 912 errors, 1913 warnings (vendored stubs under `typings/vendor`; remaining errors dominated by project debt and third-party modules lacking rich annotations such as `mozilla_django_oidc`).
- 2025-10-05T15:46Z — `pyright --stats` → 879 errors, 1914 warnings (bootstrap now skips missing `types-pytest`/`pytest-stubs`; remaining counts unchanged).
- 2025-10-05T15:41Z — `pyright --stats` → 879 errors, 1914 warnings (bootstrap script failed to install `pytest-stubs`; run executed without refreshed stubs).

### Latest Mypy Run
- 2025-10-05T17:38Z — `mypy .` → 1185 errors (failures dominated by vendored setuptools/DRF stubs plus first-party apps lacking type hints; see pyright section for overlapping hotspots).

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
- [ ] Update `docs/typing/automation_manifest.json` after each helper run and re-sync docs via `scripts/typing/sync_docs.py`.

## Recent Progress

- Agent overrides now flow through frozen dataclasses and mapping proxies, ensuring repeated normalisation produces deterministic inputs.
- Core agent helpers run under `# pyright: strict`, so expanding provider support no longer relies on `Any` payloads.
- Cases, jobs, and artifacts models expose `typed_objects()` and `scoped()` helpers, reducing the cost of migrating call sites to typed querysets.
- The automation helper specs in `docs/typing/automation_helper_specs.md` capture the CLI contract for every fixer so contributors can script their cleanup instead of editing files manually.
- `tests/_typing.py` now exposes shared fixture protocols; run `scripts/typing/annotate_fixtures.py --apply` to keep pytest modules annotated automatically.
- Operations websocket consumers now run with `# pyright: strict`, using channel-layer protocols to remove the remaining `Any` fallthroughs.
- Guardian configuration helpers now run under `# pyright: strict`, with JSON coercion utilities to sanitise provider chains and instruction lists for Celery tasks.
- Vendored stubs live under `typings/vendor` with helper headers that suppress Pyright diagnostics stemming from upstream stub quirks; re-run `scripts/typing/vendor_stubs.py` after updating pip packages to refresh the copies.
- `scripts/typing/vendor_stubs.py` now emits docstring-aware stubs for `mozilla_django_oidc` so pyright/mypy can see local helpers even without first-party hints.
- Typing bootstrapper now treats missing pytest stub packages as optional so the helper records `ok` status without manual intervention.

Keeping this document current helps the team understand where typing debt still lives and which areas should be prioritised in upcoming sprints.
