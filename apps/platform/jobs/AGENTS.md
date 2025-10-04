# uDocket — Jobs (Models/Telemetry/API) Guide

Scope: `apps/platform/jobs/` (Job model, telemetry shaping, serializers, API views).

## Model Conventions
- Use `Job.Status` enums for all state transitions; add UI mappings when introducing new statuses.
- Derived fields like `transcript_path`, `duration_s`, `upload_progress` must be updated only by orchestrators (operations/tasks).
- `Job.save` auto‑hydrates `organization_id` from the related case when missing (apps/platform/jobs/models.py:74).
- Use `Job.scoped()` to access the typed manager (e.g., tenancy helpers like `for_user`).

## Query Scoping
- Expose `.for_user(user)` on querysets and scope via tenancy helpers in views/serializers.
- Avoid unscoped `.objects` access in APIs; always filter by case/org where applicable.

## Telemetry
- Use `jobs.telemetry` (`JobTelemetry`, `job_telemetry`, `analyze_jobs`) to produce stable payloads for UI and API (apps/platform/jobs/telemetry.py:1).
- When adding new metadata keys written by tasks, extend telemetry accessors rather than inlining file reads elsewhere.
 - Telemetry endpoints (DRF): `GET /api/v1/jobs/<id>/detail/` returns the enriched payload consumed by UI; keep compatibility when evolving keys.
 - Status polling: `GET /api/v1/jobs/<id>/status/` must remain lightweight and stable for frequent polling.

## APIs
- Keep serializers lean; rely on telemetry for computed fields.
- Respect capability checks before exposing artifact paths, hashes, or sensitive fields.
- Websocket payloads: when emitting events, include `job_id`, `status`, and `transcript_file|path` when available; align fields with `JobConsumer._current_job_payload`.

## Titles & Uniqueness
- Use `jobs.utils.unique_title` to generate de‑duplicated titles with numeric suffixes (apps/platform/jobs/utils.py:1).
- For audio conversion sub‑jobs (`job_kind == "audio_conversion"`), generate titles via `_unique_conversion_title` and mark telemetry with `source_job_id` so the UI can nest rows.

## Approval Gating (Artifacts)
- Do not create separate “approved” sidecar artifacts. Instead, only create the durable `CaseArtifact` once a job’s output is approved per policy, and set its checksum at creation (immutable thereafter).
