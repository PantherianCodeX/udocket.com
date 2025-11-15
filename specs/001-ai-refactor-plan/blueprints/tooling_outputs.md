# Tooling Output Relocation Plan

## Targets
- Coverage reports → `out/test-reports/coverage.xml`
- Typewiz artifacts → `out/typewiz/`
- Requirements exports → `out/requirements/`

## Steps
1. Update `.coveragerc` + CI commands to write to `out/test-reports`.
2. Configure `typewiz.toml` output path; ensure `.gitignore` covers `out/typewiz/`.
3. Modify `scripts/dev/export_requirements.py` to write into `out/requirements/` (create dir if missing).
4. Update README + docs to mention new output paths.
5. Add CI check verifying root is free from stray coverage/typewiz files.

## Evidence
- Document command output logs in `reports/docs/ai_module_migration.log` once executed (Phase 8).
