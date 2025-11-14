# Quickstart – AI Module Migration Completion Plan

## 1. Prerequisites
- Python 3.12 toolchain with `uv` + `make` targets configured (see repository README).
- Access to managed Postgres + object storage buckets already provisioned for readiness/ops JSONL data.
- Approved LangSmith + LangFuse vendor accounts with signed DPAs; API keys must be added to `.env` (no central secrets service yet).
- Membership in the AI Modernization group (grants CI + staging cluster access).

## 2. Environment Setup
1. `cp .env.example .env` (first-time only) and populate LangSmith/LangFuse env vars per the Archon knowledge-base docs. The template now sets `UV_PROJECT_ENVIRONMENT=.venv` + `UV_CACHE_DIR=.cache/uv` so any `uv … --project apps/platform` invocation automatically hydrates the shared root virtualenv.
   - `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY=<key>`, `LANGSMITH_PROJECT=<env-name>`, `LANGSMITH_ENDPOINT=https://api.smith.langchain.com` (or custom endpoint).
   - `LANGFUSE_PUBLIC_KEY=<key>`, `LANGFUSE_SECRET_KEY=<key>`, `LANGFUSE_BASE_URL=<host>`.
2. `uv sync` – ensure LangGraph, LangSmith, and LangFuse dependencies are installed via lockfile.
3. `set -a && source .env && set +a` – load env vars into the local shell (repeat when `.env` changes).
4. `make typing.ai && make all.test` – validate baseline typing/tests before changes.

## 3. LangSmith Workspace Provisioning
1. Run `python automation/pipelines/langsmith/provision_workspace.py --env staging` to create workspace + roles.
2. Append new API keys to `.env` using the `LANGSMITH_*` variables above; document rotation timestamps inline (comment) until the secrets service exists.
3. Add workspace metadata into `packages/automation/agents/tooling_workspaces.py` using the ToolingWorkspace schema.
4. Trigger a smoke evaluation via `python automation/pipelines/langsmith/run_eval.py --lane dialup-rd --prompt-bundle readiness-baseline.toml`.
5. Check `tests/langgraph/test_eval_exports.py` to ensure EvaluationEvidence entries validate and land in Postgres.

## 4. Temporary LangFuse Enablement
1. Execute `python automation/observability/langfuse_enable.py --env dev --sampling 0.2 --ttl-days 30`.
2. Verify OTLP exporters forward spans by tailing `logs/otlp-dev.log` and checking LangFuse UI.
3. Document enablement evidence in `ops/runbooks/langfuse-rd.md` (screenshots + timestamps).
4. Test kill switch: `python automation/observability/langfuse_disable.py --env dev` must revoke credentials within 15 minutes; archive exported data to object storage per runbook.

## 5. Readiness Inventory + Reporting
1. Populate MigrationStageReadiness records via `python services/readiness/snapshot.py --lane modernization`.
2. Publish ops JSONL + dashboards using `make ops.publish-readiness`.
3. Export LangSmith evaluations for governance using `python automation/pipelines/langsmith/export_results.py --format json`
4. Confirm dashboards update (`apps/ops_console`) and that audit hashes are appended in `storage/audit/ai-module/*.jsonl`.

## 6. Validation Checklist
- ✅ LangSmith smoke eval completed and results ingested.
- ✅ LangFuse R&D spans visible and kill switch validated.
- ✅ Readiness inventory + migration backlog refreshed with new tooling dependencies captured.
- ✅ Budget alerts configured in `packages/common/telemetry/vendor_usage.py` with thresholds.

Once complete, proceed to `/speckit.tasks` to break down execution work.
