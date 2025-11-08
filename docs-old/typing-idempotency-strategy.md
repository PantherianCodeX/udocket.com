# Typing Idempotency Strategy — October 2025

This memo summarises what the most recent typing-focused changes delivered and how we can turn those wins into reusable tooling. The objective is to chip away at the remaining Pyright backlog without reintroducing churn.

## Digest of the Last Typing Commits

| Area | Highlight | Follow-on Opportunity |
| --- | --- | --- |
| Core Django models & settings | Nullable fields and settings accessors are now annotated without resorting to `Any`. | Extract the nullable-field pattern into a mixin so future model updates stay consistent. |
| Jobs/Cases/Artifacts models | Introduced `typed_objects()` / `scoped()` accessors for strongly typed querysets. | Provide a mixin or codemod that rolls the helpers out to remaining models. |
| Agent IO modules | JSON coercion helpers and Azure client guards now run under strict mode. | Share the JSON validators with other telemetry pipelines before adding new providers. |
| Analyze agent | Stage overrides are normalised by frozen dataclasses, producing deterministic runtime inputs. | Build scripts that validate organisation overrides and regenerate defaults with the same helpers. |
| Documentation | Roadmap sections emphasise strict-mode promotion instead of new ignores. | Sync roadmap sections with generated manifests so narrative guidance cannot drift. |

## Current Error Snapshot

Local `pyright` runs without the typed virtualenv still report thousands of missing-import errors. Once the bootstrapper installs Django/DRF/pytest stubs the rate drops to the high hundreds, concentrated in fixtures and presenter tests. Automation should degrade gracefully when the virtualenv is missing by emitting a clear instruction rather than failing mid-run.

## Idempotent Helpers to Build

1. **Strict pragma manager (`scripts/typing/strictify.py`)**
   - Inputs: list of modules or glob patterns plus `--dry-run`.
   - Behaviour: insert `# pyright: strict` when missing, keep docstring/comment ordering intact, and make repeated runs a no-op.
   - Output: optional manifest so CI can track strict coverage over time.

2. **Typed manager mixin**
   - Publish a helper in `apps/platform/utils/typing.py` that encapsulates the `typed_objects()` / `scoped()` pattern and asserts the default manager is untouched.
   - Running the helper twice should not double-register managers.

3. **Stub synchroniser (`scripts/typing/check_stubs.py`)**
   - Validate that required stub overlays exist, regenerate placeholders when needed, and warn when pyright config drifts from repository defaults.

4. **Pytest fixture annotator**
   - Use LibCST to add fixture annotations for commonly used pytest fixtures, skipping files that are already typed.
   - Because it relies on syntax-aware rewrites, rerunning the script should preserve formatting and avoid duplicate imports.

5. **Document synchroniser**
   - Track strict-mode adoption, helper coverage, and error counts in a machine-readable manifest (JSON or YAML).
   - Regenerate human-readable sections in `typing-roadmap.md`, `typing_debt_assessment.md`, and `typing-idempotency-playbook.md` from that manifest to keep guidance current.

The full automation specifications live in `docs/typing/automation_helper_specs.md`. Reference that file for CLI flags, exit codes, and idempotency guarantees when implementing or updating any helper.

## Reporting Plan

- Keep the rolling status log in `docs/typing/typing_progress_log.md` up to date after each helper run or wave milestone so subsequent work picks up without rediscovery.
- After each typing PR, append the latest `pyright --stats` summary (with command, date, and environment notes) to `docs/typing_debt_assessment.md`.
- Link roadmap updates directly to the helpers or manifests that drove the change so reviewers can verify evidence quickly.
- Review the manifest quarterly to decide whether new automation is needed or if manual clean-up is acceptable for the remaining modules.
- Regenerate `docs/typing/automation_status.md` via `scripts/typing/sync_docs.py` so the helper and strict manifest tables stay current.
- Keep `# pyright: strict` only in modules that are listed in the strict manifest. Remove the pragma from other files to avoid IDE noise; use the manifest + CI gates to enforce strictness.

### Implementation Checklist
- [x] Ship `scripts/typing/bootstrap_env.py` and expose it via `just typing-bootstrap`.
- [x] Seed `docs/typing/automation_manifest.json` from the template and wire `scripts/typing/sync_docs.py` into CI.
- [x] Add `tests/_typing.py` and run the fixture annotator across the loudest suites.
- [x] Vendor upstream stub packages via `scripts/typing/vendor_stubs.py` so pyright does not depend on the virtualenv at analysis time.
- [x] Enhance `scripts/typing/check_strict.py` with focused pyright/mypy runs and manifest-driven module selection to accelerate cleanup.
- [ ] Promote clean modules to strict, capturing entries in `docs/typing/strict_manifest.json`.
- [ ] Run the manager codemod on operations/jobs/apps so querysets inherit typed managers before enabling stricter analysis.

## Upcoming Focus Areas

1. Ship the strict pragma manager and run it across `packages/core/agents/**` before touching new modules.
2. Backfill typed pytest fixtures starting with the logging and presenter suites, which still account for a large share of `reportMissingParameterType` diagnostics.
3. Integrate stub validation into CI to prevent regressions when dependency versions change.
4. Schedule recurring pyright snapshots (with and without the virtualenv) so we can distinguish configuration issues from missing type information.

Executing the helper roadmap above turns repetitive cleanups into scripted fixes, reducing reviewer load and making strict-mode adoption sustainable.
