# DevOps Readiness Module Blueprint

## Goals
- Provide a feature-scoped toolkit (`packages/devops/readiness`) that ingests the datasets in `specs/001-ai-refactor-plan/data/readiness/`, emits ops/audit artifacts, and exposes a CLI entry point for future automation.
- Keep all runtime interactions behind typed helpers so LangGraph agents can orchestrate readiness refreshes deterministically.

## Components
1. **`ReadinessServiceConfig`** – frozen dataclass describing feature directory, lane, and reports location. All consumers instantiate this config to avoid ad-hoc path handling.
2. **`ReadinessService`** – orchestrates dataset validation, hashing, and ops JSONL emission. Methods:
   - `refresh(dry_run: bool = False)` → `ReadinessServiceResult` (counts + dataset hash + ops path).
   - Private helpers for JSON loading, schema validation (status enum, cutoff date string), and SHA256 hashing across inventory/gaps to align with ops/audit sealing rules.
3. **`ReadinessServiceResult`** – dataclass returned to callers/CLI with summary metadata for downstream reporting.
4. **`packages/devops/readiness/cli.py`** – argparse-based CLI with `refresh` command, defaulting to the feature directory, enabling `--dry-run`, and printing machine-readable summaries for future scripts/CI jobs.
5. **Future entry points** – `pyproject.toml` console script: `devops-readiness=packages.devops.readiness.cli:main` (to be added when implementation merges into production tooling).

## Data Flow
1. CLI or scripts instantiate `ReadinessService` with `feature_dir` pointing to the active story (e.g., `specs/001-ai-refactor-plan`).
2. Service loads `data/readiness/inventory.json` + `gaps.json`, validates schema constraints (enum membership, required fields, cutoff date shape).
3. Service computes SHA256 digest across both files; this hash becomes the `artifact_hash` for ops/audit links.
4. Unless `--dry-run`, service appends a JSON line to `reports/readiness_ops.jsonl` capturing timestamp, lane, counts, evidence paths. Audit chain + seal creation will be layered atop this output when the ops harness is implemented.
5. CLI prints summary stats for human monitoring while returning exit codes suitable for CI.

## Integration Points
- **Ops/Audit**: `readiness_ops.jsonl` remains the canonical source during planning; implementation will add `reports/audit/readiness_audit.jsonl` entries and seal generation inside the same service.
- **LangGraph Agents**: Future automation tasks will import `ReadinessService` directly from `packages.devops.readiness` instead of shelling out to scripts, allowing typed orchestration workflows.
- **Docs**: `docs/automation/langgraph-agents.md` §8.3 will reference this module when describing readiness refresh procedures.

## Testing & Tooling
- Unit tests live under `tests/devops/readiness/test_service.py`; property tests reuse fixtures defined in `drafts/test_plan.md`.
- CLI tests exercise argument parsing and error handling (missing datasets, bad lane) to enforce friendly diagnostics.
- `make typing.ai` ensures the new package conforms to zero-Any policy.

## Rollout Plan
1. Keep toolkit scoped to feature directory until readiness artifacts move into production storage.
2. Once implementation sprints begin, wire CLI into `Makefile` + CI so `make readiness.refresh` runs the tool and publishes ops/audit evidence.
3. Expand service to generate LangSmith/LangFuse evidence pointers (VendorUsageBudget links) before activation.
