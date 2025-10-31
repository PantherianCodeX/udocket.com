PYTHON ?= python
UV ?= uv

.PHONY: init-precommit typing type-baseline type-strict tests ci-check typing-audit typing-dashboard typing-readiness typing-ci typing-clean-cache

init-precommit:
	$(UV) pip install --quiet pre-commit || true
	pre-commit install

typing: type-baseline type-strict

type-baseline:
	pyright
	mypy

type-strict:
	$(PYTHON) scripts/typing/ci_enforce_strict.py
	$(PYTHON) scripts/typing/check_strict.py --tool both

tests:
	pytest -q

ci-check: typing tests

# --- typewiz helpers ---
reports/typing:
	mkdir -p reports/typing

typing-audit: reports/typing
	uv run --no-sync --project apps/platform typewiz audit --max-depth 3 --manifest reports/typing/typing_audit.json

typing-dashboard: typing-audit
	uv run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format markdown --output reports/typing/dashboard.md
	uv run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format html --output reports/typing/dashboard.html

typing-readiness: typing-audit
	uv run --no-sync --project apps/platform typewiz readiness --manifest reports/typing/typing_audit.json --level folder --status blocked --limit 20 || true
	uv run --no-sync --project apps/platform typewiz readiness --manifest reports/typing/typing_audit.json --level folder --status ready --limit 20 || true

# CI-focused target: produce manifest and exit non-zero on errors (default behavior per typewiz.toml)
typing-ci: reports/typing
	uv run --no-sync --project apps/platform typewiz audit --max-depth 3 --manifest reports/typing/typing_audit.json
	uv run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format json --output reports/typing/dashboard.json || true
	uv run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format markdown --output reports/typing/dashboard.md || true
	uv run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format html --output reports/typing/dashboard.html || true

typing-clean-cache:
	rm -f .typewiz_cache.json

DC := docker compose

lint-docs:
	$(DC) run --rm docs bash -lc 'cd packages/udocket_docs && uv run python -m docs.tools.manage_docs --lint'

sync-docs:
	$(DC) run --rm docs bash -lc 'cd packages/udocket_docs && uv run python -m docs.tools.manage_docs --sync'

build-docs:
	$(DC) run --rm docs bash -lc 'cd packages/udocket_docs && uv run python -m docs.tools.manage_docs --build'

preview-docs:
	$(DC) run --rm --service-ports docs bash -lc 'cd packages/udocket_docs && uv run mkdocs serve --config-file mkdocs.yml --dev-addr 0.0.0.0:8010'
