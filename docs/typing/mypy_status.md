# mypy Status Snapshot

This snapshot tracks the current mypy baseline and complements the broader strategy in `docs/typing_refactor_plan.md` and `docs/typing_debt_assessment.md`.

## Baseline metrics
- Command: `mypy --explicit-package-bases apps packages`
- Current result: **229 errors across 47 files** (latest run shared on 2024‑xx‑xx). Update this count whenever the command is re-run so we can chart progress toward zero.

## High-volume error buckets
1. **Stale `type: ignore` pragmas** – especially in admin modules, auth helpers, and management commands. With `--warn-unused-ignores`, these now surface as actionable errors.
2. **Untyped third-party integrations** – missing stubs for Django, DRF, `requests`, and Celery trigger "missing library stub" failures and propagate `Any` downstream.
3. **Django model field annotations** – redeclaring model attributes as `str`/`datetime` conflicts with descriptor types and masks nullable semantics (`Optional[...]`).
4. **Loose payload plumbing** – presenter, guardian, and operations flows still treat API payloads as `object`/`dict[str, Any]`, producing attribute/indexing errors.
5. **Configuration helpers** – `config/settings.py` accepts `_env_file`/`_env_file_encoding` that are absent from the current `Settings` signature, generating incompatible-call errors.

## Cleanup playbook
- Install/upgrade stubs (`django-stubs`, `djangorestframework-stubs`, `types-requests`, Celery stubs) so we remove the "missing stub" noise.
- When editing a module for behavior or refactor work, raise it to the stricter mypy bar in the same change—typed helpers, precise return types, and cleaned ignores.
- Stage dedicated "typing cleanup" PRs for modules without planned feature work; keep them focused on annotations, data modeling, and unused-ignore removal.
- Prefer modeling real data structures (TypedDicts, Protocols, dataclasses) over sprinkling `cast(Any, …)`.
- Run `mypy --explicit-package-bases apps packages` before/after each logical chunk and record the new totals here.

## Tracking template
```
| Date       | Errors | Files | Notes |
|------------|--------|-------|-------|
| 2024-xx-xx |   229  |   47  | Baseline snapshot after enabling warn_unused_ignores |
```
Update the table with each meaningful reduction so we can demonstrate progress alongside the pyright strictness work.
