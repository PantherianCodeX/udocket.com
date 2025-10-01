# uDocket — Configuration Guide

Scope: `config/` (shared pydantic settings loader) and Django settings under `apps/platform/config`.

## Pydantic Settings
- Centralized in `config/settings.py` with `.env` support.
- Enforce CA‑only Azure regions at validation time. Compute default sqlite path off `STORAGE_ROOT`.

## Django Settings
- Live in `apps/platform/config/settings`. Base resolves `STORAGE_ROOT` and robustly falls back to sqlite in dev (apps/platform/config/settings/base.py:1).
- Use `ENV_READ_DOTENV=1` only when intentionally loading `.env` directly; docker compose already provides env vars.

## URL Structure & Tenancy
- Prefer organization‑prefixed routes for UI and API: `/{org_slug}/cases/...`, `/{org_slug}/jobs/...`, and websockets `/ws/{org_slug}/jobs/<id>/`.
- Middleware should resolve `org_slug` to the active organization; reject cross‑org access.
- Websocket routing should mirror the same prefix to enforce scoping at connect time.

## Database Partitioning
- Default: single schema with `organization_id` columns and Postgres Row‑Level Security policies for defense‑in‑depth.
- Alternative: per‑org schemas or databases, controlled via environment. If adopted, set `search_path` per request/worker and run migrations per schema.

## Storage Layout
- Platform uses `MEDIA_ROOT/tenants/<org>/cases/<case_id>/...` (audio/transcript/analysis/ops). Always allocate via `ensure_case_dirs`.

## Security Defaults
- Keep DEBUG off in production; limit allowed hosts; enforce OIDC/Keycloak auth for DRF.
