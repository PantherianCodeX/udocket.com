# Typing Debt Assessment

Last updated: _please update this timestamp when you touch the file_.

## Snapshot

- **Open `# type: ignore` comments**: _fill in count when you run mypy_
- **Modules still untyped**:
  - `apps/platform/operations/tasks.py`
  - `apps/platform/jobs/views.py`
  - `apps/platform/ui/views/*` (work in progress; see incremental annotations on table helpers).
- **Third-party stub gaps**: investigate upstream type hints for Azure SDK packages and HTMX helpers.

## Hotspots to Tackle Next

1. **Operations pipeline** – migrate runtime helpers (`operations/utils.py`, `runtime.py`) to precise payload objects.
2. **UI presenters** – extract shared `TypedDict` structures for job rows, telemetry, and websocket messages to avoid ad-hoc dictionaries.
3. **Tests** – gradually adopt `typing` helpers in pytest fixtures to avoid cascading `Any` usage.

## Action Items

- [ ] Re-run mypy/pyright weekly and record the summary numbers here.
- [ ] When touching any module listed above, remove at least one legacy ignore or replace one `Any` usage.
- [ ] File issues for dependencies that need stub packages.

Keeping this document current helps the team understand where typing debt still lives and which areas should be prioritised in upcoming sprints.
