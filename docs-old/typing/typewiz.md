Typewiz integration
===================

Overview
--------
- We use `typewiz` to aggregate diagnostics from Pyright and mypy and produce actionable dashboards for strict typing rollout.
- It runs locally via Makefile targets and in CI (non‑blocking job) and Nightly (additional job) until we are ready to gate.

Local usage
-----------
- Audit + manifest: `make typing-audit` (`typewiz audit --readiness --readiness-status blocked --readiness-status ready` is wired in)
- Dashboards (md + html): `make typing-dashboard`
- Readiness (targeted buckets): `make typing-readiness`
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
- Inline readiness output keeps CI summaries actionable (blocked/close/ready buckets show `<none>` when empty).
- Use `typewiz readiness --status blocked --status ready` to re-evaluate without re-running the audit.
- Switch to `--readiness-level file` for per-module diagnostics when promoting folders to strict mode.

Notes
-----
- Aligns with AGENTS typing guidance; do not introduce `Any` in strict zones.
- Keep Pyright and mypy configs as the source of truth; typewiz reads them.
- Project pins `typewiz` at `v0.1.1`; run `uv lock --project apps/platform` after updating to later tags.
- Environment overrides: `TYPEWIZ_STATUSES`, `TYPEWIZ_LEVEL`, and `TYPEWIZ_LIMIT` customise the Make targets (see `Makefile`).
