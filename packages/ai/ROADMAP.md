# packages.ai Migration Notes

- Stage orchestration (outline/timeline/entity/compose) remains in `packages.core`.
- Next migration phase:
  1. Extract chunking + prompt building into `packages.ai.compilers`.
  2. Replace direct `packages.core.llm` usage with `DefaultAIClient`.
  3. Delete legacy provider loaders once automation agents depend on the new API.

This file documents staging only; keep the canonical plan in `docs/overview/tdd/appendices/repository_trees.md`.
