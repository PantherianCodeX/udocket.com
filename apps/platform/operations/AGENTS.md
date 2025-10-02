# uDocket — Operations (Celery/Storage/Channels) Guide

Scope: `apps/platform/operations/` (tasks, storage paths, websocket updates, ops logging).

## Responsibilities
- Orchestrate background work (Celery), write reproducible metadata and logs, and notify the UI.
- Shape task inputs/outputs to be explicit and deterministic; avoid implicit DB coupling where possible.

## Tasks
- Use `@shared_task(bind=True)` and explicit keyword-only args. See `transcribe_job` (apps/platform/operations/tasks.py:80).
- Status transitions: set `Job.status`, `started_at`, `finished_at`, and `upload_progress` predictably.
- Emit websocket updates via `send_job_update`/`send_case_update` at notable milestones.
- Write ops meta via `update_job_meta` and human logs via `append_job_log` (apps/platform/operations/utils.py:1). Ensure append-only behavior.
- Handle cancellation, retries, and terminal states consistently; prefer `Job.Status` enums.
 - For analysis tasks, follow standard filenames and audit streams:
   - Analyze: `analysis/<job_id>__summary_v1.md`, ops `<job_id>__summary_log.json`, audit `ops_summary.jsonl`
   - Timeline: `analysis/<job_id>__timeline_v1.json`, ops `<job_id>__timeline_log.json`, audit `ops_timeline.jsonl`
   - Graph: `analysis/<job_id>__entities_v1.json`, `analysis/<job_id>__graph_v1.json`, ops `<job_id>__graph_log.json`, audit `ops_graph.jsonl`

## Storage
- Use `tenant_case_root` and `ensure_case_dirs` for per‑case directories (apps/platform/operations/storage.py:12).
- Required subdirs: `audio/`, `transcript/`, `analysis/`, `ops/`. Avoid writing outside the case root.
- Name ops files deterministically (`{job_id}_transcription_log.json`, `{job_id}_transcription.log`).

## Azure & Batch
- For batch uploads, use `upload_with_sas` helpers and record remote hashes when configured.
- Keep all Azure regions in Canada only. Never leak PII to non‑Canadian endpoints.

## Provenance
- Update ops JSON with: `case_id`, `job_id`, `source_audio`, `language`, `region`, `attempts`, hashes, and timestamps.
- Append JSONL audit entries for high‑level events (enqueue, start, succeed/fail).
 - Consider computing output SHA‑256 and include in ops meta for reproducibility.

## Error Handling
- Fail fast with clear logs; include actionable metadata in ops JSON (e.g., `error_code`, `error_message`).
- Avoid raising without logging; rely on `JobRuntimeContext` to update status and provenance metadata.

## Typing Expectations
- This package runs under `disallow_untyped_defs` in `mypy.ini`; every new function must be fully annotated.
- Follow `docs/typing-roadmap.md`: replace loose `dict[str, Any]` payloads with `TypedDict`/dataclasses and avoid new `# type: ignore` comments.
- When patching tests that exercise operations, ensure fixtures are annotated (see `tests/AGENTS.md`).

## Patterns
- If batch mode requires local WAV, normalize via core `normalize_audio` and persist the conversion reasons to ops JSON.
- Prefer `_unique_*` helpers to create reproducible titles/labels (see `_unique_conversion_title`).
- Emit `send_case_update(case_id, event="artifact.created", kind=<type>, job_id=job_id)` after writing artifacts so UI modules update in real time.

## Websocket Event Schema (v1)
- Jobs channel message (group `jobs_<job_id>`):
  - Required: `type: "job.update"`, `event` (one of: `snapshot`, `started`, `uploading`, `converting`, `running`, `succeeded`, `failed`, `cancelled`, `corrupted`, `review`), `job_id` (str), `status` (Job.Status).
  - Optional: `progress_percent` (0–100 float), `upload_progress`, `transcript_file|transcript_path`, `case_id`, `review_status`, `reviewed_by`, `reviewed_at`, `error_message`.
- Cases channel message (group `cases_<case_id>`):
  - Required: `type: "case.update"`, `event` (e.g., `artifact.created`, `jobs.changed`).
  - Optional: `kind` (e.g., `summary|timeline|graph|transcript`), `job_id`, `artifact_id`.
- Versioning: keep fields backward‑compatible; when adding a new required field or changing semantics, bump `event_version` and update client handlers.
