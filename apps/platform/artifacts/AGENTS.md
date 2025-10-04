# uDocket — Artifacts (CaseArtifact) Guide

Scope: `apps/platform/artifacts/` (artifact model, admin, serializers).

## Model Rules
- `CaseArtifact` is append‑only for content; avoid modifying or reusing physical files. New runs should create new versions and records.
- Uniqueness: `unique_together = (case_id, type, title)`; use helpers to generate unique titles.
- Organization ID is auto‑hydrated on save when missing (apps/platform/artifacts/models.py:148).
- Use `CaseArtifact.scoped()` when you need a typed manager with tenancy helpers (e.g., `CaseArtifact.scoped().for_user(user)`).

-## Types & File Paths
- Everything the system ingests or produces should be an artifact. Recommended types:
  - `AUDIO` (original uploads under `audio/<job>__<original>`) — includes `mime`, `duration_s`, and hashes in metadata
  - `TRANSCRIPT` (primary text)
  - `SUMMARY` (markdown or text)
  - `TIMELINE` (JSON, optional HTML viz)
  - `ENTITIES` (extracted entities JSON)
  - `RELATIONSHIPS` (client-centric relationship map JSON; see schema below)
  - `GRAPH` (optional viz/graph JSON, if a separate representation is used)
  - `DOCUMENT` (uploaded PDFs/docs) and `OCR_TEXT`/`OCR_JSON` (OCR outputs)
  - Store absolute `path` only after validating existence and scoping under the tenant case root.
  - For downloads, serve via authorized views; avoid exposing raw paths.

## Metadata
- Keep provenance: `source_transcript|source_audio|source_document`, `case_id`, `job_id`, `schema_version`, tool/library versions, timestamps.
- Hashing is mandatory: compute SHA‑256 for every artifact and set both `CaseArtifact.checksum` and the per‑run ops JSON; include size in bytes where possible. Checksums are immutable once set.
- Only include non‑sensitive, scoped information in API responses unless capability allows more detail.
- Approval gating: do not create “approved sidecar” artifacts. Instead, only promote/create the durable artifact after approval (policy enforced at the task/UI layer).

## Retention & Destruction
- Retention policies are organization‑specific. Plan to store settings on Organization and enforce via scheduled tasks.
- On destruction, generate a destruction certificate artifact (JSON or PDF) summarizing: artifact ids/paths destroyed, checksums, requestor, authorizer, timestamps, and method. Append an `ops_destruct.jsonl` event.

## RELATIONSHIPS Artifact (client‑centric)
- Type: `RELATIONSHIPS`
- Path: `analysis/<job_id>__relationships_v1.json`
- Schema:
  {
    "client": { "id": "string", "label": "string" },
    "people": [ { "id": "string", "label": "string", "role": "WITNESS|OPPOSING|COUNSEL|FAMILY|OTHER" } ],
    "relations": [
      {
        "source": "client",            // literal or client id
        "target": "<person_id>",        // one of people[].id
        "type": "REPRESENTED_BY|ADVISED_BY|OPPOSED_BY|AFFILIATED_WITH|RELATED_TO|MENTIONED_WITH",
        "evidence": [ { "ts": number|null, "text": "string" } ]
      }
    ]
  }
