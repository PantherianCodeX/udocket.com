# **uDocket — Technical Description Document (TDD v7 Outline)**

**Audience:** Engineering, Security, QA, Ops, Product  
**Purpose:** Target outline for the next major TDD revision. Optimized for fast LLM parsing (stable identifiers, shallow nesting) and for human navigation during reviews.

---

## Document controls
| Field | Value |
| --- | --- |
| Version | 0.1-draft |
| Status | In review (content parity achieved; awaiting Architecture/Security approvals) |
| Last updated | 2025-10-19 |
| Primary owners | Platform Architecture, Security Engineering |
| Migration plan | Supersede prior TDD versions once Architecture/Security approvals are recorded (parity verified 2025-10-19) |
| Docs validation | `python scripts/docs/lint_docs.py` (see `docs/README.md` for tooling) |

---

## 0) Reading guide
- **Scope:** Entire platform lifecycle (design → operations → governance).  
- **Structure:** Numbered sections with ≤3 levels of depth; appendices mirror section numbers for reference artifacts.  
- **Cross-references:** Use `§<number>` for sections and `App.<letter>` for appendices.  
- **LLM hint:** Each subsection starts with a one-line purpose statement before implementation details.
- **Maintenance:** Run `python scripts/docs/lint_docs.py` (or see `docs/README.md`) before submitting edits to keep references, formatting, and settings keys synchronized with the codebase.

---

## 1) Executive summary

### 1.1 Mission & problem statement
*Purpose: State why uDocket exists and which pain points it solves.*
- Deliver a secure, auditable case automation platform that converts unstructured inputs (audio, exhibits, staff notes) into consumable legal artifacts without sacrificing compliance.
- Replace ad hoc transcription and summarization processes that lack residency controls, approval gating, or defensible audit trails.
- Empower multidisciplinary users (intake, operators, reviewers, counsel) with coordinated workflows backed by deterministic settings and artifacts.

### 1.2 Solution overview
*Purpose: Summarize the end-to-end approach at one glance.*
- Web platform (Django + Channels) for staff/clients, Celery workers for long-running jobs, and dedicated Guardian & Signing services enforcing READY/QUARANTINED and digital seal policies.
- Agent pipeline: Transcribe → Analyze → Compose, each producing immutable artifacts under Guardian review, enriched with manifests and ops telemetry.
- Zero-trust foundation: mTLS between services, Postgres RLS with policy-driven RBAC, object storage with SHA-256 integrity, and centralized Settings snapshots for every job.

### 1.3 Out-of-scope items
*Purpose: Clarify boundaries to prevent scope creep.*
- No generic e-discovery, enterprise DMS migration tooling, or third-party redaction services; integrations focus on Azure Speech, selected LLM providers, and in-house signing.
- Hardware devices, telephony capture, and in-person interview tooling remain outside MVP scope (ingest assumes digital uploads).
- Non-Canadian speech regions and unrestricted LLM model bring-your-own configurations are disabled pending future waivers.

### 1.4 Success metrics & KPIs
*Purpose: Define measurable signals for program health.*
- `transcription_cycle_time` ≤ 30 minutes P95 for batch jobs (case-ready transcript).
- ≥ 95% Guardian pass rate on first submission with < 1% false negatives per quarter.
- FinOps: LLM spend per case maintained within org-defined monthly caps; ≥ 90% forecast accuracy.
- Platform reliability: Web/worker availability ≥ 99.5%, no Sev-1 incidents triggered by residency or RBAC violations.

### 1.5 Document readers & decision checkpoints
*Purpose: Identify stakeholders and when they must engage.*
- **Architecture & Security:** approve changes to principles, Guardian rules, and Settings service contracts.
- **Engineering leads:** align sprint plans with agent, API, and storage sections; sign off before major releases.
- **Product & Ops:** review executive summary and operations sections before customer onboarding waves.
- Trigger checkpoints: pre-production launch, regulator readiness reviews, significant provider changes, or artifact schema revisions.
- RACI assignments for each domain live in App.S and govern who signs off on changes or exceptions.

- **Source material:** `§1`, `§35` overview blurbs  
- **Priority:** High (front-matter defines narrative used by PRD/TDD consumers)

### 1.6 Customer-facing SLAs
*Purpose: Publish external commitments distinct from internal SLOs and make escalation paths obvious to buyers and auditors.*
- **Availability:** 99.5 % rolling 30 day for staff UI/API; 99.0 % for client portal. Breaches trigger customer notice within 24 h and a public incident postmortem within 5 business days (`App.H` templates).
- **Support response:** Severity 1 (production outage/legal exposure) acknowledged ≤ 1 hour, mitigated or workaround shared ≤ 4 hours; Sev 2 ≤ 4 hour acknowledgement, Sev 3/4 within one business day. Support queue owned by Platform Support with SRE on-call backup.
- **Restore targets:** RTO ≤ 1 hour for Postgres/object storage (see §12.4) and ≤ 4 hours for Guardian/Signer; RPO ≤ 15 minutes. Manual fallback playbooks in §12.10 describe degraded operations while restoration proceeds.
- **Escalation:** Customer SLA breaches escalate to Duty Manager + SRE on-call + Product within 30 minutes; regulators and contractual stakeholders notified per §12.3 templates. Decision log entries capture SLA breaches and remediation commitments (§15.3).

---

## 2) Core principles & constraints

### 2.1 Guiding principles (immutability, determinism, zero-trust)
*Purpose: Anchor architecture decisions to explicit tenets.*
- Artifacts are immutable, content-addressed, and versioned; human approvals elevate READY → APPROVED.
- Guardian gating: the Guardian service is the decision authority for READY/QUARANTINED; downstream stages accept APPROVED artifacts only.
- Deterministic controls over non-deterministic LLM output: UUIDv7 row IDs, UUIDv8 derived IDs (HMAC-based per §6.7), Settings snapshots, prompt/version capture.
- Zero-trust for every hop: deny-by-default RBAC, workload identities, enforced mTLS, and per-request DB GUC binding.
- Observability and auditability as first-class: every job/action emits structured telemetry with correlation IDs.
- Settings as a platform: a centralized Settings Service defines effective configuration (system/org/case), is versioned/audited, and snapshots embed into every job.
- Operational safety defaults: database sessions pin `search_path`, enforce timeouts, and fail closed when required RLS GUCs are missing.
- Real-time transport policy: SSE for one-way server→client status, Channels for bidirectional collaboration and controls.

### 2.2 Regulatory & contractual constraints (Canada residency, SOC2, privacy)
*Purpose: Spell out compliance rails enforced across the stack.*
- Data residency: compute and storage restricted to canadacentral/canadaeast; cross-region requires dual-approved waiver stamped in manifests.
- SOC 2 / ISO controls: change management, incident response, and logging mapped to specific sections (`§20`, `§24`, `App.E`).
- Privacy commitments: DPIA/RoPA artifacts, entity masking, retention baselines, HIPAA override mode (stricter access + retention).
- HIPAA override mode: disabled by default (`privacy.hipaa.enabled=false`). When enabled, enforces per-org field encryption (`security.field_encryption.enabled=true`, `security.field_encryption.key_scope='per_org'`), requires WebAuthn for privileged roles (`security.mfa.webauthn_required_roles` includes `org_admin|org_manager|org_operator|org_reviewer`), blocks evidence-store prompt excerpts (`evidence_store.redacted_excerpts.enabled=false`), shortens retention windows (Appendix C), and disallows portal delivery of PHI-tagged attachments unless a waiver is recorded. Uploads carrying `PHI=true` are rejected with `POLICY_BLOCK` when HIPAA mode is off.
- The `PHI=true` marker is collected at upload via a staff-facing “Contains PHI” toggle (default false) and may also be asserted by the post-upload classifier; both paths write the flag to artifact metadata. If a downstream classifier later upgrades an artifact to PHI while HIPAA mode is disabled, the artifact is retro-quarantined, downstream approvals are invalidated, and portal links are revoked until an organization enables HIPAA mode or files a waiver.
- Rationale: the platform blocks PHI ingestion unless an org explicitly enables HIPAA mode, preventing accidental handling outside approved compliance footing.
- Legal hold and destruction policies align with jurisdictional obligations captured in Appendix C.
- Audit linkage: DPIA/RoPA records referenced in audit seals (`§14.2`, Appendix N); HIPAA override activations require Compliance approval and manifest tagging.

### 2.3 Non-functional requirements (SLOs, latency budgets, availability)
*Purpose: Capture performance and reliability expectations.*
- Guardian decisions ≤ 5 minutes P95; Compose jobs complete ≤ 45 minutes P95 under nominal load.
- Service availability: web/channels 99.5%, Guardian 99.9%, Settings API 99.9% (due to policy enforcement criticality).
- Latency targets: SSE job progress updates < 1s lag; artifact download start < 500ms for approved documents.
- Error budgets tie directly to deploy gates (`§41.7`)—breaches block releases until burn rate stabilizes.

### 2.4 Assumptions & dependencies
*Purpose: Make explicit the foundational inputs the solution relies on.*
- Identity provider: Keycloak with Organizations feature remains authoritative; no secondary IdP fallback.
- Cloud dependencies: Azure Speech (Canada), Azure Blob/S3-compatible storage with versioning, managed Redis/Postgres.
- DevOps baseline: Kubernetes with mesh or workload identity capable of enforcing strict mTLS and egress controls.
- Client orgs commit to providing language/region selections that map to policy allowlists; Settings activation enforces this.

- **Source material:** `§1.1`, `§2`, `§29`, `§34`, `§41`  
- **Priority:** High (feeds platform policies, approval reviews)

---

## 3) Platform architecture overview

### 3.1 High-level system context diagram
*Purpose: Orient readers to major components and trust boundaries before diving into detail.*
- Staff users, reviewers, and clients interact with the **Web App** (Django ASGI) via browser connections protected by TLS 1.3; SSE provides status streaming while Channels enables bidirectional collaboration. SSE payloads include only IDs and metadata already permitted by RLS—no raw PII or artifact bodies traverse the channel.
- Background processing occurs in the **Worker cluster** (Celery) which orchestrates agent pipelines, storage operations, and notifications.
- Supporting services—**Guardian**, **Digital Signer**, **Settings**, **LLM Registry**, **Reference Engine**, and **Notifications**—communicate over mTLS within the cluster and persist state to Postgres with RLS.
- External dependencies (Azure Speech, LLM providers, TSA/OCSP authorities, email/SMS gateways) sit outside the trusted cluster and are accessed under strict egress policies.  
- Visual: see `App.A` for the full context diagram and sequence overlays.

### 3.2 Deployment topology (environments, Kubernetes primitives)
*Purpose: Capture the runtime footprint and security guardrails applied per environment.*
- Kubernetes namespaces per environment (`dev`, `staging`, `prod`, `audit`) host Deployments for `web`, `channels`, `workers`, `guardian`, `signer`, `llm-registry`, `reference`, `notifications`, `settings`, ingress controllers, Redis broker/cache, and object-storage sidecars.
- Service mesh or SPIFFE/SPIRE workload identity enforces strict mTLS; certificates rotate with TTL ≤ 24h and SLO of 99.9% renewals within five minutes of expiry. Certificates that exceed `security.tls.cert_ttl_minutes + 5` minutes trigger a hard fail (traffic denied) and page on-call; soft warnings fire 30 minutes before TTL expiry to allow proactive rotation.
- Network policy: ingress terminates TLS (TLS 1.3 preferred; limited TLS 1.2 fallback). Egress is default-deny aside from kube-dns and the Istio egress gateway; the gateway enforces the Canadian Azure and third-party allowlists rendered from the `network.egress.allowed_hosts` Settings bundle, and drift detection nightly resolves each FQDN (e.g., `*.blob.core.windows.net`, `*.table.core.windows.net`, `*.queue.core.windows.net`, TSA/OCSP hosts) to compare against SAN lists.
- TLS details: allowed ciphers `TLS_AES_128_GCM_SHA256`, `TLS_AES_256_GCM_SHA384`, `ECDHE-ECDSA-AES128-GCM-SHA256`, `ECDHE-RSA-AES128-GCM-SHA256`; OCSP stapling enabled on ingress. TLS 1.2 fallback is restricted to a FIPS-aligned profile `{'ECDHE-ECDSA-AES128-GCM-SHA256','ECDHE-RSA-AES128-GCM-SHA256','ECDHE-ECDSA-AES256-GCM-SHA384','ECDHE-RSA-AES256-GCM-SHA384'}` and may only be enabled via `security.tls.legacy_exceptions[]` entries that include endpoint name, justification, and expiry. CHACHA20-Poly1305 is supported only under TLS 1.3, satisfying mobile performance needs without weakening the FIPS posture.
- Platform services leverage managed secrets (Vault or Azure Key Vault). Nodes run chrony/NTP with ±100 ms drift to support TSA validation. Redis handles broker/cache needs; Postgres (regional HA) stores relational data.
- Object storage: Azure Blob (prod) or S3-compatible (dev) buckets configured for versioning, SSE-KMS, and immutable retention for audit sinks.

#### 3.2.1 Policy manifests (illustrative)
*Purpose: Show concrete Kubernetes/service-mesh policies to enforce topology constraints.*

AuthorizationPolicy (Istio)
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata: { name: mesh-egress-allowlist, namespace: platform }
spec:
  action: ALLOW
  rules:
    - to:
        - operation:
            hosts: ["*.canadacentral.azure.com", "*.canadaeast.azure.com"]
    - to:
        - operation:
            hosts: ["tsa.example.ca", "ocsp.example.ca"]
```
- Illustrative host list; production values are rendered from the `network.egress.allowed_hosts` Settings bundle (SYSTEM scope) so environments stay in lockstep with approved endpoints.

NetworkPolicy (Kubernetes)
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: mesh-egress-baseline, namespace: platform }
spec:
  podSelector: { matchLabels: { mesh: enabled } }
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector: { matchLabels: { kube-system: "true" } }
          podSelector: { matchLabels: { k8s-app: kube-dns } }
      ports:
        - protocol: UDP
          port: 53
    - to:
        - namespaceSelector: { matchLabels: { istio: control-plane } }
          podSelector: { matchLabels: { app: istio-egressgateway } }
    # External destinations are mediated by the service mesh AuthorizationPolicy allowlist.
```

AdmissionPolicy (prevent PgBouncer statement pooling)
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata: { name: deny-statement-pooling }
spec:
  rules:
    - name: block-statement-pooling
      match: { resources: { kinds: ["Deployment"], namespaces: ["platform"] } }
      validate:
        message: "PgBouncer must not use statement pooling"
        foreach:
          - list: "spec/template/spec/containers"
            preconditions:
              - key: "{{ element.name }}"
                operator: Equals
                value: pgbouncer
            deny:
              conditions:
                - key: "{{ element.env[?name=='POOL_MODE'].value | default('session') }}"
                  operator: Equals
                  value: statement
```
- PgBouncer is permitted to run only in `transaction` (default) or `session` pooling modes as published through the `db.pgbouncer.pool_mode` Setting; statement pooling remains blocked to preserve per-request GUCs. Workers and web pods expose a `/healthz/pgbouncer-mode` probe that executes `SHOW pool_mode` via PgBouncer admin and fails closed if the reported mode drifts from the allowlist, aligning with §4.4 RLS guarantees.

Ingress TLS policy (snippet)
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: platform
  annotations:
    nginx.ingress.kubernetes.io/ssl-protocols: "TLSv1.3 TLSv1.2"
    nginx.ingress.kubernetes.io/ssl-ciphers: "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
``` 
- TLS 1.3 cipher suites are implicit; the annotation lists only the TLS 1.2 fallback suites the gateway permits.
- Authoritative TLS policy is driven by `security.tls.min_version` (default `TLSv1.3`) and `security.tls.cipher_profile` Settings bundles; any TLS 1.2 exposure must be explicitly listed in `security.tls.legacy_exceptions[]` with documented review and expiry. Mesh and ingress templates consume the same settings so routing surfaces stay consistent.

Pod Security Admission (namespace labels)
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: platform
  labels:
    pod-security.kubernetes.io/enforce: "restricted"
    pod-security.kubernetes.io/enforce-version: "latest"
```

### 3.3 Service inventory table (role, tech stack, scaling)
*Purpose: Provide a tabular summary for capacity planning and onboarding.*

| Service | Runtime | Responsibilities | Scaling & notes | Observability anchors |
| --- | --- | --- | --- | --- |
| Web | Django ASGI (uvicorn + gunicorn) | REST APIs, staff UI, client portal, SSE endpoints, approval workflows | HPA on CPU+request latency; sticky sessions avoided | `web_http_*`, `frontend_latency_seconds`, `audit_event_total` |
| Channels | Django Channels (Redis-backed) | Real-time editors, approvals, QA feedback | Separate Deployment with autoscale on WS connections | `channels_active_connections`, `channels_msg_latency_seconds` |
| Workers | Celery (prefork) | Media normalization, agent orchestration, notifications, ingestion, destruction | Queue length auto-scaling; dedicated queues per agent class | `celery_queue_depth`, `job_duration_seconds`, `task_retry_total` |
| Guardian | FastAPI | Artifact READY/QUARANTINED decisions, policy evaluation, audit history | Pod HPA on latency; 99.9% SLO | `guardian_decision_latency_seconds`, `guardian_ready_ratio` |
| Digital Signer | FastAPI | PDF/A signing, OCSP/CRL/TSA validation, bundle creation | Scales with signing queues; relies on KMS/TSA connectors | `signer_request_latency_seconds`, `tsa_drift_seconds` |
| LLM Registry | FastAPI | Provider catalog, health probes, token accounting, fallback logic | Low QPS; run ≥2 replicas | `llm_provider_health`, `llm_circuit_state` |
| Settings Service | FastAPI | Hierarchical settings APIs, bundle activation, diff previews | Autoscale on QPS; Redis pub/sub for cache invalidation | `settings_activation_total`, `settings_cache_hit_ratio` |
| Reference Engine | FastAPI + worker cron | International court catalogs, validators, questionnaires | Scheduled updates; horizontal scale minimal | `reference_sync_duration_seconds`, `catalog_version` |
| Notification Service | Celery beat + worker | Outbox delivery (email/SMS/in-app), receipt tracking | Scales with delivery volume; provider specific adapters | `delivery_success_ratio`, `delivery_retry_total` |
| Storage adapters | Sidecar / init jobs | Object storage integrity checks, audio normalization caching | Scoped per namespace | `storage_hash_mismatch_total`, `object_store_latency_seconds` |

- **Stack note:** Web and Channels services run on Django 5.2 with ASGI deployment (uvicorn + gunicorn) and Django Channels 4.x; dependencies pinned in `apps/platform/requirements.txt`.

### 3.4 Data flows between services
*Purpose: Describe the critical sequences that tie services together.*
- **Upload → Guardian → Approval:** Web accepts uploads, stages to object storage, inserts DRAFT artifacts, calls Guardian for readiness, then surfaces for reviewer approval (sequence in `App.A.2`).
- **Agent pipeline:** Workers fetch inputs (audio/transcripts), execute Transcribe/Analyze/Compose stages, write artifacts + manifests, and notify Guardian & SSE. Settings snapshots travel alongside each job to guarantee reproducibility.
- **Notification loop:** Worker pushes delivery requests to Notification Service; receipts update artifact manifests and audit events. Portal fetches approved deliverables via signed URLs with guardian-enforced readiness.
- **Telemetry stream:** All services emit logs/metrics/traces to the Observability Fabric (Elastic/OTel stack). Guardian decisions and settings activations append to ops audit JSONL under each case.
- **Settings change propagation:** Activations in Settings Service publish invalidation events; consuming services flush caches and rehydrate GUC policies on next request/task.

### 3.5 External integrations (Azure Speech, LLM providers, TSA/OCSP)
*Purpose: Catalog regulated touchpoints subject to policy and audit.*
- **Azure Speech (canadacentral/canadaeast):** Batch transcription via SAS URLs and on-demand streaming; operations include hashing uploads, enforcing PCM normalization, and monitoring quotas.
- **LLM providers:** Restricted to org-approved regions and models; Selection algorithm honors `fallback_priority`. Evidence store records prompts, redaction metrics, and envelope metadata per call.
- **Digital trust services:** TSA and OCSP/CRL endpoints defined in settings (`sign.trust_roots[]`); signer enforces drift ≤ ±5s and caches responses ≤12h.
- **Notification channels:** Email/SMS providers configured per organization; webhook adapters log request/response pairs with PII masking.
- **Reference Engine:** Maintains international court catalogs with localized labels, validator rules, and questionnaire templates; scheduled sync jobs update per jurisdiction and publish catalog versions for downstream services.
- **Optional analytics sinks:** Metrics exported to Grafana/Prometheus; FinOps dashboards consume cost metrics for monthly guardrails.
- Sub-processor directory: see App.Q for approved vendors, residency posture, and DPA commitments.

- **Source material:** `§1.2`, `§1.3`, `App.A`, `§3`, `§24`  
- **Priority:** High (core architecture reference)

---

### 3.6 Region allowlist enforcement & egress policies (binding)
*Purpose: Enforce Canada-only compute/storage and control outbound traffic to providers.*
- Settings define allowlists per org: `regions.allowlist.compute = ['canadacentral','canadaeast']`, `regions.allowlist.storage = ['canadacentral','canadaeast']`. Activation lints reject disallowed regions.
- Network layer: Kubernetes `NetworkPolicy`/service mesh `AuthorizationPolicy` denies egress to non-allowlisted CIDRs/hostnames; provider endpoints pinned by FQDN and SAN match with mTLS.
- Providers: Azure Speech endpoints restricted to Canadian regions; LLM runtime filters models by allowed regions before selection; cross-region requires dual-approved waiver stamped in manifests and Guardian rules log.
- Storage: object buckets created in approved regions; replication outside allowlist disabled unless waiver present; replication metadata recorded in manifests.
- Drift detection: nightly job resolves each configured host, validates SAN entries against `network.egress.allowed_hosts`, and compares resulting CIDRs to the allowlist; deviations alert and auto-disable offending endpoints.
- Telemetry: `residency_block_total` increments on blocks; audit records include `RESIDENCY_POLICY_BLOCK` reason and settings snapshot hash.

---

## 4) Identity, tenancy & access control

### 4.1 AuthN provider (Keycloak) and realm configuration
*Purpose: Define the identity backbone and token contract consumed by all services.*
- Realm `udocket` with clients `staff-ui`, `client-portal`, `service-api`, `guardian`, `signer`, `settings`, `notifications`, `llm-registry`, `reference`.
- Roles split into realm (`sysadmin`, `auditor`) and organization scope (`org_admin`, `org_manager`, `org_operator`, `org_reviewer`, `org_external_counsel`, `org_client`).
- Tokens include `org_ids[]`, `active_org_id`, `active_org_roles[]`, optional `org_directory[]`. Middleware rejects any request where `active_org_id ∉ org_ids[]`.
- Access tokens ≤15 minutes, refresh tokens 12h (staff) / 2h (portal); offline tokens disabled unless security approves exceptions. Step-up MFA signaled via OIDC `acr` claim for sensitive endpoints.
- Login flow for org switching triggers re-authentication to mint new tokens bound to the selected organization—no custom headers for impersonation allowed.

### 4.2 Org/case membership model and RBAC lattice
*Purpose: Explain how authorization decisions resolve across org and case scopes.*
- `organization` table is the root tenant; `case` rows reference `org_id`. Users gain visibility through Keycloak Organizations; the platform mirrors minimal metadata for labels.
- `case_member(user_id, case_id, role)` narrows access within an organization; default operator scope is “own cases.” Org settings can widen to “all org cases” with policy approval.
- Effective permissions compile from Settings bundles into `effective_permission` (resource/action/role/field). `udocket_can(...)` function enforces deny-by-default, with only `sysadmin` realm role as hardcoded bypass.
- Policies drive field-level allowances (`field_mask_rule`) and exclusivity (e.g., artifact types). Settings activation pipeline validates coverage before publishing changes.

### 4.3 Session management & token binding
*Purpose: Prevent token misuse and session fixation across services and clients.*
- Middleware sets per-request context (`active_org_id`, `active_user`, roles) and stores them via `set_config(..., true)` to bind DB sessions. Missing context triggers 403 with `RLS_CONTEXT_MISSING`.
- Access tokens bind to device fingerprint hashes; switching orgs invalidates active SSE/WebSocket connections to prevent cross-org leakage.
- Device fingerprint derivation (binding): `ua_hash = sha256(lower(user-agent))`, IP normalized (`IPv4 /24`, `IPv6 /48`), `device_fp = sha256(f\"{ua_hash}:{ip_prefix}\")`; tokens carry `device_fp` claim and mismatches trigger re-auth/step-up flows.
- Org settings `security.session.device_bind.ip_prefix_len_v4|ip_prefix_len_v6` control those prefix lengths (defaults `/24` and `/48`); mobile-heavy orgs may widen prefixes to reduce unnecessary prompts while retaining auditability. Behind trusted corporate NATs or CDN proxies the IP prefix is treated as a *soft* signal (enforced only when `security.session.device_bind.enforce_ip=true`); WebAuthn and per-device secrets remain the authoritative binders for privileged access, and ingress trusts `X-Forwarded-For` only from mesh-managed gateway CIDRs declared in `security.session.trusted_proxy_cidrs[]`.
- Refresh tokens are device-bound when enabled per org policy; defaults disable long-lived offline tokens except where Security approves exceptions.
- Break-glass endpoints require step-up MFA, justification, and explicit expiry; generated `BreakGlassEvent` audited for post-hoc review.
- Org switch to higher privileges defaults to requiring step-up MFA (`security.org_switch.step_up_required=true`), overridable only with documented risk acceptance.
- HIPAA mode extends step-up MFA by enforcing WebAuthn for privileged roles (`security.mfa.webauthn_required_roles`) before approvals or portal deliveries touching HIPAA-classed artifacts.

### 4.4 Database RLS and GUC enforcement
*Purpose: Describe how data-layer access rules enforce the same contract as the API tier.*
- All tenant tables carry `org_id`; Postgres RLS policies require per-connection GUCs (`udocket.active_org`, `active_user`, `active_roles`, `realm_roles`, `operator_scope`).
- Helper functions (`udocket_has_realm_role`, `udocket_is_case_member`, `udocket_can`) centralize policy evaluation. Any query without GUC setup is denied; the `/healthz/pgbouncer-mode` probe confirms PgBouncer stays in approved `transaction` or `session` pooling modes (statement pooling remains blocked) so per-request GUCs remain intact.
- Secure views (`*_secure`) act as the only read surfaces; application role lacks direct SELECT on base tables. CI lints ensure ORM queries reference views, and production deployments rely on compiled helper tables (e.g., `field_mask_rule_effective`) to avoid per-row subqueries inside those views.
- Advisory locks (`udlock` schema) encapsulate concurrency primitives with heartbeat registries and GC routines.

- Normative SQL (binding):

```sql
-- Policy tables (compiled by Settings activation job)
-- effective_permission(org_id, resource, action, role, field NULLABLE)
-- field_mask_rule(org_id, resource, field, mask, allowed_role)

-- Central allow function (deny-by-default; sysadmin bypass)
CREATE OR REPLACE FUNCTION udocket_can(
  p_resource text,
  p_action   text,
  p_case     uuid,
  p_artifact uuid,
  p_field    text DEFAULT NULL
)
RETURNS boolean
LANGUAGE plpgsql STABLE AS $$
DECLARE v_org   uuid := NULLIF(current_setting('udocket.active_org',   true), '')::uuid;
DECLARE v_roles text := coalesce(current_setting('udocket.active_roles', true),'');
DECLARE v_scope text := coalesce(current_setting('udocket.operator_scope', true),'own_cases');
DECLARE r text;
BEGIN
  IF udocket_has_realm_role('sysadmin') THEN RETURN true; END IF;
  IF v_org IS NULL THEN RETURN false; END IF;

  -- Enforce operator scope: when scoped to own_cases and a case is in play,
  -- deny if caller is not a member (realm sysadmin already handled above)
  IF p_case IS NOT NULL AND v_scope <> 'all_org_cases' THEN
    IF NOT udocket_is_case_member(p_case) THEN
      RETURN false;
    END IF;
  END IF;

  FOR r IN SELECT regexp_split_to_table(v_roles, ',') LOOP
    IF EXISTS (
      SELECT 1
        FROM effective_permission ep
       WHERE ep.org_id = v_org
         AND ep.resource = p_resource
         AND ep.action   = p_action
         AND ep.role     = r
         AND (
              (ep.field IS NULL AND p_field IS NULL)
           OR (ep.field IS NOT NULL AND ep.field = p_field)
         )
    ) THEN
      RETURN true;
    END IF;
  END LOOP;
  RETURN false;
END $$;

-- RLS policies rewritten to use settings-driven `udocket_can`
DROP POLICY IF EXISTS case_visibility ON "case";
CREATE POLICY case_visibility ON "case"
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('CASE','read',"case".id,NULL,NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('CASE','write',"case".id,NULL,NULL)
);

DROP POLICY IF EXISTS artifact_visibility ON artifact;
CREATE POLICY artifact_visibility ON artifact
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND EXISTS (SELECT 1 FROM "case" c WHERE c.id = artifact.case_id)
  AND udocket_can('ARTIFACT','read',artifact.case_id,artifact.id,NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('ARTIFACT','write',artifact.case_id,artifact.id,NULL)
);

DROP POLICY IF EXISTS job_vis ON job;
CREATE POLICY job_vis ON job
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND EXISTS (SELECT 1 FROM "case" c WHERE c.id = job.case_id)
  AND udocket_can('JOB','read',job.case_id,NULL,NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('JOB','write',job.case_id,NULL,NULL)
);

DROP POLICY IF EXISTS qa_vis ON qa_log;
CREATE POLICY qa_vis ON qa_log
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND EXISTS (SELECT 1 FROM "case" c WHERE c.id = qa_log.case_id)
  AND udocket_can('QA_LOG','read',qa_log.case_id,NULL,NULL)
);

DROP POLICY IF EXISTS gdh_vis ON guardian_decision_history;
CREATE POLICY gdh_vis ON guardian_decision_history
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND EXISTS (
    SELECT 1
      FROM artifact a
      JOIN "case" c ON c.id = a.case_id
     WHERE a.id = guardian_decision_history.artifact_id
       AND udocket_can('GUARDIAN_DECISION','read', c.id, a.id, NULL)
  )
);

DROP POLICY IF EXISTS delivery_vis ON delivery_receipt;
CREATE POLICY delivery_vis ON delivery_receipt
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND EXISTS (
    SELECT 1
      FROM artifact a
      JOIN "case" c ON c.id = a.case_id
     WHERE a.id = delivery_receipt.artifact_id
       AND udocket_can('DELIVERY_RECEIPT','read', c.id, a.id, NULL)
  )
);

-- Enforce RLS even for table owners (unchanged)
ALTER TABLE "case"                  FORCE ROW LEVEL SECURITY;
ALTER TABLE artifact                FORCE ROW LEVEL SECURITY;
ALTER TABLE job                     FORCE ROW LEVEL SECURITY;
ALTER TABLE qa_log                  FORCE ROW LEVEL SECURITY;
ALTER TABLE delivery_receipt        FORCE ROW LEVEL SECURITY;
ALTER TABLE guardian_decision_history FORCE ROW LEVEL SECURITY;
```

- Session hardening (binding):
  - `SET LOCAL search_path = pg_catalog, public;` (prevent implicit resolution)
  - `SET LOCAL statement_timeout = '30s';`
  - `SET LOCAL idle_in_transaction_session_timeout = '15s';`
  - `SET LOCAL lock_timeout = '5s';`
  - `SET LOCAL deadlock_timeout = '200ms';`
  - Enforce `ALTER DEFAULT PRIVILEGES` for the application role to prevent accidental base table grants.

- Priority: High (security gating and policy determinism)
- RLS and masking policies enforced even for table owners via `ALTER TABLE ... FORCE ROW LEVEL SECURITY`, ensuring administrative sessions respect policies.
- Operational canaries verify GUC presence and pooling mode; see `App.J` for SQL snippets (`rls_context_ok` check, boot probe, search_path/timeout guard).

### 4.5 Field-level masking, auditing, and break-glass procedures
*Purpose: Detail how sensitive data exposure is minimized while retaining auditability.*
- `udocket_mask` and `udocket_mask_json` functions apply redaction, hashing, or nulling per `field_mask_rule`. JSON fields support only REDACT/NULL; policy compiler blocks invalid masks.
- Masked views (`case_secure`, `artifact_secure`, `qa_log_secure`, etc.) prevent bypass; application role granted SELECT only on these views. Sysadmin role remains the sole bypass for investigations.
- Audit trail essentials: `audit_event` captures every significant change; `entitlement_snapshot` records token issuance with device fingerprints.
- Break-glass usage logs justification, duration, and triggers watchdog that terminates sessions on expiry. Post-event review queues ensure accountability.
- All read/write paths emit structured logging with correlation IDs and case/job references; anomaly detectors alert on unusual access patterns.

Masking helpers (normative)
```sql
CREATE OR REPLACE FUNCTION udocket_mask(value text, mask text)
RETURNS text LANGUAGE plpgsql STABLE AS $$
BEGIN
  CASE mask
    WHEN 'REDACT' THEN RETURN '[REDACTED]';
    WHEN 'HASH' THEN RETURN encode(digest(coalesce(value,''), 'sha256'),'hex');
    WHEN 'NULL' THEN RETURN NULL;
    ELSE RAISE EXCEPTION 'Invalid mask %', mask;
  END CASE;
END $$;

CREATE OR REPLACE FUNCTION udocket_mask_json(value jsonb, mask text)
RETURNS jsonb LANGUAGE plpgsql STABLE AS $$
BEGIN
  CASE mask
    WHEN 'REDACT' THEN RETURN '"[REDACTED]"'::jsonb;
    WHEN 'NULL' THEN RETURN 'null'::jsonb;
    ELSE RAISE EXCEPTION 'Invalid JSON mask %', mask;
  END CASE;
END $$;
```

Secure view example (security barrier)
```sql
CREATE VIEW artifact_secure WITH (security_barrier=true) AS
SELECT id, org_id, case_id, type, state, content_sha256,
       CASE WHEN (SELECT 1 FROM field_mask_rule r
                   WHERE r.org_id = artifact.org_id
                     AND r.resource='ARTIFACT' AND r.field='content_uri'
                     AND NOT udocket_can('ARTIFACT','read',artifact.case_id,artifact.id,'content_uri')
                ) IS NULL
            THEN content_uri
            ELSE udocket_mask(content_uri,'REDACT') END AS content_uri,
       manifest
  FROM artifact;
```
- Settings activation maintains `CREATE INDEX field_mask_rule_org_resource_field ON field_mask_rule(org_id, resource, field)` and precomputes effective allowlists into helper tables so hot paths avoid repeated subqueries; helpers refresh atomically with each activation.

### 4.6 Field-level encryption (selected columns)
*Purpose: Protect sensitive fields at rest beyond masking/secure views, with clear key management and performance caveats.*
- Scope: selected columns (e.g., PII in `case`, contact data) encrypted using application or DB functions (e.g., `pgcrypto`), with keys managed via KMS and rotated on schedule.
- Design:
  - Keys: per‑env root in KMS; per‑org data keys derived/sealed; app decrypts only for authorized roles and purposes.
  - Indexing: avoid plaintext indexes; use deterministic hashing or search surrogates; document limits.
  - Migrations: backfill jobs with progress logs; dual‑write period until switchover; metrics/traces around decrypt errors.
- Operations: rotation procedure with cutover windows; break‑glass audit trail; performance budgets documented.
- Source material: `§29.2`, `§29.5`, `App.C` classification

- **Source material:** `§2` (all subsections), `§29.6`, `§29.7`  
- **Priority:** High (security gating)

---

## 5) Data model & storage layer

### 5.1 Relational schema (cases, jobs, artifacts, settings)
*Purpose: Establish the canonical schema used by agents, reviewers, and audit tooling.*
- **organization:** UUIDv7 `id`, `name`, JSONB `settings`, `region_allowlist`, timestamps (`created_at`, `archived_at`). Enforces residency policy inputs.
- **user_account:** UUIDv7 `id`, `keycloak_sub`, contact fields, optional `default_org_id`. Keeps reference integrity without duplicating org membership logic.
- **case:** UUIDv7 `id`, `org_id` FK, `title`, `representation_type`, `status`, legal hold fields, audit columns. Write-once invariants enforced via triggers (legal hold reason mask applied via secure view).
- **case_member:** Composite PK `(user_id, case_id)` storing per-case role; informs `udocket_is_case_member`.
- **artifact:** UUIDv7 `id`, `org_id`, `case_id`, `type`, `state`, `content_uri`, `content_sha256`, JSONB `manifest`, OCC `version`, review metadata (`approved_at/by`, etc.). Trigger `artifact_immutable_check` blocks changes to immutable fields.
- **job**, **job_task**, **job_checkpoint:** Track orchestration progress, settings snapshot hashes, checkpoint JSONB, and OCC versions to support retries.
- **guardian_decision_history**, **qa_log**, **delivery_receipt**, **audit_event**, **entitlement_snapshot** provide governance history with RLS and secure views.
- **settings bundles:** Stored via Settings Service (see §9) but referenced in jobs (`settings_snapshot_sha256`) and manifests for traceability.
- ERD lives in `App.G`; state diagrams in `App.J` illustrate artifact/job lifecycles.

### 5.2 Artifact lifecycle and state machine semantics
*Purpose: Define how artifacts progress and how exclusivity & approvals apply.*
- States: `DRAFT` (agent output awaiting Guardian), `READY` (Guardian pass), `QUARANTINED` (Guardian fail), `APPROVED` (human reviewer), `REJECTED` (terminal). `ARCHIVED` flag hides without altering state.
- Guardian transitions only mutate `DRAFT` or `READY`; `QUARANTINED` sticks unless a new submit succeeds. Reviewers promote `READY → APPROVED` and demote any prior approved artifact of the same exclusive type.
- Exclusive types enforced via unique index `one_approved_per_case_type` (state=`APPROVED`, `archived=false`). Settings maintain the type allowlist.
- Manifests capture provenance: schema and graph versions, source artifacts, settings snapshot hash, regions, template versions, and optional SHA pins for dependencies.
- Ops logging: each run writes human-readable `.log`, structured `.json`, and appends to case-level `ops_<agent>.jsonl`.
- Data lineage: App.R documents end-to-end traceability from source artifacts to signed deliverables, aligning manifest fields with Guardian decisions.

### 5.3 Object storage layout & integrity guarantees
*Purpose: Define canonical paths, hashing, and security controls for artifacts and media.*
- Canonical case root: `storage/media/<ORG_ID>/cases/<CASE_ID>/` with categories:
  - `audio/<job_id>__<original>` — original uploads and normalized audio
  - `transcript/<job_id>__transcript.txt` — primary transcripts
  - `analysis/` — Analyze outputs (summaries, outlines, seeds, hints, staff reports)
  - `docs/` — Compose deliverables (client/lawyer, bundle, QA/staff reports) and portal messaging attachments (`ATTACHMENT_*`)
  - `ops/` — human logs, per-run JSON, and append-only `ops_<agent>.jsonl` audit streams
- Integrity: compute and persist `content_sha256` for all immutable artifacts; manifests include SHA-256 of outputs and `settings_snapshot_sha256` for provenance. Batch mode may record remote hashes (`BATCH_HASH_REMOTE=1`, `BATCH_HASH_MAX_MB`).
- Versioning: reruns must not overwrite prior outputs; suffix filenames with `_v{n}` and update manifests. Object storage buckets enable versioning for rollback and audit defense.
- Security: buckets are private by default with server-side encryption (SSE-KMS). Access via short-lived signed URLs; range requests supported for large downloads. Egress and region policies enforce Canada-only storage.
- Normalization: audio inputs normalized to PCM 16 kHz mono when feasible (ffmpeg); normalized copies stored with job-prefixed names for reproducibility and reprocessing.
- Immutability: artifacts are treated as write-once; update attempts to immutable fields are rejected by database triggers. Deletions rely on retention/legal-hold settings (see §14.2).
- Telemetry: object storage latency and hash mismatch counters exported; nightly integrity sweeps sample-verify SHA-256 and bucket versioning state.
- Path template: `storage/media/<ORG_ID>/cases/<CASE_ID>/artifacts/<ARTIFACT_ID>/content.bin|manifest.json`; case-level directories include `audio/`, `transcript/`, `analysis/`, `docs/`, `ops/`. Legacy `storage/media/cases/<CASE_ID>/` layouts are deprecated and blocked in new deployments.
- Upload staging uses `upload_session` records with expected hashes and single-use tokens; finalize promotes staged object into artifact storage.
- SHA-256 computed at write; persisted in `artifact.content_sha256`. Reads recompute and quarantine inconsistencies (`ARTIFACT_INTEGRITY_MISMATCH`).
- Buckets enable versioning + object lock for immutable audit sinks (per §20.1). KMS keys scoped per org when configured (`storage.kms.key_scoping='per_org'`).
- QA diagnostics stored separately under `/job/{job}/qa_logs/{qa_log}/` to keep non-artifact notes; reviewer-visible QA reports remain Guardian-gated artifacts under `docs/`.

### 5.4 Advisory locking & concurrency controls
*Purpose: Prevent double-processing and ensure idempotent behavior across workers.*
- `udlock` schema implements hashed advisory locks (`scope:key`) with helpers for session and transaction locks, plus registry tables capturing holder PIDs, node IDs, and heartbeat timestamps.
- Instrumented wrappers (`udlock.try_lock_i`, `udlock.xact_lock_i`) update registry for observability; `udlock.gc_registry()` cleans orphaned entries by cross-referencing `pg_locks`.
- Job orchestration acquires locks before emitting artifacts (`analyze:lifecycle:{job_id}`, `compose:section:{job_id}:{section}`) to avoid duplicates on retries.
- Upload finalization and approval flows use OCC versions to guarantee single-writer semantics; concurrent approval attempts fail with version mismatch requiring refresh.

#### 5.4.1 Exclusive approval swap (binding)
*Purpose: Enforce at most one APPROVED artifact per `(case_id,type)` and make approvals idempotent and race-free.*
- Unique index (binding):
  ```sql
  CREATE UNIQUE INDEX one_approved_per_case_type
      ON artifact (case_id, type)
   WHERE state='APPROVED' AND archived=false;
  ```
- Approval algorithm (transaction; READ COMMITTED):
  1) Acquire case/type lock: `udlock.xact_lock('case-approval', CONCAT(:org_id,'/',:case_id,'/',:type))`.
  2) Demote any existing `APPROVED` for `(org_id, case_id, type)` to `READY`.
  3) Approve target only if `state='READY'` and `version=:expected_version`; increment `version`.
  4) If no row updated but target already `APPROVED` → return 200 idempotent; else 409 conflict.
  5) Emit audit + SSE. See §11.2.1 for portal invalidation behavior.

Notes
- Prefer OCC columns (`version INT NOT NULL DEFAULT 0`) on hot rows; use advisory locks only for cross-row invariants like the exclusive swap.
- Settings may define additional exclusive types; the baseline index above remains in place, with settings activation validating coverage.
- This procedure is normative; API behaviours in §10.3.2 defer to it to avoid divergence.

### 5.5 Partitioning, indexing, and performance considerations
*Purpose: Ensure data scale aligns with operational SLOs.*
- Time-series tables (`audit_event`, `delivery_receipt`, `guardian_decision_history`) partitioned by month (`created_at`/`decided_at`); ops job rotates partitions ahead of time.
- Targeted indexes support hot paths: `artifact_consumable`, `job_org_case_kind_status`, GIN on `qa_log.issues_json`, etc. Guardian history unique index prevents duplicate idempotency keys.
- Autovacuum tuned for high-churn partitions (`vacuum_scale_factor=0.05`, `analyze_scale_factor=0.02`, `naptime=30s`). Monitoring alerts on `pg_stat_all_tables.n_dead_tup` spikes.
- Search path locked to `pg_catalog, public` per session; statement/lock/idle timeouts enforced (`30s`, `5s`, `15s`, `200ms` deadlock).
- Capacity planning uses metrics from §12 to size Postgres/Redis; cross-region replicas considered only for read-heavy analytics with strict RLS enforcement.

- **Source material:** `§3`, `§4`, `§10.3`, `§29.5`, `App.J`, `App.G`  
- **Priority:** High (feeds DB migrations, data governance)

### 5.6 Artifact manifest schema (normative)
*Purpose: Define a consistent, verifiable manifest format for artifacts.*
Schema (JSON Schema draft 2020-12)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://udocket.ca/schemas/artifact_manifest_v1.json",
  "type": "object",
  "required": ["schema_version","source","provenance","hashes","settings_snapshot_sha256"],
  "properties": {
    "schema_version": {"type":"string", "const":"1"},
    "type": {"type":"string"},
    "source": {
      "type": "object",
      "properties": {
        "case_id": {"type":"string", "format":"uuid"},
        "job_id": {"type":"string", "format":"uuid"},
        "inputs": {"type":"array", "items": {"type":"string", "format":"uuid"}}
      },
      "required":["case_id","job_id"]
    },
    "provenance": {
      "type": "object",
      "properties": {
        "compute_region": {"type":"string"},
        "storage_region": {"type":"string"},
        "tool_versions": {"type":"object"},
        "template_version": {"type":["string","null"]}
      },
      "required":["compute_region","storage_region","tool_versions"]
    },
    "hashes": {
      "type":"object",
      "properties": {"content_sha256": {"type":"string"}},
      "required":["content_sha256"]
    },
    "settings_snapshot_sha256": {"type":"string"}
  }
}
```

### 5.7 Ingestion pipelines & malware/archives defenses
*Purpose: Secure intake against malicious payloads while preserving evidence integrity.*
- Pipeline: raw uploads (`EXHIBIT_RAW`, `COURT_DOC_RAW`, `EMAIL_RFC822`, `FINANCIALS_RAW`, audio) land in staging, run through normalization/OCR/parsers to emit structured counterparts (`*_TEXT`, `EMAIL_ATTACHMENTS`, `FINANCIALS_TABLE`, `TRANSCRIPT`, `DIARIZATION`). Structured artifacts remain `DRAFT` until Guardian marks them `READY`; reviewers promote to `APPROVED`.
- Malware scanning: scan on upload/finalize with signatures and heuristics; block/quarantine positive hits; log details to `audit_event`.
- Archive defenses: enforce archive type allowlist, depth/ratio caps; detect zip bombs and path traversal (Zip Slip) in extractors.
- MIME & size policies: allowlist content types; settings define max size per type; reject suspicious double extensions.
- Evidence: record original filenames, sizes, and content hashes; store normalization provenance for audio.
- Source material: `§37.3`, `§4.1–4.3`

Example
```json
{
  "schema_version": "1",
  "type": "TRANSCRIPT",
  "source": {"case_id": "...", "job_id": "...", "inputs": ["..."]},
  "provenance": {
    "compute_region": "canadacentral",
    "storage_region": "canadacentral",
    "tool_versions": {"udocket_core": "0.9.0", "azure_speech": "1.38"},
    "template_version": null
  },
  "hashes": {"content_sha256": "sha256-..."},
  "settings_snapshot_sha256": "sha256-..."
}
```
## 6) Agent ecosystem

### 6.1 Agent contract (inputs, outputs, manifests, ops logging)
*Purpose: Define the shared behavior that keeps agents composable and observable.*
- Terminology: Appendix I covers lane names, artifact states, and failure classes referenced throughout §6.
- Agents implement the `TranscriptionAgent`-style interface: accept structured config (`TranscriptionConfig` family) rather than CLI flags, pull secrets from `.env` mirroring `config/settings.py`.
- Return value encapsulates success data (`TranscriptionResult`/agent-specific models) and raises rich exceptions with machine-actionable codes; Celery tasks capture and surface to UI.
- Filesystem layout: artifacts saved under `storage/media/<org_id>/cases/<case_id>/<category>/` with `job_id` prefixes; ops logs in `ops/` with per-run JSON + human-readable log, plus append-only `ops_<agent>.jsonl`.
- Deterministic naming/versioning: reruns append `_v{n}` suffix; manifests store `settings_snapshot_sha256`, model/provider versions, compute/storage regions, and SHA-256 of outputs.
- Audit & telemetry: each run logs structured metadata (duration, attempts, cost envelope) and writes SSE updates; metrics exported for `job_duration_seconds`, `agent_retry_total`, etc.

### 6.2 Transcription agent (batch/on-demand modes)
*Purpose: Summarize ingestion flow from audio to transcript artifacts.*
- Modes: `on-demand` streaming for shorter recordings (local processing), `batch` for longer files via Azure Batch Transcription (HTTPS SAS URL). Canada-only regions enforced.
- Input processing: audio uploads hashed, normalized via ffmpeg (PCM 16 kHz mono). Artifacts created: `TRANSCRIPT_INPUT`, `AUDIO_NORMALIZED`.
- Multi-track support: batch mode can ingest stereo/multi-channel sources, splitting speakers prior to diarization; single-track on-demand relies on optional diarization metadata when available.
- Outputs: timestamped transcript (`transcript/<job_id>__transcript.txt`) with header metadata (case, source name, hashes, language, region, duration); optional `DIARIZATION` JSON for batch mode.
- Ops artifacts: `ops/<job_id>__transcription.log`, `ops/<job_id>__transcription_log.json`, case-level `ops_transcription.jsonl` append. Guardian invoked automatically post-write.
- Stdout contract: single JSON line `{status, transcript_file, region, language, attempts, duration_s}` enabling CLI automation.
 - See App.D for canonical artifact types and filenames (TRANSCRIPT, AUDIO_NORMALIZED) and versioning rules.

### 6.3 Analyze agent (LangGraph lanes, QA, artifacts)
*Purpose: Capture the multi-lane analysis pipeline that feeds Compose and downstream tooling.*
- Graph built with LangGraph; lanes include `Events`, `Timeline`, `Issues`, `Entities`, `Facts`, plus staff report generation. Each lane produces typed Pydantic outputs.
- Inputs: latest transcript (`TRANSCRIPT`), optional `DIARIZATION`, approved exhibits (`EXHIBIT_TEXT`, etc.), and settings snapshot. Retrieval uses chunking + embeddings constrained to allowed regions.
- Deterministic IDs: UUIDv8 derived from transcript spans and content to remain stable across reruns; references validated across lanes.
- QA stages: per-lane validation (schema, references, policy lint, token bounds) with `qa_log` entries; final QA ensures cross-lane consistency before Guardian submission.
- Artifacts: `analysis/<job_id>__summary_v1.md|json`, outline, timeline seeds, entity hints, staff report, plus ops JSON + JSONL audit. Failures surface via SSE with actionable errors.
 - See App.D for summary/outline/timeline/entity artifact schemas, filenames, and versioning.

### 6.4 Compose agent (deliverables, QA loops, templates)
*Purpose: Describe final deliverable generation and QA gating.*
- LangGraph pipeline with `OutlineBuilder`, parallel `SectionWriter` nodes (client/lawyer lanes), `SectionQA`, and `FinalWeave`. Inputs include Analyze outputs, intake data, templates.
- Templates resolved via Settings + organization-specific overrides; `unique_title` helper prevents collisions. Manifest stores template version, language, document type.
- QA loops enforce forbidden patterns (`compose.policy.forbidden_patterns[]`), required sections, link counts, and reference integrity. Lane retries limited by `compose.max_retries`.
- Outputs written to `docs/`: `compose_client_v1.md|docx`, `compose_lawyer_v1.md|docx`, bundle excerpt, QA/staff reports. Guardian ensures readiness before reviewer approval.
- Envelopes capture LLM metadata (model, prompt version, region) for reproducibility; FinOps counters track token usage per section.
- See App.D for compose deliverables and QA artifacts and their canonical filenames.
- Model selection: stage-specific profiles defined in `config/llm_assignments.json` map Analyze/Compose lanes to settings keys (`analyze.model.id`, `compose.model.id`) so org/case overrides stay deterministic.

### 6.5 Future agents (timeline, relationship graph) and integration checklist
*Purpose: Provide a runway for upcoming automation without breaking contracts.*
- Planned agents (Timeline, Relationship Graph) inherit the same contract: deterministic IDs, manifest provenance, Guardian gating, ops logging, and Settings-driven configuration.
- Checklist for new agents: define artifact types (Appendix D), extend manifests, register Celery task + SSE events, add ops JSON/JSONL schema, wire Settings keys, update QA/approval flows, document review UX impacts.
- Integration tests must include dry-run/diff of settings, policy linting, and cross-artifact dependency validation (e.g., timeline referencing approved transcripts).
- Any new agent must expose FINOPS metrics, adhere to region allowlists, and update `App.E` traceability map before launch.

- **Source material:** `§5`, `§9`, `§10`, `§11`, `§33`, `AGENTS.md` references  
- **Priority:** High (agent pipeline under active development)

### 6.6 Agent failure handling & resilience
*Purpose: Standardize failure classes, retries, and safeguards to avoid duplication and policy drift.*
- Failure taxonomy (binding):
  - `TRANSIENT`: upstream 429/5xx/timeouts/network. Action → exponential backoff with jitter; respect `Retry-After`; bounded attempts; trip provider circuit on threshold.
  - `POLICY`: forbidden pattern, redaction breach, region disallow. Action → fail lane; emit Guardian quarantine if applicable; surface actionable reason codes.
  - `INPUT`: bad media/schema. Action → fail lane; no auto-retry; record validation details in ops JSON.
  - `INTEGRITY`: hash mismatch/content drift. Action → block downstream; require resubmit with corrected input; log `ARTIFACT_INTEGRITY_MISMATCH`.
  - `CONCURRENCY`: OCC/version conflicts or lock contention. Action → short jittered retry; escalate if repeated; surface conflict to UI.
  - `REGION_POLICY`: residency disallowance. Action → block and log `RESIDENCY_POLICY_BLOCK`; waivers per §3.6.
- Retries & budgets: default 5 attempts; `backoff_factor=2`; jitter 10–20%; max delay 120s; per-agent overrides allowed via Settings.
- Node idempotency (binding): rerunning a completed lane issues zero new provider calls; outputs identical or schema-equivalent.
- Single-flight: use `udlock` advisory locks for job/lane scopes; hold < `udlock.max_session_hold_seconds` with heartbeats every `udlock.heartbeat.interval_seconds`.
- Telemetry: export `agent_retry_total`, `agent_lane_fail_total{reason}`, and duration histograms; write ops logs with `attempt`, `final_state`, `reasons[]`.

### 6.7 LangGraph implementation spec (normative)
*Purpose: Standardize graph runtime behavior for Analyze/Compose.*
- Graph state: typed payloads; immutable inputs; explicit checkpoints.
- Nodes & contracts: input/output schemas; side‑effect boundaries; reproducibility requirements.
- Concurrency & ordering: deterministic ordering where needed; fan‑out/fan‑in patterns documented.
- Checkpointing & idempotency: resume from last good node; no duplicate provider calls after success.
- LLM call wrapper (mandatory): consistent logging, redaction, retry, and cost accounting.
- Memory & retrieval policy: bounded context, chunking, embeddings restricted to allowed regions.
- Error classes & actions: per §6.6 taxonomy mapped to node behaviors.
- Source material: `§54.1–54.10`, `§56`

Deterministic UUIDv8 helper (binding)
```python
def uuidv8_deterministic(
    case_id: UUID,
    lane_or_section: str,
    anchors: dict,
    org_salt: bytes,
) -> UUID:
    anchor_bytes = json.dumps(anchors, separators=(',', ':'), sort_keys=True).encode()
    payload = {
        "case": str(case_id),
        "scope": lane_or_section,
        "anchors_sha256": hashlib.sha256(anchor_bytes).hexdigest(),
    }
    msg = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()
    digest = hmac.new(org_salt, msg, hashlib.sha256).digest()
    b = bytearray(digest[:16])
    b[6] = (b[6] & 0x0F) | (0x8 << 4)
    b[8] = (b[8] & 0x3F) | 0x80
    return UUID(bytes=bytes(b))
```
- Anchors must be canonicalized (sorted transcript spans, referenced Analyze UUIDs, outline positions). Staged vectors live in `spec/vectors/uuidv8.json`; CI asserts the helper reproduces vectors.
- Implementation uses the Python 3.12 standard library `hashlib`/`hmac` exactly as pinned in the runtime container digest; no third-party crypto libraries are pulled in. `org_salt` is derived from a per-org secret stored in KMS (`uuidv8.org_salt_secret`) and materialized via HKDF; rotating the secret issues new UUIDs for future artifacts while manifests keep prior IDs immutable, ensuring replay does not re-key historical records.
- CI test `tests/spec/test_uuidv8_vectors.py` verifies both deterministic output and correct version/variant bits for every reference vector.

Node catalog (illustrative)
| Node | Purpose | Inputs | Outputs |
| --- | --- | --- | --- |
| OutlineBuilder | produce narrative outline | transcript, settings | outline JSON |
| SectionWriter (client) | draft client section(s) | outline, settings, templates | section text + metadata |
| SectionWriter (lawyer) | draft lawyer section(s) | outline, settings, templates | section text + metadata |
| SectionQA | enforce policy gates | section text, policies | QA notes, status |
| FinalWeave | assemble deliverable | sections, templates | composed MD/DOCX |

### 6.8 Compose/Policy lint settings (declarative)
*Purpose: Enforce structural and policy rules via settings instead of code.*
- Settings: `compose.policy.*` (forbidden patterns, required sections, link limits) and `analyze.policy.*` for lane checks.
- Lint flow: pre‑publish checks at node and final weave; failures produce QA logs and block Guardian submission.
- Extensibility: org overrides constrained by safety validators in Settings activation.
- Source material: `§53`, `§6.4`

### 6.9 Graph versioning & migrations
*Purpose: Allow safe evolution of graphs across versions.*
- Version pins: manifests include graph version; upgrades supported via migration plan per change.
- Compatibility: nodes may support multiple versions; deprecations follow the API deprecation policy.
- Acceptance: migration tests verifying schema equivalence or documented deviations.
- Source material: `§55`, `§56`

### 6.10 Compose Graph details (parallels Analyze)
*Purpose: Provide deeper detail on Compose graph structure and gates.*
- Lanes: client and lawyer lanes in parallel; optional bundle excerpt lane; shared OutlineBuilder and FinalWeave.
- Concurrency: SectionWriter nodes run in parallel with bounded concurrency; OCC on artifact writes; udlock on section scopes.
- Retries: per‑section retry budgets; failures summarized in QA; forbidden patterns and missing sections block FinalWeave.
- Provenance: per section envelope logged with model/prompt versions; manifests include graph_version and template versions.
- QA gates: enforce required sections, link counts, references, and forbidden patterns (`compose.policy.*`).
- Source material: `§56`

### 6.11 Agent schemas and error codes
*Purpose: Provide typed outputs per lane and a canonical error taxonomy mapping.*
- Schemas (illustrative Pydantic models):
  - Analyze: `SummaryJSON`, `OutlineJSON`, `TimelineSeed`, `EntityHint`, `StaffReport` with `uuid`, `source_span`, `evidence_refs[]`.
  - Compose: `SectionOutput { section_id, role: client|lawyer, text_md, envelope_id, issues[] }`.
  - QA: `QAIssue { code, level, message, ref?, location? }`.
- Example Pydantic models (Analyze extract):
  ```python
  class SourceSpan(BaseModel):
      start_ms: int
      end_ms: int

  class AnalyzeEvent(BaseModel):
      id: UUID
      title: str
      datetime: datetime | None = None
      participants: list[UUID] = []
      source_spans: list[SourceSpan] = []
      notes: str | None = None

  class AnalyzeIssue(BaseModel):
      id: UUID
      label: str
      description: str
      related_events: list[UUID] = []
      risk: Literal['LOW','MEDIUM','HIGH'] = 'LOW'
  ```
- Compose JSON example:
  ```python
  class ComposeSection(BaseModel):
      key: str
      title: str
      body_md: str
      references: list[UUID] = []

  class ComposeDocument(BaseModel):
      doc_type: Literal['CLIENT','LAWYER']
      language: str | None = None
      sections: list[ComposeSection]
      outline: list[str]
      analyze_refs: dict[str, list[UUID]] = {}
  ```
- Error codes (binding):
  - `E_TRANSIENT_PROVIDER` (TRANSIENT): wrap 429/5xx/timeouts; retry per §6.6.
  - `E_POLICY_FORBIDDEN` (POLICY): forbidden pattern redaction failure; fail lane.
  - `E_INPUT_INVALID` (INPUT): schema/media invalid; fail lane with details.
  - `E_INTEGRITY_MISMATCH` (INTEGRITY): hash/content drift; quarantine and halt.
  - `E_CONFLICT` (CONCURRENCY): OCC/lock conflict; short retry then surface.
  - `E_REGION_BLOCK` (REGION_POLICY): residency disallow; block with remediation.
- Mapping: All error codes must map to §6.6 failure taxonomy; ops JSON must include `{ code, class, message, attempt, final }`.

### 6.12 Quality KPIs & monitoring
*Purpose: Make analysis, transcription, and Guardian quality targets measurable and auditable.*
- **Speech accuracy:** Word Error Rate (WER) target ≤ 8 % for on-demand, ≤ 6 % for batch transcripts measured against quarterly golden sets; dashboards plot WER trend per language with alerts when ≥ 2 % regression (`metrics: transcription_wer_pct{mode,language}`).
- **Guardian effectiveness:** False-negative rate (quarantined after customer exposure) ≤ 0.5 % per quarter, false-positive (unjustified quarantine) ≤ 5 % with remediation documented in App.H RB-GUARD-QUAR review log. Weekly sampling validates decision reasons against policy matrix.
- **Review delta:** Reviewer change rate for Analyze/Compose deliverables < 15 % of sections (measured via `qa_log` issue density and Manual/Agent edit diffs). Exceeding thresholds triggers regression analysis in LangGraph acceptance tests (§13.3).
- **QA defect density:** `qa_issue_density` metric targets ≤ 0.2 blocking defects per artifact; Compose/Analyze QA lanes surface severity distribution for release gates.
- **FinOps + quality blend:** Track tokens-per-approved artifact and rejection counts to ensure budget adherence does not degrade quality; anomalies produce decision-log entries (§15.3).
- Quality KPIs feed quarterly leadership reviews; results archived as `QUALITY_KPI_REPORT` artifacts in Appendix D catalog.

---

## 7) Digital signing & Guardian services

### 7.1 Guardian decision pipeline (READY/QUARANTINED rules)
*Purpose: Govern artifact readiness before human review or client exposure.*
- Terminology: See Appendix I for Guardian decision terms, waiver definitions, and failure categories.
- Entry point `POST /api/v1/guardian/submit` with signed request body `{artifact_id, org_id, case_id, content_sha256?}` and optional idempotency key. Guardian retrieves artifact + effective settings snapshot.
- Decision logic evaluates rulesets per org (JSON, versioned) using artifact metadata, manifest fields, settings posture, and optional hashes. If mismatch detected (`content_sha256` vs DB), returns 412 and sets state `QUARANTINED`.
- State update: artifacts in `DRAFT`/`READY` transition to `READY` or remain `QUARANTINED`. Previously `QUARANTINED` artifacts stay quarantined until resubmitted with a passing decision.
- Response includes `decision`, `reasons`, `guardian_decision_id`; idempotency ensures repeated submissions with same payload return prior decision while conflicting payloads yield 409.
- Hard SLO: decision latency ≤ 5 minutes P95; synthetic jobs validate rule engine and database connectivity (`/synthetic/status`).

#### 7.1.2 Reason codes (normative)
*Purpose: Standardize machine-actionable reasons and remediation guidance.*
- Categories and examples:
  - `INTEGRITY_HASH_MISMATCH`: content SHA mismatch vs DB. Remediation: resubmit with correct content.
  - `POLICY_FORBIDDEN_PATTERN`: content violates forbidden pattern. Remediation: edit content; re-run QA.
  - `POLICY_REGION_BLOCK`: compute/storage region disallowed. Remediation: adjust region; or obtain waiver (§3.6).
  - `MISSING_SECTION`: required section absent (Compose). Remediation: update template or regenerate.
  - `SOURCE_NOT_APPROVED`: upstream artifact not APPROVED. Remediation: approve source or select valid input.
  - `DEBUG_MODE_BLOCKED`: DEBUG enabled in production. Remediation: disable DEBUG.
  - `RESIDENCY_WAIVER_USED`: waiver applied; flagged for audit. Remediation: verify approvals and rationale.
- Sample decision record (guardian_decision_history):
  ```json
  {
    "artifact_id": "00000000-0000-0000-0000-000000000000",
    "org_id": "11111111-1111-1111-1111-111111111111",
    "idempotency_key": "abc-123",
    "decision": "QUARANTINED",
    "reasons": ["POLICY_FORBIDDEN_PATTERN", "MISSING_SECTION"],
    "rules_version": "2025-10-19.3",
    "settings_snapshot_sha256": "sha256-...",
    "decided_at": "2025-10-19T20:15:00Z"
  }
  ```

Reason matrix (illustrative)
| Code | Category | Human message | Remediation | Dashboard tag |
| --- | --- | --- | --- | --- |
| INTEGRITY_HASH_MISMATCH | INTEGRITY | Content integrity mismatch | Re-upload or recompute; resubmit | integrity_mismatch |
| POLICY_FORBIDDEN_PATTERN | POLICY | Forbidden content detected | Edit content; update patterns if false positive | policy_forbidden |
| POLICY_REGION_BLOCK | POLICY | Region not allowed | Change region or obtain waiver | policy_region |
| MISSING_SECTION | STRUCTURE | Required section missing | Update template/prompts; regenerate | missing_section |
| SOURCE_NOT_APPROVED | STATE | Upstream not approved | Approve source; rebind | source_not_approved |
| DEBUG_MODE_BLOCKED | CONFIG | Debugging mode blocked | Disable DEBUG; redeploy | debug_block |
| RESIDENCY_WAIVER_USED | WAIVER | Residency waiver applied | Verify dual approvals; audit | waiver_used |

#### 7.1.1 Invariants & idempotency (binding)
*Purpose: Make Guardian behavior predictable, testable, and safe under retries.*
- Determinism: the same artifact evaluated under the same rules snapshot yields the same decision and reasons.
- Idempotency: submitting the same artifact with the same `Idempotency-Key` returns the prior decision; conflicting payloads with the same key yield 409. Guardian caches keys for the same 24-hour TTL defined by `api.idempotency.ttl_hours` so replay windows align with API expectations.
- Scope of mutation: Guardian only sets the state of the submitted artifact (`DRAFT↔READY` or `QUARANTINED`); it never approves artifacts and never mutates other artifacts.
- History integrity: `guardian_decision_history` defines a unique index on `(org_id, artifact_id, idempotency_key) WHERE idempotency_key IS NOT NULL` to prevent duplicate keys; a `guardian_decision` view exposes the latest decision per artifact.
- Residency waivers: when `regions.cross_region_waiver=true` (§3.6), Guardian stamps `cross_region=true` into the artifact manifest and logs `REGION_WAIVER_USED`; waivers require dual approval (Security + Architecture).
- Signals: on `READY` or `QUARANTINED`, emit `artifact_state` SSE and structured audit events with correlation IDs; consumers must treat these as at-least-once.
- Unique index (binding):
  ```sql
  CREATE UNIQUE INDEX guardian_decision_history_idem_idx
      ON guardian_decision_history (org_id, artifact_id, idempotency_key)
   WHERE idempotency_key IS NOT NULL;
  ```

### 7.2 Digital signature service (PDF/A, TSA, OCSP)
*Purpose: Produce tamper-evident deliverables with verifiable trust anchors.*
- API handles signing requests with `{artifact_id, content_uri, manifest}`; service converts to PDF/A, applies digital signature using org template, and embeds manifests.
- Trust roots configured via settings (`sign.trust_roots[]`); activation validates certificates, expiry, and records version as audit artifact `SIGN_TRUST_ROOTS@<version>`.
- OCSP/CRL checks performed per signature; cache responses for min(`max-age`, 12h) with a 30-minute soft-fail window. During the window the portal surfaces a “verification pending” badge, audit logs record `SIGN_VERIFY_SOFT_FAIL`, and downloads remain available. If the responder remains unreachable beyond 30 minutes the signer returns `SIGN_REVOKE_STATUS_UNKNOWN`, the artifact is quarantined from portal delivery, and on-call is paged with escalation to the TSA vendor.
- TSA integration enforces ±5 second drift vs platform NTP; out-of-drift timestamps rejected. Metrics track `sign_verify_status_total`, `ocsp_latency_seconds`, `ocsp_staple_age_seconds`, `tsa_latency_seconds`, and `tsa_time_drift_seconds`.
- Output artifacts include signature certificates (`SIGNATURE_CERT`) and optional destruction certificates, each referencing underlying content SHA and manifest.
- Manifest schema (Pydantic) captures key version, TSA thumbprint, signer identity (Keycloak subject, display name), device fingerprint metadata, and document context; enforcing provenance on every signed artifact.

### 7.3 Request signing and verification (HMAC)
*Purpose: Authenticate inter-service calls crossing trust boundaries.*
- All mutating APIs (Guardian, Signer, Settings activation) require HMAC headers: `X-Signature-Key-Id`, `X-Timestamp` (RFC3339), `X-Request-Signature`, plus `Idempotency-Key` when supported.
- Signature computed over canonical request components (`method`, `path`, `timestamp`, `body hash`) with org/service-specific shared keys stored in managed secrets.
- Receiver validates timestamp skew (<5 minutes), looks up key ID, recomputes signature, and rejects mismatches with `401 AUTH_ERROR`. Clients should keep system clocks within ±1 minute; retries near the boundary add ±30s random jitter to avoid flapping. Replay protection uses `Idempotency-Key` + short-lived cache.
- Rotation handled via dual-publish of keys; clients send new key ID with overlap window. Appendix F includes request/response examples.

#### 7.3.1 Key rotation flows (normative)
*Purpose: Ensure safe rollovers without request loss.*
- Dual-publish: maintain `{current, next}` keys; announce rotation window; accept both for N days.
- Cutover: flip `current=next`; generate new `next`; revoke old with grace; update service configs via Settings activation.
- Audit: record rotation events; correlate with error spikes; roll back if verification failures increase.
- Emergency revoke: push denylist for compromised key IDs; page on-call; rotate immediately; verify traffic returns to normal.

### 7.4 Audit trails and decision history models
*Purpose: Provide tamper-evident records for regulators and incident response.*
- `guardian_decision_history` partitioned by `decided_at`; records `artifact_id`, `org_id`, `idempotency_key`, `decision`, `reasons`, `rules_version`, `settings_snapshot_sha256`. View `guardian_decision` exposes latest decision per artifact.
- Signing operations append to `audit_event` with actor metadata, IP, UA, and payload referencing trust-root version and TSA token hash.
- Ops JSONL streams (`ops_transcription.jsonl`, `ops_summary.jsonl`, `ops_compose.jsonl`) capture agent-level context used by Guardian during investigation.
- Break-glass events, waiver usage (cross-region), and trust-root updates require dual approval and generate dedicated audit artifacts per §14 / Appendix D.
- Observability dashboards highlight Guardian decision rates, quarantine reasons, and signature verification outcomes for compliance teams.

- **Source material:** `§5.2`, `§6`, `§49`, `App.A` sequence  
- **Priority:** High (legal compliance)

---

## 8) LLM governance & runtime
- Glossary: Appendix I documents LLM envelope, FinOps metrics, and prompt terminology used in §8.

### 8.1 Provider registry, health, and selection algorithm
*Purpose: Ensure model selection obeys residency, health, and preference constraints.*
- Settings-driven catalog (`llm.providers[]`, `llm.models[]`) stores endpoints, auth, supported languages, regions, rate limits, pricing, and fallback priorities.
- Registry polls providers for latency/error rates; circuit breaker flips to OPEN when thresholds exceeded, with half-open probes every 60s.
- Selection steps: enforce region allowlists (`regions.allowlist.compute/storage`), filter by language/org preference, honor case-specific overrides if healthy, otherwise iterate `fallback_priority`. Token ceilings per job lane cap prompts.
- Decision trace recorded in logs and evidence store: chosen model, reason code (`PRIMARY_DEGRADED`, `RATE_LIMIT`, `POLICY_REGION_BLOCK`), health snapshot, cost estimate.
- **Provider data-use posture:** Registry enforces vendor toggles (`llm.providers[].log_retention=false`, `llm.providers[].train_on_data=false`) and verifies contract clauses that forbid prompt/output reuse. Health probes include periodic API checks of provider-side `x-ms-logging-enabled` (Azure) headers; deviations generate `PROVIDER_DATA_POLICY_DRIFT` alerts and block selection until remediated.

### 8.2 Prompt management, redaction, and evidence store
*Purpose: Control prompt content and maintain audit-friendly records.*
- Prompt templates validated via Pydantic with explicit version IDs; stored under `packages/udocket_core/config/` and referenced in manifests.
- Redaction layer strips PII before sending to providers; outcomes tracked (`redaction_stats`, `forbidden_patterns_detected`).
- Evidence store (hardened datastore) records `{prompt_template_id, template_version, model_id, model_version, redaction_ruleset_id, input_hashes, output_hashes, request_id, actor_id, case_id, timestamps}`. Access restricted to `auditor|sysadmin`.
- Logs include truncated prompt/response excerpts with redacted content for debugging; raw prompts never persisted outside short-lived buffers.
- HIPAA mode: settings flip `evidence_store.redacted_excerpts.enabled=false`, preventing storage of prompt/response excerpts and requiring downstream consumers to rely on manifests, envelopes, and hashed payloads. Investigations rely on the reproducibility envelope plus redaction metrics; support teams debug provider issues by running a `llm_replay` dry-run with scrubbed synthetic inputs rather than exposing original prompts.
- Sampling: at least 5 % of inference calls per model/org are reviewed daily; the audit sampler writes signed reports under `ops/security/provider_audits/YYYY-MM/` summarizing detections and confirming provider response headers.
- Validators: nightly harness runs template checksum/linting and regeneration smoke tests; failures halt deployments until resolved. Evidence store schema validated via `udocket_core.llm.config` Pydantic models.
- **Vendor assurances:** Contracts and runtime checks assert that Azure Speech, Azure OpenAI, and other sub-processors have “no training on customer data” flags enabled; agent wrappers set `x-ms-azureml-client-env-data-collection=false` (where supported) and audit responses for confirmation. Evidence of the most recent verification lives in `ops/security/provider_audits/`.

PII posture (binding)
- No raw PII in artifacts produced by LLMs; only masked content is permitted in user-visible outputs per policy.
- Full, unredacted prompts/outputs may be stored only in the evidence store with encryption at rest, tight RBAC (`auditor|sysadmin`), and retention aligned with privacy posture.
- Mask‑unmask maps used for redaction are never written to artifacts; they remain confined to the evidence store context.

### 8.3 Cost controls and FinOps budgets
*Purpose: Prevent runaway spend and provide transparency to orgs.*
- Pre-call guard enforces tokens-in ≤ `analyze|compose.token_ceiling` and ensures projected cost + month-to-date ≤ `llm.finops.monthly_cap_usd`. Violations return `429 RATE_LIMIT` with reasons `TOKEN_CEILING` or `BUDGET_EXCEEDED`.
- Metrics exported: `llm_call_count`, `llm_tokens_in/out`, `llm_cost_estimate_total{org,case,job,model}` feeding FinOps dashboards (`§57.3`).
- Monthly CSV artifacts `FINOPS_REPORT` generated per org, listing cost breakdowns; Guardian/Reviewer approvals required for distribution.
- Deployment gate (`§57.4`) blocks releases when month-over-month cost regression exceeds threshold (default 10%).

### 8.7 FinOps deploy guard (binding)
*Purpose: Prevent regressions from shipping without visibility and approval.*
- Trigger: MoM cost regression beyond threshold (default 10%) or budget breach forecasts for top N orgs.
- Action: Block deploy; page Product/SRE; require approval or mitigation plan; annotate release.
- Metrics: `finops_mom_regression_flag{org}`, dashboards in §12.6; acceptance requires green state prior to release.
- Emergency override: `llm.finops.override_until` (SYSTEM) provides a time-boxed bypass with dual approval; overrides are logged, surface in App.K controls evidence, and expire automatically at the configured timestamp.

### 8.4 Safety harness (jailbreak tests, policy enforcement)
*Purpose: Guard against prompt injection, bias, and policy breaches.*
- Pre-call injection filters: pattern-based sanitization, allowlist of instructions, region/language cross-check. Policy guard rejects requests hitting forbidden patterns.
- Golden-set tests: nightly runs across languages evaluate jailbreak resistance, toxicity, fairness; regressions page on-call and block deploys.
- QA nodes re-validate outputs against schema, length, references, and organization-specific policies (`compose.policy.*`, `analyze.*`). Failures escalate to QA logs and SSE notifications.
- Forbidden content detection triggers automatic Guardian quarantine request and records event in `audit_event` with reason `LLM_POLICY_BLOCK`.

### 8.5 Reproducibility envelopes & replay strategy
*Purpose: Allow future re-execution or provider migration without ambiguity.*
- Every LLM call persists a reproducibility envelope `{prompt_template_id, template_version, model_id, model_version, stop_sequences, truncation_policy_version, temperature, top_p, penalties, redaction_ruleset_id, token_ceiling, settings_snapshot_sha256, input_hashes, output_hashes}`.
- Envelope stored in evidence store and keyed by job/artifact ID; Compose/Analyze manifests reference envelope IDs for traceability.
- Replay harness can re-run top cases on alternate providers, verifying schema equivalence and logging divergences; used for provider exit drills.
- Fallback policy ensures deterministic IDs remain stable: same inputs + envelope guarantee same structure even if textual content varies.
- Deterministic UUIDv8 helper (binding) defined in §6.7 ensures Events/Entities/Facts remain stable; vectors under `spec/vectors/uuidv8.json` keep CI honest.

- **Source material:** `§7`, `§48`, `§57`, `§54.6-54.10`  
- **Priority:** High (LLM oversight is board-level risk)

### 8.6 Provider matrix (illustrative; normative constraints via settings)
*Purpose: Make region/model constraints explicit for ops and reviewers.*

| Provider | Model ID | Regions | Max context | Notes |
| --- | --- | --- | ---: | --- |
| azure_openai | gpt-4o-mini | canadacentral, canadaeast | 128000 | Default Analyze/Compose profile; low latency |
| azure_openai | o3-mini | canadacentral, canadaeast | 200000 | Long-context drafting; higher cost |
| azure_openai | text-embedding-3-large | canadacentral, canadaeast | 8192 | Embeddings for retrieval |

Notes
- Settings `llm.models[]` define authoritative IDs and regions; this table is illustrative only. Non-Canadian regions are blocked unless waiver (§3.6). Registry health governs selection order (§8.1).

---

## 9) Configuration & settings platform

### 9.1 Hierarchical scopes (system/org/case)
*Purpose: Describe how configuration inherits and overrides safely across tenants.*
- Scopes: `SYSTEM` (platform-wide defaults), `ORG` (organization-specific overrides), `CASE` (per-case refinement). Effective settings calculated by overlaying lower scopes onto SYSTEM.
- Settings defined via Pydantic models, grouped into bundles (e.g., `analyze.*`, `compose.*`, `regions.*`). Bundles track versioning and change metadata.
- Sensitive keys (secrets, trustroots) stored encrypted; read APIs redact values where necessary. Some keys enforce immutability at certain scopes (e.g., residency constraints cannot be relaxed at CASE level).
- Each bundle includes validation rules referencing Appendix E for full key catalog and default values.

### 9.2 Settings service APIs and SDK usage
*Purpose: Provide contract for services fetching and snapshotting settings.*
- FastAPI service exposes REST endpoints: `GET /api/v1/settings/<scope>` (effective values), `POST /api/v1/settings/bundles` (activation), `GET /api/v1/settings/bundles/<id>` (metadata), `/api/v1/settings/validate/*` endpoints for region/privacy lints.
- SDK (`SettingsClient`) caches reads per request/context, supports type-safe access (`get(key, type=...)`), and snapshotting (`snapshot()`) to embed in jobs with `settings_snapshot_sha256`.
- Authentication via service tokens + HMAC signing for mutating endpoints. Responses include `version_id`, `bundle_id`, and list of contributing scopes for auditing.
- Clients must avoid direct `.env` reads except for bootstrapping; runtime decisions rely on Settings API to respect dual approvals.
- Definitions expressed via Pydantic models (illustrative):
  ```python
  class SettingDefinition(BaseModel):
      key: str
      datatype: Literal['BOOL','INT','FLOAT','STRING','DURATION','ENUM','JSON','REGION','PERCENT']
      enum_values: list[str] | None = None
      default_value: Any
      mutable_scope: list[Literal['SYSTEM','ORG','CASE']]
      validation_schema: dict[str, Any] | None = None
  ```
  - Case-scoped keys (examples): `compose.tone`, `compose.section.length_limits`, `compose.max_retries`, `analyze.token_ceiling`, `portal.link.expiry`, `visibility.operators.scope`.
  - Org/system keys include residency allowlists, quotas, notifications, LLM provider/model catalogs, TLS policies, `security.field_encryption.*`, `integrity.downstream_action`, request-signing keys, FinOps thresholds, and case enumerations (`case.status.enum`, `case.representation_type.enum`).
- Privacy helpers: `/api/v1/settings/privacy/templates` exposes DPIA/RoPA template metadata by matrix version so Privacy tooling stays aligned with Appendix H.

### 9.3 Activation workflow, diff preview, and dual approval
*Purpose: Ensure configuration changes are intentional and auditable.*
- Activation flow: proposed bundle submitted with desired overrides and metadata; Settings service computes diff against current effective values, runs validators (policy, residency, safety), and returns `unsafe_reasons[]`.
- If `unsafe_reasons[]` populated, activation blocked unless `--force` with dual approval (Security + Architecture) and step-up MFA per `§36.10`. Forcing logs justification and attaches to bundle record.
- Approved activations produce `settings_activation` records with signature, actor IDs, `authorized_roles`, and diff summary; propagate invalidation events over Redis pub/sub.
- Rollback path leverages stored history; last known good bundle can be re-applied with identical diff log. Activation lock prevents concurrent modifications to same bundle (`activation_lock` advisory key).

### 9.4 Caching, invalidation, and policy compilation
*Purpose: Keep runtime consistent without stale policy decisions.*
- Services maintain in-memory cache keyed by `(scope, org_id, case_id, bundle_id)` with TTL + version checks. Redis distributed cache optional for cross-instance sharing.
- Invalidation: Settings service publishes `settings.changed` events `{scope, org_id, case_id, bundle_id}`; subscribers flush caches and reload on next access. Health checks verify caches clear after activation.
- Policy compilation pipeline materializes `effective_permission` and `field_mask_rule` tables per org. Activation jobs run inside workers with transaction-scope locks to avoid race conditions.
- Drift detection compares cached hash vs actual database values; mismatch triggers warnings and eventual forced reload.

### 9.5 Settings telemetry and drift detection
*Purpose: Provide visibility into config usage and anomalies.*
- Metrics: `settings_cache_hit_ratio`, `settings_activation_total{result}`, `settings_validation_failure_total{reason}`, `policy_compile_duration_seconds`.
- Audit events recorded for every activation, validation failure, and forced override. FinOps monitors track cost-related settings changes.
- Drift detection job scans for stale `settings_snapshot_sha256` on jobs vs current effective hash; results logged and optionally flagged in UI.
- Traceability matrix in Appendix E maps each critical feature (agents, Guardian, FinOps, portal) to settings keys; updates required whenever keys change.

- **Source material:** `§36`, `§45`, `§42`  
- **Priority:** High (touches cross-platform config controls)

### 9.6 Policy bundle versioning & diff preview (binding)
*Purpose: Safely evolve settings with visibility and rollback.*
- Version every activation; retain prior bundle; provide human‑readable diff and machine JSON diff.
- Validate policies (RBAC writes, field unmasking, region widening) and flag `unsafe_reasons[]`.
- Dry‑run mode compares compiled tables (`effective_permission`, `field_mask_rule`) before/after.

### 9.7 Activation & rollback (binding)
*Purpose: Provide guardrails for changes to take effect.*
- Activation requires approvals (see §9.3) when unsafe; otherwise single approver per policy.
- On failure or regression, roll back to prior bundle; invalidate caches; recompile policies.
- Record activation window, approvers, and effects in audit.

### 9.8 Activation lock & uniqueness (helpers + OCC)
*Purpose: Prevent concurrent conflicting activations and ensure uniqueness.*
- Acquire advisory lock `settings-activate:{org_id}`; enforce OCC on `setting_bundle` row.
- Unique constraint on `ACTIVE` state per org; migrations ensure constraint; OCC update flips active bundle.
- Source material: `§36.8–36.11`

### 9.9 Enforcement points
*Purpose: Enumerate where runtime must consult Settings or compiled policy.*
- API: authorization (RBAC writes, approvals), CORS, rate limits, portal download guards.
- Workers: agent configurations (models, budgets), residency policy, Guardian/Signer configs.
- Frontend: feature flags, UI flows for approvals and messaging, locales.
- DB: RLS policies and secure masking views referencing compiled tables.

### 9.10 Acceptance
*Purpose: Define completion gates for Settings platform changes.*
- Unit tests: precedence, validators, compilers.
- Integration: activation dry‑run/diff, rollback, cache invalidation.
- Security: unsafe change rules flagged; dual approval enforced; audit records complete.

### 9.11 Security review gates (binding)
*Purpose: Make governance checkpoints explicit and auditable.*
- Waivers: residency cross‑region waivers require Security + Architecture approvals with step‑up MFA; manifests stamped; Appendix D/E updated.
- Guardian rule changes: dry‑run/diff required; unsafe reasons enumerated; dual approval enforced; rollback path documented.
- Settings activation (unsafe): requires dual approval, justification, and audit event; see §9.3 and §36.
- Org Settings: reviewers and roles configured to reflect these gates; acceptance requires end‑to‑end drill.

---

## 10) APIs & integration contracts

### 10.1 REST and WebSocket conventions (naming, pagination, errors)
*Purpose: Standardize interface behavior across services for ease of integration.*
- REST base path `/api/v1/` per service; plural resources (`/cases`, `/artifacts`). Mutations use optimistic concurrency (`version`) for idempotent semantics.
- Pagination envelope `{items, page, page_size, total, next_page}`; sorting `?sort=field:asc`. Invalid sort or masked fields → 400.
- Error envelope `ApiError { code, message, details?, correlation_id }`; servers always include `X-Request-ID`. Rate-limit headers exposed to browsers (see §10.5 CORS contract).
- Real-time:
  - SSE for jobs/cases; emit `progress|state|error|artifact_state` only after committing DB transactions. Monotonic event IDs via Redis `sse:case:{case_id}:seq`.
  - Channels (WebSocket) for collaborative editing and controls; OIDC-authenticated; topics namespaced per case/job.
- RBAC/masking: all reads select from `*_secure` views; serializers never “unmask” redacted fields. Gateway rejects spoof headers (`X-Org-ID`, `X-Active-Roles`); authorization derives solely from OIDC claims.

List contracts (normative)
- Sorting: only on whitelisted fields; multiple fields separated by comma; direction with `:asc|:desc` (default asc). Invalid field/direction → 400.
- Filtering: query params match exact fields; masked fields are not filterable; server may return 400 if filter would breach masking.
- Examples: `?sort=created_at:desc,type:asc&page=2&page_size=50`; `?case_id=<uuid>&type=SUMMARY_MD`.

### 10.2 Artifact/job/review endpoints
*Purpose: Document key CRUD operations and state transitions.*
- Artifacts
  - List: `GET /api/v1/artifacts?case_id=&type=&state=&archived=&page=&page_size=` (RLS-scoped). Org-wide listing via `scope=org` uses token `active_org_id`; `org_id` param not supported.
  - Create (DRAFT): `POST /api/v1/cases/{case_id}/artifacts` with `{type, file|json, manifest}`.
  - Submit to Guardian (idempotent per artifact): `POST /api/v1/artifacts/{artifact_id}/submit_guardian {content_sha256}` → `DRAFT→READY` or `QUARANTINED`.
  - Get: `GET /api/v1/artifacts/{artifact_id}`; Download: `GET /api/v1/artifacts/{artifact_id}/download` (requires `APPROVED`).

- Jobs
  - Create: `POST /api/v1/cases/{case_id}/jobs/{kind}` with `Idempotency-Key` (TTL default 24h) → returns job id.
  - Get: `GET /api/v1/jobs/{id}`; Control: `POST /api/v1/jobs/{id}/pause|resume` (OCC on `version`).
  - Overlap guard: advisory lock `jobkind:{case_id}/{kind}`; conflicts → 409 `JOB_KIND_BUSY`.

- Reviews (OCC + swap lock)
  - Approve: `POST /api/v1/reviews/{artifact_id}/approve {note?, expected_version}`; acquire `case-approval:{org}/{case}/{type}`, demote prior APPROVED of same type, approve if `READY` and version matches; already APPROVED → 200 idempotent.
  - Reject: `POST /api/v1/reviews/{artifact_id}/reject {note?, expected_version}` symmetrical to approve.

### 10.3 Upload lifecycle & idempotency model
*Purpose: Ensure uploads remain tamper-evident and recoverable.*
- Flow: `POST /api/v1/cases/{case_id}/uploads` creates staging record; client uploads to SAS URL; `POST /api/v1/uploads/{id}/finalize` with `Idempotency-Key` + HMAC promotes to artifact.
- Finalize transaction:
  1. Acquire advisory lock via `udlock.xact_lock('uploadsession', upload_session_id)` (helper `with_idempotency_lock`).
  2. Validate session (`status='PENDING'`, not expired) and presence of staging object.
  3. Verify provided hash/size/type against policy.
  4. Server-side COPY staging object to `/org/{org}/case/{case}/artifact/{artifact_id}/content.bin`.
  5. Insert artifact row (`state='DRAFT'`, immutable fields set) with new UUIDv7 and manifest payload.
  6. Update session `status='FINALIZED'`; optionally auto-submit to Guardian (idempotent).
- Idempotency: reuse key within TTL returns same `artifact_id`; reuse with different payload → 409 `IDEMPOTENCY_SIGNATURE_MISMATCH`. TTL default 24h (`api.idempotency.ttl_hours`).
- Retention: expired keys are purged nightly (and opportunistically on insert) so the table stays bounded; retries beyond TTL must supply a fresh key.
- Session expiry via janitor; stale sessions cleaned with `EXPIRED`. Range requests supported; all downloads require `APPROVED` state.

#### 10.3.1 Idempotency keys store (binding)
*Purpose: Provide a generic mechanism for safe retries across create/approve flows.*
```sql
CREATE TABLE idempotency_keys (
  org_id UUID NOT NULL,
  scope  TEXT NOT NULL,                -- e.g., 'job:create'
  key    TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  result_ref TEXT NULL,                -- e.g., job_id
  PRIMARY KEY (org_id, scope, key)
);
CREATE INDEX idempotency_keys_expiry_idx ON idempotency_keys (expires_at);
```
Handler pattern
1) `udlock.xact_lock(scope, CONCAT(:org_id,'/',:key))`.
2) Insert `(org,scope,key,result_ref,expires_at)` on first execution with `expires_at = now() + make_interval(hours => :ttl_hours)`; on conflict, return `result_ref`.
3) Optional overlapping-run guard per case/kind: `udlock.try_lock('jobkind', CONCAT(:case_id,'/',:kind))` → 409 `JOB_KIND_BUSY` if held.
- Nightly janitor job `ops/idempotency/purge.py` deletes expired rows and runs `VACUUM (ANALYZE)` to keep the table bounded; `expires_at` is pinned to `api.idempotency.ttl_hours`.

#### 10.3.2 Reviews API (approval with OCC; binding)
*Purpose: Make approval actions safe under concurrency and retries.*
- `POST /api/v1/reviews/{artifact_id}/approve { note?, expected_version }` (implementation follows §5.4.1)
  - Step 1: `udlock.xact_lock('case-approval', CONCAT(org_id,'/',case_id,'/',type))`.
  - Step 2: demote existing `APPROVED` artifact for `(case_id,type)` (`state='READY'`, increment `version`).
  - Step 3: `UPDATE artifact SET state='APPROVED', review_reason=:note, approved_at=now(), approved_by=:user, version=version+1 WHERE id=:artifact_id AND state='READY' AND version=:expected_version`.
  - Step 4: if rowcount=0 but artifact already `APPROVED`, return 200 (idempotent); otherwise 409 (stale version or state).
  - Step 5: emit audit + SSE; on demotion/invalidation trigger portal guard per §11.2.1.
- `POST /api/v1/reviews/{artifact_id}/reject { reason, expected_version }`
  - Acquire the same `case-approval` lock, `UPDATE artifact SET state='REJECTED', ...` when state∈{`READY`,`APPROVED`} and version matches.
  - On success emit audit/SSE and portal invalidation events per §11.2.1; conflicts return 409.

### 10.4 Guardian, Settings, and Signature APIs
*Purpose: Enumerate service-specific endpoints integrations rely on.*
- Guardian: `POST /api/v1/guardian/submit`, `POST /api/v1/guardian/quarantine`, readiness endpoints (`/healthz`, `/readyz`, `/rulesz`, `/synthetic/status`).
- Settings: `GET /api/v1/settings/<scope>`, `POST /api/v1/settings/bundles`, `/api/v1/settings/validate/*` for regions/privacy, `GET /api/v1/settings/changelog`.
- Digital Signer: `POST /api/v1/sign`, `POST /api/v1/sign/verify`, `GET /api/v1/sign/certificates/{artifact_id}`.
- Privacy & governance: `POST /api/v1/privacy/dpia`, `POST /api/v1/privacy/ropa`, list/read endpoints (`GET /api/v1/privacy/dpia`, `/api/v1/privacy/ropa`), entitlement history (`GET /api/v1/admin/entitlements/history`). All responses include `X-Request-ID` and follow the ApiError schema; OpenAPI specs tag operations with `privacy` and enforce auditor-only access.
- Security: HMAC signing required for all mutating operations; examples in Appendix F. SSE under `/api/v1/jobs/{id}/events`.

### 10.5 OpenAPI governance, linting, and example requirements
*Purpose: Keep API documentation consistent and machine-validated.*
- Specs: OpenAPI 3.0.3; `x-stability` tags (`stable|beta|experimental`); deprecations emit `Deprecation: true` and `Sunset` headers (≥90 days).
- Spectral rules (`ops/openapi/spectral.yaml`): enforce `oidc`, `hmacSignature` on mutating ops, error envelope on 4xx/5xx, shared pagination, and forbid org/role spoof headers.
- Examples must not include real PII; Spectral rule `no-pii-examples` enforces masking, and rate-limit responses (429) must include `Retry-After`/`X-RateLimit-*` headers as shown in Appendix F.
- CORS exposure (binding): expose `X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After, ETag, Deprecation, Sunset`. Preflight allow `Authorization, Content-Type, Idempotency-Key, X-Request-Signature, X-Signature-Key-Id, X-Timestamp, If-Match`. Add `Vary: Origin, Access-Control-Request-Method, Access-Control-Request-Headers`.
- Rate limits & antifraud: per-org and per-IP thresholds; portal download caps with anomaly trip expiring active links; 429 includes rate-limit headers and `Retry-After`. Binding defaults (`api.rate_limits.web.rpm_per_org=600`, `api.rate_limits.web.rpm_per_ip=300`, `portal.download.rate_limits.user_rpm=60`, `portal.download.rate_limits.org_rpm=200`) live in Appendix E; overrides must stay within the 10–2000 RPM guardrails enforced by Settings validation.
- Idempotency TTL (binding): default 24h; reusing keys after TTL executes anew; conflicting reuse returns 409.
- CI: `spectral lint` and schema diff checks gate merges; examples validate. Appendix F holds canonical payloads.

 - **Source material:** `§21`, `§44`, `§52`, `§21.9`, `§47`  
 - **Priority:** High (interfaces for downstream tooling & partners)

### 10.6 HTTP caching & range behavior (binding)
*Purpose: Standardize safe and efficient delivery semantics for approved artifacts.*
- Preconditions: downloads require `state='APPROVED'`; token or signed URL must authorize access to the case/org.
- ETag: responses include a strong validator derived from `artifact.content_sha256` and encoded as a quoted base16 string with a `sha256:` prefix (e.g., `"sha256:0123abcd..."`). The value stays stable across full and ranged requests. Clients may use `If-None-Match` for conditional GETs (304) and `If-Range` for resumable downloads; weak validators are forbidden.
- Range requests: support `Range: bytes=...`; respond with `206 Partial Content`, include `Content-Range`, `Accept-Ranges: bytes`, and correct `Content-Length` for the segment. Full responses remain `200 OK`.
- Headers: include `Content-Disposition` with a safe filename; expose `ETag` via CORS (see §10.5). Signed URLs include short TTLs; servers reject expired or mismatched signatures.
- Caching policy: emit explicit cache directives (e.g., `Cache-Control: private, no-cache` for non-PII, `private, no-store` for PHI/HIPAA artifacts) per org policy. Prefer conditional requests with ETag over long-lived caches for PII.
- Integrity: optional segment integrity checks via store MD5/CRC when available; canonical integrity remains SHA-256 at artifact creation.
- HEAD: support `HEAD` to return metadata (ETag, length) so clients can plan range requests.
- Token enforcement: single-use signed URLs rely on `download_token` rows; fetching requires successful token consumption and verifies artifact hash/state plus current residency allowlists (deny with 403 `POLICY_BLOCK` if regions drift).

### 10.7 Error model and codes (normative)
*Purpose: Provide a consistent envelope and code semantics across services.*
- Envelope (binding):
  ```python
  class ApiError(BaseModel):
      code: Literal[
        "POLICY_BLOCK","QUARANTINED","INTEGRITY_ERROR",
        "VALIDATION_ERROR","AUTH_ERROR","NOT_FOUND",
        "CONFLICT","RATE_LIMIT","PROVIDER_DEGRADED"
      ]
      message: str
      details: dict[str, Any] | None = None
      correlation_id: str
  ```
  - Servers echo the `Idempotency-Key` header (if present) in responses to aid callers with safe retries.
- HTTP mapping examples:
  - `409 CONFLICT`: `code="CONFLICT"` (idempotency mismatch, stale OCC version, job kind busy).
  - `412 PRECONDITION_FAILED`: `code="INTEGRITY_ERROR"` (hash mismatch) or `code="POLICY_BLOCK"` (portal invalidation).
  - `429 TOO_MANY_REQUESTS`: `code="RATE_LIMIT"` (rate ceilings, token budgets); include `Retry-After`, rate-limit headers per §10.5 and `details.retry_after_ms` when known.
  - `503 SERVICE_UNAVAILABLE`: `code="PROVIDER_DEGRADED"` (circuit open, dependency outage).
- Headers: always emit `X-Request-ID`; add `Retry-After`, `Deprecation`, `Sunset`, and rate-limit headers when applicable. Error payloads are included in Spectral lint checks (§10.5).

Client retry guidance (normative)
| Error code | Typical cause | Client action |
| --- | --- | --- |
| `CONFLICT` + stale `version` | Optimistic concurrency failure | Re-fetch resource, apply latest state, retry with updated `expected_version` |
| `CONFLICT` + idempotency mismatch | Replayed key with different payload | Generate a new `Idempotency-Key`; ensure request body matches original |
| `RATE_LIMIT` | Per-org/IP quota exceeded | Honor `Retry-After` header; exponential backoff |
| `POLICY_BLOCK` | Guardian/portal policy violation | Surface message to operator; resolve underlying policy issue before retrying |
| `QUARANTINED` | Guardian rejected artifact | Present remediation reasons; require manual fix |
| `INTEGRITY_ERROR` | Hash/ETag mismatch | Re-upload/file new hash; do not retry blindly |

### 10.8 SSE event schema & sync snapshot (normative)
*Purpose: Define canonical SSE events and replay behavior.*
- Event types: `job.update`, `artifact.state`, `qa.notes`, `portal_link_invalidated`, `settings.activated`.
- Envelope: `id` (monotonic), `event`, `data` (JSON), `retry` (ms). `id` echoes in `Last-Event-ID`.
- Sequencing: IDs are monotonic per stream (`sse:case:{case_id}` and `sse:job:{job_id}`) and minted via Redis `INCR`, ensuring ordered delivery across multiple web pods without requiring cross-stream ordering.
- Sync snapshot: if `Last-Event-ID` predates retention window, server emits a snapshot (RLS‑scoped) before live tail.
- Delivery: at‑least‑once; clients de‑dupe via `id`. Snapshots include a bounded window and watermarks.
- Security: events enforced by RLS; tokens bound to org/case; portal receives a subset.
- Settings Service emits identical payloads via SSE (`settings.activated`) and Redis `settings.changed` events so workers and browser clients observe the same activation metadata.
- Retention: SSE replay buffers keep 24 hours of events; reconnects beyond that window receive a snapshot plus the latest live tail.
- Source material: `§45`, `§50`

Payloads (illustrative)
| Event | data fields | Notes |
| --- | --- | --- |
| job.update | `{ job_id, case_id, org_id, status, progress?, error? }` | `status ∈ {PENDING,RUNNING,PAUSED,FAILED,COMPLETED}` |
| artifact.state | `{ artifact_id, case_id, org_id, type, state, previous_state?, ts }` | `state ∈ {DRAFT,READY,QUARANTINED,APPROVED,REJECTED}` |
| qa.notes | `{ job_id?, artifact_id?, case_id, notes:[{level,msg,ts}] }` | Levels: INFO|WARN|ERROR; limited to staff |
| portal_link_invalidated | `{ artifact_id, case_id, reason, ts }` | Portal consumes to revoke stale links |
| settings.activated | `{ scope, org_id?, case_id?, bundle_id, version_id, ts }` | Triggers cache invalidation on clients |

Examples
```json
// job.update
{ "id":"1024","event":"job.update","data": {"job_id":"...","case_id":"...","org_id":"...","status":"RUNNING","progress":42}}

// artifact.state
{ "id":"1030","event":"artifact.state","data": {"artifact_id":"...","case_id":"...","org_id":"...","type":"SUMMARY_MD","state":"APPROVED","previous_state":"READY","ts":"2025-10-19T21:12:00Z"}}

// portal_link_invalidated
{ "id":"1035","event":"portal_link_invalidated","data": {"artifact_id":"...","case_id":"...","reason":"APPROVAL_SWAP","ts":"2025-10-19T21:14:00Z"}}
```

### 10.9 Rate limits & antifraud controls
*Purpose: Prevent abusive usage while providing clear backoff guidance.*
- Global throttles: `api.rate_limits.web.rpm_per_org`, `api.rate_limits.web.rpm_per_ip`; 429 responses include `Retry-After`, `X-RateLimit-*`, and support exponential backoff guidance.
- Portal downloads: per-user/org caps (`portal.download.rate_limits.*`) with anomaly detection; exceeding triggers `portal_link_invalidated` and optional step-up MFA.
- SSE/Channels: server disconnects on org switch or token expiry; reconnects honour backoff (`retry` field) and enforce token binding.
- Fraud signals: repeated 4xx from a single IP escalate to security incident workflow; rate-limit spikes logged via `API_RATE_ALERT` audit events.
- Source material: `§21.7`, `§45`

### 10.10 Timezone & clock policy
*Purpose: Guarantee consistent timestamps across APIs, UI, and downstream systems.*
- **Storage:** All persisted timestamps use UTC (`TIMESTAMP WITH TIME ZONE`) with millisecond precision; APIs return ISO 8601 UTC (`Z`) strings. Case/portal locale rendering converts at presentation time only.
- **Client hints:** Requests may include `X-Client-Timezone` for UX personalization; server never trusts it for persistence or policy enforcement.
- **Clock hygiene:** Services rely on chrony/NTP with ±100 ms drift budget (aligned with TSA requirements in §3.2). Health checks fail closed if drift exceeds 250 ms; alerts page SRE.
- **UI controls:** Date pickers default to case locale; portal displays timezone label on deliverables and approvals. Manual edits capture both UTC timestamp and operator-local zone for audit clarity.
- **Backfills/migrations:** Jobs ensure time arithmetic uses timezone-aware APIs; tests verify `created_at`/`decided_at` fields remain UTC during bulk updates.

---

## 11) Frontend & client experience
- Glossary: Appendix I defines approval roles, portal messaging objects, and artifact states referenced here.

### 11.1 Staff UI (case workspace, approvals, analytics)
*Purpose: Summarize the operator/reviewer experience and dependencies.*
- Case workspace shows artifact timeline, job status, approvals queue, and Guardian outcomes; integrates with SSE for live updates and Channels for collaborative notes.
- Approvals panel enforces multi-step review (agent output, manual edits) with OCC guardrails; components display readiness, reviewer count, and pending manual edits.
- Analytics dashboards surface LLM cost, artifact coverage, QA issues; data sourced from `audit_event`, `ops_*` logs, and FinOps metrics.
- Component-level permissions derived from Settings-driven policy map; UI respects field masks (e.g., masked SHA values replaced with `[REDACTED]`).

### 11.2 Client portal (document delivery, messaging, access controls)
*Purpose: Outline client-facing surface and data exposure guardrails.*
- Portal provides read-only access to approved artifacts, messaging with staff, and signoff flows. Download links are signed and time‑bound; range support per §10.6.
 - Messaging system (see §11.6) allows secure replies; attachments stored as artifacts with Guardian review before release.
- Access dependent on Keycloak `org_client` role; portal tokens shorter-lived with automatic step-up for approvals/signoffs.
- Portal UI enforces cross-org isolation by closing sessions on org switch and clearing caches when token scope changes.

#### 11.2.1 Portal invalidation (binding)
*Purpose: Ensure clients cannot access stale or revoked artifacts after review actions.*
- The platform invalidates active portal links whenever an approval swap demotes a previously `APPROVED` artifact of the same `(case,type)`, a reviewer rejects an `APPROVED` artifact, Guardian sets the artifact to `QUARANTINED`, or integrity monitoring raises `ARTIFACT_INTEGRITY_MISMATCH`.
- Invalidations emit `portal_link_invalidated {artifact_id, reason, ts}` events and SSE notifications; subsequent downloads return `403` and the portal shows a denial banner.
- Indexes/search hide demoted or rejected artifacts; portal lists reflect only the latest `APPROVED` artifacts per exclusive type.
- Copy surfaced to clients is settings-driven via `i18n.portal.invalidation.message_key`, allowing Product/Legal to localize or update messaging without code changes.

#### 11.2.2 Fetch-time guard (binding)
*Purpose: Enforce explicit checks on every fetch to avoid stale or unauthorized content.*
- Preconditions: `state='APPROVED'`, case/org membership, and fresh signed URL or token.
- Conditional requests: require `If-Match` with artifact ETag; mismatches → `412 PRECONDITION_FAILED` with guidance to refresh.
- Rate limits: per‑user/org caps; anomalies invalidate links and prompt step‑up MFA when configured.

### 11.3 Accessibility (WCAG AA) and localization strategy
*Purpose: Ensure frontends meet accessibility and language requirements.*
- WCAG 2.2 AA compliance: keyboard navigation, focus states, ARIA labels, color contrast checks. Automated audits run in CI; manual audits scheduled per release.
- Localization: staff UI initially English/French; portal supports additional locales via Settings (`i18n.supported_locales[]`). Strings managed in translation files with fallback logic.
- Date/time formatting relies on case locale; transcripts labelled with language metadata. Screenreader testing prioritized for approval flows and messaging.
- Templates offer locale variants with placeholder linting per locale; cross-language toggle supported for courts/catalogs. RTL readiness documented for supported locales; fallback flags alert admins when translations are missing.
- CI runs pseudolocalization suite (`scripts/i18n/pseudolocale.sh`) and axe-core screen-reader scripts; latest WCAG audit summary stored as `ACCESSIBILITY_AUDIT` artifact (referenced in App.L). Accessibility KPI dashboard tracks open issues, assistive-technology test passes, and remediation SLAs.

### 11.4 Real-time collaboration (SSE + Channels policies)
*Purpose: Govern multi-user interactions without compromising security.*
- SSE streams status updates (`job.update`, `artifact.state`, `qa.notes`) to both staff and clients with token-binding; server disconnects on token expiry or org switch.
- Channels-based editors allow Manual/Agent edits with conflict resolution; optimistic locking ensures edits create new artifact versions awaiting approval.
- Real-time controls (pause/resume jobs, rerun Guardian) restricted to authorized roles; commands processed via Channels with audit events capturing actor and outcome.

### 11.5 Security hardening (headers, anti-phishing, download guards)
*Purpose: Mitigate browser threats and misuse.*
- Security headers: `Content-Security-Policy`, `Strict-Transport-Security` (`max-age >= 180d`, includeSubDomains), `X-Frame-Options=DENY`, `Referrer-Policy=no-referrer`.
- Anti-phishing: link verification, suspicious message detection, `Report` workflows logging to audit event.
- Downloads enforce `APPROVED` state, `If-Match` checks, and limit simultaneous downloads per user to deter scraping. Portal messaging attachments scanned via malware pipeline (§37.3).
- Browser fingerprinting and anomaly detection integrate with Settings to flag suspicious access patterns.

- **Source material:** `§18`, `§11.6`, `§21.2`, `§29.4`, `§45`  
- **Priority:** Medium (align with UX strategy)

---

### 11.6 Secure portal messaging (scope, model, APIs)
*Purpose: Enable secure, RLS‑enforced messaging between clients and staff with attachments.*
- Scope: internal messaging only (non‑email/SMS), stored in DB + object storage; attachments are first-class artifacts (`ATTACHMENT_RAW`/`ATTACHMENT_TEXT`) so they inherit Guardian review, retention, and portal invalidation semantics.
- Data model & RLS: `message_thread`, `message`, `message_attachment`, `message_read_receipt`; `message_attachment` stores lightweight metadata and the backing `ATTACHMENT_*` artifact id so RLS/Guardian controls apply uniformly; secure views mirror case membership policies.
- Object storage: separate prefix for attachments; scanning pipeline; retention tied to case lifecycle.
- APIs: list/create messages/attachments, read receipts, thread visibility; rate limits apply; signed URLs for attachments.
- Settings: enable/disable per org; size/type allowlists; retention overrides.
- Observability: delivery/read metrics, anomaly detection; alerts on abuse patterns.
### 11.7 Manual/Agent edit flows & dual approval
*Purpose: Clarify reviewer counts, state transitions, and UI prompts for edit workflows.*
- Manual Edit: creates a child version (`DRAFT`); reviewers (count configurable per `reviews.required_types[]`) must approve before promotion; demotes any prior APPROVED exclusive artifact.
- Agent Edit: interactive session produces a candidate child; same approval semantics as Manual Edit; UI shows “AI Assisted” badge with audit trail.
- Dual approval: certain artifacts (e.g., legal deliverables) require two distinct reviewers (roles defined in Settings); UI displays remaining approvals and enforces step-up MFA when configured.
- Database guardrails enforce distinct approvers via a partial unique index (e.g., `CREATE UNIQUE INDEX approve_once_per_user ON artifact_review (artifact_id, reviewer_id, approval_type) WHERE state IN ('PENDING','APPROVED')`), preventing the same reviewer from consuming multiple required slots.
- i18n: all approval banners, edit prompts, and invalidation copy are localized via settings-driven strings (`i18n.*`).
- Source material: §§11, 21; see Appendix A.8 for state diagrams

### 11.8 Notifications & outbound communications
*Purpose: Guarantee idempotent delivery across email/SMS/providers while preserving audit trails.*
- Outbox pattern: `outbox_delivery` stores messages with `status`, OCC `version`, retry counters, and provider metadata. Workers claim batches via `FOR UPDATE SKIP LOCKED` and transition states atomically (`status='PENDING' → 'SENDING'`) with OCC checks to avoid duplicate sends.
- Provider idempotency: unique constraint on `(org_id, channel, external_message_id)` prevents replays; delivery receipts enforce `(org_id, channel, provider_event_id)` uniqueness before updating status.
- Webhook intake: verifies HMAC (`X-Request-Signature`), updates receipts under OCC, and writes `delivery_receipt_secure` view rows for auditor access.
- Email deliverability: org onboarding validates SPF/DKIM alignment; DMARC policy must be `quarantine` or `reject` for production domains. Bounce/complaint webhooks feed delivery receipts and trigger follow-up tasks.
- SMS compliance: enforce opt-in state, STOP/HELP handling, and region-specific sender policies; shortened links stay case/org scoped and inherit download-token rules.
- Download tokens: signed URLs include `artifact_id`, hash, state, expiry, and optional single-use flag. Fetch flow validates tokens via `download_token` table before streaming.
- Sender workers claim batches with `FOR UPDATE SKIP LOCKED` and OCC (`version` column) to ensure single flight per outbox row; helper functions encapsulate the lock usage.
- SQL guardrails (normative):
  ```sql
  ALTER TABLE outbox_delivery
    ADD COLUMN external_message_id TEXT,
    ADD COLUMN version INT NOT NULL DEFAULT 0,
    ADD CONSTRAINT outbox_unique_extmsg UNIQUE (org_id, channel, external_message_id);

  ALTER TABLE delivery_receipt
    ADD COLUMN provider_event_id TEXT,
    ADD CONSTRAINT receipt_provider_event_unique UNIQUE (org_id, channel, provider_event_id);
  ```
- Resend logic first checks these unique keys; if a provider reports an already-sent ID, the system treats it as delivered and avoids re-sending. Audit events capture every send/receipt attempt with correlation IDs.
- Region revalidation: on every download, ensure `artifact.manifest.storage_region` (and `compute_region`, when present) remains within the current effective allowlist; violations return 403 `POLICY_BLOCK` with audit events.
- Source material: §17; Appendix F exemplars

### 11.9 In-app notifications
*Purpose: Cover real-time notifications inside the portal/staff UI.*
- Channels: rendered through SSE/Channels with read receipts; stored as `IN_APP_NOTIFICATION` artifacts when audit needs persistency.
- Rate limits: share same quotas as outbox notifications; Settings keys `notifications.in_app.rate_limit_per_minute` and `notifications.in_app.daily_cap`.
- L10n: UI strings localized via `i18n.notifications.*`; actions link to case resources with RLS checks.
- Observability: metrics `inapp_notification_sent_total`, `inapp_notification_click_total`; anomalies trigger `alert_notifications_inapp_anomaly` with App.H runbook reference.

### 11.10 Document assembly pipeline
*Purpose: Describe post-Compose rendering, linting, and approval loop.*
- Inputs: latest `COMPOSE_CLIENT`/`COMPOSE_LAWYER` artifacts and organization templates (`TEMPLATE` artifacts) selected via Settings.
- Steps: lint placeholders, render DOCX (optionally PDF/A), compute SHA-256, write `ASSEMBLED_DOC_*` artifacts (`DRAFT → READY → APPROVED`).
- Exclusive types: approving a new assembled document demotes the prior APPROVED version atomically (same swap logic as Compose).
- Telemetry: emit metrics `document_assembly_duration_seconds`, `document_assembly_error_total`; lint warnings recorded in ops logs for reviewer visibility.

## 12) Observability, reliability & operations
- Glossary: Appendix I includes observability metrics, watchdog terminology, and quota concepts cited in §12.

### 12.1 Telemetry stack (logs, metrics, traces)
*Purpose: Ensure platform-wide visibility, SLOs, and actionable alerts.*
- Structured logs: `ts, trace_id, org_id, case_id, user_id, job_id, artifact_id, action, result, latency_ms, settings_bundle_id` with PII redaction.
- Metrics: queue depth, job durations, Guardian latency/throughput, Signer verify latency (including `sign_verify_status_total`, `ocsp_latency_seconds`, `ocsp_staple_age_seconds`, `tsa_latency_seconds`, `tsa_time_drift_seconds`), LLM health/circuit state, delivery rates, integrity incidents (`integrity_scan_queue_depth`, `integrity_quarantine_total`), SSE reconnect rate, `artifacts_ready_total`, `artifacts_approved_total`, `time_to_approval_seconds`. All Prometheus metrics use seconds for duration histograms and `_total` counters for events; legacy `*_ms` signals are being renamed as part of §12.6 monitoring hygiene.
- FinOps metrics: `llm_cost_estimate_total{org,case,job,model}`, `finops_cost_per_case_usd{org,case}`, `finops_cost_per_org_usd{org,month}`, `delivery_events_total{org,channel,status}`, `finops_mom_regression_flag{org}`.
- Privacy/Governance: `residency_block_total`, `dpia_records_total{status}`, `ropa_records_total`, `entitlement_snapshots_total`, `policy_unsafe_activations_blocked_total`.
- Advisory locks: `udlock_locks_held{scope,kind}`, `udlock_lock_age_seconds_p95{scope,kind}`, `udlock_watchdog_stale_total{action}`, `udlock_registry_gc_total`.
- Traces correlate web → workers → Guardian/Signer/LLM; ingress injects `X-Request-ID` on missing. API SLOs: Availability ≥ 99.9%/30d; P95: reads 250ms, writes 500ms; Portal TTFB ≤ 400ms in-region, calculated over rolling 5-minute windows.
- Immutable audit sink: dual-stream audit_event to DB + WORM storage; hourly AUDIT_SEAL artifact with rolling Merkle root; verification validates chain continuity. Metrics `audit_worm_lag_seconds`, `audit_seal_errors_total`. If seal verification fails for more than one interval, the release pipeline blocks new approvals and portal deliveries until the seal returns to green and Security signs off.
- Log retention & sampling:
  - Staff/API request logs retained 90 days hot, 365 days cold (object storage) with 10 % sampling for successful 2xx responses; 4xx/5xx retained in full with sensitive fields masked via `logging.redaction.enabled`.
  - LLM evidence logs retained 365 days with `train_on_data=false` confirmation; HIPAA mode reduces retention to 180 days and forces excerpt suppression (§8.2).
  - Masking tests run in CI (`tests/logging/test_redaction.py`) to prevent PII leakage; failures block merges (§13.7).


### 12.2 Runbooks and synthetic monitors
*Purpose: Ensure operational readiness and quick diagnosis.*
- Synthetic checks: `/readyz` with RLS enforcement, settings cache validation, NTP drift. Guardian synthetic job ensures policy enforcement; Signer synthetic verifies TSA reachability.
- Runbooks stored in ops repo (linked in App.H) cover Guardian quarantine handling, PgBouncer pooling misconfig, artifact integrity mismatch, and SSE replay issues.
- Automation: watchdog tasks auto-quarantine artifacts with integrity failures, restart pods on failed health checks, and rotate settings caches when invalidation fails.
- Fail-closed defaults: if Guardian is unavailable, artifacts remain `DRAFT`; if Settings is unavailable, new jobs block on snapshot fetch while running jobs continue with embedded snapshots. These scenarios have dedicated alerts and runbooks in App.H.

### H.5 RB-LLM-003 — Provider degradation / circuit breaker (normative)
Purpose: Detect and act on degraded LLM providers to protect budgets and SLAs.

Linked alert: `alert_llm_circuit_open` (Grafana: FinOps → LLM Cost & Circuit dashboard).

Signals
- Metrics: `llm_circuit_state{model}`, error rate > threshold (e.g., >5%/5m), latency P95 > budget, provider 429s.
- Health probes failing; registry marks provider as `DEGRADED`.

Triage (5-minute)
1) Confirm models affected; inspect dashboard panels filtered by `model` and `org`.
2) Check fallback outcomes in logs (reason `PRIMARY_DEGRADED`), and cost deltas.
3) Verify region policy not cause (see `POLICY_REGION_BLOCK`).

Decision
- If OPEN circuits present: keep OPEN; allow half-open probes every 60s. Ensure fallback models are healthy and within budgets.
- If latency/error just over threshold: raise replicas; notify Product if budget impact > X.

Post-remediation
- Track `llm_circuit_state` returning to CLOSED; annotate incident with timestamps and budget impact.
- File provider incident with vendor ticket if persistent.

Preventive actions
- Tighten timeouts; raise pre-call token ceilings checks; adjust fallback priorities; add synthetic prompts to golden set.

### 12.3 Incident response workflows & escalation paths
*Purpose: Define how the team reacts to outages or security events.*
- Incident severity levels with defined on-call rotations (Engineering, Security, Product). Playbooks for RBAC breaches, data residency violations, Guardian outages.
- Post-incident reviews required within 48h; actions tracked in ops backlog. Metrics `incident_count_total`, `mttr_minutes`.
- Communication templates for customer notifications, regulators, and internal leadership included in App.H; latest redlines stored as `INCIDENT_TEMPLATE` artifacts covering PII disclosure, residency breach, and major outage scenarios.

### 12.4 Backup, DR objectives, and failover drills
*Purpose: Maintain data durability and disaster preparedness.*
- Postgres: daily full snapshots + continuous WAL shipping; target RPO ≤ 15 minutes, RTO ≤ 1 hour. Quarterly restore drills documented.
- Object storage: versioning + lifecycle rules; deletion requires dual confirmation. Immutable audit sinks operate under WORM retention policies.
- Redis: persistence optional; rely on recomputation for queues. For critical caches, use managed Redis with cross-zone replicas.
- DR exercises simulate region failure; cross-region read replicas considered once residency waivers approved. Settings and Guardian services replicate configuration backups.

### 12.5 Capacity planning, autoscaling, and performance budgets
*Purpose: Keep services within latency/cost budgets as usage grows.*
- Autoscaling policies: HPAs for web/channels (CPU, request latency), workers (queue depth), Guardian/Signer (p95 latency). Compose/Analyze queue lengths monitored for backlog thresholds.
- Capacity reviews quarterly: evaluate job volume, LLM spend, storage growth. Provide forecasts to FinOps (link to §57).
- Performance budgets tracked via dashboards: upload finalize ≤ 5s, SSE lag < 1s, LLM lane runtime budgets (5–15 minutes per lane depending on complexity).
- Stress tests run pre-release using synthetic workloads; results captured in App.H for regression comparison.
- Benchmark snapshots in App.L capture the latest measured baselines feeding these budgets; deviations trigger escalation before release.

#### 12.5.1 Failure taxonomy & resilience (binding)
*Purpose: Define platform-wide recovery behavior and safety nets.*
- Classes and remedies:
  - `TRANSIENT` (429/5xx/timeouts): exponential backoff + jitter; respect `Retry-After`; bounded attempts. Trip per-model/provider circuit on threshold; half-open probes every 60s.
  - `POLICY` (forbidden/region): no auto-retry; Guardian quarantine when applicable; actionable errors surfaced.
  - `INPUT` (validation/media): no auto-retry; clear user-facing error; link to docs.
  - `INTEGRITY` (hash mismatch): block pipeline; quarantine; require resubmit; audit `ARTIFACT_INTEGRITY_MISMATCH`.
  - `CONCURRENCY` (OCC/locks): short jittered retries; escalate after N attempts; ensure OCC versions in APIs.
- Circuits and watchdogs:
  - LLM circuits: OPEN/HALF-OPEN/CLOSED; metrics `llm_circuit_state`, reason codes (`PRIMARY_DEGRADED`, `RATE_LIMIT`). Runbook App.H RB-LLM-003.
  - Advisory lock watchdog: metrics `udlock_watchdog_stale_total`, `udlock_lock_age_seconds_p95`; defaults `udlock.max_session_hold_seconds=300`, `udlock.heartbeat.interval_seconds=5`. Runbook App.H RB-LOCK-006. `kill_stale=false` in prod; remediation: terminate holder or GC registry (`udlock.gc_registry()`).
- Queues and DLQ:
  - Outbox pattern for notifications with retries/backoff; poison messages routed to DLQ with capped replays and operator alerts.
- Integrity scan DLQ: dead-letter queue `q.integrity.deadletter` captures items exceeding retry budget (`last_error`, `attempts`, `cause`). DLQ processing emits on-call alerts and requires manual triage per App.H runbook.
- Downstream propagation: when a source artifact is quarantined for integrity mismatch, workers walk `manifest.source_artifacts[]` and apply `integrity.downstream_action ∈ {mark_stale, quarantine}` to dependents so UI surfaces NEEDS_REVIEW banners; defaults are `quarantine` for legal deliverables (`COMPOSE_*`, `ATTACHMENT_*`) and `mark_stale` for Analyze outputs per Appendix D.
- SLO guardrails:
  - Guardian decision P95 ≤ 5m; Compose ≤ 45m P95; upload finalize ≤ 5s. Alerts on burn rates and budget breaches; see §12.6 dashboards.

- **Source material:** `§20`, `§24`, `§41`, `App.H`  
- **Priority:** Medium (operational readiness)

---

### 12.6 Named dashboards & alert routing
*Purpose: Provide common observability views and bind alerts to runbooks.*
- Guardian SLO & Throughput (SRE): decision latency P50/P95/P99, error rate, queue depth, synthetic success, SLO burn rate.
- Queues & KEDA (SRE): Celery queue depth per lane, replicas, scaling events, DLQ intake and drain.
- LLM Cost & Circuit (Platform): tokens in/out, estimated spend vs cap, circuit state per model/provider, fallback reason codes.
- Audit Seal & WORM (SecEng): seal cadence, seal errors, WORM lag, verification status.
- Portal Security (SecEng): download rate per org/user, anomaly triggers, link invalidations, adaptive MFA prompts.
- Advisory Locks (SRE): locks held by scope/kind, age percentiles, stale detections, terminations; tied to App.H RB-LOCK-006.
- Unit Economics & Delivery (PM/SRE): cost per case/org; MoM deltas; top 10 expensive cases; delivery counts and failure rates.

Alert routing
- Sev-1 pages on: Guardian SLO burn > 2x target 15m; audit seal missed 2 intervals; queue depth > 3× budget 10m.
- All alerts include `dashboard_url`, `runbook_id` (when applicable), and last 5 relevant traces.

### 12.7 Synthetic monitors coverage
*Purpose: Continuously validate critical paths and assumptions.*
- Web: `/readyz` checks RLS GUCs; `/healthz` verifies DB connectivity and cache coherence.
- Guardian: submit synthetic artifact; expect deterministic READY with known inputs; verifies rules load; latency < SLO.
- Signer: sign a synthetic document against test trust roots; verify TSA/OCSP reachability.
- Settings: activate a safe test bundle; diff preview matches expected; revert; validators pass.
- Portal: download approved synthetic artifact; ETag/Range behavior validated; portal invalidation simulated.
- Alert thresholds: burn-rate SLO alerts and synthetic failures must page on-call with proper runbook IDs.

### 12.8 Quotas & metering
*Purpose: Enforce fair‑use and protect performance budgets.*
- Quotas: per‑org limits on uploads/day, concurrent jobs, portal downloads/min; Settings expose knobs and per-org overrides.
- Enforcement: API checks at submission and per request; friendly 429s with `Retry-After` + guidance; dashboards for sustained breaches.
- Metering: counters for usage; monthly exports; tie-in with FinOps budgets; anomaly detection.
- Source material: `§40`, `§57.3`

### 12.9 FinOps dashboards & alert wiring
*Purpose: Ensure cost signals are visible and actionable.*
- Dashboards: `llm_cost_estimate_total`, `finops_cost_per_case_usd`, MoM regression panel, top N expensive cases, budget forecasts.
- Alerts: regression > threshold (default 10%); monthly cap risk > X%; route to Product/SRE with runbooks; annotate releases.
- Acceptance: dashboards exist and alerts fire in staging drill before enabling in prod.

### 12.10 Business continuity & degraded operations
*Purpose: Outline how teams sustain service when automation or guardians fail.*
- **LLM outage:** Pause Compose/Analyze submission queues; switch agents to manual review lane per App.H RB-LLM-003; provide fallback templates for staff authorship. Notify customers via incident template (`INCIDENT_TEMPLATE_LLMDOWN`) with expected recovery window.
- **Guardian impairment:** Freeze approvals that rely on Guardian READY; manual reviewers follow paper checklist (`docs/runbooks/guardian-manual-review.md`) and log decisions as `MANUAL_GUARDIAN_DECISION` artifacts until service recovers.
- **Transcription fallback:** Route urgent audio to vetted human transcription vendor under DPA (no cross-border transfer) with manual import once automated pipeline restored.
- **Communication cadence:** Duty Manager sends initial update within SLA (§1.6) and hourly until resolved; final customer notice includes timeline, data impact, and remediation.
- **Drills:** Semi-annual BCP exercise simulating combined Guardian + LLM outage; evidence stored as `BCP_DRILL_REPORT` artifacts linked in App.H.

### 12.11 Fail-closed behaviors matrix
*Purpose: Summarize safety defaults, their downstream impact, and where to find remediation guidance.*

| Subsystem | Fail-closed behavior | User impact | Runbook |
| --- | --- | --- | --- |
| Guardian | Rejects submissions; artifacts remain `DRAFT` until service recovers | New approvals paused; portal shows READY-only backlog | App.H RB-GUARD-001 |
| Settings Service | New jobs block on snapshot fetch; running jobs continue with embedded snapshots | Operators see queue backlog; activation UI disabled | App.H Standard template + Settings rollback drill |
| Audit seal / WORM | Portal deliveries blocked if seal chain breaks for >1 interval | Reviewers cannot promote artifacts; portal download attempts 503 | App.H RB-AUDIT-004 |
| Residency policy guard | Jobs error with `RESIDENCY_POLICY_BLOCK` on drift | Org must adjust settings or seek waiver before resubmission | App.H RB-RES-BLOCK |
| LLM provider circuit | LangGraph lanes halt once fallback exhausted | Compose/Analyze jobs paused; manual drafting invoked | App.H RB-LLM-003 |

---

## 13) Quality, testing & compliance validation

### 13.1 Test strategy tiers (unit, integration, end-to-end, property)
*Purpose: Provide a holistic testing framework for engineering teams.*
- Unit tests cover models, services, and policies with high type coverage (pyright/mypy). Integration tests simulate agent flows, Guardian decisions, settings activation.
- End-to-end tests orchestrate uploads → Guardian → approval → portal delivery with stubbed providers; nightly in staging.

### 13.2 Property tests & fixtures
*Purpose: Increase confidence in critical invariants and edge cases.*
- Property tests: settings precedence (SYSTEM≺ORG≺CASE), RLS denials without GUCs, idempotency store uniqueness, approval swap exclusivity.
- Fixtures: synthetic audio for long/short transcripts, redaction payloads with seeded PII, sample manifests, decision history rows with varied reasons.
- Test gates: required to pass in CI before promoting settings or rules changes; failure blocks deploy.
- Property-based tests validate UUIDv8 determinism, manifest integrity, and advisory locks across edge cases.
- UUIDv8 vectors from `spec/vectors/uuidv8.json` feed analyze/compose determinism tests ensuring helper outputs remain stable across refactors.
- Coverage targets: ≥ 90% for critical modules (agents, Guardian, Settings) per AGENTS guides.

### 13.3 Governance/privacy acceptance suites
*Purpose: Validate compliance requirements continuously.*
- DSAR/erasure flows, legal hold enforcement, field masking, and break-glass logging validated with synthetic cases.
- Residency matrix: activations that violate regional policies are rejected with `VALIDATION_ERROR`; runtime pre-flight blocks cross-jurisdiction runs (`RESIDENCY_POLICY_BLOCK`).
- Privacy API Spectral stubs warn until GA, then block; endpoints declare security and HMAC; examples avoid PII.

### 13.4 LangGraph contract tests and replay harnesses
*Purpose: Prevent regressions in agent graph behavior and reproducibility.*
- Node idempotency: re-run a completed lane → zero new LLM calls; outputs identical or schema-equivalent.
- Checkpoint resume: kill between Lane QA and Final QA → resume at Final QA without re-calling LLM.
- Cross-lane integrity: conflicting entity/event refs cause Final QA rejection with actionable QA log.
- Fallback correctness: force primary model OPEN circuit → fallback chosen; evidence records circuit state.
- Deterministic IDs: same anchors yield same UUIDv8; changed spans produce new IDs.
- Policy block: simulate region disallowance → `POLICY_BLOCK` in ContextBuilder; token ceilings truncate prompts within bounds.

### 13.5 Deployment gates (FinOps, error budgets, security scans)
*Purpose: Enforce release safety and cost controls.*
- CI gates: type-checks, lint/format, unit/integration, OpenAPI lint, SBOM, image signing; nightly DAST on staging before promotion.
- FinOps: block releases when MoM cost regression exceeds threshold (default 10%).
- Error budgets: breaches block releases until burn rate stabilizes; dashboards link from alerts.
- Vulnerability policy: SCA/SAST/secret scanning on every PR; Criticals block unless risk-accepted.

### 13.6 SBOM & build provenance
*Purpose: Guarantee supply-chain transparency and tamper-evident releases.*
- Builds emit CycloneDX SBOMs (`build/sbom/*.json`) via Syft/Grype; artifacts stored in object storage (`ops/artifacts/sbom/<commit>.json`) with SHA-256 recorded in release manifest.
- Container images signed with Cosign + Sigstore keyless flow; attestations include SLSA provenance (`predicateType: https://slsa.dev/provenance/v1`) capturing git commit, builder, and build inputs. Verification runs in deployment pipelines and documented in App.K evidence.
- SBOM retention: minimum 2 years or life of supported release, whichever longer. Access requires Security or Compliance role; auditors receive read-only bucket link during assessments.
- Third-party dependency diffs reviewed weekly; high-risk packages flagged in `DEPENDENCY_RISK_REPORT` artifacts referenced in App.P.
- OSS licenses and notices shipped with releases are catalogued in App.P.

### 13.7 Secure coding standard & scanning
*Purpose: Establish mandatory guardrails for code quality and vulnerability prevention.*
- Standards: OWASP ASVS L2/L3 controls where relevant; banned APIs list (`docs/security/banned_apis.md`) enforced via custom ruff rules and pyright plugins; secret-scanning (detect-secrets + trufflehog) runs on every PR.
- Coverage targets: unit coverage ≥ 80 % per critical service, integration coverage ≥ 60 %; failing to meet thresholds blocks merge without approved exception logged in App.O risk register.
- Tooling: ruff, mypy, pyright, bandit, semgrep, gitleaks, dependency-review. Critical/High findings must be resolved or explicitly risk-accepted with expiry.
- KPI dashboard tracks open vulns by severity, mean remediation time, and SLA compliance (Critical ≤ 7 days, High ≤ 14 days). Breaches escalate to Security leadership and appear in §15.3 decision log.

### 13.8 Compliance evidence generation (SOC2, privacy records)
*Purpose: Automate artifacts required for audits and regulator reviews.*
- Generate quarterly `SYSADMIN_RECERT_REPORT` artifacts; contract tests assert creation, audit trail, and dual-approval gates.
- Publish DPIA/RoPA record references in audit seals; retain evidence of settings activations and Guardian decisions.
- Diagram drift checks: fail build when diagrams change without source updates; ensure traceability.
- Diagram drift check (binding): CI job `diagram:diff` ensures exported ERD/service-map assets only change alongside their `.mmd`/`.drawio` sources and associated commit notes.

- **Source material:** `§23`, `§31`, `§57`, `§41.7`, `App.E`  
- **Priority:** Medium (QA & compliance alignment)

---

## 14) Operations playbooks & lifecycle
- Glossary: Appendix I captures retention, legal hold, and governance terms referenced in this chapter.

### 14.1 Tenant provisioning & offboarding
*Purpose: Standardize customer lifecycle in ops tools.*
- Provisioning: create org in Keycloak, configure domains (SPF/DKIM), set residency allowlists, budgets, templates, rotate initial secrets. Onboard staff via invites with role assignments.
- Offboarding: disable logins, export data with tamper-evident bundles, revoke keys, enforce retention/erasure, archive audit seals. Checklist recorded in App.H.

### 14.2 Artifact retention, legal hold, and destruction flows
*Purpose: Align document lifecycle with policy and legal requirements.*
- Retention defaults: artifacts ≥ 365 days, audit logs ≥ case retention, privacy artifacts ≥ 730 days (Appendix N). HIPAA mode shortens certain retention and disables excerpt artifacts.
- Legal hold: `case.legal_hold = true` prevents destruction and surfaces reason (masked in secure view). Releases require approvals and audit log entries.
- Destruction: queued jobs with Guardian oversight produce `DESTRUCTION_CERT` artifacts; double-check via manifest before final delete.
- Object lock: production buckets enforce versioning + Object Lock (compliance mode) for audit sinks; destroy operations require dual approval and manifest verification.
- Ops scripts: `ops/scripts/destroy_case.py` (dry-run + execute) logs intended artifacts, checks legal hold, and writes `DESTRUCTION_CERT`; references recorded in Appendix N.
- HIPAA mode enforcement: when `privacy.hipaa.enabled=true`, retention jobs honor shortened schedules, approvals for HIPAA-classed artifacts require WebAuthn step-up, evidence-store excerpts stay disabled, and portal delivery of PHI-tagged attachments is rejected unless a security waiver is recorded.

#### 14.2.1 DSAR/erasure mode (binding)
*Purpose: Support hard-purge erasure requests without compromising provenance.*
- Settings: `compliance.erasure_mode ∈ {'off','hard_purge'}` (ORG) toggles hard purge; `compliance.subject_hkdf_salt` (SYSTEM, KMS-backed) seeds deterministic subject hashes. See Appendix E for key traceability.
- Scope: Hard purge deletes artifacts, QA logs, evidence, and prompts tied to the subject; legal hold supersedes erasure requests and blocks purge.
- Artifact proof: Every purge emits an `ERASURE_JOURNAL` artifact capturing minimal evidence (subject hash, scope, approvals) and referencing the job manifest hash. Guardian review ensures readiness before portal exposure.
- Approval: Dual approval when policy requires (`privacy.dpia.reviewers.roles`), with audit records referencing erasure justification and timestamps. Waivers recorded when residency/retention conflicts arise.
- Process: Scheduler selects eligible records, acquires locks to avoid concurrent purges, performs deletion, writes `ERASURE_JOURNAL`, and appends ops log entry (`ops/<job_id>__erasure_log.json`).
- Restores: Backup restore jobs must replay all applicable `ERASURE_JOURNAL` entries before the recovered case or subject is re-exposed to reviewers or clients.
- Manifest schema (normative):
  ```json
  {
    "schema_version": "erasure@1.0",
    "org_id": "UUID",
    "case_id": "UUID|null",
    "subject_hash": "sha256-hex",
    "scope": ["ARTIFACTS","QA_LOGS","EVIDENCE","PROMPTS"],
    "requested_by_user_id": "UUID",
    "approved_by_user_ids": ["UUID","UUID"],
    "justification": "string",
    "executed_at": "RFC3339",
    "settings_snapshot_sha256": "sha256-hex"
  }
  ```
- Audit: Tombstone audit links preserve chain integrity without retaining content; purge actions emit `audit_event('DSAR_ERASURE_EXECUTED', {...})` with scope, actors, and manifest hash.
- Backups exception: immutable backups are not altered in-place. Instead, restore-point catalogue retains entries ≤ 35 days; if restoration is required, operators immediately re-run DSAR purge on recovered data before bringing case online. Evidence (backup set IDs, purge confirmation) appended to the initiating `ERASURE_JOURNAL`.

### 14.3 Key management & secret rotation
*Purpose: Maintain cryptographic hygiene across services.*
- Secrets stored in Vault/Key Vault; rotation schedule documented (e.g., API HMAC keys quarterly, TLS certs ≤24h TTL). Rotation triggers service reload and Settings activation updates.
- Guardian and Signer keys require dual control. Audit events record rotation actor, key scope, and previous expiration.
- Client-provided keys (email, SMS) stored per org with restricted access; rotation process includes verification with provider.
- Root key material (Vault transit master, signing HSM keys) operates under two-person integrity: no single operator can export or rotate without co-approval. Break-glass escrow requires Security + Platform VP sign-off and generates `KEY_ESCROW_EVENT` artifacts.
- Hardware-backed keys: production signing keys live in cloud HSM (Azure Key Vault HSM) with policy `KV-Policy-Prod-001`; audit logs exported nightly and referenced in App.K evidence.
- Rotation automation pipelines: TLS certs rotate via GitHub Action `secops/rotate-certs.yml`, which writes attestations to `ops/security/cert_rotation/<date>.json` and updates `azure-key-vault://platform-secrets/certs/*`; Guardian/Signer HMAC keys rotate with `ops/security/rotate_guardian_keys.py`. Evidence bundles are attached to App.K control entries.
- Rotation cadence summary: TLS certs ≤24h TTL, API HMAC quarterly, Guardian/Signer keys semi-annually, customer-supplied keys per contract or ≤90 days. Upcoming rotations tracked in change calendar; overdue keys page SecEng.
- Escape hatch: should KMS become unavailable, documented manual signing path (App.H RB-SIGNER-HSM) allows temporary softkey use capped at 24 h with post-incident review.

### 14.4 Vulnerability management & supply chain updates
*Purpose: Keep dependencies secure and up-to-date.*
- Monthly dependency audits using SCA tools; critical CVEs patched within 48h. `ops/security` backlog tracks remediation.
- Infrastructure scanning (container, cluster) integrated with security triage. Penetration testing results stored as artifacts (`PENTEST_REPORT`).
- Supply chain safeguards: pin dependencies, use checksums, enable SBOM generation. Build pipeline signs artifacts and release images.

### 14.5 Change management, versioning, and rollout plans
*Purpose: Ensure coordinated releases across services.*
- Versioning: semantic for APIs, semver-like for settings bundles, `graph_version` for agents. Releases require change tickets referencing TDD sections.
- Rollouts: canary in staging, phased production release, with rollback plan. Documented in App.H runbooks.
- Communication: notify stakeholders (Product, Support, Security) with release notes summarizing changes, risk, and mitigation.
- Case enum migration playbook: settings introduce new `case.status`/`representation_type` values first; DB adds `CHECK ... NOT VALID` constraints, validates post-backfill, and only then removes deprecated values. Deprecations flow through Settings/UI; final removal requires data migration and constraint regeneration.

### 14.6 Organization directory sync (Ops)
*Purpose: Keep org users and roles aligned with upstream IdP/Directory without breaking tenancy or RLS.*
- Scope: sync users, org membership, and role mappings; avoid storing PII beyond required identifiers.
- Integration: Keycloak/SCIM connectors; scheduled and on‑demand sync; diff‑based updates; conflict resolution rules.
- Safety: deny‑by‑default; degraded mode on sync failure; audit changes with actor/source; dry‑run mode for large updates.
- Observability: metrics (`dirsync_changes_total{kind}`, `dirsync_errors_total`), dashboards and alerts for failures.
- Source material: `§44`, roadmap §15.2

### 14.7 Admin governance & recertification
*Purpose: Periodically verify entitlements, policies, and exceptions.*
- Cadence: quarterly recertification; dual approvals for exceptions; step‑up MFA required.
- Artifacts: `SYSADMIN_RECERT_REPORT` and decision logs; surfaced to auditors; retention aligns with §14.2.
- Enforcement: block unsafe policy activations pending recert; alerts on overdue reviews; SSE events for recert windows.
- Automation: scheduled job (`0 3 1 */3 *`) enumerates principals with realm `sysadmin` or elevated org roles and produces structured reports `{principal_id, roles[], last_login, justification?, reviewer_ids[], attested_at}`; Security/Architecture must attest or revoke within 14 days or access is suspended until resolved.
- Source material: `§29.7`

### 14.8 Data migration & seeding operations
*Purpose: Keep schema changes, backfills, and seed data predictable and auditable.*
- Migration pipeline: every schema change ships with forward/backward-safe Alembic migrations plus dry-run artefacts (`migrations/README.md`) enumerating pre/post conditions. Dual-write windows are required when mutating hot tables; toggles live under Settings bundles with rollout/rollback instructions.
- Seed data strategy: baseline organizations, roles, settings bundles, and Guardian rules install via `ops/scripts/bootstrap_platform.py` (idempotent). Seed updates run through the same approval flow as settings activations, with diff previews captured in App.K controls evidence.
- Backfills: long-running data backfills execute in Celery workers with OCC guards, chunked pagination, and advisory locks (`udlock.xact_lock('backfill', ...)`) to prevent overlap. Progress metrics and human logs land in `ops/<job_id>__backfill_log.json`.
- Smoke checks: migrations must register probes (`tests/migrations/test_<id>.py`) verifying secure views, RLS policies, and settings compilers post-upgrade. A staging cutover drill is mandatory before production rollout and recorded in App.M.
- Rollback: documented `down_revision` paths plus data snapshots for destructive changes; rollback playbooks include verification of recompiled policies, rehydrated caches, and SSE stream health.

### 14.9 Security disclosure & penetration testing
*Purpose: Formalize external vulnerability reporting, pentest cadence, and fix SLAs.*
- Vulnerability disclosure: publish `security.txt` at `/.well-known/security.txt` with `Contact: mailto:security@udocket.ca` and `Encryption: https://udocket.ca/pgp/security.asc`. Inbound reports acknowledge within 24h, provide triage results within 3 business days, and target remediation per severity SLA below. Disclosures tracked in the security incident register and mapped to App.K controls.
- Penetration testing: annual third-party assessments at minimum, with additional tests after major architecture changes (new data flows, agent classes, residency waivers). Findings log as `PENTEST_REPORT` artifacts, feed triage dashboards, and require verification of remediation evidence prior to closure.
- Severity SLAs: Critical fixes within 7 days, High within 14 days, Medium within 45 days, Low within 90 days unless risk accepted by Security and Architecture. Exceptions require waiver entries in App.O and Security leadership approval.
- Coordination: bug bounty pilots leverage the disclosure inbox; sanitized findings shared with Product/Ops for customer messaging when impact crosses multi-tenant boundaries.
- Monitoring: security backlog reviewed in weekly governance sync; outstanding high/critical items block releases per §13.4 deployment gates.

- **Source material:** `§14.2`, `§14.5–§14.9`, `§25`, `§37`, `§39`, `App.D`, `App.K–App.O`  
- **Priority:** Medium (Ops + Security)

---

## 15) Roadmap alignment & open questions
- Glossary: Appendix I defines non-functional constraint terminology and deliverable acceptance vocabulary used below.

### 15.1 Near-term milestones (feature gates, migrations)
*Purpose: Keep engineering/program leadership aligned with delivery timeline.*
- Q1: finalize Analyze/Compose LangGraph production rollout, Guardian v2 ruleset, FinOps deploy gate enforcement.
- Q2: Timeline/relationships agent alpha, Settings self-service diff preview UI, improved SSE replay guard.
- Feature flags tracked via Settings bundles; gating decisions recorded in decision log.

### 15.2 Dependencies on external programs (IAM overhaul, infra upgrades)
*Purpose: Highlight work reliant on other teams or vendors.*
- IAM roadmap: Keycloak upgrade, org directory sync integration, potential SSO for enterprise clients (requires Settings and portal changes).
- Infra upgrades: Kubernetes version bump, service mesh migration, storage cost optimization.
- Provider dependencies: Azure Speech SLA adjustments, new LLM providers pending security review.

### 15.3 Risks, mitigations, and decision log
*Purpose: Surface known risks and capture resolution context.*
- Risks: LLM policy drift, Guardian false negatives, residency waiver backlog, staffing for manual reviews.
- Mitigations: continuous evals, rule dry-run/diff, automated waiver stamping, cross-training reviewers.
- Decision log entries include change rationale, date, owners, references to sections impacted.

### 15.4 Outstanding research spikes
*Purpose: Track unresolved technical investigations.*
- Evaluate on-device speech normalization fallback, cross-region replication strategy, privacy-preserving analytics, automated QA suggestions for manual edits.
- Each spike records hypothesis, owner, expected completion, linked documents.

### 15.5 Sunset plan for legacy behaviors and documents
*Purpose: Plan deprecation steps for obsolete flows.*
- Retire prior TDD versions (v6 and earlier) once approvals complete; archive older docs with version tags.

### 15.6 Non-functional constraints (consolidated)
*Purpose: Centralize cross-cutting constraints and SLOs.*
- SLOs: API availability ≥ 99.9%/30d; read P95 ≤ 250ms; write P95 ≤ 500ms; decision P95 ≤ 5m; Compose P95 ≤ 45m.
- Security: TLS 1.3 preferred; mTLS for service‑to‑service; HSTS; CSP; signed images and SBOM.
- Residency: Canada‑only unless waiver; storage/compute pinned per §3.6.
- Privacy: masking, secure views, field‑level encryption (§4.6) for sensitive classes.
- Performance: backpressure via rate limits and quotas; bounded memory for LLM contexts; capped retries.

### 15.7 Deliverables acceptance
*Purpose: Define acceptance gates for major outputs of this program.*
- Platform: end-to-end path (upload→Guardian→approval→portal) passes in staging with synthetic data.
- Governance: runbooks executed; audits verified; settings validators enforce unsafe rules.

### 15.8 Roadmap alignment hooks
*Purpose: Link roadmap milestones to owners and dependencies so this TDD stays actionable.*
- Milestones → Epics:
  - Milestone M1 (Analyze LangGraph GA) → Product epic `P-123`; depends on App.A diagrams, §6.7/§6.11 completion, App.H RB-LLM-003 drill.
  - Milestone M2 (Portal messaging GA) → Product epic `P-207`; references §11.6 and Appendix J; depends on App.A A.8 flow and security review gates (§9.11).
  - Milestone M3 (FinOps deploy guard) → SRE epic `SRE-88`; depends on §8.7, §12.9, FinOps dashboards wiring acceptance.
- Dependency notes: provider template updates (Appendix D) tracked in backlog; cross-team sequence captured in roadmap doc linking to this section.
---

## 16) Search & knowledge retrieval

### 16.1 Indexing model and sources
*Purpose: Provide cross-layer search over artifacts while honoring residency and RBAC.*
- Sources: transcripts (latest approved or job-scoped), Analyze outputs (summaries, outlines, timeline seeds, entity hints), Compose deliverables, QA logs, and selected metadata fields; exclude sensitive raw attachments unless policy allows.
- Indices: full-text (Postgres/ES/OpenSearch) for keyword search; optional vector index for semantic search. Embeddings providers must respect `regions.allowlist.compute`.
- Document identity: each indexed record carries `artifact_id` (and lane/section for Analyze/Compose) to enable deep-linking; titles via shared `unique_title` helper.
- Update policy: on artifact APPROVED, indexers upsert records; on demotion/archival, records are hidden. Index jobs emit ops logs and metrics.
- Locale awareness: analyzers respect document language metadata; cross-language toggle exposes translated artifacts when available with fallbacks.

### 16.2 Retrieval APIs and results
*Purpose: Standardize how clients and agents query and consume results.*
- API: `GET /api/v1/search?case_id&q=&k=&type=` with filters for artifact types. Responses include snippets, highlights, and stable refs (`artifact_id`, lane/section IDs).
- Agents: Analyze/Compose retrieval uses case-scoped search with token ceilings and redaction; results include canonical refs to App.D artifact entries and transcript timestamps when applicable.
- Caching: per-query cache keyed by `(case_id, q, filters)` with short TTL; eviction on artifact state changes.

### 16.3 Security, residency, and RBAC enforcement
*Purpose: Ensure search respects the same deny-by-default policy as reads.*
- Index-time filters store `org_id`, `case_id`, and visibility state; query-time adds RLS-like constraints using the token’s `active_org_id` and case membership. Masked fields remain masked in results.
- Residency: embedding/vector stores must be deployed in allowed regions; cross-region search disabled unless waiver exists and manifests reflect the waiver.
- Audit: log `SEARCH_QUERY_EXECUTED` with hashed query, `case_id`, and filters; redact content; metrics `search_qps`, `search_latency_seconds`, `search_results_per_query_p95`.

### 16.4 Cost, performance, and quality budgets
*Purpose: Keep retrieval affordable and responsive.*
- Budgets: target P95 search latency ≤ 400ms; vector queries capped at `search.vector.max_top_k` with backpressure on sustained load.
- FinOps: track `search_cost_estimate_total` (if using paid vector providers). Circuit open if budget exceeded.
- Quality: relevance evaluated with curated queries and golden answers; dashboards show precision/recall trends.

### 16.5 UI integration and relevance feedback
*Purpose: Close the loop between users and ranking signals.*
- Staff UI: unified search in case workspace with filters; excerpts link to transcript timestamps and Analyze entities/events.
- Feedback: click/expand signals logged (privacy-safe) and fed to relevance tuning jobs. Feature flags control exposure.
- See App.D for searchable artifact types and field maps; §11 for UX constraints; §8 for LLM-powered retrieval compliance.
- Sunset manual artifact upload flow once new staging pipeline fully vetted.
- Plan retirement for non-Settings-based configuration files; ensure agents rely solely on Settings service.

- **Source material:** `§32`, `§33`, `§35`, `§57`, `App.E` decision log  
- **Priority:** Medium (keeps roadmap aligned)

---

## Appendices (link targets)
- **App.A** System context & sequence diagrams *(source: App.A)*  
- **App.B** Threat model catalog *(source: §31, App.B)*  
- **App.C** Data classification & retention matrices *(source: App.C, §15)*  
- **App.D** Canonical artifact catalog *(source: App.F)*  
- **App.E** Settings key map and traceability index *(source: §42)*  
- **App.F** API reference snippets / example payloads *(source: §21.9)*  
- **App.G** ERD and schema migrations history *(source: App.I)*  
- **App.H** Ops runbooks & health check playbooks *(source: §20.3, App.H)*  
- **App.I** Glossary and taxonomy *(source: Glossary, §16 taxonomy notes)*  
- **App.J** SQL policy patterns *(source: §4.4, §11.6)*  
- **App.K** Controls assurance map *(source: §2.2, §12, §14)*  
- **App.L** Benchmark baselines *(source: §3.2, §8, §12)*  
- **App.M** Environment & dependency matrix *(source: §3.2, §14.8)*  
- **App.N** Privacy controls traceability *(source: §2.2, §14.2)*  
- **App.O** Active waivers ledger *(source: §3.6, §7.1.1, §14.9)*  
- **App.P** Third-party & OSS notices *(source: §13.6, App.P)*  
- **App.Q** Sub-processors & DPAs *(source: §3.5, §8, §14.3)*  
- **App.R** Data lineage maps *(source: §5.6, §6, §7)*  
- **App.S** Ownership & RACI map *(source: §1.5, §15)*  

---

## Appendix A — System context & sequence diagrams (normative)
*Purpose: Provide authoritative visuals of service boundaries and key workflows.*
- **A.1 System context:** Updated diagram (`docs/diagrams/system-context-v7.mmd`) depicting web, workers, supporting services, external dependencies, and trust boundaries. Includes overlays for mTLS domains and network policies.
- **A.2 Upload → Guardian → Approve:** Mermaid sequence source `docs/diagrams/upload-guardian-approve-v7.mmd`; shows client upload, staging, artifact creation, Guardian submission, reviewer approval, SSE notifications, and portal invalidation.
- **A.3 Signing & delivery:** Mermaid sequence source `docs/diagrams/signing-delivery-v7.mmd`; covers signing request, TSA/OCSP validation, artifact promotion, link generation, and client download with ETag/If-Match.
- **A.4 Error flows:** Diagram source `docs/diagrams/error-flows-v7.mmd`; illustrates TRANSIENT/POLICY/INPUT/INTEGRITY/CONCURRENCY paths with retries, quarantine, and user feedback.
- **A.5 Approvals UX:** Flow source `docs/diagrams/approvals-ux-v7.mmd`; illustrates staff review, QA, approve/reject, and portal invalidation.
- **A.6 Portal invalidation:** Sequence `docs/diagrams/portal-invalidation-v7.mmd`; shows invalidation path and 403 behavior.
- **A.7 Analyze/Compose pipeline:** Sequence `docs/diagrams/analyze-compose-v7.mmd`; illustrates LangGraph lanes, artifact writes, and Guardian readiness.
- **A.8 Manual/Agent Edit flows:** Flow `docs/diagrams/approvals-edit-flows-v7.mmd`; shows editor flows and promotion/demotion behavior.
- Diagrams maintained via `diagram:diff` CI job; PRs must include source updates (Mermaid/Draw.io) alongside exported SVG/PNG.

---

## Appendix B — Threat model catalog
*Purpose: Centralize high‑value threats, mitigations, and validations (STRIDE).* 

B.1 STRIDE summary (illustrative; see App.H for runbooks)
- Spoofing (identity):
  - Vector: forged inter‑service calls
  - Mitigations: mTLS, HMAC signing (§7.3), short‑lived tokens, audience scoping
  - Validation: synthetic signed/unsigned request tests in staging
- Tampering (data at rest/in transit):
  - Vector: object storage overwrite or man‑in‑the‑middle
  - Mitigations: SSE‑KMS, bucket versioning, strong ETag from SHA‑256, TLS 1.3, WORM audit sink
  - Validation: integrity sweeps, WORM verification
- Repudiation:
  - Vector: missing audit trail of approvals/decisions
  - Mitigations: `audit_event`, `guardian_decision_history`, `delivery_receipt`, SSE correlation IDs
  - Validation: runbook drills; dashboards for decision rates and audit seals
- Information disclosure:
  - Vector: field leakage, portal stale links
  - Mitigations: secure views/masking (§4.5), portal invalidation (§11.2.1), strict CORS/ETag
  - Validation: unit/integration tests, staging drills
- Denial of service:
  - Vector: provider throttling, queue saturation
  - Mitigations: rate limits, circuit breakers, autoscaling, DLQ
  - Validation: synthetics and alert burn‑rate
- Elevation of privilege:
  - Vector: RLS bypass, unsafe settings activation
  - Mitigations: RLS GUC canaries (§4.4), deny‑by‑default policies, dual approval for unsafe changes
  - Validation: activation dry‑run/diff; fail‑closed probes

B.2 Top threats & mitigations (illustrative)
- RLS bypass via pooling misconfig → AdmissionPolicy blocks statement pooling; fail‑closed canaries (§4.4, App.J.6).
- Residency leakage to non‑CA endpoints → mesh egress allowlist; region allowlist settings; Guardian waiver stamping (§3.6, §7.1.1).
- Prompt injection & policy drift → safety harness, golden‑set tests, QA gates, Guardian policy checks (§8.4, §7.1).
- SSE replay abuse → Last‑Event‑ID handling, snapshot rules, token‑bound streams (§10.8).
- Artifact integrity tamper → SHA‑256 ETag, WORM audit sink, integrity sweeps (§5.3, §12.1).

B.3 Abuse controls (illustrative)
- Portal scraping → rate limits, anomaly triggers, forced invalidation, step‑up MFA (§11.2.2, §12.8).
- Messaging misuse → content scanning, attachment limits, abuse reporting, audit trails (§11.6).
- Brute forcing APIs → global/org rate limits, IP throttles, 429 guidance, runbooks (§10.7, §12.6, App.H).
*Purpose: Document top risks, mitigations, and residual risk ratings.*
- **Threat tables:** Expanded STRIDE matrix covering RLS bypass, region leakage, LLM prompt exfiltration, Guardian rule poisoning, signature spoofing, SSE replay, and portal phishing.
- **Mitigation mapping:** For each threat, list preventive/detective controls (section references) and automation coverage (synthetics, alerts). Residual risk rated (Low/Medium/High) with owner.
- **Abuse cases:** Scenarios such as malicious reviewer approval, compromised client account, and mass download scraping with corresponding throttles and anomaly detection.
- **Updates:** Threat catalog reviewed quarterly by Security + Architecture; changes tracked in decision log and referenced in §15.3.

---

## Appendix C — Data classification & retention matrices
*Purpose: Define classification, masking, storage location, and baseline retention.*

C.1 Classification table
| Class | Examples | Masking | Storage | Default retention |
| --- | --- | --- | --- | --- |
| PUBLIC | docs, marketing | none | object storage (public site) | n/a |
| INTERNAL | non‑PII ops logs | redact sensitive fields | object storage (private) | life of case + 2y |
| PII | names, contact info | REDACT/HASH in logs | object storage (private) | life of case + 2y |
| SENSITIVE_PII | health, minors | REDACT in UI logs; NULL in JSON | object storage (private, KMS) | case + 2y (HIPAA may override) |
| HIPAA_PH | medical | REDACT everywhere; no excerpts | object storage (private, KMS) | org policy (shorter) |

C.2 Retention mapping
- Map artifact types to retention groups (see §14.2 baseline and overrides). HIPAA override mode shortens Compose deliverables and disables excerpts.
*Purpose: Align information handling with policy and jurisdictional requirements.*
- **Classification table:** Data classes (PUBLIC, INTERNAL, PII, SENSITIVE_PII, HIPAA_PH) with storage locations, at-rest/in-transit protections, masking requirements, default retention, permitted roles.
- **Residency matrix:** Mapping of `region_tag` to jurisdictions, residency/transfer rules, breach notification SLA (ties into §8.2). Specifies waiver requirements and Guardian stamping expectations.
- **Retention schedules:** Baseline retention for each artifact type (transcripts, analysis outputs, compose deliverables, audit logs, DPIA/ROPA). Includes HIPAA overrides and cross-reference to Appendix N.
- **Compliance dependencies:** Links to legal counsel sign-off and policy documents; updates require dual approval and version bump in Settings (`privacy.legal.matrix_version`).

Retention schedule (baseline; orgs may set stricter)
- Transcripts (TRANSCRIPT): ≥ 365 days from approval or case closure, whichever is later.
- Analyze outputs (SUMMARY/OUTLINE/TIMELINE/ENTITIES): ≥ 365 days; align with transcript retention to preserve traceability.
- Compose deliverables (CLIENT/LAWYER/BUNDLE/QA reports): ≥ 365 days; promoters may archive older versions when a newer APPROVED version exists.
- Ops logs (ops_*.jsonl, per-run JSON): retained for life of case + 2 years in the operational store; dual-streamed to WORM object storage with bucket-level retention locks per audit policy.
- Privacy artifacts (DPIA_RECORD, ROPA_RECORD): ≥ 730 days; listed in audit seals; access limited to `auditor|sysadmin`.
- QA logs: retained for life of case; hidden from portal; included in WORM audit scope.
- Entitlement snapshots and audit events: life of case + 2 years; WORM copies per audit policy.
- Legal hold: any hold on the case supersedes retention timers; destruction jobs must check hold state and emit `DESTRUCTION_CERT` artifacts upon completion.

HIPAA override mode
- Shortens certain retentions (e.g., Compose deliverables) and disables excerpt artifacts; requires explicit activation in Settings with dual approval and audit trail.

---

## Appendix D — Canonical artifact catalog
*Purpose: Define stable artifact types, filenames, directories, and versioning rules consumed by UI, agents, and Guardian.*

General rules
- Filenames are prefixed with `job_id` when tied to a run, and use `_v{n}` suffixes for regenerated versions without overwrite.
- All artifacts persist content SHA-256 in `artifact.content_sha256` and again in the manifest.
- Ops logs are per-run JSON + human-readable `.log`, plus append-only `ops_<agent>.jsonl` at the case level.

Ingestion inputs (binding)

| Artifact type | Purpose | Notes |
| --- | --- | --- |
| EXHIBIT_RAW | Original exhibit uploads (PDF/image/archive) | Stored under `docs/raw/`; Guardian enforces format allowlist prior to parsing. |
| EXHIBIT_TEXT | Parsed/ocr text companion for exhibits | Linked to `EXHIBIT_RAW` via `source.inputs[]`; feeds Analyze search. |
| COURT_DOC_RAW | Court filings or orders as uploaded | Similar handling to `EXHIBIT_RAW`; maintains original casing. |
| COURT_DOC_TEXT | Structured text extraction for court documents | Used for diffing, timeline extraction, and Compose references. |
| EMAIL_RFC822 | Raw RFC822 email payloads (including headers) | Stored encrypted; normalized to `EMAIL_TEXT` and attachments. |
| EMAIL_TEXT | Parsed email body (plaintext/HTML converted) | Preserves header metadata for Guardian/Compose citations. |
| EMAIL_ATTACHMENTS | Individual artifacts emitted per attachment | Guardian scans each attachment; retained under case `docs/attachments/`. |
| FINANCIALS_RAW | Spreadsheet or CSV financial uploads | Normalized before conversion; preserved for audit. |
| FINANCIALS_TABLE | Structured table representation of financial artifacts | Stored as JSON/CSV; downstream analytics consume. |
| MEMO_TEXT_* | Staff/comms memos with deterministic suffix per template | Used by Guardian to validate memo templates and approvals. |

Canonical artifact table

| Artifact type | Directory / pattern | Exclusive | Manifest pointer | Notes |
| --- | --- | --- | --- | --- |
| TRANSCRIPT | `transcript/<job_id>__transcript.txt` | No | `<transcript>.manifest.json` | Header includes case, source, language, hashes |
| AUDIO_NORMALIZED | `audio/<job_id>__<normalized_name>` | No | n/a | PCM 16 kHz mono copy for reproducibility |
| SUMMARY_MD | `analysis/<job_id>__summary_v1.md` | **Yes** | `<summary>.manifest.json` | Human-readable narrative |
| SUMMARY_JSON | `analysis/<job_id>__summary_v1.json` | **Yes** | `<summary>.manifest.json` | Structured narrative (optional) |
| OUTLINE_JSON | `analysis/<job_id>__outline_v1.json` | No | `<outline>.manifest.json` | Hierarchical outline for Compose |
| TIMELINE_SEEDS_JSON | `analysis/<job_id>__timeline_seeds_v1.json` | No | `<timeline_seeds>.manifest.json` | Deterministic UUID per event |
| ENTITY_HINTS_JSON | `analysis/<job_id>__entity_hints_v1.json` | No | `<entity_hints>.manifest.json` | Deterministic UUID per entity/relationship |
| STAFF_REPORT_MD | `analysis/<job_id>__staff_report_v1.md` | No | `<staff_report>.manifest.json` | Required staff report |
| COMPOSE_CLIENT_MD/DOCX | `docs/<job_id>__compose_client_v1.md|docx` | **Yes** | `<compose_client>.manifest.json` | Client-facing deliverable |
| COMPOSE_LAWYER_MD/DOCX | `docs/<job_id>__compose_lawyer_v1.md|docx` | **Yes** | `<compose_lawyer>.manifest.json` | Lawyer deliverable |
| COMPOSE_BUNDLE_EXCERPT_MD | `docs/<job_id>__compose_bundle_v1.md` | **Yes** | `<compose_bundle>.manifest.json` | Excerpt for bundle |
| COMPOSE_STAFF_REPORT_MD | `docs/<job_id>__compose_staff_report_v1.md` | No | `<compose_staff_report>.manifest.json` | QA staff notes |
| COMPOSE_QA_REPORT_MD | `docs/<job_id>__compose_qa_report_v1.md` | No | `<compose_qa_report>.manifest.json` | QA outcomes |
| DPIA_RECORD | `privacy/<job_id>__dpia_v1.json|md` | No | `<dpia>.manifest.json` | DPIA artifact |
| ROPA_RECORD | `privacy/<job_id>__ropa_v1.json|md` | No | `<ropa>.manifest.json` | RoPA snapshot |
| AUDIT_SEAL | `ops/<timestamp>__audit_seal_v1.json` | No | `<audit_seal>.manifest.json` | Rolling Merkle root |
| SIGNATURE_CERT | `docs/<job_id>__signature_cert_v1.json` | No | `<signature_cert>.manifest.json` | Signer certificate bundle |
| ATTACHMENT_RAW | `docs/<job_id>__attachment_raw_v1.bin` | No | `<attachment_raw>.manifest.json` | Source binary for portal messaging/client uploads; Guardian-gated |
| ATTACHMENT_TEXT | `docs/<job_id>__attachment_text_v1.json|md` | No | `<attachment_text>.manifest.json` | Parsed/normalized attachment companion for searchability |
| TIMELINE_V2 (future) | `timeline/<job_id>__timeline_v2.json|md` | TBD | `<timeline_v2>.manifest.json` | Normalize timeline assets; reuse upstream UUIDs |
| ERASURE_JOURNAL | `privacy/<job_id>__erasure_journal_v1.json` | No | `<erasure_journal>.manifest.json` | Hard-purge DSAR evidence; subject hashed with HKDF salt |

Ops logs
- Transcription: `ops/<job_id>__transcription_log.json`, `ops/<job_id>__transcription.log`, case-level `ops_transcription.jsonl`.
- Analyze: `ops/<job_id>__summary_log.json`, case-level `ops_summary.jsonl`.
- Compose: `ops/<job_id>__compose_log.json`, case-level `ops_compose.jsonl`.
- QA diagnostics: `ops/<job_id>__qa_log.json` (internal diagnostics only); reviewer-facing QA outputs stay Guardian-gated artifacts per the table above.

Exclusive types (binding)
- At most one APPROVED per case for `SUMMARY_MD`, `SUMMARY_JSON`, `COMPOSE_CLIENT_*`, `COMPOSE_LAWYER_*`, `COMPOSE_BUNDLE_EXCERPT_MD`.
- Settings may extend `artifact.exclusive_types[]`; Guardian enforces readiness; approval swap logic in §5.4.1.

Sample manifest pointers
- Each artifact includes a manifest conforming to §5.6; examples should be stored beside artifacts as `<filename>.manifest.json` for debugging.

Notes
- Replace `_v1` with `_v{n}` on regenerated artifacts; prior versions remain on disk. UI promotes only approved versions per type exclusivity rules.
- For any new artifact, add a distinct type constant, filename template, directory, and ops logging pattern here before implementation.
- Default downstream integrity action (`integrity.downstream_action`) is `quarantine` for legal deliverables (`COMPOSE_*`, `ATTACHMENT_*`) and `mark_stale` for Analyze narrative artifacts; overrides must be explicitly justified during Settings activation.

---

 

## Appendix E — Settings key map & traceability index
*Purpose: Link platform behavior to configuration keys for audit and troubleshooting.*

E.1 Key catalog (scope: SYSTEM | ORG | CASE)
- regions.allowlist.compute — ORG — [canadacentral, canadaeast] — Allowed compute regions; enforced by §3.6.
- regions.allowlist.storage — ORG — [canadacentral, canadaeast] — Allowed storage regions; enforced by §3.6 and §5.3.
- analyze.model.id — ORG|CASE — default profile — LLM model profile for Analyze lanes; see §8 and §6.3.
- analyze.token_ceiling — ORG|CASE — 100000 — Max tokens per Analyze job; see §8.3.
- analyze.max_retries — ORG|CASE — 2 — Retry budget per lane; see §6.3 QA loops.
- compose.model.id — ORG|CASE — default profile — LLM model profile for Compose; see §8 and §6.4.
- compose.token_ceiling — ORG|CASE — 100000 — Max tokens per Compose job; §8.3.
- compose.max_retries — ORG|CASE — 2 — Retry budget per lane; §6.4.
- compose.policy.forbidden_patterns[] — ORG — [] — Content forbids; §6.4 QA.
- compose.templates.client.template_id — ORG — default — DOCX/MD template selection; §6.4.
- compose.templates.lawyer.template_id — ORG — default — DOCX/MD template selection; §6.4.
- guardian.rules.version — ORG — v1 — Ruleset version; §7.1.
- guardian.decision_slo_ms — SYSTEM|ORG — 300000 — Decision latency SLO; §7.1, §12.
- sign.trust_roots[] — SYSTEM|ORG — [] — Trust roots for signing; §7.2.
- sign.tsa.endpoint — SYSTEM|ORG — null — TSA API endpoint; §7.2.
- sign.tsa.max_time_drift_secs — SYSTEM — 5 — NTP drift tolerance; §7.2, §3.2.
- llm.providers[] — SYSTEM|ORG — [] — Provider catalog; §8.1.
- llm.models[] — SYSTEM|ORG — [] — Model catalog and fallback priorities; §8.1.
- llm.finops.monthly_cap_usd — ORG — 0 (disabled) — Monthly LLM spend cap; §8.3, §13.4.
- api.idempotency.ttl_hours — SYSTEM — 24 — TTL for idempotency; §10.3.
- api.rate_limits.web.rpm_per_org — SYSTEM|ORG — 600 — Org RPM (validated range 10–2000); §10.5.
- api.rate_limits.web.rpm_per_ip — SYSTEM|ORG — 300 — IP RPM (validated range 10–2000); §10.5.
- portal.download.rate_limits.user_rpm — ORG — 60 — Portal download/user (validated range 10–2000); §10.5.
- portal.download.rate_limits.org_rpm — ORG — 200 — Portal download/org (validated range 10–2000); §10.5.
- security.org_switch.step_up_required — SYSTEM — true — Enforce step-up on privilege increase; §4.3.
- security.disclosure.contact — SYSTEM — null — Security.txt contact; §25.1.
- security.disclosure.encryption_key_url — SYSTEM — null — PGP key URL; §25.1.
- security.pentest.cadence — SYSTEM — annual — Pentest schedule; §25.1.
- security.mfa.webauthn_required_roles — ORG — [] — Roles requiring WebAuthn step-up (HIPAA mode); §2.2, §4.3.
- security.session.device_bind.ip_prefix_len_v4 — ORG — 24 — IPv4 prefix length for device binding; §4.3.
- security.session.device_bind.ip_prefix_len_v6 — ORG — 48 — IPv6 prefix length for device binding; §4.3.
- udlock.max_session_hold_seconds — SYSTEM — 300 — Advisory lock hold time; App.H RB-LOCK-006.
- udlock.heartbeat.interval_seconds — SYSTEM — 5 — Heartbeat period; App.H RB-LOCK-006.
- compliance.erasure_mode — ORG — off — Hard-purge toggle for DSAR mode; §14.2.1.
- compliance.subject_hkdf_salt — SYSTEM — managed secret — HKDF salt for DSAR subject hashing; §14.2.1.
- privacy.legal.matrix_version — SYSTEM — semver — Data residency/legal matrix version; App.C.
- privacy.hipaa.enabled — ORG — false — HIPAA override mode toggle; §2.2, §14.2, App.C.
- privacy.hipaa.bundle_version — SYSTEM — semver — HIPAA policy bundle version pin; §2.2, App.C.
- i18n.supported_locales[] — ORG — [en-CA, fr-CA] — Supported locales; §11.3.
- storage.bucket_versioning_required — SYSTEM — true — Bucket versioning must be enabled; §5.3, §12.1.
- storage.remote_hash.enabled — ORG|CASE — false — Record remote hashes for batch inputs; §5.3.
- storage.remote_hash.max_mb — ORG|CASE — 50 — Max remote bytes to hash; §5.3.
- settings.activation.require_dual_approval — SYSTEM — true — Dual approval for unsafe changes; §9.3.
- logging.redaction.enabled — SYSTEM — true — Redact PII in logs; §12.1.
- evidence_store.redacted_excerpts.enabled — ORG — true — Allow storage of prompt/response excerpts; HIPAA mode sets false; §2.2, §8.2.
- llm.finops.override_until — SYSTEM — null — Optional timestamp to temporarily relax FinOps guard (dual approval required); §8.7.

E.2 Traceability map
- Agents → analyze.*, compose.*, llm.* (Sections §6, §8)
- Guardian/Signer → guardian.*, sign.* (Sections §7)
- Storage & integrity → storage.* (Sections §5, §12)
- Portal/Frontend → portal.*, i18n.*, security.* (Sections §11)
- APIs → api.*, rate limits, CORS (Sections §10)
- Operations → udlock.*, logging.*, privacy.legal.*, security.pentest.* (Sections §12, §14, App.H)

E.3 Linting (binding)
- CI must flag settings keys referenced in this document that are missing in service repositories. The `settings:lint-keys` pipeline step runs on every PR and fails the build when discrepancies are detected.
- Script pattern: load Appendix E lists, scan OpenAPI/spec/config code for usage; fail when unmapped keys found.
- Regions/Residency → regions.allowlist.*, privacy.* (Sections §3.6, App.C)
- APIs/Rate limits → api.*, portal.download.* (Sections §10)
- FinOps → llm.finops.* (Sections §8.3, §12.6, §13.4)
- Security/Compliance → security.*, privacy.*, logging.redaction.* (Sections §4, §12, §25)
- Ops/Locks → udlock.* (App.H)

E.3 Audit checklist (activation)
- Include justification, reviewers, validation results (`unsafe_reasons[]`), impacted scopes, and planned rollout. Ensure lints pass (residency, safety, cost) and link to decision log (§15.3).

E.4 Change log
- Maintain a rolling history of key modifications with references to PRs, decision log entries, and rollout notes.

---

## Appendix F — API reference snippets & examples (normative)
*Purpose: Provide signed, idempotent examples to guide integrations.*

F.1 Guardian submit (HMAC + Idempotency-Key)
```bash
curl -sS -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $IDEMP" \
  -H "X-Signature-Key-Id: $KEY_ID" \
  -H "X-Timestamp: $(date -u +%FT%TZ)" \
  -H "X-Request-Signature: $(./scripts/sign.sh body.json)" \
  https://platform.local/api/v1/guardian/submit \
  -d '{"artifact_id":"...","org_id":"...","case_id":"...","content_sha256":"..."}'
```

F.2 Reviews approve (OCC lock implied)
```bash
curl -sS -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  https://platform.local/api/v1/reviews/$ARTIFACT_ID/approve \
  -d '{"note":"Looks good","expected_version":3}'
```

F.3 Signing request (HMAC)
```bash
curl -sS -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Signature-Key-Id: $KEY_ID" \
  -H "X-Timestamp: $(date -u +%FT%TZ)" \
  -H "X-Request-Signature: $(./scripts/sign.sh body.json)" \
  https://platform.local/api/v1/sign \
  -d '{"artifact_id":"...","content_uri":"..."}'
```

F.4 SSE events with Last-Event-ID
```bash
curl -N -H "Authorization: Bearer $TOKEN" \
  -H "Last-Event-ID: $LAST_ID" \
  https://platform.local/api/v1/jobs/$JOB_ID/events
```

Notes
- Headers exposed to browsers per §10.5 CORS; examples avoid PII.
- OpenAPI snippets below are normative; service implementations must keep them in sync with Spectral rules.

F.5 Conditional GET with ETag and range
```bash
curl -I -H "Authorization: Bearer $TOKEN" \
  https://platform.local/api/v1/artifacts/$A/download

curl -L -H "Authorization: Bearer $TOKEN" \
  -H "If-None-Match: \"$ETAG\"" \
  -H "Range: bytes=0-1048575" \
  https://platform.local/api/v1/artifacts/$A/download
```

F.6 CORS preflight
```bash
curl -i -X OPTIONS \
  -H "Origin: https://portal.local" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization, Idempotency-Key, X-Request-Signature, X-Signature-Key-Id, X-Timestamp, If-Match" \
  https://platform.local/api/v1/artifacts/$A/download
```

F.7 Upload Finalize
```yaml
openapi: 3.0.3
paths:
  /api/v1/uploads/{upload_session_id}/finalize:
    post:
      parameters:
        - in: header
          name: X-Signature-Key-Id
          required: true
          schema: { type: string }
        - in: header
          name: X-Timestamp
          required: true
          schema: { type: string, format: date-time }
        - in: header
          name: Idempotency-Key
          required: true
          schema: { type: string }
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [sha256]
              properties:
                sha256: { type: string, pattern: "^[a-f0-9]{64}$" }
                manifest: { type: object }
                auto_submit_guardian: { type: boolean, default: true }
      responses:
        "200":
          description: Finalized
          content:
            application/json:
              schema:
                type: object
                properties:
                  artifact_id: { type: string, format: uuid }
        "409": { description: Conflict (expired/aborted/idempotency mismatch) }
        "412": { description: INTEGRITY_ERROR (hash mismatch) }
      security:
        - oidc: []
        - hmacSignature: []
```

F.8 Guardian Submit
```yaml
openapi: 3.0.3
paths:
  /api/v1/guardian/submit:
    post:
      responses:
        "200": { description: OK, application/json: { schema: { $ref: "#/components/schemas/GuardianDecision" } } }
        "409": { description: Idempotency signature mismatch }
        "412": { description: INTEGRITY_ERROR }
      security:
        - oidc: []
        - hmacSignature: []
components:
  schemas:
    GuardianDecision:
      type: object
      required: [decision, guardian_decision_id]
      properties:
        decision: { type: string, enum: [READY, QUARANTINED] }
        reasons: { type: array, items: { type: string } }
        guardian_decision_id: { type: string, format: uuid }
```

F.9 Review Approve (OCC)
```yaml
openapi: 3.0.3
paths:
  /api/v1/reviews/{artifact_id}/approve:
    post:
      parameters:
        - in: path
          name: artifact_id
          required: true
          schema: { type: string, format: uuid }
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [expected_version]
              properties:
                note: { type: string }
                expected_version: { type: integer, minimum: 0 }
      responses:
        "200": { description: Approved }
        "409":
          description: Conflict (stale version or illegal state)
```

F.10 Rate limit response example (normative)
```jsonc
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 60
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 2025-10-19T21:15:00Z
X-Request-ID: 09c2d6c0-2bdc-4f8e-9f2d-4f64cb9f2e30
{
  "code": "RATE_LIMIT",
  "message": "Per-organization API request ceiling reached.",
  "details": {"retry_after_ms": 60000},
  "correlation_id": "09c2d6c0-2bdc-4f8e-9f2d-4f64cb9f2e30"
}
```
Illustrative payload; redact or mask as needed to comply with §10.5 rules prohibiting PII in examples.

Notes
- Headers exposed to browsers per §10.5 CORS; examples avoid PII.
- Full components (security schemes, shared headers/params) live in service-local specs; CI lints enforce shared rules.

---

## Appendix G — ERD & schema migrations history
*Purpose: Capture database structure evolution and reference diagrams.*
- **ERD:** `docs/erd/udocket-erd-v7.svg` exported from Draw.io source with entity descriptions matching §5.1.
- **Migration ledger:** Table summarizing major migrations (ID, date, purpose, impacted tables). Highlights backward-compatibility considerations and deployment notes.
- **Schema policies:** Links to lint rules ensuring ORM uses secure views, triggers enforcing immutability, and migration templates for advisory locks or partitioning.
- **Tooling:** Instructions for generating ERD updates and running schema diff checks prior to migration PR merge.

---

## Appendix H — Ops runbooks & health check playbooks
*Purpose: Collect operational runbooks referenced from alerts and dashboards; enable fast, consistent remediation.*

### H.1 Runbook index
- RB-GUARD-001 Guardian SLO breach
- RB-QUEUE-002 Backlog saturation & KEDA tuning
- RB-LLM-003 Provider degradation / circuit breaker
- RB-AUDIT-004 Audit seal failure
- RB-PORTAL-005 Download anomaly & link revoke
- RB-LOCK-006 Advisory-lock stale detection & remediation

### H.2 Standard runbook template
- Purpose: one sentence describing the operational objective.
- Signals: metrics/logs/traces that trigger or inform the runbook.
- Triage (5-minute checklist): quick steps to confirm scope, blast radius, and holder liveness.
- Decision tree: conditional actions based on environment and risk (prod vs staging), including guardrails.
- Post-remediation: verification steps to ensure system health and to capture evidence.
- Preventive actions: changes that reduce recurrence (tuning, automation, code fixes).
- Field snippets: vetted commands and SQL queries with placeholders.

### H.3 RB-LOCK-006 — Advisory-lock stale detection & remediation (normative)
Purpose: Detect and remediate session-scoped advisory locks that exceed the configured hold time without breaking correctness.

Signals (any triggers page on-call):
- Metric `udlock_watchdog_stale_total{action=alert}` increased in last 5m
- Lock age P95 > `udlock.max_session_hold_seconds`
- Repeated stale detections for the same `(scope,k)` within 15m

Triage — 5-minute checklist
1) Confirm scope & blast radius
   - Grafana → Advisory Locks dashboard: filter by `scope` and `node_id`.
   - Note affected `case_id`/`job_id` if `k` is of the form `caseId/jobkind` or `org/case/type`.
2) Verify holder liveness
   - Query:
     ```sql
     SELECT r.scope, r.k, r.node_id, r.backend_pid, now()-r.acquired_at AS age, a.state, a.query
       FROM udlock.registry r JOIN pg_stat_activity a ON a.pid=r.backend_pid
      WHERE now()-r.acquired_at > make_interval(secs => :threshold_seconds)
      ORDER BY age DESC;
     ```
   - If `a.state IN ('idle','idle in transaction')` or heartbeat > 2× interval → stale.
3) Check job/case impact (if `scope='jobkind'`)
   - `SELECT id, kind, status, started_at, finished_at FROM job WHERE case_id=:case LIMIT 1;`
   - If job still making progress (recent checkpoints) → prefer notify over terminate.

Decision tree
- Prod default (`udlock.watchdog.kill_stale=false`)
  - Action: Alert only. Post a remediation note in incident channel; ask owner pod to release lock (rolling restart of that worker Deployment if needed).
  - Evidence: attach top 5 rows from the query above and last job checkpoint id.
- Staging / controlled prod exception (approved by on-call SRE + service owner):
  - Terminate session: `SELECT pg_terminate_backend(:backend_pid);`
  - Verify release: lock disappears from `pg_locks`; `udlock.registry` row GC’d within 60s or by `SELECT udlock.gc_registry();`
  - Resume: If a job was blocked, it resumes on next retry loop.

Post-remediation
- Confirm metrics return to baseline (`udlock_locks_held`, `udlock_watchdog_stale_total` plateau).
- Open a defect if the same `(scope,k)` reappears within 24h; include `node_id`, last 200 lines of the worker pod logs, and query plan of the blocking transaction (if any).

Preventive actions
- Ensure all session locks are taken via `udlock.try_lock_i(...)` (instrumented) and held < `udlock.max_session_hold_seconds`.
- Tune `udlock.heartbeat.interval_seconds` to 5–10s; avoid noisy heartbeats (<3s) in production.
- Add a short “finally” clause in workers to call `udlock.unlock(...)` on early abort paths.

Field runbook snippets
- Identify pod from `node_id`: `kubectl get pod -A | grep <node_id>`
- Bounce a single worker pod: `kubectl delete pod <pod> -n <ns> --grace-period=5`
- Force GC registry (safe): `SELECT udlock.gc_registry();`

### H.6 RB-GUARD-QUAR — Guardian quarantine handling (normative)
Purpose: Quickly diagnose and resolve QUARANTINED artifacts without bypassing policy.

Linked alert: `alert_guardian_quarantine_spike` (Grafana: Guardian SLO dashboard).

Signals
- Guardian decisions with `decision=QUARANTINED` increase; reasons include `POLICY_FORBIDDEN_PATTERN`, `INTEGRITY_HASH_MISMATCH`, `SOURCE_NOT_APPROVED`.
- READY backlog drops, approval throughput slows.

Triage
1) Inspect guardian dashboard filtered by `reasons[]` and `org_id`.
2) Sample decisions in `guardian_decision_history_secure`; confirm rules_version and settings snapshot.
3) If `INTEGRITY_HASH_MISMATCH`, verify upload finalize and recompute hash.

Decision
- `POLICY_FORBIDDEN_PATTERN`: notify product; route to QA/Agent edits; consider template or policy updates.
- `SOURCE_NOT_APPROVED`: instruct operator to approve upstream artifact or rebind inputs.
- `REGION`/`DEBUG_MODE_BLOCKED`: enforce settings fix and re-submit.

Post-remediation
- Track READY ratio recovery; log incident with counts per reason.

### H.7 RB-RES-BLOCK — Residency block remediation (normative)
Purpose: Enforce Canada-only residency while providing a waiver path when approved.

Linked alert: `alert_residency_policy_block` (Grafana: Residency dashboard).

Signals
- Errors `RESIDENCY_POLICY_BLOCK` in logs; settings validation failures; egress policy denies to non-CA endpoints.

Triage
1) Confirm org allowlists (`regions.allowlist.*`).
2) Check provider endpoints; DNS drift; mesh egress policies.

Decision
- If legitimate cross-region need: require dual approval (Security + Architecture), set `cross_region_waiver=true`, re-run; Guardian stamps waiver in manifest.
- Else: adjust settings to allowed regions; update provider config.

Post-remediation
- Verify blocks drop to zero; audit waiver usage in ops.

### H.8 RB-ETAG — If-Match/ETag failures (normative)
Purpose: Ensure clients download the exact approved bytes and handle invalidations correctly.

Linked alert: `alert_portal_412_spike` (Grafana: Portal Security dashboard).

Signals
- 412 PRECONDITION_FAILED spikes on portal downloads.

Triage
1) Confirm approval swap or rejection; check portal invalidation events.
2) Verify ETag equals artifact `content_sha256`.

Decision
- Instruct clients to re-fetch metadata and retry with fresh ETag.
- If portal link stale: regenerate signed URL; ensure portal displays denial banner for revoked artifacts.

Post-remediation
- Monitor 412 rate returning to baseline; verify portal behavior in staging.

### H.4 SQL helper — Two-key advisory lock (normative)
Purpose: Provide a stable 64-bit advisory lock key derived from a scope and key, minimizing collisions and supporting both session- and xact-scoped locks.

Helper (PostgreSQL)
```sql
-- Two-part hashing to 64-bit key space
CREATE OR REPLACE FUNCTION udlock.key64(scope text, k text)
RETURNS bigint
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT ((hashtextextended(scope, 0)::bigint << 32)
       #  (hashtextextended(k,     0)::bigint       ))::bigint;
$$;

-- Session-scoped lock wrappers (instrumented variants `*_i` record registry rows)
CREATE OR REPLACE FUNCTION udlock.lock(scope text, k text) RETURNS void AS $$
  SELECT pg_advisory_lock(udlock.key64(scope,k));
$$ LANGUAGE sql VOLATILE;

CREATE OR REPLACE FUNCTION udlock.try_lock(scope text, k text) RETURNS boolean AS $$
  SELECT pg_try_advisory_lock(udlock.key64(scope,k));
$$ LANGUAGE sql VOLATILE;

CREATE OR REPLACE FUNCTION udlock.unlock(scope text, k text) RETURNS void AS $$
  SELECT pg_advisory_unlock(udlock.key64(scope,k));
$$ LANGUAGE sql VOLATILE;

-- Transaction-scoped lock
CREATE OR REPLACE FUNCTION udlock.xact_lock(scope text, k text) RETURNS void AS $$
  SELECT pg_advisory_xact_lock(udlock.key64(scope,k));
$$ LANGUAGE sql VOLATILE;
```

Usage
- Exclusive approval swap: `udlock.xact_lock('case-approval', CONCAT(:org,'/',:case,'/',:type))` (see §5.4.1).
- Overlapping job guard: `udlock.try_lock('jobkind', CONCAT(:case,'/',:kind))` (see §10.3.1).
- Python helper (psycopg3):
  ```python
  from contextlib import contextmanager

  @contextmanager
  def advisory_lock(cur, org_id: str, scope_key: str) -> None:
      cur.execute(
          """
          SELECT pg_advisory_xact_lock(
            (("x" || replace(%s, '-', ''))::bit(128)::bigint >> 64),
            hashtextextended(%s, 0)
          );
          """,
          [org_id, scope_key],
      )
      try:
          yield
      finally:
          cur.execute(
              """
              SELECT pg_advisory_unlock(
                (("x" || replace(%s, '-', ''))::bit(128)::bigint >> 64),
                hashtextextended(%s, 0)
              );
              """,
              [org_id, scope_key],
          )
  ```
- Canonical scopes: `artifact:{artifact_id}`, `case-type:{case_id}/{type}`, `jobkind:{case_id}/{kind}`, `idempotency:{scope}:{key}`, `settings:activate:{scope}/{case_id}`. Align helpers under `udlock.*` to ensure watchdog visibility.

---

## Appendix I — Glossary & taxonomy
*Purpose: Ensure consistent terminology across platform, docs, and UI.*

Glossary entries
- Artifact: Immutable content record with `content_sha256` and manifest; states `DRAFT|READY|QUARANTINED|APPROVED|REJECTED`; `ARCHIVED` flag hides without state change.
- Exclusive type: Artifact type for which a case may have at most one `APPROVED` at a time; enforced by unique index and approval swap (§5.4.1).
- Guardian: Service deciding `READY|QUARANTINED` for artifacts before human approval; writes `guardian_decision_history`.
- Review/Approval: Human action promoting `READY→APPROVED`; idempotent re-approve; may demote prior same-type artifact (§10.3.2).
- Manifest: JSON payload embedded in artifacts capturing provenance (regions, hashes, settings snapshot), tool versions, and inputs (§5.6).
- SSE: Server-Sent Events for streaming job and artifact updates; token-bound; supports `Last-Event-ID`.
- RLS: PostgreSQL Row Level Security enforcing org/case scoping and deny-by-default policies; secure views restrict field access.
- OCC: Optimistic concurrency control using `version` columns to avoid lost updates.
- udlock: Advisory lock helpers (`scope:key`) supporting session and transaction locks with registry visibility.
- Residency waiver: Temporary exception allowing cross-region processing; requires dual approval; manifest stamped and audited (§3.6, §7.1.1).
- FinOps metrics: Cost/time series including `llm_cost_estimate_total`, `finops_cost_per_case_usd`, `finops_mom_regression_flag` used for dashboards and deploy guards (§8.3, §12.9).
- LangGraph node: Typed step in Analyze/Compose graphs (e.g., OutlineBuilder, SectionWriter) producing deterministic outputs with envelopes (§6.7–§6.10).
- Quota: Per-org limits (uploads/day, concurrent jobs, portal downloads) enforced via rate limiting and monitored in §12.8.

## Appendix J — SQL policy patterns (normative)

J.1 Per-request GUC setup
```sql
SELECT set_config('udocket.active_org',    :active_org_uuid::text, true);
SELECT set_config('udocket.active_user',   :active_user_uuid::text, true);
SELECT set_config('udocket.active_roles',  :active_roles_csv, true);
SELECT set_config('udocket.realm_roles',   :realm_roles_csv, true);
SELECT set_config('udocket.operator_scope',:operator_scope, true); -- 'own_cases' | 'all_org_cases'
```

J.2 Helpers (realm role, case membership)
```sql
CREATE OR REPLACE FUNCTION udocket_has_realm_role(role text)
RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT position(',' || role || ',' IN ',' || coalesce(current_setting('udocket.realm_roles', true),'') || ',') > 0
$$;

CREATE OR REPLACE FUNCTION udocket_is_case_member(p_case uuid)
RETURNS boolean LANGUAGE sql STABLE AS $$
  WITH v_user AS (
    SELECT NULLIF(current_setting('udocket.active_user', true),'')::uuid AS uid
  )
  SELECT EXISTS (
    SELECT 1 FROM case_member cm, v_user u
     WHERE cm.case_id = p_case AND cm.user_id = u.uid
  );
$$;
```

J.3 Secure portal messaging RLS (binding)
```sql
-- Threads visible to case members per policy
CREATE POLICY msg_thread_vis ON message_thread
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('MESSAGE_THREAD','read',case_id,NULL,NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('MESSAGE_THREAD','write',case_id,NULL,NULL)
);

CREATE POLICY msg_vis ON message
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('MESSAGE','read',case_id,NULL,NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('MESSAGE','write',case_id,NULL,NULL)
);

CREATE POLICY msg_att_vis ON message_attachment
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('MESSAGE_ATTACHMENT','read',case_id,NULL,NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('MESSAGE_ATTACHMENT','write',case_id,NULL,NULL)
);

CREATE POLICY msg_read_vis ON message_read_receipt
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND EXISTS (
    SELECT 1 FROM message m
    WHERE m.id = message_read_receipt.message_id
      AND udocket_can('MESSAGE','read',m.case_id,NULL,NULL)
  )
);
```

J.4 Messaging tables (illustrative DDL)
```sql
CREATE TABLE message_thread (
  id uuid PRIMARY KEY,
  org_id uuid NOT NULL,
  case_id uuid NOT NULL,
  title text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE message (
  id uuid PRIMARY KEY,
  org_id uuid NOT NULL,
  case_id uuid NOT NULL,
  thread_id uuid NOT NULL REFERENCES message_thread(id) ON DELETE CASCADE,
  author_id uuid NOT NULL,
  body text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE message_attachment (
  id uuid PRIMARY KEY,
  org_id uuid NOT NULL,
  case_id uuid NOT NULL,
  message_id uuid NOT NULL REFERENCES message(id) ON DELETE CASCADE,
  content_uri text NOT NULL,
  content_sha256 text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE message_read_receipt (
  id uuid PRIMARY KEY,
  org_id uuid NOT NULL,
  message_id uuid NOT NULL REFERENCES message(id) ON DELETE CASCADE,
  reader_id uuid NOT NULL,
  read_at timestamptz NOT NULL DEFAULT now()
);
```

J.3 Central allow function (deny-by-default; sysadmin bypass)
```sql
CREATE OR REPLACE FUNCTION udocket_can(p_resource text, p_action text, p_case uuid, p_artifact uuid, p_field text DEFAULT NULL)
RETURNS boolean LANGUAGE plpgsql STABLE AS $$
DECLARE v_org uuid := NULLIF(current_setting('udocket.active_org', true), '')::uuid;
DECLARE v_roles text := coalesce(current_setting('udocket.active_roles', true),'');
DECLARE v_scope text := coalesce(current_setting('udocket.operator_scope', true),'own_cases');
DECLARE r text;
BEGIN
  IF udocket_has_realm_role('sysadmin') THEN RETURN true; END IF;
  IF v_org IS NULL THEN RETURN false; END IF;
  IF p_case IS NOT NULL AND v_scope <> 'all_org_cases' AND NOT udocket_is_case_member(p_case) THEN
    RETURN false;
  END IF;
  FOR r IN SELECT regexp_split_to_table(v_roles, ',') LOOP
    IF EXISTS (
      SELECT 1 FROM effective_permission ep
       WHERE ep.org_id = v_org AND ep.resource = p_resource AND ep.action = p_action AND ep.role = r
         AND ((ep.field IS NULL AND p_field IS NULL) OR (ep.field IS NOT NULL AND ep.field = p_field))
    ) THEN RETURN true; END IF;
  END LOOP;
  RETURN false;
END $$;
```

J.4 RLS policy bindings (selected)
```sql
CREATE POLICY case_visibility ON "case"
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('CASE','read',"case".id,NULL,NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('CASE','write',"case".id,NULL,NULL)
);

CREATE POLICY artifact_visibility ON artifact
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND EXISTS (SELECT 1 FROM "case" c WHERE c.id=artifact.case_id)
  AND udocket_can('ARTIFACT','read',artifact.case_id,artifact.id,NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('ARTIFACT','write',artifact.case_id,artifact.id,NULL)
);

CREATE POLICY gdh_visibility ON guardian_decision_history
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('GUARDIAN_HISTORY','read',artifact_id,NULL,NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('GUARDIAN_HISTORY','write',artifact_id,NULL,NULL)
);

CREATE POLICY ent_hist_vis ON entitlement_snapshot
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('ENTITLEMENT_HISTORY','read',NULL,NULL,NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('ENTITLEMENT_HISTORY','write',NULL,NULL,NULL)
);

CREATE POLICY audit_vis ON audit_event
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('AUDIT_EVENT','read',NULL,NULL,NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('AUDIT_EVENT','write',NULL,NULL,NULL)
);
```

J.5 Secure views and privileges (binding)
```sql
CREATE VIEW case_secure WITH (security_barrier=true) AS
SELECT
  id,
  org_id,
  title,
  representation_type,
  status,
  legal_hold,
  udocket_mask('CASE','legal_hold_reason', legal_hold_reason) AS legal_hold_reason,
  legal_hold_since,
  created_at
FROM "case";

CREATE VIEW artifact_secure WITH (security_barrier=true) AS
SELECT id,
       org_id,
       case_id,
       type,
       state,
       content_sha256,
       CASE
         WHEN (SELECT 1
                 FROM field_mask_rule r
                WHERE r.org_id = artifact.org_id
                  AND r.resource='ARTIFACT'
                  AND r.field='content_uri'
                  AND NOT udocket_can('ARTIFACT','read',artifact.case_id,artifact.id,'content_uri')
              ) IS NULL
         THEN content_uri
         ELSE udocket_mask(content_uri,'REDACT')
       END AS content_uri,
       manifest,
       created_by,
       created_at,
       approved_at,
       approved_by,
       rejected_at,
       rejected_by,
       review_reason,
       version
  FROM artifact;

CREATE VIEW qa_log_secure WITH (security_barrier=true) AS
SELECT id, org_id, case_id, job_id, scope, lane_or_section, notes_md, issues_json, source_artifacts,
       created_by, created_at
  FROM qa_log;

CREATE VIEW guardian_decision_history_secure WITH (security_barrier=true) AS
SELECT id,
       artifact_id,
       org_id,
       idempotency_key,
       decision,
       reasons,
       rules_version,
       settings_snapshot_sha256,
       decided_at
  FROM guardian_decision_history;

CREATE VIEW guardian_decision AS
SELECT DISTINCT ON (artifact_id) artifact_id,
       org_id,
       idempotency_key,
       decision,
       reasons,
       rules_version,
       settings_snapshot_sha256,
       decided_at
  FROM guardian_decision_history
 ORDER BY artifact_id, decided_at DESC, id DESC;

CREATE VIEW delivery_receipt_secure WITH (security_barrier=true) AS
SELECT id,
       artifact_id,
       org_id,
       channel,
       recipient,
       status,
       details,
       created_at,
       provider_event_id
  FROM delivery_receipt;

CREATE VIEW entitlement_snapshot_secure WITH (security_barrier=true) AS
SELECT id,
       org_id,
       user_id,
       token_id,
       active_org_roles,
       realm_roles,
       device_fp,
       ip,
       ua_hash,
       minted_at
  FROM entitlement_snapshot;

REVOKE SELECT ON TABLE "case", artifact, qa_log, guardian_decision_history, delivery_receipt FROM udocket_app;
GRANT  SELECT ON case_secure, artifact_secure,
                  qa_log_secure, guardian_decision_history_secure, delivery_receipt_secure,
                  entitlement_snapshot_secure
       TO udocket_app;
GRANT USAGE ON SCHEMA public TO udocket_app;
```

J.6 Partitioning and rotation (illustrative)
```sql
ALTER TABLE audit_event PARTITION BY RANGE (created_at);
CREATE TABLE audit_event_2025_01 PARTITION OF audit_event
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE delivery_receipt_2025_01 PARTITION OF delivery_receipt
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
ALTER TABLE guardian_decision_history PARTITION BY RANGE (decided_at);
CREATE TABLE guardian_decision_history_2025_01 PARTITION OF guardian_decision_history
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```
- Ops job `ops/db/rotate_partitions.py` creates upcoming partitions and seals older ones; indexes remain local to each partition to limit bloat.

J.7 Operational canaries (fail-closed)
```sql
-- Connect guard: verify all GUCs present
SELECT current_setting('udocket.active_org', true) IS NOT NULL
   AND current_setting('udocket.active_user', true) IS NOT NULL
   AND current_setting('udocket.active_roles', true) IS NOT NULL AS rls_context_ok;

-- Boot probe for PgBouncer pooling
-- Expect ERROR unless transaction/session pooling is in use
SELECT 1 FROM "case" WHERE org_id = current_setting('udocket.active_org', true)::uuid;

-- Search-path and timeout guard
SHOW search_path;   -- expect exactly: pg_catalog, public
SHOW statement_timeout; -- expect >= 30s
```

- Integrity queue health probe ensures rows do not accumulate faster than workers drain; alerts fire on backlog age breaches.

J.8 Integrity scan queue (artifact sweep)
```sql
CREATE TABLE integrity_scan_queue (
  org_id UUID NOT NULL,
  artifact_id UUID NOT NULL,
  enqueued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, artifact_id)
);

INSERT INTO integrity_scan_queue (org_id, artifact_id)
VALUES (:org_id, :artifact_id)
ON CONFLICT DO NOTHING;

SELECT artifact_id
  FROM integrity_scan_queue
 FOR UPDATE SKIP LOCKED
 LIMIT :batch;
```
- Workers quarantine via Guardian (`/api/v1/guardian/quarantine`) and remove rows once reconciled; metrics track backlog size and age.

J.9 Download tokens (signed URL guard)
```sql
CREATE TABLE download_token (
  id UUID PRIMARY KEY,
  artifact_id UUID NOT NULL,
  org_id UUID NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  single_use BOOLEAN NOT NULL DEFAULT FALSE,
  consumed_at TIMESTAMPTZ NULL
);

CREATE INDEX download_token_lookup
  ON download_token (artifact_id, expires_at);

UPDATE download_token
   SET consumed_at = now()
 WHERE id = :token_id
   AND single_use = TRUE
   AND consumed_at IS NULL
   AND expires_at > now()
RETURNING 1;
```
- Fetch logic requires this update to succeed before streaming, then validates artifact state (`APPROVED`), SHA match, region allowlists, and audit logging.

---

## Appendix K — Controls assurance map
*Purpose: Link external controls (SOC 2, ISO 27001, internal policies) to evidence inside this TDD.*

Quick crosswalk (illustrative)
| Control family | See |
| --- | --- |
| SOC2 CC1 / ISO 5 | §2, §15.3, App.S |
| SOC2 CC6 / ISO 9 | §4, App.J |
| SOC2 CC7 / ISO 12 | §12, §14.5, App.H |
| SOC2 CC8 / ISO 14 | §3.2, §12.5, App.L |
| SOC2 PI / ISO 18 | §2.2, §14.2, App.N |
| Vendor CUECs | §3.5, §8, App.Q |

| Control ID / Policy | Scope | Primary coverage (Section/App) | Evidence artifact(s) | Status |
| --- | --- | --- | --- | --- |
| SOC2 CC1.1 / ISO 5.1 | Governance & principles | §2 Core principles; §15.3 Risks | App.K map, App.O waivers ledger, decision log exports | Pass |
| SOC2 CC6.x / ISO 9 | Access control | §4 Identity & RLS; App.J SQL policies | `case_secure`/`artifact_secure` views, Settings activation audit trail (App.E) | Pass |
| SOC2 CC7.x / ISO 12 | Operations & change | §12 Observability; §14.5 Change mgmt | App.H runbooks, Guardian/Signer synthetics, deployment playbooks | Pass |
| SOC2 CC8.x / ISO 14 | Availability & resilience | §3.2 topology; §12.5 capacity | App.L benchmarks, autoscaling dashboards, synthetic monitor reports | Pass |
| SOC2 PI1 / ISO 18 | Privacy & retention | §2.2 regulatory constraints; §14.2 retention | App.N privacy traceability matrix, DPIA/ROPA artifacts | Pass |
| SOC2 CUEC / Vendor reviews | Third-party oversight | §3.5 external integrations; §8 LLM governance | Provider registry health logs, evidence store envelopes, vendor reassessment checklist | Pass |
| Internal POL-SC-01 | Security incident response | §12.3 incident workflows; §14.9 disclosure | Incident register exports, security.txt contact, on-call rotation docs | Pass |
| Internal POL-DS-02 | Data residency | §3.6 region enforcement; §7.1 Guardian decisions | Egress AuthorizationPolicy manifests, App.O waiver entries, ops logs `RESIDENCY_POLICY_BLOCK` | Pass |
| Internal POL-AU-01 | Audit & approvals | §10 API contracts; §11 approvals UX | Guardian history, audit_event partitions, reviewer swap algorithm logs | Pass |
| Internal POL-BCP-03 | Business continuity | §12.10 BCP drills; App.H runbooks | `BCP_DRILL_REPORT` artifacts, incident templates | Pass |

Controls mapped here drive quarterly evidence reviews. Each entry references runbooks, dashboards, or artifacts cited in the final column; missing evidence must be captured before release sign-off.

---

## Appendix L — Benchmark baselines
*Purpose: Capture recent performance and cost baselines that back the documented SLOs.*

| Workload | Date (UTC) | Load profile | P50 / P95 latency | Cost / tokens | Source |
| --- | --- | --- | --- | --- | --- |
| Web API (`GET /api/v1/cases`) | 2025-09-30 | 1k virtual users, 50 RPS step | 0.112 s / 0.238 s | n/a | k6 run `benchmarks/api_caselist.json`, Grafana `web_http_latency_seconds` |
| Guardian READY decision | 2025-10-05 | 500 concurrent submissions, 5k/day | 48 s / 242 s | n/a | Synthetic job `guardian_slo.yaml`, `guardian_decision_latency_seconds` |
| Compose client deliverable | 2025-10-11 | Transcript 9k tokens, default templates | 8.3 min / 21.4 min | 58k tokens | LangGraph harness `compose_benchmark.py`, `llm_cost_estimate_total` |
| Analyze summary lane | 2025-10-11 | Transcript 9k tokens, 4 exhibits | 6.1 min / 13.7 min | 42k tokens | LangGraph harness `analyze_benchmark.py`, `agent_lane_duration_seconds` |
| Portal DOCX download 25 MB | 2025-09-28 | 500 clients, CDN disabled | 310 ms / 480 ms TTFB | n/a | Locust scenario `portal_download.py`, Nginx access logs |

Benchmarks run at least quarterly and after significant infra upgrades using the dedicated synthetic suite (`tests/synthetic/perf/*`). Results update App.L and dashboards referenced in §12.6; deviations ≥10% trigger review prior to release, with raw outputs archived under `ops/perf/<date>/`.

---

## Appendix M — Environment & dependency matrix
*Purpose: Document supported platform versions per environment and upgrade cadence.*

| Component | Dev/Staging | Production | Upgrade policy | Notes |
| --- | --- | --- | --- | --- |
| Kubernetes | 1.29 | 1.28 | Minor upgrades every 6 months; patch monthly | Managed AKS clusters with PodSecurity restricted profile; next prod upgrade Q1 2026; baseline CIS AKS v1.29 |
| Service mesh (Istio) | 1.21.1 | 1.20.4 | N-1 support; canary namespace before prod rollout | mTLS enforced cluster-wide; cert TTL 24h; planned prod bump Q2 2025 |
| Postgres | 15.6 | 15.6 HA | Major every 18 months; logical replication for blue/green | Patroni-managed; statement pooling disabled; HA failover drills quarterly |
| Redis | 7.2 | 7.2 | Patch quarterly; persistence `aof` for broker, none for cache | Managed Azure Cache for Redis Enterprise; next review Q2 2025 |
| Python runtime | 3.12.x | 3.12.x | Security releases within 30 days | Pinned in `Dockerfile` & dependency locks; min supported 3.11 for tooling; deprecation notice 90 days prior |
| Node.js (build) | 20.x LTS | 20.x LTS | Upgrade within 45 days of LTS patch | Build-time only; no runtime exposure; Node 18 blocked since 2025-07 |
| Terraform | 1.8.x | 1.8.x | Upgrade quarterly with module pin review | State stored in Terraform Cloud; nightly drift detection; drift incidents logged in App.H |
| Nginx ingress controller | 1.11.x | 1.10.x | Patch monthly; major with Kubernetes cadence | TLS 1.3 preferred; OCSP stapling enabled; next prod upgrade Q1 2025 |
| Base OS images | Debian 12 | Debian 12 | Rebuild monthly or on critical CVE | Images signed; SBOM generated per build; CIS benchmark level 1 enforced |

Upgrade windows recorded in the change calendar; App.M supports audit inquiries regarding environment parity and planned rollouts.

---

## Appendix N — Privacy controls traceability
*Purpose: Provide a single view from regulatory obligations to settings, gates, and evidence.*

| Obligation (Reg / Article) | Settings / gates | Enforcement point | Evidence artifacts |
| --- | --- | --- | --- |
| Data residency (PIPEDA s.17, GDPR Art.44) | `regions.allowlist.*`, `integrity.downstream_action` | Guardian residency checks (§3.6, §7.1.1) | AuthorizationPolicy manifests, ops `RESIDENCY_POLICY_BLOCK` logs, App.O waivers |
| DPIA / RoPA maintenance (GDPR Art.35/30) | `privacy.dpia.*`, `privacy.ropa.*` | Privacy activation workflow (§9.3) | DPIA/ROPA artifacts, audit seals, App.K mapping |
| HIPAA override mode (HIPAA §164.312) | `privacy.hipaa.enabled`, `security.mfa.webauthn_required_roles`, `evidence_store.redacted_excerpts.enabled` | Dual approval (§9.11), Guardian/portal guards | HIPAA manifest entries, audit events, QA logs |
| Legal hold & retention (GDPR Art.5, CPPA) | `privacy.legal.matrix_version`, `compliance.erasure_mode` | Destruction job approval (§14.2), DSAR scheduler (§14.2.1) | `DESTRUCTION_CERT`, `ERASURE_JOURNAL`, secure views showing masked reasons |
| DSAR / erasure fulfillment (GDPR Art.17) | `compliance.subject_hkdf_salt`, `compliance.erasure_mode` | DSAR operations runbook (§14.2.1) | Ops logs, audit events `DSAR_ERASURE_EXECUTED`, App.H drills |
| Masking & field protection (SOC2 CC6.6) | `field_mask_rule`, `security.field_encryption.*` | Secure views (§4.5) and encryption routines (§4.6) | Masking helper tests, encryption key rotation records |
| Client portal delivery (PIPEDA Safeguards) | `portal.download.rate_limits.*`, `compose.policy.forbidden_patterns[]` | Guardian readiness + portal invalidation (§11.2.1) | Portal invalidation SSE events, QA reports, App.H RB-ETAG output |

Matrix reviewed quarterly with Privacy & Security; updates required whenever referenced settings or obligations change.

---

## Appendix O — Active waivers ledger
*Purpose: Track approved temporary deviations (residency, security, privacy) with expiry and owners.*

| Waiver ID | Category | Scope | Approved by | Effective / Expiry | Conditions | Status |
| --- | --- | --- | --- | --- | --- | --- |
| (none) | — | — | — | — | — | No active waivers |

Process: waiver requests originate via Settings activation metadata or incident response; Security + Architecture approvals required. Entries mirror App.K controls evidence and must include remediation plans before expiry. Stale waivers trigger §12.3 incident workflow.

### Risk acceptances (time-boxed)
| Acceptance ID | Risk description | Owner | Mitigation / Monitoring | Accepted until | Status |
| --- | --- | --- | --- | --- | --- |
| (none) | — | — | — | — | No open risk acceptances |

Risk acceptances capture deviations such as deferred CVE remediation or temporary SLO relaxations. Entries require Security + Product approval, explicit expiry, and linkage to incident/problem tickets. Items auto-escalate to leadership if not reviewed 7 days before expiry.

---

## Appendix P — Third-party & OSS notices
*Purpose: Centralize licensing, attribution, and notice obligations for distributed software.*

| Component / Package | License | Notice location | Additional obligations |
| --- | --- | --- | --- |
| Django | BSD-3-Clause | `licenses/django/LICENSE` | Include copyright notice in customer-facing docs |
| Celery | BSD-3-Clause | `licenses/celery/LICENSE` | Provide acknowledgement in operator manual |
| Azure SDKs | MIT | `licenses/azure-sdk/LICENSE` | No attribution required; note data use terms in App.Q |
| LangGraph | Apache-2.0 | `licenses/langgraph/LICENSE` | Preserve NOTICE text in redistributed binaries |
| ffmpeg | LGPL-2.1 | `licenses/ffmpeg/NOTICE` | Dynamic linking only; provide source offer on request |
| openpyxl | MIT | `licenses/openpyxl/LICENSE` | None |
| Company-specific scripts | Proprietary | `licenses/custom/README.md` | Internal use only; no redistribution without approval |

Process: SBOM generation (§13.6) cross-checks license metadata nightly; discrepancies raise `LICENSE_GAP` alerts. Updated notices shipped in `NOTICE.md` alongside release artifacts.

---

## Appendix Q — Sub-processors & DPAs
*Purpose: List sanctioned data processors, residency posture, and contractual guarantees.*

| Provider | Service | Region(s) in scope | Data classes processed | DPA/Terms highlights |
| --- | --- | --- | --- | --- |
| Microsoft Azure Speech | Transcription (batch/on-demand) | Canada Central / Canada East | Audio uploads, transcript text | DPA §3 forbids training on customer data; residency locked to Canada; 30-day deletion |
| Microsoft Azure OpenAI | LLM inference | Canada Central / Canada East | Prompt excerpts (redacted), generated text | Enterprise agreement disables logging & training; retention ≤ 24h |
| Entrust TSA / OCSP | Timestamping & revocation | Canada | Hashes, certificate metadata | No content retention; logs retained 90 days for audits |
| Twilio SendGrid (optional) | Email delivery | Canada/EU data center | Notification metadata, recipient email | Data residency restriction via regional sub-account; logs 30 days |
| Telnyx | SMS delivery | Canada | Phone numbers, message metadata | Opt-out enforcement, no content mining |
| Back-office transcription vendor (manual fallback) | Human transcription (break-glass) | Canada | Audio, transcript | Activated only under App.H manual fallback; NDA + DPA prohibits data retention beyond 7 days |

All sub-processors contractually commit to “no training on customer prompts/outputs” clauses. Annual review ensures residency alignment; updates trigger customer notification per §12.3.

---

## Appendix R — Data lineage maps
*Purpose: Provide visual traceability from inputs to signed deliverables.*

- **R.1 Artifact lineage overview:** Mermaid diagram `docs/diagrams/data-lineage-v7.mmd` showing flow from audio/exhibits → Transcribe artifacts → Analyze outputs → Compose deliverables → Guardian → Signer → Portal.
- **R.2 UUID provenance:** Table mapping deterministic UUID anchors (transcript spans, timeline events) to downstream artifacts; generated via `scripts/lineage/export_uuid_map.py`.
- **R.3 Audit linkage:** Describes how manifests reference `settings_snapshot_sha256`, upstream artifact IDs, and Guardian decision IDs; includes example JSON in `docs/examples/lineage/compose_client.json`.
- Lineage diagrams must be regenerated with each schema/manifest change; CI `diagram:diff` gate (§13.8) verifies updates. Auditors can cross-check lineage by loading `LINEAGE_REPORT` artifacts produced during quarterly controls testing.

---

## Appendix S — Ownership & RACI map
*Purpose: Clarify accountability for each major area documented in this TDD.*

| Domain / Section | Responsible | Accountable | Consulted | Informed |
| --- | --- | --- | --- | --- |
| Agent pipelines (§6) | Platform AI Lead | Director of Engineering | QA Lead, Product | Support, Customer Success |
| Guardian & Signer (§7) | Security Engineering Lead | CISO | Platform Architecture, Legal | Support, Customer Success |
| LLM governance (§8) | AI Governance Lead | CTO | Security, Privacy Officer | Product, Customer Success |
| Settings platform (§9) | Platform Architecture Lead | Director of Engineering | Security, QA | Support |
| APIs & Integrations (§10) | API Engineering Manager | Director of Engineering | Product, Support | Customers (release notes) |
| Frontend & Portal (§11) | UX Engineering Manager | VP Product | Accessibility SME, Support | Customer Success |
| Observability & Ops (§12) | SRE Manager | VP Engineering | Security, Product | Support, Customers |
| Quality & Compliance (§13) | QA Manager | VP Engineering | Security, Privacy | Product, Customers |
| Operations lifecycle (§14) | Operations Lead | COO | Security, Legal | Customer Success |
| Roadmap & governance (§15) | Product Strategy Lead | VP Product | Architecture, Security | All teams |

RACI reviewed every release train; updates recorded in decision log (§15.3) and mirrored in internal handbook.

- Mesh-controlled pods allow egress only to cluster DNS and the Istio egress gateway; the gateway enforces external destinations via the AuthorizationPolicy allowlist above. Namespaces without the mesh label can define their own policies, but production workloads inherit this baseline.
