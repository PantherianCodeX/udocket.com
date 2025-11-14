# Feature Specification: AI Module Migration Completion Plan

**Feature Branch**: `001-ai-refactor-plan`  
**Created**: 2025-11-14  
**Status**: Draft  
**Input**: User description: "Plan the completion of the re-engineering and refactor of the AI module. Parts have been migrated, determine where we are and chart a plan forward to full migration, modern LLM tooling and observability installed and configured, ready to dial in the pipeline." Additional directive: "we need to install depends for llm tooling - we want to add LangSmith for prototyping and evals and LangFuse for observability. LangFuse will only be connected for initial R&D of pipeline only and will not be a permanent feature."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assess Current Migration State (Priority: P1)

The AI program manager needs a single source of truth showing exactly which AI module components, environments, and controls have already migrated to the modern architecture so they can explain status and unblock stakeholders.

**Why this priority**: Without a factual baseline, the remaining refactor cannot be sequenced, funding cannot be justified, and dependent teams remain uncertain.

**Independent Test**: Generate the readiness dashboard and confirm it lists every AI module surface with an explicit state (Complete / In Flight / Blocked) plus owner and evidence links.

**Acceptance Scenarios**:

1. **Given** existing partial migrations, **When** the manager loads the readiness inventory, **Then** all AI module components show source/target state, owning team, last validation date, and blocking issues.
2. **Given** a component with missing data, **When** the manager flags it, **Then** the system captures the gap with owner assignment and includes it in the migration risk log.

---

### User Story 2 - Plan Remaining Modernization (Priority: P2)

The staff engineer responsible for the AI module needs a sequenced plan that maps remaining refactor tasks to LangGraph pipeline stages, identifies dependencies, and provides estimates so the work can be scheduled.

**Why this priority**: A credible plan is necessary to commit to delivery dates and ensure modernization follows platform standards (type-first contracts, AI runtime layering, residency guards).

**Independent Test**: Review the migration backlog artifact and verify every remaining component has a target design summary, dependency list, effort sizing, and acceptance gates tied to LangGraph stages.

**Acceptance Scenarios**:

1. **Given** a partially migrated capability, **When** the engineer opens its task stack, **Then** they see target architecture notes, integration touchpoints, and required verification steps.
2. **Given** two tasks with ordering constraints, **When** the plan is generated, **Then** the dependencies are reflected in the roadmap with critical path flags.

---

### User Story 3 - Enable LLM Tooling & Observability (Priority: P3)

The AI operations lead needs to ensure modern LLM tooling—including LangSmith for prototyping/evaluations and a temporary LangFuse connection for R&D observability—is fully specified before pipeline dial-up, alongside baseline OTLP metrics, ops JSONL, and audit logs.

**Why this priority**: Dialing up the pipeline without governed evaluation tooling or scoped observability violates platform standards, prevents rapid tuning, and risks leaving the temporary LangFuse hookup in place longer than allowed.

**Independent Test**: Execute the tooling and observability checklist and confirm LangSmith workspaces, LangFuse dashboards, and native telemetry each meet governance rules, route calls through the approved AI runtime, and include activation/deactivation runbooks.

**Acceptance Scenarios**:

1. **Given** LangSmith access is provisioned, **When** the lead triggers a prototype evaluation from a LangGraph lane, **Then** the results sync to readiness artifacts with residency attestations and do not bypass AI runtime enforcement.
2. **Given** LangFuse is limited to R&D, **When** the lead executes the disconnect playbook, **Then** ingestion stops within the allowed window, credentials are revoked, and the plan records the teardown evidence for audits.

### Edge Cases

- Discovery shows a component without an identified owner; the plan must route it to governance for reassignment before migration continues.
- Legacy AI module paths carry data lacking residency metadata; specification must block promotion until residency fields are populated and verified.
- Telemetry backfills reveal missing historical data; plan must include compensating controls (synthetic traces or manual verification) before allowing cutover.
- LangSmith evaluation datasets inadvertently contain production PII; the plan must define redaction workflows and halt usage until data is purged.
- The "temporary" LangFuse integration remains connected past the R&D phase; governance must require automated kill switches and certification before any extension.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Provide a canonical AI module inventory that lists every service, workflow, model call, and storage touchpoint with current vs. target architecture mapping, owner, and last validation date.
- **FR-002**: Generate a migration readiness matrix that scores each component across architecture, data residency, testing, observability, and AI runtime compliance, highlighting blockers with mitigation owners.
- **FR-003**: Produce a prioritized backlog of remaining refactor tasks with effort ranges, dependencies, and LangGraph stage alignment so program planning can schedule the work.
- **FR-004**: Define the target modern LLM tooling toolkit—with LangSmith as the sanctioned prototyping/evaluation surface—covering dependency installs, workspace governance, prompt dataset policies, decision criteria, rollout sequencing, and integration checkpoints.
- **FR-005**: Specify observability requirements for every pipeline stage, including LangFuse-backed R&D dashboards, native metrics, traces, ops JSONL artifacts, and audit events needed to support runbooks and tuning sessions.
- **FR-006**: Document the AI runtime enforcement plan ensuring all providers are accessed through `packages.ai.api` (or injected `AIClient`), with residency/egress guardrails, waiver handling, and fail-closed behaviors.
- **FR-007**: Outline the activation plan for dialing up the modernized pipeline, covering dry-runs, sampling strategies, rollback triggers, and stakeholder sign-offs for each release lane.
- **FR-008**: Capture communication, risk, and dependency management processes, including weekly reporting cadence, executive checkpoints, and integration touchpoints with Guardian/Settings teams.
- **FR-009**: Establish activation/teardown controls for the temporary LangFuse integration (environment allow-list, sampling rules, kill-switch validation, post-R&D data purge) and evidence requirements proving it is not a permanent feature.

### Key Entities

- **MigrationStageReadiness**: Represents a LangGraph stage (ingest, planner, executor, auditor, etc.) with fields for current status, evidence links, scoring across architecture/compliance/observability, and target cutoff date.
- **CapabilityGap**: A structured gap record containing component ID, deficiency category (architecture, tooling, telemetry, residency), severity, owner, mitigation plan, and due date.
- **ObservabilityControl**: Defines telemetry/control expectations per pipeline stage (metrics, traces, ops JSONL schema, alert routing), noting whether LangFuse is active, the environment scope, and the associated enable/disable evidence.
- **LLMToolingDecision**: Captures selected tooling (evaluation harness, guardrails, prompt registry) with LangSmith-specific governance data, comparison matrices, approvals, and rollout sequencing.

### Schema & Interface Contracts *(Constitution P1)*

- **Internal Models**: MigrationStageReadiness, CapabilityGap, ObservabilityControl, and LLMToolingDecision will be expressed as typed dataclasses or `TypedDict` structures within the agent package to ensure deterministic serialization when emitting ops/audit artifacts.
- **External Schemas**: Publish JSON schema revisions for the readiness matrix export, LangSmith evaluation evidence, and observability checklist so downstream tooling (dashboards, audit bots) can validate inputs; version identifiers must increment when fields or enumerations change.
- **Backward Compatibility**: Provide migration notes for consumers of legacy readiness exports; support a dual-write period where both old and new schema are emitted until downstream teams confirm cutover.

### Compliance, Observability & Residency *(Constitution P2 & P5)*

- **Telemetry**: Instrument each LangGraph stage with OTLP spans, latency/cost metrics, and structured ops JSONL entries; define dashboards covering migration velocity, blocker aging, LLM cost per run, prompt change frequency, plus LangFuse R&D dashboards with explicit enable/disable evidence.
- **Residency & Data Handling**: Specify residency classification for all AI module data (PII/regulated/unregulated), storage regions, retention periods, and redaction requirements for exported readiness data; document LangSmith dataset handling and ensure temporary LangFuse traces follow the same residency policies, blocking activation when metadata is missing.
- **AI Runtime Contract**: Confirm all LLM calls route through the centralized AI runtime (`packages.ai.api` or injected `AIClient`), enforce provider allow-lists, capture prompt/response metadata for audits, and describe expected prompt evaluation cadence before promoting new prompts.

### Security, Performance & Resilience *(Constitution P5 & P6)*

- **Threat Model**: Evaluate abuse cases including prompt injection into partially migrated stages, unauthorized access to migration dashboards, LangSmith credential leakage, and LangFuse trace exfiltration; require security review plus automated scanning of artifacts before release.
- **Performance Budgets**: Establish target budgets per pipeline stage (e.g., readiness computation completes in <10 minutes, observability export latency <2 minutes, LangFuse sampling adds <5% run overhead) and define escalation procedures if budgets exceed thresholds during ramp.
- **Migrations & DR**: Mandate forward-only migrations with snapshot backups of existing manifests, include rollback instructions for readiness data, ensure DR playbooks incorporate new telemetry and AI runtime dependencies, and document LangFuse teardown/recovery paths since it is temporary.
- **Frontend/UX**: Ensure readiness surfaces meet accessibility expectations (keyboard navigation, high-contrast views) and localization for stakeholder-facing summaries if required by governance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of AI module components and LangGraph stages are represented in the readiness inventory with verified ownership and evidence links.
- **SC-002**: At least 90% of remaining modernization tasks carry documented dependencies, estimates, and acceptance gates, enabling inclusion in the next two quarterly plans.
- **SC-003**: Observability coverage plan demonstrates metrics/traces/logging definitions for every pipeline stage, including LangFuse R&D dashboards, with at least 95% of required telemetry hooks validated in non-production dry-runs.
- **SC-004**: Executive steering committee approves the migration plan with no high-severity risks left unmitigated (or explicitly waived) and commits to the activation timeline.
- **SC-005**: LangSmith prototyping/evaluation enablement reaches 90% of targeted engineers, and the LangFuse integration is disconnected within 15 minutes of the R&D phase ending, with audit evidence captured.

## Assumptions

1. All earlier partial migrations followed the LangGraph agent specification and any deviations will be surfaced in the readiness discovery workshops.
2. Modern LLM tooling selections must integrate with existing residency/egress guardrails; no provider outside the current compliance perimeter will be considered without a separate governance project.
3. Observability infrastructure (OTLP pipeline, ops JSONL storage, dashboarding stack) already exists; this effort configures and extends it for the AI module rather than building net-new infrastructure.
4. LangFuse access is restricted to R&D environments with pre-approved data boundaries, and stakeholders agree the integration will be removed once permanent observability reaches parity.
