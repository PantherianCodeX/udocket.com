# Compose Agent LLM Plan

This document defines the Compose pipeline stages, the LLM responsibilities for each step, and the contract for generating timeline and relationship graph artifacts. It aligns with the root **AGENTS.md**, `docs/ROADMAP.md`, and `docs/AGENTS_LANGGRAPH.md` requirements.

## Objectives
- Assemble client- and lawyer-facing deliverables from approved transcripts and summaries without leaving Canadian regions.
- Generate timeline (`timeline_v2.*`) and relationship graph (`graph_v2.*`) artifacts inside the Compose pipeline.
- Produce deterministic, versioned outputs with per-run ops JSON, audit JSONL entries, and SHA-256 hashes.
- Fail fast on missing credentials or artifacts; never fall back to non-LLM heuristics for narrative content.

## Inputs
- Latest approved transcript and summary (`analysis/<job_id>__summary_v1.*`).
- Optional staff report, timeline seeds, and entity hints from the Analyze agent.
- Intake metadata (court, parties, relief sought, deadlines) and attached case artifacts (letters, statements, forms).
- Organization configuration: LLM provider chain, stage map overrides, DOCX templates.

## Stage Overview
The Compose agent orchestrates the following stages. LLM-powered nodes are prefixed with **LLM**.

1. **input_discovery** (deterministic)
   - Locate the primary transcript, approved summary, intake metadata, and auxiliary artifacts.
   - Validate dependencies (summary approval, transcript availability) and hydrate shared state.

2. **parse_sources** (deterministic)
   - Parse transcript segments, summary outline, and staff report into structured payloads.
   - Collect references for timeline/graph grounding (timestamps, speakers, issue tags).

3. **LLM `compose.context_builder`**
   - Analyze intake details, key issues, parties, and outstanding questions into a compact brief.
   - Output JSON `{ parties, issues, court, division, relief, risks, questionnaire_flags }`.

4. **LLM `compose.timeline_builder`**
   - Produce a normalized event list referencing transcript timestamps and speakers.
   - Output JSON schema `events[{ ts_start, ts_end?, speaker?, label, summary, evidences[] }]`.
   - Write to `analysis/<job_id>__timeline_v2.json`, plus optional HTML snapshot.

5. **LLM `compose.graph_builder`**
   - Extract entities (people, organizations, locations, documents) and relationship edges with evidence.
   - Output JSON schema `{ entities[], relationships[] }` with timeline refs.
   - Write to `analysis/<job_id>__graph_v2.json` and optional HTML/PNG render metadata.

6. **LLM `compose.client_brief`**
   - Draft a client-facing Markdown deliverable (grade-6 reading level, empathetic tone) referencing timeline events.
   - Output Markdown stored at `analysis/<job_id>__compose_client_v1.md`.

7. **LLM `compose.lawyer_brief`**
   - Draft a professional, issue-organized Markdown deliverable for legal counsel.
   - Output Markdown stored at `analysis/<job_id>__compose_lawyer_v1.md`.

8. **LLM `compose.qa_review`**
   - Verify mandatory sections, cross-check against context brief, and flag missing references.
   - Emit structured QA findings appended to ops JSON.

9. **render_artifacts** (deterministic)
   - Convert Markdown outputs to DOCX using per-org templates.
   - Persist Markdown/DOCX pairs, timeline/graph JSON (and optional HTML/PNG), ops JSON, and audit JSONL with SHA-256 hashes.

10. **ops_finalize** (deterministic)
    - Write `ops/<job_id>__compose_log.json`, append `ops/ops_compose.jsonl`, emit websocket events.

## Data Contracts
- Timeline schema upgrades to `v2` with richer labels and evidence arrays. Ops metadata records schema version, event count, checksum, and source inputs.
- Graph schema upgrades to `v2` capturing entity roles, relationship categories, and evidence pointers to both transcript timestamps and timeline event IDs.
- Every timeline event, entity, and relationship must expose a stable `uuid` (UUIDv5 over canonical content) alongside any human-readable identifiers to preserve cross-run referential integrity.
- Markdown deliverables must embed source references (`[TS 00:12:30]`) for traceability; QA stage validates reference density.
- Ops JSON stores: `case_id`, `job_id`, `artifacts`, `checksums`, `provider_chain`, `stage_results`, `timeline_file`, `graph_file`, `source_summary`, timestamps, and tool/library versions.
- Audit JSONL lines include `compose_client_md`, `compose_lawyer_md`, `timeline_v2`, `graph_v2`, `duration_s`, and guardian verdict summaries when applied.

## Stage Profiles & Token Budgets
Default token guidance (configurable per org via stage map overrides):

| Stage Key | Purpose | Recommended Context Tokens | Output Reserve |
|-----------|---------|----------------------------|----------------|
| `compose.context_builder` | Intake + summary condensation | 32k | 2k |
| `compose.timeline_builder` | Event extraction | 64k | 4k |
| `compose.graph_builder` | Entity/relationship synthesis | 64k | 4k |
| `compose.client_brief` | Client deliverable | 80k | 6k |
| `compose.lawyer_brief` | Lawyer deliverable | 100k | 8k |
| `compose.qa_review` | QA & discrepancy detection | 32k | 2k |

These limits inform stage profile hints and default `max_tokens` when configuring providers.

## Provider Chain Defaults
- Default provider chain: `['azure', 'openai']` with Azure deployments required for production (Canada Central/East).
- Stages inherit provider/model defaults from `config/llm_assignments.json` but remain overrideable per organization via LLM configuration records.
- Timeline and graph stages share the same defaults so standalone Timeline/Graph tools remain consistent with Compose outputs.

## Failure Handling
- Missing transcript or summary → raise `MissingDependencyError` before invoking LLMs.
- LLM failures → bubble descriptive `ComposeStageError` with stage name, provider, model, attempt count.
- If timeline/graph stages fail, mark compose job failed; downstream deliverables must not proceed without them.
- QA failures flag the job and write actionable guidance to ops JSON; guardian enforcement runs post-render via the existing Guardian agent.

## Outputs & Storage Layout
- Markdown: `analysis/<job_id>__compose_client_v1.md`, `analysis/<job_id>__compose_lawyer_v1.md`.
- DOCX: `analysis/<job_id>__compose_client_v1.docx`, `analysis/<job_id>__compose_lawyer_v1.docx`.
- Timeline: `analysis/<job_id>__timeline_v2.json`, optional `..._v2.html`, `..._v2.png`.
- Graph: `analysis/<job_id>__graph_v2.json`, optional `..._v2.html`, `..._v2.png`.
- Ops JSON: `ops/<job_id>__compose_log.json`.
- Audit JSONL: `ops/ops_compose.jsonl`.

## Next Steps
1. Implement `packages/udocket_core/agents/compose_lib.py` mirroring the Analyze agent structure with stage orchestrator and deterministic writers.
2. Extend `config/llm_assignments.json` with the Compose stage defaults listed above.
3. Update UI stage cards and ops telemetry to surface timeline/graph outputs generated by Compose.
4. Add Celery task `compose_job` to coordinate Compose agent execution, artifact creation, and guardian review triggers.
