# uDocket MVP Skeleton (Dockerized) — v0.12

This package includes fixes for Pydantic v2 (uses `pydantic-settings`), explicit `PYTHONPATH=/app`,
and module discovery (`db/__init__.py`, `config/__init__.py`).

## Quick start
1) Implement or customise your **pilot agent** inside the importable interface:
   `packages/udocket_core/agents/transcribe_lib.py` (see `TranscriptionAgent`).
2) Copy `.env.example` to `.env` and fill required values.
   - Postgres defaults are provided; start the bundled database with `docker compose up -d postgres`.
   - The container entrypoint runs `python manage.py migrate`, `python manage.py enable_rls`, and `python manage.py bootstrap_defaults` automatically; you can rerun them manually if needed.
3) Build & run the stack:
   docker compose up --build
- Platform (UI + API) → http://localhost:8000

## Notes
- Postgres is now the default application database. Per-organization row-level security is enforced via `python manage.py enable_rls`.
- Local development bootstrap is controlled via `PLATFORM_BOOTSTRAP_ENABLED`. The default `.env.example` seeds an `admin/changeme` superuser, a demo organization, and permission presets; override or disable these variables for production.
- Default bootstrap values also live in `config/bootstrap_defaults.json`. Point `PLATFORM_BOOTSTRAP_CONFIG` at a custom file to tailor per-environment seeds without baking credentials into the image.
- Django admin remains limited to superusers; seeded superusers can also sign in through `/login/` to access the tenant-scoped UI while staff/non-admin accounts rely solely on the UI.
- Application migrations were flattened into new `0001_initial.py` files for the local apps; run `docker compose down --volumes` after pulling to ensure your database is recreated before starting the stack.
- Azure OpenAI providers now enforce Canada-only endpoints (canadacentral/canadaeast). Set the per-provider `allow_non_ca_region` flag only for temporary local testing; production deployments must stay in-region.
- Media storage is tenant-aware: artifacts for organization `ORG123` live under `/media/tenants/ORG123/cases/<CASE_ID>/...`.
- Run tests inside the dev container directly: `pytest`. The devcontainer provides the runtime and services, so no local helper scripts are required.
- Remote dev: open the repository in VS Code using **Dev Containers > Reopen in Container** to attach to the `platform-dev` service defined under `.devcontainer/` (starts alongside Postgres and Redis).
- Permissions: Visit `/permissions/` for a read-only catalog of artifact fields, presets, and roles (edits still happen via Django admin for MVP).
- Platform uploads let you choose `batch` (default) or `on-demand` transcription.
- Batch mode optionally enables speaker diarization via UI toggle or `--diarization` flag.
- JSON Schemas: run `make lint-schemas` (requires `jsonschema`) to validate shared schemas under `spec/schemas`. When ready for CI wiring, add this target to the lint pipeline after Spectral runs so schema drift fails early.

## Authentication & dashboard flow
- Sign in at `/login/` to use the themed welcome screen. Local username/password login remains available in development, while production instances surface a Single Sign-On button when OIDC is configured.
- After authenticating, members with access to multiple organizations land on the organization chooser. Pick a workspace to continue; single-organization members are auto-forwarded to the dashboard.
- The dashboard is now widget-driven. Metrics, case tables, job summaries, and upcoming deadlines are rendered as modular widgets that can be customized per organization as template overrides are introduced (see `docs/dashboard_widgets.md`).

## Transcription Modes
- Batch: audio is uploaded to Azure Blob Storage; the agent invokes Azure Batch Transcription using an HTTPS SAS URL.
  - Requires Azure Storage credentials in `.env`:
    - `AZURE_BLOB_ACCOUNT` and `AZURE_BLOB_KEY` (or `AZURE_BLOB_CONNECTION_STRING`)
    - `AZURE_BLOB_CONTAINER` (e.g., `udocket-audio`)
    - Optional: `AZURE_BLOB_SAS_TTL_MIN` (default 120)
  - In the platform UI, pick “Batch” and optionally enable “Diarization”.
  - Requires Azure Speech resource tier Standard (S0). Free (F0) keys are rejected by the Batch API.
  - Diarization is supported only in Batch mode in this project. Output includes per-utterance timestamps and `SPK_n` labels.
  - Duration in the transcript header is computed from the Batch result (offset + duration), so it’s accurate for remote files.
  - Optional hashing of remote audio for provenance:
    - `BATCH_HASH_REMOTE=1` to stream and compute SHA256 of the source URL prior to transcription
    - `BATCH_HASH_MAX_MB=200` caps hashing to URLs ≤ this many MB (default 200)
    - If available, Blob `Content-MD5` is also captured.
- On-demand: the agent streams local audio via the Speech SDK recognizer (fast, no Blob required).

## Azure Setup (batch mode)
1) Create a Storage account and a private container (e.g., `udocket-audio`).
2) Add env vars in `.env` as above; rebuild the Django platform worker: `docker compose build platform_worker`.
3) Run: `docker compose up -d`. The Celery worker in `apps.platform` uploads audio and passes a SAS URL to the agent.
4) Create an Azure Speech resource in the same Canada region (canadacentral/canadaeast) with tier Standard (S0) and set `AZURE_SPEECH_KEY`/`AZURE_SPEECH_REGION`.

## Roadmap
- Platform migration and consolidation plan: see `docs/ROADMAP.md`.

## Devcontainer notes (persisting chat sessions)
- Rebuilding the VS Code devcontainer used to wipe CLI/chat history stored under the container HOME.
- The devcontainer compose now mounts persistent volumes for `/root/.config`, `/root/.cache`, and `/root/.local/share` so tools like Codex CLI and editors retain session data across rebuilds.
- To apply: Reopen in Container (Rebuild) from VS Code. Existing named volumes are reused automatically; nothing else is required.
