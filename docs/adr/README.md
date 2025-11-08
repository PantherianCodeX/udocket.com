# Architecture Decision Records

The ADRs in this directory capture notable, high-impact decisions for the uDocket platform. Each record is immutable once accepted; superseding a decision requires a new ADR that references the prior entry.

## Index

| ADR | Title | Status | Summary |
| --- | --- | --- | --- |
| [ADR-0001](ADR-0001-guardian-ready-quarantine.md) | Guardian READY/QUARANTINED gating | Accepted | Guardian is the authoritative policy gate before reviews or portal exposure. |
| [ADR-0002](ADR-0002-api-versioning-and-sunset.md) | Public API versioning & sunset policy | Accepted | Calendar-versioned API releases with deprecation headers and tooling guardrails. |
| [ADR-0003](ADR-0003-localization-and-policy-engine.md) | Localization & Policy Engine control/data plane split | Accepted | Separates RM (control plane) and LPE (data plane) with signed bundles. |
| [ADR-0004](ADR-0004-opa-policy-plane.md) | Open Policy Agent policy plane integration | Accepted | OPA evaluates signed bundles for residency, HIPAA, and attachment rules. |
