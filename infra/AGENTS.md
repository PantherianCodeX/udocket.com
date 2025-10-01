# uDocket — Infrastructure Guide

Scope: `infra/` (Dockerfiles, compose, logging), `.devcontainer/` for editor environments.

## Compose Services
- `platform`: Django ASGI app (UI + DRF + Channels) on `8000`.
- `platform_worker`/`platform_beat`: Celery worker and beat; depend on Redis and Postgres.
- `redis`, `postgres`, `keycloak` for local dev; Keycloak served on `8085` with imported realm.

## Live Reload (compose develop)
- Uses `develop.watch` for `apps/platform` and `packages`. Rebuild on requirements/Dockerfile changes.

## Environment
- `.env` provides shared variables; platform sets `DJANGO_SETTINGS_MODULE=apps.platform.config.settings.prod` in compose.
- Mount `./storage:/app/storage` for persistent media/db in dev.

## Tips
- Use `ALLOW_SQLITE_DEV_FALLBACK=true` to let platform fall back to sqlite when DB host is unavailable during quick local runs.
- For Azure interactions, keep keys and region limited to Canadian regions; never commit secrets.
