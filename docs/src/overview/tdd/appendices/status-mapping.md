# Status Mapping (Guardian)

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
