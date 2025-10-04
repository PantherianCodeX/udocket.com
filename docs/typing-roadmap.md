# Typing Roadmap

## Summary of Current Issues
- `pyright` currently reports ~600 errors and ~3,300 warnings, so we cannot enable strict blocking yet.
- The vast majority of errors come from pytest fixtures in `tests/`, where parameters such as `monkeypatch`, `db`, and `settings` lack annotations, and helper lambdas capture `Unknown` types.
- Django and DRF helpers (e.g., `APIClient`, model managers) surface as `Unknown` because stub packages are missing; `.objects.create` chains and response objects are therefore untyped.
- Several UI presenter tests instantiate `dict[str, Any]` structures and access nested members as `object`, which triggers index/type errors under strict mode.

## Recommended Strategy Before Enforcing Strict Mode
1. **Add missing stub packages**
   - Install `django-stubs` and `djangorestframework-stubs` (bundled with the platform requirements) so Pyright recognizes Django managers and DRF clients. PyPI does not currently publish `pytest-django` stubs, so focus on annotating fixtures directly until an official stub package is available.
   - Configure `pyrightconfig.json` to include any local stub directories if we add custom protocol definitions.

2. **Annotate pytest fixtures explicitly**
   - Import `from _pytest.monkeypatch import MonkeyPatch` and annotate fixture arguments to eliminate `Unknown` parameters (for example, in `tests/platform/test_job_runtime_context.py`).
   - For shared fixtures (`db`, `settings`, `client`), create typed wrapper fixtures in `conftest.py` that return concrete protocol types so individual tests remain tidy.

3. **Refactor helper lambdas into typed callables**
   - Replace inline lambdas that append tuples/dicts with small inner functions using `TypedDict`/`Protocol` definitions, which keeps event payload shapes explicit and reduces `Unknown` propagation.

4. **Model structured payloads**
   - Introduce `TypedDict` classes for the nested dictionaries used in presenter tests (`tests/ui/test_llm_presenters.py`, `tests/ui/test_organization_settings.py`) so Pyright understands the expected keys and removes `object` index errors.

5. **Tighten runtime APIs gradually**
   - Start with leaf modules (e.g., anything under `packages/udocket_core/`) by adding return types and generics while running Pyright in `--warnings` mode; once they pass, raise their directories to `strict` via per-module config.

6. **Gate strict mode**
   - Update CI to fail on Pyright errors only after the above buckets are cleared. Until then, keep strict mode locally but allow warnings so contributors can chip away iteratively.

## Patterns Established (2024-03 Typing Pass)
- **Nullable model fields** – When a Django field uses `null=True`, annotate the descriptor with `Optional[...]` for both the set and get generics (e.g., `models.TextField[Optional[str], Optional[str]]`). This satisfies the mypy-django plugin and prevents the “generic get type parameter is not optional” error.
- **Manager helpers** – Prefer `QuerySet.as_manager()` or a thin subclass that casts `super().get_queryset()` instead of silencing overrides. This keeps `objects` typed as `Manager[Model]` for Pylance/Pyright while still exposing typed helper methods (see `apps/platform/jobs/models.py` for the pattern).
- **Stub overlays** – Project stubs live under `typings/`. Only include files that need overriding (e.g., `typings/django/db/models/base.pyi`) and avoid empty `__init__.pyi` files that would shadow upstream stubs. Ensure `pyrightconfig.json`’s `stubPath` points to this directory so both CLI and Pylance pick it up.
- **Tooling parity** – The devcontainer and VS Code recommendations now install `ms-python.mypy-type-checker`. Keep per-editor settings aligned with `pyrightconfig.json` so pyright and pylance share the same strict configuration.

## Prompt for Refactoring With Strong Typing in Mind
Use the following prompt with reviewers or AI assistants to ensure we refactor rather than silence diagnostics:

> We are refactoring the uDocket codebase to enable Pyright strict mode. For each file you touch:
> 1. Identify why Pyright reports `Unknown` or `Any` types and eliminate the root cause by adding concrete annotations, helper protocols, or typed fixtures. Do **not** silence diagnostics.
> 2. When a lambda or ad-hoc dict is flagged, convert it into a named function or `TypedDict`/`Protocol` with explicit types.
> 3. Prefer refactoring toward reusable utilities (e.g., shared fixtures in `conftest.py`) rather than scattering repetitive annotations across tests.
> 4. If third-party stubs are missing, add the appropriate stub package and update imports accordingly.
> 5. After changes, run `pyright` and relevant pytest modules to confirm both type safety and behavior remain intact.
>
> Deliverables must include a brief summary of the refactor, updated tests if behavior changes, and confirmation that Pyright reports zero errors in the touched scope.

This roadmap ensures we clear the backlog of type errors by tightening abstractions instead of suppressing diagnostics, keeping the codebase ready for strict enforcement.
