# AI Refactor Reports

This folder stores evidence and metadata for Feature `002-ai-refactor-plan`.

- `manifest.jsonl`: Signed implementation manifest covering `specs/001-ai-refactor-plan/` artifacts.
- `manifest_gaps.json`: Gap detector output for missing artifact coverage.
- `automation_env.log`, `baseline_env.log`: Captured environment/session exports for automation tasks.
- `baseline_gates.log`: Results from `make typing.ai`, `make all.test`, `make docs.check.links`, and `make schema.lint`.
- Other artifacts (LangSmith evals, Typewiz reports) land here per the quickstart and doc requirements.
