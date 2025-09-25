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

## Storage & Isolation
- Use sqlite DBs under a temp storage root where possible; settings already fall back to repo `storage/` path for developer environments.
