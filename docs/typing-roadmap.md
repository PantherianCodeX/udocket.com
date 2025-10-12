# Typing Roadmap

## Summary of Current Issues
For day-to-day execution status, see `docs/typing/typing_progress_log.md`, which records the active waves and any blockers so the effort can resume quickly after context resets.
- Without the stub bootstrapper, `pyright` still reports well over a thousand errors due to missing Django/pytest stubs; once the stubs are present locally the count drops toward the ~700 error / ~3,500 warning band tracked in recent runs, so we cannot enable strict blocking yet.
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

## March 2025 Progress & New Guidance
- `packages/udocket_core/agents/common` now runs clean under `pyright` thanks to explicit JSON aliases and payload guards. Reuse the new helpers (`JSONValue`, `_ensure_json_object`, `_content_from_*`) when wiring additional agents so downstream code never handles `Any` payloads from Azure.
- When normalizing third-party responses, prefer the pattern used in `common/azure_client.py`: convert unknown mappings into concrete `dict[str, object]`, gate every branch with `_is_json_structure`, and coerce payloads via `_coerce_json_value`. This keeps telemetry dictionaries JSON-serialisable without sprinkling `cast` calls across consumers.
- For append-only storage helpers (`append_jsonl`, audit writers, etc.), accept `Mapping[str, JSONValue]` rather than wide `Dict[str, Any]`. If a caller passes a mutable mapping, materialise it once before serialisation as shown in `common/io.py` to keep write paths deterministic.
- When updating typing in other agent folders, start by hoisting shared aliases into `packages/udocket_core/agents/common/io.py` (or adding new ones there) so that follow-on modules inherit consistent types without redefining local `TypedDict`s.
- Manual retries and request fallbacks should stay in the runtime wrapper (`AzureChatClient._chat`). Avoid folding error handling into per-agent code; instead expose structured exceptions with typed payloads so Celery tasks can log without `Any` casts.
- `packages/udocket_core/agents/analyze_lib.py` now uses shared helpers (`coerce_object_dict`, `_normalize_providers`) and typed `StageModelInfo`/`StageCatalogEntry` structures. Stage configuration inputs are normalised to `dict[str, object]`, so future contributors should preserve that pattern when adding new stage options or provider overrides.
- Core JSON helpers now expose `coerce_object_dict` in `packages/udocket_core/utils.json.py`; prefer this when normalising metadata or provider payloads so every consumer shares the same str-key conversion instead of duplicating casts.
- Use `normalize_json_object` when you need stricter key/value hygiene (trim blanks, drop nullish entries) without hand-written loops. LLM admin metadata normalisation relies on it, so mirror the helper instead of rolling bespoke filters.
- When reading organization defaults (`config/analyze_defaults.json`), call `_coerce_int`/`_coerce_float` rather than sprinkling `int(...)`/`float(...)` coercions. This keeps environment overrides predictable and Pyright-friendly.

## October 2025 Idempotency & Automation Focus
- Stage overrides now flow through `StageOverride` dataclasses, giving us deterministic provider/model selection and making it safe to re-run normalisation scripts.
- The new **Typing Idempotency Playbook** (`docs/typing-idempotency-playbook.md`) captures helper patterns and a backlog of automation ideas (bootstrap script, manager codemods, fixture shims) so contributors reach for tooling first.
- The companion **Typing Idempotency Strategy** memo (`docs/typing-idempotency-strategy.md`) records recent typing commits, error snapshots, and the helper roadmap. Reference it when planning new automation work before touching high-churn modules.
- When introducing new structured payloads, prefer frozen dataclasses or mapping proxies to guarantee that repeated normalisation yields identical output. This keeps diffs stable even when automation rewrites configs multiple times.
- Detailed CLI contracts for every helper live in `docs/typing/automation_helper_specs.md`; wire them up via `just` aliases so onboarding boils down to running `just typing-bootstrap`, `just typing-strictify MODULE=...`, and `just typing-sync-docs`.
- Track automation state in `docs/typing/automation_manifest.json` (template in `docs/typing/automation_manifest_template.json`) and regenerate this roadmap with `scripts/typing/sync_docs.py` whenever the manifest changes.

## November 2025 Tooling Discipline
- Always start a typing pass with the combined checker: `python scripts/typing/check_strict.py --tool both`. This reports deltas for pyright and mypy together so we do not lose ground on modules that were previously clean in only one tool.
- Follow up with targeted runs (`--tool pyright` / `--tool mypy` plus `--module` selectors) when iterating on fixes. The focused mode keeps output short and guards against regressions if we pause mid-refactor. Do not re-run repo-wide checks during confirmations unless you explicitly note the broader scope.
- When a module needs heavier reshaping, lean on the automation helpers in `scripts/typing/` first (for example, `strictify.py`, `manager_codemod.py`, `annotate_fixtures.py`) to keep refactors idempotent. Only fall back to manual edits if the helpers cannot express the change yet, and remember to extend the helper afterward.
- Document any newly-required helper combinations (e.g., bootstrap + strictify) in the PR description and update the playbook so future contributors can rerun the same sequence without guesswork.
- Pair the typing sweeps with targeted pytest runs (`pytest <path/to/test>.py`) so we validate behaviour without hammering the entire suite between edits; keep the full run for profiling or release checkpoints. Capture the exact commands in the PR body for reproducibility.

## Patterns Established (2024-03 Typing Pass)
- **Nullable model fields** – When a Django field uses `null=True`, annotate the descriptor with `Optional[...]` for both the set and get generics (e.g., `models.TextField[Optional[str], Optional[str]]`). This satisfies the mypy-django plugin and prevents the “generic get type parameter is not optional” error.
- **Manager helpers** – Prefer `QuerySet.as_manager()` or a thin subclass that casts `super().get_queryset()` instead of silencing overrides. This keeps `objects` typed as `Manager[Model]` for Pylance/Pyright while still exposing typed helper methods (see `apps/platform/jobs/models.py` for the pattern).
- **Scoped managers** – Expose a classmethod like `Case.scoped()` that returns the typed manager (cast from `objects`). This keeps runtime behavior identical while giving Pyright a strongly-typed handle for helpers such as `for_user` without violating Django’s base `Model.objects` signature.
- **Stub overlays** – Project stubs live under `typings/`. Only include files that need overriding (e.g., `typings/simple_history/models.pyi`) and avoid empty `__init__.pyi` files that would shadow upstream stubs. Ensure `pyrightconfig.json`’s `stubPath` points to this directory so both CLI and Pylance pick it up when overlays are present.
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
