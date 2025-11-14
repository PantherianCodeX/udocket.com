# Data Model – AI Module Migration Completion Plan

## MigrationStageReadiness
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `stage_key` | StrEnum (matches `packages/common/agents/stage_map.py`) | LangGraph stage identifier | Must exist in canonical stage map |
| `status` | StrEnum {complete,in_flight,blocked,not_started} | Current modernization state | Only allowed values; `complete` requires `last_validated_at` |
| `owner_team` | str | Responsible team name | Non-empty; must map to directory in org taxonomy |
| `last_validated_at` | datetime | Most recent evidence timestamp | Required for `complete` or `in_flight` |
| `evidence_links` | list[str] | URLs/doc refs proving status | At least one entry for every non-`not_started` record |
| `architecture_score` | int | 0-5 alignment score | Range 0–5 |
| `compliance_score` | int | Residency/AI runtime score | Range 0–5 |
| `observability_score` | int | Telemetry readiness score | Range 0–5 |
| `cutoff_date` | date | Target completion date | Must be ≥ today |

**Relationships**: `MigrationStageReadiness` aggregates multiple `CapabilityGap` records (one-to-many) keyed by `stage_key`.

## CapabilityGap
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `gap_id` | UUID | Unique identifier | Must be UUIDv7 |
| `component_id` | str | AI module component identifier | Matches readiness inventory keys |
| `category` | StrEnum {architecture,tooling,telemetry,residency,risk} | Gap classification | Required |
| `severity` | StrEnum {low,medium,high,critical} | Impact level | `critical` requires exec owner |
| `owner` | str | Mitigation owner | Non-empty |
| `mitigation_plan` | str | Summary of fix | ≥25 chars |
| `due_date` | date | Planned resolution | ≥ today |
| `status` | StrEnum {open,in_progress,blocked,closed} | Lifecycle | `closed` requires `resolution_notes` |
| `resolution_notes` | str? | Closure details | Required if status `closed` |

**Relationships**: Linked to `MigrationStageReadiness` via `stage_key`, and optionally to `ObservabilityControl` or `ToolingWorkspace` when remediation involves tooling.

## ObservabilityControl
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `control_id` | UUID | Identifier | UUIDv7 |
| `stage_key` | StrEnum | Stage where control applies | Must exist |
| `metrics` | list[str] | Metric names emitted | Non-empty |
| `traces` | list[str] | Trace/span names | Optional but logged |
| `ops_jsonl_schema_version` | str | Schema version used | Semver pattern |
| `alert_routing` | list[str] | Pager/SOC channels | Non-empty |
| `langfuse_enabled` | bool | Whether LangFuse emits data | true only for R&D |
| `environment_scope` | list[StrEnum {dev,staging,preprod,prod}] | Allowed environments | Must align with directives |
| `enablement_evidence` | list[str] | Links to screenshots/runbooks | Required when `langfuse_enabled` true |
| `validation_status` | StrEnum {planned,in_progress,validated} | Checklist state | `validated` requires timestamp |

## LLMToolingDecision
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `decision_id` | UUID | Identifier | UUIDv7 |
| `tooling_type` | StrEnum {langsmith,guardrails,prompt_registry} | Tool classification | Required |
| `summary` | str | Rationale for choosing tool | ≥50 chars |
| `comparison_matrix` | list[str] | Key differentiators vs alternatives | 1–5 entries |
| `approvals` | list[str] | Stakeholder approvals | Non-empty |
| `rollout_sequence` | list[str] | Stage/lane order | Chronological |
| `residency_notes` | str | How residency/egress is handled | Required |

## ToolingWorkspace
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `workspace_id` | UUID | Identifier | UUIDv7 |
| `vendor` | StrEnum {LangSmith,LangFuse} | Vendor name | Required |
| `environment` | StrEnum {dev,staging,preprod} | Workspace scope | Required |
| `owners` | list[str] | Responsible individuals | ≥1 |
| `env_var_names` | list[str] | `.env` variable names holding credentials (e.g., `LANGSMITH_API_KEY`) | ≥1 |
| `expires_at` | datetime | Rotation deadline | ≤90 days from issue |
| `governance_status` | StrEnum {approved,pending,revoked} | Current compliance state | Required |
| `notes` | str | Additional guidance | Optional |

## EvaluationEvidence
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `experiment_id` | str | LangSmith experiment identifier | Matches LangSmith UID format |
| `dataset_hash` | str | Digest of dataset used | SHA256 hex |
| `prompt_bundle_id` | str | Prompt manifest identifier | Non-empty |
| `metrics` | dict[str,float] | Named metrics (pass_rate,latency,cost) | Values 0–1 for ratios; latency ms |
| `run_started_at` | datetime | Time evaluation began | Required |
| `run_completed_at` | datetime | Time evaluation finished | ≥ start |
| `owner` | str | Person responsible | Non-empty |
| `governance_tags` | list[str] | Labels like critical/smoke | Optional |
| `attachments` | list[str] | Evidence links | Optional |

## ObservabilitySession
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `session_id` | UUID | LangFuse session id | UUIDv7 |
| `environment` | StrEnum {dev,staging} | Allowed env | Prod forbidden |
| `sampling_rate` | float | 0–1 fraction of traffic observed | ≤0.25 |
| `status` | StrEnum {enabled,disabled,scheduled_for_disable} | Lifecycle | `enabled` requires kill-switch reference |
| `kill_switch_reference` | str | Runbook link | Required when enabled |
| `retention_days` | int | Data retention | ≤30 |
| `decommissioned_at` | datetime? | When disabled | Required once status `disabled` |

## VendorUsageBudget
| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `vendor` | StrEnum {LangSmith,LangFuse} | Vendor name | Required |
| `month` | date | First day of month | Must be first day |
| `allocated_amount_usd` | decimal | Budgeted spend | >0 |
| `actual_amount_usd` | decimal | Actual spend to date | ≥0 |
| `alert_80_sent_at` | datetime? | Timestamp of 80% alert | Optional |
| `alert_100_sent_at` | datetime? | Timestamp of 100% alert | Optional |
| `variance_percent` | float | ((actual-allocated)/allocated)*100 | Auto-calculated |
| `mitigation_plan` | str | Steps when over budget | Required if variance>10 |
