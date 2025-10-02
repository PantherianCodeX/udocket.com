# uDocket — Agents Guide

This document defines how automation and contributors should add and operate "agents" in the uDocket stack. It covers the current transcription agent and lays down clear conventions for future agents such as summarization, timelines, and relationship/graph extraction.

Note: This is the root guide. For area‑specific practices (UI, operations, jobs, artifacts, accounts, authorization, core libs, config, infra, tests), also read the AGENTS.md files colocated in those directories. When working in any area, you must follow the closest AGENTS.md in that subtree.

Quick index of AGENTS guides in this repo:
- apps/platform/AGENTS.md
- apps/platform/ui/AGENTS.md
- apps/platform/operations/AGENTS.md
- apps/platform/jobs/AGENTS.md
- apps/platform/cases/AGENTS.md
- apps/platform/artifacts/AGENTS.md
- apps/platform/accounts/AGENTS.md
- apps/platform/authorization/AGENTS.md
- packages/udocket_core/AGENTS.md
- config/AGENTS.md
- infra/AGENTS.md
- tests/AGENTS.md

## Overview
- Services:
  - `apps/platform` (Django + Channels + Celery): primary UI, API surface, and background workers.
- Core agent implementation lives in `packages/udocket_core/agents/transcribe_lib.py` (Azure Speech, Canada regions only).
  - Modes: `on-demand` (local stream) and `batch` (Azure Batch Transcription via HTTPS SAS URL).
  - Diarization: supported in `batch` mode only.
  - Outputs: timestamped transcript `.txt`, per-job JSON metadata, append-only ops audit JSONL.
- Storage layout (per-case): `storage/media/cases/<CASE_ID>/`
  - `audio/` original uploads as `<job_id>__<original_name>`
  - `transcript/` transcript files as `<job_id>__transcript.txt`
  - `ops/` logs, metadata, and ops audit files
  - Proposed for analysis agents: `analysis/` (see below)
- Database: SQLite by default (or Postgres) with tables `cases`, `jobs`

## Agent Contract (all agents)
To make agents composable and observable when executed inside Celery workers, follow this contract:
- Implement the `TranscriptionAgent` interface (see `packages/udocket_core/agents/transcribe_lib.py`).
  - Accepts structured config (`TranscriptionConfig`) instead of CLI flags.
  - Read configuration from `.env` where relevant, mirroring `config/settings.py` keys.
- Return a `TranscriptionResult` object; raise rich exceptions for recoverable errors (the task layer records metadata and updates the UI).
- Deterministic outputs:
  - Write artifacts with stable, case-scoped names and versioning (e.g., `_v2` suffix) when re-running the same job.
- Ops logging:
  - Write a human log and a structured JSON metadata file for each run under `ops/` (see examples below).
  - Append an audit line to an ops JSON Lines file for later analytics.
- Security & locality:
  - Canada-only Azure regions (`canadacentral` or `canadaeast`). Do not send PII to non-Canadian services by default.

Reference patterns exist in `packages/udocket_core/agents/transcribe_lib.py`.

## Current Transcription Agent
- Entry: `packages/udocket_core/agents/transcribe_lib.py`
- Inputs: local file path or HTTPS SAS URL (batch mode), language, diarization flag (batch only)
- Outputs:
  - Transcript: `storage/media/cases/<case>/transcript/<job_id>__transcript.txt`
    - Header includes case, source name, hash(es), language, region, duration, timestamp
    - Body contains text with interval timestamps unless diarization already provides timing
  - Job meta (per job): `storage/media/cases/<case>/ops/<job_id>_transcription_log.json`
  - Human log (per job): `storage/media/cases/<case>/ops/<job_id>_transcription.log`
  - Case ops audit: `storage/media/cases/<case>/ops/ops_transcription.jsonl`
- One-line JSON to stdout on success, e.g.: `{ "status":"ok", "transcript_file":"/app/storage/.../transcript/<job>__transcript.txt", "region":"canadacentral", "language":"en-CA", "attempts":1, "duration_s":732.5 }`

## Analysis Agents
The repository hosts agents that consume transcripts and emit analysis artifacts. Use the following conventions.

- Common input discovery:
  - Default transcript input: the latest `<job_id>__transcript.txt` or the most recent transcript file in `transcript/`.
  - Agents should accept `--input <path>` to override, and `--case`, `--case-dir`, `--outdir` similarly to the transcriber.

- Output directory:
  - Write to `storage/media/cases/<case>/analysis/` and `storage/media/cases/<case>/ops/`.
  - Use per-job or per-run names with the same prefix style when tied to a transcription job: `<job_id>__<artifact>.<ext>`.

- Summarization agent
  - Purpose: produce one or more levels of summary from a transcript.
  - Artifacts:
    - Primary: `analysis/<job_id>__summary_v1.md` (markdown) or `.txt`
    - Optional: `analysis/<job_id>__outline_v1.json` (hierarchical bullets)
    - Ops JSON (per run): `ops/<job_id>__summary_log.json`
    - Ops audit JSONL: `ops/ops_summary.jsonl`
  - Staff report (mandatory): `analysis/<job_id>__staff_report_v1.md` (+ optional JSON companion) with gaps/risks/discrepancies and questionnaire score.
  - Stdout (success): `{ "status":"ok", "summary_file":"<abs_path>", "words":1234, "source_transcript":"<abs_path>" }`

- Compose agent (final assembly)
  - Purpose: generate final, audience-specific deliverables; timeline and relationships are produced within this pipeline (LLM-only).
  - Inputs: `summary_v1.json`, `timeline_v2.json` (or transcript), `entities_v2.json`/`graph_v2.json` (or transcript), intake data, and case artifacts (letters, statements, forms).
  - Outputs:
    - Client deliverable (grade 6, in-client voice): `analysis/<job_id>__compose_client_v1.md` and `.docx`
    - Lawyer deliverable (professional legal): `analysis/<job_id>__compose_lawyer_v1.md` and `.docx`
    - Timeline: `analysis/<job_id>__timeline_v2.json` (+ `...html` and optional `...png`)
    - Graph: `analysis/<job_id>__graph_v2.json` (+ `...html` and optional `...png`)
    - Ops JSON (per run): `ops/<job_id>__compose_log.json`
    - Ops audit JSONL: `ops/ops_compose.jsonl`
  - Notes: per‑org DOCX template selection with uDocket default fallback; no offline fallbacks; fail fast on missing credentials.

- Cross-artifact conventions
  - Versioning: use `_v2`, `_v3`, etc. when regenerating artifacts without overwriting previous outputs.
  - Hashing: where feasible, compute SHA-256 of outputs and include in ops JSON for provenance.
  - Tracing: include `source_transcript` (abs path), `case_id`, `job_id`, timestamps, tool/library versions, and key settings in ops JSON.
  - Approvals/versioning: Manual Edit and Agent Edit produce new versions that require Reviewer approval to promote to the parent task.
  - Object identity: every structured record (events, entities, relationships, outline nodes, etc.) must include a stable `uuid` field. Derive UUIDs deterministically (e.g., UUID5 of canonical content) to avoid collisions across reruns while keeping outputs reproducible.
  - Titles: when creating human-readable artifact titles, always call the shared `unique_title` helper to avoid collisions within a case/organization.

## Worker Integration
- Celery tasks in `apps.platform.operations.tasks` orchestrate uploads, call `TranscriptionAgent.transcribe`, and persist telemetry.
- To integrate new agents, add Celery tasks that wrap your agent implementation and emit job/case websocket updates via `send_job_update`/`send_case_update`.
- Ensure agents write artifacts under the case path, update ops metadata, and keep runtimes within configured Celery soft/hard timeouts.

## Configuration & Environment
- Required (see `.env.example`):
  - `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` (`canadacentral` or `canadaeast`)
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
- Per-case directory: `storage/media/cases/<CASE_ID>/`
  - `audio/<job>__<original>` — upload payloads
  - `transcript/<job>__transcript.txt` — primary transcript
  - `analysis/` — outputs from summarization, timelines, entities/graphs (proposed standard)
  - `ops/` — human logs, per-run JSON meta, and `ops_*.jsonl` audit streams
- Per-run meta naming: `<job_id>__<agent>_log.json` where `<agent>` in `{transcription, summary, timeline, graph, …}`
- Audit streams: `ops/ops_<agent>.jsonl`

## Coding Guidelines
- Language: Python 3.11.
- Style: type-annotated functions; avoid one-letter names; no inline comments unless essential.
- Strong typing:
  - Read and follow `docs/typing-roadmap.md` and `docs/typing_refactor_plan.md` before touching code.
  - Per-module enforcement: `packages/udocket_core/logging` must remain mypy/pyright clean (CI enforces `mypy packages/udocket_core/logging` and `pyright packages/udocket_core/logging`). Do not introduce `Any` or untyped defs there.
  - When editing other modules, remove `Any` usage, add precise types, and reduce pyright warnings in that scope. Never add `# type: ignore` without an accompanying TODO referencing the typing roadmap.
  - Annotate pytest fixtures and helper lambdas per the typing roadmap; prefer `TypedDict`/`Protocol` for structured payloads.
- Stub dependencies: install `apps/platform/requirements.txt` (which bundles the Django and DRF stub packages) so Pyright has Django/DRF annotations locally.
- Dependencies: avoid heavyweight or networked services unless approved; prefer Azure services in Canadian regions.
- Error handling: fail fast with clear messages; write structured meta and human logs; never raise without logging.
- Refactors spanning many files should rely on helper scripts (add them under `scripts/` when reusable) instead of manual editing. Always run `pyright` to surface import/function issues across the tree before finishing a refactor.
- Version control: keep diffs minimal and focused; avoid unrelated refactors.

## Local Development
- Start stack: `docker compose up --build`
  - Django platform (primary UI/API): `http://localhost:8000`
- Create a case via the platform UI and upload audio from the case page.
- The Celery worker (`platform_worker` service) picks up jobs automatically and writes outputs under the case directory.
- To exercise the agent manually, open a Django shell and invoke the `TranscriptionAgent`:
  ```python
  from packages.udocket_core.agents import TranscriptionAgent, TranscriptionConfig
  cfg = TranscriptionConfig.from_env()
  agent = TranscriptionAgent(cfg)
  agent.transcribe(
      input="/app/storage/media/cases/<CASE>/audio/<job>__file.wav",
      case_id="<CASE>",
      case_dir=Path("/app/storage/media/cases/<CASE>"),
      job_id="<JOB>",
      language="en-CA",
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
- Summarization: produce layered summaries (short, detailed) with links to timeline events.
- Timelines: merge diarized offsets and transcript segments into normalized events with speakers and labels.
- Relationships: derive entities and edges with evidence back-pointers to transcript timestamps.
- All of the above should follow the contract here to ensure the Admin UI and API can surface artifacts consistently as features land.
 - Platform migration to Django/DRF/Channels and end-to-end authorization/IAM integration: see `docs/ROADMAP.md`.
