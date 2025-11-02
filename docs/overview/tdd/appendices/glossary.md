---
title: "uDocket — TDD Appendix: Glossary"
subtitle: "Canonical terminology reference"
authors:
  - "Platform Documentation Team"
version: "0.1-draft"
status: implementable
classification: Confidential
last_updated: "2025-10-29"
updated_by: "Documentation Team"
owners:
  - "Platform Documentation Team"
reviewers:
  - "Platform Architecture"
approvers:
  - "Architecture Steering Committee"
approved_by:
approved_date:
---

______________________________________________________________________

## Document Controls

| Field | Value |
| --- | --- |
| Authors | Platform Documentation Team |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Documentation Team |
| Reviewers | Platform Architecture |
| Approvers | Architecture Steering Committee |
| Approved by | |
| Approved date | |

______________________________________________________________________

## Terms

Authoritative definitions used across TDD, services, and UI. Keep terms concise and stable; link here from specs instead of duplicating definitions.

- Artifact: Immutable content record with `class`, `status`, `content_hash`, and manifest. Statuses follow §5.2 (`STORED`, `PROCESSING`, `PENDING_JUDGMENT`, `CLEARED_FOR_USE`, `OPERATOR_PREP`, `APPROVAL_REQUESTED`, `QUEUED_FOR_REVIEW`, `CHANGES_REQUESTED`, `QUARANTINED`, `APPROVED`, `SIGNED`, `RELEASED`, `REVOKED`, `ARCHIVED`, `DELETED`).
- Work Product: In‑progress content before promotion to an artifact; subject to edits and approvals.
- Candidate Deliverable: A proposed artifact version awaiting Reviewer approval to promote.
- Exclusive type: Artifact type for which a case may have at most one `APPROVED` at a time; enforced by unique index and approval swap (§5.4.1).
- Guardian: Policy and quality gate that issues PASS/WARN/BLOCK/WAIVED judgments and drives workflow transitions before review.
- Localization & Policy Engine (LPE): OPA‑backed rules and data policies (RLS/masking) compiled from the Settings Registry; governs access decisions via `udocket_can`.
- Reference Manager (RM): Editorial/catalog service for jurisdictional data, questionnaires, and localization strings; publishes signed bundles to LPE.
- Settings Registry: Central configuration and activation workflow for org/case policies, roles, and enforcement profiles.
- LLM Registry: Registry of model providers/versions and allowed profiles per organization.
- Transcribe Agent: Azure Speech–backed agent that produces case transcripts and ops metadata (Canada regions only).
- Analyze Agent: Consumes transcripts to produce summaries, outlines, timeline seeds, entity hints, and staff reports.
- Compose Agent: Produces client/lawyer deliverables and QA artifacts via LangGraph with guard rails.
- Case: Top‑level container for jobs, artifacts, and operations; storage under `storage/media/cases/<CASE_ID>/`.
- Job: A unit of work executed by agents or tools; writes ops logs and per‑run metadata; artifacts are prefixed with `<job_id>__`.
- Manifest: JSON payload embedded in artifacts capturing provenance (regions, hashes, settings snapshot), tool versions, and inputs (§5.6).
- Review/Approval: Moves CDs from `OPERATOR_PREP` → `APPROVAL_REQUESTED` → `QUEUED_FOR_REVIEW`, culminating in `REVIEW.APPROVED`/`REVIEW.CHANGES_REQUESTED`/`REVIEW.QUARANTINED`.
- Diarization: Speaker segmentation supported in batch transcription mode.
- Ops Audit: Append‑only JSONL streams under `ops/` for provenance and analytics.
- ADR: Architecture Decision Record (immutable). Stored under `docs/adr/`.
- RLS (Row‑Level Security): Postgres policies restricting per‑row access; enforced via settings‑compiled functions.
- Effective Permission: Settings‑compiled permission entries defining resource/action/role checks (see `udocket_can`).
- Field Mask Rule: Settings‑compiled masking profile for sensitive fields and allowed roles.
- SSE: Server‑Sent Events for streaming job and artifact updates; token‑bound; supports `Last-Event-ID`.
- OCC: Optimistic concurrency control using `version` columns to avoid lost updates.
- udlock: Advisory lock helpers (`scope:key`) supporting session and transaction locks with registry visibility.
- Residency waiver: Temporary exception allowing cross‑region processing; requires dual approval and audited manifests.
- FinOps metrics: Cost/time series (e.g., `llm_cost_estimate_total`, `finops_cost_per_case_usd`, `finops_mom_regression_flag`) used for dashboards and deploy guards.
- LangGraph node: Typed step in Analyze/Compose graphs producing deterministic outputs with envelopes.
- Quota: Per‑org limits (uploads/day, concurrent jobs, portal downloads) enforced via rate limiting.
- PASS/WARN/BLOCK: Guardian judgments; see Status Mapping appendix for canonical meanings.

See also: Status Mapping (Appendix).
