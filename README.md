# uDocket MVP Skeleton (Dockerized) — v0.12

This package includes fixes for Pydantic v2 (uses `pydantic-settings`), explicit `PYTHONPATH=/udocket`,
and module discovery (`db/__init__.py`, `config/__init__.py`).

## Quick start
1) Implement or customise your **pilot agent** inside the importable interface:
   `packages/udocket_core/agents/transcribe_lib.py` (see `TranscriptionAgent`).
2) Copy `.env.example` to `.env` and fill required values.
   - Postgres defaults are provided; start the bundled database with `PROJECT_NAME=udocket-dev make stack.up SERVICES=postgres`.
   - The container entrypoint runs `python manage.py migrate`, `python manage.py enable_rls`, and `python manage.py bootstrap_defaults` automatically; you can rerun them manually if needed.
   - `APP_ROOT` defaults to `/udocket` inside containers; update it (and derived paths such as `STORAGE_ROOT`) when running directly on your host.
   - Runtime configuration checks run on startup. Use `UDOCKET_SKIP_RUNTIME_CHECKS=1` only for short-lived maintenance commands (e.g., a one-off `manage.py collectstatic` in CI); the core stack should run with validation enabled.
3) Install the [`uv` CLI](https://astral.sh/uv) so local scripts and containers use the same dependency manager.
4) Local parity: sync the dev dependencies for each project (uv creates an isolated `.venv` beside every project automatically):

   ```bash
   uv sync --frozen --group dev --project apps/platform
   uv sync --frozen --group dev --project packages/udocket_common
   uv sync --frozen --group dev --project packages/udocket_core
   ```

   No manual activation is required—`uv run --project <path> …` will always pick the matching virtualenv.

   Everyday quality gates wrap uv automatically:

   ```bash
   # Tests
   make all.test          # common → core → platform → docs

   # Lint + formatting + typing
   make all.lint
   make all.type

   # Apply formatting/autofixes when needed
   make all.fix

   # Export pip-compatible manifests (pre-commit runs this automatically)
   make all.export-reqs
   # Prompt resources
   make prompts.lint
   ```

   **Testing reminders**

   - Prefer `make all.test` to fan out across common/core/platform/docs with the correct interpreters.
   - Platform/common/core suites share the `apps/platform` environment: `uv run --project apps/platform --extra dev pytest -n auto -q`.
   - Docs tooling has its own environment: `uv run --project packages/udocket_docs --extra dev python -m doc_tools.pytest_runner` (add `--coverage` or use `make docs.test.coverage` when needed).
   - Avoid running `pytest` from the repo root; it mixes Django+docs tests and requires incompatible dependency sets.

   Prompt templates live under `packages/udocket_prompts`. Validate changes with `make prompts.lint`, or render a specific prompt via `make prompts.render DOMAIN=analyze KEY=system_summary [LOCALE=en-CA] [VARS=vars.json]` when iterating on copy.

5) Build & run the stack:

```bash
PROJECT_NAME=udocket-dev make stack.up
```

   Need the raw compose invocation? Run `PROJECT_NAME=udocket-dev docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.cache.yml up --build -d` instead.

- Platform (UI + API) → http://localhost:8000

- Sanity check the running services at any time:

```bash
PROJECT_NAME=udocket-dev make stack.smoke
```

### Optional: enable BuildKit cache reuse

- Create a container-based builder once: `docker buildx create --name udocket --driver docker-container --bootstrap --use`.
- Pre-create cache directories (idempotent; use `sudo` if previous builds created root-owned paths) via `make build.cache.clean` (runs `scripts/setup_buildx_cache.sh` under the hood):

  ```bash
  ./scripts/setup_buildx_cache.sh
  ```

- Cache directories live under `.docker/buildx-cache/` (platform, platform_worker, platform_beat, keycloak, platform-dev, docs). Host and devcontainer builds share them automatically.
- `make images.cache.warm` primes the BuildKit cache layers for the platform, docs, and keycloak images when you want warmer Bake runs without producing artifacts.
- To read/write caches, include the dev overlay: `PROJECT_NAME=udocket-dev docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.cache.yml build`. Skip it for legacy builds or first-run setups to avoid import warnings.
- VS Code devcontainer users can opt in by appending `../docker-compose.cache.yml` to the `dockerComposeFile` list in `.devcontainer/devcontainer.json`.

### Compose environments

- **Development** — the Makefile defaults to `PROJECT_NAME=udocket-dev` and uses the dev overlay automatically. The raw command is:

  ```bash
  PROJECT_NAME=udocket-dev docker compose \
    -f docker-compose.yml \
    -f docker-compose.dev.yml \
    -f docker-compose.cache.yml \
    up -d
  ```

  Use `make stack.up`, `make stack.down`, and `make stack.logs` to manage the dev stack. Override `PROJECT_NAME` when you want side-by-side stacks (e.g., `PROJECT_NAME=my-feature make stack.up`).

- Docs tooling uses the same overlay. Copy `packages/udocket_docs/.env.example` to `packages/udocket_docs/.env` before running `make docs.build` or `make docs.preview`.

- **Production** — run the base compose file plus the production overlay after preparing a production `.env` (secrets, SSL, database, etc.) and copying `storage/` to persistent storage:

```bash
PROJECT_NAME=udocket docker compose \
    -f docker-compose.yml \
    -f docker-compose.prod.yml \
    up -d
  ```

  Bind host ports in `docker-compose.prod.yml` or layer another override file if you front the stack with Nginx/Traefik. In production, terminate TLS at the proxy; Keycloak continues to listen on 8085 inside the compose network.

- Every first-party service (platform web, worker, beat, docs toolbox, Keycloak) runs with `/udocket` as the working directory and resolves storage under `/udocket/storage`. When authoring new compose overlays or Dockerfiles, keep that convention so runtime path helpers continue to work across environments.

- See `docs/ops/prod-overlay-checklist.md` for the canonical Keycloak proxy layout and the post-deployment verification steps we expect on every rollout.

- To inspect a production stack quickly:

```bash
PROJECT_NAME=udocket make stack.prod.ps
PROJECT_NAME=udocket make stack.prod.logs
```

## Continuous Integration

- GitHub Actions runs Ruff, Pyright, and Mypy in parallel matrices per package so lint and type regressions surface quickly.
- Package-specific pytest jobs execute with `-n auto` and publish XML/HTML coverage; a follow-up job combines reports for dashboards.
- `make prompts.lint` and `make all.export-reqs` are enforced in CI (and pre-commit) to keep prompt metadata and requirements manifests deterministic.

### Maintenance shortcuts

- Run `make help` to list all curated commands (builds, linting, cache maintenance, Docker utilities).
- Use `make compose.reset CONFIRM=1` when you need a clean slate: stops the stack, deletes project images, clears volumes and removes orphan containers.
- `make docker.prune CONFIRM=1` performs the equivalent of `docker container/image/network/volume prune --force` in one go.
- `make buildx.du`, `make buildx.prune CONFIRM=1`, and `make buildx.builders.reset CONFIRM=1` show cache size, prune caches, and delete non-default builders safely.
- `make context.list` lists Docker contexts; `make context.remove CONTEXT=name CONFIRM=1` removes a specific one, and `make context.clean CONFIRM=1` drops everything except `default`.
- `make docker.reset CONFIRM=1` bundles the heavy-duty cleanup (compose reset, prunes, builder cleanup) followed by `docker du` to verify reclaimed space.
- Need help by topic? Run `make <group>.help` for a filtered list (labels are lowercased with punctuation mapped to dots, e.g. `make tests.help`, `make docker.images.help`, `make docker.buildx.help`).
- Build production-ready images without the dev overlay using `PROJECT_NAME=udocket make images.build.prod`.

### Common Make arguments

Most targets accept optional variables so you can customize behaviour without editing the Makefile:

- `CONFIRM=1` — required for destructive actions (prune, reset, delete) as a safety interlock.
- `SERVICES="platform platform_worker"` — scope stack commands such as `make stack.up` to a subset of services.
- `PLATFORMS=linux/amd64,linux/arm64` — run `make images.build` for multiple architectures via Buildx Bake.
- `PROGRESS=auto` — switch Bake progress output from the default `plain` stream to an interactive view.
- `LOAD=1` or `PUSH=1` — flags for `make images.build` to load into the local Docker daemon or push to the configured registry.
- `TAG=v1.2.3` / `REGISTRY=ghcr.io/acme` — override image tags/registry when baking release artifacts.
- `FOLLOW=0` — disable log streaming in `make stack.logs` and print the current buffer instead.

## Shared Python packages
- Shared, framework-agnostic helpers live under `packages/udocket_common`. Import them via `packages.udocket_common.*` (the repo root sits on `PYTHONPATH` in every container and the dev workflow).
- Package-specific helpers continue to reside under their respective package namespaces (e.g., `packages.udocket_core.*`). Only promote utilities into `udocket_common` when they have no dependencies on Django, Celery, or provider SDKs.
- If you later publish the packages independently, either install them side-by-side or add a top-level shim that re-exports `packages.udocket_common` — avoid hand-rolled relative imports to keep the path story predictable.

## Notes
- Postgres is now the default application database. Per-organization row-level security is enforced via `python manage.py enable_rls`.
- Local development bootstrap is controlled via `PLATFORM_BOOTSTRAP_ENABLED`. The default `.env.example` seeds an `admin/changeme` superuser, a demo organization, and permission presets; override or disable these variables for production.
- Default bootstrap values also live in `config/bootstrap_defaults.json`. Point `PLATFORM_BOOTSTRAP_CONFIG` at a custom file to tailor per-environment seeds without baking credentials into the image.
- Django admin remains limited to superusers; seeded superusers can also sign in through `/login/` to access the tenant-scoped UI while staff/non-admin accounts rely solely on the UI.
- Application migrations were flattened into new `0001_initial.py` files for the local apps; run `PROJECT_NAME=udocket-dev docker compose -f docker-compose.yml -f docker-compose.dev.yml down --volumes` after pulling to ensure your database is recreated before starting the stack.
- Azure OpenAI providers now enforce Canada-only endpoints (canadacentral/canadaeast). Set the per-provider `allow_non_ca_region` flag only for temporary local testing; production deployments must stay in-region.
- Media storage is tenant-aware: artifacts for organization `ORG123` live under `/media/tenants/ORG123/cases/<CASE_ID>/...`.
- Run platform/common/core tests from the dev container with `uv run --project apps/platform --extra dev pytest` (or `make platform.test`). Docs tests belong to `packages/udocket_docs` and should be invoked via `uv run --project packages/udocket_docs --extra dev python -m doc_tools.pytest_runner`. Avoid calling `pytest` from the repo root to prevent dependency bleed.
- Remote dev: open the repository in VS Code using **Dev Containers > Reopen in Container** to attach to the `platform-dev` service defined under `.devcontainer/` (starts alongside Postgres and Redis).
- Permissions: Visit `/permissions/` for a read-only catalog of artifact fields, presets, and roles (edits still happen via Django admin for MVP).
- Platform uploads let you choose `batch` (default) or `on-demand` transcription.
- Batch mode optionally enables speaker diarization via UI toggle or `--diarization` flag.

## Authentication & dashboard flow
- Sign in at `/login/` to use the themed welcome screen. Local username/password login remains available in development, while production instances surface a Single Sign-On button when OIDC is configured.
- After authenticating, members with access to multiple organizations land on the organization chooser. Pick a workspace to continue; single-organization members are auto-forwarded to the dashboard.
- The dashboard is now widget-driven. Metrics, case tables, job summaries, and upcoming deadlines are rendered as modular widgets that can be customized per organization as template overrides are introduced (see `docs/dashboard_widgets.md`).

## Transcription Modes
- Batch: audio is uploaded to Azure Blob Storage; the agent invokes Azure Batch Transcription using an HTTPS SAS URL.
  - Requires Azure Storage credentials in `.env`:
    - `AZURE_BLOB_ACCOUNT` and `AZURE_BLOB_KEY` (or `AZURE_BLOB_CONNECTION_STRING`)
    - `AZURE_BLOB_CONTAINER` (e.g., `udocket-audio`)
    - Optional: `AZURE_BLOB_SAS_TTL_MIN` (default 120)
  - In the platform UI, pick “Batch” and optionally enable “Diarization”.
  - Requires Azure Speech resource tier Standard (S0). Free (F0) keys are rejected by the Batch API.
  - Diarization is supported only in Batch mode in this project. Output includes per-utterance timestamps and `SPK_n` labels.
  - Duration in the transcript header is computed from the Batch result (offset + duration), so it’s accurate for remote files.
  - Optional hashing of remote audio for provenance:
    - `BATCH_HASH_REMOTE=1` to stream and compute SHA256 of the source URL prior to transcription
    - `BATCH_HASH_MAX_MB=200` caps hashing to URLs ≤ this many MB (default 200)
    - If available, Blob `Content-MD5` is also captured.
- On-demand: the agent streams local audio via the Speech SDK recognizer (fast, no Blob required).

## Azure Setup (batch mode)
1) Create a Storage account and a private container (e.g., `udocket-audio`).
2) Add env vars in `.env` as above; rebuild the Django platform worker: `PROJECT_NAME=udocket-dev make images.build IMAGES=platform_worker`.
   - Fallback raw command: `PROJECT_NAME=udocket-dev docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.cache.yml build platform_worker`.
3) Run `PROJECT_NAME=udocket-dev make stack.up`. The Celery worker in `apps.platform` uploads audio and passes a SAS URL to the agent.
   - Fallback raw command: `PROJECT_NAME=udocket-dev docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.cache.yml up -d`.
4) Create an Azure Speech resource in the same Canada region (canadacentral/canadaeast) with tier Standard (S0) and set `AZURE_SPEECH_KEY`/`AZURE_SPEECH_REGION`.

## Roadmap
- Platform migration and consolidation plan: see `docs/ROADMAP.md`.

## Devcontainer notes (persisting chat sessions)
- Rebuilding the VS Code devcontainer used to wipe CLI/chat history stored under the container HOME.
- The devcontainer compose now mounts persistent volumes for `/root/.config`, `/root/.cache`, and `/root/.local/share` so tools like Codex CLI and editors retain session data across rebuilds.
- To apply: Reopen in Container (Rebuild) from VS Code. Existing named volumes are reused automatically; nothing else is required.
