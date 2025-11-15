# Schema Rename Playbook (`spec/` → `schemas/`)

## Goal
Rename the canonical schema bundle from `spec/` to `schemas/` without breaking tooling or docs.

## Steps
1. **Inventory references**: `rg -n "spec/" -g"*.md"`, `rg -n "spec/" -g"*.py"` across repo to identify hard-coded paths.
2. **Move directory**: use `git mv spec schemas` (future implementation) ensuring CI paths updated.
3. **Update tooling configs**: adjust `doc_tools`, Spectral configs, and any scripts referencing `spec/` (e.g., `scripts/schema/*.py`).
4. **Docs updates**: modify `docs/overview/tdd/appendices/repository_trees.md`, `docs/automation/langgraph-agents.md`, README, quickstart references.
5. **CI/Lint**: run `make typing.ai`, `make all.test`, `make docs.check.links`, Spectral on new path.
6. **Audit**: confirm `storage/ops/` references use new path; ensure `.gitignore` includes `schemas/` artifacts.

## Risks & Mitigation
- Missed references: rely on ripgrep search + CI to catch.
- Tooling caches: clean `.typewiz_cache`, doc build caches before running tests.

## Evidence
- Track rename readiness in `reports/governance_storyboard.md`.
