# uDocket — Legacy API (FastAPI) Guide

Scope: `apps/api/` (compatibility endpoints while migrating to Django Platform UI/API).

## Purpose & Boundaries
- Provide minimal endpoints for uploads and case management to keep older clients working.
- New features should target the Django platform first; add here only when needed for compatibility.

## Patterns
- Use pydantic models for request validation; ensure fields are trimmed/normalized (apps/api/app/routers/cases.py:18).
- Enforce allowed audio MIME types via settings and validate diarization rules (apps/api/app/routers/transcriptions.py:1).
- Use `packages.udocket_core.storage.paths` for computing paths; keep storage under `STORAGE_ROOT`.

## Storage & IDs
- Generate `job_id` server‑side and name files deterministically (`<job>__<original>` for audio; `<job>__transcript.txt` for transcripts).

## Migration Notes
- Prefer proxying to platform tasks for any asynchronous or Azure‑dependent work to avoid duplication.
- Keep health endpoints stable for smoke checks.

