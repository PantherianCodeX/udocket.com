# uDocket — Agent Team (LangGraph) Plan

Scope: entire agentic stack across transcription, summary, timeline, and entities/graph. This plan defines roles, goals, backstories, LangGraph node design, shared state, prompts, and integration points so we can implement a reliable, Canadian‑region compliant agent graph.


## North Star
- Generate accurate, auditable legal artifacts from transcripts to accelerate court form preparation — without sending PII outside Canada.
- Deterministic files, structured outputs per stage, additive versioning, and clear ops logs per the root AGENTS.md.


## Agent Roles, Goals, Backstories
Use these as system prompts/personas in LangGraph nodes.

- Orchestrator — "Case Supervisor"
  - Goal: coordinate all stages; enforce guardrails (Canadian regions, file naming, versioning), and make recovery decisions on failure without silent fallbacks.
  - Backstory: a meticulous paralegal supervisor in Canada, trained on uDocket conventions, responsible for deadlines and compliance.

- Input Steward — "Records Clerk"
  - Goal: discover latest transcript (or provided path), parse header/body, detect diarization, collect case intake data.
  - Backstory: a clerk who prepares clean inputs for downstream agents and flags missing context early.

- Transcriber — "Court Reporter" (implemented)
  - Goal: produce timestamped transcripts from audio using Azure Speech (Canada), diarization in batch mode.
  - Backstory: a court reporter who stamps time and speakers consistently.

- Context Builder — "Docket Summarist"
  - Goal: compile an intake brief (court, division, parties, posture) and an index of transcript segments.
  - Backstory: a summary writer who extracts what matters from intake and headers.

- Extractor — "Issue Analyst"
  - Goal: extract issues, claims/remedies, material facts (with timestamps), deadlines, orders, exhibits, and legal references as JSON.
  - Backstory: an analyst who structures hearings into machine‑readable outlines.

- Chronologist — "Timeline Editor"
  - Goal: normalize an event list tied to transcript timestamps and speakers.
  - Backstory: an editor obsessed with chronological clarity.

- Entity Mapper — "Relationship Cartographer"
  - Goal: identify people, orgs, places, dockets and propose relationship edges with evidence pointers.
  - Backstory: a mapper who sees roles and links across dialogue.

- Drafter — "Brief Writer"
  - Goal: produce a layered Markdown summary (exec summary, detailed narrative by issue, claims/remedies, posture, risks, next steps) referencing timestamps.
  - Backstory: a Canadian paralegal who writes for practitioners preparing forms.

- QA Auditor — "Compliance Officer"
  - Goal: verify required sections exist, cross‑check counts, apply style conventions, redact obvious PII in ops logs, and compute SHA‑256 for artifacts.
  - Backstory: a compliance specialist who signs off on artifacts and logs provenance.

- File Steward — "Ops Scribe"
  - Goal: write per‑run JSON meta, append case ops JSONL, and ensure versioned outputs.
  - Backstory: a scribe who never overwrites and always leaves an audit trail.


## Graph Design (LangGraph)
We model each role as a node with clear inputs/outputs. Control flow is linear with guarded branches; failures propagate to the caller so the task can surface actionable errors instead of silently falling back.

- Nodes
  1. `input_discovery` (Input Steward)
  2. `parse_transcript` (Input Steward)
  3. `context_builder` (Context Builder)
  4. `extract_outline` (Extractor, JSON schema)
  5. `build_timeline_seeds` (Chronologist, JSON schema)
  6. `build_entity_hints` (Entity Mapper, JSON schema)
  7. `draft_markdown` (Drafter, Markdown)
  8. `qa_and_finalize` (QA Auditor)
  9. `write_ops_and_artifacts` (File Steward)

- Edges
  - Straight line 1→9 with error edges:
    - If 4/5/6 Azure disabled or schema invalid → raise a descriptive error and stop; orchestration layer chooses retry strategy.
    - If 7 fails → degrade to outline‑only summary header + bulleted key facts.
  - Graph terminates with `status=ok|failed`, all errors logged.

- Shared State (example dataclass)
```
case_id: str
job_id: str
case_dir: Path
transcript_path: Path | None
header_meta: dict
segments: list[dict]  # {ts: float|None, speaker: str|None, text: str}
intake: dict          # case fields (position, court, division, etc.)
outline: dict | None
timeline_seeds: list[dict] | None
entity_hints: dict | None
draft_md: str | None
final_md: str | None
artifacts: dict[str, Path]  # summary, outline, timeline_seeds, entity_hints
ops: dict                   # per‑run meta items
errors: list[str]
attempts: dict[str, int]
```

- Guardrails
  - Azure OpenAI endpoint must be `canadacentral` or `canadaeast`.
  - Never send audio; only transcripts + minimal intake context.
  - Versioned files with `_vN` suffix using `_next_versioned`.


## Node I/O Contracts
- `input_discovery`
  - In: case_id, job_id, case_dir, optional input path
  - Out: transcript_path (latest if none provided)

- `parse_transcript`
  - In: transcript_path
  - Out: header_meta (parsed banner), segments (list)

- `context_builder`
  - In: header_meta, intake
  - Out: brief dict `{ parties, court, division, posture, claims? }`

- `extract_outline` (Azure JSON schema)
  - In: segments (plus brief)
  - Out: `outline` (see packages/udocket_core/agents/summary/AGENTS.md schema)

- `build_timeline_seeds` (Azure JSON schema)
  - In: segments
  - Out: `timeline_seeds` (array of events)

- `build_entity_hints` (Azure JSON schema)
  - In: segments
  - Out: `entity_hints` ({ entities, relations })

- `draft_markdown` (Azure creative → Markdown)
  - In: outline, timeline_seeds, entity_hints, brief, segments
  - Out: `draft_md`

- `qa_and_finalize`
  - In: draft_md
  - Out: `final_md` (ensured sections), `checksums`

- `write_ops_and_artifacts`
  - In: final_md + JSON artifacts
  - Out: files under `analysis/`, ops JSON, audit JSONL


## Prompt Principles
- Shared system prompt: Canadian paralegal assistant. Use only provided info. Do not fabricate. Return exact schema/Markdown requested.
- JSON stages use response_format: json_schema with schemas defined in the Summarize agent AGENTS.
- Include compact context: intake brief + a bounded window of diarized segments (chunk and slide if needed; keep token limits configurable).


## Security & Locality
- Validate endpoint hostnames; deny non‑Canadian regions.
- Mask PII in ops logs; do not log raw prompts unless `DEBUG=1`.
- Respect upstream duration limits; summarizer should process text only.


## Integration Points
- Celery tasks
  - Transcription: `transcribe_job` (exists)
  - Summarize: `summarize_job` → call SummarizeAgent; write artifacts and ops logs, register CaseArtifact, emit websocket.
  - Timeline: consume `timeline_seeds` if present.
  - Graph: consume `entity_hints` if present.

- UI
  - Summarize panel already wired; ensure artifact titles and download links reflect new outputs.


## Implementation Plan
1) Implement `packages/udocket_core/agents/summarize_lib.py` (config, agent, pipeline, Azure REST client).
2) Update `apps/platform/operations/tasks.py:summarize_job` to use SummarizeAgent, pass intake fields.
3) Ensure versioned outputs and ops logs; register CaseArtifact for summary.
4) Extend timeline/graph tasks to optionally read `timeline_seeds`/`entity_hints` if present.
5) Add unit tests for transcript parsing, versioned filenames, and schema shapes; keep flow test passing without Azure.
6) Optional: create `packages/udocket_core/agents/langgraph_orchestrator.py` to wire nodes when `langgraph` is installed.


## Optional: LangGraph Skeleton
Below is a minimal sketch; keep import optional to avoid hard dependency.
```
try:
    from langgraph.graph import StateGraph, END
except Exception:  # optional dependency
    StateGraph = None
    END = None

def build_summarize_graph(impl):
    # `impl` provides python callables for each node, operating on a mutable dict state
    if StateGraph is None:
        raise RuntimeError("langgraph not installed")
    g = StateGraph(dict)
    g.add_node("input_discovery", impl.input_discovery)
    g.add_node("parse_transcript", impl.parse_transcript)
    g.add_node("context_builder", impl.context_builder)
    g.add_node("extract_outline", impl.extract_outline)
    g.add_node("build_timeline_seeds", impl.build_timeline_seeds)
    g.add_node("build_entity_hints", impl.build_entity_hints)
    g.add_node("draft_markdown", impl.draft_markdown)
    g.add_node("qa_and_finalize", impl.qa_and_finalize)
    g.add_node("write_ops_and_artifacts", impl.write_ops_and_artifacts)

    g.set_entry_point("input_discovery")
    g.add_edge("input_discovery", "parse_transcript")
    g.add_edge("parse_transcript", "context_builder")
    g.add_edge("context_builder", "extract_outline")
    g.add_edge("extract_outline", "build_timeline_seeds")
    g.add_edge("build_timeline_seeds", "build_entity_hints")
    g.add_edge("build_entity_hints", "draft_markdown")
    g.add_edge("draft_markdown", "qa_and_finalize")
    g.add_edge("qa_and_finalize", "write_ops_and_artifacts")
    g.add_edge("write_ops_and_artifacts", END)
    return g.compile()
```


## Backward Compatibility
- Offline summarization stays the default when Azure env is not configured so development and CI remain deterministic.
