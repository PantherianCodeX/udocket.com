# Docs: How To

This guide explains how to add and maintain TDD documentation in this repo. The doc root is `docs/`; human-authored files live under `docs/src/`. The HTML site is built with MkDocs; PDFs are built with Pandoc. Mermaid is pre-rendered for PDFs via `mmdc`.

## Add a service page
- Create `docs/src/services/<service>.md` (e.g., `settings-registry.md`).
- Keep deep technical content here; keep `docs/src/tdd/TDD.md` high-level and link to services.
- Use consistent headings (Sentence case). Vale guides tone and terms.

## Add a diagram (Mermaid)
- Save `.mmd` under `docs/src/tdd/appendices/diagrams/` (subfolders allowed).
- In Markdown, prefer a live Mermaid block for the site and an image fallback for PDF:
  
  ```
  ```mermaid
  %% site render
  graph TD; A-->B;
  ```
  ![Artifact Overview](../../tdd/appendices/diagrams/artifact-lifecycle-overview-v1.svg)
  ```
- Before generating PDFs, render diagrams: `bash scripts/docs/render_mermaid.sh --all`.

## Add a runbook
- Create `docs/src/ops/runbooks/<topic>.md` or update `docs/src/ops/runbooks/index.md`.

## Add an ADR
- Create `docs/src/adr/ADR-XXXX-title.md` (increment number; brief title).
- Keep one decision per ADR; link from TDD or service pages when referenced.

## Lint and build locally
- Lint markdown: `npx markdownlint-cli2 'docs/src/**/*.md'`.
- Style checks (Vale):
  - From `docs/`: `vale src/`
  - Rules live under `docs/styles/vale/`.
- Build site: `mkdocs -f docs/mkdocs.yml build --clean` (outputs to `docs/site/`).
- Build TDD PDF:
  - `bash scripts/docs/render_mermaid.sh --all`
  - `bash scripts/docs/build_pdf_tdd.sh` (outputs to `docs/build/pdf/tdd.pdf`).

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
- Keep `TDD.md` short; push details into service pages and appendices.
- Use descriptive diagram filenames with version suffixes (e.g., `*-v1.mmd`).
- For renamed/replaced artifacts, add `_v2`, `_v3`, etc. and update links.
