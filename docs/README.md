# Documentation tooling

The `docs/TDDv7.md` file is large enough that it benefits from a dedicated
lint/preview workflow. Everything you need lives in this repository so you
can keep the document consistent without guessing which tools to run.

## Quick start

```bash
# Install the Python utilities (mdformat + helpers)
pip install -r requirements-docs.txt

# Optionally install markdownlint for richer feedback
npm install --location=global markdownlint-cli2 markdownlint-cli2-config-standard

# Run the full lint suite
python scripts/docs/lint_docs.py
```

The aggregator runs:

1. `mdformat --check --wrap 0 docs/TDDv7.md`
2. `markdownlint-cli2 docs/TDDv7.md` (skipped if the CLI is not on `PATH`)
3. `scripts/docs/check_settings_keys.py` to ensure Appendix E only lists
   keys that actually exist in the codebase
4. `scripts/docs/link_check.py` for appendix/diagram/section sanity checks

All steps are wired into the `Docs Validation` GitHub workflow, so a clean
run locally mirrors CI.

## Rendering Mermaid diagrams

The repository already contains source `.mmd` files under `docs/diagrams/`.
To render them locally:

```bash
npm install --location=global @mermaid-js/mermaid-cli
scripts/docs/render_mermaid.sh
```

Rendered SVGs land in `docs/diagrams/_rendered/` (git-ignored). The CI job
`render-diagrams` performs the same action so broken diagrams are caught
automatically.

## VS Code setup

Open the workspace and install the recommended extensions when prompted:

- `DavidAnson.vscode-markdownlint` for inline Markdown feedback
- `yzhang.Markdown-All-in-One` for TOC generation and keybindings
- `bierner.markdown-preview-github-styles` to preview with GitHub styling

The `.vscode/settings.json` file does not force a formatter, so you can
delegate formatting to `mdformat` by running `mdformat docs/TDDv7.md`
manually or via the lint script above.

## Tips

- Run `python scripts/docs/lint_docs.py` before committing large edits to
  catch slips in numbering, appendix references, or settings names.
- Use `pipx`/`npm install --location=global` if you prefer keeping tooling
  isolated from project virtual environments.
- Set `STRICT_DOCS=0` when invoking `link_check.py` directly if you only want
  warnings instead of hard failures.
