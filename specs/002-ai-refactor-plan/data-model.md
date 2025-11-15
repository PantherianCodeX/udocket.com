# Data Model — AI Refactor Implementation Delivery

## 1. ImplementationBlueprintRecord
- **Purpose**: Maps each `specs/001-ai-refactor-plan` artifact to concrete repository work.
- **Fields**:
  - `artifact_path` (StrEnum) — canonical relative path under `specs/001-ai-refactor-plan/`.
  - `artifact_sha256` (hex string) — content hash for immutability.
  - `target_repo_path` (path string) — destination code/doc file or directory.
  - `owner` (StrEnum) — accountable engineering group or DRI.
  - `status` (Enum: `pending`, `in_progress`, `complete`, `blocked`).
  - `evidence_refs` (List[UUID]) — ops/audit/log entries proving completion.
  - `dependencies` (List[ArtifactID]) — other records that must finish first.
  - `critical_path` (bool) — true when delay affects LangGraph dial-up.
- **Relationships**:
  - One-to-many with `ResidencyObservabilityLedger` entries that prove completion.
  - One-to-one with LangGraph lane packages when artifact describes a pipeline stage.
- **Validation Rules**:
  - `artifact_sha256` must match the current artifact before status can become `complete`.
  - `dependencies` cannot include cycles; validated before manifest signing.

## 2. LangGraphLanePackage
- **Purpose**: Represents the typed configuration for each lane/stage in `automation/pipelines/`.
- **Fields**:
  - `lane_id` (StrEnum) — e.g., `ANALYZE_MAIN`, `COMPOSE_CLIENT`.
  - `stage_keys` (List[StageKey]) — ordered StageKey sequence per LangGraph spec §2.5.
  - `qa_contracts` (List[ContractID]) — references QA/observability requirements.
  - `cost_ceiling_tokens` (int) — aggregate token budget per lane run.
  - `depends_on` (List[LaneID]) — upstream lanes required before activation.
  - `schema_refs` (List[SchemaVersion]) — JSON Schema IDs used by the lane.
  - `ai_runtime_profile` (StrEnum) — pointer to `packages.ai.api` profile.
- **Relationships**:
  - Each lane package binds multiple `ImplementationBlueprintRecord` entries (one per stage/artifact).
  - QA contracts reference telemetry rows in `ResidencyObservabilityLedger`.
- **Validation Rules**:
  - Stage sequence must align with capability mapping (GENERATE/EXTRACT/EVAL/etc.).
  - `cost_ceiling_tokens` enforced at runtime; plan enforces static threshold.

## 3. ResidencyObservabilityLedger
- **Purpose**: Append-only ledger capturing AI runtime interactions, telemetry exports, and residency attestations.
- **Fields**:
  - `ledger_id` (UUID) — primary key.
  - `feature_id` (StrEnum) — e.g., `001-ai-refactor-plan`, `002-ai-refactor-plan`.
  - `run_id` (UUID) — correlates to readiness dry run or CI job.
  - `stage_key` (StageKey) — LangGraph stage that produced the entry.
  - `residency_tag` (StrEnum) — e.g., `US-EAST`, `EU-CENTRAL`.
  - `telemetry_bundle_path` (path string) — location in `storage/ops/audit`.
  - `langsmith_eval_ids` (List[UUID]) — eval runs produced during the stage.
  - `langfuse_session_id` (UUID | null) — only during R&D window.
  - `disconnect_event` (bool) — marks LangFuse teardown evidence.
  - `timestamp` (datetime, UTC) — append time.
- **Relationships**:
  - Linked from ImplementationBlueprintRecord (evidence) and LangGraphLanePackage (QA contract compliance).
- **Validation Rules**:
  - Entries are immutable; updates append a new record referencing the same run.
  - `langfuse_session_id` must be null once R&D-only window closes.

## 4. ReadinessDatasetSnapshot
- **Purpose**: Normalized readiness tables produced from spec/001 inputs.
- **Fields**:
  - `component_id` (UUID) — stable identifier for a module/capability.
  - `lane_id` (StrEnum) — matches `LangGraphLanePackage.lane_id`.
  - `owner` (StrEnum) — DRI.
  - `status` (Enum: `unknown`, `partial`, `ready`, `blocked`).
  - `last_validated_at` (datetime) — recency requirement (<14 days).
  - `evidence_refs` (List[UUID]) — ledger IDs proving readiness.
  - `risk_score` (int 0–100) — derived metric based on blockers.
- **Relationships**:
  - Aggregates ImplementationBlueprintRecord states to compute readiness.
  - Feeds dashboards/CLI and is consumed by quickstart validation flows.
- **Validation Rules**:
  - `status` transitions must be monotonic unless a regression entry is logged.
  - `last_validated_at` must update whenever evidence references change.

## 5. EntityRelationshipGraph
- **Purpose**: Captures relational context extracted by Analyze pipelines (entities, events, relationships).
- **Fields**:
  - `graph_id` (UUID) — unique per dry run / dataset.
  - `nodes` (List[EntityNode]) — participants, institutions, events, evidence artifacts.
  - `edges` (List[RelationshipEdge]) — directional or undirected relationships with metadata.
  - `provenance_refs` (List[ArtifactID]) — links to source transcripts/documents.
  - `confidence` (float 0–1) — aggregate confidence for the graph build.
  - `schema_version` (Str) — JSON Schema version for graph exports.
- **Relationships**:
  - `nodes` reference readiness components; edges power downstream timeline/relationship agents.
  - Stored with readiness snapshots and referenced by LangGraph lanes that require relational context.
- **Validation Rules**:
  - Each edge must reference valid node IDs and include an evidence reference.
  - Missing entity relationships block readiness sign-off until waived with audit evidence.
