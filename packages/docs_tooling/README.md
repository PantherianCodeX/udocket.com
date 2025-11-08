# uDocket Docs Package

This package hosts the documentation toolchain for the uDocket platform. It includes:

- MkDocs configuration (`packages/docs_tooling/mkdocs.yml`) and Markdown sources under `docs/`.
- Custom MkDocs plugins and shared tooling under `src/` and `tools/`.
- WeasyPrint assets for PDF rendering that mirror the MkDocs site styling.
- Theme overrides (CSS/JS) live in `docs/assets/`; generated artifacts are written under `packages/docs_tooling/build/` and copied into the site via the `include-build-assets` plugin.

Install dependencies with [`uv`](https://github.com/astral-sh/uv) (the Make targets call these under the hood):

```bash
uv sync --frozen --extra dev
```

Build the site locally via the Makefile (preferred so the correct config file is passed through) or run MkDocs directly:

```bash
uv run --package mkdocs mkdocs serve --config-file packages/docs_tooling/mkdocs.yml --watch-theme
```

Generate PDFs with the shared WeasyPrint styling:

```bash
uv run --project packages/docs_tooling python -m doc_tools.build.pdf
```

## Asset & diagrams layout

- Author Markdown inside `docs/`. Keep Mermaid sources beside their owning documents under a local `diagrams/` directory (for example, `docs/platform/guardian/diagrams/guardian-judgment-flow-v1.mmd`).
- Rendered diagrams are emitted to `packages/docs_tooling/build/diagrams/`; MkDocs publishes them under `build/diagrams/…` using the `include-build-assets` plugin.
- Theme overrides (CSS/JS) belong in `docs/assets/`. When additional static assets are needed, add them there so they participate in MkDocs live reload.
- To regenerate diagrams after editing `.mmd` files run:

  ```bash
  uv run --project packages/docs_tooling python -m doc_tools.render_mermaid --all
  ```

  The CLI defaults to incremental rebuilds; pass `--all` to force a full render.

## Environment

- Copy `.env.example` to `.env` (the docs container already ships one). The docs settings loader reads `DOCS_TOOLING_ENV_FILE`, then `packages/docs_tooling/.env`, and finally the repository `.env`, mirroring the platform and core packages.
- `UDOCKET_REPO_ROOT` controls where sources are loaded from. Override it when running outside the container, e.g. `UDOCKET_REPO_ROOT=/path/to/checkout`.
- `DOCS_TOOLING_ROOT`, `DOCS_TOOLING_CONFIG_ROOT`, `DOCS_TOOLING_BUILD_ROOT`, and `UDOCKET_DOC_BUILDS_ROOT` fall back to the detected repo root when unspecified, so most local workflows work without extra configuration.

## MkDocs plugins

The docs site enables two local plugins distributed from `packages/docs_tooling/plugins/udocket_mkdocs_plugins`:

```yaml
plugins:
  - auto-image-scale:
      scale_attr: data-scale
      class_map:
        img--half: 0.5
  - include-build-assets:
      source_dir: packages/docs_tooling/build
      site_prefix: build
```

- `auto-image-scale` inspects rendered HTML, locates `<img>` tags that opt in via `data-scale` or a mapped CSS class, and injects explicit width/height attributes derived from the source image.
- `include-build-assets` copies artifacts generated outside MkDocs (diagrams, PDFs) from `packages/docs_tooling/build/` into the site output under `build/`. The site references these assets with `build/…` URLs so paths remain stable regardless of page depth.

Both plugins are packaged with entry points under the `udocket-mkdocs-plugins` distribution. When adding new plugins or adjusting defaults, update `pyproject.toml`, the README, and ensure unit tests cover the behaviour.
The plugin modules live under `src/` and are covered by the top-level
Pyright configuration, so keep them fully typed.

## Test coverage

Run the docs toolbox test suite with coverage enforced at 90% (override via `DOCS_COV_MIN` if you need a higher bar locally):

```bash
make docs.test.coverage
# or directly
uv run --project packages/docs_tooling python -m doc_tools.pytest_runner --coverage
```

Coverage runs emit a term report and fail if the configured threshold is not met. Integrate the `docs.test.coverage` target in CI to keep regressions from landing.

> **Important:** the docs tests live in a different environment than the Django platform. Always invoke them via `doc_tools.pytest_runner` (or the `make docs.test*` targets). Running `pytest` from the repo root will try to import Django/DRF without their dependencies and can mask real failures.
