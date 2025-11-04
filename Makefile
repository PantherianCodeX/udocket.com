MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

PYTHON ?= python
UV ?= uv
# Ensure uv uses a single shared env at repo root for local runs
export UV_PROJECT_ENVIRONMENT := $(CURDIR)/opt/venv
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
REGISTRY ?= ghcr.io/udocket
IMAGES ?= platform docs keycloak
SERVICES ?= platform platform_worker platform_beat redis postgres postgres-keycloak keycloak
SERVICE ?= platform
CMD ?=
DEV_SERVICE := platform-dev
DOCS_SERVICE := docs
PLATFORM_IMAGE := udocket-platform
DOCS_IMAGE := udocket-docs-toolbox
KEYCLOAK_IMAGE := udocket-keycloak
BAKE_EXTRA_FLAGS ?=

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

CONFIRM_CMD = @if [ "$(CONFIRM)" != "1" ]; then echo "Set CONFIRM=1 to run $@"; exit 1; fi

.PHONY: \
  help %.help \
  ci.precommit.install ci.check \
  all.test all.lint all.lint.ruff all.lint.format all.type all.type.mypy all.type.pyright all.format all.fix all.export-reqs \
  platform.test platform.test.verbose platform.test.failfast platform.test.cov platform.test.clean \
  platform.lint platform.lint.ruff platform.lint.format platform.type platform.type.mypy platform.type.pyright platform.format platform.fix platform.export-reqs \
  common.test common.test.verbose common.test.cov common.lint common.lint.ruff common.lint.format common.type common.type.mypy common.type.pyright common.format common.fix common.export-reqs common.clean \
  core.test core.test.verbose core.test.cov core.lint core.lint.ruff core.lint.format core.type core.type.mypy core.type.pyright core.format core.fix core.export-reqs core.clean \
  docs.test docs.test.coverage docs.lint docs.sync docs.preview docs.build docs.export-reqs \
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
ci.check: typing.run all.lint all.type all.test ## Run typing, lint, and tests (CI parity)

##@ Aggregate
all.test: ## Run all automated tests (common → core → platform → docs)
	@$(MAKE) common.test
	@$(MAKE) core.test
	@$(MAKE) platform.test
	@$(MAKE) docs.test

all.lint: ## Run lint + formatting checks for every project
	@$(MAKE) platform.lint
	@$(MAKE) common.lint
	@$(MAKE) core.lint
	@$(MAKE) docs.lint

all.lint.ruff: ## Run ruff lint across all projects
	@$(MAKE) platform.lint.ruff
	@$(MAKE) common.lint.ruff
	@$(MAKE) core.lint.ruff
	@$(MAKE) docs.lint

all.lint.format: ## Run formatting checks across code packages
	@$(MAKE) platform.lint.format
	@$(MAKE) common.lint.format
	@$(MAKE) core.lint.format

all.type: ## Run mypy + pyright on core code packages
	@$(MAKE) platform.type
	@$(MAKE) common.type
	@$(MAKE) core.type

all.type.mypy: ## Run mypy on all code packages
	@$(MAKE) platform.type.mypy
	@$(MAKE) common.type.mypy
	@$(MAKE) core.type.mypy

all.type.pyright: ## Run pyright on all code packages
	@$(MAKE) platform.type.pyright
	@$(MAKE) common.type.pyright
	@$(MAKE) core.type.pyright

all.format: ## Apply ruff formatting across code packages
	@$(MAKE) platform.format
	@$(MAKE) common.format
	@$(MAKE) core.format

all.fix: ## Apply ruff fixes across code packages
	@$(MAKE) platform.fix
	@$(MAKE) common.fix
	@$(MAKE) core.fix

all.export-reqs: ## Export pip-compatible requirement manifests for every project
	@python scripts/dev/export_requirements.py

##@ Platform • Quality
platform.test: ## Run platform pytest suite quietly
	$(UV) run --project apps/platform --extra dev pytest -q

platform.test.verbose: ## Run platform pytest suite verbosely
	$(UV) run --project apps/platform --extra dev pytest -v

platform.test.failfast: ## Run platform pytest suite, stopping on first failure
	$(UV) run --project apps/platform --extra dev pytest -x

platform.test.cov: ## Run platform pytest suite with coverage
	$(UV) run --project apps/platform --extra dev pytest --cov=apps/platform

platform.test.clean: ## Clean platform pytest cache
	rm -rf .pytest_cache

platform.lint: ## Run lint + formatting checks for platform code
	@$(MAKE) platform.lint.ruff
	@$(MAKE) platform.lint.format

platform.lint.ruff: ## Run ruff lint for platform code (legacy ignores applied)
	$(UV) run --project apps/platform --extra dev ruff check --extend-ignore E402,E501 apps/platform

platform.lint.format: ## Run ruff formatting checks for high-churn platform modules
	$(UV) run --project apps/platform --extra dev ruff format --check apps/platform/operations apps/platform/jobs || true

platform.type: ## Run mypy and pyright on platform code
	@$(MAKE) platform.type.mypy
	@$(MAKE) platform.type.pyright

platform.type.mypy: ## Run mypy on platform code
	$(UV) run --project apps/platform --extra dev mypy apps/platform

platform.type.pyright: ## Run pyright on platform code
	$(UV) run --project apps/platform --extra dev pyright apps/platform

platform.format: ## Apply ruff formatter to platform code
	$(UV) run --project apps/platform --extra dev ruff format apps/platform

platform.fix: ## Apply formatter + autofixes to platform code
	$(UV) run --project apps/platform --extra dev ruff format apps/platform
	$(UV) run --project apps/platform --extra dev ruff check --fix apps/platform

platform.export-reqs: ## Export platform requirements.txt manifests
	python scripts/dev/export_requirements.py platform

##@ Common Package (udocket_common)
common.test: ## Run udocket_common tests quietly
	$(UV) run --project packages/udocket_common --extra dev pytest -q packages/udocket_common

common.test.verbose: ## Run udocket_common tests verbosely
	$(UV) run --project packages/udocket_common --extra dev pytest -v packages/udocket_common

common.test.cov: ## Run udocket_common tests with coverage
	$(UV) run --project packages/udocket_common --extra dev pytest --cov=packages/udocket_common packages/udocket_common

common.clean: ## Clean udocket_common pytest cache
	rm -rf packages/udocket_common/.pytest_cache

common.lint: ## Run lint + formatting checks for udocket_common
	@$(MAKE) common.lint.ruff
	@$(MAKE) common.lint.format

common.lint.ruff: ## Run ruff lint for udocket_common
	$(UV) run --project packages/udocket_common --extra dev ruff check packages/udocket_common

common.lint.format: ## Run ruff formatting checks for udocket_common
	$(UV) run --project packages/udocket_common --extra dev ruff format --check packages/udocket_common

common.type: ## Run mypy and pyright on udocket_common
	@$(MAKE) common.type.mypy
	@$(MAKE) common.type.pyright

common.type.mypy: ## Run mypy on udocket_common
	$(UV) run --project packages/udocket_common --extra dev mypy packages/udocket_common

common.type.pyright: ## Run pyright on udocket_common
	$(UV) run --project packages/udocket_common --extra dev pyright packages/udocket_common

common.format: ## Apply ruff formatter to udocket_common
	$(UV) run --project packages/udocket_common --extra dev ruff format packages/udocket_common

common.fix: ## Apply formatter + autofixes to udocket_common
	$(UV) run --project packages/udocket_common --extra dev ruff format packages/udocket_common
	$(UV) run --project packages/udocket_common --extra dev ruff check --fix packages/udocket_common

common.export-reqs: ## Export udocket_common requirements manifests
	python scripts/dev/export_requirements.py common

##@ Core Package (udocket_core)
core.test: ## Run udocket_core tests quietly
	$(UV) run --project packages/udocket_core --extra dev pytest -q packages/udocket_core

core.test.verbose: ## Run udocket_core tests verbosely
	$(UV) run --project packages/udocket_core --extra dev pytest -v packages/udocket_core

core.test.cov: ## Run udocket_core tests with coverage
	$(UV) run --project packages/udocket_core --extra dev pytest --cov=packages/udocket_core packages/udocket_core

core.clean: ## Clean udocket_core pytest cache
	rm -rf packages/udocket_core/.pytest_cache

core.lint: ## Run lint + formatting checks for udocket_core
	@$(MAKE) core.lint.ruff
	@$(MAKE) core.lint.format

core.lint.ruff: ## Run ruff lint for udocket_core
	$(UV) run --project packages/udocket_core --extra dev ruff check packages/udocket_core

core.lint.format: ## Run ruff formatting checks for udocket_core
	$(UV) run --project packages/udocket_core --extra dev ruff format --check packages/udocket_core

core.type: ## Run mypy and pyright on udocket_core
	@$(MAKE) core.type.mypy
	@$(MAKE) core.type.pyright

core.type.mypy: ## Run mypy on udocket_core
	$(UV) run --project packages/udocket_core --extra dev mypy packages/udocket_core

core.type.pyright: ## Run pyright on udocket_core
	$(UV) run --project packages/udocket_core --extra dev pyright packages/udocket_core

core.format: ## Apply ruff formatter to udocket_core
	$(UV) run --project packages/udocket_core --extra dev ruff format packages/udocket_core

core.fix: ## Apply formatter + autofixes to udocket_core
	$(UV) run --project packages/udocket_core --extra dev ruff format packages/udocket_core
	$(UV) run --project packages/udocket_core --extra dev ruff check --fix packages/udocket_core

core.export-reqs: ## Export udocket_core requirements manifests
	python scripts/dev/export_requirements.py core

##@ Tests (compatibility aliases)
pytest.all: ## Alias for platform.test (temporary compatibility)
	@$(MAKE) platform.test

pytest.verbose: ## Alias for platform.test.verbose
	@$(MAKE) platform.test.verbose

pytest.failfast: ## Alias for platform.test.failfast
	@$(MAKE) platform.test.failfast

pytest.cov: ## Alias for platform.test.cov
	@$(MAKE) platform.test.cov

pytest.clean: ## Alias for platform.test.clean
	@$(MAKE) platform.test.clean

##@ Docs Toolbox

##@ Typing
typing.run: typing.baseline typing.strict ## Run baseline and strict typing checks
typing.baseline: ## Run pyright and mypy type checks
	mkdir -p reports/typing
	$(UV) run --project apps/platform --extra dev typewiz audit --mode current --fail-on warnings --manifest reports/typing/typing_audit.json --readiness --readiness-status blocked --readiness-status ready apps/platform/operations packages/udocket_core/agents packages/udocket_common
	$(UV) run --project apps/platform --extra dev mypy
typing.strict: ## Enforce strict typing gates
	$(UV) run --project apps/platform --extra dev python scripts/typing/ci_enforce_strict.py
	$(UV) run --project apps/platform --extra dev python scripts/typing/check_strict.py --tool both
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
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; $(UV) run python -m doc_tools.manage_docs --build"
docs.lint: ## Run docs linting pipeline inside the toolbox
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; $(UV) run python -m doc_tools.manage_docs --lint"
docs.sync: ## Sync docs artifacts (fetch/update remote content)
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; $(UV) run python -m doc_tools.manage_docs --sync"
docs.preview: ## Serve docs locally with live reload
	$(DOCS_COMPOSE) run --rm --service-ports $(DOCS_SERVICE) bash -lc "set -euo pipefail; $(UV) run mkdocs serve --config-file packages/udocket_docs/mkdocs.yml --dev-addr 0.0.0.0:8010"

DOCS_TEST_ARGS := $(filter-out docs.test,$(MAKECMDGOALS))
DOCS_COV_ARGS := $(filter-out docs.test.coverage,$(MAKECMDGOALS))

escape_dquotes = $(subst ",\",$(1))

.PHONY: docs.test docs.test.coverage

ifeq ($(firstword $(MAKECMDGOALS)),docs.test)
  DOCS_EXTRA_GOALS := $(DOCS_TEST_ARGS)
else ifeq ($(firstword $(MAKECMDGOALS)),docs.test.coverage)
  DOCS_EXTRA_GOALS := $(DOCS_COV_ARGS)
else
  DOCS_EXTRA_GOALS :=
endif

ifneq ($(strip $(DOCS_EXTRA_GOALS)),)
%:
	@:
endif

docs.test: $(DOCS_TEST_ARGS)
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -eo pipefail; DOCS_PYTEST_ARGS=\"$(call escape_dquotes,$(strip $(DOCS_TEST_ARGS)))\" $(UV) run --project packages/udocket_docs --extra dev python -m doc_tools.pytest_runner"

docs.test.coverage: $(DOCS_COV_ARGS)
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -eo pipefail; DOCS_PYTEST_ARGS=\"$(call escape_dquotes,$(strip $(DOCS_COV_ARGS)))\" $(UV) run --project packages/udocket_docs --extra dev python -m doc_tools.pytest_runner --coverage"

docs.export-reqs: ## Export docs toolbox requirements manifests
	python scripts/dev/export_requirements.py docs

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
	@$(MAKE) compose.reset CONFIRM=1
	@$(MAKE) docker.prune CONFIRM=1
	@$(MAKE) buildx.prune CONFIRM=1
	@$(MAKE) buildx.reset CONFIRM=1
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
	@$(MAKE) containers.stop.all CONFIRM=1
	@$(MAKE) containers.remove.all CONFIRM=1

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
	@$(MAKE) compose.reset CONFIRM=1
	@$(MAKE) images.prune CONFIRM=1
	@$(MAKE) volumes.prune CONFIRM=1
	@$(MAKE) networks.prune CONFIRM=1

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
	@$(MAKE) buildx.clean CONFIRM=1
	@$(MAKE) buildx.setup
buildx.reset.builders: ## Remove all non-default BuildKit builders
	$(CONFIRM_CMD)
	docker buildx ls | awk 'NR>1 && $$1 != "default" {print $$1}' | xargs -r -n1 docker buildx rm
buildx.reset.all: ## Full Buildx cleanup (caches and builders)
	$(CONFIRM_CMD)
	@$(MAKE) buildx.prune CONFIRM=1
	@$(MAKE) buildx.clean CONFIRM=1
	@$(MAKE) buildx.reset.builders CONFIRM=1


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
	@printf $(HELP_CMD_FORMAT) "CONFIRM=1" " Unlock guarded destructive commands"
	@printf $(HELP_CMD_FORMAT) "SERVICES=\"platform docs\"" " Scope stack actions"
	@printf $(HELP_CMD_FORMAT) "PLATFORMS=linux/amd64,linux/arm64" "Multi-arch Bake builds"
	@printf $(HELP_CMD_FORMAT) "FOLLOW=0" " Disable streaming in stack.logs"
	@printf "\nHint: run \033[36mmake <group>.help\033[0m for a specific group (e.g., 'tests.help').\n"
	@printf "See \033[32mREADME.md#Common Make arguments \033[0mfor additional options."

%.help:
	@$(UV) run --project apps/platform --extra dev python scripts/make_help.py "$*" "$(firstword $(MAKEFILE_LIST))"
TYPEWIZ_STATUSES ?= blocked ready
TYPEWIZ_LEVEL ?= folder
TYPEWIZ_LIMIT ?= 20
