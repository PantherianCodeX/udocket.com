# Root Cleanup Blueprint

## Objective
Restore repo root to canonical directories (apps/, automation/, packages/, services/, config/, infra/, ops/, tests/, tooling/, docs/, schemas/, specs/, out/, storage/, scripts/).

## Checklist
1. Remove stray files: `reading`, `udocket-starship.sh`, legacy `requirements/`, coverage/typewiz artifacts at root.
2. Relocate `db/` helpers → `tooling/fixtures/sqlalchemy/` with import updates.
3. Ensure outputs go to `out/` (`out/test-reports/coverage.xml`, `out/typewiz/`, `out/requirements/`).
4. Delete unused directories (old `spec/` duplicates once rename completes).
5. Update `.gitignore` entries for removed paths.
6. Capture before/after screenshots stored under `reports/root_cleanup_evidence/` (use `tree -L 1`).

## Evidence
- Run `tree -L 1 > reports/root_cleanup_evidence/before.txt` pre-cleanup and similar for after.
- Document in `reports/governance_storyboard.md` referencing FR root cleanup.
