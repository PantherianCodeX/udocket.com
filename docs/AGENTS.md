# uDocket — Agents Guide

This document defines how automation and contributors should add and operate "agents" in the uDocket stack. It covers the current transcription agent and lays down clear conventions for future agents such as summarization, timelines, and relationship/graph extraction.

**Single source:** This is the only AGENTS guide. All area-specific copies have been removed; reference this file (and the TDD’s engineering standards in §2.3) whenever you need binding guidance.

## Engineering standards (binding)

- **Type-first development.** Before editing logic, introduce the strongly typed primitives the file needs (dataclasses, `TypedDict`, `Protocol`, `StrEnum`, wrappers, or helper classes). Provider payloads must be represented by precise types or local stubs—never raw dicts. Missing third-party stubs are added alongside the change (no TODOs).
- **Zero tolerance for `Any`.** New code may not add `typing.Any`. When touching legacy code, remove Any annotations as part of the change. Casts are a last resort: keep them in helper functions with a short comment explaining the invariant they protect. Never add `# type: ignore` or lint ignores; fix the root cause instead.
- **Strict Python 3.12+.** Use modern syntax (`match/case`, `StrEnum`, `dataclasses`, `contextlib.asynccontextmanager`, `zoneinfo`). Delete compatibility branches for earlier Python versions and refuse polyfills/back-compat shims.
- **Separation of concerns.** Main modules orchestrate flows; supporting modules provide models and pure helpers. Do not mix HTTP/Django concerns with LangGraph orchestration or disk IO in the same function. Extract shared helpers to `packages/common` when they are framework-agnostic, otherwise keep them in package-scoped `utils.py`. Module-level helpers stay short and single-purpose.
- **Quality over speed.** Restructure when the design demands it. Keep functions small (prefer <40 LOC) and files cohesive. Document invariants whenever you add or change behavior.
- **Testing discipline.** Every touched module must remain ≥90% line coverage (unit + property tests). Add property tests for determinism (UUIDs, manifests, approvals) whenever you add new data structures. Integration tests cover Celery tasks, Guardian/Signer interactions, and settings activation. No change merges without green tests.
- **Tooling requirements.** Run commands through the provided containers/venvs (`make ...`, `uv run --project …`). Never install ad-hoc dependencies via `pip`. Docs/spec changes must pass `doc_tools.check_links` and MkDocs builds.
- **Helper placement & wrappers.** Cross-cutting helpers (JSON, hashing, parsing) belong in `packages/common`. Agent-specific helpers live alongside the agent implementation. Use thin wrappers (value objects) around primitive strings/IDs instead of passing raw literals between layers.
- **AI runtime layering.** Automation agents call `packages.ai.api` (or an injected `AIClient`) exclusively for AI operations. Provider adapters, routing, and residency/egress guards live under `packages/ai/`; platform or automation code MUST NOT import provider SDKs directly.
- **No back-compat.** When removing deprecated APIs or flags, delete the compat code entirely. Do not add toggles to support “old” behavior—migrations happen in one direction.
- **Flow of control.** Entry-point modules validate inputs, snapshot settings, and delegate to type-safe helpers. They never mutate global state or perform best-effort retries outside the shared retry utilities.
- **Additional expectations.** Always update specs (this file + TDD §2.3) when you introduce new behaviors, include Guardian/Settings impacts in PR descriptions, and keep ops/audit logging additive and deterministic.

## Overview

- Services:
  - `apps/platform` (Django + Channels + Celery): primary UI, API surface, and background workers.
- Core agent implementation lives in `packages/core/agents/transcribe_lib.py` (Azure Speech, region policy enforced).
  - Modes: `on-demand` (local stream) and `batch` (Azure Batch Transcription via HTTPS SAS URL).
  - Diarization: supported in `batch` mode only.
  - Outputs: timestamped transcript `.txt`, per-job JSON metadata, append-only ops audit JSONL.
- Storage layout (per-case, tenant scoped): `storage/media/tenants/<ORG_ID>/cases/<CASE_ID>/`
  - `audio/` original uploads as `<job_id>__<original_name>`
  - `transcript/` transcript files as `<job_id>__transcript.txt`
  - `ops/` logs, metadata, and ops audit files
  - `analysis/` Analyze agent outputs (summaries, seeds, hints, staff reports)
  - `docs/` Compose agent deliverables (Markdown, DOCX, QA bundle)
- Database: SQLite by default (or Postgres) with tables `cases`, `jobs`

## Agent Contract (all agents)

To make agents composable and observable when executed inside Celery workers, follow this contract:

- Implement the `TranscriptionAgent` interface (see `packages/core/agents/transcribe_lib.py`).
  - Accepts structured config (`TranscriptionConfig`) instead of CLI flags.
  - Read configuration from `.env` where relevant, mirroring `config/settings.py` keys.
- Return a `TranscriptionResult` (from `packages.common.agents`) and raise rich exceptions for recoverable errors (the task layer records metadata and updates the UI).
- Deterministic outputs:
  - Write artifacts with stable, case-scoped names and versioning (e.g., `_v2` suffix) when re-running the same job.
- Ops logging:
  - Write a human log and a structured JSON metadata file for each run under `ops/` (see examples below).
  - Append an audit line to an ops JSON Lines file for later analytics.
- Security & locality:
  - AI workloads must run in the organization’s approved regions. Do not send PII outside the configured residency policy.

Reference patterns exist in `packages/core/agents/transcribe_lib.py`.

## Current Transcription Agent

- Entry: `packages/core/agents/transcribe_lib.py`
- Inputs: local file path or HTTPS SAS URL (batch mode), language, diarization flag (batch only)
- Outputs:
  - Transcript: `storage/media/tenants/<ORG_ID>/cases/<CASE_ID>/transcript/<job_id>__transcript.txt`
    - Header includes case, source name, hash(es), language, region, duration, timestamp
    - Body contains text with interval timestamps unless diarization already provides timing
  - Job meta (per job): `storage/media/tenants/<ORG_ID>/cases/<CASE_ID>/ops/<job_id>_transcription_log.json`
  - Human log (per job): `storage/media/tenants/<ORG_ID>/cases/<CASE_ID>/ops/<job_id>_transcription.log`
  - Case ops audit: `storage/media/tenants/<ORG_ID>/cases/<CASE_ID>/ops/ops_transcription.jsonl`
- One-line JSON to stdout on success, e.g.: `{ "status":"ok", "transcript_file":"${STORAGE_ROOT}/media/.../transcript/<job>__transcript.txt", "region":"westeurope", "language":"en-US", "attempts":1, "duration_s":732.5 }`

## Analysis Agents

The repository hosts agents that consume transcripts and emit analysis artifacts. Use the following conventions.

- Common input discovery:
  - Default transcript input: the latest `<job_id>__transcript.txt` or the most recent transcript file in `transcript/`.
  - Agents should accept `--input <path>` to override, and `--case`, `--case-dir`, `--outdir` similarly to the transcriber.

- Output directory:
  - Write to `storage/media/tenants/<ORG_ID>/cases/<CASE_ID>/analysis/` and `storage/media/tenants/<ORG_ID>/cases/<CASE_ID>/ops/`.
  - Use per-job or per-run names with the same prefix style when tied to a transcription job: `<job_id>__<artifact>.<ext>`.

- Analyze agent
  - Purpose: produce layered analyses from transcripts, including structured artifacts for downstream compose/timeline/graph tooling.
  - Artifacts:
    - Primary: `analysis/<job_id>__summary_v1.md` (markdown) or `.txt`
    - Optional: `analysis/<job_id>__outline_v1.json` (hierarchical bullets)
    - Timeline seeds: `analysis/<job_id>__timeline_seeds_v1.json` with deterministic `uuid` per event
    - Entity hints: `analysis/<job_id>__entity_hints_v1.json` with deterministic `uuid` per entity/relationship
    - Ops JSON (per run): `ops/<job_id>__summary_log.json`
    - Ops audit JSONL: `ops/ops_summary.jsonl`
  - Staff report (mandatory): `analysis/<job_id>__staff_report_v1.md` (+ optional JSON companion) with gaps/risks/discrepancies and questionnaire score.
  - Stdout (success): `{ "status":"ok", "summary_file":"<abs_path>", "words":1234, "source_transcript":"<abs_path>" }`

- Compose agent (final assembly)
  - Purpose: generate final, audience-specific deliverables using a LangGraph pipeline with dedicated client and lawyer lanes plus QA gating.
  - Inputs: `summary_v1.json`/`summary_v1.md`, optional timeline seeds & entity hints, intake data, case metadata, and organization-specific provider/template configuration.
  - Outputs:
    - Client deliverable (grade 6, in-client voice): `docs/<job_id>__compose_client_v1.md` and `.docx`
    - Lawyer deliverable (professional legal): `docs/<job_id>__compose_lawyer_v1.md` and `.docx`
    - Bundle excerpt: `docs/<job_id>__compose_bundle_v1.md`
    - QA artifacts: `docs/<job_id>__compose_staff_report_v1.md`, `docs/<job_id>__compose_qa_report_v1.md`
    - Ops JSON (per run): `ops/<job_id>__compose_log.json`
    - Ops audit JSONL: `ops/ops_compose.jsonl`
  - Notes: per‑org DOCX template selection with uDocket default fallback; LangGraph reducers prevent concurrent write conflicts; QA loops until status is acceptable or iteration limits are reached.

- Cross-artifact conventions
  - Versioning: use `_v2`, `_v3`, etc. when regenerating artifacts without overwriting previous outputs.
  - Hashing: where feasible, compute SHA-256 of outputs and include in ops JSON for provenance.
  - Tracing: include `source_transcript` (abs path), `case_id`, `job_id`, timestamps, tool/library versions, and key settings in ops JSON.
  - Approvals/versioning: Manual Edit and Agent Edit produce new versions that require Reviewer approval to promote to the parent task.
- Object identity: every structured record (events, entities, relationships, outline nodes, etc.) must include a stable `uuid` field. Preserve upstream UUIDs when rerunning stages; derive deterministic fallbacks (e.g., UUID5 of canonical content) when none exist. Never expose these UUIDs as user-facing titles.
  - Titles: when creating human-readable artifact titles or per-org/per-case labels, always call the shared `unique_title` helper to avoid collisions within a case/organization.

### Tool and artifact naming map

To avoid future confusion, the table below captures the canonical naming conventions for every first-party agent. Always refer to the *tool* (UI panel, Celery task wrapper, job kind) separately from the *artifacts* it emits.

| Tool / Agent | UI label & panel key | `job_kind` / `agent_type` | Primary artifacts (types & filenames) | Notes |
| --- | --- | --- | --- | --- |
| Transcribe | `Transcribe` / `transcribe` | `transcription` | `transcript/<job_id>__transcript.txt`, ops logs | Produces audio conversions when needed. |
| Analyze | `Analyze` / `analyze` | `analyze` | Stage outputs written under `analysis/` (summary JSON+MD, outline, timeline seeds, entity hints, case brief, optional staff report). Approved outputs generate individual artifacts automatically. | Stage outputs are stored on disk immediately; artifacts are promoted versions exposed in the UI once approved. |
| Compose | `Compose` / `compose` | `compose` | Client & lawyer deliverables (`compose_client_v1.*`, `compose_lawyer_v1.*`), bundle/QA reports, compose ops logs | LangGraph pipeline with parallel lanes, guard rails, and QA gating. |
| Timeline (future standalone) | `Timeline` / `timeline` | `timeline` | To-be-defined `timeline_v2.*` assets | When run independently, should still read latest summary outputs. |

General guidelines:

- Keep UI copy and telemetry fields aligned with the tool name (`Analyze`) while the structured payloads keep the `summary_*` vocabulary for the case narrative outputs.
- Stage outputs may encompass multiple files; artifacts are per-file records created only after approval and removed if later rejected. Each artifact points to a single physical file.
- When adding new artifacts to an existing tool, prefix them with the job ID and use the tool’s directory (`analysis/`, `compose/`, etc.).
- Dependency flags in presenters/components must describe artifacts (`has_summary`, `has_timeline`, etc.) rather than tools. Avoid introducing aliases that duplicate the same concept under different names.

## Worker Integration

- Celery tasks in `apps.platform.operations.tasks` orchestrate uploads, call `TranscriptionAgent.transcribe`, and persist telemetry.
- To integrate new agents, add Celery tasks that wrap your agent implementation and emit job/case websocket updates via `send_job_update`/`send_case_update`.
- Ensure agents write artifacts under the case path, update ops metadata, and keep runtimes within configured Celery soft/hard timeouts.

## Configuration & Environment

- Required (see `.env.example`):
- `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` (must be one of the tenant’s approved speech regions)
  - `LANGUAGE`, `STORAGE_ROOT`, `DATABASE_URL`
  - Batch mode storage: `AZURE_BLOB_*` settings for SAS uploads
- Diagnostics and provenance:
  - Set `DEBUG=1` to enable SDK-level logs into `ops/` for transcription.

## Tools (Editors)

- Manual Edit: common tool to edit text artifacts (Markdown/JSON) as a child job action; saving creates a version proposal requiring Reviewer approval.
- Agent Edit: interactive chat editor (LLM) that modifies the artifact; same approval/versioning semantics as Manual Edit.

## Intake, Questionnaire, and Interview Guidance

- Intake panel includes a “Generate Questionnaire” tool (LLM panel), using per‑org seed questions and forms; result is Markdown, editable via Manual/Agent Edit, and used during interviews.
- Interview page is a per‑case hub with live checklist, notes, and call logging; sessions append minimal audit lines.

## Approvals & Roles

- Reviewer role is part of default seed roles; approvals are configurable per page/tool (required reviewer count, allowed roles) in Org Settings.
  - `BATCH_HASH_REMOTE=1` and `BATCH_HASH_MAX_MB` to record remote SHA-256 and MD5 (if present) when using batch mode.

## File & Naming Conventions

- Per-case directory: `storage/media/tenants/<ORG_ID>/cases/<CASE_ID>/`
  - `audio/<job>__<original>` — upload payloads
  - `transcript/<job>__transcript.txt` — primary transcript
  - `analysis/` — outputs from summarization, timelines, entities/graphs (proposed standard)
  - `ops/` — human logs, per-run JSON meta, and `ops_*.jsonl` audit streams
- Per-run meta naming: `<job_id>__<agent>_log.json` where `<agent>` in `{transcription, summary, timeline, graph, …}`
- Audit streams: `ops/ops_<agent>.jsonl`

## Coding Guidelines

- Language: Python 3.12.
- Style: type-annotated functions; avoid one-letter names; no inline comments unless essential.
- Strong typing:
  - Read and follow `docs/typing-roadmap.md` and `docs/typing_refactor_plan.md` before touching code.
  - Per-module enforcement: `packages/core/logging` must remain mypy/pyright clean (CI enforces `mypy packages/core/logging` and `pyright packages/core/logging`). Do not introduce `Any` or untyped defs there.
  - When editing other modules, remove `Any` usage, add precise types, and reduce pyright warnings in that scope. Never add `# type: ignore` without an accompanying TODO referencing the typing roadmap.
  - Annotate pytest fixtures and helper lambdas per the typing roadmap; prefer `TypedDict`/`Protocol` for structured payloads.
- Stub dependencies: run `uv sync --frozen --group dev --project apps/platform` to ensure Pyright and Django/DRF stubs are installed before editing. Activation isn’t required—invoke tools with `uv run --project apps/platform …` so the right interpreter is picked automatically.
- Dependencies: avoid heavyweight or networked services unless approved; prefer Azure services that align with the organization’s residency policy.
- Error handling: fail fast with clear messages; write structured meta and human logs; never raise without logging. Never introduce provider/model fallback logic—jobs must use the exact configured provider chain and raise actionable errors if initialization fails.
- Refactors spanning many files should rely on helper scripts (add them under `scripts/` when reusable) instead of manual editing. Always run `pyright` to surface import/function issues across the tree before finishing a refactor.
- Version control: keep diffs minimal and focused; avoid unrelated refactors.

## Local Development

- Start stack: `PROJECT_NAME=udocket-dev make stack.up`
  - Django platform (primary UI/API): `http://localhost:8000`
- Sync dependencies locally before running management commands: `uv sync --frozen --group dev --no-install-project --project apps/platform`
- Create a case via the platform UI and upload audio from the case page.
- The Celery worker (`platform_worker` service) picks up jobs automatically and writes outputs under the case directory.
- To exercise the agent manually, open a Django shell and invoke the `TranscriptionAgent`:

  ```python

  from packages.core.agents import TranscriptionAgent, TranscriptionConfig
  cfg = TranscriptionConfig.from_env()
  agent = TranscriptionAgent(cfg)
  agent.transcribe(
      input=f"{STORAGE_ROOT}/media/cases/<CASE>/audio/<job>__file.wav",
      case_id="<CASE>",
      case_dir=Path(STORAGE_ROOT) / "media" / "cases" / "<CASE>",
      job_id="<JOB>",
      language="en-US",
      mode="batch",
      diarization=True,
  )
  ```

## Operational Notes

- Diarization is only supported in batch mode. The platform UI enforces this.
- Region guardrails are enforced by both settings validation and the agent.
- Duration limits are configurable via env (e.g., `MAX_MINUTES`).
- All agents should prefer additive file outputs and append-only audit logs.

## Troubleshooting

- 400 on upload: check `ALLOWED_AUDIO_MIME`.
- Batch fails quickly: ensure Azure Speech tier Standard (S0) and correct region; Free (F0) is not supported by Batch API.
- On-demand no speech: verify input is PCM WAV 16 kHz mono (agent auto-converts via ffmpeg when possible).
- Missing Azure SDKs: ensure `azure-cognitiveservices-speech` and `azure-storage-blob` are installed in the platform runtime.

## Roadmap Alignment (summaries, timelines, relationships)

- Analyze: produce layered analyses (short, detailed) with links to timeline events and seed timeline/entity extraction.
- Timelines: merge diarized offsets and transcript segments into normalized events with speakers and labels.
- Relationships: derive entities and edges with evidence back-pointers to transcript timestamps.
- All of the above should follow the contract here to ensure the Admin UI and API can surface artifacts consistently as features land.
- Platform migration to Django/DRF/Channels and end-to-end authorization/IAM integration: see `docs/ROADMAP.md`.
