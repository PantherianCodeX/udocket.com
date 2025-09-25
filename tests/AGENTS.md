# uDocket — Tests Guide

Scope: `tests/` across platform and legacy API.

## Philosophy
- Start specific: unit tests for presenters, selectors, utils. Then integration tests for views and API endpoints. Avoid networked dependencies.

## Patterns
- Django: use `@pytest.mark.django_db` and DRF `APIClient` for API tests; use `Client` for UI views. Seed organizations and set active org in session where required.
- Celery/tasks: call task functions directly; do not rely on Celery runtime within unit tests (see tests/test_platform_flow.py:87).
- FastAPI legacy: keep smoke tests minimal; prefer platform APIs for new work.
- UI fragments: when exercising HTMX views, pass `HX-Request: true` and assert returned partials and `HX-Trigger` headers where applicable.
- Realtime events: validate websocket payloads include required keys per the event schema (type, event, job_id/status). Prefer lightweight channel consumer tests using Channels' test client.

## E2E Transcription Tests
- Location: `tests/e2e/test_transcribe_e2e.py`
- Marker: `e2e_transcribe` (registered in `pytest.ini`). These tests are skipped by default.
- Enable explicitly with: `E2E_TRANSCRIBE=1 pytest -m e2e_transcribe`
- Requirements:
  - `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` set to `canadacentral` or `canadaeast`.
  - `ffmpeg` and `ffprobe` available in PATH.
  - Optional: provide an input speech clip via `E2E_SPEECH_FILE` or `E2E_SPEECH_URL`. If not provided, the tests try `espeak`/`pico2wave`/`say` to synthesize a 1-second clip.
- Scope: exercises the agent’s audio normalization (format conversion) and on‑demand Azure STT end‑to‑end. Designed to be very short to minimize upload/processing time and cost.

## Storage & Isolation
- Use sqlite DBs under a temp storage root where possible; settings already fall back to repo `storage/` path for developer environments.
