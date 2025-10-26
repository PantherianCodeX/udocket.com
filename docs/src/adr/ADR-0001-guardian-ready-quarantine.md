# ADR-0001 — Guardian READY/QUARANTINED gating

- **Status:** Accepted  
- **Date:** 2025-02-14  
- **Deciders:** Architecture Steering Committee, Security Review Board  
- **Tags:** guardian, artifacts, approvals, compliance

## Context

Review workflows were inconsistent about when agent outputs became visible to staff or clients. Some artifacts bypassed automated policy scans, entered reviewer queues directly, and leaked non-compliant deliverables. We needed a deterministic contract that:

- Forces every artifact through policy evaluation before human approval.  
- Captures machine-readable decision history for audits.  
- Keeps downstream automation from acting on stale or quarantined content.  
- Works uniformly across Transcribe, Analyze, Compose, and any future agents.

## Decision

Introduce a dedicated Guardian service as the authoritative gatekeeper for artifact readiness.

- Agents write artifacts in `DRAFT`, then call `POST /guardian/submit` with `artifact_id`, `content_sha256`, and settings snapshot metadata.  
- Guardian evaluates signed policy bundles (privacy, residency, forbidden patterns) and returns one of:
  - `READY` — artifact may enter reviewer queues.
  - `QUARANTINED` — artifact stays hidden; decision contains machine-actionable reasons.  
- Guardian persists all decisions in `guardian_decision_history` with idempotency keys, polymerized settings hashes, and timestamps.  
- Downstream services must never promote artifacts that are not `READY`. Manual edits resubmit for re-evaluation.  
- Decision latency SLO: P95 ≤ 5 minutes (batch window), enforced via dashboards/alerts.

## Consequences

- Reviewers and portal surfaces only see artifacts after Guardian marks them `READY`.  
- Agent pipelines must handle quarantine gracefully (log, surface reason to SSE/UI, halt promotion).  
- We gained immutable audit trails for regulator reviews.  
- Additional policy domains (HIPAA overrides, waiver controls) can be layered into Guardian without touching agent code.  
- Trade-off: additional policy hop adds latency; mitigated with horizontal scaling and retries.

