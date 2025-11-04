# Contributing Guidelines

This project treats contributor experience and code quality as first-class requirements. Please align with the practices below when opening pull requests or sharing patches.

## Imports & shared packages

- Shared utilities live under `packages.udocket_common.*`. Import helpers from that package rather than re-implementing them in app-specific modules.
- When a helper becomes broadly useful (e.g., identifier generation, time formatting), promote it into `packages.udocket_common` together with tests.

## Dependency hygiene

- Avoid “optional” imports. If a module is needed, add it to the appropriate `pyproject.toml` / lockfile group and commit the change.
- Scripts and tooling should fail fast with a clear error when a dependency is absent rather than silently degrading behaviour.

## Typing & quality gates

- Type checking is enforced via:

  ```bash
  make typing.run          # pyright + mypy + strict enforcement scripts
  uv run --project apps/platform --extra dev typewiz audit \
    --mode current \
    --manifest reports/typing/typing_audit.json \
    --readiness \
    --readiness-status blocked \
    --readiness-status ready  # optional detailed report
  ```

- Use Typewiz readiness reports to identify directories that are ready for stricter enforcement and to track regression risks. Do not introduce new `# type: ignore` comments without filing a follow-up ticket that references the typing roadmap.
- All new modules should be `pyright: strict` or satisfy the stricter project configuration.

## Docs tooling workflow

- Generate and lint docs via the curated Make targets:

  ```bash
  make docs.lint
  make docs.build
  make docs.test.coverage   # enforces ≥90% coverage for doc tooling
  ```

- Mermaid sources live inside a `diagrams/` folder beside the owning document (for example, `docs/platform/guardian/diagrams/guardian-judgment-flow-v1.mmd`). Rendered assets are produced via `packages/udocket_docs/src/doc_tools/render_mermaid.py` and published under `build/diagrams/...`.
- Theme overrides (CSS/JS) live in `docs/assets/`; build artefacts belong in `packages/udocket_docs/build/`.

## Tests & coverage

- Core quality commands (all wrap uv and respect the shared env):

  ```bash
  make all.test          # common → core → platform → docs
  make all.lint          # ruff lint + format checks for code packages
  make all.type          # mypy + pyright across packages
  make all.fix           # apply ruff format + autofixes (when needed)
  make all.export-reqs   # regenerate requirements/*.txt (pre-commit runs this)
  ```

- Per-project commands (examples):

  ```bash
  make platform.test      # pytest (platform)
  make common.test        # pytest (packages/udocket_common)
  make core.test          # pytest (packages/udocket_core)
  make docs.test          # pytest (docs toolbox in container)

  make platform.lint      # ruff check + format --check
  make platform.type      # mypy + pyright

  make common.lint.ruff   # ruff only
  make common.format      # ruff format code layout
  make core.type.mypy     # targeted checks
  ```

- Target ≥90 % coverage per module. Critical shared packages (e.g., `packages.udocket_common`) must meet or exceed this target before changes are merged.
