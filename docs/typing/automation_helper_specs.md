# Typing Automation Helper Specs

This document spells out the automation we rely on to keep typing passes repeatable. Each helper includes the CLI contract, expected guardrails for idempotency, and hints for wiring it into CI and the developer workflow.

## 1. Bootstrap Environment (`scripts/typing/bootstrap_env.py`)
- **Purpose**: Ensure Django/DRF/pytest stubs plus internal stub overlays are available before running static checks.
- **CLI**: `python scripts/typing/bootstrap_env.py [--venv <path>] [--check-only]`
- **Workflow**:
  1. Resolve the target virtualenv (default: `.venv`).
  2. Verify `pip` is available; bail with actionable error if not.
  3. Install (or upgrade) stub wheels listed in `pyproject.toml` / `requirements-dev.txt`.
  4. Confirm required overlay paths in `pyrightconfig.json` exist; create empty directories when missing.
- **Idempotency checks**: The script records an install hash (package + version) in `.cache/typing/bootstrap.json`. Reruns compare hashes and skip unchanged packages.
- **Exit codes**: `0` on success/no-op, `10` if pip is missing, `20` if locking fails.
- **Validation**: Automatically run `pyright --stats` post-install (optional `--no-stats`). Append snapshot to `docs/typing_debt_assessment.md` via the document synchroniser.

## 2. Strictify (`scripts/typing/strictify.py`)
- **Purpose**: Idempotently add `# pyright: strict` to modules/directories that are clean.
- **CLI**: `python scripts/typing/strictify.py src/<path> [--dry-run] [--check]`
- **Behaviour**:
  - Accept glob-style inputs or module paths.
  - Skip files already marked strict; retain shebangs and encoding pragmas.
  - Optionally run `pyright --verifytypes` for the target module when `--check` is set.
- **Implementation notes**:
  - Use LibCST to preserve formatting.
  - Maintain a manifest `docs/typing/strict_manifest.json` with `module`, `last_verified`, and `command` fields.
- **Idempotency**: The script sorts manifest entries and overwrites the file atomically; repeated runs produce identical output.

## 3. Manager Codemod (`scripts/typing/manager_codemod.py`)
- **Purpose**: Standardise the `typed_objects()` + `scoped()` helper pattern across Django models.
- **CLI**: `python scripts/typing/manager_codemod.py apps/platform/cases/models.py [--apply|--preview]`
- **Algorithm**:
  1. Detect custom managers or `objects` attribute overrides.
  2. Generate helper methods using the shared mixin (`apps.platform.utils.typing.TypedManagerMixin`).
  3. Insert canonical imports and update call sites if `--apply` is set.
- **Idempotency**: The codemod derives helper names from the model name; rerunning it does not duplicate methods.
- **Verification hooks**: Emits a summary of updated models; `--preview` shows diffs without touching disk.

## 4. Pytest Fixture Annotator (`scripts/typing/annotate_fixtures.py`)
- **Purpose**: Add typed fixtures (`monkeypatch`, `settings`, `db`, `client`, etc.) across the test suite.
- **CLI**: `python scripts/typing/annotate_fixtures.py tests/ [--update-imports]`
- **Implementation**:
  - Parse files with LibCST, identify fixture parameters lacking annotations, and add imports from `tests._typing`.
  - Insert `from tests._typing import MonkeyPatch, SettingsFixture, ...` where required.
- **Idempotency**: Maintains a sorted import block and recognises already-annotated fixtures to avoid duplication.
- **Post-check**: Optionally run `pytest --maxfail=1 --disable-warnings -q tests/<subset>` to ensure behaviour unchanged.

## 5. Stub Synchroniser (`scripts/typing/check_stubs.py`)
- **Purpose**: Keep project stub overlays aligned with runtime modules.
- **CLI**: `python scripts/typing/check_stubs.py [--fix]`
- **Key steps**:
  - Read `pyrightconfig.json` for `stubPath` entries.
  - Ensure each overlay file has a matching runtime module.
  - When `--fix` is supplied, generate minimal `.pyi` skeletons based on inspected runtime signatures.
- **Reporting**: Outputs a Markdown summary that can be appended to `docs/typing_debt_assessment.md`.
- **Idempotency**: Uses deterministic ordering and hashing; regenerated stubs contain a header comment with the generator version.

## 6. Document Synchroniser (`scripts/typing/sync_docs.py`)
- **Purpose**: Regenerate sections of the typing docs from machine-readable manifests.
- **CLI**: `python scripts/typing/sync_docs.py docs/typing/automation_manifest.json`
- **Behaviour**:
  - Read manifest fields (`pyrightStats`, `strictModules`, `helpers`, etc.).
  - Rewrite tagged regions within `typing-roadmap.md`, `typing_debt_assessment.md`, and `typing-idempotency-playbook.md`.
  - Preserve manual notes outside the tagged regions.
- **Idempotency**: The manifest is sorted, and the sync script uses stable formatting.
- **Integration**: Pair with a pre-commit hook to ensure docs reflect the latest manifest before pushing.

## 7. Stage Override Linter (`scripts/typing/lint_stage_overrides.py`)
- **Purpose**: Validate organisation-provided stage maps using the `StageOverride` dataclass.
- **CLI**: `python scripts/typing/lint_stage_overrides.py config/analyze_defaults.json [--fix]`
- **Features**:
  - Ensures provider/model names resolve via `_normalize_providers`.
  - Optionally writes back normalised JSON with deterministic ordering.
  - Emits actionable diagnostics for disallowed providers or token limits.
- **Idempotency**: Sorted output and canonical ordering guarantee identical rewrites on repeated runs.

## CI & Tooling Integration
- Add a `just typing-bootstrap` recipe that wraps the bootstrapper and re-runs `pyright --stats`.
- Introduce `just typing-strictify MODULE=<path>` to promote clean modules to strict mode.
- Configure GitHub Actions to run `scripts/typing/sync_docs.py` and commit regenerated docs if the manifest changed (using a bot account).
- Include the bootstrapper and document synchroniser in the devcontainer `postCreateCommand` so editors start with stubs in place.

## Manifest Schema
- Store automation state in `docs/typing/automation_manifest.json` with the structure described in `docs/typing/automation_manifest_template.json`:
  - `pyrightStats`: command, files, errors, warnings, recordedAt.
  - `helpers`: array with helper name, version, lastRun, status.
  - `strictModules`: list of `{ "path": "...", "verifiedAt": "..." }` entries.
  - `notes`: free-form strings for upcoming work.

## Implementation Tips
- Prefer LibCST or Bowler for codemods to preserve formatting.
- Run helper unit tests under `tests/typing_helpers/` to keep automation reliable.
- When publishing helpers, include `--dry-run`/`--check` flags and document them here.
- Whenever a helper graduates from proposal to implementation, update this file and the manifest template with the final CLI signature.

By treating these helpers as first-class tooling, we can push toward pyright strict mode without manual, repetitive edits.
