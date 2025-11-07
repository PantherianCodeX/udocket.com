# Core Packaging Strategy (informative)

**Purpose:** capture the current stance on packaging `packages.core`, how it interacts with the monorepo, and outline a safe path to publish subsets without slowing rapid development.

## Current state

- `packages.core` and `packages.common` ship as monorepo modules. They are imported directly by the Django platform, Celery workers, and docs tooling.
- Shared helpers (`packages.common.*`) are the consolidation point for deterministic IDs, JSON utilities, time helpers, and title generation. New cross-cutting utilities should land here before appearing in app-specific code.
- Distribution happens through the repository itself (container builds, uv projects). No packages are currently published to PyPI or an internal index.

## Centralise or publish?

| Option | Pros | Cons |
| --- | --- | --- |
| Keep monorepo modules only | Single source of truth; instant refactors across services; minimal release overhead. | Consumers must use the repo or built images; harder for external tooling to reuse libraries. |
| Publish `packages.core` / `packages.common` packages | Enables reuse in satellite services; allows independent semantic versioning. | Requires release automation, compatibility policy, and dependency syncing across repos; increases coordination overhead. |

**Recommendation:** stay monorepo-first until we have a real consumer outside this repository. When that happens, publish `packages.common` first (small surface area, pure utilities), then evaluate whether `packages.core` needs the same treatment or if a lighter “client” package suffices.

## Publishing playbook (when needed)

1. Introduce explicit version fields in `pyproject.toml` for the packages we plan to publish.
2. Add a release workflow (GitHub Actions) that builds wheels and publishes to the chosen index (internal or PyPI) after tagging.
3. Create compatibility tests that exercise the published artefact against the platform to detect accidental API breaks.
4. Document dependency upgrade steps for downstream services, including how to handle breaking changes.

## Preserving rapid development

To keep iteration speed high while the packages live in the monorepo:

- **Import boundaries:** app code should import from `packages.core.*` and `packages.common.*` only. Avoid reaching into Django-specific modules from common code.
- **CI lanes:** keep the existing uv project separation (platform vs. docs vs. packages). If publishing begins, add a job that installs the wheel into a clean environment and runs smoke tests.
- **Docs/tooling split:** the docs toolbox already treats `packages/docs_tooling` as a standalone uv project. Maintain that boundary so the docs pipeline can be containerised or published independently if needed.

## Future separation path

When it becomes necessary to split core/UI/docs into distinct repositories or deployable units:

1. Freeze shared helpers in `packages.common` and publish them.
2. Extract `packages.core` into its own repo or package while keeping its API backward compatible; the platform imports move to the published distribution.
3. Move docs tooling (`packages.docs_tooling`) into a dedicated repository only after step 2, updating CI to consume the published packages.
4. Retain integration tests in this monorepo (or a dedicated end-to-end repo) that pull the published artefacts to ensure the full stack remains healthy.

This staged approach ensures each move has guardrails and that local development remains straightforward (`uv sync` + `make stack.up`) throughout the transition.
