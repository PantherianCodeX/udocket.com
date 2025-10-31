PYTHON ?= python

.PHONY: init-precommit typing type-baseline type-strict tests ci-check typing-audit typing-dashboard typing-readiness typing-ci typing-clean-cache

init-precommit:
	$(PYTHON) -m pip install pre-commit || true
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
	. ./.venv/bin/activate && typewiz audit --max-depth 3 --manifest reports/typing/typing_audit.json

typing-dashboard: typing-audit
	. ./.venv/bin/activate && typewiz dashboard --manifest reports/typing/typing_audit.json --format markdown --output reports/typing/dashboard.md
	. ./.venv/bin/activate && typewiz dashboard --manifest reports/typing/typing_audit.json --format html --output reports/typing/dashboard.html

typing-readiness: typing-audit
	. ./.venv/bin/activate && typewiz readiness --manifest reports/typing/typing_audit.json --level folder --status blocked --limit 20 || true
	. ./.venv/bin/activate && typewiz readiness --manifest reports/typing/typing_audit.json --level folder --status ready --limit 20 || true

# CI-focused target: produce manifest and exit non-zero on errors (default behavior per typewiz.toml)
typing-ci: reports/typing
	. ./.venv/bin/activate && typewiz audit --max-depth 3 --manifest reports/typing/typing_audit.json
	. ./.venv/bin/activate && typewiz dashboard --manifest reports/typing/typing_audit.json --format json --output reports/typing/dashboard.json || true
	. ./.venv/bin/activate && typewiz dashboard --manifest reports/typing/typing_audit.json --format markdown --output reports/typing/dashboard.md || true
	. ./.venv/bin/activate && typewiz dashboard --manifest reports/typing/typing_audit.json --format html --output reports/typing/dashboard.html || true

typing-clean-cache:
	rm -f .typewiz_cache.json

lint-docs:
	. ./.venv/bin/activate && python -m docs.tools.manage_docs --lint

sync-docs:
	. ./.venv/bin/activate && python -m docs.tools.manage_docs --sync

build-docs:
	. ./.venv/bin/activate && python -m docs.tools.manage_docs --build

preview-docs:
	. ./.venv/bin/activate && mkdocs serve -f docs/config/mkdocs.yml --dev-addr 0.0.0.0:8010
