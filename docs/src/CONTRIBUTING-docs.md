# Docs: How To

This guide explains how to add and maintain TDD documentation in this repo. The doc root is `docs/`; human-authored files live under `docs/src/`. The HTML site is built with MkDocs; PDFs are built with Pandoc. Mermaid is pre-rendered for PDFs via `mmdc`.

## Add a service page

- Create a spec under `docs/src/platform/`, `docs/src/automation/`, `docs/src/data/`, or `docs/src/customer/` (for example, `docs/src/platform/settings.md`).
- Keep deep technical content here; keep `docs/src/overview/tdd.md` high‑level and link to the service spec.
- Use consistent headings (Sentence case). Vale guides tone and terms.

## Add a diagram (Mermaid) {#add-a-diagram}

- Save `.mmd` under the owning doc’s local `diagrams/` folder:
  - Cross‑cutting (TDD‑owned): `docs/src/overview/tdd/diagrams/`
  - Service‑owned: `docs/src/<area>/<service>/diagrams/`
  - App‑owned: `docs/src/experience/<app>/diagrams/`
- In Markdown, prefer a live Mermaid block for the site and an image fallback for PDF using the build path mapping:
  
  ```mermaid
  %% site render
  graph TD; A-->B;
  ```

  ![Artifact Overview](_assets/mermaid/overview/tdd/diagrams/artifact-lifecycle-overview-v1.svg)

- Rendered SVGs live under `docs/_assets/mermaid/` (mirrored into `docs/src/_assets/mermaid/`) so MkDocs can serve them alongside the Markdown sources. Use `_assets/mermaid/...` in image links so paths remain correct regardless of page depth.

- Before generating PDFs, render diagrams: `bash docs/tools/render_mermaid.sh` (only re-renders `.mmd` files that changed). Use `--all` to force a complete rebuild.

- Embed rules:
  - Owner docs should contain the Mermaid fence and an adjacent image fallback that points at the pre-rendered SVG.
  - Consumer docs must link to the owner’s section and reuse the rendered SVG (`/_assets/mermaid/<REL>.svg`); never duplicate the Mermaid source.
  - The source path pattern is `docs/src/<REL>.mmd`, and the build artifact lives at `docs/_assets/mermaid/<REL>.svg` (mirrored to `docs/src/_assets/mermaid/<REL>.svg`).
- Optional metadata: add `%% id: <slug>`, `%% version: v1`, or `%% owner: <owner-doc>` comments to encode diagram provenance for the index.
- Keep the appendix up to date by running `python -m docs.tools.build.diagram_index` whenever diagrams are added, renamed, or removed.

## Add a runbook

- Create `docs/src/ops/runbooks/<topic>.md` or update `docs/src/ops/runbooks.md`.

## Add an ADR

- Create `docs/src/adr/ADR-XXXX-title.md` (increment number; brief title).
- Keep one decision per ADR; link from TDD or service pages when referenced.

## Lint and build locally

- Install doc tooling once:
  - `pip install -r requirements-docs.txt`
  - `npm ci`
  - `apt-get install -y chromium` (or `brew install chromium` on macOS) so the Mermaid CLI can launch a headless browser
  - Vale CLI ships in the devcontainer; when running locally, download v3.7.1 from the official releases if you want parity.
- Node tooling expects Node.js 22.x (see `.nvmrc` and devcontainer). Use `nvm use` or install the pinned version to avoid CLI mismatches.
- Run the aggregate lint script (or `make lint-docs` if you already activated the repository virtualenv):
  - `python -m docs.tools.lint_docs` (lints entire `docs/src/`)
  - Optional: pass one or more targets, e.g. `python -m docs.tools.lint_docs docs/src/platform/settings.md docs/src/overview/tdd.md`
- The lint runner executes (in order): `python -m docs.tools.build.runbook_catalog --check`, `python -m docs.tools.build.diagram_index --check`, `check_structure.py` (platform/automation/data/customer/experience/ops), `check_appendices.py`, `markdownlint` (npx plus optional global `markdownlint-cli`), `check_settings_keys.py`, `check_links.py` with `STRICT_DOCS=1`, and a strict MkDocs build (`docs/tools/build/mkdocs.py --dry-run`).
- Validate service specs against the template: `python -m docs.tools.check_structure docs/src/platform docs/src/automation docs/src/data docs/src/customer`
- Lint markdown: `npx markdownlint --config docs/config/.markdownlint.json 'docs/src/**/*.md'`.
- Style checks (Vale):
  - From `docs/`: `vale --config docs/config/vale.ini src/`
  - Rules live under `docs/config/vale/`.
- Build site: `mkdocs -f docs/config/mkdocs.yml build --clean` (outputs to `docs/site/`).
- Build TDD PDF:
  - `bash docs/tools/render_mermaid.sh --all`
  - `bash docs/tools/build/pdf_tdd.sh` (outputs to `docs/build/pdf/tdd.pdf`).
  - The MkDocs wrapper also supports a dry run: `python -m docs.tools.build.mkdocs --dry-run`.

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

- Sources: `docs/src/` (TDD, platform, automation, data, customer, experience, ADR, runbooks, .assets).
- Generated: `docs/site/`, `docs/build/` (gitignored).
- Config: `.markdownlint.json` (extends `docs/config/.markdownlint.json`), `docs/config/mkdocs.yml`, `docs/config/vale.ini`, `docs/config/.markdownlint.json`, `docs/config/mermaidrc.json`, `docs/config/settings_key_skip.txt`.
- Scripts: `docs/tools/*.sh`.

## Tips

- Keep `overview/tdd.md` short; push details into service pages and appendices.
- Use descriptive diagram filenames with version suffixes (e.g., `*-v1.mmd`).
- For renamed/replaced artifacts, add `_v2`, `_v3`, etc. and update links.
