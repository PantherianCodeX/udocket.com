# Typing Refactor Plan

This document lays out the baseline rules for strengthening static typing across the uDocket stack. Every change that touches Python code must either preserve the current typing signal or improve it. Treat the guidance here as the canonical checklist before merging.

## Objectives

1. **Protect the existing gating** – keep mypy and pyright warning counts flat or lower. No new `# type: ignore` comments without an accompanying TODO pointing to a follow-up.
2. **Prioritise high-churn modules** – whenever you edit a file, tighten its annotations, add `TypedDict`/`Protocol`s, or migrate to dataclasses where it makes the intent clearer.
3. **Surface typed APIs** – all new helper functions should expose typed signatures and return values. Avoid `Any` and bare dictionaries in public interfaces.
4. **Measure progress** – record notable wins (modules migrated, ignores removed) directly in PR descriptions so we can track velocity against quarterly typing targets.

## Workflow Checklist

- Run `just lint-types` (or the equivalent mypy/pyright commands) before submitting.
- Replace loose `dict`/`list` usage with typed containers (`dict[str, object]`, `list[JobRow]`, etc.).
- Share common shape definitions from `typing` modules rather than inlining anonymous dictionaries.
- Prefer `@dataclass` or `NamedTuple` where we shuttle structured data between layers (e.g., job metadata, websocket payloads).
- Keep third-party stubs in sync: add/update `types-` wheels in `pyproject.toml` when a dependency starts producing `Any` spillage.
- When the same clean-up appears in multiple reviews (for example, adding `# pyright: strict` or wiring `typed_objects()`), log the pattern in `docs/typing-idempotency-strategy.md` and automate it before repeating the manual edit.

## Rollout & Reporting

- Maintain this document as the single source of truth; if you add a new typing initiative, document the goal and success criteria here.
- Update `docs/typing_debt_assessment.md` monthly with the current ignore counts and hotspots.
- Raise any structural blockers (missing stubs, legacy modules that require larger rewrites) in the engineering stand-up so they can be scheduled.

Staying disciplined about the plan above keeps us on track for fully typed services without slowing feature velocity.
