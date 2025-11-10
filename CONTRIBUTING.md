# Contributing Guidelines

This project treats contributor experience and code quality as first-class requirements. Please align with the practices below when opening pull requests or sharing patches.

## Imports & shared packages

- Shared utilities live under `packages.common.*`. Import helpers from that package rather than re-implementing them in app-specific modules.
- When a helper becomes broadly useful (e.g., identifier generation, time formatting), promote it into `packages.common` together with tests.

## Environment setup & dependency hygiene

- The shared virtual environment lives at `./.venv`. Both the devcontainer and local development shell activate that environment.
- After cloning (or whenever a `uv.lock` changes), run `uv sync --project apps/platform --extra dev --frozen` (or `scripts/udocket uv platform sync`) to hydrate the platform toolchain.
- Docs tooling has its own dependency group: keep it current via `scripts/udocket uv doctools sync`.
- Always activate the environment in your shell (`source .venv/bin/activate`) so `python`, `pip`, `udocket`, and VS Code all point at the same interpreter.
- Avoid “optional” imports. If a module is needed, add it to the appropriate `pyproject.toml` / lockfile group and commit the change.
- Scripts and tooling should fail fast with a clear error when a dependency is absent rather than silently degrading behaviour.

## Typing & quality gates

- Type checking is enforced via:

  ```bash
  scripts/udocket typing run          # pyright + mypy + strict enforcement scripts
  scripts/udocket typewiz audit --mode current --readiness
  ```

- Use Typewiz readiness reports to identify directories that are ready for stricter enforcement and to track regression risks. Do not introduce new `# type: ignore` comments without filing a follow-up ticket that references the typing roadmap.
- All new modules should be `pyright: strict` or satisfy the stricter project configuration.

## Docs tooling workflow

- Generate and lint docs via the curated CLI targets:

  ```bash
  scripts/udocket docs lint
  scripts/udocket docs build
  scripts/udocket docs test coverage   # enforces ≥90% coverage for doc tooling
  ```

- Mermaid sources live inside a `diagrams/` folder beside the owning document (for example, `docs/platform/guardian/diagrams/guardian-judgment-flow-v1.mmd`). Rendered assets are produced via `packages/docs_tooling/src/doc_tools/render_mermaid.py` and published under `build/diagrams/...`.
- Theme overrides (CSS/JS) live in `docs/assets/`; build artefacts belong in `packages/docs_tooling/build/`.

## Tests & coverage

- Unit tests run via `pytest`:

  ```bash
  scripts/udocket tests all
  scripts/udocket tests pytest-cov
  ```

- Target ≥90 % coverage per module. Critical shared packages (e.g., `packages.common`) must meet or exceed this target before changes are merged.
