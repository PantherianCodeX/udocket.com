# uDocket — Agents Engineering Guide

This guide defines the engineering standards and review expectations that apply to
every automation agent. Architecture, lane definitions, artifact inventories, and
QA contracts now live in the authoritative references:

- Platform TDD (`docs/overview/tdd.md`) for system-wide context and ownership.
- LangGraph Agent Orchestration Specification (`docs/automation/langgraph-agents.md`)
  for pipeline structure, stage contracts, and artifact/output details.

When the specs change, update them first. This file never re-states component
behaviour; it only enforces cross-cutting engineering discipline.

## Engineering standards (binding)

- **Type-first development.** Introduce the strongly typed primitives a file
  needs (dataclasses, `TypedDict`, `Protocol`, `StrEnum`, wrappers) before
  implementing logic. Provider payloads are modeled with precise types or local
  stubs; missing third-party stubs are added alongside the change. Enums mandatory, ad-hoc strings and basic data types with constrained elements **must** be Enum/StrEnum where possible and practical.
- **Zero tolerance for `Any`.** New code must not add `typing.Any`. When touching
  legacy code, remove `Any` annotations as part of the change. Casts belong in
  helpers with brief invariant comments. Never add `# type: ignore`; fix the root
  cause instead.
- **Strict Python 3.12+.** Use modern syntax (`match/case`, `StrEnum`,
  `dataclasses`, `contextlib.asynccontextmanager`, `zoneinfo`). Delete
  compatibility branches for older versions.
- **Separation of concerns.** Entry points orchestrate flows; helpers supply
  models/pure functions. Do not mix HTTP/Django concerns with LangGraph execution
  or disk I/O inside the same function. Extract shared helpers to
  `packages/common`; package-scoped helpers stay in local `utils.py`.
- **Quality over speed.** Keep functions small, document invariants, and refactor
  when design demands it.
- **Testing discipline.** Maintain ≥90 % line coverage for touched modules.
  Supply property tests for deterministic behaviours (UUIDs, manifests,
  approvals). Integration tests cover Celery tasks, Guardian/Signer interactions,
  and Settings activation. No change merges without green tests.
- **Tooling requirements.** Run commands via the provided containers/venvs
  (`make …`, `uv run --project …`). Never install ad-hoc dependencies via `pip`.
  Use the package-specific typing targets (`make typing.ai` today, wired into
  `make typing.run`) so the correct mypy/pyright/Ruff configs run inside the
  curated environments before merging. All documentation tooling (`make docs.*`)
  must run through the docs container invoked by those targets—running doc_tools
  locally is unsupported and will drift dependencies. Docs/spec changes must pass
  `doc_tools.check.links` and MkDocs builds.

### Codex CLI home configuration

- Pin the Codex CLI to a deterministic home per repo by running
  `./scripts/codexhome.sh .` (or provide any absolute/relative path). The script
  resolves the target directory, persists it to `.codex/.codexhome`, and keeps the
  shared prompts/config committed while ignoring user artifacts (auth tokens,
  session logs, etc.).
- To apply the setting inside the current shell without re-opening your terminal,
  run `eval "$(./scripts/codexhome.sh --print-export .)"`.
- VS Code terminals automatically read `.codex/.codexhome` on startup (see
  `.vscode/settings.json`). If you change the location, rerun the script so the
  stored path stays in sync.
- Only the project-level slash commands, prompts, and config files live in git.
  Personal Codex state is ignored by default—never commit auth credentials or
  session output.
- **Helper placement & wrappers.** Cross-cutting helpers (JSON, hashing, parsing)
  live in `packages/common`. Agent-specific helpers stay with the agent. Use thin
  wrappers (value objects) instead of raw literals between layers.
- **AI runtime layering.** Automation agents call `packages.ai.api` (or an
  injected `AIClient`) exclusively for AI operations. Provider adapters, routing,
  and residency/egress guards live under `packages/ai/`; automation code MUST NOT
  import provider SDKs directly.
- **No back-compat shims.** Remove deprecated APIs outright. Do not introduce
  toggles to preserve old behaviour.
- **Flow of control.** Entry-point modules validate inputs, snapshot settings,
  and delegate to type-safe helpers. They never mutate global state or implement
  bespoke retry loops outside the shared retry utilities.

## Coordination & specs

- The TDD describes how automation fits into the wider platform. Use it for
  ownership, context, and integration guidance—never for stage-by-stage detail.
- Pipeline behaviour, lanes, artifacts, and QA rules are *only* documented in
  `docs/automation/langgraph-agents.md`. Update that spec before shipping code.
- When docs disagree, LangGraph spec wins, then the TDD, then this file.

## Execution expectations (summary)

- Deterministic scaffolding wraps inherently non-deterministic LLM output:
  filenames, manifest versions, UUID derivations, and ops/audit streams must
  match the spec. Never rely on provider determinism.
- Every job writes structured ops metadata plus an append-only audit JSONL entry.
  Human-readable logs remain optional but recommended.
- Storage layout, artifact naming, approvals, and promotion workflows must match
  the LangGraph spec; do not invent alternates in code or docs.
- Residency, egress, and waiver enforcement flows through the AI runtime
  (`packages.ai.*`) and Settings snapshots. Automation code may not bypass those
  guards.

## Testing & observability

- Property tests cover deterministic surfaces (UUIDs, manifests, approvals).
- Integration tests exercise Celery tasks, Guardian verdicts, and Settings
  activation snapshots.
- Observability hooks (`agent_*` metrics, ops JSONL, audit seals) must align with
  the LangGraph spec; when adding instrumentation, update both the spec and the
  relevant runbooks under `ops/`.

## References

- `docs/overview/tdd.md` — platform overview, ownership, and governance.
- `docs/automation/langgraph-agents.md` — binding LangGraph pipeline spec.
- `docs/platform/settings.md` — configuration governance and activation model.

## Recent Changes
- 002-ai-refactor-plan: Added Python 3.12 (monorepo standard for automation agents/services). + LangGraph runtime, `packages.ai.api` + injected `AIClient`, LangSmith SDK, LangFuse client (R&D-only), structlog, OpenTelemetry, pytest/Hypothesis, uv tooling, Typewiz, Ruff/Pyright, repo-standard make targets.

- 001-ai-refactor-plan: Added Python 3.12 for agents/services, TypeScript (React) for readiness dashboards. + LangGraph runtime, LangSmith SDK (`langsmith`), LangFuse client, structlog, OpenTelemetry, Postgres drivers (`asyncpg`/`psycopg`), uv-managed tooling, pytest/Hypothesis, Typewiz, Ruff, Pyright.
- 001-ai-refactor-plan: Added Python 3.12 (monorepo standard) + LangGraph orchestration, `packages.ai.api` runtime, LangSmith SDK for evaluations, LangFuse collector (R&D only), structlog + OpenTelemetry, ops JSONL pipeline

## Active Technologies
- Python 3.12 (monorepo standard for automation agents/services). + LangGraph runtime, `packages.ai.api` + injected `AIClient`, LangSmith SDK, LangFuse client (R&D-only), structlog, OpenTelemetry, pytest/Hypothesis, uv tooling, Typewiz, Ruff/Pyright, repo-standard make targets. (002-ai-refactor-plan)
- Append-only ops JSONL + audit JSONL under `storage/ops|audit/ai-refactor/`; readiness datasets under `specs/001-ai-refactor-plan/data/`; schemas in `schemas/automation/`; Postgres used only by the established readiness dashboards (no new stores added). (002-ai-refactor-plan)

