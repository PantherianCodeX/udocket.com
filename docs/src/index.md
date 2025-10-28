# Documentation tooling

The `docs/src/overview/tdd.md` file is large enough that it benefits from a dedicated lint/preview workflow. Everything you need lives in this repository so you can keep the document consistent without guessing which tools to run.

## Quick start

```bash
# Install the Python utilities (mdformat, mkdocs, etc.)
pip install -r requirements-docs.txt

# Install Node-based helpers (mermaid-cli, markdownlint)
# Requires Node.js 22.x (see .nvmrc)
npm ci

# Run the full lint suite
python scripts/docs/lint_docs.py
```

The aggregator runs:

1. `mdformat --check --wrap no docs/src/overview/tdd.md`
1. `markdownlint-cli2 docs/src/overview/tdd.md` (skipped if the CLI is not on `PATH`)
1. `scripts/docs/check_settings_keys.py` to ensure Appendix E only lists keys that actually exist in the codebase
1. `scripts/docs/link_check.py` for appendix/diagram/section sanity checks

All steps are wired into the `Docs Validation` GitHub workflow, so a clean run locally mirrors CI.

## Runbook catalog

Runbook sections live in individual service specifications but are aggregated into `docs/src/ops/runbooks/index.md` for responders. To refresh the catalog:

```bash
python scripts/docs/build_runbook_catalog.py
```

Authoring guidelines:

- Each runbook section in a source document must start with an H2 heading that contains the word “runbook” so the builder can detect the block.
- Use consistent anchors by including the RB identifier (for example `RB-LPE-COMPILER`) in the heading; the generator emits `<a id="...">` anchors automatically so other docs can deep-link to the catalog.
- Keep Purpose/Contract/State/Failure/Observability scaffolding in every runbook to satisfy `lint_docs.py` template checks and provide operators with fast context before the detailed steps.
- Follow the single runbook template defined here—no alternate classes or formats—so responders see consistent Purpose/Contract/State/Failure/ Observability scaffolding across services, mirroring the Platform Operations standard.

## Rendering Mermaid diagrams

Source `.mmd` files live under each owner doc’s local `diagrams/` folder. Cross‑cutting TDD diagrams live under `docs/src/overview/tdd/diagrams/`. To render them locally (outputs to `docs/src/build/mermaid/`):

```bash
scripts/docs/render_mermaid.sh
```

Use `--all` to force a full rebuild. Rendered SVGs land in `docs/src/build/mermaid/` (checked in so MkDocs and PDF builds can read them). Reference them in Markdown/HTML using `/build/mermaid/...` so paths remain correct when the site is published. The CI job `Docs CI` performs the same action so broken diagrams are caught automatically.

## VS Code setup

Open the workspace and install the recommended extensions when prompted:

- `DavidAnson.vscode-markdownlint` for inline Markdown feedback
- `yzhang.Markdown-All-in-One` for TOC generation and keybindings
- `bierner.markdown-preview-github-styles` to preview with GitHub styling

The `.vscode/settings.json` file does not force a formatter, so you can delegate formatting to `mdformat` by running `mdformat docs/src/overview/tdd.md` manually or via the lint script above.

## Tips

- Run `python scripts/docs/lint_docs.py` before committing large edits to catch slips in numbering, appendix references, or settings names.
- If Appendix E must mention a configuration key that is not implemented yet, add it to `docs/settings_key_skip.txt` together with a short code comment referencing the follow-up work. Remove entries once the code ships so the key list stays authoritative.
- Use `pipx`/`npm install --location=global` if you prefer keeping tooling isolated from project virtual environments.
- Set `STRICT_DOCS=0` when invoking `link_check.py` directly if you only want warnings instead of hard failures.
