# Docs: How To

This guide explains how to add and maintain TDD documentation in this repo. The doc root is `docs/`; human-authored files live under `docs/src/`. The HTML site is built with MkDocs; PDFs are built with Pandoc. Mermaid is pre-rendered for PDFs via `mmdc`.

## Add a service page

- Create `docs/src/services/<service>.md` (e.g., `settings.md`).
- Keep deep technical content here; keep `docs/src/overview/tdd.md` high‑level and link to services.
- Use consistent headings (Sentence case). Vale guides tone and terms.

### API error code subsections

- Every service and app specification keeps the prose preamble under `### 3.3 API Error Codes (binding)` using the shared template (`docs/src/services/_template.md` / `docs/src/apps/_template.md`).
- Author the canonical definitions in `docs/src/services/<service>/error_codes.yaml` (or `docs/src/apps/<app>/error_codes.yaml`). Follow `spec/schemas/api_error_codes.schema.yaml` for required fields (`code`, `http_status`, `audit_required`, `description`, `client_action`) and optional `scenario`/`related_metrics`.
- Run `python scripts/docs/build_api_error_codes.py` (or `--check`) after editing the YAML. The script rewrites the summary & catalog tables in each spec and regenerates `docs/src/overview/tdd/appendices/api_error_codes.md`.
- The tables live between HTML comment markers (`<!-- BEGIN/END AUTO-GENERATED: api-error-codes:* -->`). Do not edit them manually—any changes will be overwritten on the next sync.
- `python scripts/docs/check_structure.py` validates marker placement and ensures every spec with a 3.3 section has a matching `error_codes.yaml`. Lint locally before submitting a PR.

### Auto-generated sections

- All doc automation shares the same marker format: `<!-- BEGIN AUTO-GENERATED: <label> -->` … `<!-- END AUTO-GENERATED: <label> -->`. Do not introduce alternative marker names or shapes.
- Never hand-edit the contents between these markers. Instead, rerun the owning build script (for example `build_api_error_codes.py`, `build_diagram_index.py`, `build_runbook_catalog.py`, `build_slo_index.py`, or `sync_document_controls.py`).
- When adding a new generated block, wrap it with the shared helpers in `scripts/docs/doc_utils.py` so future tooling can manage it consistently.

## Add a diagram (Mermaid)

- Save `.mmd` under the owning doc’s local `diagrams/` folder:
  - Cross‑cutting (TDD‑owned): `docs/src/overview/tdd/diagrams/`
  - Service‑owned: `docs/src/services/<service>/diagrams/`
  - App‑owned: `docs/src/apps/<app>/diagrams/`
- In Markdown, prefer a live Mermaid block for the site and an image fallback for PDF using the build path mapping:
  
  ```mermaid
  %% site render
  graph TD; A-->B;
  ```

  ![Artifact Overview](../../build/mermaid/overview/tdd/diagrams/artifact-lifecycle-overview-v1.svg)

- Rendered SVGs live under `docs/src/build/mermaid/` so MkDocs can serve them alongside the Markdown sources. Use `/build/mermaid/...` in image links so paths remain correct regardless of page depth.

- Before generating PDFs, render diagrams: `bash scripts/docs/render_mermaid.sh` (only re-renders `.mmd` files that changed). Use `--all` to force a complete rebuild.

- Embed rules:
  - Owner docs should contain the Mermaid fence and an adjacent image fallback that points at the pre-rendered SVG.
  - Consumer docs must link to the owner’s section and reuse the rendered SVG (`/build/mermaid/<REL>.svg`); never duplicate the Mermaid source.
  - The source path pattern is `docs/src/<REL>.mmd`, and the build artifact lives at `docs/src/build/mermaid/<REL>.svg`.
- Optional metadata: add `%% id: <slug>`, `%% version: v1`, or `%% owner: <owner-doc>` comments to encode diagram provenance for the index.
- Keep the appendix up to date by running `python scripts/docs/build_diagram_index.py` whenever diagrams are added, renamed, or removed.

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
- Run the aggregate lint script (or `make lint-docs` if you already activated the project virtualenv):
  - `python scripts/docs/lint_docs.py` (lints entire `docs/src/`)
  - Optional: pass one or more targets, e.g. `python scripts/docs/lint_docs.py docs/src/services/settings.md docs/src/overview/tdd.md`
- The lint runner executes (in order): `build_runbook_catalog.py --check`, `build_diagram_index.py --check`, `check_structure.py` (services/apps/ops), `check_appendices.py`, `markdownlint-cli2` (npx + optional global), `check_settings_keys.py`, `link_check.py` with `STRICT_DOCS=1`, and a strict MkDocs build via `scripts/docs/build_mkdocs.py --dry-run`.
- Validate service specs against the template: `python scripts/docs/check_structure.py docs/src/services`
- Lint markdown: `npx markdownlint-cli2 'docs/src/**/*.md'`.
- Style checks (Vale):
  - From `docs/`: `vale src/`
  - Rules live under `docs/styles/vale/`.
- Build site: `mkdocs -f docs/mkdocs.yml build --clean` (outputs to `docs/site/`).
- Build TDD PDF:
  - `bash scripts/docs/render_mermaid.sh --all`
  - `bash scripts/docs/build_pdf_tdd.sh` (outputs to `docs/build/pdf/tdd.pdf`).
  - The MkDocs wrapper also supports a dry run: `python scripts/docs/build_mkdocs.py --dry-run`.

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

- Sources: `docs/src/` (TDD, services, ADR, runbooks, assets).
- Generated: `docs/site/`, `docs/build/` (gitignored).
- Config: `docs/mkdocs.yml`, `docs/.vale.ini`, `docs/.markdownlint.json`, `docs/.mermaidrc`.
- Scripts: `scripts/docs/*.sh`.

## Tips

- Keep `overview/tdd.md` short; push details into service pages and appendices.
- Use descriptive diagram filenames with version suffixes (e.g., `*-v1.mmd`).
- For renamed/replaced artifacts, add `_v2`, `_v3`, etc. and update links.
