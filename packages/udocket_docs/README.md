# uDocket Docs Package

This package hosts the documentation toolchain for the uDocket platform. It includes:

- MkDocs configuration (`packages/udocket_docs/mkdocs.yml`) and Markdown sources under `docs/`.
- Custom MkDocs plugins and shared tooling under `src/` and `tools/`.
- WeasyPrint assets for PDF rendering that mirror the MkDocs site styling.

Install dependencies with [`uv`](https://github.com/astral-sh/uv):

```bash
uv sync --frozen --extra dev
```

Build the site locally:

```bash
uv run --package mkdocs mkdocs serve --config-file packages/udocket_docs/mkdocs.yml --watch-theme
```

Generate PDFs with the shared WeasyPrint styling:

```bash
uv run python tools/pdf_build.py
```

## Environment

- Copy `.env.example` to `.env` (already committed for the docs container) to configure repo roots. The defaults assume the repository is mounted at `/udocket` (matching the docs toolbox container).
- `UDOCKET_REPO_ROOT` controls where sources are loaded from. Override it when running outside the container, e.g. `UDOCKET_REPO_ROOT=/path/to/checkout`.
- `UDOCKET_DOCS_ROOT`, `UDOCKET_DOCS_CONFIG_ROOT`, `UDOCKET_DOCS_BUILD_ROOT`, and `UDOCKET_DOC_BUILDS_ROOT` fall back to `UDOCKET_REPO_ROOT` if unset.
