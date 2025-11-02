MAKEFLAGS += --warn-undefined-variables
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

PYTHON ?= python
UV ?= uv
DC := docker compose

COMPOSE_BASE := docker-compose.yml
COMPOSE_OVERRIDE := docker-compose.override.yml
COMPOSE_CACHE := docker-compose.cache.yml
COMPOSE_DEVCONTAINER := .devcontainer/docker-compose.devcontainer.yml

DEVCONTAINER_COMPOSE := $(DC) -f $(COMPOSE_BASE) -f $(COMPOSE_OVERRIDE) -f $(COMPOSE_CACHE) -f $(COMPOSE_DEVCONTAINER)
DOCS_COMPOSE := $(DC) -f $(COMPOSE_BASE) -f $(COMPOSE_CACHE)

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

PLATFORM_TAGS := $(subst $(space),$(comma),$(strip $(PLATFORM_TAGS_LIST)))
DOCS_TAGS := $(subst $(space),$(comma),$(strip $(DOCS_TAGS_LIST)))
KEYCLOAK_TAGS := $(subst $(space),$(comma),$(strip $(KEYCLOAK_TAGS_LIST)))

BAKE_IMAGE_FLAGS := --progress=$(PROGRESS) --set common.platforms=$(PLATFORMS)
BAKE_IMAGE_FLAGS += --set platform.tags=$(PLATFORM_TAGS)
BAKE_IMAGE_FLAGS += --set docs.tags=$(DOCS_TAGS)
BAKE_IMAGE_FLAGS += --set keycloak.tags=$(KEYCLOAK_TAGS)
BAKE_IMAGE_FLAGS += $(BAKE_EXTRA_FLAGS)

ifneq ($(strip $(DO_LOAD)),0)
  BAKE_IMAGE_FLAGS += --load
endif
ifneq ($(DO_PUSH),0)
  BAKE_IMAGE_FLAGS += --push
endif

BAKE_CACHE_FLAGS := --progress=$(PROGRESS) --set common.platforms=$(PLATFORMS)
BAKE_CACHE_FLAGS += $(BAKE_EXTRA_FLAGS)

ALWAYS_CONFIRM ?=
ifeq ($(strip $(CONFIRM)),1)
  ALWAYS_CONFIRM := 1
endif
ifeq ($(strip $(ALWAYS_CONFIRM)),1)
  CONFIRM := 1
endif

CONFIRM_CMD = @if [ "$(CONFIRM)" != "1" ]; then echo "Set CONFIRM=1 (or ALWAYS_CONFIRM=1) to run $@"; exit 1; fi

.PHONY: \
  help \
  ci.precommit.install ci.check \
  tests.pytest \
  typing.run typing.baseline typing.strict typing.ci \
  typewiz.audit typewiz.dashboard typewiz.readiness typewiz.clean \
  cache.clean.all cache.clean.mypy cache.clean.pytest cache.clean.pyright cache.clean.coverage cache.clean.pycache \
  build.cache.clean \
  images.build images.load images.push images.cache.warm \
  stack.up stack.down stack.build stack.restart stack.logs stack.ps \
  platform.shell worker.shell beat.shell keycloak.shell \
  docs.env.build docs.env.up docs.env.down docs.env.shell \
  docs.tools.build docs.tools.lint docs.tools.sync docs.tools.preview \
  dev.build dev.up dev.down dev.shell \
  db.psql.shell db.keycloak.shell \
  redis.shell redis.ping \
  docker.system.du docker.system.prune docker.system.reset \
  docker.context.list docker.context.remove docker.context.clean \
  docker.containers.list docker.containers.list-running docker.containers.stop.all docker.containers.remove.all docker.containers.prune docker.containers.reset \
  docker.images.list docker.images.remove.all docker.images.prune docker.images.reset \
  docker.networks.list docker.networks.prune docker.networks.reset \
  docker.volumes.list docker.volumes.prune docker.volumes.reset \
  compose.ps compose.reset compose.reset.all \
  buildx.du buildx.setup buildx.inspect buildx.clean buildx.prune buildx.reset buildx.reset.all

.DEFAULT_GOAL := help

help: ## Show this help
	@awk 'BEGIN {FS=":.*##"} \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0,5); next } \
		/^[a-zA-Z0-9_.-]+:.*##/ { printf "  \033[36m%-32s\033[0m %s\n", $$1, $$2 }' \
		$(MAKEFILE_LIST)

##@ CI
ci.precommit.install: ## Install pre-commit and register git hooks
	$(UV) pip install --quiet pre-commit || true
	pre-commit install

ci.check: typing.run tests.pytest ## Run typing checks and tests (CI parity)

##@ Tests
tests.pytest: ## Execute pytest suite quietly
	pytest -q

##@ Typing
typing.run: typing.baseline typing.strict ## Run baseline and strict typing checks

typing.baseline: ## Run pyright and mypy type checks
	pyright
	mypy

typing.strict: ## Enforce strict typing gates
	$(PYTHON) scripts/typing/ci_enforce_strict.py
	$(PYTHON) scripts/typing/check_strict.py --tool both

typing.ci: reports/typing ## CI-focused Typewiz run (JSON + markdown + HTML where possible)
	$(UV) run --no-sync --project apps/platform typewiz audit --max-depth 3 --manifest reports/typing/typing_audit.json
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format json --output reports/typing/dashboard.json || true
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format markdown --output reports/typing/dashboard.md || true
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format html --output reports/typing/dashboard.html || true

##@ Typewiz
typewiz.audit: reports/typing ## Generate Typewiz audit manifest
	$(UV) run --no-sync --project apps/platform typewiz audit --max-depth 3 --manifest reports/typing/typing_audit.json

typewiz.dashboard: typewiz.audit ## Render Typewiz dashboards (MD + HTML)
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format markdown --output reports/typing/dashboard.md
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format html --output reports/typing/dashboard.html

typewiz.readiness: typewiz.audit ## Show Typewiz readiness summary (blocked/ready folders)
	$(UV) run --no-sync --project apps/platform typewiz readiness --manifest reports/typing/typing_audit.json --level folder --status blocked --limit 20 || true
	$(UV) run --no-sync --project apps/platform typewiz readiness --manifest reports/typing/typing_audit.json --level folder --status ready --limit 20 || true

typewiz.clean: ## Drop Typewiz caches and generated reports
	rm -rf .typewiz_cache
	rm -rf reports/typing

##@ Cache Cleaning
cache.clean.mypy: ## Remove mypy cache directory
	rm -rf .mypy_cache

cache.clean.pytest: ## Remove pytest cache directory
	rm -rf .pytest_cache

cache.clean.pyright: ## Remove Pyright cache directory
	rm -rf .pyrightcache

cache.clean.coverage: ## Remove coverage artifacts
	rm -f .coverage
	rm -rf htmlcov

cache.clean.pycache: ## Remove Python bytecode and __pycache__ dirs across repo
	find . -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.py[co]' \) -delete
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

cache.clean.all: typewiz.clean cache.clean.mypy cache.clean.pytest cache.clean.pyright cache.clean.coverage cache.clean.pycache ## Remove all local caches (typing, tests, coverage, bytecode)

build.cache.clean: ## Remove BuildKit cache directories and recreate scaffolding
	rm -rf .docker/buildx-cache
	./scripts/setup_buildx_cache.sh

##@ Images
images.build: ## Build images via Buildx Bake (defaults to Bake, release-aware push)
	@if [ "$(USE_BUILD)" = "1" ]; then \
	  docker buildx bake $(BAKE_IMAGE_FLAGS) $(IMAGES); \
	else \
	  $(DC) build $(IMAGES); \
	fi

images.load: ## Build images and load into the local Docker daemon
	$(MAKE) images.build LOAD=1

images.push: ## Build images and push to the configured registry
	$(MAKE) images.build PUSH=1

images.cache.warm: ## Prime toolchain layers via Bake cache target
	docker buildx bake $(BAKE_CACHE_FLAGS) cache-warm

##@ Platform
stack.up: ## Start core stack detached (override with SERVICES="..." as needed)
	$(DC) up -d $(SERVICES)

stack.down: ## Stop stack containers
	$(DC) down

stack.build: ## Build platform-facing images (Bake pipeline)
	$(MAKE) images.build IMAGES="platform keycloak"

stack.restart: ## Restart stack services (override with SERVICES="...")
	$(DC) restart $(SERVICES)

stack.logs: ## Tail logs from core stack (FOLLOW=0 to disable streaming)
	@if [ "$(FOLLOW)" = "0" ]; then \
	  $(DC) logs $(SERVICES); \
	else \
	  $(DC) logs -f $(SERVICES); \
	fi

stack.ps: ## Show container status for this project
	$(DC) ps

##@ Platform Shells
platform.shell: ## Open a shell inside the platform container
	$(DC) exec platform bash -l

worker.shell: ## Open a shell inside the Celery worker container
	$(DC) exec platform_worker bash -l

beat.shell: ## Open a shell inside the Celery beat container
	$(DC) exec platform_beat bash -l

keycloak.shell: ## Open a shell inside the Keycloak container
	$(DC) exec keycloak bash -l

##@ Docs Environment
docs.env.build: ## Build the docs toolbox image (Bake-driven)
	$(MAKE) images.build IMAGES=docs

docs.env.up: ## Start the docs toolbox service detached
	$(DOCS_COMPOSE) up -d $(DOCS_SERVICE)

docs.env.down: ## Stop the docs toolbox service and remove resources
	$(DOCS_COMPOSE) down

docs.env.shell: ## Open a shell inside the docs toolbox container
	$(DOCS_COMPOSE) exec $(DOCS_SERVICE) bash -l

##@ Docs Tools
docs.tools.build: ## Render docs output (PDF/HTML as configured)
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; cd packages/udocket_docs && $(UV) run python -m docs.tools.manage_docs --build"

docs.tools.lint: ## Run docs linting pipeline inside the toolbox
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; cd packages/udocket_docs && $(UV) run python -m docs.tools.manage_docs --lint"

docs.tools.sync: ## Sync docs artifacts (fetch/update remote content)
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; cd packages/udocket_docs && $(UV) run python -m docs.tools.manage_docs --sync"

docs.tools.preview: ## Serve docs locally with live reload
	$(DOCS_COMPOSE) run --rm --service-ports $(DOCS_SERVICE) bash -lc "set -euo pipefail; cd packages/udocket_docs && $(UV) run mkdocs serve --config-file mkdocs.yml --dev-addr 0.0.0.0:8010"

##@ Dev Environment
dev.build: ## Build the devcontainer image
	$(DEVCONTAINER_COMPOSE) build $(DEV_SERVICE)

dev.up: ## Start the devcontainer service detached
	$(DEVCONTAINER_COMPOSE) up -d $(DEV_SERVICE)

dev.down: ## Stop the devcontainer stack
	$(DEVCONTAINER_COMPOSE) down

dev.shell: ## Open a shell inside the devcontainer service
	$(DEVCONTAINER_COMPOSE) exec $(DEV_SERVICE) bash -l

##@ Databases
db.psql.shell: ## Connect to the primary PostgreSQL service using psql
	$(DC) exec postgres bash -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

db.keycloak.shell: ## Connect to the Keycloak PostgreSQL service using psql
	$(DC) exec postgres-keycloak bash -lc 'psql -U keycloak -d keycloak'

##@ Redis
redis.shell: ## Open a Redis CLI session inside the redis container
	$(DC) exec redis redis-cli

redis.ping: ## Run a Redis PING health-check command
	$(DC) exec redis redis-cli -n 1 ping

##@ Docker System
docker.system.du: ## Display Docker disk usage summary
	docker system df

docker.system.prune: ## Remove dangling containers/images/networks/volumes (global)
	$(CONFIRM_CMD)
	docker container prune --force
	docker image prune --all --force
	docker network prune --force
	docker volume prune --force

docker.system.reset: ## Run full Docker & Buildx cleanup sequence
	$(CONFIRM_CMD)
	@$(MAKE) compose.reset ALWAYS_CONFIRM=1
	@$(MAKE) docker.system.prune ALWAYS_CONFIRM=1
	@$(MAKE) buildx.prune ALWAYS_CONFIRM=1
	@$(MAKE) buildx.reset ALWAYS_CONFIRM=1
	@$(MAKE) docker.system.du

##@ Docker Contexts
docker.context.list: ## List available Docker contexts
	docker context ls

docker.context.remove: ## Remove a Docker context (usage: make docker.context.remove CONTEXT=name)
	@if [ -z "$(CONTEXT)" ]; then echo "CONTEXT is required (usage: make docker.context.remove CONTEXT=name)"; exit 1; fi
	$(CONFIRM_CMD)
	docker context rm "$(CONTEXT)"

docker.context.clean: ## Remove all non-default Docker contexts
	$(CONFIRM_CMD)
	docker context ls --format '{{.Name}}' | awk '$$1 != "default"' | xargs -r -n1 docker context rm

##@ Docker Containers
docker.containers.list: ## List all Docker containers
	docker ps -a

docker.containers.list-running: ## List running Docker containers
	docker ps

docker.containers.stop.all: ## Stop all running Docker containers
	$(CONFIRM_CMD)
	docker ps -q | xargs -r docker stop

docker.containers.remove.all: ## Remove all Docker containers
	$(CONFIRM_CMD)
	docker ps -a -q | xargs -r docker rm

docker.containers.prune: ## Remove all stopped Docker containers
	$(CONFIRM_CMD)
	docker container prune --force

docker.containers.reset: ## Stop and remove all Docker containers
	$(CONFIRM_CMD)
	@$(MAKE) docker.containers.stop.all ALWAYS_CONFIRM=1
	@$(MAKE) docker.containers.remove.all ALWAYS_CONFIRM=1

##@ Docker Images
docker.images.list: ## List all Docker images
	docker images -a

docker.images.remove.all: ## Remove all Docker images
	$(CONFIRM_CMD)
	docker images -a -q | xargs -r docker rmi -f

docker.images.prune: ## Remove dangling Docker images
	$(CONFIRM_CMD)
	docker image prune --all --force

docker.images.reset: ## Remove all Docker images
	$(CONFIRM_CMD)
	docker images -a -q | xargs -r docker rmi -f

##@ Docker Networks
docker.networks.list: ## List all Docker networks
	docker network ls

docker.networks.prune: ## Remove all dangling Docker networks
	$(CONFIRM_CMD)
	docker network prune --force

docker.networks.reset: ## Remove all Docker networks
	$(CONFIRM_CMD)
	docker network ls --format '{{.ID}}' | xargs -r docker network rm

##@ Docker Volumes
docker.volumes.list: ## List all Docker volumes
	docker volume ls

docker.volumes.prune: ## Remove all dangling Docker volumes
	$(CONFIRM_CMD)
	docker volume prune --force

docker.volumes.reset: ## Remove all Docker volumes
	$(CONFIRM_CMD)
	docker volume ls --format '{{.Name}}' | xargs -r docker volume rm

##@ Docker Compose
compose.ps: ## List Docker containers for this project
	$(DC) ps

compose.reset: ## Stop stack, remove images/volumes/orphans for this project
	$(CONFIRM_CMD)
	$(DC) down --rmi all --volumes --remove-orphans

compose.reset.all: ## Full reset of Docker Compose resources for this project
	$(CONFIRM_CMD)
	@$(MAKE) compose.reset ALWAYS_CONFIRM=1
	@$(MAKE) docker.images.prune ALWAYS_CONFIRM=1
	@$(MAKE) docker.volumes.prune ALWAYS_CONFIRM=1
	@$(MAKE) docker.networks.prune ALWAYS_CONFIRM=1

##@ Buildx
buildx.du: ## Show BuildKit cache disk usage
	docker buildx du || true

buildx.setup: ## Ensure Buildx builder is created and active
	./scripts/setup_buildx_builder.sh

buildx.inspect: ## Show Buildx builder details
	docker buildx inspect --bootstrap

buildx.clean: ## Remove Buildx cache directories
	$(CONFIRM_CMD)
	rm -rf .docker/buildx-cache
	./scripts/setup_buildx_cache.sh

buildx.prune: ## Prune all BuildKit caches for the active builder
	$(CONFIRM_CMD)
	docker buildx prune --all --force

buildx.reset: ## Remove all non-default BuildKit builders
	$(CONFIRM_CMD)
	docker buildx ls | awk 'NR>1 && $$1 != "default" {print $$1}' | xargs -r -n1 docker buildx rm

buildx.reset.all: ## Full Buildx cleanup (caches and builders)
	$(CONFIRM_CMD)
	@$(MAKE) buildx.prune ALWAYS_CONFIRM=1
	@$(MAKE) buildx.clean ALWAYS_CONFIRM=1
	@$(MAKE) buildx.reset ALWAYS_CONFIRM=1
