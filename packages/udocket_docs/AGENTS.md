# Docs Agents Guide

Follow the root **uDocket — Agents Guide** plus these doc-specific notes.

- All documentation sources live under `/docs/` in the repo root.
- Use `uv sync --frozen --extra dev` in `packages/udocket_docs/` to install the locked toolchain; do not rely on system `pip`.
- Prefer running tasks through the docs toolbox container via `make docs.build`, `make docs.lint`, etc. (these commands wrap `docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.cache.yml run --rm docs …`) so MkDocs, WeasyPrint, Vale, and Mermaid share cached layers.
- Generated assets belong in `packages/udocket_docs/build/` and `packages/udocket_docs/site/`; keep the tracked Markdown and SVG sources clean.
- Use `python -m doc_tools.manage_docs --lint` (or the Makefile targets) before submitting changes; CI mirrors this exact pipeline.
- PDF deliverables must be rendered via `tools/pdf_build.py` so MkDocs and WeasyPrint share the CSS that the site uses.
