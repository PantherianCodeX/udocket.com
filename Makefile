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

CONFIRM_CMD = @if [ "$(CONFIRM)" != "1" ]; then echo "Set CONFIRM=1 to run $@"; exit 1; fi

.PHONY: \
  help \
  ci.help tests.help typing.help typewiz.help clean.help images.help platform.help platform.shells.help platform.databases.help \
  doctools.env.help doctools.tools.help dev.help keycloak.help redis.help \
  docker.system.help docker.contexts.help docker.containers.help docker.images.help docker.networks.help docker.volumes.help compose.help buildx.help \
  ci.precommit.install ci.check \
  pytest.all pytest.verbose pytest.failfast pytest.cov pytest.clean \
  typing.run typing.baseline typing.strict typing.ci \
  typewiz.audit typewiz.dashboard typewiz.readiness typewiz.clean \
  clean.all clean.mypy clean.pyright clean.pycache coverage.clean \
  images.build images.load images.push images.cache.warm \
  stack.up stack.down stack.build stack.restart stack.logs stack.ps \
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
ci.check: typing.run pytest.all ## Run typing checks and tests (CI parity)

##@ Tests
pytest.all: ## Execute pytest suite quietly
	pytest -q
pytest.verbose: ## Execute pytest suite with verbose output
	pytest -v
pytest.failfast: ## Execute pytest suite, stopping on first failure
	pytest -x
pytest.cov: ## Execute pytest suite with coverage reporting
	pytest --cov=apps/platform
pytest.clean: ## Remove pytest cache directory
	rm -rf .pytest_cache

##@ Typing
typing.run: typing.baseline typing.strict ## Run baseline and strict typing checks
typing.baseline: ## Run pyright and mypy type checks
	pyright
	mypy
typing.strict: ## Enforce strict typing gates
	$(PYTHON) scripts/typing/ci_enforce_strict.py
	$(PYTHON) scripts/typing/check_strict.py --tool both
typing.ci: ## CI-focused Typewiz run (JSON + markdown + HTML where possible)
	$(UV) run --no-sync --project apps/platform typewiz audit --max-depth 3 --manifest reports/typing/typing_audit.json
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format json --output reports/typing/dashboard.json || true
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format markdown --output reports/typing/dashboard.md || true
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format html --output reports/typing/dashboard.html || true

##@ Typewiz
typewiz.audit: ## Generate Typewiz audit manifest
	$(UV) run --no-sync --project apps/platform typewiz audit --max-depth 3 --manifest reports/typing/typing_audit.json
typewiz.dashboard: ## Render Typewiz dashboards (MD + HTML)
	$(MAKE) typewiz.audit
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format markdown --output reports/typing/dashboard.md
	$(UV) run --no-sync --project apps/platform typewiz dashboard --manifest reports/typing/typing_audit.json --format html --output reports/typing/dashboard.html
typewiz.readiness: ## Show Typewiz readiness summary (blocked/ready folders)
	$(MAKE) typewiz.audit
	$(UV) run --no-sync --project apps/platform typewiz readiness --manifest reports/typing/typing_audit.json --level folder --status blocked --limit 20 || true
	$(UV) run --no-sync --project apps/platform typewiz readiness --manifest reports/typing/typing_audit.json --level folder --status ready --limit 20 || true
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
coverage.clean: ## Remove coverage artifacts
	rm -f .coverage
	rm -rf htmlcov
clean.all: typewiz.clean clean.mypy pytest.clean clean.pyright coverage.clean clean.pycache ## Remove all local caches (typing, typewiz, tests, coverage, bytecode)

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

##@ Platform • Shells
platform.shell: ## Open a shell inside the platform container
	$(DC) exec platform bash -l
worker.shell: ## Open a shell inside the Celery worker container
	$(DC) exec platform_worker bash -l
beat.shell: ## Open a shell inside the Celery beat container
	$(DC) exec platform_beat bash -l

##@ Platform • Databases
psql.shell: ## Connect to the primary PostgreSQL service using psql
	$(DC) exec postgres bash -lc 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

##@ Doctools • Environment
doctools.build: ## Build the docs toolbox image (Bake-driven)
	$(MAKE) images.build IMAGES=docs
doctools.up: ## Start the docs toolbox service detached
	$(DOCS_COMPOSE) up -d $(DOCS_SERVICE)
doctools.down: ## Stop the docs toolbox service and remove resources
	$(DOCS_COMPOSE) down
doctools.shell: ## Open a shell inside the docs toolbox container
	$(DOCS_COMPOSE) exec $(DOCS_SERVICE) bash -l

##@ Doctools • Tools
docs.build: ## Render docs output (PDF/HTML as configured)
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; cd packages/udocket_docs && $(UV) run python -m docs.manage_docs --build"
docs.lint: ## Run docs linting pipeline inside the toolbox
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; cd packages/udocket_docs && $(UV) run python -m docs.manage_docs --lint"
docs.sync: ## Sync docs artifacts (fetch/update remote content)
	$(DOCS_COMPOSE) run --rm $(DOCS_SERVICE) bash -lc "set -euo pipefail; cd packages/udocket_docs && $(UV) run python -m docs.manage_docs --sync"
docs.preview: ## Serve docs locally with live reload
	$(DOCS_COMPOSE) run --rm --service-ports $(DOCS_SERVICE) bash -lc "set -euo pipefail; cd packages/udocket_docs && $(UV) run mkdocs serve --config-file mkdocs.yml --dev-addr 0.0.0.0:8010"

##@ Devcontainer • Environment
dev.build: ## Build the devcontainer image
	$(DEVCONTAINER_COMPOSE) build $(DEV_SERVICE)
dev.up: ## Start the devcontainer service detached
	$(DEVCONTAINER_COMPOSE) up -d $(DEV_SERVICE)
dev.down: ## Stop the devcontainer stack
	$(DEVCONTAINER_COMPOSE) down
dev.shell: ## Open a shell inside the devcontainer service
	$(DEVCONTAINER_COMPOSE) exec $(DEV_SERVICE) bash -l

##@ KeyCloak
keycloak.shell: ## Open a shell inside the Keycloak container
	$(DC) exec keycloak bash -l
keycloak.psql.shell: ## Connect to the Keycloak PostgreSQL service using psql
	$(DC) exec postgres-keycloak bash -lc 'psql -U keycloak -d keycloak'

##@ Redis
redis.shell: ## Open a Redis CLI session inside the redis container
	$(DC) exec redis redis-cli
redis.ping: ## Run a Redis PING health-check command
	$(DC) exec redis redis-cli -n 1 ping

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
	$(DC) ps
compose.reset: ## Stop stack, remove images/volumes/orphans for this project
	$(CONFIRM_CMD)
	$(DC) down --rmi all --volumes --remove-orphans
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

define PRINT_HELP_GROUP
	@printf $(HELP_GROUP_FORMAT) "$(1)"
	@grep -E '^$(2).*:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS=":.*##"} { printf $(HELP_CMD_FORMAT), $$1, $$2 }'
endef

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
	@printf "\nHint: run \033[36mmake <group>.help\033[0m (for example, \'tests.help\' or \'docker.images.help\') for focused command lists.\n"
	@printf "See \033[32mREADME.md#Common Make arguments \033[0mfor additional options.\n\n"

ci.help:
	$(call PRINT_HELP_GROUP,CI,ci\.)

tests.help:
	$(call PRINT_HELP_GROUP,Tests,pytest\.)

typing.help:
	$(call PRINT_HELP_GROUP,Typing,typing\.)

typewiz.help:
	$(call PRINT_HELP_GROUP,Typewiz,typewiz\.)

clean.help:
	$(call PRINT_HELP_GROUP,Other Cache Cleaning,(clean|coverage)\.)

images.help:
	$(call PRINT_HELP_GROUP,Images,images\.(build|load|push|cache\.warm))

platform.help:
	$(call PRINT_HELP_GROUP,Platform,stack\.)

platform.shells.help:
	$(call PRINT_HELP_GROUP,Platform Shells,(platform|worker|beat)\.shell)

platform.databases.help:
	$(call PRINT_HELP_GROUP,Platform Databases,psql\.shell)

doctools.env.help:
	$(call PRINT_HELP_GROUP,Doctools Environment,doctools\.)

doctools.tools.help:
	$(call PRINT_HELP_GROUP,Doctools Tools,docs\.(build|lint|sync|preview))

dev.help:
	$(call PRINT_HELP_GROUP,Devcontainer Environment,dev\.)

keycloak.help:
	$(call PRINT_HELP_GROUP,KeyCloak,keycloak\.)

redis.help:
	$(call PRINT_HELP_GROUP,Redis,redis\.)

docker.system.help:
	$(call PRINT_HELP_GROUP,Docker System,docker\.(du|prune|reset))

docker.contexts.help:
	$(call PRINT_HELP_GROUP,Docker Contexts,context\.)

docker.containers.help:
	$(call PRINT_HELP_GROUP,Docker Containers,containers\.)

docker.images.help:
	$(call PRINT_HELP_GROUP,Docker Images,images\.(list|remove\.all|prune|reset))

docker.networks.help:
	$(call PRINT_HELP_GROUP,Docker Networks,networks\.)

docker.volumes.help:
	$(call PRINT_HELP_GROUP,Docker Volumes,volumes\.)

compose.help:
	$(call PRINT_HELP_GROUP,Docker Compose,compose\.)

buildx.help:
	$(call PRINT_HELP_GROUP,Docker Buildx,buildx[._])
