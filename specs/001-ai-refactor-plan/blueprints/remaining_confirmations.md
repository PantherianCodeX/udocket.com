# Remaining Confirmations Blueprint

## Items
1. `deps/typewiz/` vendor exception → annotate README and governance doc until upstream release.
2. Dev/stub directory policy → ensure `tooling/` + `typings/` only, update AGENTS.md/TDD.
3. Docker reference audit → search for `spec/` path usage post-rename and confirm no stale references in Dockerfiles.

## Plan
- Create checklist referencing FR IDs (010–016) in `reports/governance_storyboard.md`.
- For each item, capture command outputs (`rg`, `docker grep`) and store logs under `reports/confirmations/`.
