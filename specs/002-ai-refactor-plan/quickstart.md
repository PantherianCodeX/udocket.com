# Quickstart — AI Refactor Implementation Delivery

## 1. Prerequisites
- Python 3.12 + uv installed (per repo root `.python-version`).
- Repo-root `.venv` created via `make bootstrap` (enforces shared environment).
- LangSmith + LangFuse credentials available (LangFuse remains R&D-only) and scoped tokens stored in `.env`.
- `SPECIFY_FEATURE=002-ai-refactor-plan` exported (script sets automatically when branch was created).

## 2. Environment Setup
```bash
# Ensure Codex home + root venv are configured
eval "$(./scripts/codexhome.sh --print-export .)"
make bootstrap
# Sync automation project metadata without creating a new venv
uv pip install -r automation/requirements.txt --python .venv/bin/python
```

## 3. Implementation Manifest Workflow
1. Re-run readiness discovery to refresh artifacts: `python -m packages.devops.readiness.cli refresh --feature 001-ai-refactor-plan --lane modernization`.
2. Generate the implementation manifest draft: `python -m packages.devops.readiness.cli manifest --feature 002-ai-refactor-plan --out specs/002-ai-refactor-plan/reports/manifest.jsonl`.
3. Review gaps flagged for missing blueprint mappings before coding.

## 4. LangGraph & Pipeline Work
1. Restore/extend `automation/pipelines/` StageMap entries per blueprint; keep stage/order/cost ceilings aligned with `docs/automation/langgraph-agents.md`.
2. Implement typed dataclasses/StrEnum wrappers for manifests, lanes, residency ledger entries.
3. Route all AI calls through `packages.ai.api`; add new `AIClient` profiles as needed inside `packages/ai` only.
4. Update schemas under `schemas/automation/ai-refactor/` and run `make schema.lint` (Spectral + doc tools) to validate exports.

## 5. Telemetry & Residency Dry Run
```bash
# Run end-to-end readiness dry run and capture evidence
uv run --project automation make readiness.dry-run 
```
- Confirm OTLP spans, LangSmith evals, LangFuse R&D traces, ops JSONL, and residency ledger entries land in `storage/ops|audit/ai-refactor/`.
- Execute the LangFuse disconnect playbook and re-run the dry run to ensure ingestion stops and evidence is logged.
- **Doc check reminder:** Before modifying LangSmith, LangFuse, or LangGraph wiring, consult the official documentation (LangGraph spec plus LangSmith/LangFuse references available through the Archon knowledge base) to ensure you’re building against the latest implementation guidance rather than stale training data, and capture the version you referenced along with the telemetry evidence.

## 6. Testing & Quality Gates
- `make typing.ai`
- `make all.test`
- `uv run --project automation python -m packages.devops.readiness.cli verify --feature 002-ai-refactor-plan`
- `make docs.check.links` if any docs/spec updates occur.
- Capture LangSmith prompt eval results + Typewiz diffs in `specs/002-ai-refactor-plan/reports/`.

## 7. Scope Guardrails
- Limit changes to repo cleanup, LangGraph pipelines, readiness toolkit, schemas, storage, and documentation specified in spec 001/002.
- Do **not** introduce new modules/services (only `packages/devops/readiness/` remains reusable reporting surface).
- Any newly discovered scope must become a future feature request.
