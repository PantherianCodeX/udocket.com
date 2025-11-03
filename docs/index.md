# Documentation tooling

The `docs/overview/tdd.md` file is large enough that it benefits from a dedicated lint/preview workflow. Everything you need lives in this repository so you can keep the document consistent without guessing which tools to run.

## Quick start

```bash
cd packages/udocket_docs

# Install the Python utilities (mkdocs, mdformat, WeasyPrint, etc.)
uv sync --frozen --extra dev

# Install Node-based helpers (mermaid-cli, markdownlint)
PUPPETEER_SKIP_DOWNLOAD=1 PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium npm ci

# Run the full lint suite (mirrors CI)
uv run python -m doc_tools.manage_docs --lint
```

Vale 3.7.1 is baked into the docs toolbox container (`make docs.build` / `make docs.lint`, which wrap `docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm docs …`).
If you run the commands on the host, install the same Vale version so the lint
step succeeds.

The aggregator runs:

1. `python -m doc_tools.build.runbook_catalog --check` to ensure the ops catalog matches the latest runbook sections
1. `python -m doc_tools.build.diagram_index --check` for Mermaid inventory freshness
1. `python -m doc_tools.check_structure docs/platform docs/automation docs/data docs/customer docs/experience docs/ops` to enforce template compliance
1. `python -m doc_tools.check_appendices` for appendix numbering and references
1. `npx markdownlint --config docs/config/.markdownlint.json 'docs/**/*.md'` plus an optional global `markdownlint-cli` invocation when available
1. `vale --config docs/config/vale-ci.ini --minAlertLevel error …` via the embedded Vale tasks (with an offline style bundle under `docs/config/vale/`)
1. `python -m doc_tools.check_settings_keys` to keep Appendix E aligned with shipped settings
1. `python -m doc_tools.check_links` (with `STRICT_DOCS=1`) for anchor and cross-document validation

All steps are wired into the `Docs Validation` GitHub workflow, so a clean run locally mirrors CI.

## Runbook catalog

Runbook sections live in individual service specifications but are aggregated into `docs/ops/runbooks.md` for responders. To refresh the catalog:

```bash
python -m doc_tools.build.runbook_catalog
```

Authoring guidelines:

- Each runbook section in a source document must start with an H2 heading that contains the word “runbook” so the builder can detect the block.
- Use consistent anchors by including the RB identifier (for example `RB-LPE-COMPILER`) in the heading; the generator emits `<a id="...">` anchors automatically so other docs can deep-link to the catalog.
- Keep Purpose/Contract/State/Failure/Observability scaffolding in every runbook to satisfy `python -m doc_tools.manage_docs --lint` template checks and provide operators with fast context before the detailed steps.
- Follow the single runbook template defined here—no alternate classes or formats—so responders see consistent Purpose/Contract/State/Failure/ Observability scaffolding across services, mirroring the Platform Operations standard.

## Rendering Mermaid diagrams

Source `.mmd` files live under each owner doc’s local `diagrams/` folder. Cross‑cutting TDD diagrams live under `docs/overview/tdd/diagrams/`. To render them locally (outputs to `packages/udocket_docs/build/diagrams/` and makes them available to MkDocs via the build-assets plugin):

```bash
cd packages/udocket_docs
uv run --project packages/udocket_docs python -m doc_tools.render_mermaid
```

Use `--all` to force a full rebuild. Rendered SVGs land in `packages/udocket_docs/build/diagrams/` (canonical store) and are copied into the published site as `build/diagrams/...`. Reference them in Markdown/HTML using `build/diagrams/...` so paths remain correct when the site is published. The CI job `Docs CI` performs the same action so broken diagrams are caught automatically.

## VS Code setup

Open the workspace and install the recommended extensions when prompted:

- `DavidAnson.vscode-markdownlint` for inline Markdown feedback
- `yzhang.Markdown-All-in-One` for TOC generation and keybindings
- `bierner.markdown-preview-github-styles` to preview with GitHub styling

The `.vscode/settings.json` file does not force a formatter, so you can delegate formatting to `mdformat` by running `mdformat docs/overview/tdd.md` manually before committing.

## Tips

- Run `python -m doc_tools.manage_docs --lint` before committing large edits to catch slips in numbering, appendix references, or settings names.
- If Appendix E must mention a configuration key that is not implemented yet, add it to `docs/config/settings_key_skip.txt` together with a short code comment referencing the follow-up work. Remove entries once the code ships so the key list stays authoritative.
- Use `pipx`/`npm install --location=global` if you prefer keeping tooling isolated from project virtual environments.
- Set `STRICT_DOCS=0` when invoking `check_links.py` directly if you only want warnings instead of hard failures.
