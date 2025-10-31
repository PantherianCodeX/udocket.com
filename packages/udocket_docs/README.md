# uDocket Docs Package

This package hosts the documentation toolchain for the uDocket platform. It includes:

- MkDocs configuration (`mkdocs.yml`) and Markdown sources under `docs/`.
- Custom MkDocs plugins and shared tooling under `src/` and `tools/`.
- WeasyPrint assets for PDF rendering that mirror the MkDocs site styling.

Install dependencies with [`uv`](https://github.com/astral-sh/uv):

```bash
uv sync --frozen --extra dev
```

Build the site locally:

```bash
uv run --package mkdocs mkdocs serve --config-file mkdocs.yml --watch-theme
```

Generate PDFs with the shared WeasyPrint styling:

```bash
uv run python tools/pdf_build.py
```

