# ADR-0005 — uDocket packaging strategy

- **Status:** accepted
- **Date:** 2025-11-03
- **Deciders:** Architecture Team
- **Tags:** packaging, architecture

## Context

uDocket began with a single `packages/core` module that bundled agents, guardrails, runtime
helpers, and assorted utilities. As the platform expanded (platform services, docs tooling,
LangGraph pipelines), teams repeatedly re-implemented helpers—deterministic UUID builders, JSON
coercers, hashing utilities—inside feature directories. This duplication complicates typing, raises
maintenance costs, and blocks future modular publishing (e.g., shipping `packages.common` or
`packages.core` independently).

We need principled boundaries between framework-agnostic helpers, domain-specific agent code, and the
platform adapters that orchestrate them.

## Decision

1. **Consolidate helpers in `packages.common`.** Promote reusable pieces (deterministic UUIDs,
   JSON payload builders, time utilities) into a shared module with dedicated tests and strict typing.
2. **Keep feature code focussed.** Agent modules (`packages.core.agents.*`) consume the shared
   helpers instead of redefining bespoke variants. Platform orchestration layers and docs tooling import
   from `packages.common` to stay DRY.
3. **Document the boundaries.** This ADR records the packaging strategy so future refactors (LangGraph
   rewrites, modular releases) follow the same pattern.

## Consequences

### Positive

- Reduced duplication and tighter typing coverage—one helper, one test surface.
- Shared utilities become discoverable across teams, simplifying onboarding and review.
- Establishes groundwork for publishing or vendoring `packages.common` / `packages.core` independently.

### Negative / Follow-ups

- Requires reviewer vigilance: contributors must continue promoting helpers rather than reinventing them locally.
- Some legacy modules still contain bespoke logic; migrate them opportunistically.
- Audit other helper categories (typing utilities, provenance metadata) and promote them into
  `packages.common` as the pipelines evolve.
