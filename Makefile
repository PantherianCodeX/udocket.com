MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

PYTHON ?= python
UV ?= uv
PROJECT_NAME ?= udocket
DC := COMPOSE_PROJECT_NAME=$(PROJECT_NAME) docker compose

COMPOSE_BASE := docker-compose.yml
COMPOSE_DEV := docker-compose.dev.yml
COMPOSE_PROD := docker-compose.prod.yml
COMPOSE_CACHE := docker-compose.cache.yml
COMPOSE_DEVCONTAINER := .devcontainer/docker-compose.devcontainer.yml

BASE_COMPOSE := $(DC) -f $(COMPOSE_BASE)
DEV_COMPOSE := $(BASE_COMPOSE) -f $(COMPOSE_DEV)
PROD_COMPOSE := $(BASE_COMPOSE) -f $(COMPOSE_PROD)

DEVCONTAINER_COMPOSE := $(DEV_COMPOSE) -f $(COMPOSE_CACHE) -f $(COMPOSE_DEVCONTAINER)
DOCS_COMPOSE := $(DEV_COMPOSE) -f $(COMPOSE_CACHE)

define compose_shell
	@container_id="$$( $(1) ps -q $(2) 2>/dev/null )"; \
	if [ -n "$$container_id" ]; then \
	  $(1) exec $(2) bash -l; \
	else \
	  $(1) run --rm $(2) bash -l; \
	fi
endef

# Image/build orchestration
USE_BUILD ?= 1
PLATFORMS ?= linux/amd64
PROGRESS ?= plain
TAG ?= dev
LOCAL_TAG ?= dev
AUTO_PUSH ?= 1
RELEASE_PATTERN ?= ^v[0-9]
SKIP_PUSH ?= 0
LOAD ?= 0
PUSH ?=
REGISTRY ?= ghcr.io/udocket
IMAGES ?= platform docs keycloak
SERVICES ?= platform platform_worker platform_beat redis postgres postgres-keycloak keycloak
SERVICE ?= platform
CMD ?=
DEV_SERVICE := platform-dev
DOCS_SERVICE := docs
DOCSITE_CONTAINER ?= udocket-docs-site
DOCSITE_ADDR ?= 0.0.0.0
DOCSITE_HOST ?= localhost
DOCSITE_PORT ?= 8010
DOCSITE_URL ?= http://$(DOCSITE_HOST):$(DOCSITE_PORT)
PLATFORM_IMAGE := udocket-platform
DOCS_IMAGE := udocket-docs-toolbox
KEYCLOAK_IMAGE := udocket-keycloak
BAKE_EXTRA_FLAGS ?=

HOST_CPUS := $(shell nproc 2>/dev/null)
ifeq ($(strip $(HOST_CPUS)),)
  HOST_CPUS := $(shell sysctl -n hw.ncpu 2>/dev/null)
endif
ifeq ($(strip $(HOST_CPUS)),)
  HOST_CPUS := 4
endif
JOBS ?= $(HOST_CPUS)

empty :=
space := $(empty) $(empty)
comma := ,

ifneq ($(strip $(PUSH)),)
  DO_PUSH := $(PUSH)
else ifeq ($(AUTO_PUSH),1)
  DO_PUSH := $(shell if printf '%s' "$(TAG)" | grep -Eq '$(RELEASE_PATTERN)'; then printf '1'; else printf '0'; fi)
else
  DO_PUSH := 0
endif

ifeq ($(SKIP_PUSH),1)
  DO_PUSH := 0
endif

DO_LOAD := $(LOAD)
ifeq ($(strip $(DO_LOAD)),)
  DO_LOAD := 0
endif

ifneq ($(DO_PUSH),0)
  ifneq ($(strip $(DO_LOAD)),0)
    $(error Cannot push and load simultaneously; set LOAD=0 or PUSH=0.)
  endif
  ifeq ($(strip $(REGISTRY)),)
    $(error REGISTRY is required when pushing images; set REGISTRY or SKIP_PUSH=1.)
  endif
endif

PLATFORM_TAGS_LIST := $(PLATFORM_IMAGE):$(LOCAL_TAG)
DOCS_TAGS_LIST := $(DOCS_IMAGE):$(LOCAL_TAG)
KEYCLOAK_TAGS_LIST := $(KEYCLOAK_IMAGE):$(LOCAL_TAG)

ifneq ($(strip $(REGISTRY)),)
  PLATFORM_TAGS_LIST += $(REGISTRY)/$(PLATFORM_IMAGE):$(TAG)
  DOCS_TAGS_LIST += $(REGISTRY)/$(DOCS_IMAGE):$(TAG)
  KEYCLOAK_TAGS_LIST += $(REGISTRY)/$(KEYCLOAK_IMAGE):$(TAG)
endif

define buildx_tags_flag
$(if $(strip $(2)),--set $(1).tags=$(firstword $(2))$(foreach tag,$(wordlist 2,$(words $(2)),$(2)), --set $(1).tags+=$(tag)))
endef

BAKE_FILES := -f bake.hcl

BAKE_IMAGE_FLAGS := $(BAKE_FILES) --progress=$(PROGRESS) --set *.platform=$(PLATFORMS)
BAKE_IMAGE_FLAGS += $(call buildx_tags_flag,platform,$(PLATFORM_TAGS_LIST))
BAKE_IMAGE_FLAGS += $(call buildx_tags_flag,docs,$(DOCS_TAGS_LIST))
BAKE_IMAGE_FLAGS += $(call buildx_tags_flag,keycloak,$(KEYCLOAK_TAGS_LIST))
BAKE_IMAGE_FLAGS += $(BAKE_EXTRA_FLAGS)

ifneq ($(strip $(DO_LOAD)),0)
  BAKE_IMAGE_FLAGS += --load
endif
ifneq ($(DO_PUSH),0)
  BAKE_IMAGE_FLAGS += --push
endif

BAKE_CACHE_FLAGS := $(BAKE_FILES) --progress=$(PROGRESS) --set *.platform=$(PLATFORMS)
BAKE_CACHE_FLAGS += $(BAKE_EXTRA_FLAGS)

CONFIRM_CMD = @CONFIRM_TARGET="$@" $(PYTHON) scripts/confirm.py

.PHONY: \
  help %.help \
  ci.precommit.install ci.check \
  pytest.all pytest.verbose pytest.failfast pytest.cov pytest.clean \
  typing.run typing.baseline typing.strict typing.ci \
  typewiz.audit typewiz.dashboard typewiz.readiness typewiz.clean \
  clean.all clean.mypy clean.pyright clean.pycache clean.coverage \
  images.build images.load images.push images.cache.warm \
  stack.up stack.down stack.build stack.restart stack.logs stack.ps stack.smoke stack.exec \
  stack.prod.logs stack.prod.ps \
  platform.shell worker.shell beat.shell keycloak.shell \
  doctools.build doctools.up doctools.down doctools.shell \
  docs.build docs.lint docs.sync docs.preview \
  dev.build dev.up dev.down dev.shell \
  psql.shell keycloak.psql.shell \
  redis.shell redis.ping \
  docker.du docker.prune docker.reset \
  context.list context.remove context.clean \
  containers.list containers.list-running containers.stop.all containers.remove.all containers.prune containers.reset \
  images.list images.remove.all images.prune images.reset \
  networks.list networks.prune networks.reset \
  volumes.list volumes.prune volumes.reset \
  compose.ps compose.reset compose.reset.all \
  buildx.du buildx.setup buildx.inspect buildx.clean buildx.prune buildx.reset buildx.reset.builders buildx.reset.all

##@ CI
ci.precommit.install: ## Install pre-commit and register git hooks
	$(UV) pip install --quiet pre-commit || true
	pre-commit install
ci.check: typing.run docs.lint all.test ## Run typing checks, docs lint, and tests (CI parity)

##@ Tests
all.test: ## Run all automated test suites in parallel
	@$(MAKE) -j $(JOBS) DOCS_ARGS= common.test core.test platform.test docs.test

pytest.all: ## Execute pytest suite quietly (backwards compatible alias)
	@$(MAKE) all.test
pytest.verbose: ## Execute pytest suite with verbose output
	$(UV) run --project apps/platform --extra dev pytest -v
pytest.failfast: ## Execute pytest suite, stopping on first failure
	$(UV) run --project apps/platform --extra dev pytest -x
pytest.cov: ## Execute pytest suite with coverage reporting
	$(UV) run --project apps/platform --extra dev pytest --cov=apps/platform
pytest.clean: ## Remove pytest cache directory
	rm -rf .pytest_cache

common.test: ## Run udocket_common test suite
	$(UV) run --project apps/platform --extra dev pytest -n auto -q packages/udocket_common

core.test: ## Run udocket_core test suite
	$(UV) run --project apps/platform --extra dev pytest -n auto -q tests/udocket_core

platform.test: ## Run platform test suite
	$(UV) run --project apps/platform --extra dev pytest -n auto -q

##@ Typing
typing.run: typing.baseline typing.strict ## Run baseline and strict typing checks
typing.baseline: ## Run pyright and mypy type checks
	mkdir -p reports/typing
	$(UV) run --project apps/platform --extra dev typewiz audit --mode current --fail-on warnings --manifest reports/typing/typing_audit.json --readiness --readiness-status blocked --readiness-status ready apps/platform/operations packages/udocket_core/agents packages/udocket_common
	$(UV) run --project apps/platform --extra dev mypy
typing.strict: ## Enforce strict typing gates
	$(PYTHON) scripts/typing/ci_enforce_strict.py
	$(PYTHON) scripts/typing/check_strict.py --tool both
	$(UV) run --project apps/platform --extra dev typewiz readiness --manifest reports/typing/typing_audit.json --level $(TYPEWIZ_LEVEL) $(foreach status,$(TYPEWIZ_STATUSES),--status $(status)) --limit $(TYPEWIZ_LIMIT) || true
typing.ci: ## CI-focused Typewiz run (JSON + markdown + HTML where possible)
	$(UV) run --no-sync --project apps/platform typewiz audit --max-depth 3 --mode full --manifest reports/typing/typing_audit.json --readiness --readiness-status blocked --readiness-status ready apps/platform/operations packages/udocket_core/agents packages/udocket_common
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format json --output reports/typing/dashboard.json || true
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format markdown --output reports/typing/dashboard.md || true
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format html --output reports/typing/dashboard.html || true

##@ Typewiz
typewiz.audit: ## Generate Typewiz audit manifest
	$(UV) run --no-sync --project apps/platform typewiz audit --max-depth 3 --manifest reports/typing/typing_audit.json --readiness --readiness-status blocked --readiness-status ready apps/platform/operations packages/udocket_core/agents packages/udocket_common
typewiz.dashboard: ## Render Typewiz dashboards (MD + HTML)
	$(MAKE) typewiz.audit
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format markdown --output reports/typing/dashboard.md
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format html --output reports/typing/dashboard.html
typewiz.readiness: ## Show Typewiz readiness summary (blocked/ready folders)
	$(MAKE) typewiz.audit
	$(UV) run --no-sync --project apps/platform typewiz readiness --manifest reports/typing/typing_audit.json --level $(TYPEWIZ_LEVEL) $(foreach status,$(TYPEWIZ_STATUSES),--status $(status)) --limit $(TYPEWIZ_LIMIT) || true
typewiz.clean: ## Drop Typewiz caches and generated reports
	rm -rf .typewiz_cache
	rm -rf reports/typing

##@ Other Cache Cleaning
clean.mypy: ## Remove mypy cache directory
	rm -rf .mypy_cache
clean.pyright: ## Remove Pyright cache directory
	rm -rf .pyrightcache
clean.pycache: ## Remove Python bytecode and __pycache__ dirs across repo
	find . -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.py[co]' \) -delete
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
clean.coverage: ## Remove coverage artifacts
	rm -f .coverage
	rm -rf htmlcov
clean.all: typewiz.clean clean.mypy pytest.clean clean.pyright clean.coverage clean.pycache ## Remove all local caches (typing, typewiz, tests, coverage, bytecode)

##@ Images
images.build: ## Build images via Buildx Bake (defaults to Bake, release-aware push)
	@if [ "$(USE_BUILD)" = "1" ]; then \
	  docker buildx bake $(BAKE_IMAGE_FLAGS) $(IMAGES); \
else \
  $(BASE_COMPOSE) build $(IMAGES); \
fi
images.load: ## Build images and load into the local Docker daemon
	$(MAKE) images.build LOAD=1
images.push: ## Build images and push to the configured registry
	$(MAKE) images.build PUSH=1
images.cache.warm: ## Prime toolchain layers via Bake cache target
	docker buildx bake $(BAKE_CACHE_FLAGS) cache-warm

images.build.prod: ## Build images with production overlays only (no dev sync)
	$(PROD_COMPOSE) build $(IMAGES)

##@ Platform
stack.up: ## Start core stack detached (override with SERVICES="..." as needed)
	$(DEV_COMPOSE) up -d $(SERVICES)
stack.down: ## Stop stack containers
	$(DEV_COMPOSE) down
stack.build: ## Build platform-facing images (Bake pipeline)
	$(MAKE) images.build IMAGES="platform keycloak" LOAD=1
stack.restart: ## Restart stack services (override with SERVICES="...")
	$(DEV_COMPOSE) restart $(SERVICES)
stack.logs: ## Tail logs from core stack (FOLLOW=0 to disable streaming)
	@if [ "$(FOLLOW)" = "0" ]; then \
	  $(DEV_COMPOSE) logs $(SERVICES); \
	else \
	  $(DEV_COMPOSE) logs -f $(SERVICES); \
	fi
stack.ps: ## Show container status for this project
	$(DEV_COMPOSE) ps

stack.smoke: ## Quick sanity check that core services resolve and are running
	$(DEV_COMPOSE) config --services
	$(DEV_COMPOSE) ps

stack.exec: ## Execute a command inside a dev service (SERVICE=platform CMD="...")
	@if [ "$(strip $(CMD))" = "" ]; then \
	  echo "Set CMD=\"...\" to run inside the container."; \
	  exit 1; \
	fi
	$(DEV_COMPOSE) exec $(SERVICE) bash -lc "$(call escape_dquotes,$(strip $(CMD)))"

##@ Platform • Production
stack.prod.up: ## Start production stack with the production overlay
	$(PROD_COMPOSE) up -d $(SERVICES)
stack.prod.down: ## Stop production stack
	$(PROD_COMPOSE) down
stack.prod.logs: ## Tail logs from the production overlay stack (FOLLOW=0 to disable streaming)
	@if [ "$(FOLLOW)" = "0" ]; then \
	  $(PROD_COMPOSE) logs $(SERVICES); \
	else \
	  $(PROD_COMPOSE) logs -f $(SERVICES); \
	fi
stack.prod.ps: ## Show production overlay container status
	$(PROD_COMPOSE) ps

##@ Platform • Shells
platform.shell: ## Open a shell inside the platform container
	$(call compose_shell,$(DEV_COMPOSE),platform)
worker.shell: ## Open a shell inside the Celery worker container
	$(call compose_shell,$(DEV_COMPOSE),platform_worker)
beat.shell: ## Open a shell inside the Celery beat container
	$(call compose_shell,$(DEV_COMPOSE),platform_beat)

##@ Platform • Databases
psql.shell: ## Connect to the primary PostgreSQL service using psql
	$(DEV_COMPOSE) exec postgres bash -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

##@ Doctools • Environment
doctools.build: ## Build the docs toolbox image (Bake-driven)
	$(MAKE) images.build IMAGES=docs
doctools.up: ## Start the docs toolbox service detached
	$(DOCS_COMPOSE) up -d $(DOCS_SERVICE)
doctools.down: ## Stop the docs toolbox service and remove resources
	$(DOCS_COMPOSE) down
doctools.shell: ## Open a shell inside the docs toolbox container
	$(call compose_shell,$(DOCS_COMPOSE),$(DOCS_SERVICE))

##@ Doctools • Tools
docs.build: ## Render docs output (PDF/HTML as configured)
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; $(UV) run --project packages/udocket_docs --extra dev python -m doc_tools.manage_docs --build"
docs.lint: ## Run docs linting pipeline inside the toolbox
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; $(UV) run --project packages/udocket_docs --extra dev python -m doc_tools.manage_docs --lint"
docs.sync: ## Sync docs artifacts (fetch/update remote content)
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; $(UV) run --project packages/udocket_docs --extra dev python -m doc_tools.manage_docs --sync --verbose"
docs.preview: ## Open the docs site in your default browser
	$(PYTHON) -c "import os, webbrowser; webbrowser.open(os.environ.get('DOCSITE_URL', 'http://localhost:8010'))"
docs.verify: ## Validate docs build prerequisites without modifying artifacts
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; \
	TMP_DIR=$$(mktemp -d); \
	trap 'rm -rf \$$TMP_DIR' EXIT; \
	$(UV) run --project packages/udocket_docs --extra dev python -m doc_tools.sync.doc_assets --dry-run; \
	$(UV) run --project packages/udocket_docs --extra dev python -m doc_tools.check_asset_paths docs; \
	$(UV) run --project packages/udocket_docs --extra dev python -m doc_tools.build.diagram_index --check; \
	$(UV) run --project packages/udocket_docs --extra dev mkdocs build --strict --site-dir \$$TMP_DIR --config-file packages/udocket_docs/mkdocs.yml"

docs.clean: ## Remove rendered docs artifacts (diagrams + site outputs)
	rm -rf docs/build
	rm -rf packages/udocket_docs/build

##@ Docsite • MkDocs Dev Server
docsite.up: ## Start MkDocs live-reload server in the docs container
	@docker rm -f $(DOCSITE_CONTAINER) >/dev/null 2>&1 || true
	DOCS_DEV_PORT=$(DOCSITE_PORT) $(DOCS_COMPOSE) run -d --name $(DOCSITE_CONTAINER) --service-ports \
		-e DOCSITE_ADDR="$(DOCSITE_ADDR)" \
		-e DOCSITE_PORT="$(DOCSITE_PORT)" \
		$(DOCS_SERVICE) bash -lc "set +u; set -eo pipefail; $(UV) run --project packages/udocket_docs --extra dev mkdocs serve --config-file packages/udocket_docs/mkdocs.yml --dev-addr \"$${DOCSITE_ADDR:-0.0.0.0}:$${DOCSITE_PORT:-8010}\""
	@echo "[docsite] Serving docs at $(DOCSITE_URL)"

docsite.down: ## Stop the MkDocs dev server container
	$(CONFIRM_CMD)
	@docker rm -f $(DOCSITE_CONTAINER) >/dev/null 2>&1 || true

docsite.restart: ## Restart the MkDocs dev server container
	$(CONFIRM_CMD)
	@$(MAKE) docsite.down CONFIRM_BYPASS=1 >/dev/null
	@$(MAKE) docsite.up DOCSITE_ADDR="$(DOCSITE_ADDR)" DOCSITE_PORT="$(DOCSITE_PORT)" DOCSITE_HOST="$(DOCSITE_HOST)"

docsite.clean: ## Stop dev server and remove rendered docs artifacts
	$(CONFIRM_CMD)
	@$(MAKE) docsite.down CONFIRM_BYPASS=1 >/dev/null
	@$(MAKE) docs.clean CONFIRM_BYPASS=1

docsite.build: ## Build docs output (alias for docs.build)
	@$(MAKE) docs.build

escape_dquotes = $(subst ",\",$(1))

.PHONY: docs.preview docs.verify docs.clean docsite.up docsite.down docsite.restart docsite.clean docsite.build docs.test docs.test.coverage

DOCS_ARGS ?= $(filter-out docs.test docs.test.coverage,$(MAKECMDGOALS))

docs.test:
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -eo pipefail; DOCS_PYTEST_ARGS=\"$(call escape_dquotes,$(strip $(DOCS_ARGS)))\" $(UV) run --project packages/udocket_docs --extra dev python -m doc_tools.pytest_runner"

docs.test.coverage:
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -eo pipefail; DOCS_PYTEST_ARGS=\"$(call escape_dquotes,$(strip $(DOCS_ARGS)))\" $(UV) run --project packages/udocket_docs --extra dev python -m doc_tools.pytest_runner --coverage"

##@ Devcontainer • Environment
dev.build: ## Build the devcontainer image
	$(DEVCONTAINER_COMPOSE) build $(DEV_SERVICE)
dev.up: ## Start the devcontainer service detached
	$(DEVCONTAINER_COMPOSE) up -d $(DEV_SERVICE)
dev.down: ## Stop the devcontainer stack
	$(DEVCONTAINER_COMPOSE) down
dev.shell: ## Open a shell inside the devcontainer service
	$(call compose_shell,$(DEVCONTAINER_COMPOSE),$(DEV_SERVICE))

##@ KeyCloak
keycloak.shell: ## Open a shell inside the Keycloak container
	$(call compose_shell,$(DEVCONTAINER_COMPOSE),keycloak)
keycloak.psql.shell: ## Connect to the Keycloak PostgreSQL service using psql
	$(DEV_COMPOSE) exec postgres-keycloak bash -lc 'psql -U keycloak -d keycloak'

##@ Redis
redis.shell: ## Open a Redis CLI session inside the redis container
	$(DEV_COMPOSE) exec redis redis-cli
redis.ping: ## Run a Redis PING health-check command
	$(DEV_COMPOSE) exec redis redis-cli -n 1 ping

##@ Docker System
docker.du: ## Display Docker disk usage summary
	docker system df
docker.prune: ## Remove dangling containers/images/networks/volumes (global)
	$(CONFIRM_CMD)
	docker container prune --force
	docker image prune --all --force
	docker network prune --force
	docker volume prune --force
docker.reset: ## Run full Docker & Buildx cleanup sequence
	$(CONFIRM_CMD)
	@$(MAKE) compose.reset CONFIRM_BYPASS=1
	@$(MAKE) docker.prune CONFIRM_BYPASS=1
	@$(MAKE) buildx.prune CONFIRM_BYPASS=1
	@$(MAKE) buildx.reset CONFIRM_BYPASS=1
	@$(MAKE) docker.du

##@ Docker • Contexts
context.list: ## List available Docker contexts
	docker context ls
context.remove: ## Remove a Docker context (usage: make context.remove CONTEXT=name)
	@if [ -z "$(CONTEXT)" ]; then echo "CONTEXT is required (usage: make context.remove CONTEXT=name)"; exit 1; fi
	$(CONFIRM_CMD)
	docker context rm "$(CONTEXT)"
context.clean: ## Remove all non-default Docker contexts
	$(CONFIRM_CMD)
	docker context ls --format '{{.Name}}' | awk '$$1 != "default"' | xargs -r -n1 docker context rm

##@ Docker • Containers
containers.list: ## List all Docker containers
	docker ps -a
containers.list-running: ## List running Docker containers
	docker ps
containers.stop.all: ## Stop all running Docker containers
	$(CONFIRM_CMD)
	docker ps -q | xargs -r docker stop
containers.remove.all: ## Remove all Docker containers
	$(CONFIRM_CMD)
	docker ps -a -q | xargs -r docker rm
containers.prune: ## Remove all stopped Docker containers
	$(CONFIRM_CMD)
	docker container prune --force
containers.reset: ## Stop and remove all Docker containers
	$(CONFIRM_CMD)
	@$(MAKE) containers.stop.all CONFIRM_BYPASS=1
	@$(MAKE) containers.remove.all CONFIRM_BYPASS=1

##@ Docker • Images
images.list: ## List all Docker images
	docker images -a
images.remove.all: ## Remove all Docker images
	$(CONFIRM_CMD)
	docker images -a -q | xargs -r docker rmi -f
images.prune: ## Remove dangling Docker images
	$(CONFIRM_CMD)
	docker image prune --all --force
images.reset: ## Remove all Docker images
	$(CONFIRM_CMD)
	docker images -a -q | xargs -r docker rmi -f

##@ Docker • Networks
networks.list: ## List all Docker networks
	docker network ls
networks.prune: ## Remove all dangling Docker networks
	$(CONFIRM_CMD)
	docker network prune --force
networks.reset: ## Remove all Docker networks
	$(CONFIRM_CMD)
	docker network ls --format '{{.ID}}' | xargs -r docker network rm

##@ Docker • Volumes
volumes.list: ## List all Docker volumes
	docker volume ls
volumes.prune: ## Remove all dangling Docker volumes
	$(CONFIRM_CMD)
	docker volume prune --force
volumes.reset: ## Remove all Docker volumes
	$(CONFIRM_CMD)
	docker volume ls --format '{{.Name}}' | xargs -r docker volume rm

##@ Docker • Compose
compose.ps: ## List Docker containers for this project
	$(DEV_COMPOSE) ps
compose.reset: ## Stop stack, remove images/volumes/orphans for this project
	$(CONFIRM_CMD)
	$(DEV_COMPOSE) down --rmi all --volumes --remove-orphans
compose.reset.all: ## Full reset of Docker Compose resources for this project
	$(CONFIRM_CMD)
	@$(MAKE) compose.reset CONFIRM_BYPASS=1
	@$(MAKE) images.prune CONFIRM_BYPASS=1
	@$(MAKE) volumes.prune CONFIRM_BYPASS=1
	@$(MAKE) networks.prune CONFIRM_BYPASS=1

##@ Docker • Buildx
buildx.du: ## Show BuildKit cache disk usage
	docker buildx du || true
buildx.setup: ## Ensure Buildx builder is created and active
	./scripts/setup_buildx_builder.sh
buildx.inspect: ## Show Buildx builder details
	docker buildx inspect --bootstrap
buildx.clean: ## Remove Buildx cache directories
	$(CONFIRM_CMD)
	rm -rf .docker/buildx-cache
buildx.prune: ## Prune all BuildKit caches for the active builder
	$(CONFIRM_CMD)
	docker buildx prune --all --force
buildx.reset: ## Refresh Buildx cache directories
	$(CONFIRM_CMD)
	@$(MAKE) buildx.clean CONFIRM_BYPASS=1
	@$(MAKE) buildx.setup
buildx.reset.builders: ## Remove all non-default BuildKit builders
	$(CONFIRM_CMD)
	docker buildx ls | awk 'NR>1 && $$1 != "default" {print $$1}' | xargs -r -n1 docker buildx rm
buildx.reset.all: ## Full Buildx cleanup (caches and builders)
	$(CONFIRM_CMD)
	@$(MAKE) buildx.prune CONFIRM_BYPASS=1
	@$(MAKE) buildx.clean CONFIRM_BYPASS=1
	@$(MAKE) buildx.reset.builders CONFIRM_BYPASS=1


.DEFAULT_GOAL := help
HELP_GROUP_FORMAT := "\n\033[1m%s\033[0m\n"
HELP_CMD_FORMAT := "  \033[36m%-32s\033[0m %s\n"

help:
	@printf $(HELP_GROUP_FORMAT) "uDocket Makefile Commands"
	@printf $(HELP_GROUP_FORMAT) "Usage:"
	@printf "  \033[36m%s\033[0m%s\033[36m%-26s\033[0m%s\n" "make " "or" " make help" " View this help message"
	@awk 'BEGIN {FS=":.*##"} \
		/^##@/ { printf $(HELP_GROUP_FORMAT), substr($$0,5); next } \
		/^[a-zA-Z0-9_.-•]+:.*##/ { printf $(HELP_CMD_FORMAT), $$1, $$2 }' \
		$(MAKEFILE_LIST)
	@printf "\n"
	@printf $(HELP_GROUP_FORMAT) "Common arguments (override per call):"
	@printf $(HELP_CMD_FORMAT) "SERVICES=\"platform docs\"" " Scope stack actions"
	@printf $(HELP_CMD_FORMAT) "PLATFORMS=linux/amd64,linux/arm64" "Multi-arch Bake builds"
	@printf $(HELP_CMD_FORMAT) "FOLLOW=0" " Disable streaming in stack.logs"
	@printf "  Destructive commands prompt for confirmation automatically.\n"
	@printf "\nHint: run \033[36mmake <group>.help\033[0m for a specific group (e.g., 'tests.help').\n"
	@printf "See \033[32mREADME.md#Common Make arguments \033[0mfor additional options."

%.help:
	@$(UV) run --project packages/udocket_docs --extra dev python scripts/make_help.py "$*" "$(firstword $(MAKEFILE_LIST))"
TYPEWIZ_STATUSES ?= blocked ready
TYPEWIZ_LEVEL ?= folder
TYPEWIZ_LIMIT ?= 20
