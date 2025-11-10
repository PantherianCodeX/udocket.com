# Technical Design Overview

This high-level TDD links to services, automation specs, and appendices. Highlights below capture the binding decisions for LangGraph agents; defer to the full spec in `docs/automation/langgraph-agents.md` for exhaustive contracts.

## LangGraph capability model

- Pipelines use capability-first `AgentTask` values (GENERATE, EXTRACT, EVAL, EMBED, ATOMS) instead of artifact-specific tasks. Stage-specific routing lives in a typed `StageKey`/`StageMap` catalog so we can reason about policy, residency, cost ceilings, and telemetry per capability.
- Every LangGraph node is named by `StageKey` and records `{agent_task, llm_profile_id, depends_on[], retry_budget, cost_ceiling}`. This metadata is exported from `packages/automation/pipelines/stage_map.py` and linted via doc tools to keep diagrams and code paths aligned.
- Finalize nodes are pure: they never call providers, only version artifacts (`_v1`, `_v2`, …), compute SHA-256 manifests, and append ops JSON/JSONL. All provider work happens in capability-specific stages.

## Analyze overview

- Analyze fans out into dedicated lanes (outline, timeline, entities, issues, gaps, flags/alerts) after atom extraction. Each lane uses `EXTRACT`, feeds the canonical summary (`GENERATE`), and reports into staff report + QA lanes (`GENERATE`/`EVAL`).
- Lane QA and cross-lane QA use `EVAL` to enforce schemas, coverage, and citation density, issuing deterministic revision directives that target specific `StageKey` values.
- Atoms remain first-class: `AN_ATOMS_EXTRACT` converts transcript segments into canonical atoms with UUID5 identities, citations, and SummaryCheck statuses. All downstream lanes consume the shared AtomsIndex for evidence and QA gating.

## Compose overview

- Compose runs client, lawyer, and optional bundle lanes in parallel (`GENERATE` + `EVAL`). Each lane now includes a deterministic `*_ASSEMBLE` node (pure) that embeds structured JSON into DOCX/Markdown templates before finalize writes.
- Cross-lane QA uses `EVAL` to synthesize staff + QA reports, and revision directives only re-run failing sections/lanes.
- Finalize nodes (`CO_FINALIZE_WRITE`) are the only stages that touch disk.

## Diagrams & appendices

- All diagrams under `docs/automation/langgraph-agents/diagrams/` and TDD appendices are kept in v1 while the spec remains in draft. Regenerate them via `make docs-diagrams` after editing Mermaid sources.
- Appendix: `docs/overview/tdd/appendices/diagrams.md` indexes every canonical diagram (LangGraph pipelines, stage catalog).
