# Docs: How To

This guide explains how to add and maintain TDD documentation in this repo. The doc root is `docs/`; human-authored files live under `docs/`. The HTML site is built with MkDocs; PDFs are built with Pandoc. Mermaid is pre-rendered for PDFs via `mmdc`.

## Add a service page

- Create a spec under `docs/platform/`, `docs/automation/`, `docs/data/`, or `docs/customer/` (for example, `docs/platform/settings.md`).
- Keep deep technical content here; keep `docs/overview/tdd.md` high‑level and link to the service spec.
- Use consistent headings (Sentence case). Vale guides tone and terms.

## Add a diagram (Mermaid)

- Save `.mmd` beside the owning document inside a `diagrams/` directory (for example, `docs/platform/guardian/diagrams/guardian-judgment-flow-v1.mmd`).
- In Markdown, prefer a live Mermaid block for the site and an image fallback for PDF using the build path mapping:
  
  ```mermaid
  %% site render
  graph TD; A-->B;
  ```

  ![Artifact Overview](build/diagrams/overview/tdd/artifact-lifecycle-overview-v1.svg)

- Rendered SVGs live under `docs/build/diagrams/` (mirrored into `packages/docs_tooling/build/diagrams/`) so MkDocs can serve them alongside the Markdown sources. Use `build/diagrams/<path relative to the owning document directory>` in image links so paths remain correct regardless of page depth (`docs/platform/guardian/diagrams/foo.mmd` → `build/diagrams/platform/guardian/foo.svg`).

- Before generating PDFs, render diagrams: `uv run --project packages/docs_tooling python -m doc_tools.render_mermaid` (only re-renders `.mmd` files that changed). Use `--all` to force a complete rebuild.

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

## Header includes & placeholders

- `packages/docs_tooling/src/doc_tools/config/header_includes.yaml` is the single source of truth for PDF header/footer fragments.
- **Front-matter placeholders** use `{<field_name>}` syntax and must map to front-matter keys. Example: `{<title>}`, `{<subtitle>}`, `{<subtitle_block>}`. `{<subtitle_block>}` is computed automatically from `subtitle` and `subtitle_lead` (blank if no subtitle).
- **Built-ins** use double braces `{{token}}` and are injected by the renderer. Defaults: `{{page_number}}`, `{{page_count}}`, `{{prefix}}` (classification + last updated), with HTML stubs defined in `DEFAULT_BUILTIN_HTML`.
- When editing headers/footers, never reintroduce legacy `{{field}}` forms for front-matter values. The templates check (`python -m doc_tools.check.templates`) emits warnings for legacy syntax; fix them instead of suppressing.
- The document controls sync job (`python -m doc_tools.sync.document_controls`) now renders header-includes automatically; do not hand-edit the YAML block in each document.

## Lint and build locally

- **Always** run lint/sync/build via the docs toolbox container to guarantee matching tooling (`make docs.*`). The Make targets automatically launch `docker compose run docs …` and inject required env (Vale, Node, Chromium, etc.).
  - `make docs.lint` — full read-only lint pipeline (structure validation, runbook/diagram/SLO/API appendix checks, markdownlint, Vale, link + settings checks). This target sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` internally for deterministic pytest runs.
  - `make docs.sync.runbooks`, `make docs.sync.diagrams`, `make docs.sync.slo`, `make docs.sync.api_codes` — rebuild the corresponding appendices after editing sources.
  - `make docs.sync` — run the standard sync pipeline (doc controls, assets, appendices, nav updates).
  - `make docs.sync.all` — run `docs.sync` plus the heavy extras (nav mapping migrations, other one-off content moves). Use this before major releases or after structure refactors.
  - `make docs.build` — strict MkDocs build (temp site dir), honoring `--dry-run` semantics embedded in manage_docs.
  - Build tasks **only** generate deliverables (mkdocs site, PDFs, diagram indexes) while sync tasks materialise deterministic content inside `docs/` (document controls, appendices, nav). Pick the one that matches your intent to avoid unreviewed file churn.
- Container shell: `make doctools.shell` drops you into the toolbox if you need to run ad-hoc commands (Vale, mkdocs serve, etc.). Prefer this over `uv run …` on the host.
- Local tool installation is optional; the toolbox image carries npm/Vale/Chromium. If you do install locally, match `.nvmrc` (Node 20.x) and Vale 3.7.1 to avoid CLI drift.
- Templates & structure checks:
  - `python -m doc_tools.check.structure docs/platform docs/automation docs/data docs/customer` — still useful per-directory, but run inside the toolbox shell.
  - `python -m doc_tools.check.templates docs/overview/tdd/appendices/_template.md ...` — ensures `_template.md` files contain the required front-matter/document-control rows and only use the sanctioned placeholders.
- Markdownlint & Vale (inside toolbox shell):
  - `npx markdownlint --config docs/config/.markdownlint.json 'docs/**/*.md'`
  - `vale --config docs/config/vale.ini docs/`
- Build & preview:
  - `uv run --project packages/docs_tooling mkdocs build --config-file packages/docs_tooling/mkdocs.yml --site-dir site --clean`
  - `uv run --project packages/docs_tooling mkdocs serve --config-file packages/docs_tooling/mkdocs.yml --dev-addr 0.0.0.0:8010`
- PDFs:
  - `uv run --project packages/docs_tooling python -m doc_tools.render_mermaid --all`
  - `uv run --project packages/docs_tooling python -m doc_tools.build.pdf --target tdd`
  - Use `--skip-build` if you already ran `make docs.build`.

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
- Scripts: `packages/docs_tooling/src/doc_tools/manage_docs.py`, `packages/docs_tooling/src/doc_tools/lint_docs.py`, sync helpers under `packages/docs_tooling/src/doc_tools/sync/`, and build assets under `packages/docs_tooling/src/doc_tools/build/`.

## Tips

- Keep `overview/tdd.md` short; push details into service pages and appendices.
- Use descriptive diagram filenames with version suffixes (e.g., `*-v1.mmd`).
- For renamed/replaced artifacts, add `_v2`, `_v3`, etc. and update links.

## Refactor backlog

We track ongoing cleanup here so contributors can pick up tasks deliberately:

1. **CLI wrappers** — migrate the remaining ad-hoc entrypoints (e.g., `doc_tools.lint_docs`, `doc_tools.pytest_runner`) to thin wrappers that detect `DOCS_TOOLBOX=1` and otherwise call the appropriate `make docs.*` targets.
2. **Shared helper extraction** — move the remaining bespoke Markdown/YAML parsing helpers (diagram metadata parsing, SLO section extraction) under `doc_tools/common` for reuse.
3. **Nav utilities** — expand `doc_tools.common.nav_utils` with serializers so future nav sync scripts don’t reimplement indentation/formatting rules.
4. **Type hygiene** — continue replacing `typing.Any` usage in older scripts (e.g., `doc_tools/build/*.py`) with precise TypedDict/dataclass models so Pyright stays green in the `pyrightconfig.docs-scripts.json` scope.
