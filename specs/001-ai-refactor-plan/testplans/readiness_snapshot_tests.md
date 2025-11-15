# Readiness Snapshot Unit & Property Tests

Focus: coverage for readiness snapshot pipeline (raw ingest → normalized datasets → ops/audit outputs). Complements the fixture/property notes in `drafts/test_plan.md` but scoped to the production code that will land in `packages/devops/readiness/`.

## Components Under Test
1. `packages/devops/readiness/service.py` – orchestrates ingest, scoring, and output emission.
2. `packages/devops/readiness/cli.py` – user entry point; thin wrapper but must validate inputs.
3. `specs/001-ai-refactor-plan/scripts/refresh_readiness.py` – planning-phase script acting as spike harness.

## Unit Tests
| ID | Target | Scenario | Assertions |
|----|--------|----------|------------|
| RS-001 | `normalize_inventory()` | Happy path converting raw CSV to `MigrationStageReadiness`. | Returns list sorted by `stage_key`; dataclasses populated; evidence links deduped. |
| RS-002 | `normalize_inventory()` | Missing owner/evidence. | Raises `ReadinessInvariantError`; also emits synthetic `CapabilityGap` via helper. |
| RS-003 | `score_stage()` | Clamp logic. | Inputs outside 0–5 raise ValueError; valid ints remain unchanged. |
| RS-004 | `emit_ops_jsonl()` | Append-only behavior. | Writes newline-delimited JSON; no truncation of existing lines; includes `artifact_hash` referencing dataset digest. |
| RS-005 | CLI `refresh` command | Unknown lane. | Command exits non-zero with friendly error and list of valid lanes. |

## Property Tests
Leveraging Hypothesis strategies sourced from the typed primitives (see `drafts/readiness_types.py`).

1. **Idempotent serialization** – Running ingest twice with identical input yields identical JSON + SHA256; property compares digests.
2. **Capability gap linkage** – For every gap referencing `stage_key`, property asserts corresponding readiness record exists; Hypothesis mutates inputs to ensure detection.
3. **Cutoff guard** – Property ensures all emitted `cutoff_date` values are ≥ frozen `today`; shrink-to-failure example should surface offending record.
4. **Ops/audit hash chaining** – Property constructs JSONL streams and confirms `artifact_hash` equals dataset hash and seal hash covers both ops + audit payloads.
5. **LangFuse sampling envelope** – Observability controls produced during ingest always adhere to sampling ≤0.25 and retention ≤30 days.

## Tooling & Execution
- Location: `tests/devops/readiness/test_snapshots.py` (unit) and `tests/devops/readiness/test_snapshots_property.py` (property).
- Use `pytest` + `hypothesis` with `pytest.mark.usefixtures("freeze_time")` to control date comparisons.
- Run via `make all.test` and `make typing.ai`; property suite joins `pytest -m property` target for CI control.

## Exit Criteria
- ≥90% line coverage across readiness service + CLI.
- No TODOs or `typing.Any` introduced while implementing tests.
- All invariants from `data-model.md` enforced either via unit or property coverage.
