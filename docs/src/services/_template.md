# Service Specification Template

This checklist ensures each service document follows the standardized structure from `docs/tdd_modularization.md`. Copy this file when authoring a new service spec and replace the placeholder text. Remove the guidance notes before publishing.

## 0) Reading Guide

Use this section to orient readers before they dive into the specification. It should be bespoke to the service—no copy/paste boilerplate and no preamble block. Summarize how to consume the doc, who owns it, required prerequisites, and where to go for adjacent material. Mix short paragraphs and bullets as needed.

- **Scope:** Tailor this to the service’s charter and the audiences that should read it.
- **Structure:** Explain how this document is laid out (sections, appendices, diagrams) and why.
- **Maintenance:** Call out linting/build requirements, review cadence, and who approves edits.
- **Change protocol:** Note how changes to this service must reference or update the doc.
- **References:** Link to TDD sections, ADRs, runbooks, or repos readers must consult first.
- **Contacts:** Give the owning teams, mailing lists, or escalation paths.

## 1) Purpose

**Purpose:** State the service’s mission and success criteria.\
**Contract:** Define scope boundaries and invariants the service guarantees.\
**State:** Summarize the lifecycle of key objects/configs the service owns.\
**Failure modes & handling:** Call out high-level risks to the mission.\
**Observability:** Metrics/logs/SLO dashboards tied to the charter.\
**Breadcrumbs:** Source files, tests, dashboards maintaining the charter.\
**References:** Cross-reference supporting specs or ADRs.

## 2) Responsibilities

**Purpose:** Enumerate functional responsibilities and non-goals.\
**Contract:** Spell out mandatory behaviours, idempotency, regulatory duties.\
**State:** Describe ownership of state transitions or data stewardship.\
**Failure modes & handling:** Identify responsibility gaps and escalation paths.\
**Observability:** Checks proving each responsibility works.\
**Breadcrumbs:** Implementation/tests supporting each responsibility.\
**References:** Service/TDD sections that expand on responsibilities.

## 3) API Contract

**Purpose:** Document public and internal interfaces.\
**Contract:** Define required inputs/outputs, authentication, and versioning.\
**State:** Highlight persisted payloads, schemas, queues, or files produced.\
**Failure modes & handling:** Enumerate error codes, retries, and backoffs.\
**Observability:** Metrics/logs/traces covering API health.\
**Breadcrumbs:** Controller handlers, schema definitions, integration tests.\
**References:** Link to schema fixtures or appendices.

### 3.1 External Interfaces

> Detail REST/gRPC/event/file contracts exposed outside the service.

### 3.2 Internal Interfaces

> Capture intra-service modules, background jobs, or queues.

## 4) State Management

**Purpose:** Explain storage and configuration strategy.\
**Contract:** Define persistence guarantees, migration expectations, and retention.\
**State:** Describe schemas, caches, and configuration sources.\
**Failure modes & handling:** Cover corruption, drift, and reconciliation flows.\
**Observability:** Metrics for storage health, cache hit rates, or config parity.\
**Breadcrumbs:** ORM models, migrations, infrastructure manifests.\
**References:** TDD appendices or diagrams related to state.

## 5) Failure Modes

**Purpose:** Provide the resilience profile and default mitigations.\
**Contract:** Identify what must fail closed vs. degraded.\
**State:** Note circuit breakers, queues, or compensating transactions.\
**Failure modes & handling:** Enumerate incidents, fallback procedures, and manual runbooks.\
**Observability:** Alerts, dashboards, and SLOs tied to failure handling.\
**Breadcrumbs:** Runbooks, incident retros, chaos tests.\
**References:** Link to ops docs or ADRs describing failure strategy.

## 6) Observability

**Purpose:** Show how to detect and diagnose issues.\
**Contract:** List mandatory telemetry and alerting coverage.\
**State:** Capture dashboards, log pipelines, or tracing spans.\
**Failure modes & handling:** Note alert fatigue risks or blind spots.\
**Observability:** Detail metrics/logs/traces plus owners.\
**Breadcrumbs:** Monitoring configs, dashboards, alert definitions.\
**References:** Observability standards or shared appendices.

## 7) Security and Compliance

**Purpose:** Capture authZ/authN, data handling classes, and regulatory duties.\
**Contract:** Define encryption rules, residency bounds, and audit requirements.\
**State:** Describe secrets, key rotation, and data classifications.\
**Failure modes & handling:** Explain how breaches or policy drifts are detected and resolved.\
**Observability:** Security alerts, audit trails, compliance evidence.\
**Breadcrumbs:** IAM configs, policy bundles, compliance tests.\
**References:** Link to residency or policy appendices/ADRs.

## 8) Operational Notes

**Purpose:** Summarize deployments, maintenance windows, and runbooks.\
**Contract:** Capture SLAs, rollout gates, and release cadence.\
**State:** Note infrastructure manifests and environment differences.\
**Failure modes & handling:** Document deployment rollback and incident processes.\
**Observability:** Release dashboards, deployment checks, synthetic monitors.\
**Breadcrumbs:** Helm charts, Terraform modules, runbooks.\
**References:** Ops appendices or deployment ADRs.

## 9) Dependencies

**Purpose:** List upstream/downstream systems and their contracts.\
**Contract:** Describe expectations on dependency behaviour and change management.\
**State:** Identify shared schemas/events and their owners.\
**Failure modes & handling:** Explain cascading failure protections.\
**Observability:** Dependency health checks and joint dashboards.\
**Breadcrumbs:** Integration specs, dependency docs.\
**References:** Link to other service docs or appendices.

## 10) References

**Purpose:** Point readers to supplemental material.\
**Contract:** Ensure references stay current and authoritative.\
**State:** Maintain links to diagrams, ADRs, glossaries.\
**Failure modes & handling:** State how outdated references are surfaced.\
**Observability:** Mention review cadence or linting support.\
**Breadcrumbs:** None (or list meta scripts).\
**References:** Optional closing links (ADR index, glossary, appendices).
