# uDocket — Configuration Guide

Scope: `config/` (shared pydantic settings loader) and Django settings under `apps/platform/config`.

## Pydantic Settings
- Centralized in `config/settings.py` with `.env` support.
- Enforce CA‑only Azure regions at validation time. Compute default sqlite path off `STORAGE_ROOT`.
 - Roadmap: add cross‑provider, per‑org region policy (adjustable) and enforce across all LLM providers.

## Django Settings
- Live in `apps/platform/config/settings`. Base resolves `STORAGE_ROOT` and robustly falls back to sqlite in dev (apps/platform/config/settings/base.py:1).
- Use `ENV_READ_DOTENV=1` only when intentionally loading `.env` directly; docker compose already provides env vars.

## Typing expectations
- Enforce the strong typing policy in `docs/typing_refactor_plan.md` whenever you touch settings or configuration helpers.
- Update Pydantic models and Django settings signatures so mypy/pyright stay clean; do not add ignores to work around `_env_file` or similar keyword usage.
- Ensure new settings helpers are typed and compatible with pyright; consult `docs/typing-roadmap.md` before adding temporary ignores.

## URL Structure & Tenancy
- Prefer organization‑prefixed routes for UI and API: `/{org_slug}/cases/...`, `/{org_slug}/jobs/...`, and websockets `/ws/{org_slug}/jobs/<id>/`.
- Middleware should resolve `org_slug` to the active organization; reject cross‑org access.
- Websocket routing should mirror the same prefix to enforce scoping at connect time.

## Database Partitioning
- Default: single schema with `organization_id` columns and Postgres Row‑Level Security policies for defense‑in‑depth.
- Alternative: per‑org schemas or databases, controlled via environment. If adopted, set `search_path` per request/worker and run migrations per schema.

## Storage Layout
- Platform uses `MEDIA_ROOT/tenants/<ORG_ID>/cases/<case_id>/...` (audio/transcript/analysis/ops). Always allocate via `ensure_case_dirs`.

## Seeded Defaults (File‑Driven)
- Maintain file‑driven defaults for:
  - Roles (ensure `Reviewer` exists), reviewer policies (required counts, allowed roles per page/tool)
  - LLM stage maps per target (`summary`, `compose`, etc.)
  - DOCX template selection (per‑org) with uDocket default fallback
  - Alert thresholds/behavior per severity
  - Data retention windows (default 90 days) and backup purge behavior
  - Questionnaire seed questions/forms
  - Branding/theme colors and assets
- Expose these in Org Settings; bootstrap new orgs from seed files.

## Security Defaults
- Keep DEBUG off in production; limit allowed hosts; enforce OIDC/Keycloak auth for DRF.
