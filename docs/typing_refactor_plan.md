# Typing Refactor Plan

This document lays out the baseline rules for strengthening static typing across the uDocket stack. Every change that touches Python code must either preserve the current typing signal or improve it. Treat the guidance here as the canonical checklist before merging.

## Objectives

1. **Protect the existing gating** – keep mypy and pyright warning counts flat or lower. No new `# type: ignore` comments without an accompanying TODO pointing to a follow-up.
2. **Prioritise high-churn modules** – whenever you edit a file, tighten its annotations, add `TypedDict`/`Protocol`s, or migrate to dataclasses where it makes the intent clearer.
3. **Surface typed APIs** – all new helper functions should expose typed signatures and return values. Avoid `Any` and bare dictionaries in public interfaces.
4. **Measure progress** – record notable wins (modules migrated, ignores removed) directly in PR descriptions so we can track velocity against quarterly typing targets.

## Workflow Checklist

- Run the combined typing sweep before touching code: `python scripts/typing/check_strict.py --tool both`. This keeps mypy and pyright in lockstep and prevents regressions in modules that were previously pyright-clean only.
- After the sweep, always narrow follow-up runs to the modules you touched: `python scripts/typing/check_strict.py --tool pyright --module apps/platform/ui/views/contexts.py` (repeat for mypy). Never re-run repository-wide pyright/mypy during a confirmation pass unless you’re profiling.
- Exercise the smallest relevant pytest slice (for example, `pytest tests/ui/test_llm_settings.py`) while iterating. Save full-suite runs for profiling or release candidates so typing passes stay fast.
- Record the exact commands you executed (including `--module` selectors) in the PR summary so reviewers can replay the same targeted checks.
- Run `just lint-types` (or the equivalent mypy/pyright commands) before submitting.
- Replace loose `dict`/`list` usage with typed containers (`dict[str, object]`, `list[JobRow]`, etc.).
- Share common shape definitions from `typing` modules rather than inlining anonymous dictionaries.
- Prefer `@dataclass` or `NamedTuple` where we shuttle structured data between layers (e.g., job metadata, websocket payloads).
- Keep third-party stubs in sync: add/update `types-` wheels in `pyproject.toml` when a dependency starts producing `Any` spillage.
- When the same clean-up appears in multiple reviews (for example, adding `# pyright: strict` or wiring `typed_objects()`), log the pattern in `docs/typing-idempotency-strategy.md` and automate it before repeating the manual edit.
- Check `docs/typing/automation_helper_specs.md` before hand-editing; if a helper exists (or should exist), extend it instead of applying one-off fixes.

## Rollout & Reporting

- Maintain this document as the single source of truth; if you add a new typing initiative, document the goal and success criteria here.
- Update `docs/typing_debt_assessment.md` monthly with the current ignore counts and hotspots.
- Raise any structural blockers (missing stubs, legacy modules that require larger rewrites) in the engineering stand-up so they can be scheduled.

Staying disciplined about the plan above keeps us on track for fully typed services without slowing feature velocity.
