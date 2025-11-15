# `packages/common/` Purity Migration Plan

## Objective
Keep `packages/common/` framework-free helpers only; move Django/HTTP/etc. into `packages/core/` or app-specific modules.

## Actions
1. Inventory modules using framework imports (`rg -n "django" packages/common`).
2. For each, plan relocation target (e.g., `packages/core/django/`, `packages/devops/…`).
3. Introduce new helper namespaces: `packages/common/paths/`, `packages/common/json/`, `packages/common/prompts/`.
4. Provide temporary shims with `DeprecationWarning` pointing to new modules.
5. Update AGENTS.md + docs referencing new purity rule.

## Evidence
- Document relocated modules list in this file.
- Track progress via `reports/governance_storyboard.md`.
