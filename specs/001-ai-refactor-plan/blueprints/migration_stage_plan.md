# Migration Stage Plan Blueprint

## Purpose
Map each LangGraph stage to modernization tasks, QA gates, and cost ceilings, referencing the stage deltas recorded in `drafts/stage_catalog.md` and the requirements in `plan.md`/`spec.md`.

## Structure
| StageKey | Status Goal | Owners | QA Gates | Cost Ceiling | Notes |
|----------|-------------|--------|----------|--------------|-------|
| `analyze.input_discovery` | Keep `complete` | AI Readiness | Ops JSONL ingest evidence logged each refresh | $0.05/run | Baseline ingestion stage. |
| `analyze.atoms_extract` | Move to `complete` after deterministic token histograms | AI Modernization | Token histogram + owner ack, auto gap creation on failure | $0.20/run | Needs retry budget bump. |
| `analyze.context_builder` | `in_flight` → `complete` once residency tags validated | AI Modernization | Residency tag validator + Spectral docs lint | $0.25/run | Uses `AgentTask.SYNTHESIZE`. |
| `analyze.gaps_extract` | `blocked` → `in_flight` once ingest diffs added | AI Modernization | Gap diff check vs readiness dataset hash | $0.30/run | Reactivated stage. |
| `analyze.flags_extract` | Activate after governance approval | Governance | Risk flag QA vs risk log entries | $0.15/run | Outputs feed risk log JSONL. |
| `compose.release_gate` | Blocked until residency attestation wired | Delivery | Ops hash verification + residency attestation upload | $0/run (no LLM) | Compose release waits for readiness hash. |

## QA/Cost References
- QA gates align with readiness fixtures + ops manifest; results feed into `reports/risk_log.jsonl` and ops seal chain.
- Cost ceilings derived from stage catalog blueprint; to be enforced in `packages/common/agents/stage_map.py` updates later.

## Activation Checklist
1. Refresh readiness datasets via CLI and ensure ops hash recorded.
2. Validate QA gates per stage (manual evidence now, automated once service integrates).
3. Update backlog entries referencing this plan (T017 pre-req for T020).
