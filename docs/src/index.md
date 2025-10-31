# Documentation tooling

The `docs/src/overview/tdd.md` file is large enough that it benefits from a dedicated lint/preview workflow. Everything you need lives in this repository so you can keep the document consistent without guessing which tools to run.

## Quick start

```bash
# Install the Python utilities (mdformat, mkdocs, etc.)
pip install -r requirements-docs.txt

# Install Node-based helpers (mermaid-cli, markdownlint)
# Requires Node.js 22.x (see .nvmrc)
npm ci

# Run the full lint suite (or `make lint-docs` if your venv is active)
python -m docs.tools.manage_docs --lint  # alias: python -m docs.tools.manage_docs --lint
```

The aggregator runs:

1. `python -m docs.tools.build.runbook_catalog --check` to ensure the ops catalog matches the latest runbook sections
1. `python -m docs.tools.build.diagram_index --check` for Mermaid inventory freshness
1. `python -m docs.tools.check_structure docs/src/platform docs/src/automation docs/src/data docs/src/customer docs/src/experience docs/src/ops` to enforce template compliance
1. `python -m docs.tools.check_appendices` for appendix numbering and references
1. `npx markdownlint --config docs/config/.markdownlint.json 'docs/src/**/*.md'` plus an optional global `markdownlint-cli` invocation when available
1. `vale --config docs/config/vale-ci.ini --minAlertLevel error …` via the embedded Vale tasks (with an offline style bundle under `docs/config/vale/`)
1. `python -m docs.tools.check_settings_keys` to keep Appendix E aligned with shipped settings
1. `python -m docs.tools.check_links` (with `STRICT_DOCS=1`) for anchor and cross-document validation

All steps are wired into the `Docs Validation` GitHub workflow, so a clean run locally mirrors CI.

## Runbook catalog

Runbook sections live in individual service specifications but are aggregated into `docs/src/ops/runbooks.md` for responders. To refresh the catalog:

```bash
python -m docs.tools.build.runbook_catalog
```

Authoring guidelines:

- Each runbook section in a source document must start with an H2 heading that contains the word “runbook” so the builder can detect the block.
- Use consistent anchors by including the RB identifier (for example `RB-LPE-COMPILER`) in the heading; the generator emits `<a id="...">` anchors automatically so other docs can deep-link to the catalog.
- Keep Purpose/Contract/State/Failure/Observability scaffolding in every runbook to satisfy `python -m docs.tools.manage_docs --lint` template checks and provide operators with fast context before the detailed steps.
- Follow the single runbook template defined here—no alternate classes or formats—so responders see consistent Purpose/Contract/State/Failure/ Observability scaffolding across services, mirroring the Platform Operations standard.

## Rendering Mermaid diagrams

Source `.mmd` files live under each owner doc’s local `diagrams/` folder. Cross‑cutting TDD diagrams live under `docs/src/overview/tdd/diagrams/`. To render them locally (outputs to `docs/build/mermaid/` and mirrors into `docs/src/_assets/mermaid/`):

```bash
docs/tools/render_mermaid.sh
```

Use `--all` to force a full rebuild. Rendered SVGs land in `docs/build/mermaid/` (canonical store) and are mirrored to `docs/src/_assets/mermaid/` so MkDocs can serve them. Reference them in Markdown/HTML using `_assets/mermaid/...` so paths remain correct when the site is published. The CI job `Docs CI` performs the same action so broken diagrams are caught automatically.

## VS Code setup

Open the workspace and install the recommended extensions when prompted:

- `DavidAnson.vscode-markdownlint` for inline Markdown feedback
- `yzhang.Markdown-All-in-One` for TOC generation and keybindings
- `bierner.markdown-preview-github-styles` to preview with GitHub styling

The `.vscode/settings.json` file does not force a formatter, so you can delegate formatting to `mdformat` by running `mdformat docs/src/overview/tdd.md` manually before committing.

## Tips

- Run `python -m docs.tools.manage_docs --lint` before committing large edits to catch slips in numbering, appendix references, or settings names.
- If Appendix E must mention a configuration key that is not implemented yet, add it to `docs/config/settings_key_skip.txt` together with a short code comment referencing the follow-up work. Remove entries once the code ships so the key list stays authoritative.
- Use `pipx`/`npm install --location=global` if you prefer keeping tooling isolated from project virtual environments.
- Set `STRICT_DOCS=0` when invoking `check_links.py` directly if you only want warnings instead of hard failures.
