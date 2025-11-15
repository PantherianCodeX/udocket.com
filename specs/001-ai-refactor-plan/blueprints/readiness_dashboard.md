# Readiness Dashboard UX Blueprint

## Audience
- Program managers tracking modernization stages.
- Governance reviewers verifying evidence + residency compliance.

## Layout
1. **Hero KPIs** (top row)
   - Stage completion matrix (count per status) using data from `tools/readiness_aggregator.ipynb` export.
   - Average scores (architecture/compliance/observability) with sparkline for trend when more snapshots exist.
2. **Stage Grid** (middle section)
   - Table keyed by `stage_key` showing status pill, owner team, last validated date, cutoff date, and evidence link icons.
   - Clicking a row expands capability gaps (severity chips, mitigation plan summaries, due dates).
3. **Gap Heatmap** (right rail)
   - Severity vs category heatmap to highlight blockers; filters support `owner_team` and `category` facets.
4. **Audit Pane** (bottom)
   - Shows latest ops JSONL record (timestamp, hash, evidence paths), with button to download `readiness_ops.jsonl` / `readiness_dashboard_snapshot.json`.

## Accessibility & UX Notes
- WCAG AA colors for status pills (`complete` green #0F8A5F, `blocked` red #C0392B, etc.).
- Keyboard navigation enabled for table/expand rows; include skip-links to hero KPIs.
- Evidence links open in new tab with descriptive tooltips.

## Data Sources
- Snapshot JSON produced by the notebook (`reports/readiness_dashboard_snapshot.json`).
- Gap data from `data/readiness/gaps.json` (fed via service to maintain parity with APIs).
- Ops hash displayed from `readiness_ops.jsonl` latest entry.

## Implementation Notes
- Frontend stack: existing React readiness dashboard (TypeScript) under `apps/readiness-dashboard` (to be created later).
- Use Recharts or similar for heatmap; keep deps minimal.
- Provide download buttons that simply read files via backend endpoint proxied from feature directory during planning.

## Next Steps
- Wire aggregator export into CI artifact for preview builds.
- Pair with documentation updates in `docs/automation/langgraph-agents.md` once dashboard screenshots exist.
