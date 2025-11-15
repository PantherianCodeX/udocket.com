# Codex Workflow Documentation Plan

## Scope
Identify all docs referencing Codex workflow and ensure they reflect the pinning steps + VS Code behavior.

## Targets
- `docs/overview/tdd/appendices/repository_trees.md`
- `AGENTS.md`
- `quickstart.md`
- Potential README sections for developer setup.

## Updates
1. Reference `scripts/codexhome.sh` as the canonical method for setting `CODEX_HOME`.
2. Explain `.codex/.codexhome` role and `.vscode` auto sourcing.
3. Include operational checklist (Section 7 of quickstart) once implementation occurs.
4. Add troubleshooting tips (re-run script when moving repo, use `--print-export`).

## Evidence
- When docs updated, run `make docs.check.links` and record logs in `reports/doc_workflow_checks.md` per Phase 8.
