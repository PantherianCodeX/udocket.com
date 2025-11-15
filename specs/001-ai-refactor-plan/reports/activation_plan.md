# Activation Playbook

## Dry-Run Steps
1. Run readiness refresh CLI (`packages.devops.readiness.cli refresh`) and verify ops hash.
2. Execute LangSmith eval + export validation.
3. Enable LangFuse R&D session, capture evidence, then disable within SLA.

## Sampling Strategy
- Start at 10% dev traffic, monitor metrics, ramp incrementally to staging.
- Compose release remains blocked until governance checklist complete.

## Rollback Triggers
- Ops hash mismatch.
- LangSmith ingestion errors.
- LangFuse disable SLA breach.

## Decision Checkpoints
| Phase | Owner | Evidence |
|-------|-------|----------|
| Dry-run complete | AI Modernization Lead | `reports/activation_dry_run.jsonl` |
| Staging dial-up | Governance | `reports/activation_checklist.md` |
| Production ready | Platform Ops | `reports/activation_signoff.md` |
