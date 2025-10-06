PYTHON ?= python

.PHONY: init-precommit typing type-baseline type-strict tests ci-check

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

