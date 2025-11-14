# Research – AI Module Migration Completion Plan

## Decision 1: Canonical storage for readiness + evaluation evidence
- **Decision**: Keep the authoritative readiness inventory and evaluation evidence in Postgres (`services/readiness`) while emitting append-only ops JSONL snapshots for downstream automation.
- **Rationale**: Postgres already stores migration manifests with audit trails; pairing it with ops JSONL maintains replayability and satisfies governance without duplicating write paths.
- **Alternatives considered**:
  - Store everything in ops JSONL only — rejected because stakeholders need relational queries and dashboards already wired to Postgres.
  - Introduce a new vector or analytics store — rejected due to unnecessary compliance lift and schedule risk.

## Decision 2: LangSmith workspace governance & key handling
- **Decision**: Provision one LangSmith workspace per environment (dev, staging, pre-prod) and record the API key, endpoint, tracing toggle, and project slug in the checked-in `.env` (variables `LANGSMITH_API_KEY`, `LANGSMITH_ENDPOINT`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`) per the Archon LangSmith observability docs; evaluations still route through `packages.ai.api` so runtime guardrails stay enforced.
- **Rationale**: Environment-scoped workspaces keep residency attestations clean while `.env` storage gives engineers immediate access now that the dev container + central secrets service are gone; the LangSmith documentation explicitly supports env-var based setup so we stay within supported patterns.
- **Alternatives considered**:
  - Waiting for the future secrets service described in the TDD — rejected because local work would remain blocked; documenting `.env` handling lets us migrate later without code churn.
  - Per-user workspaces — rejected due to operational overhead and fragmented reporting.

## Decision 3: LangSmith evaluation export format
- **Decision**: Export LangSmith experiment results (scores, latency, cost, dataset hash, prompt bundle id) into the readiness repository using the EvaluationEvidence schema defined in this plan and validate via JSON Schema before ingestion.
- **Rationale**: Structured exports keep dashboards, audits, and ops JSONL aligned; schema validation enforces type-first guarantees.
- **Alternatives considered**:
  - Manual PDF/CSV uploads — rejected because they are not auditable and break automation.
  - Direct LangSmith dashboard embedding — rejected due to governance and residency concerns.

## Decision 4: Temporary LangFuse integration scope
- **Decision**: Enable LangFuse only in R&D environments with a 15-minute disablement SLA, sampling capped at 25%, masked prompts, `.env`-backed credentials (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`) as called out in the Archon LangFuse SDK setup guide, and a scripted teardown (credential purge + data export) triggered at R&D completion.
- **Rationale**: Meets observability needs without breaching the "temporary" constraint; relying on `.env` mirrors the LangFuse SDK guidance while we work toward centralized secrets, and the rapid kill switch satisfies compliance and cost controls.
- **Alternatives considered**:
  - Permanent LangFuse deployment — rejected per directive and long-term residency cost.
  - No LangFuse usage — rejected because we need deeper traces during early dial-up.

## Decision 5: Vendor cost and performance envelopes
- **Decision**: Budget LangSmith + LangFuse combined spend at ≤10% over forecast with automated alerts when 80% and 100% thresholds are crossed; enforce LangSmith eval turnaround <30 minutes p95 and LangFuse overhead <5% runtime.
- **Rationale**: Aligns with success metrics in the spec and keeps vendor usage sustainable.
- **Alternatives considered**:
  - Unlimited burst usage — rejected due to financial and capacity risks.
  - Stricter budgets (<5%) — rejected because early R&D requires flexibility for experimentation.

## Decision 6: Local workflow sans dev container
- **Decision**: Standardize on host-based workflows: developers copy `.env.example` → `.env`, inject LangSmith/LangFuse keys, run `uv sync` from repo root, and execute `make typing.ai`, `make all.test`, and targeted `pytest` modules locally instead of `make shell.ai`.
- **Rationale**: The dev container is retired, so we must document canonical commands for local shells; uv keeps dependencies deterministic and mirrors CI, while `.env` storage avoids blocking on the future secrets service.
- **Alternatives considered**:
  - Reintroducing the dev container — rejected to keep focus on local reproducibility and avoid Docker-in-Docker overhead.
  - Freeform per-engineer setup — rejected because it fragments tooling versions and undermines reproducibility.
