---
title: "uDocket — TDD Appendix: Status Mapping"
subtitle: "Guardian judgments to artifact status reference"
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

<!-- BEGIN AUTO-GENERATED: document-controls -->
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
<!-- END AUTO-GENERATED: document-controls -->

______________________________________________________________________

## Judgments

Canonical mapping between Guardian judgments and artifact statuses/UI labels. This page is the single source of truth; specs and code link here.

- PASS: Artifact meets policy requirements.
  - UI label: Approved / Pass
  - Typical action: Promote to artifact, visible to intended audience.
- WARN: Artifact has issues that require review but may be override‑approved.
  - UI label: Needs Review / Warning
  - Typical action: Assign reviewer, capture remediation notes; do not auto‑promote.
- BLOCK: Artifact fails policy checks and must not be delivered.
  - UI label: Blocked / Rejected
  - Typical action: Quarantine; require changes before re‑evaluation.

Provenance

- Code references: packages/udocket_core/artifacts/status.py (status enums) and Guardian outputs.
- UI: presenters should reflect `has_summary`, `has_timeline`, etc. derived from artifacts, not tools.
