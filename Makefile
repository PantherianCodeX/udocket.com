PYTHON ?= python
UV ?= uv
DC := docker compose

COMPOSE_BASE := docker-compose.yml
COMPOSE_OVERRIDE := docker-compose.override.yml
COMPOSE_CACHE := docker-compose.cache.yml
COMPOSE_DEVCONTAINER := .devcontainer/docker-compose.devcontainer.yml

DEVCONTAINER_COMPOSE := $(DC) -f $(COMPOSE_BASE) -f $(COMPOSE_OVERRIDE) -f $(COMPOSE_CACHE) -f $(COMPOSE_DEVCONTAINER)
DOCS_COMPOSE := $(DC) -f $(COMPOSE_BASE) -f $(COMPOSE_CACHE)

.PHONY: help init-precommit typing type-baseline type-strict tests ci-check typing-audit typing-dashboard typing-readiness typing-ci \
	typing-clean-cache clean-typewiz-cache clean-mypy-cache clean-pytest-cache clean-pyright-cache clean-coverage-cache clean-all-caches \
	build-devcontainer up-devcontainer down-devcontainer build-docs-image warm-build-cache clear-build-cache \
	docker-compose-reset docker-prune-all buildx-du buildx-prune buildx-reset docker-contexts docker-context-rm docker-context-clean \
	docker-system-df docker-maintenance

help: ## Display this help text with the most common targets
	@echo "Available make targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS=":.*##"}; {printf "  %-28s %s\n", $$1, $$2}'

init-precommit: ## Install pre-commit and register git hooks
	$(UV) pip install --quiet pre-commit || true
	pre-commit install

tests: ## Execute pytest suite quietly
	pytest -q

typing: type-baseline type-strict ## Run baseline and strict typing checks

typing-baseline: ## Run pyright and mypy type checks
	pyright
	mypy

typing-strict: ## Enforce strict typing gates
	$(PYTHON) scripts/typing/ci_enforce_strict.py
	$(PYTHON) scripts/typing/check_strict.py --tool both

# CI-focused target: produce manifest and exit non-zero on errors (default behavior per typewiz.toml)
typing-ci: reports/typing ## CI-focused Typewiz run (JSON + markdown + HTML where possible)
	uv run --no-sync --project apps/platform typewiz audit --max-depth 3 --manifest reports/typing/typing_audit.json
	uv run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format json --output reports/typing/dashboard.json || true
	uv run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format markdown --output reports/typing/dashboard.md || true
	uv run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format html --output reports/typing/dashboard.html || true

ci-check: typing tests ## Run typing checks and tests (CI parity)

# --- typewiz helpers ---
typewiz-audit: reports/typing ## Generate Typewiz audit manifest
	uv run --no-sync --project apps/platform typewiz audit --max-depth 3 --manifest reports/typing/typing_audit.json

typewiz-dashboard: typing-audit ## Render Typewiz dashboards (MD + HTML)
	uv run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format markdown --output reports/typing/dashboard.md
	uv run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format html --output reports/typing/dashboard.html

typewiz-readiness: typing-audit ## Show Typewiz readiness summary (blocked/ready folders)
	uv run --no-sync --project apps/platform typewiz readiness --manifest reports/typing/typing_audit.json --level folder --status blocked --limit 20 || true
	uv run --no-sync --project apps/platform typewiz readiness --manifest reports/typing/typing_audit.json --level folder --status ready --limit 20 || true

# --- cache cleaning ---
cache-clean-typewiz: ## Drop Typewiz caches and generated reports
	rm -f .typewiz_cache.json
	rm -rf reports/typing

cache-clean-mypy: ## Remove mypy cache directory
	rm -rf .mypy_cache

cache-clean-pytest: ## Remove pytest cache directory
	rm -rf .pytest_cache

cache-clean-pyright: ## Remove Pyright cache directory
	rm -rf .pyrightcache

cache-clean-coverage: ## Remove coverage artifacts
	rm -f .coverage
	rm -rf htmlcov

cache-clean-all: cache-clean-typewiz cache-clean-mypy cache-clean-pytest cache-clean-pyright cache-clean-coverage ## Remove all local caches (typing, tests, coverage)

# --- docker build ---
devcontainer-build: ## Build the VS Code devcontainer image
	$(DEVCONTAINER_COMPOSE) build platform-dev

devcontainer-up: ## Start the devcontainer service detached
	$(DEVCONTAINER_COMPOSE) up -d platform-dev

devcontainer-down: ## Stop the devcontainer stack and remove resources
	$(DEVCONTAINER_COMPOSE) down

doctools-build: ## Build the docs toolbox image with cache support
	$(DOCS_COMPOSE) build docs

doctools-up: ## Start the devcontainer service detached
	$(DOCS_COMPOSE) up -d

doctools-down: ## Stop the devcontainer stack and remove resources
	$(DOCS_COMPOSE) down

# --- build caches ---
build-cache-warm: ## Pre-warm BuildKit cache for platform images
	./scripts/devcontainer/warm_buildx_cache.sh

build-cache-clean: ## Remove BuildKit cache directories and recreate scaffolding
	rm -rf .docker/buildx-cache
	./scripts/setup_buildx_cache.sh

# --- doc tools compose shortcuts ---
docs-lint: ## Run docs linting pipeline inside docs toolbox
	$(DOCS_COMPOSE) run --rm docs bash -lc "set -euo pipefail; cd packages/udocket_docs && uv run python -m docs.tools.manage_docs --lint"

docs-sync: ## Sync docs artifacts (fetch/update remote content)
	$(DOCS_COMPOSE) run --rm docs bash -lc "set -euo pipefail; cd packages/udocket_docs && uv run python -m docs.tools.manage_docs --sync"

docs-build: ## Build docs output (PDF/HTML as configured)
	$(DOCS_COMPOSE) run --rm docs bash -lc "set -euo pipefail; cd packages/udocket_docs && uv run python -m docs.tools.manage_docs --build"

docs-preview: ## Serve docs locally with live reload
	$(DOCS_COMPOSE) run --rm --service-ports docs bash -lc "set -euo pipefail; cd packages/udocket_docs && uv run mkdocs serve --config-file mkdocs.yml --dev-addr 0.0.0.0:8010"

# --- docker/compose/buildx maintenance ---
docker-compose-reset: ## Stop stack, remove images/volumes/orphans for this project
	$(DC) down --rmi all --volumes --remove-orphans

docker-prune-all: ## Remove dangling containers/images/networks/volumes (global)
	docker container prune --force
	docker image prune --all --force
	docker network prune --force
	docker volume prune --force

docker-buildx-du: ## Show BuildKit cache disk usage
	docker buildx du || true

docker-buildx-prune: ## Prune all BuildKit caches for active builder
	docker buildx prune --all --force

docker-buildx-reset: ## Remove all non-default BuildKit builders
	docker buildx ls | awk 'NR>1 && $$1 != "default" {print $$1}' | xargs -r -n1 docker buildx rm

docker-contexts: ## List available Docker contexts
	docker context ls

docker-context-rm: ## Remove a Docker context (usage: make docker-context-rm CONTEXT=name)
	@if [ -z "$(CONTEXT)" ]; then echo "CONTEXT is required (usage: make docker-context-rm CONTEXT=name)"; exit 1; fi
	docker context rm "$(CONTEXT)"

docker-context-clean: ## Remove all non-default Docker contexts
	docker context ls --format '{{.Name}}' | awk '$$1 != "default"' | xargs -r -n1 docker context rm

docker-du: ## Display Docker disk usage summary
	docker system df

docker-reset-all: docker-compose-reset docker-prune-all docker-buildx-prune docker-buildx-reset docker-du ## Run full Docker/Buildx cleanup sequence
