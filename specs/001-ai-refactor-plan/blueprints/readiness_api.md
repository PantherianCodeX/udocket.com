# Readiness API Blueprint

## Scope
- Implements `/readiness/components`, `/readiness/components/{componentId}/gaps`, and `/migrations/backlog` endpoints defined in `contracts/openapi.yaml`.
- Backed by `packages/devops/readiness` service for data refresh + ops hashing.
- Exposed via Django REST Framework viewsets routed under `ops.udocket.internal/api/v1`.

## Architecture
1. **Serializer layer**
   - `MigrationStageReadinessSerializer` → maps dataclasses to API schema (fields mirror `drafts/readiness_types.py`).
   - `CapabilityGapSerializer` → reuses validation from typed primitives; enforces UUIDv7 format via `UUIDField`.
   - `MigrationTaskSerializer` → emits backlog entries once `scripts/migration_plan_generator.py` produces JSON.
2. **Views**
   - `ReadinessComponentViewSet` (`list`) → supports `status` + `owner_team` query params, default pagination off.
   - `CapabilityGapView` (`post`) → upserts gap for a component; writes to feature-scoped storage during planning, later to Postgres.
   - `MigrationBacklogView` (`get`) → serves `data/backlog/migration_backlog.json`.
3. **Service integration**
   - Views call `ReadinessService.refresh(dry_run=True)` before responding to guarantee data freshness and attach `X-Readiness-Hash` header.

## Contracts & Validation
- Query params strictly typed; invalid enum returns 422 JSON error with `detail`.
- POST gap payload cross-validates `componentId` path parameter.
- Responses include `Artifact-Hash` header derived from readiness datasets to aid audit linking.
- Error structures align with DRF default (`{"detail": ...}`) to avoid client drift.

## Observability
- Each API call logs structured events to ops JSONL (`reports/readiness_ops.jsonl`) by reusing the service output.
- Metrics: request count, latency, filtered/unfiltered counts, gap creation success rate.
- Hooks for LangFuse/OTLP instrumentation added once US3 completes.

## TODO for Implementation
- Scaffold Django app module `apps/readiness/api.py` with serializers/views outlined here.
- Wire routes into `config/urls.py` under `/api/v1` namespace.
- Add Spectral contract tests referencing `testplans/api_readiness_tests.md`.
