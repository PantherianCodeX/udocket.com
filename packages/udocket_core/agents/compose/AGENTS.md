# Compose Agent Guide

This guide covers the Compose agent pipeline that generates case deliverables (client & lawyer briefs), normalized timeline v2 artifacts, and relationship graph assets. Follow these conventions together with the root `AGENTS.md` and the area guides located alongside the UI and operations code.

## Purpose
- Consume approved Analyze outputs (summary JSON/Markdown, timeline seeds, entity hints, case brief) plus transcript excerpts and intake metadata.
- Produce deterministic artifacts housed under `storage/media/cases/<CASE>/analysis/` with `_vN` suffix versioning and append-only ops logs under `ops/`.
- Maintain stable UUIDs for every structured record (timeline events, entities, relationships) and reserve user-facing titles for presenter helpers via `unique_title`.
- Hydrate stages with the current case metadata (case identifiers, organization, job titles) alongside Analyze outputs so prompts stay grounded in the matter context.

## Stage Plan
The Compose pipeline runs sequential stages. Stage keys align with `config/llm_assignments.json` and `packages/udocket_core/agents/compose/profiles.py`.

| Stage key | Role | Inputs | Output | Notes |
|-----------|------|--------|--------|-------|
| `compose.context_builder` | Case Brief Synthesizer | Intake payload, case metadata, summary JSON/Markdown, staff report, transcript excerpt | JSON case brief (`parties`, `issues`, `posture`, `risks`, `next_steps`, `key_facts`) | Must return structured JSON; feeds downstream prompts. |
| `compose.timeline_builder` | Timeline Author | Case brief, timeline seeds, case metadata, summary data, transcript excerpt | `timeline_v2` JSON `{"events": [...]}` | Preserve provided `id`/`uuid` values when present; derive UUID5 otherwise. |
| `compose.timeline_summary` | Timeline Narrator | Case metadata, timeline_v2 JSON, summary data | Markdown narrative of key milestones | Feeds both briefs and QA with human-readable highlights. |
| `compose.graph_builder` | Relationship Cartographer | Case brief, entity hints, timeline, case metadata, summary data, transcript excerpt | Graph JSON `{entities, relationships}` | Every entity/relationship returns stable `uuid` + `id`; include evidence pointers. |
| `compose.entity_brief` | Entity Briefing Specialist | Case metadata, graph payload, entity hints, timeline | Markdown briefing covering parties and relationships | Used by both client and lawyer deliverables for quick reference. |
| `compose.graph_visual` | Graph Visual Planner | Case metadata, graph payload | JSON with embeddable HTML, sizing, and accessibility notes | Enables UI/docx embedding with consistent styling. |
| `compose.client_brief` | Client Brief Drafter | Case brief, timeline, graph, summary Markdown, staff report, intake, case metadata | Markdown deliverable at grade-six reading level | Tone: empathetic/explanatory. |
| `compose.lawyer_brief` | Counsel Brief Drafter | Case brief, timeline, graph, summary Markdown, case metadata | Professional Markdown with issue/evidence organization | Lower temperature (`COMPOSE_LAWYER_TEMPERATURE`). |
| `compose.qa_review` | QA Reviewer | Case brief, timeline, graph, client & lawyer Markdown, case metadata | JSON QA payload (`status`, `alerts`, `recommendations`) | Temperature forced to 0; no generative text. |

All stages rely on Canadian-region Azure OpenAI deployments by default. Configure per-organization overrides through LLM assignments.

## LLM Configuration
- Default provider chain: `azure`. Organizations can override via `provider_chain` or per-stage `stage_map` entries in `LLMConfiguration` records. Use the stage keys above.
- Recommended default models (see `config/llm_assignments.json`):
  - Context/Timeline/Graph/QA → `gpt-4o-mini`
  - Client/Lawyer briefs → `gpt-4o`
- Stage profiles defined in `profiles.py` set context window guidance and reserved output tokens. Respect these when selecting custom models.
- `ComposeAgent.compose()` automatically merges provider chains and loads provider credentials via `get_provider_secret_with_metadata`.

## Inputs
- Summary artifacts: JSON + Markdown (latest `_vN` files) resolved from Analyze job metadata or directory search.
- Timeline seeds: `{job_id}__timeline_seeds_v1.json` (analysis dir) with UUID-bearing events.
- Entity hints: `{job_id}__entity_hints_v1.json` with entities/relations and UUIDs.
- Staff report / case brief: `{job_id}__case_brief_v1.{json|md}` if present.
- Transcript: latest `.txt` transcript to provide excerpt context.

## Outputs
- `analysis/<job_id>__timeline_v2.json`
- `analysis/<job_id>__graph_v2.json`
- `analysis/<job_id>__entities_v2.json` (entity list derived from graph payload)
- `analysis/<job_id>__compose_timeline_v1.md` (timeline narrative)
- `analysis/<job_id>__compose_entities_v1.md` (entity briefing)
- `analysis/<job_id>__compose_graph_visual_v1.json` (graph embed instructions)
- `analysis/<job_id>__compose_client_v1.{md,docx}`
- `analysis/<job_id>__compose_lawyer_v1.{md,docx}`
- Ops log: `ops/<job_id>__compose_log.json`
- Audit stream: `ops/ops_compose.jsonl`

All structured outputs MUST include a `uuid` field, preserving incoming UUIDs when supplied and generating UUID5 signatures from canonical content otherwise. Do not expose UUIDs in UI titles; presenters build human labels with `unique_title` in the operations task layer.

## Failure Handling
- Any stage failure raises `ComposeStageError` with stage-qualified message. Caller (Celery task) records `compose_status="failed"` in job metadata and surfaces the error.
- Missing prerequisite artifacts cause early validation errors before LLM calls. Compose does not silently regenerate Analyze outputs.

## Testing Guidance
- Use `tests/test_compose_lib.py` for unit coverage of helper normalization utilities and artifact creation.
- End-to-end flow coverage lives in `tests/test_platform_flow.py` (Compose section). When adding new outputs, extend both tests.

## Integration Notes
- Celery task `apps.platform.operations.tasks.compose_job` resolves inputs, builds provider credential map, and registers artifacts with deterministic titles (`unique_title`).
- UI presenters consume artifact metadata from `CaseArtifact` records; ensure metadata fields include source summary filenames for audit linking.

Following this plan keeps Compose aligned with the Analyze pipeline and maintains deterministic, auditable artifacts across reruns.
