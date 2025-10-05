# Typing Idempotency Playbook

_Last updated: 2025-10-05_

This playbook captures the conventions that keep repeated typing passes safe to re-run. When a script or helper is rerun, it should land the same changes (or no changes at all) so we avoid churn in review cycles.

## Recent Commit Themes (last few typing-focused PRs)
- Analyze agent overrides are now normalised via frozen dataclasses, giving us deterministic inputs for stage configuration.
- Shared agent helpers coerce JSON payloads into typed containers, letting us centralise fixes instead of scattering casts.
- Django models expose `typed_objects()` and `scoped()` helpers, so moving code to typed querysets no longer requires bespoke casts per model.
- The typing roadmap documents strict-mode expectations for agents and managers, providing the policy cover needed to enforce the helpers above.

## Diagnostic Snapshot
- Running `pyright --stats` without Django/pytest stubs still triggers a flood of missing-import errors. Once the bootstrap script installs those stubs, the count falls back toward the ~700 error / 3,500 warning baseline recorded in earlier strict-mode pushes.
- Remaining errors typically fall into a handful of buckets (untyped fixtures, managers, and presenter dictionaries), making them ideal candidates for targeted automation.

## Idempotent Acceleration Strategy
1. **Bootstrap the environment** – add a reusable `scripts/typing/bootstrap_env.py` that installs Django/DRF/pytest stubs into `.venv`. The script should exit cleanly if stubs are already present.
2. **Automate manager migrations** – codemods can detect `Model.objects` usage and suggest the `typed_objects()`/`scoped()` helpers. Because the helpers follow a shared pattern, rerunning the fixer is safe.
3. **Stage map linting** – reuse the analyze agent’s `_normalize_stage_map` to validate organisation overrides and rewrite alias-heavy maps into canonical keys.
4. **Transcript helper adoption** – replace ad-hoc transcript parsing with `parse_transcript` and `TranscriptSegment` so future parsing fixes happen in one place.
5. **Error bucket tagging** – capture `pyright --stats` output each time we touch typing debt and append the snapshot (with the command and date) to `docs/typing_debt_assessment.md`.

## Helper & Tooling Backlog
- **Typed fixture module** – publish a `tests/_typing.py` module that exposes annotated versions of `monkeypatch`, `settings`, `db`, and `client` so suites can import them once.
- **Strict-mode guardrail** – add a script that inserts `# pyright: strict` pragmas and verifies module lists without duplicating headers.
- **Telemetry schema stubs** – maintain stub overlays for high-churn telemetry payloads so Pyright sees concrete types even before runtime code is refactored.
- **Manager coverage report** – produce a report listing models that still rely on untyped managers to prioritise the next migrations.

## Next Steps
- Land the bootstrap script and strict pragma fixer, update CI docs to point at them, and record the resulting pyright counts.
- Schedule a follow-up audit once the error count drops below 500 to identify the hardest remaining buckets (operations tasks, presenters, and UI tests).
