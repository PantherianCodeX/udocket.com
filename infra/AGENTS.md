# uDocket — Infrastructure Guide

Scope: `infra/` (Dockerfiles, compose, logging), `.devcontainer/` for editor environments.

## Compose Services
- `platform`: Django ASGI app (UI + DRF + Channels) on `8000`.
- `platform_worker`/`platform_beat`: Celery worker and beat; depend on Redis and Postgres.
- `redis`, `postgres`, `keycloak` for local dev; Keycloak (26.4) served on `8085` with imported realm, the `organizations` feature enabled, and default client scopes requesting the `organizations` and `case_memberships` claims. Populate the `case_memberships` user attribute (e.g., `CASE-123:reviewer`) so login tokens carry membership data.

## Live Reload (compose develop)
- Uses `develop.watch` for `apps/platform` and `packages`. Rebuild on requirements/Dockerfile changes.

## Environment
- `.env` provides shared variables; platform sets `DJANGO_SETTINGS_MODULE=apps.platform.config.settings.prod` in compose.
- Mount `./storage:/app/storage` for persistent media/db in dev.

## Dockerfile Standards & Build Cache
- `infra/docker/Dockerfile.platform` keeps apt metadata setup (`apt-get update`, repo keyrings) isolated from package installs. Add new dependencies to the logical `RUN` block that matches their domain (core runtime vs. developer build toolchain vs. CLI/utilities) so cache busts stay scoped.
- The devcontainer post-create hook runs `scripts/setup_buildx_cache.sh` followed by `scripts/devcontainer/warm_buildx_cache.sh` to prime the local Buildx cache automatically (for both `platform` and `platform-dev`). Set `SKIP_BUILDX_WARM=1` to opt out or re-run the warm script manually after purging caches.
- Cache warm requires a Buildx builder using the `docker-container` driver. The warm script will reuse or create `udocket-builder` automatically when possible; if it still reports a legacy `docker` driver, run `docker buildx create --use --name udocket-builder --driver docker-container` inside the affected environment (host and/or devcontainer) and rerun the warm script.
- Build commands in compose use the local cache at `.docker/buildx-cache/<service>`—ensure that directory stays writable and check in new cache directories when adding services.

## Tips
- Use `ALLOW_SQLITE_DEV_FALLBACK=true` to let platform fall back to sqlite when DB host is unavailable during quick local runs.
- For Azure interactions, keep keys and region limited to Canadian regions; never commit secrets.
