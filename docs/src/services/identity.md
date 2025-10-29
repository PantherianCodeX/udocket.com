---
title: uDocket — Identity & Access Specification
subtitle: Authentication, Authorization, Masking, and Break-Glass Controls
author:
  - Identity & Access Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
owners:
  - Platform Engineering
  - Security Engineering
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - Site Reliability Engineering
  - Compliance Engineering
adr_index: docs/adr/README.md
related_adrs:
  - ADR-0001-guardian-ready-quarantine.md
  - ADR-0002-identity-provider-strategy.md
  - ADR-0004-localization-and-policy-engine.md
header-includes:
  - |
    <style>
      table {
        font-size: 8.5pt;
      }
      table td,
      table th {
        font-size: inherit;
        word-break: break-word;
        overflow-wrap: anywhere;
      }
    </style>
  - <header class="page-header">uDocket — Identity & Access Specification <br>
    Authentication, Authorization, Masking, and Break-Glass Controls</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-29 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

| Field | Value |
| --- | --- |
| Authors | Identity & Access Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Owners | Platform Engineering; Security Engineering |
| Reviewers | Site Reliability Engineering; Compliance Engineering |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by | |
| Approved date | |

**Status:** KEP: Provisional → Implementable → Implemented

**Section Requirements (binding):**
    - Preamble: Purpose/Contract/State/Failure/Observability/References/Breadcrumbs (`scripts/docs/lint_docs.py --check-template`)
    - Section tags: `(binding)`, `(normative)` or `(informative)`
    - Links resolve: §/App./ADR (`docs-link-check`)
    - Document validation: `python scripts/docs/lint_docs.py`
    - Settings keys: Document/code are in-sync
    - All requirements are CI gated

**Section tags:**
    - `(binding)` denotes requirements that block launch until implemented and tested.
    - `(normative)` captures default behaviors that may evolve via waivers or roadmap.
    - `(informative)` provides background or examples.
    - When a subsection omits a tag it is treated as informative by default—add the explicit tag when the content carries binding or normative weight.

______________________________________________________________________

## Reading Guide

- **Scope:** Keycloak realm configuration, org/case membership lattice, session binding, database RLS GUCs, masking, auditing, and break-glass governance. Guardian, Portal, Workers, and all APIs rely on this contract.
- **Structure:** Sections follow the 0–10 template. Responsibilities (§2) summarise primary duties; §3 covers authentication and federation; §4 the authorization lattice and database enforcement; §5 session/device binding; §6 masking and break-glass; remaining sections handle failure, observability, ops, and dependencies.
- **Maintenance:** Run `python scripts/docs/lint_docs.py docs/src/services/identity.md docs/src/overview/tdd.md docs/tdd_modularization.md` before landing identity changes. Update runbooks via `build_runbook_catalog.py --check`, rerun `make lint-db` when modifying RLS or masking SQL.
- **Change protocol:** Realm topology, token lifetimes, masking profiles, or break-glass policies require Security + Architecture approval. Any change impacting GUC setup or secure views must accompany migrations/tests and notify data platform owners.
- **References:** TDD §4 summary, Guardian spec §5 (quarantine), Settings spec (§2.4, §2.7, `security.*` keys), Worker Cluster spec §2 (watchdogs), Ops runbooks `RB-IDP-FAILOVER`, `RB-BREAK-GLASS`, `RB-RLS-CONTEXT`, `RB-MASK`.
- **Contacts:** Platform Engineering (identity services), Security Engineering (policy), SRE (session/watchdog automation), on-call alias `identity-oncall@`, Slack `#identity-access`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Provide a single source of truth for authentication, authorization, masking, and break-glass controls so all services enforce consistent identity guarantees. **|**
**Contract:** Keycloak realm configuration, token semantics, RLS GUC requirements, masking profiles, and break-glass workflows published here are binding; services must not diverge without updating this doc and associated policies. **|**
**State:** Keycloak realm configs, Settings bundles (`security.*`, `identity.*`), database functions (`udocket_can`, `udocket_mask`), secure views, audit trails, masking vault entries, break-glass ledger. **|**
**Failures & handling:** IdP outages, federation drift, device-binding mismatches, RLS GUC gaps, or masking violations trigger automated guards and runbooks in §8. **|**
**Observability:** Dashboards “Identity Posture”, “RLS Context Guards”, “Masking Vault & Profiles”, metrics `auth_layer_violation_total`, `rls_context_missing_total`, `device_fp_mismatch_total`, `break_glass_event_missing_retrospective_total`. **|**
**Breadcrumbs:** Implementation `apps/platform/auth/`, `apps/platform/db/guards.py`, `packages/udocket_core/masking/`, Keycloak exporters `infra/keycloak/`, tests `tests/platform/auth/`, `tests/platform/db/`, `tests/security/`. **|**
**References:** Settings spec (`security.*`, `identity.org_switch.*`), Guardian spec (policy enforcement), TDD §4 summary.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Enumerate what the identity stack owns across authentication, authorization, masking, and emergency access. **|**
**Contract:** Keycloak realm configuration, GUC enforcement, masking profiles, and break-glass controls must adhere to this document; deviations require Security + Architecture approval. **|**
**State:** Realm config, Settings bundles, secure views, masking vault, break-glass ledger. **|**
**Failures & handling:** IdP outages, RLS gaps, masking violations route through §5 and §8 runbooks. **|**
**Observability:** Dashboards “Identity Posture”, “RLS Context Guards”, “Masking Vault & Profiles”, PagerDuty analytics. **|**
**Breadcrumbs:** Keycloak exporters, `apps/platform/auth`, `apps/platform/db/guards.py`, masking modules, runbook catalog. **|**
**References:** Settings spec, Guardian spec, Worker Cluster spec, Ops runbook catalog.

- Operate the Keycloak realm, clients, roles, federation brokers, and token lifecycles for staff, portal, and service accounts.
- Maintain the org/case membership lattice, effective permissions (`udocket_can`), and secure views/SQL policies that enforce row-level security and masking.
- Enforce session/device binding, token step-up MFA, and break-glass workflows with dual approval and audit trail.
- Govern masking profiles, reversible tokenization, audit logging, and detokenization controls for sensitive data.
- Provide automation, metrics, and runbooks for IdP failover, federation linting, RLS context verification, and masking compliance.

______________________________________________________________________

## 3) API Contract (binding)

**Purpose:** Document external and internal interfaces for authentication, federation, and session enforcement. **|**
**Contract:** Clients MUST authenticate via Keycloak; services MUST validate tokens, org binding, and device fingerprints as defined here. **|**
**State:** Keycloak realm configuration, Settings bundles (`identity.*`, `security.session.*`), session/device fingerprint records, break-glass ledger. **|**
**Failures & handling:** Federation drift, token replay, or device mismatches escalate via §5 and §8 runbooks. **|**
**Observability:** Metrics `auth_layer_violation_total`, `device_fp_mismatch_total`, federation lint dashboards, audit logs. **|**
**Breadcrumbs:** Keycloak exporters (`infra/keycloak/`), `apps/platform/auth`, `apps/platform/session`, tests `tests/platform/auth/`. **|**
**References:** Settings spec §2, TDD §4, Ops runbooks `RB-IDP-FAILOVER`, `RB-DEVICE-FP`, `RB-BREAK-GLASS`.

### 3.1 External Interfaces (binding)

- Realm `uDocket` hosts clients `staff-ui`, `client-portal`, `service-api`, `guardian`, `signer`, `settings`, `notifications`, `llm-registry`, `reference-manager`, `lpe`; the legacy `reference` client remains read-only until LPE decomm.  
- Roles split into realm (`sysadmin`, `auditor`) and org scope (`org_admin`, `org_manager`, `org_operator`, `org_reviewer`, `org_external_counsel`, `org_client`). Tokens include `org_ids[]`, `active_org_id`, `active_org_roles[]`, optional `org_directory[]`; middleware rejects requests when `active_org_id ∉ org_ids[]`.  
- Token lifetimes: access ≤ 15 min (staff/portal), refresh 12 h (staff) / 2 h (portal); offline tokens disabled unless a waiver is logged. OIDC `acr` claims signal step-up MFA.  
- Org switching forces re-auth to mint a token bound to the new org; impersonation headers are forbidden.  
- Availability: Keycloak runs active-active across zones with Galera-backed MariaDB or Aurora Postgres; hourly exports keep warm-standby replicas in sync and Envoy drains unhealthy pods automatically.  
- Federation: Azure Entra ID, Okta, Ping, ADFS supported via identity brokering. Automated lint enforces MFA assurance, signed assertions, SCIM provisioning, and residency prerequisites before activation.  
- Emergency access: failure of an external IdP flips `identity.org.{org_id}.primary_idp=keycloak` with dual approval and `RB-IDP-FAILOVER`; Keycloak failover promotes the warm standby without relaxing policy.

### 3.2 Internal Interfaces (binding)

- Middleware applies per-request context (`set_config`) so Postgres sessions inherit org/user/role GUCs before executing queries; `rls_context_assert` guards block queries lacking context.  
- Session manager binds tokens to device fingerprints (UA hash + IP prefix) and enforces Settings `security.session.device_bind.*` knobs; hard mode terminates mismatches, soft mode logs and throttles.  
- Watchdog jobs (`ops/scripts/identity/watch_device_fingerprint.py`) reconcile device mismatch counts, break-glass expiries, and federation lint results, emitting SSE warnings to the UI.  
- PgBouncer health probe `/healthz/pgbouncer-mode` asserts pooling remains `transaction` or approved `session` so per-request GUCs stay intact.

## 4) State Management (binding)

**Purpose:** Maintain the data structures that enforce authorization, masking, and break-glass controls. **|**
**Contract:** `udocket_can` and masking profiles are the single sources of truth; secure views and vault state must remain aligned with Settings bundles. **|**
**State:** `organization`, `case`, `case_member`, `effective_permission`, `field_mask_rule`, secure views, masking vault, break-glass ledger. **|**
**Failures & handling:** Drift or unauthorized changes route through `RB-RLS-CONTEXT`, `RB-MASK`, or `RB-BREAK-GLASS`. **|**
**Observability:** Metrics `rls_context_missing_total`, `masking_transformation_total`, `break_glass_event_total`; dashboards “RLS Context Guards”, “Masking Vault & Profiles”. **|**
**Breadcrumbs:** `packages/udocket_core/permissions/`, `packages/udocket_core/masking/`, migrations under `apps/platform/db/`. **|**
**References:** TDD §4, Appendix J, Settings spec §2.4.

### 4.1 Authorization lattice & data access (binding)

- Tenancy model: `organization` as root, `case.org_id` referencing the tenant. `case_member(user_id, case_id, role)` scopes access (default “own cases”; Settings may widen to “all org cases”).  
- Effective permissions compile from Settings into `effective_permission` and feed `udocket_can` (deny-by-default; only `sysadmin` bypasses).  
- Secure views (`case_secure`, `artifact_secure`, `qa_log_secure`, `delivery_receipt_secure`, …) expose only masked data; `ALTER TABLE ... FORCE ROW LEVEL SECURITY` enforces policies even for table owners.  
- Example policy:

```sql
CREATE POLICY artifact_visibility ON artifact
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND EXISTS (SELECT 1 FROM "case" c WHERE c.id = artifact.case_id)
  AND udocket_can('ARTIFACT', 'read', artifact.case_id, artifact.id, NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true), '')::uuid
  AND udocket_can('ARTIFACT', 'write', artifact.case_id, artifact.id, NULL)
);
```

### 4.2 Masking & break-glass governance (binding)

- Masking modes (redaction, pseudonymization, hashing, partial) render through `udocket_mask` / `udocket_mask_json`; JSON fields accept only REDACT/NULL.  
- Example secure view:

```sql
CREATE OR REPLACE VIEW artifact_secure WITH (security_barrier=true) AS
SELECT id,
       org_id,
       case_id,
       type,
       class,
       status,
       udocket_mask(
         'ARTIFACT',
         'content_uri',
         org_id,
         case_id,
         id,
         content_uri,
         (SELECT mode
            FROM field_mask_rule r
           WHERE r.org_id = artifact.org_id
             AND r.profile = COALESCE(NULLIF(current_setting('udocket.mask_profile', true), ''), 'default')
             AND r.resource = 'ARTIFACT'
             AND r.field = 'content_uri'
           LIMIT 1)
       ) AS content_uri,
       manifest
  FROM artifact;
```

- `field_mask_rule` indexes refresh atomically during Settings activation. Masking vault and detokenization processes log `MASKING_EVENT`.  
- Break-glass events follow `spec/schemas/break_glass_event.schema.json`; weekly audit job enforces retrospectives or blocks releases.

### 4.3 Session & token binding state (binding)

- Device fingerprint: `ua_hash = sha256(lower(user-agent))`, IP normalized (`IPv4 /24`, `IPv6 /48`), `device_fp = sha256(f"{ua_hash}:{ip_prefix}")`. Tokens embed `device_fp`; mismatches force re-auth and alerting.  
- Settings `security.session.device_bind.*` govern prefix sizes and enforcement mode (`soft` vs `hard`); trusted proxies enumerated in `security.session.trusted_proxy_cidrs[]`.  
- Refresh tokens inherit device binding only when explicitly enabled; privilege escalation requires step-up MFA (`security.org_switch.step_up_required=true`).

## 5) Failure Modes (binding)

**Purpose:** Capture primary identity failure scenarios and default remediation. **|**
**Contract:** Guards fail closed; services remain blocked until runbooks complete and evidence is recorded. **|**
**State:** Federation config, session fingerprints, masking vault, break-glass ledger. **|**
**Failures & handling:** Listed below. **|**
**Observability:** Metrics `rls_context_missing_total`, `device_fp_mismatch_total`, `break_glass_event_missing_retrospective_total`, federation lint dashboards. **|**
**Breadcrumbs:** Runbooks `RB-IDP-FAILOVER`, `RB-RLS-CONTEXT`, `RB-DEVICE-FP`, `RB-MASK`, `RB-BREAK-GLASS`. **|**
**References:** Ops runbook catalog, TDD §4.

- IdP outage (org federation) → switch to Keycloak-native auth via `identity.org.{org_id}.primary_idp=keycloak`, execute `RB-IDP-FAILOVER`, notify Security/org admins.  
- Keycloak control-plane degradation → promote warm standby, rotate tokens, verify audit entries before reopening.  
- Federation drift (missing MFA, unsigned responses) → automated lint blocks activation; update IdP metadata and re-run lint before enabling.  
- Missing RLS GUCs → `rls_context_assert` raises, deployment halts; investigate middleware/PgBouncer (`RB-RLS-CONTEXT`).  
- Device fingerprint mismatch surge → terminate sessions, require step-up, review trusted proxies (`RB-DEVICE-FP`).  
- Masking or break-glass violation → alerts `logging_neverlog_violation_total` / `break_glass_event_missing_retrospective_total`, remediate via `RB-MASK` / `RB-BREAK-GLASS`.

## 6) Observability (binding)

**Purpose:** Ensure identity controls remain visible and actionable. **|**
**Contract:** Metrics, dashboards, and synthetic probes listed here must remain enabled; removals require Security + SRE approval. **|**
**State:** Prometheus rules, Grafana dashboards, synthetic jobs, audit logs. **|**
**Failures & handling:** Blind spots entered in retrospectives with follow-up actions. **|**
**Observability:** Metrics/dashboards enumerated below. **|**
**Breadcrumbs:** Monitoring configs `infra/monitoring/identity-prometheus-rules.yaml`, synthetic definitions `synthetics/identity_*`. **|**
**References:** Ops observability standards, Settings spec §2.

- Metrics: `auth_layer_violation_total`, `rls_context_missing_total`, `device_fp_mismatch_total`, `break_glass_event_total`, `masking_transformation_total`, `logging_neverlog_violation_total`.  
- Dashboards: “Identity Posture”, “RLS Context Guards”, “Masking Vault & Profiles”, “Break-Glass Governance”.  
- Synthetic monitors: `synthetics/identity_token_flow.yaml`, `synthetics/rls_context_probe.yaml`, `synthetics/masking_alias_roundtrip.yaml`.  
- Logs: structured `IDENTITY_EVENT`, `AUTH_EVENT`, `MASKING_EVENT`, `BREAK_GLASS_EVENT` containing Settings snapshot hash and device data.

## 7) Security & Compliance (binding)

**Purpose:** Capture regulatory and privacy controls enforced by the identity stack. **|**
**Contract:** FIPS, HIPAA, and residency requirements remain active; waivers recorded in App.O with expiry/remediation. **|**
**State:** Settings bundles (`security.*`, `identity.*`), masking vault, waiver ledger, audit sink. **|**
**Failures & handling:** Breaches open Security incidents and execute the corresponding runbooks before traffic resumes. **|**
**Observability:** Security dashboards, SIEM feeds, audit seal checks. **|**
**Breadcrumbs:** Settings spec, Guardian spec, LPE spec, Security runbooks. **|**
**References:** Appendix O waivers, Appendix Q sub-processors, Security governance docs.

- `security.tls.fips_mode` enforces FIPS ciphers; changes require Security approval and attestation updates.  
- HIPAA mode mandates WebAuthn for privileged roles and HIPAA-specific masking profiles before approvals or portal delivery.  
- “Never log” scrubber prevents sensitive data leakage; violations trigger `logging_neverlog_violation_total`.  
- Residency/masking waivers propagate via LPE/Reference Manager contexts and get stamped into Guardian manifests; expiry alerts block new activations.  
- Immutable audit sink retains identity, masking, and break-glass logs for ≥ 365 days.

## 8) Operational Notes

**Purpose:** Summarize day-2 operations, staffing, alerting, and evidence expectations. **|**
**Contract:** Operational playbooks must stay current; missing evidence blocks releases. **|**
**State:** Rosters, freeze calendars, runbooks, automation evidence (`ops/identity/<date>/`). **|**
**Failures & handling:** Incident triggers map directly to runbooks in §8.3. **|**
**Observability:** PagerDuty analytics, runbook execution tracker, automation reports. **|**
**Breadcrumbs:** Ops catalog, runbooks `docs/src/ops/runbooks/identity/*.md`, automation scripts. **|**
**References:** Ops runbook catalog, Ops governance policies.

### 8.1 Operational Posture (binding)

**Purpose:** Define staffing expectations and readiness posture. **|**
**Contract:** `identity-oncall@` rotation responds within 15 minutes; maintenance windows follow the platform schedule. **|**
**State:** Roster `ops/identity/roster.yaml`, freeze calendar `ops/identity/freeze_windows.ics`, escalation matrix. **|**
**Failures & handling:** Staffing gaps trigger `identity_oncall_gap_total`; releases pause until coverage restored. **|**
**Observability:** PagerDuty analytics, staffing dashboards. **|**
**Breadcrumbs:** Ops governance policies. **|**
**References:** Ops staffing handbook.

### 8.2 Incident Triggers (binding)

**Purpose:** Map monitoring signals to incident response. **|**
**Contract:** Alerts below page the on-call rotation with associated runbooks. **|**
**State:** Prometheus alert rules, PagerDuty services, suppression policies. **|**
**Failures & handling:** False positives reviewed weekly; suppression changes tracked in Ops catalog. **|**
**Observability:** Alert dashboards, PagerDuty reports. **|**
**Breadcrumbs:** Alert definitions in `infra/monitoring/identity-prometheus-rules.yaml`. **|**
**References:** Alert catalog, Ops runbook catalog.

- `auth_layer_violation_total` (critical) → verify HMAC/MFA (`RB-IDP-FAILOVER`).  
- `rls_context_missing_total` spike → inspect middleware/PgBouncer (`RB-RLS-CONTEXT`).  
- `device_fp_mismatch_total` sustained increase → investigate compromised sessions (`RB-DEVICE-FP`).  
- `break_glass_event_missing_retrospective_total` → execute `RB-BREAK-GLASS`.  
- `logging_neverlog_violation_total` → execute `RB-MASK`.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Keep operational playbooks aligned with alerts and exercised on schedule. **|**
**Contract:** Runbooks must exist, link to alerts, and produce evidence per cadence. **|**
**State:** Runbook files, automation outputs `ops/identity/<date>/`. **|**
**Failures & handling:** Missing or stale runbooks block releases until refreshed. **|**
**Observability:** Runbook execution tracker, drill logs. **|**
**Breadcrumbs:** Ops catalog, automation scripts. **|**
**References:** Ops runbook catalog, drill tracker.

#### 8.3.1 Runbook Index (informative)

| Signal / Scenario | Runbook | Notes |
| --- | --- | --- |
| IdP outage / federation drift | `RB-IDP-FAILOVER` | Switch to Keycloak-native auth, rollback steps |
| RLS context failures | `RB-RLS-CONTEXT` | Middleware/PgBouncer remediation |
| Device fingerprint surge | `RB-DEVICE-FP` | Rotate tokens, update trusted proxies |
| Masking violation | `RB-MASK` | Detokenization audit and remediation |
| Break-glass governance gap | `RB-BREAK-GLASS` | Close events, capture retrospectives |

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarize the critical runbooks responders execute during incidents. **|**
**Contract:** Each runbook must remain current and linked from alert definitions. **|**
**State:** Runbook Markdown files, automation scripts, evidence directories. **|**
**Failures & handling:** Gaps discovered during drills trigger immediate updates and retrospective notes. **|**
**Observability:** Runbook execution tracker, drill reports. **|**
**Breadcrumbs:** Ops runbook catalog (`docs/src/ops/runbooks/identity/*.md`). **|**
**References:** Ops runbook catalog, incident retrospectives.

- `RB-IDP-FAILOVER` — federation failover/rollback with evidence capture.  
- `RB-RLS-CONTEXT` — diagnose missing GUCs or pooling drift.  
- `RB-DEVICE-FP` — investigate compromised sessions, rotate credentials.  
- `RB-MASK` — remediate PII leakage, update scrubber coverage.  
- `RB-BREAK-GLASS` — dual approval workflow, retrospective documentation.

#### 8.3.3 Drill Cadence & Evidence (informative)

- Quarterly drills cover IdP failover, RLS failure, and masking breach; evidence stored under `ops/identity/drills/<date>/`.  
- Automation validates runbook execution dates each release; failures raise `identity_runbook_outdated_total`.

### 8.4 Migrations & Backfills (informative)

**Purpose:** Capture schema/config changes that impact identity systems. **|**
**Contract:** Realm or database migrations require change approval, staging dry-run, and signed artifacts. **|**
**State:** Keycloak export diffs, database migrations (`apps/platform/db/migrations/*`), change tickets. **|**
**Failures & handling:** Failed migrations roll back via `RB-RLS-CONTEXT`; releases pause until reconciliation completes. **|**
**Observability:** Migration dashboard, Flux change reports. **|**
**Breadcrumbs:** Keycloak export automation, migration scripts, change tickets. **|**
**References:** Ops change-management policy, Settings activation procedures.

### 8.5 Operational Workflows (informative)

**Purpose:** Track recurring tasks (lint, audits, retrospectives). **|**
**Contract:** Workflows produce evidence stored in `ops/identity/<date>/`; missed runs block releases. **|**
**State:** Checklists for federation lint, masking audit, break-glass review. **|**
**Failures & handling:** Missed workflows generate backlog tickets and escalations. **|**
**Observability:** Workflow completion dashboard, audit logs. **|**
**Breadcrumbs:** Workflow documentation, automation scripts, staffing rosters. **|**
**References:** Ops governance policies, workflow checklists.

- Weekly federation lint review.  
- Monthly masking vault audit and break-glass retrospective verification.  
- Quarterly review of trusted proxy CIDRs and device binding thresholds.

## 9) Dependencies

**Purpose:** Identify upstream/downstream systems the identity stack relies on. **|**
**Contract:** Dependency changes must coordinate with identity owners and update this spec. **|**
**State:** Keycloak realm exports, Settings bundles, residency/masking catalogs, runbooks. **|**
**Failures & handling:** Dependency regressions trigger §5 runbooks. **|**
**Observability:** Dependency health dashboards, lint pipelines. **|**
**Breadcrumbs:** Referenced service specifications. **|**
**References:** Settings spec, LPE spec, Reference Manager spec, Worker Cluster spec.

| Dependency | Role | Notes |
| --- | --- | --- |
| Keycloak | Identity provider and token issuer | Realm config, federation, token lifetime management |
| Settings Registry | Stores identity/session/TLS policy knobs (`security.*`, `identity.*`) | Activation pipeline validates bounds |
| Guardian | Relies on masking and waiver metadata for verdict gating | Guardian policies log break-glass usage |
| Worker Cluster | Executes watchdog jobs (residency/masking/device) | Publishes SSE warnings to UI |
| Localization & Policy Engine | Provides masking profile metadata and residency contexts | Context digest embedded in manifests |
| Reference Manager | Supplies IdP lint metadata and residency catalogs | Powers federation lint automation |

## 10) References

- TDD §4 Identity, tenancy & access control (summary).  
- Settings Registry specification — `../services/settings.md`.  
- Guardian specification — `../services/guardian.md`.  
- Worker Cluster specification — `../services/worker-cluster.md`.  
- Ops runbook catalog — `../ops/runbooks/index.md`.
