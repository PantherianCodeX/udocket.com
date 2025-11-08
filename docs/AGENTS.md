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
  stubs; missing third-party stubs are added alongside the change.
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
  `make typing.run` executes the repo-wide typewiz gates plus the AI runtime’s
  dedicated mypy/pyright/Ruff configurations; run it (along with tests/docs)
  before merging. Docs/spec changes must pass `doc_tools.check.links` and
  MkDocs builds.
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
- **Change management.** Specs (TDD + LangGraph) and Guardian/Settings impacts
  must be updated and cited in every PR description; ops/audit logging stays
  additive and deterministic.

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
