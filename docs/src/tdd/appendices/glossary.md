# Glossary

Authoritative definitions used across TDD, services, and UI. Keep terms concise and stable; link here from specs instead of duplicating definitions.

- Artifact: A versioned file produced by a tool or manual edit; immutable once promoted. Examples: transcript.txt, compose_client_v1.md, staff_report_v1.md.
- Work Product: In‑progress content before promotion to an artifact; subject to edits and approvals.
- Candidate Deliverable: A proposed artifact version awaiting Reviewer approval to promote.
- Guardian: Policy and quality gate that classifies outputs and enforces PASS/WARN/BLOCK outcomes with evidence.
- Localization & Policy Engine (LPE): OPA‑backed rules and data policies (RLS/masking) compiled from the Settings Registry; governs access decisions via `udocket_can`.
- Reference Manager (RM): Service for canonical references, identifiers, and registries used by agents and platform features.
- Settings Registry: Central configuration and activation workflow for org/case policies, roles, and enforcement profiles.
- LLM Registry: Registry of model providers/versions and allowed profiles per organization.
- Transcribe Agent: Azure Speech–backed agent that produces case transcripts and ops metadata (Canada regions only).
- Analyze Agent: Consumes transcripts to produce summaries, outlines, timeline seeds, entity hints, and staff reports.
- Compose Agent: Produces client/lawyer deliverables and QA artifacts via LangGraph with guard rails.
- Case: Top‑level container for jobs, artifacts, and operations; storage under `storage/media/cases/<CASE_ID>/`.
- Job: A unit of work executed by agents or tools; writes ops logs and per‑run metadata; artifacts are prefixed with `<job_id>__`.
- Diarization: Speaker segmentation supported in batch transcription mode.
- Ops Audit: Append‑only JSONL streams under `ops/` for provenance and analytics.
- ADR: Architecture Decision Record (immutable). Stored under `docs/src/adr/`.
- RLS (Row‑Level Security): Postgres policies restricting per‑row access; enforced via settings‑compiled functions.
- Effective Permission: Settings‑compiled permission entries defining resource/action/role checks (see `udocket_can`).
- Field Mask Rule: Settings‑compiled masking profile for sensitive fields and allowed roles.
- PASS/WARN/BLOCK: Guardian judgments; see Status Mapping for canonical meanings.

See also: Status Mapping (Appendix).

