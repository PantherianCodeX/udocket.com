# Typing Remediation Plan

## Why this matters
Strong typing is now a standing requirement for the Django consolidation roadmap and any incremental code changes. Every pull request that touches Python must maintain or reduce our static-analysis error counts in both `mypy` and `pyright`. Do not merge behavior or refactor work that expands the typing debt.

## Current type-checking baseline
- `mypy --explicit-package-bases apps packages` reports 229 errors across 47 files. Most issues involve stale `type: ignore` directives, unmodeled Django model fields, loose `object` payloads, and configuration helpers with mismatched signatures.
- `pyright` reports roughly 605 errors and 3363 warnings in non-strict mode. A small number of modules (for example, `apps/platform/operations/llm.py`) generate the bulk of diagnostics, largely in the categories `reportUnknownMemberType`, `reportUnknownVariableType`, and `reportUnknownArgumentType`.

These numbers set the ceiling: new work must trend them downward. See `docs/typing_debt_assessment.md` for a module-by-module snapshot and cleanup priorities.

## Root causes to fix
1. **Missing third-party type information** – install or vendor stubs for Django, DRF, pytest, `requests`, Celery, and any other framework that surfaces as `Unknown`.
2. **Manual annotations fighting Django descriptors** – avoid annotating model attributes directly; instead, rely on `django-stubs`, protocols, or helper accessors used only for type checking.
3. **Untyped request/response plumbing** – viewsets and Celery tasks frequently accept `request`, `payload`, or `context` values without structure. Introduce `TypedDict`, `Protocol`, or dataclass definitions and thread them through helper layers.
4. **Loose telemetry helpers** – JSON assemblers return heterogenous dictionaries, leading to `dict[str, Any]` cascades. Model the payloads explicitly and validate optional fields.
5. **Fixture-heavy tests** – pytest fixtures need annotated wrappers or stubs so pyright understands the callable signatures instead of escalating to `Unknown`.
6. **Redundant or stale ignores** – legacy `# type: ignore` comments (especially without error codes) hide actionable problems and should be removed or narrowed.

## Guardrails for ongoing work
- **Touch a module? Type it.** When you modify behavior or perform a refactor, bring that module to the stronger typing bar in the same change.
- **Greenfield code ships typed.** New modules, functions, and classes must include precise annotations and pass both mypy and pyright without blanket ignores.
- **Typing-only PRs stay scoped.** When scheduling cleanup work, focus on annotations, payload modeling, and removing obsolete ignores; avoid unrelated refactors.
- **No "cast-everything" fixes.** Do not widen values to `Any` or lean on `cast` unless paired with concrete schemas or runtime validation.
- **Document remaining gaps.** If you must keep a targeted ignore, narrow it (e.g., `# type: ignore[attr-defined]`) and explain why it remains.
- **Per-module strictness gates.** When a file is clean, add `# pyright: strict` (and, if helpful, a mypy module override) so future edits cannot regress it while the rest of the repo catches up. Track these files in PR descriptions.

## Remediation workflow
1. **Stabilize dependencies**
   - Add or update stub packages (`django-stubs`, `djangorestframework-stubs`, `pytest-stubs`, `types-requests`, etc.). Align `pyrightconfig.json` with the active Django settings module.
2. **Refactor by feature slice**
   - Pick a vertical (jobs telemetry, operations consumers, UI presenters) and introduce helper functions or view models that expose typed interfaces. Land the refactor once `pyright <subpath>` and `mypy` for that slice are clean.
3. **Model Django data correctly**
   - Use `Protocol`/`TypedDict` views or `if TYPE_CHECKING` helpers for models. Leave runtime `models.Field(...)` assignments unannotated.
4. **Tighten request/response layers**
   - Define typed serializers, payload wrappers, and Celery task inputs. Avoid passing raw dictionaries without structure between layers.
5. **Harden tests**
   - Wrap fixtures in typed helper modules or import pytest stubs so pyright understands fixture return values. Annotate lambda fixtures explicitly where unavoidable.
6. **Continuously measure progress**
   - After each chunk, run `pyright <target>` and `mypy --explicit-package-bases <target>`. Record diagnostics in the PR description and ensure the counts fall or stay flat.
7. **Lock in strictness per module**
   - Once a path is clean, annotate it (`# pyright: strict`, mypy overrides) and update `docs/typing_debt_assessment.md` so we build a rolling inventory without blocking unrelated areas.

## Keeping production moving
- Plan typing work in slices that fit sprint capacity; if a module cannot reach strictness without major rework, document the blockers in `docs/typing_debt_assessment.md` and defer the strict marker until the fix is feasible.
- Use per-module strict toggles instead of repo-wide strict mode to avoid halting production while still locking down cleaned files.
- When deadlines conflict with cleanup, isolate functional changes behind feature flags and schedule a follow-up typing task rather than landing risky partial annotations.

## Prompt for future refactor/type tasks

> **Goal**: Bring `<module path>` to zero `pyright` errors (strict) and zero `mypy` errors.
> 
> **Steps**:
> 1. Run `mypy --explicit-package-bases apps packages` and `pyright <module path>`; include the current diagnostics in the task context.
> 2. Install or reference the necessary type stubs for any frameworks you touch. Replace `object`/`Any` placeholders with concrete `TypedDict`, `Protocol`, `Enum`, or dataclass definitions that reflect real payloads.
> 3. Remove blanket `# type: ignore` comments. If an ignore is unavoidable, narrow it to a specific code and document the follow-up task.
> 4. For Django models, avoid redeclaring field attributes; rely on stubs or `TYPE_CHECKING` helpers instead.
> 5. Update or add unit tests when stricter types surface latent bugs (e.g., a `None` path that now raises). Keep behavior changes intentional and covered.
> 6. Re-run mypy and pyright; confirm both pass for `<module path>` and share the command output in the PR description.
> 7. If the typing work exposes a real bug, fix it and add regression coverage rather than masking it.
> 
> **Deliverable**: A reviewable PR that eliminates static-analysis diagnostics for `<module path>`, introduces the necessary typed helpers, and preserves or improves runtime behavior.

Following this checklist keeps the typing initiative focused on durable design improvements instead of superficial fixes.
