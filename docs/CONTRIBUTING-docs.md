# Docs: How To

This guide explains how to add and maintain TDD documentation in this repo. The doc root is `docs/`; human-authored files live under `docs/`. The HTML site is built with MkDocs; PDFs are built with Pandoc. Mermaid is pre-rendered for PDFs via `mmdc`.

## Add a service page

- Create a spec under `docs/platform/`, `docs/automation/`, `docs/data/`, or `docs/customer/` (for example, `docs/platform/settings.md`).
- Keep deep technical content here; keep `docs/overview/tdd.md` high‑level and link to the service spec.
- Use consistent headings (Sentence case). Vale guides tone and terms.

## Add a diagram (Mermaid) {#add-a-diagram}

- Save `.mmd` beside the owning document inside a `diagrams/` directory (for example, `docs/platform/guardian/diagrams/guardian-judgment-flow-v1.mmd`).
- In Markdown, prefer a live Mermaid block for the site and an image fallback for PDF using the build path mapping:
  
  ```mermaid
  %% site render
  graph TD; A-->B;
  ```

  ![Artifact Overview](build/diagrams/overview/tdd/artifact-lifecycle-overview-v1.svg)

- Rendered SVGs live under `docs/build/diagrams/` (mirrored into `packages/udocket_docs/build/diagrams/`) so MkDocs can serve them alongside the Markdown sources. Use `build/diagrams/<path relative to the owning document directory>` in image links so paths remain correct regardless of page depth (`docs/platform/guardian/diagrams/foo.mmd` → `build/diagrams/platform/guardian/foo.svg`).

- Before generating PDFs, render diagrams: `uv run --project packages/udocket_docs python -m doc_tools.render_mermaid` (only re-renders `.mmd` files that changed). Use `--all` to force a complete rebuild.

- Embed rules:
  - Owner docs should contain the Mermaid fence and an adjacent image fallback that points at the pre-rendered SVG.
  - Consumer docs must link to the owner’s section and reuse the rendered SVG (`/build/diagrams/<REL>.svg`); never duplicate the Mermaid source.
  - The source path pattern is `docs/<area>/<doc>/diagrams/<name>.mmd` (with optional subdirectories), and the build artifact lives at `docs/build/diagrams/<area>/<doc>/<name>.svg`.
- Optional metadata: add `%% id: <slug>`, `%% version: v1`, or `%% owner: <owner-doc>` comments to encode diagram provenance for the index.
- Keep the appendix up to date by running `make docs.sync.diagrams` whenever diagrams are added, renamed, or removed.

## Add a runbook

- Create `docs/ops/runbooks/<topic>.md` or update `docs/ops/runbooks.md`.

## Add an ADR

- Create `docs/adr/ADR-XXXX-title.md` (increment number; brief title).
- Keep one decision per ADR; link from TDD or service pages when referenced.
- Shortcut: `python -m doc_tools.create_adr "Background worker topology"` generates the next numbered skeleton (`--dry-run` prints instead of writing, `--deciders/--tags` customise metadata).

## Lint and build locally

- Install doc tooling once (from `packages/udocket_docs/`):
  - `uv sync --frozen --extra dev`
  - `PUPPETEER_SKIP_DOWNLOAD=1 PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium npm ci`
  - `apt-get install -y chromium` (or `brew install chromium` on macOS) so the Mermaid CLI can launch a headless browser
  - Vale CLI ships in the docs toolbox container; install Vale v3.7.1 locally if you prefer running outside the container.
- Node tooling expects Node.js 20.x (see `.nvmrc` and devcontainer). Use `nvm use` or install the pinned version to avoid CLI mismatches.
- Use the unified doc manager (`uv run python -m doc_tools.manage_docs`) or the Make targets (`make lint-docs`, `make build-docs`) to run common workflows:
  - `uv run python -m doc_tools.manage_docs --lint` — read-only checks
  - `uv run python -m doc_tools.manage_docs --sync` — regenerate runbook/diagram/SLO/API appendices and sync document controls/assets
  - `uv run python -m doc_tools.manage_docs --build` — strict MkDocs build (temporary site dir on `--dry-run`)
  - `uv run python -m doc_tools.manage_docs --pdf` — produce TDD/PRD PDFs
  - Combine flags for bespoke flows, e.g. `uv run python -m doc_tools.manage_docs --lint --sync --dry-run` or `uv run python -m doc_tools.manage_docs --all`
- `--dry-run` keeps the workspace read-only for sync/build tasks (scripts emit what would have changed and run `--check` variants where available).
- Lint tasks include: runbook/diagram/API appendices in `--check` mode, structure validation (`platform`, `automation`, `data`, `customer`, `experience`, `ops`), appendix/table verification, markdownlint (`npx markdownlint-cli`), Vale (via `docs/config/vale-ci.ini`), documented settings parity, and strict link checking.
- Validate service specs against the template: `uv run python -m doc_tools.check_structure docs/platform docs/automation docs/data docs/customer`
- Lint markdown: `npx markdownlint --config docs/config/.markdownlint.json 'docs/**/*.md'`.
- Style checks (Vale):
  - From `docs/`: `vale --config docs/config/vale.ini src/`
  - Rules live under `docs/config/vale/`.
- Build site: `uv run mkdocs build --config-file packages/udocket_docs/mkdocs.yml --site-dir site --clean`.
- Preview docs locally (default dev server port 8010):
  - `uv run mkdocs serve --config-file packages/udocket_docs/mkdocs.yml --dev-addr 0.0.0.0:8010`
- Build TDD/PRD PDFs:
  - `uv run --project packages/udocket_docs python -m doc_tools.render_mermaid --all`
  - `uv run python tools/pdf_build.py`
  - Provide `--target`/`--skip-build` to narrow the scope or reuse an existing MkDocs build.

## Cross-linking and single-source rules

- One canonical home per topic. If content is reused, move shared truth into an appendix and link to it.
- Preferred cross-refs: `TDD §X.Y`, `Service §N.M`, `App.<letter>`; Vale nudges format.
- Label policy paragraphs with `(binding)`, `(normative)`, or `(informative)` when applicable.

## CI and releases

- Every PR/main:
  - Markdownlint, Vale, Mermaid pre-render check, MkDocs build, TDD PDF build.
- Tagged release (`vX.Y.Z`):
  - Builds site and TDD PDF, computes checksums, uploads release assets.
  - No PDFs are committed to git; only release assets are published.

## File layout reference

- Sources: `docs/` (TDD, platform, automation, data, customer, experience, ADR, runbooks, .assets).
- Generated: `docs/site/`, `docs/build/` (gitignored).
- Config: `.markdownlint.json` (extends `docs/config/.markdownlint.json`), `docs/config/mkdocs.yml`, `docs/config/vale.ini`, `docs/config/.markdownlint.json`, `docs/config/mermaidrc.json`, `docs/config/settings_key_skip.txt`.
- Scripts: `packages/udocket_docs/src/doc_tools/manage_docs.py`, `packages/udocket_docs/src/doc_tools/lint_docs.py`, sync helpers under `packages/udocket_docs/src/doc_tools/sync/`, and build assets under `packages/udocket_docs/src/doc_tools/build/`.

## Tips

- Keep `overview/tdd.md` short; push details into service pages and appendices.
- Use descriptive diagram filenames with version suffixes (e.g., `*-v1.mmd`).
- For renamed/replaced artifacts, add `_v2`, `_v3`, etc. and update links.
