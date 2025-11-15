# Vendor Budget Monitoring Plan

## Targets
- LangSmith + LangFuse combined spend ≤10% above forecast (per research.md Decision 5).
- Alerts at 80% and 100% thresholds; mitigation plan required when variance >10%.

## Data Sources
- `packages/common/telemetry/vendor_usage.py` (VendorUsageBudget dataclass).
- Readiness artifacts linking vendor usage snapshots to ops JSONL entries.

## Monitoring Steps
1. Weekly: run `python -m packages.common.telemetry.vendor_usage report --vendor langsmith --month <YYYY-MM-01>` (to be implemented) and append snapshot to `reports/vendor_budget_plan.md`.
2. Compare actual vs allocated; if >=80% trigger Slack alert; if ≥100% escalate to governance.
3. Record mitigation plan referencing readiness risk log ID.

## Alert Hooks
| Vendor | Threshold | Channel | Owner |
|--------|-----------|---------|-------|
| LangSmith | 80% | #ai-modernization | AI Modernization Lead |
| LangSmith | 100% | #ai-modernization + Finance ticket | AI Modernization Lead |
| LangFuse | 80% | #ai-observability | AI Observability Lead |
| LangFuse | 100% | #ai-observability + Security | AI Observability Lead |

## Current Snapshot (2025-11-15)
| Vendor | Month | Allocated | Actual | Variance | Mitigation |
|--------|-------|-----------|--------|----------|------------|
| LangSmith | 2025-11-01 | $6,000 | $4,200 | -30% | Continue monitoring |
| LangFuse | 2025-11-01 | $2,000 | $600 | -70% | Spend within experimental cap |
