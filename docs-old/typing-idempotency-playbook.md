# Typing Idempotency Playbook

_Last updated: 2025-10-05_

This playbook captures the conventions that keep repeated typing passes safe to re-run. When a script or helper is rerun, it should land the same changes (or no changes at all) so we avoid churn in review cycles.

## Recent Commit Themes (last few typing-focused PRs)
- Analyze agent overrides are now normalised via frozen dataclasses, giving us deterministic inputs for stage configuration.
- Shared agent helpers coerce JSON payloads into typed containers, letting us centralise fixes instead of scattering casts.
- Django models expose `typed_objects()` and `scoped()` helpers, so moving code to typed querysets no longer requires bespoke casts per model.
- The typing roadmap documents strict-mode expectations for agents and managers, providing the policy cover needed to enforce the helpers above.

## Diagnostic Snapshot
- Running `pyright --stats` without Django/pytest stubs still triggers a flood of missing-import errors. Once the bootstrap script installs those stubs, the count falls back toward the ~700 error / 3,500 warning baseline recorded in earlier strict-mode pushes.
- Remaining errors typically fall into a handful of buckets (untyped fixtures, managers, and presenter dictionaries), making them ideal candidates for targeted automation.

## Idempotent Acceleration Strategy
1. **Bootstrap first, always** – run `python scripts/typing/bootstrap_env.py` (or `just typing-bootstrap`) before touching typing debt so pyright sees the correct stubs. The script should report a no-op when hashes match.
2. **Codemod managers** – use `python scripts/typing/manager_codemod.py --apply` to introduce `typed_objects()`/`scoped()` helpers. Rerunning the codemod is safe because helper names are derived from the model.
3. **Promote modules to strict** – once warnings are cleared, call `python scripts/typing/strictify.py <module>` to add `# pyright: strict` and update the strict manifest.
4. **Lint stage overrides** – validate overrides via `python scripts/typing/lint_stage_overrides.py --fix` so configuration rewrites remain deterministic and leverage the new `StageOverride` dataclass.
5. **Sync documentation** – regenerate roadmap and debt snapshots by running `python scripts/typing/sync_docs.py docs/typing/automation_manifest.json` after updating the manifest.

## Helper & Tooling Blueprints
The detailed CLI contract and implementation notes for every helper live in `docs/typing/automation_helper_specs.md`. Treat that file as the source of truth when building or updating automation.

### Quick Command Palette
- `just typing-bootstrap` → wraps `scripts/typing/bootstrap_env.py` and records `pyright --stats`.
- `just typing-strictify MODULE=...` → runs the strictifier in `--check` mode first, then applies on success.
- `just typing-annotate-fixtures` → executes the fixture annotator across `tests/` and reruns focused pytest targets.
- `just typing-sync-docs` → regenerates documentation sections from the automation manifest.

### Automation Manifest
- Maintain `docs/typing/automation_manifest.json` (see template in `docs/typing/automation_manifest_template.json`).
- Run `scripts/typing/sync_docs.py` after updating the manifest so this playbook, the roadmap, the debt assessment, and `automation_status.md` stay in sync.
- Record helper versions and last-run timestamps to make regression hunting trivial.

## Delivered Helpers
- `scripts/typing/bootstrap_env.py` – prepares stub packages and records pyright stats.
- `scripts/typing/strictify.py` – idempotently injects `# pyright: strict` into clean modules and updates the strict manifest.
- `scripts/typing/annotate_fixtures.py` – annotates common pytest fixtures and ensures `tests/_typing.py` is imported.
- `scripts/typing/manager_codemod.py` – reports (and optionally adds) `typed_objects()`/`scoped()` helpers to Django models.
- `scripts/typing/check_stubs.py` – verifies stub overlays exist and can scaffold missing `.pyi` skeletons.
- `scripts/typing/lint_stage_overrides.py` – normalises analyze stage overrides via the new `StageOverride` dataclass.
- `scripts/typing/sync_docs.py` – generates `docs/typing/automation_status.md` from the automation manifest.

## Helper & Tooling Backlog
- **Strict-mode telemetry** – extend `check_stubs.py` to diff stub coverage and raise when runtime modules go missing.
- **Telemetry schema stubs** – generate stub overlays via `scripts/typing/check_stubs.py --fix` so telemetry payloads remain strongly typed.
- **Manager coverage report** – extend `scripts/typing/manager_codemod.py --check` to emit coverage metrics per app and update the automation manifest.
- **Doc synchroniser hook** – wire `scripts/typing/sync_docs.py` into a pre-commit check so stale numbers never land.

## Next Steps
- Implement the helper specs, add `just` aliases, and commit the generated `automation_manifest.json` alongside documentation updates.
- Schedule a follow-up audit once the error count drops below 500; use the manifest to decide which helper delivers the next biggest win (operations tasks, presenters, UI tests).
