# Readiness Fixtures & Property Tests

Phase 2 requires deterministic fixtures so downstream tooling (CLI + ingest service) can exercise schema contracts before we touch production code. This note documents the fixtures we generated and the property tests they will power.

## Fixture Inventory

| File | Description | Deterministic Rule |
|------|-------------|--------------------|
| `data/readiness/examples/inventory.modernization.json` | Minimal readiness dataset with both a "complete" stage and a "blocked" stage pointing at a gap. | Sorted lexicographically by `stage_key`; timestamps encoded in UTC ISO-8601; capability gap IDs reference the gap fixture below. |
| `data/readiness/examples/gaps.modernization.json` | Gap catalog for the modernization lane. | UUIDv7 strings, mitigation text >=25 chars, due dates in the future. |

## Property-Test Matrix

1. **Inventory round-trip determinism**  
   - Load fixture → serialize via `MigrationStageReadiness` dataclasses → write JSON.  
   - Property: SHA256 of the serialized body matches `inventory.modernization.json.sha256`.  
   - Guards against non-deterministic ordering or datetime formatting regressions.
2. **Gap linkage completeness**  
   - For every readiness record referencing a gap UUID, assert `gap_id` exists in the gap fixture.  
   - Property: orphaned references cause Hypothesis to shrink to the minimal failing stage entry, ensuring quick debugging.
3. **Score bounds**  
   - Hypothesis generates scores in `[-2, 10]`, but property asserts stored values remain within `[0, 5]`.  
   - Ensures validators clamp/raise before emitting exports.
4. **Cutoff invariants**  
   - Property: `cutoff_date` must be `>= date.today()`; fixtures already satisfy this, so the test simply replays the sample through the validator to guarantee future updates cannot regress.  
   - Hypothesis vary `today` using frozen time contexts.
5. **Capability gap auto-generation trigger**  
   - Simulate readiness rows missing `owner_team`/`evidence_links`; property asserts the ingest logic emits a new gap entry with `category="risk"` and `severity >= medium`.  
   - Use fixtures as the stable baseline and mutate via Hypothesis strategies.
6. **Ops JSONL hash propagation**  
   - Once `scripts/refresh_readiness.py` writes ops JSONL, property asserts `artifact_hash` equals the digest of `inventory.modernization.json`.  
   - Fixture-based test prevents accidental hashing of unsorted data.
7. **LangFuse sampling bounds**  
   - Generate `ObservabilitySession` records with Hypothesis; property ensures `sampling_rate <= 0.25` and `retention_days <= 30`.  
   - Fixtures define canonical good values so the strategy shrinks toward them.

## Test Harness Notes
- Implement tests inside `tests/devops/readiness/test_fixtures.py` once coding begins.
- Use `hypothesis-jsonschema` against the typed primitives to keep generators aligned with the enums in `drafts/readiness_types.py`.
- Store fixture hashes under `data/readiness/examples/*.sha256` so CI can detect accidental edits; Hypothesis tests reference those files for comparison.
