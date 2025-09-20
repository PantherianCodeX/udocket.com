# uDocket — Agents Guide

This document defines how automation and contributors should add and operate "agents" in the uDocket stack. It covers the current transcription agent and lays down clear conventions for future agents such as summarization, timelines, and relationship/graph extraction.

## Overview
- Services: three FastAPI apps in Docker
  - `apps/api` (public API): creates cases, uploads audio, creates jobs, exposes job status and transcript download.
  - `apps/admin` (admin UI): case management, job diagnostics, download, and Azure remote hash refresh.
  - `apps/worker` (background worker): polls DB jobs and invokes the agent CLI defined by `AGENT_CMD_TEMPLATE`.
- Core agent: `packages/udocket_core/agents/transcribe.py` (Azure Speech, Canada regions only)
  - Modes: `on-demand` (local stream) and `batch` (Azure Batch Transcription via HTTPS SAS URL)
  - Diarization: supported in `batch` mode only
  - Outputs: timestamped transcript `.txt`, per-job JSON metadata, append-only ops audit JSONL
- Storage layout (per-case): `storage/media/cases/<CASE_ID>/`
  - `audio/` original uploads as `<job_id>__<original_name>`
  - `transcript/` transcript files as `<job_id>__transcript.txt`
  - `ops/` logs, metadata, and ops audit files
  - Proposed for analysis agents: `analysis/` (see below)
- Database: SQLite by default (or Postgres) with tables `cases`, `jobs`

## Agent Contract (all agents)
To make agents composable and observable, follow this contract:
- CLI interface:
  - Must accept: `--case <CASE_ID>`, `--case-dir <abs_path_to_case_dir>` or `--outdir <dir>` for primary outputs, and any agent-specific flags.
  - Must read configuration from `.env` where relevant, mirroring `config/settings.py` keys.
- Stdout summary:
  - Print a single JSON object on a single line on success, then exit `0`.
  - Include at minimum: `{"status":"ok","artifact":"<path or key>","duration_s":<optional>}`; add agent-specific fields.
- Exit codes:
  - `0` success; `2` recoverable/content errors (empty audio, timeout, validation); `10+` configuration/dependency errors; `11+` bad inputs or unsupported mode; `13` policy/limits.
- Deterministic outputs:
  - Write artifacts with stable, case-scoped names and versioning (e.g., `_v2` suffix) when re-running the same job.
- Ops logging:
  - Write a human log and a structured JSON metadata file for each run under `ops/` (see examples below).
  - Append an audit line to an ops JSON Lines file for later analytics.
- Security & locality:
  - Canada-only Azure regions (`canadacentral` or `canadaeast`). Do not send PII to non-Canadian services by default.

Reference patterns exist in `packages/udocket_core/agents/transcribe.py`.

## Current Transcription Agent
- Entry: `packages/udocket_core/agents/transcribe.py`
- Inputs: local file path or HTTPS SAS URL (batch mode), language, diarization flag (batch only)
- Outputs:
  - Transcript: `storage/media/cases/<case>/transcript/<job_id>__transcript.txt`
    - Header includes case, source name, hash(es), language, region, duration, timestamp
    - Body contains text with interval timestamps unless diarization already provides timing
  - Job meta (per job): `storage/media/cases/<case>/ops/<job_id>_transcription_log.json`
  - Human log (per job): `storage/media/cases/<case>/ops/<job_id>_transcription.log`
  - Case ops audit: `storage/media/cases/<case>/ops/ops_transcription.jsonl`
- One-line JSON to stdout on success, e.g.: `{ "status":"ok", "transcript_file":"/app/storage/.../transcript/<job>__transcript.txt", "region":"canadacentral", "language":"en-CA", "attempts":1, "duration_s":732.5 }`

## Future Analysis Agents (proposed)
The repository is ready to host additional agents that consume transcripts and emit analysis artifacts. Use the following conventions.

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
  - Stdout (success): `{ "status":"ok", "summary_file":"<abs_path>", "words":1234, "source_transcript":"<abs_path>" }`

- Timeline agent
  - Purpose: create a time-ordered event list, optionally linked to speakers and transcript offsets.
  - Artifacts:
    - Primary: `analysis/<job_id>__timeline_v1.json`
      - Schema (array): `{ "ts_start": number, "ts_end": number|null, "speaker": "SPK_1"|null, "text": string, "labels": [string] }`
    - Optional visualization: `analysis/<job_id>__timeline_v1.html` (self-contained)
    - Ops JSON: `ops/<job_id>__timeline_log.json`
    - Ops audit: `ops/ops_timeline.jsonl`
  - Stdout: `{ "status":"ok", "timeline_file":"<abs_path>", "events": 42 }`

- Entities & relationships agent
  - Purpose: extract people, organizations, locations, docket numbers, and relationships (e.g., said_by, represented_by, alleges, agrees_with).
  - Artifacts:
    - Entities: `analysis/<job_id>__entities_v1.json`
      - Schema: `{ "entities": [{ "id": string, "name": string, "type": "PERSON"|"ORG"|"LOC"|"DOCKET"|"OTHER", "mentions": [{ "ts": number|null, "text": string }] }] }`
    - Graph: `analysis/<job_id>__graph_v1.json`
      - Schema: `{ "nodes": [{ "id": string, "label": string, "type": string }], "edges": [{ "id": string, "source": string, "target": string, "type": string, "evidence": [{ "ts": number|null, "text": string }] }] }`
    - Ops JSON: `ops/<job_id>__graph_log.json`
    - Ops audit: `ops/ops_graph.jsonl`
  - Stdout: `{ "status":"ok", "entities_file":"<abs_path>", "graph_file":"<abs_path>", "entities": N, "edges": M }`

- Cross-artifact conventions
  - Versioning: use `_v2`, `_v3`, etc. when regenerating artifacts without overwriting previous outputs.
  - Hashing: where feasible, compute SHA-256 of outputs and include in ops JSON for provenance.
  - Tracing: include `source_transcript` (abs path), `case_id`, `job_id`, timestamps, tool/library versions, and key settings in ops JSON.

## Worker Integration
- The worker currently constructs the transcription command from `config/settings.py:AGENT_CMD_TEMPLATE` and enriches job rows with transcript metrics.
- To integrate new agents via the worker, follow the same pattern:
  - Add a job type/flow in DB/API (e.g., `analysis_type`), or invoke analysis agents as a post-processing step when transcripts complete.
  - Ensure the agent keeps the stdout one-line JSON contract and writes artifacts under the case path.
  - Keep runtime within `JOB_TIMEOUT_SEC` and ensure idempotency for retry safety.

## Configuration & Environment
- Required (see `.env.example`):
  - `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` (`canadacentral` or `canadaeast`)
  - `LANGUAGE`, `STORAGE_ROOT`, `DATABASE_URL`
  - Worker: `POLL_INTERVAL_SEC`, `JOB_TIMEOUT_SEC`, `MAX_CONCURRENT`
  - Agent command template: `AGENT_CMD_TEMPLATE`
  - Batch mode storage: `AZURE_BLOB_*` settings for SAS uploads
- Diagnostics and provenance:
  - Set `DEBUG=1` to enable SDK-level logs into `ops/` for transcription.
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
- Language: Python 3.11
- Style: type-annotated functions; avoid one-letter names; no inline comments unless essential
- Dependencies: avoid heavyweight or networked services unless approved; prefer Azure services in Canadian regions
- Error handling: fail fast with clear messages; write structured meta and human logs; never raise without logging
- Version control: keep diffs minimal and focused; avoid unrelated refactors

## Local Development
- Start stack: `docker compose up --build`
  - API: `http://localhost:8080`
  - Admin: `http://localhost:8081`
- Create a case (Admin UI → New Case) and upload audio from the case page.
- Worker picks up the job automatically and writes outputs under the case directory.
- Run agent directly (example):
  - On-demand from local file: `python packages/udocket_core/agents/transcribe.py --input "/app/storage/media/cases/<CASE>/audio/<job>__file.wav" --case "<CASE>" --outdir "/app/storage/media/cases/<CASE>/transcript" --language "en-CA" --mode "on-demand"`
  - Batch from HTTPS SAS URL: `python packages/udocket_core/agents/transcribe.py --input "https://.../file.wav?<SAS>" --case "<CASE>" --case-dir "/app/storage/media/cases/<CASE>" --language "en-CA" --mode "batch" --diarization`

## Operational Notes
- Diarization is only supported in batch mode in this project. Admin UI and worker enforce this.
- Region guardrails are enforced by both settings validation and the agent.
- Duration limits are configurable via env (e.g., `MAX_MINUTES`).
- All agents should prefer additive file outputs and append-only audit logs.

## Troubleshooting
- 400 on upload: check `ALLOWED_AUDIO_MIME`.
- Batch fails quickly: ensure Azure Speech tier Standard (S0) and correct region; Free (F0) is not supported by Batch API.
- On-demand no speech: verify input is PCM WAV 16 kHz mono (agent auto-converts via ffmpeg when possible).
- Missing Azure SDKs: install `azure-cognitiveservices-speech` (worker) and `azure-storage-blob` (admin for diagnostics).

## Roadmap Alignment (summaries, timelines, relationships)
- Summarization: produce layered summaries (short, detailed) with links to timeline events.
- Timelines: merge diarized offsets and transcript segments into normalized events with speakers and labels.
- Relationships: derive entities and edges with evidence back-pointers to transcript timestamps.
- All of the above should follow the contract here to ensure the Admin UI and API can surface artifacts consistently as features land.
 - Platform migration to Django/DRF/Channels and end-to-end authorization/IAM integration: see `docs/ROADMAP.md`.
