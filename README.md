# uDocket MVP Skeleton (Dockerized) — v0.12

This package includes fixes for Pydantic v2 (uses `pydantic-settings`), explicit `PYTHONPATH=/app`,
and module discovery (`db/__init__.py`, `config/__init__.py`).

## Quick start
1) Copy your **pilot agent** into:
   packages/udocket_core/agents/transcribe.py
2) Copy `.env.example` to `.env` and fill required values.
3) Build & run:
   docker compose up --build
- API   → http://localhost:8080
- Admin → http://localhost:8081

## Notes
- SQLite by default; for Postgres, set `DATABASE_URL` and run Alembic.
- Worker calls your agent using `AGENT_CMD_TEMPLATE` from `.env`.
- Admin/API uploads let you choose `batch` (default) or `on-demand` transcription.
- Batch mode optionally enables speaker diarization via UI toggle or `--diarization` flag.

## Transcription Modes
- Batch: audio is uploaded to Azure Blob Storage; the agent invokes Azure Batch Transcription using an HTTPS SAS URL.
  - Requires Azure Storage credentials in `.env`:
    - `AZURE_BLOB_ACCOUNT` and `AZURE_BLOB_KEY` (or `AZURE_BLOB_CONNECTION_STRING`)
    - `AZURE_BLOB_CONTAINER` (e.g., `udocket-audio`)
    - Optional: `AZURE_BLOB_SAS_TTL_MIN` (default 120)
  - In Admin UI, pick “Batch” and optionally enable “Diarization”.
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
2) Add env vars in `.env` as above; rebuild worker: `docker compose build worker`.
3) Run: `docker compose up -d`. The worker uploads audio and passes a SAS URL to the agent.
4) Create an Azure Speech resource in the same Canada region (canadacentral/canadaeast) with tier Standard (S0) and set `AZURE_SPEECH_KEY`/`AZURE_SPEECH_REGION`.
