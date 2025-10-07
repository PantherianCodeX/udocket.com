Typewiz integration
===================

Overview
--------
- We use `typewiz` to aggregate diagnostics from Pyright and mypy and produce actionable dashboards for strict typing rollout.
- It runs locally via Makefile targets and in CI (non‑blocking job) and Nightly (additional job) until we are ready to gate.

Local usage
-----------
- Audit + manifest: `make typing-audit`
- Dashboards (md + html): `make typing-dashboard`
- Readiness (top blocked/ready folders): `make typing-readiness`

CI/Nightly
----------
- CI job `Typewiz Audit` runs on every push/PR, uploads `reports/typing/*` artifacts, and does not block builds.
- Nightly job `Typewiz Nightly Audit` posts a summary to the workflow summary and uploads artifacts.

Ratcheting plan
---------------
- Keep repo-wide baseline (`pyright` baseline) via `typewiz.toml`.
- Enforce strict zones via per-folder overrides `typewiz.dir.toml` starting with `packages/udocket_core/logging`.
- Expand strict zones incrementally (e.g., `packages/udocket_core/agents`, `apps/platform/admin`) once clean.
- When stable, remove legacy ad-hoc typing steps and make the typewiz CI job blocking.

Configuration
-------------
- Root config: `typewiz.toml` sets runners, paths, and profiles.
- Folder override example (strict): `packages/udocket_core/logging/typewiz.dir.toml`.

Notes
-----
- Aligns with AGENTS typing guidance; do not introduce `Any` in strict zones.
- Keep Pyright and mypy configs as the source of truth; typewiz reads them.

