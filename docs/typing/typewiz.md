Typewiz integration
===================

Overview
--------
- We use `typewiz` to aggregate diagnostics from Pyright and mypy and produce actionable dashboards for strict typing rollout.
- It runs locally via Makefile targets and in CI (non‑blocking job) and Nightly (additional job) until we are ready to gate.

Local usage
-----------
- Audit + manifest: `make typing-audit` (prints the readiness summary by default via `typewiz audit --readiness --readiness-status blocked --readiness-status ready`)
- Dashboards (md + html): `make typing-dashboard`
- Readiness (targeted buckets): `make typing-readiness` (shows both `blocked` and `ready` folders; rerun with `TYPEWIZ_STATUS=close` to focus on near-ready directories)
- One-off console run:

  ```bash
  uv run --project apps/platform --extra dev typewiz audit \
    --mode current \
    --fail-on warnings \
    --manifest reports/typing/typing_audit.json \
    --readiness \
    --readiness-status blocked \
    --readiness-status ready \
    apps/platform packages/udocket_common tests
  ```

CI/Nightly
----------
- CI job `Typewiz Audit` runs on every push/PR, uploads `reports/typing/*` artifacts, and does not block builds.
- Nightly job `Typewiz Nightly Audit` posts a summary to the workflow summary and uploads artifacts.

Ratcheting plan
---------------
- Keep repo-wide baseline (`pyright` baseline) via `typewiz.toml`.
- Enforce strict zones via per-folder overrides `typewiz.dir.toml` starting with `packages/udocket_core/logging`.
- Expand strict zones incrementally as folders reach zero diagnostics. Current strict zones:
  - `packages/udocket_core/logging/` (strict)
  - `apps/platform/admin/` (strict)
  - `apps/platform/authorization/` (strict)
  - `apps/platform/jobs/` (strict)
  - Candidates (validate, then promote): `tests/`, `packages/udocket_core/agents/`, `apps/platform/operations/`
- When stable, remove legacy ad-hoc typing steps and make the typewiz CI job blocking.

Configuration
-------------
- Root config: `typewiz.toml` sets runners, paths, and profiles.
- Folder override example (strict): `packages/udocket_core/logging/typewiz.dir.toml`.

Readiness workflow (v0.1.1)
---------------------------
- `typewiz audit --readiness` prints an immediate readiness summary for the requested buckets at the end of every run. Use `--readiness-level file` to dig into individual modules.
- `typewiz readiness --status blocked --status ready` reuses the manifest when you want to re-check without scanning the codebase again.
- Empty buckets are now reported explicitly (`<none>`), so the CI summary remains useful even when an area is fully green.

Notes
-----
- Aligns with AGENTS typing guidance; do not introduce `Any` in strict zones.
- Keep Pyright and mypy configs as the source of truth; typewiz reads them.
- Repo pins `typewiz` to `v0.1.1` (see `apps/platform/pyproject.toml`); run `uv lock --project apps/platform` after pulling future upgrades.
- Environment overrides:
  - `TYPEWIZ_STATUSES="blocked close ready"` to print multiple buckets at once when using `make typing-readiness`.
  - `TYPEWIZ_LEVEL=file` for per-file listings.
  - `TYPEWIZ_LIMIT=5` to tighten the output focus.
