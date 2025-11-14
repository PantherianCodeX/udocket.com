# LangGraph Stage Catalog – Modernization Deltas

This document records the changes we will apply to the canonical stage catalog once implementation promotes them into `automation/pipelines/` and `packages/common/agents/stage_map.py`. The source of truth today is `packages/common/agents/stage_map.py` (see commit `HEAD` during this planning pass). No production files are modified here; this is a blueprint for the follow-up PR.

## Scope
- Target the Analyze lane (`StageKey.AN_*`) that powers readiness discovery and reporting.
- Ensure Compose lane touchpoints are noted where readiness exports flow back into client deliverables.
- Provide cost ceilings, QA hooks, and enable/disable switches per FR-012.

## Delta Summary

| StageKey | Current Spec (from stage_map.py) | Planned Delta | Rationale |
|----------|----------------------------------|---------------|-----------|
| `AN_INPUT_DISCOVERY` | Enabled, `agent_task=None`, retry budget 1, no cost ceiling. | Keep enabled; add `cost_ceiling=$0.05`, `llm_profile_id="analyze.input"`, QA hook: log ingestion stats to ops JSONL. | Baseline parsing remains cheap but must emit deterministic ingest evidence.
| `AN_ATOMS_EXTRACT` | Enabled, `AgentTask.ATOMS`, depends on input discovery, retry 1. | Increase `retry_budget` to 2, set `cost_ceiling=$0.20`, attach QA policy requiring token histogram + owner ack. | Extraction failures are common on legacy manifests; second retry plus QA note keeps runs deterministic.
| `AN_CONTEXT_BUILD` | Enabled, `agent_task=None`, depends on atoms extract. | Add `agent_task=AgentTask.SYNTHESIZE` (new) to clarify workload, embed QA rule verifying residency tags are preserved. | Context builder now enriches readiness models with residency notes that must be validated.
| `AN_OUTLINE_DRAFT` | Enabled, `AgentTask.EXTRACT`, depends on context build. | Add OTLP span name `readiness.outline`, `cost_ceiling=$0.35`, QA gating on CapabilityGap auto-generation toggles. | Outline stage now seeds blockers/gaps; telemetry ensures we pick up automated gap creation issues early.
| `AN_TIMELINE_BUILD` | Enabled, `AgentTask.EXTRACT`, depends on atoms. | Keep cost ceiling `0.10`, require new dependency on `AN_CONTEXT_BUILD` so readiness metadata flows into scheduling. | Aligns timeline stage with modernization gating.
| `AN_ENTITIES_EXTRACT` | Enabled, `AgentTask.EXTRACT`, depends on atoms. | No structural change; add QA check verifying every entity ties back to `MigrationStageReadiness.stage_key`. | Entities now populate readiness matrix owners.
| `AN_ISSUES_EXTRACT` | Disabled today. | Re-enable with `agent_task=AgentTask.EXTRACT`, `cost_ceiling=$0.15`, `retry_budget=1`, gating on readiness dataset hash parity. | We need automated blocker capture; leaving disabled undermines FR-003.
| `AN_GAPS_EXTRACT` | Disabled today. | Re-enable, tie dependency to `AN_OUTLINE_DRAFT`, feed outputs into `CapabilityGap` store, add QA rule comparing `gap_id` uuids to readiness dataset diff. | Supports deterministic gap generation.
| `AN_FLAGS_EXTRACT` | Disabled today. | Re-enable strictly for governance flags, `agent_task=AgentTask.EXTRACT`, keep sampling guard to avoid noise, record results in `reports/risk_log.jsonl`. | Governance wants early warnings tied to readiness.
| `AN_SUMMARY_DRAFT` | Enabled, `AgentTask.GENERATE`, depends on outline + timeline + entities. | Attach `cost_ceiling=$0.60`, `retry_budget=1`, require QA join after readiness dataset reload completes. | Prevents runaway spend and ensures summary waits for refreshed readiness data.
| `AN_STAFF_REPORT` | Disabled. | Keep disabled during planning; convert to optional stage triggered manually when exec briefing requested. Document manual activation flow. | Not needed for baseline readiness sprint, but blueprint describes optional use.
| `AN_LANE_QA` | Enabled, `AgentTask.EVAL`, depends on summary. | Expand QA stage to include readiness schema validation + Spectral lint. Update doc to mention `doc_tools` dependency. | Aligns with FR-005 (telemetry + docs gating).
| `AN_QA_JOIN` | Enabled, depends on lane QA. | No functional change; ensure it serializes ops JSONL hash into audit log before Compose lane picks it up. | Maintains deterministic audit trail.
| `AN_FINALIZE_WRITE` | Enabled, depends on QA join. | Add dependency on `AN_FLAGS_EXTRACT` so risk flags cannot be skipped, enforce `cost_ceiling=$0` (no LLM cost expected). | Finalization becomes pure IO/logging stage.
| `CO_RELEASE_WRITE` | Enabled, Compose lane final gate. | Document new dependency on readiness artifacts; no stage_map change besides `depends_on += [StageKey.AN_FINALIZE_WRITE]`. | Compose release must wait for readiness approvals before publishing client deliverables.

## Additional Notes
- Cost ceilings mirror the performance guardrails in `plan.md` (readiness recompute <10 minutes, LangSmith eval <30 minutes, LangFuse overhead <5%). We will translate time budgets into USD based on current provider rates when updating `stage_map.py`.
- QA hooks map to new evidence files stored under `specs/001-ai-refactor-plan/reports/`; they will later port into `automation/pipelines/` manifests alongside test entry points.
- The modernized catalog continues to treat `StageKey` as the canonical enum exported from `packages/common/agents/stage_map.py`. Any new stage keys introduced during US2 backlog generation must be added to that enum before referencing them elsewhere.

## Promotion Checklist
1. Extend `_spec` helper (or instantiate `StageSpec` directly) to populate `cost_ceiling`, `llm_profile_id`, and future `qa_hook_id` fields.
2. Re-run `make typing.ai` after updating `stage_map.py` to ensure StrEnum additions propagate to dependents.
3. Copy this table into `automation/pipelines/analyze_modernization.yaml` (to be added) so pipeline manifests stay in sync with the production stage map.
4. Update `docs/automation/langgraph-agents.md` §8.3 summarizing the enablement of the newly reactivated stages and their QA/cost attributes.
