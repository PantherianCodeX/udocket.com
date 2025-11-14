# LangSmith & LangFuse Environment Placeholders

The modernization feature keeps secrets out of git, but we must document the exact `.env` knobs so engineers can hydrate local shells without re-reading the entire TDD.

## Variable Inventory

| Vendor | Variable | Purpose | Notes |
|--------|----------|---------|-------|
| LangSmith | `LANGSMITH_API_KEY` | Workspace API key scoped to env (dev/staging/preprod). | Rotate every 90 days or immediately after offboarding; store rotation timestamp as an inline comment in `.env`. |
| LangSmith | `LANGSMITH_ENDPOINT` | API base URL (`https://api.smith.langchain.com` unless using a residency-specific endpoint). | Keep protocol + hostname only; trailing slashes allowed. |
| LangSmith | `LANGSMITH_PROJECT` | Project slug for eval routing. | Mirrors the per-environment workspace name. |
| LangSmith | `LANGSMITH_TRACING` | `true/false` toggle for structured tracing. | Default `true` for dev/staging, `false` elsewhere unless governance signs off. |
| LangFuse | `LANGFUSE_PUBLIC_KEY` | Frontend key for SDK initialization. | R&D only; disable and purge after each campaign per Observability control. |
| LangFuse | `LANGFUSE_SECRET_KEY` | Server-side API key. | Store only in `.env`; rotate <=30 days because LangFuse TTL requirement in research.md. |
| LangFuse | `LANGFUSE_BASE_URL` | Instance host (e.g., `https://cloud.langfuse.com`). | Required even when using the managed SaaS cluster. |

## Placeholder Snippet (copy into `.env`)
```dotenv
# LangSmith
LANGSMITH_API_KEY="changeme-dev-langsmith"
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_PROJECT="modernization-dev"
LANGSMITH_TRACING=true

# LangFuse (R&D only)
LANGFUSE_PUBLIC_KEY="changeme-langfuse-public"
LANGFUSE_SECRET_KEY="changeme-langfuse-secret"
LANGFUSE_BASE_URL="https://cloud.langfuse.com"
```

## Rotation & Evidence
- Track rotation timestamps directly in `.env` comments until the secrets service lands (per `research.md`). Example: `LANGSMITH_API_KEY=... # rotated 2025-11-14 by user`.
- For LangSmith workspaces, store API keys in password manager, then paste into `.env`; update `specs/001-ai-refactor-plan/reports/langsmith_workspace_records.jsonl` when T024 runs.
- For LangFuse, enforce the 15-minute disablement SLA: once a session is shut off, immediately revoke keys and log the event in `reports/langfuse_enable_disable.md`.

## Usage Notes
1. Duplicate `.env.example` → `.env`, inject the placeholders above, then replace with real values locally.
2. Run `set -a && source .env && set +a` before invoking `uv`, `make`, or the readiness scripts.
3. Never commit `.env` or the filled placeholders; `.gitignore` already blocks `.env*`.
4. If you rename environments, update `LANGSMITH_PROJECT` and LangSmith workspace metadata (`data/tooling/workspaces.yaml`).
