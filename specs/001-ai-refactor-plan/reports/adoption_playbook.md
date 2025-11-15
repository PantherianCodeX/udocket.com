# LangSmith Adoption Readiness Playbook

## Phases
1. **Pilot** – Dev workspace only, tooling evidence captured in feature dir.
2. **Staging** – After governance sign-off, enable staging workspace, run eval/export checks.
3. **Handoff** – Transition ownership to Platform Ops with runbooks + evidence references.

## Steps per Phase
- Provision workspace via script; append to workspace log.
- Run eval + export validation; archive results.
- Update vendor budget plan with incremental spend.
- Execute activation checklist before promoting.

## Owners
- AI Modernization → Pilot + Staging.
- Platform Ops → Production adoption.

## Evidence
- `reports/langsmith_workspace_records.jsonl`
- `reports/langsmith_eval_export.json`
- `reports/vendor_budget_plan.md`
