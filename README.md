# uDocket MVP Skeleton (Dockerized) — v0.3

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