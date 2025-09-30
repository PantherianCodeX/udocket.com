# uDocket — Summarize Analysis Agent Guide

Scope: this guide governs the Summarize analyzer implementation under `packages/udocket_core/agents/summarize/` and any platform tasks that orchestrate it. It extends the root AGENTS.md contract and the `packages/udocket_core/AGENTS.md` rules.

Purpose: generate layered, legally‑useful summaries from approved transcripts, suitable for preparing court forms, timelines, and relationship graphs. The agent consumes diarized or plain transcripts and produces both human‑readable and structured artifacts for downstream tools.


## Design Goals
- Deterministic, reproducible outputs with per‑run metadata and audit logging.
- Privacy and locality: process only transcripts and metadata; never upload audio; ensure Canadian residency when Azure is used.
- Composable pipeline: multiple “sub‑agents” produce structured JSON at each stage and a cohesive Markdown summary assembled last.
- Provider-agnostic orchestration: provider/model selection flows from the active `LLMConfiguration`, and chat clients are constructed dynamically via `packages.udocket_core.llm.runtime` (Azure, OpenAI-compatible, Anthropic, Ollama, etc.).
- Stage-level tuning: per-stage output limits, temperature, and deployment overrides are stored in `LLMConfiguration.stage_map` and configured through the platform UI.
- First‑class integration with Celery tasks and UI panels; no overwrites (versioned filenames).
- Long-context friendly: allow entire interviews to flow through by tuning prompt limits and stage model/token overrides instead of truncating aggressively.


## Agent Composition (Sub‑Agent Roles)
Implement the SummarizeAgent as a pipeline of small, purpose‑specific stages. Each stage has an input contract and a structured output, written to disk under `analysis/`, and referenced by the ops metadata.

- ContextBuilder (Stage 0)
  - Input: transcript header/body, case intake fields.
  - Output: compact case brief (in-memory) injected into all prompts.
  - Automatically chunks transcript excerpts per stage so Azure prompts stay within the selected model’s context window (or any manual override).

- Extractor (Stage 1)
  - Task: extract Parties, Issues, Claims & Remedies, Facts, Deadlines, Orders, Exhibits, Legal References.
  - Output file: `analysis/<job_id>__outline_v1.json` (schema below).

- Chronologist (Stage 2)
  - Task: produce normalized event seeds for the Timeline agent.
  - Output file: `analysis/<job_id>__timeline_seeds_v1.json`.

- EntityMapper (Stage 3)
  - Task: derive entity/role hints and proto‑relations to jump‑start the Graph agent.
  - Output file: `analysis/<job_id>__entity_hints_v1.json`.

- Drafter (Stage 4)
  - Task: assemble a layered Markdown summary with mandatory sections and references to timestamps.
  - Output file: `analysis/<job_id>__summary_v1.md` (primary artifact).

- QA/Assembler (Stage 5)
  - Task: verify required sections, compute SHA‑256 for every artifact, finalize ops metadata, append audit JSONL.


## Library API (Core Package)
Add `packages/udocket_core/agents/summarize_lib.py` implementing a pure‑Python library (no Django imports).

- Data classes
  - `SummarizeConfig`
    - `language: str = "en-CA"`
    - `temperature: float = 1.0`
    - `max_output_tokens: int = 24000`
    - `provider_chain: List[str]` — default provider preference order when stage configs do not override it.
    - `max_prompt_segments: int = 250` (0 disables the segment cap)
    - `max_prompt_chars: int = 32000` (0 disables the char cap)
    - `default_stage_model: str | None`
    - `stage_model_overrides: Dict[str, str]`
    - `stage_max_output_tokens: Dict[str, int]`
    - `chars_per_token: float = 4.0`
    - `debug: bool = False`
    - `@classmethod from_env()` — loads defaults from `config/summarize_defaults.json`; no credentials are pulled from environment variables.
  - `SummarizeResult`
    - `status: str`
    - `summary_file: Path`
    - `outline_file: Path | None`
    - `timeline_seeds_file: Path | None`
    - `entity_hints_file: Path | None`
    - `words: int`
    - `source_transcript: Path`
    - `meta_json: Path` — per‑run ops JSON
    - `audit_jsonl: Path` — case ops audit stream

- Main class
  - `class SummarizeAgent:`
    - `def __init__(self, config: SummarizeConfig | None = None) -> None`
    - `def summarize(self, *, input: Path | None, case_id: str, case_dir: Path, job_id: str, intake: dict | None = None, transcript_hint: dict | None = None) -> SummarizeResult`
      - Input discovery: if `input` is None, use the most recent transcript under `transcript/`.
      - Writes artifacts and ops logs under `analysis/` and `ops/` with versioned names (`_v2` etc.).
- Network usage: the active LLM configuration supplies provider and model details. Per-provider credentials are sourced from `LLMProviderCredential` rows (decrypted in the worker) and combined with stage overrides before constructing chat clients. Azure endpoints must still target canadacentral or canadaeast unless the credential metadata explicitly allows otherwise.

- Helpers
  - Transcript parsing: split header/body; detect diarized lines like `"[MM:SS] SPK_<id>: text"`; build normalized segments.
  - `_next_versioned(Path) -> Path` — reuse from `transcribe_lib` to avoid overwrites.
  - `_append_jsonl(Path, dict)` — append audit rows.
  - `sha256(Path) -> str` — compute SHA‑256 for all artifacts.


## Azure OpenAI Integration
- Transport: REST (no heavy SDK).
- Endpoint: `POST {AZURE_OPENAI_ENDPOINT}/openai/deployments/{DEPLOYMENT}/chat/completions?api-version={API_VERSION}`
- Headers: `api-key`, `Content-Type: application/json`.
- Shared system prompt: “You are a Canadian paralegal assistant. Use only provided information. Do not fabricate. Return outputs in the exact schema or Markdown requested. Keep PII within context.”
- JSON schema forcing for structured stages via `response_format: { type: "json_schema", json_schema: { name, schema } }`.
- Locality guard: reject endpoints not in `canadacentral` or `canadaeast` (raise with clear message). Never send audio — transcripts only.


## File & Naming
- Input transcript (default): latest `transcript/*__transcript.txt` under the case path.
- Outputs (versioned on re‑run):
  - Primary summary: `analysis/<job_id>__summary_v1.md`
  - Outline: `analysis/<job_id>__outline_v1.json`
  - Timeline seeds: `analysis/<job_id>__timeline_seeds_v1.json`
  - Entity hints: `analysis/<job_id>__entity_hints_v1.json`
- Ops logging per run:
  - Per‑run JSON: `ops/<job_id>__summary_log.json`
  - Audit lines: `ops/ops_summary.jsonl`


## Structured Output Schemas

Outline v1 (written as JSON):
```
{
  "parties": { "client": {"name": string|null, "role": string|null}, "opposing": {"name": string|null, "role": string|null}, "counsel": [{"name": string, "for": "client"|"opposing"|"other"}] },
  "issues": [{ "id": string, "title": string, "description": string, "stance_client": string|null, "stance_opposing": string|null, "status": "RAISED"|"RESOLVED"|"DEFERRED" }],
  "claims_and_remedies": [{ "claim": string, "remedy_requested": string|null, "amounts": [string], "jurisdictional_notes": string|null }],
  "facts": [{ "ts": number|null, "speaker": string|null, "text": string, "tags": [string] }],
  "deadlines": [{ "label": string, "date": string|null, "ts": number|null, "basis": string|null }],
  "orders_and_directions": [{ "date": string|null, "ts": number|null, "text": string }],
  "exhibits": [{ "id": string, "description": string, "cited_ts": [number] }],
  "legal_refs": [{ "citation": string, "context": string }]
}
```

Timeline seeds v1:
```
[{ "ts_start": number, "ts_end": number|null, "speaker": string|null, "text": string, "labels": [string] }]
```

Entity hints v1:
```
{
  "entities": [{ "id": string, "name": string, "type": "PERSON"|"ORG"|"LOC"|"DOCKET"|"OTHER", "aliases": [string] }],
  "relations": [{ "type": string, "source": string, "target": string, "evidence": [{ "ts": number|null, "text": string }] }]
}
```

Markdown summary v1 sections (required):
- Case metadata (court, division, parties, posture)
- Executive summary (5–10 bullets)
- Detailed narrative aligned to issues and facts (include `[mm:ss]` refs where available)
- Claims and remedies sought
- Procedural posture, orders, and deadlines
- Risks, gaps, questions
- Next‑step checklist


## Ops Metadata
Per‑run JSON: `ops/<job_id>__summary_log.json` (keys)
- `case_id`, `job_id`, `source_transcript`
- `summary_file`, `outline_file`, `timeline_seeds_file`, `entity_hints_file`
- `sha256_summary`, `sha256_outline`, `sha256_timeline_seeds`, `sha256_entity_hints`
- `language`, `provider_chain`, `timestamp_utc`, `status`
- Optional when `debug = True`: `prompt_tokens`, `completion_tokens`

Audit line in `ops/ops_summary.jsonl` mirrors the above in a single JSON object with `ts` and `event` (`"summary.created"`).


## Configuration & Environment
- Primary control plane: `LLMConfiguration` rows (scoped per organization) capture the provider chain and stage map the worker must honour. Each configuration is surfaced in the UI for selection when queueing jobs.
- Each organization manages credentials via `LLMProviderCredential` records (UI: Case ▸ LLM ▸ Providers). The worker decrypts the API key/endpoint at runtime and merges stage overrides before invoking a provider.
- Default runtime parameters (temperature, provider chain, prompt limits, stage token budgets) are defined in `config/summarize_defaults.json`.
- If the active LLM configuration references a provider without credentials, the worker must exit with a descriptive error. No offline or pseudo-local fallback is permitted.


## Stage Capabilities API
- `SummarizeAgent.stage_catalog()` returns metadata for each stage:
  - `label`, `description`, `resource_notes`
  - `min_context_tokens`, `recommended_context_tokens`, `output_reserve_tokens`
  - `recommended_models` (provider/model pairs with sufficient context window) and a full `eligible_models` list.
- The UI can use this to surface model recommendations (e.g., “Outline Extractor prefers models with ≥100k tokens”).


## Celery/Platform Integration
- Task: `apps.platform.operations.tasks.summarize_job`
  - Replace internal logic to invoke `SummarizeAgent.summarize(...)`.
  - Pass `intake` from `Case` model fields (if present): `client_position`, `court_level`, `court_division`, `court_location`, `court_case_number`, `court_date`, `filing_deadline`, `client_name`, `opposing_party`.
  - Register artifact (`CaseArtifact` type = `SUMMARY`) with checksum; emit `send_case_update(..., event="artifact.created", kind="summary")`.
  - Fail fast when no configured LLM provider is available. The worker must surface a descriptive error and record the ops JSON/JSONL entry rather than attempting a degraded offline path.


## Error Handling & Retries
- Fail fast with descriptive messages when:
  - No transcript found / transcript unreadable
  - Requested provider lacks credentials or required options (e.g., missing API key/deployment)
  - Provider API returns non-success responses (include HTTP status + summarized body in ops JSON)
  - Azure endpoints violate the Canadian region guard (unless explicitly overridden via credential metadata)
- Retries: exponential back‑off on transient 429/5xx (bounded by config). Log attempts in ops metadata.
- Always write ops JSON and append an audit line on both success and failure (with `status`).


## Security Notes
- Enforce Canadian residency for Azure endpoints; other providers must honour organization policy (store endpoints per credential).
- Never transmit raw audio.
- Avoid persisting sensitive prompts/responses unless `debug=1`.
- Respect `MAX_MINUTES`/size limits upstream (transcription). Summarizer should stream transcript content to prompts with compact context windows (chunk + roll‑up strategy) when needed.


## CLI (Optional)
You may expose a thin CLI under `scripts/`:
```
python -m packages.udocket_core.agents.summarize_lib \
  --case <CASE_ID> \
  --case-dir /app/storage/media/cases/<CASE_ID> \
  --job <JOB_ID> \
  --input /app/storage/media/cases/<CASE_ID>/transcript/<job>__transcript.txt
```
Stdout (success): `{ "status":"ok", "summary_file":"<abs_path>", "words":1234, "source_transcript":"<abs_path>" }`


## Testing
- Unit: transcript parsing (diarized vs. plain), versioning behavior, schema shape validity.
- Integration (platform): ensure platform flows surface configuration errors when required provider credentials are absent; add a gated E2E that runs against a configured provider (skipped by default).


## Roadmap
- Link timeline seeds and entity hints directly into the Timeline and Graph agents when those tasks are invoked, preferring latest versions.
- Add citation links back to transcript timestamps in Markdown summary.
- Add per‑section confidence/coverage diagnostics in ops JSON.
