# **uDocket — Technical Description Document (TDD)**

> Note: `docs/TDDv7.md` now carries the fully ported structure and content (see Appendix P parity log). This legacy document is retained for historical reference until Architecture/Security approvals flip authority per the migration criteria.

**Audience:** Engineering, Security, QA, Ops, Product
**Purpose:** Authoritative implementation plan derived from the PRD; specifies architecture, data models, interfaces, pipelines, controls, and operational procedures sufficient to build the system end-to-end.

---

## Document controls
| Field | Value |
| --- | --- |
| Version | 0.1-draft |
| Status | Legacy reference (awaiting Architecture/Security archival sign-off) |
| Last updated | 2025-10-19 |
| Primary owners | Platform Architecture, Security Engineering |
| Source PRD | Product strategy baseline (internal) |
| Related references | Root `AGENTS.md`, area `AGENTS.md` files, `docs/typing-roadmap.md`, `docs/typing_refactor_plan.md`, `docs/privacy/residency/` |

### Revision history
| Date | Version | Author | Notes |
| --- | --- | --- | --- |
| 2025-10-19 | 0.1-draft | Platform Architecture | Baseline architecture, security, and pipeline contract captured. |
| 2025-10-19 | 0.1-draft | Codex automation audit | Structural normalization, document controls, heading corrections. |

---

## 1) Architectural overview

### 1.1 Principles
* **Single Source of Truth:** All case files and structured outputs are **artifacts** with immutable **content** and **SHA-256** integrity.
* **Guardian:** Guardian is the last line of defence against policy violations and potential lawsuits. It decides **READY** vs **QUARANTINED** for **artifacts**.
* **Approval gating:** Downstream stages accept **APPROVED** artifacts only; human Review promotes `READY → APPROVED`.
 * **Deterministic IDs; non-deterministic content:** Analyze/Compose **do not** guarantee byte-identical content. **Primary keys use UUIDv7.** We generate **deterministic UUIDv8 only for derived, in-document entities** and guarantee **stable control surfaces** (settings snapshot, model versioning, recorded prompts). Content is validated by **schema and referential invariants**, not byte equality.
* **Isolation by design:** Keycloak RBAC + PostgreSQL RLS + **case membership** enforce strict per-org/per-case segregation (operators default to “own cases”).
* **Region allowlists:** Processing and storage are bound to per-org policies and **fail closed** on non-compliance.
* **Observability:** Jobs, decisions, transitions emit structured telemetry with correlation IDs.
* **Zero-trust by default:** All service-to-service traffic is mutually authenticated (mTLS) and authorized by workload identity; no plaintext intra-cluster traffic is permitted. Certificates are short-lived and rotated automatically (see §1.3, §24).
* **Operational safety defaults:** DB sessions pin `search_path`, enforce sane timeouts, and fail closed if RLS GUCs are missing (details §2.2.2).
* **Settings as a platform:** Central **Settings Service** (system/org/case scopes) governs effective configuration; versioned, auditable, and snapshot-embedded in jobs.
* **Real-time transport policy:** **SSE** for one-way server→client updates (status/progress). **Django Channels** for two-way live controls and collaborative editing.
* **Policy-driven RBAC:** All row/field access is **deny-by-default** and policy-driven from **Settings** (system→org→case). The **only hardcoded exception** is the realm `sysadmin` role, which retains full access. Field-level visibility is enforced via security-barrier views and serializers; no hardcoded per-role logic in queries.


### 1.2 Logical components
* **Web App (ASGI/Django):** Staff UI, client portal, REST APIs, **SSE** endpoints, case/artifact management, reviews.
* **Channels (Django Channels):** Two-way collaboration (editors, approvals, live controls).
* **Workers (Celery):** Long tasks: media normalization, transcription orchestration, Analyze, Compose, Assembly, Delivery, Destruction, Ingestion.
* **Guardian Service (FastAPI):** Artifact **READY/QUARANTINED**; reads org/case **settings** from Settings Service (never caller overrides).
* **Digital Signature Service (FastAPI):** PDF/A signing & verification; manifest; LTV (OCSP/CRL/TSA).
* **LLM Provider Registry:** Provider/model catalog, health, selection, fallback, quotas (Settings-backed).
* **Reference Engine:** International court catalogs, validators, questionnaire layering & versioning.
* **Notification Service:** Outbox → providers (email/SMS/in-app); delivery receipts.
* **Settings Service:** Definitions, bundles, precedence resolution, caching, pub/sub invalidation.
* **Storage Layer:** PostgreSQL (RLS), Object Storage (artifacts & media), Redis (broker/cache).
* **Observability Fabric:** logs/metrics/traces/alerts and runbooks.


### 1.3 Deployment topology
* **Kubernetes**; per-env namespaces. Deployments: `web`, `channels`, `workers`, `guardian`, `signer`, `llm-registry`, `reference`, `notifications`, `settings`, `ingress`, `redis`, object-storage connector, log/metrics agents.
* **Ingress TLS**; **egress policies** restrict provider regions.
* **Service-to-service mTLS with workload identity** (SPIFFE/SPIRE or service mesh equivalent) is **binding**; plaintext intra-cluster calls are denied by policy.
  * **Mesh requirements:** If Istio/Linkerd is used, enforce **STRICT** mTLS, SDS-delivered certs with **TTL ≤ 24h**, and automatic rotation with jitter; deny policy on certs older than 48h.
  * **Certificate SLOs:** 99.9% of cert rotations complete within 5 minutes of expiry; alert if >15 minutes to rotate.
* **Time sync:** Nodes run chrony/NTP with max drift ±100ms; TSA drift checks in §6 depend on this.
* **TLS policy (ingress):** TLS 1.3 preferred and default; TLS 1.2 allowed only where legacy interop is required.
  * **Ciphers:** TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384, ECDHE-ECDSA-AES128-GCM-SHA256, ECDHE-RSA-AES128-GCM-SHA256. OCSP stapling enabled.
* **Managed secrets:** Vault/Key Vault.
* **Object storage:** Azure Blob or S3-compatible (MinIO for dev).
* **Broker:** Redis. **DB:** PostgreSQL with RLS.

---

## 2) Identity, tenancy & RBAC

### 2.1 Keycloak
* **Realm:** `udocket`
* **Clients:** `staff-ui`, `client-portal`, `service-api`, `guardian`, `signer`, `settings`, `notifications`, `llm-registry`, `reference`
* **Organizations:** **Keycloak Organizations** are authoritative for org membership and org-scoped roles.
* **Roles**
  * **Realm-scoped:** `sysadmin`, `auditor` (cross-org per policy).
  * **Org-scoped:** `org_admin`, `org_manager`, `org_operator`, `org_reviewer`, `org_external_counsel`, `org_client`.
* **Token claims (protocol mappers)**
  * `sub`, `email`, `name`
  * `org_ids[]` — Organization UUIDs the user belongs to
  * `active_org_id` — **scalar** UUID the token is minted for
  * `active_org_roles[]` — roles effective in `active_org_id`
  * (optional) `org_directory[]` — `{id, name}` for switcher UX
* **Auth middleware**
  * Trusts only the token: `active_org_id ∈ org_ids[]` and uses `active_org_roles[] ∪ realm_roles[]`.
  * Sets `request.ctx.active_org_id` (no `X-Org-ID` headers accepted for authZ).
  * Populates per-request role context for handlers and RLS.
* **Token lifetimes & step-up**
  * Access tokens: ≤ 15m; Refresh tokens: ≤ 12h (staff) / ≤ 2h (portal). Offline tokens disabled by default; allowlist exceptions only.
  * Step-up MFA asserted via OIDC `acr` claim; server validates `acr` on endpoints flagged as step-up (see §2.3).


### 2.2 RLS & case membership
* All tenant tables include `org_id UUID NOT NULL`.
* **RLS** binds each DB session to `active_org_id` from the token.
* **Case scoping:** `case_member (user_id, case_id, role)` governs per-case access within the active org.
* **Default visibility:** Operators see only their own cases; settings may widen to “all org cases”.
* **Policy-driven allow:** Row and field access are decided by policy compiled from Settings (see **§2.7** & **§36**), with a single hardcoded bypass for the realm `sysadmin` role.

```sql
-- Per-connection GUCs set by middleware using active_org_id from token + settings
SELECT set_config('udocket.active_org', :active_org_uuid::text, true);
SELECT set_config('udocket.active_user', :active_user_uuid::text, true);
SELECT set_config('udocket.active_roles', :active_roles_csv, true); -- e.g. 'org_admin,org_operator'
SELECT set_config('udocket.realm_roles', :realm_roles_csv, true);   -- e.g. 'sysadmin'
SELECT set_config('udocket.operator_scope', :operator_scope, true); -- 'own_cases' | 'all_org_cases'

-- Realm role helper (for sysadmin bypass)
CREATE OR REPLACE FUNCTION udocket_has_realm_role(role text)
RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT position(',' || role || ',' IN ',' || coalesce(current_setting('udocket.realm_roles', true),'') || ',') > 0
$$;

-- Case membership helper
CREATE OR REPLACE FUNCTION udocket_is_case_member(p_case uuid)
RETURNS boolean LANGUAGE sql STABLE AS $$
  WITH v_user AS (
    SELECT NULLIF(current_setting('udocket.active_user', true),'')::uuid AS uid
  )
  SELECT EXISTS (
    SELECT 1
      FROM case_member cm, v_user u
     WHERE cm.case_id = p_case
       AND cm.user_id = u.uid
  );
$$;

-- Policy tables (compiled by Settings activation job) — see §3.2 for DDL
-- effective_permission(org_id, resource, action, role, field NULLABLE)
-- field_mask_rule(org_id, resource, field, mask, allowed_role)

-- Central allow function (deny-by-default; sysadmin bypass)
CREATE OR REPLACE FUNCTION udocket_can(p_resource text, p_action text, p_case uuid, p_artifact uuid, p_field text DEFAULT NULL)
RETURNS boolean
LANGUAGE plpgsql STABLE AS $$
DECLARE v_org uuid := NULLIF(current_setting('udocket.active_org', true), '')::uuid;
DECLARE v_roles text := coalesce(current_setting('udocket.active_roles', true),'');
DECLARE v_scope text := coalesce(current_setting('udocket.operator_scope', true),'own_cases');
DECLARE r text;
BEGIN
  IF udocket_has_realm_role('sysadmin') THEN RETURN true; END IF;
  IF v_org IS NULL THEN RETURN false; END IF;

  -- Enforce operator scope: when scoped to own_cases and a case is in play, deny if caller is not a member
  IF p_case IS NOT NULL AND v_scope <> 'all_org_cases' THEN
    IF NOT udocket_is_case_member(p_case) THEN
      RETURN false;  -- short-circuit deny (realm sysadmin already handled above)
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
  AND EXISTS (SELECT 1 FROM "case" c WHERE c.id=artifact.case_id)
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
ALTER TABLE "case"     FORCE ROW LEVEL SECURITY;
ALTER TABLE artifact   FORCE ROW LEVEL SECURITY;
ALTER TABLE job        FORCE ROW LEVEL SECURITY;
ALTER TABLE qa_log     FORCE ROW LEVEL SECURITY;
ALTER TABLE delivery_receipt FORCE ROW LEVEL SECURITY;
ALTER TABLE guardian_decision_history FORCE ROW LEVEL SECURITY;
```

> Instruction (unchanged): Middleware must set all GUCs per connection. If a GUC is missing, `current_setting(..., true)` returns NULL, which safely denies access.

**Session hardening (binding)**
* On every request/worker task start, set:
  * `SET LOCAL search_path = pg_catalog, public;`  -- prevent malicious implicit name resolution
  * `SET LOCAL statement_timeout = '30s';`
  * `SET LOCAL idle_in_transaction_session_timeout = '15s';`
  * `SET LOCAL lock_timeout = '5s';`
  * `SET LOCAL deadlock_timeout = '200ms';`
* Enforce `ALTER DEFAULT PRIVILEGES` for `udocket_app` to avoid accidental base table grants.


#### 2.2.1 Field-level masking views
Use security-barrier views for field controls; all read paths must select from these views:
```sql
-- Enable pgcrypto for HASH mask
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Masking helper (uses field_mask_rule; sysadmin sees cleartext)
CREATE OR REPLACE FUNCTION udocket_mask(p_resource text, p_field text, p_value text)
RETURNS text
LANGUAGE plpgsql STABLE AS $$
DECLARE v_org uuid := NULLIF(current_setting('udocket.active_org', true),'')::uuid;
DECLARE v_roles text := coalesce(current_setting('udocket.active_roles', true),'');
DECLARE r text;
BEGIN
  IF udocket_has_realm_role('sysadmin') THEN RETURN p_value; END IF;
  FOR r IN SELECT regexp_split_to_table(v_roles, ',') LOOP
    IF EXISTS (SELECT 1 FROM field_mask_rule f
               WHERE f.org_id=v_org AND f.resource=p_resource AND f.field=p_field AND f.allowed_role=r) THEN
      RETURN p_value;
	END IF;
  END LOOP;
  CASE (SELECT f.mask FROM field_mask_rule f
        WHERE f.org_id=v_org AND f.resource=p_resource AND f.field=p_field LIMIT 1)
    WHEN 'REDACT' THEN
      RETURN '[REDACTED]';
    WHEN 'HASH'   THEN
      RETURN encode(digest(coalesce(p_value,''), 'sha256'), 'hex');
    WHEN 'LAST4'  THEN
      RETURN right(p_value, 4);
    WHEN 'NULL'   THEN
      RETURN NULL;
    ELSE
      RETURN NULL;
  END CASE;
END $$;

CREATE VIEW case_secure WITH (security_barrier=true) AS
SELECT
  id, org_id, title, representation_type, status, legal_hold,
  udocket_mask('CASE','legal_hold_reason', legal_hold_reason) AS legal_hold_reason,
  legal_hold_since, created_at
FROM "case";

CREATE VIEW artifact_secure WITH (security_barrier=true) AS
SELECT
  id, org_id, case_id, type, state, archived, archived_at, archived_by,
  udocket_mask('ARTIFACT','content_sha256', content_sha256) AS content_sha256,
  -- Use JSON-aware masking to avoid invalid casts when masking occurs
  udocket_mask_json('ARTIFACT','manifest', manifest) AS manifest,
  content_uri, created_by, created_at, approved_at, approved_by, rejected_at, rejected_by, review_reason, version
FROM artifact;

-- JSON masking helper: only REDACT/NULL are supported for JSON fields.
-- Policy compile MUST reject HASH/LAST4 masks on JSON columns.
CREATE OR REPLACE FUNCTION udocket_mask_json(p_resource text, p_field text, p_value jsonb)
RETURNS jsonb
LANGUAGE plpgsql STABLE AS $$
DECLARE v text;
BEGIN
  v := udocket_mask(p_resource, p_field, p_value::text);
  IF v IS NULL THEN
    RETURN NULL;
  ELSIF v = '[REDACTED]' THEN
    RETURN to_jsonb(v);
  ELSE
    RETURN p_value;     -- visible
  END IF;
END $$;
```

> Instruction: Middleware must set all four GUCs per connection. If a GUC is missing, current_setting(..., true) returns NULL, which safely denies access via the policy.
> Use a request-scoped transaction and `set_config(..., true)` (LOCAL) at the **start** of each request/worker task. With PgBouncer, avoid “statement” pooling; use “session/transaction” pooling to ensure GUC visibility per transaction.


##### 2.2.1.1 DB privileges & secure views (binding)
* To prevent accidental bypass of masking/RLS, the application role must not `SELECT` base tables.
* All reads go through `*_secure` **security-barrier** views.

```sql
-- Application role (adjust name if different in your env)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'udocket_app') THEN
    CREATE ROLE udocket_app NOINHERIT;
  END IF;
END $$;

-- Pass-through secure views for tables without masked fields (still security-barrier)
CREATE VIEW qa_log_secure WITH (security_barrier=true) AS
SELECT id, org_id, case_id, job_id, scope, lane_or_section, notes_md, issues_json, source_artifacts,
       created_by, created_at
  FROM qa_log;

CREATE VIEW guardian_decision_history_secure WITH (security_barrier=true) AS
SELECT id, artifact_id, org_id, idempotency_key, decision, reasons, rules_version,
       settings_snapshot_sha256, decided_at
  FROM guardian_decision_history;

CREATE VIEW delivery_receipt_secure WITH (security_barrier=true) AS
SELECT id, artifact_id, org_id, channel, recipient, status, details, created_at, provider_event_id
  FROM delivery_receipt;

-- Revoke direct reads from base tables; grant reads only on secure views
REVOKE SELECT ON TABLE "case", artifact, qa_log, guardian_decision_history, delivery_receipt FROM udocket_app;
GRANT  SELECT ON case_secure, artifact_secure,
                  qa_log_secure, guardian_decision_history_secure, delivery_receipt_secure
       TO udocket_app;
-- Allow resolving view names in the schema, but not base tables
GRANT USAGE ON SCHEMA public TO udocket_app;
```

**ORM rule (binding):** DAL/ORM query builders MUST reference `*_secure` views for reads.
CI enforces this with a linter that rejects `FROM "case"` or `FROM artifact` in app code (migrations/tests excluded).


#### 2.2.2 RLS/GUC operational canaries (fail-closed)
* **Connect guard:** all authenticated web/worker requests must first set GUCs and execute:
  ```sql
  SELECT current_setting('udocket.active_org', true) IS NOT NULL
       AND current_setting('udocket.active_user', true) IS NOT NULL
       AND current_setting('udocket.active_roles', true) IS NOT NULL
    AS rls_context_ok;
  ```
* If `rls_context_ok=false` → **403** and log `RLS_CONTEXT_MISSING`.
* **PgBouncer guard (binding):** On startup, each service executes a RLS-gated probe under a fresh connection. If the probe succeeds while `pool_mode=statement`, the process **exits non-zero** with error `PGB_STRICT_MODE_REQUIRED`. A Kubernetes **AdmissionPolicy** rejects Pods configured with PgBouncer statement pooling.
  ```text
  Boot probe:
    SELECT 1 FROM "case" WHERE org_id = current_setting('udocket.active_org', true)::uuid;
    Expectation: ERROR (missing GUCs) unless transaction/session pooling is in use.
  Policy: Pod Admission denies PgBouncer with pool_mode=statement.
  ```
* **Health canary:** `/readyz` performs a read against a known canary table under RLS and fails if rows visible ≠ expected.
* **Worker scoping:** Celery tasks **must** open a new DB connection (or reset session) per task and set GUCs before any query. Reuse only with **transaction pooling**.

* **Search-path & timeout canary:** `/readyz` verifies `show search_path` returns exactly `pg_catalog, public` and `statement_timeout >= 30s`; mismatch → fail readiness.

```
Runtime invariant (normative): Any Postgres query executed without GUCs MUST be denied by RLS. If PgBouncer switches to statement pooling, health checks fail and ingress returns 503.
```


### 2.3 MFA & step-up
* **MFA required for:** `sysadmin`, `org_admin`, `org_manager`, `org_reviewer`.
* **Step-up MFA** for: break-glass, template/policy activation, certificate issuance, client signoff initiation.


### 2.4 Break-glass
* Endpoint requires step-up MFA + justification + duration; emits `BreakGlassEvent`
* **Enforced auto-expiry** at DB (CHECK on `expires_at > now()`) with watchdog that terminates sessions at expiry
* Post-hoc review queue.


### 2.5 Multi-org behavior & org switcher
* **UI switcher:** Uses `org_directory[]` (`{id, name}`) from token claims when present; otherwise calls a read-only directory endpoint to resolve names for `org_ids[]`. Selecting an org triggers **OIDC re-auth** to mint a token with that `active_org_id`.
* **Security:**
  * Switching to an org that increases effective privilege **requires step-up MFA by default**
    (`security.org_switch.step_up_required=true` at SYSTEM scope; orgs may relax only with a documented risk acceptance).
  * Emit `audit_event('ORG_SWITCH', {from_org, to_org})`.
* **Real-time:** On org switch, **close SSE/WS** connections and re-establish with the new token to prevent cross-org leakage.
* **APIs:** No custom org headers; authorization derives solely from `active_org_id` in the token.

> **Note:** We do **not** maintain a `user_org_membership` DB table; Keycloak Organizations are the source of truth. We only mirror Organization metadata (id/name) for FK/labels and rely on token claims for enforcement.


#### 2.5.1 Token binding & session fixation
* Access tokens are **bound** to `active_org_id` and a device fingerprint hash; on org switch we mint a new token and invalidate WS/SSE for the prior token.
  * **Device fingerprint derivation (binding):**  
    `ua_hash = SHA256(lower(User-Agent))` (canonicalized)  
    `ip_fingerprint = IPv4 /24, IPv6 /48` (NAT-tolerant)  
    `device_fp = SHA256(ua_hash || ':' || ip_fingerprint)`
  * Tokens include a `device_fp` **claim**; servers verify it against the derived fingerprint and reject on mismatch (step-up or full re-auth required on mismatch).
* Session fixation: after org switch, the server rotates session identifiers and CSRF tokens; clients MUST discard old tokens.
* UX: switching into an org that increases privileges displays a step-up MFA interstitial with a summary of **new effective roles**.
* **Replay guard:** server echoes `Idempotency-Key` and `X-Request-ID` on successful mutating requests to bind UI flows to a single session/token.


### 2.6 Locking strategy & concurrency helpers (global)
**Goal:** Maximize throughput while preventing race conditions. Prefer constraints and atomic predicates; add OCC on hot rows; reserve advisory locks for cross-row, multi-statement invariants. Default isolation: **READ COMMITTED**.

**Hierarchy & order:** Always acquire locks in the order **org → case → artifact/job/subject**.

**Primitives:**
1. **Constraints & atomic updates** (first choice): `UNIQUE`/partial indexes, `CHECK`, FK; `UPDATE ... WHERE <state_predicates>`.
2. **Optimistic Concurrency Control (OCC):** `version INT NOT NULL DEFAULT 0`; `... AND version=:expected_version` + `version=version+1`.
3. **Row locks** when read→compute→write on a *single row*: `SELECT ... FOR UPDATE`.
4. **Advisory locks** only for cross-row invariants (e.g., exclusive approval swap; job single-flight). Use two-key locks scoped by org.
5. **Instrumented locks (watchdog-ready):** use `udlock.*_i(...)` wrappers (see §3.3) to emit lock registry rows + heartbeats for **session-scoped** advisory locks; xact-scoped locks remain lightweight but are visible to the watchdog via `pg_locks`.

**Two-key advisory lock helper (SQL):**
```sql
-- lock_key1: org UUID high 64 bits; lock_key2: scoped hash
SELECT pg_advisory_xact_lock(
  (("x" || replace(:org_id::text, '-', ''))::bit(128)::bigint >> 64),
  hashtextextended(:scope_key, 0)
);
```

**Python helper (psycopg3):**
```python
from contextlib import contextmanager

@contextmanager
def advisory_lock(cur, org_id: str, scope_key: str):
    cur.execute(
        """
        SELECT pg_advisory_xact_lock(
          (("x" || replace(%s, '-', ''))::bit(128)::bigint >> 64),
          hashtextextended(%s, 0)
        );
        """,
        [org_id, scope_key],
    )
    yield  # released on tx end
```

**Canonical scopes (helpers):**
* `with_artifact_lock(org_id, artifact_id)` → `scope_key = 'artifact:'||artifact_id`
* `with_case_type_lock(org_id, case_id, type)` → `scope_key = case_id||'/type:'||type`
* `with_job_kind_lock(org_id, case_id, kind)` → `scope_key = case_id||'/jobkind:'||kind`
* `with_idempotency_lock(org_id, scope, key)` → `scope_key = scope||':'||key`
* `with_settings_activate_lock(org_id?, scope, case_id?)` → `scope_key = 'settings:activate:'||scope||'/'||coalesce(case_id,'-')||'/'||coalesce(org_id,'-')`

**Where to apply which:**
* **Artifact transitions**: atomic predicates + OCC; advisory lock only for *exclusive-swap*.
* **Reviews (approve/reject)**: advisory case/type lock + OCC on target artifact.
* **Job lifecycle**: OCC on `job`; advisory `with_job_kind_lock` to single-flight `case×kind`.
* **Outbox**: OCC on `outbox_delivery` to avoid worker/webhook races.
* **Advisory-lock hygiene**: session-scoped locks must be **short-lived (< max_hold_s)** and created through `udlock.try_lock_i(...)` so the watchdog can attribute/alert (§41.8).
* **Settings activation**: advisory `with_settings_activate_lock` + OCC on `setting_bundle`.
* **Download tokens & integrity queue**: rely on atomic `UPDATE ... WHERE` and `ON CONFLICT DO NOTHING`.


### 2.7 Policy-driven RBAC & Field Controls
* **Source of truth:** Settings (system→org→case) define resource actions and field masks.
* **Compilation:** On settings activation, a job compiles JSON policy into compact DB tables `effective_permission` and `field_mask_rule` for fast RLS decisions.
* **Lint:** Reject `field_mask_rule` entries that apply `HASH` or `LAST4` to JSON fields; only `REDACT`/`NULL` are valid for JSON.
* **Deny-by-default:** Absence or parse failure of policy denies access; `sysadmin` (realm role) is the only built-in bypass.
* **Enforcement:** RLS uses `udocket_can(...)`; field visibility via `*_secure` views and the `udocket_mask(...)` helper; serializers must not bypass views.
* **Caching:** Web/workers keep a hot cache (LRU) for permission checks; invalidated by `settings.changed` pub/sub.
**Note:** Compiled policies **must** include auditor visibility for `ENTITLEMENT_HISTORY.read` (e.g., `auditor|sysadmin`), otherwise entitlement snapshots will be invisible under RLS.

---

## 3) Data model (relational)

### 3.1 Conventions
* **Primary keys:** `UUIDv7` (app-generated) for artifacts and other row identities.
* **Deterministic derived IDs:** `UUIDv8` for in-document derived entities (Analyze/Compose), using HMAC salt (see §27).
* **Timestamps:** `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`.
* **Artifact immutability:** `content_uri`, `content_sha256`, and `manifest` are write-once per artifact row.
* **Artifact states (approval-gated):**
  `DRAFT` → `READY` → `APPROVED` (consumable) or `REJECTED`; `QUARANTINED` on Guardian failure.
  **State semantics:**
  - `REJECTED` is **terminal**; to proceed, emit a **new artifact** (content is immutable).
  - `QUARANTINED` is **not terminal**; the same artifact may transition to `READY` after a **successful re-evaluation by Guardian** (e.g., rule/policy corrections). If remediation requires content change, create a new artifact per immutability.
* **Exclusive types:** Enforced at **approval time** (not by Guardian). At most one `APPROVED` artifact per `(case_id,type)`.
* **Archived flag:** `archived BOOLEAN DEFAULT FALSE` hides from defaults without changing state.
* **Manifests:** Pydantic-validated at API boundary.
* **Indices:** composite org/case keys; GIN on JSONB; FTS as needed.
* **OCC columns:** Hot rows carry `version INT NOT NULL DEFAULT 0` (artifact, job, outbox_delivery, setting_bundle).

### 3.2 Core tables (selected)
```sql
-- Policy compilation targets (settings → DB)
CREATE TABLE effective_permission (
  org_id UUID NOT NULL,
  resource TEXT NOT NULL,
  action   TEXT NOT NULL,
  role     TEXT NOT NULL,
  field    TEXT NULL,
  PRIMARY KEY (org_id, resource, action, role, field)
);
CREATE INDEX effperm_lookup ON effective_permission (org_id, resource, action, role);

CREATE TABLE field_mask_rule (
  org_id UUID NOT NULL,
  resource TEXT NOT NULL,
  field    TEXT NOT NULL,
  mask     TEXT NOT NULL CHECK (mask IN ('REDACT','NULL','HASH','LAST4')),
  allowed_role TEXT NOT NULL,
  PRIMARY KEY (org_id, resource, field, allowed_role)
);
CREATE INDEX fieldmask_lookup ON field_mask_rule (org_id, resource, field);

-- Manifest versioning fields (add to ArtifactManifest in §4.1 and DB manifest content)
-- Add (conceptually) to JSON: { "schema_version": "analyze@1.0", "graph_version": "analyze@v1" }

-- FK ON DELETE policies (documented practice)
-- organization(id) -> RESTRICT (except directory sync archival flag)
-- case(id) -> RESTRICT by default; destruction flow handles deletes
-- user_account(id) -> SET NULL for created_by/approved_by/rejected_by to keep artifacts viewable

-- Dynamic exclusivity index
-- If settings.artifact.exclusive_types[] expands, we maintain a generated index per type pattern.
-- Baseline index remains (one_approved_per_case_type); settings activation job validates coverage.
```


```sql
CREATE TABLE organization (
  id          UUID PRIMARY KEY,
  name        TEXT NOT NULL,
  settings    JSONB NOT NULL DEFAULT '{}'::jsonb,
  region_allowlist JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  archived_at TIMESTAMPTZ NULL
);

CREATE TABLE user_account (
  id             UUID PRIMARY KEY,           -- UUIDv7
  keycloak_sub   TEXT UNIQUE NOT NULL,
  email          TEXT NOT NULL,
  display_name   TEXT,
  default_org_id UUID NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  archived_at    TIMESTAMPTZ NULL,
  archived_by    UUID NULL
);

CREATE TABLE case (
  id            UUID PRIMARY KEY,            -- UUIDv7
  org_id        UUID NOT NULL REFERENCES organization(id),
  title         TEXT NOT NULL,
  representation_type TEXT NOT NULL,         -- validated by Settings
  status        TEXT NOT NULL,               -- validated by Settings
  created_by    UUID NULL REFERENCES user_account(id),
  legal_hold    BOOLEAN NOT NULL DEFAULT FALSE,
  legal_hold_reason TEXT,
  legal_hold_since  TIMESTAMPTZ,
  archived      BOOLEAN NOT NULL DEFAULT FALSE,
  archived_at   TIMESTAMPTZ NULL,
  archived_by   UUID NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE case_member (
  user_id    UUID NOT NULL REFERENCES user_account(id),
  case_id    UUID NOT NULL REFERENCES "case"(id),
  role       TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, case_id)
);

CREATE TABLE artifact (
  id               UUID PRIMARY KEY,         -- UUIDv7
  org_id           UUID NOT NULL REFERENCES organization(id),
  case_id          UUID NOT NULL REFERENCES "case"(id),
  type             TEXT NOT NULL CHECK (type ~ '^[A-Z0-9_]+$'),
  state            TEXT NOT NULL CHECK (state IN ('DRAFT','READY','APPROVED','REJECTED','QUARANTINED')),
  archived         BOOLEAN NOT NULL DEFAULT FALSE,
  archived_at      TIMESTAMPTZ NULL,
  archived_by      UUID NULL,
  content_uri      TEXT NOT NULL,            -- write-once
  content_sha256   CHAR(64) NOT NULL,        -- write-once
  manifest         JSONB NOT NULL DEFAULT '{}'::jsonb,  -- write-once
  created_by       UUID NOT NULL REFERENCES user_account(id),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- review metadata (for audit & UX)
  approved_at      TIMESTAMPTZ NULL,
  approved_by      UUID NULL REFERENCES user_account(id),
  rejected_at      TIMESTAMPTZ NULL,
  rejected_by      UUID NULL REFERENCES user_account(id),
  review_reason    TEXT NULL,
  -- OCC
  version          INT NOT NULL DEFAULT 0
);
```

```sql
-- Prevent post-write mutations of immutable columns
CREATE OR REPLACE FUNCTION artifact_immutable_check()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP='UPDATE' AND (
    NEW.content_uri    IS DISTINCT FROM OLD.content_uri OR
    NEW.content_sha256 IS DISTINCT FROM OLD.content_sha256 OR
    NEW.manifest       IS DISTINCT FROM OLD.manifest
  ) THEN
    RAISE EXCEPTION 'artifact immutable fields cannot change';
  END IF;
  RETURN NEW;
END; $$;

CREATE TRIGGER artifact_immutable_trg
  BEFORE UPDATE ON artifact
  FOR EACH ROW EXECUTE FUNCTION artifact_immutable_check();
```

```sql
CREATE TABLE guardian_decision_history (
  id UUID PRIMARY KEY,
  artifact_id UUID NOT NULL REFERENCES artifact(id),
  org_id UUID NOT NULL REFERENCES organization(id),
  idempotency_key TEXT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('READY','QUARANTINED')),
  reasons JSONB,
  rules_version TEXT,
  settings_snapshot_sha256 CHAR(64),
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
PARTITION BY RANGE (decided_at);

CREATE UNIQUE INDEX gdh_idem_unique
  ON guardian_decision_history (org_id, artifact_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE VIEW guardian_decision AS
SELECT DISTINCT ON (artifact_id) *
FROM guardian_decision_history
ORDER BY artifact_id, decided_at DESC, id DESC;

-- Jobs / QA / Delivery (unchanged except for indexes below)
```

```sql
-- Entitlements history (admin/auditor)
CREATE TABLE entitlement_snapshot (
  id UUID PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organization(id),
  user_id UUID NOT NULL REFERENCES user_account(id),
  token_id TEXT NOT NULL,
  active_org_roles TEXT NOT NULL,     -- comma CSV
  realm_roles TEXT NOT NULL,          -- comma CSV
  device_fp TEXT NOT NULL,
  ip TEXT,
  ua_hash CHAR(64) NOT NULL,
  minted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ent_snap_org_user_time ON entitlement_snapshot (org_id, user_id, minted_at DESC);

ALTER TABLE entitlement_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE entitlement_snapshot FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ent_hist_vis ON entitlement_snapshot;
CREATE POLICY ent_hist_vis ON entitlement_snapshot
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('ENTITLEMENT_HISTORY','read',NULL,NULL,NULL)
);

CREATE VIEW entitlement_snapshot_secure WITH (security_barrier=true) AS
SELECT id, org_id, user_id, token_id, active_org_roles, realm_roles, device_fp,
       ip, ua_hash, minted_at
  FROM entitlement_snapshot;

REVOKE SELECT ON entitlement_snapshot FROM udocket_app;
GRANT  SELECT ON entitlement_snapshot_secure TO udocket_app;
```

**Partitioning & indexes for approval-gated/high-volume tables (binding)**
* `audit_event`, `delivery_receipt` are partitioned by `created_at`; `guardian_decision_history` is partitioned by `decided_at`; (`qa_log` optional).
* All time-ordered indexes are **LOCAL** to partitions to keep bloat bounded.

```sql
-- Partitioning examples
ALTER TABLE audit_event PARTITION BY RANGE (created_at);
CREATE TABLE audit_event_2025_01 PARTITION OF audit_event
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
-- Repeat monthly; ops job `ops/db/rotate_partitions.py` creates next 2 months and seals previous.
```

```sql
-- RLS for audit_event (read via secure view only)
ALTER TABLE audit_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_event FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS audit_vis ON audit_event;
CREATE POLICY audit_vis ON audit_event
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('AUDIT_EVENT','read',NULL,NULL,NULL)
)
WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('AUDIT_EVENT','write',NULL,NULL,NULL)
);

CREATE VIEW audit_event_secure WITH (security_barrier=true) AS
SELECT id, org_id, actor_user_id, actor_role, object_type, object_id, action,
       payload, ip, ua, created_at
  FROM audit_event;

REVOKE SELECT ON audit_event FROM udocket_app;
GRANT  SELECT ON audit_event_secure TO udocket_app;
```

```sql
-- At most one APPROVED artifact per (case, type), ignoring archived
CREATE UNIQUE INDEX one_approved_per_case_type
  ON artifact (org_id, case_id, type)
  WHERE state = 'APPROVED' AND archived = FALSE;

-- Fast filters for consumable sets
CREATE INDEX artifact_consumable
  ON artifact (org_id, case_id, type, created_at DESC)
  WHERE state = 'APPROVED' AND archived = FALSE;

-- Helpful extras for ops / analytics
CREATE INDEX gdh_artifact_decided_at_desc
  ON guardian_decision_history (artifact_id, decided_at DESC);
CREATE INDEX delivery_receipt_artifact_status
  ON delivery_receipt (artifact_id, status, created_at DESC);
CREATE INDEX qa_log_job_scope ON qa_log (job_id, scope, created_at DESC);
CREATE INDEX qa_log_case_created ON qa_log (case_id, created_at DESC);
CREATE INDEX qa_log_issues_gin ON qa_log USING GIN (issues_json);
CREATE INDEX job_org_case_kind_status ON job (org_id, case_id, kind, status, started_at DESC);
CREATE INDEX artifact_case_state_created
  ON artifact (org_id, case_id, state, created_at DESC);
CREATE INDEX audit_event_org_created
  ON audit_event (org_id, created_at DESC);
CREATE INDEX qa_log_org_case_created
  ON qa_log (org_id, case_id, created_at DESC);
```

**job**
`id UUID PK`, `org_id FK`, `case_id FK`, `kind TEXT CHECK (...)`, `status TEXT CHECK (...)`, `settings_snapshot_sha256 CHAR(64)`, `started_at`, `finished_at`, `created_by REFERENCES user_account(id)`, `archived BOOLEAN`, **`version INT NOT NULL DEFAULT 0`**

**job_task**
`id UUID PK`, `job_id FK`, `name TEXT`, `status TEXT CHECK (...)`, `checkpoint JSONB`, `logs_uri TEXT`, `metrics JSONB`, `started_at`, `finished_at`

**job_checkpoint**
`id UUID PK`, `job_id FK`, `task_name TEXT`, `checkpoint JSONB`, `updated_at TIMESTAMPTZ`

**qa_log**
```
id UUID PRIMARY KEY,
org_id UUID, case_id UUID, job_id UUID,
scope TEXT CHECK (scope IN ('ANALYZE_LANE','ANALYZE_FINAL','COMPOSE_SECTION')),
lane_or_section TEXT,
notes_md TEXT, issues_json JSONB,
source_artifacts JSONB NOT NULL -- e.g., [{"id":"uuid-..."}]
created_by UUID NULL,
created_at TIMESTAMPTZ DEFAULT now()
```

**delivery_receipt**
`id UUID PK`, `artifact_id UUID FK REFERENCES artifact(id)`, `org_id FK`,
`channel TEXT CHECK (channel IN ('EMAIL','SMS','PORTAL'))`,
`recipient TEXT`,
`status TEXT CHECK (status IN ('SENT','DELIVERED','OPENED','DOWNLOADED','BOUNCED'))`,
`details JSONB`, `created_at`

**signature_certificate** (1:1 with SIGNATURE_CERT artifact)
`id UUID PK`, `artifact_id UUID FK REFERENCES artifact(id)`, `org_id FK`,
`pdf_uri TEXT`, `signature_profile JSONB`, `tsa_token BYTEA`, `ocsp_responses JSONB`, `manifest JSONB`, `created_at`

**destruction_certificate** (1:1 with DESTRUCTION_CERT)
`id UUID PK`, `artifact_id UUID FK REFERENCES artifact(id)`, `org_id FK`,
`pdf_uri TEXT`, `manifest JSONB`, `created_at`

**audit_event**
`id UUID PK`, `org_id FK`, `actor_user_id UUID NULL`, `actor_role TEXT`,
`object_type TEXT`, `object_id UUID`, `action TEXT`,
`payload JSONB`, `ip TEXT`, `ua TEXT`, `created_at`

**reference_catalog…**
normalized catalog tables with `canonical_id`, `version`, `effective_from`, `deprecated_at`, `aliases JSONB`, `labels JSONB` (locale→string), `provenance JSONB`.


### 3.3 Concurrency Helpers (DB)
```sql
-- 64-bit stable advisory lock keys using two-part hashing to avoid collisions.
-- We standardize on <scope>:<key> (e.g., "case-approval:org/CASE/type" or "job-create:org/key").

CREATE SCHEMA IF NOT EXISTS udlock;

CREATE OR REPLACE FUNCTION udlock.key_parts(scope TEXT, k TEXT)
RETURNS TABLE (k1 BIGINT, k2 BIGINT)
LANGUAGE sql IMMUTABLE AS $$
  SELECT
    hashtextextended(scope, 0)::bigint,
    hashtextextended(k, 0)::bigint
$$;

CREATE OR REPLACE FUNCTION udlock.xact_lock(scope TEXT, k TEXT)
RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE a BIGINT; b BIGINT;
BEGIN
  SELECT * INTO a,b FROM udlock.key_parts(scope, k);
  PERFORM pg_advisory_xact_lock(a, b);
END $$;

CREATE OR REPLACE FUNCTION udlock.try_lock(scope TEXT, k TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql AS $$
DECLARE a BIGINT; b BIGINT; ok BOOLEAN;
BEGIN
  SELECT * INTO a,b FROM udlock.key_parts(scope, k);
  SELECT pg_try_advisory_lock(a, b) INTO ok;
  RETURN ok;
END $$;

CREATE OR REPLACE FUNCTION udlock.unlock(scope TEXT, k TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql AS $$
DECLARE a BIGINT; b BIGINT; ok BOOLEAN;
BEGIN
  SELECT * INTO a,b FROM udlock.key_parts(scope, k);
  SELECT pg_advisory_unlock(a, b) INTO ok;
  RETURN ok;
END $$;

-- Registry + instrumented wrappers + heartbeat
CREATE TABLE IF NOT EXISTS udlock.registry (
  scope        TEXT    NOT NULL,
  k            TEXT    NOT NULL,
  k1           BIGINT  NOT NULL,
  k2           BIGINT  NOT NULL,
  backend_pid  INT     NOT NULL,
  node_id      TEXT    NOT NULL,            -- logical worker id / pod name
  hold_kind    TEXT    NOT NULL CHECK (hold_kind IN ('SESSION','XACT')),
  acquired_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (k1, k2, backend_pid)
);

CREATE OR REPLACE FUNCTION udlock.registry_upsert(scope TEXT, k TEXT, hold_kind TEXT, node_id TEXT)
RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE a BIGINT; b BIGINT;
BEGIN
  SELECT * INTO a,b FROM udlock.key_parts(scope, k);
  INSERT INTO udlock.registry(scope,k,k1,k2,backend_pid,node_id,hold_kind)
  VALUES (scope,k,a,b,pg_backend_pid(),node_id,hold_kind)
  ON CONFLICT (k1,k2,backend_pid) DO UPDATE
    SET last_heartbeat = now();
END $$;

CREATE OR REPLACE FUNCTION udlock.registry_heartbeat()
RETURNS VOID
LANGUAGE plpgsql AS $$
BEGIN
  UPDATE udlock.registry
     SET last_heartbeat = now()
   WHERE backend_pid = pg_backend_pid();
END $$;

-- Instrumented session try-lock
CREATE OR REPLACE FUNCTION udlock.try_lock_i(scope TEXT, k TEXT, node_id TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql AS $$
DECLARE ok BOOLEAN;
BEGIN
  ok := udlock.try_lock(scope, k);
  IF ok THEN
    PERFORM udlock.registry_upsert(scope, k, 'SESSION', node_id);
  END IF;
  RETURN ok;
END $$;

-- Instrumented xact lock
CREATE OR REPLACE FUNCTION udlock.xact_lock_i(scope TEXT, k TEXT, node_id TEXT)
RETURNS VOID
LANGUAGE plpgsql AS $$
BEGIN
  PERFORM udlock.xact_lock(scope, k);
  PERFORM udlock.registry_upsert(scope, k, 'XACT', node_id);
END $$;

-- Cleanup helpers: drop registry rows with no matching pg_locks entry (best-effort)
CREATE OR REPLACE FUNCTION udlock.gc_registry()
RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE n INT;
BEGIN
  WITH live AS (
    SELECT r.k1, r.k2, r.backend_pid
      FROM udlock.registry r
      JOIN pg_locks l
        ON l.locktype='advisory'
       AND ((l.classid = r.k1 AND l.objid = r.k2) OR (l.objid = r.k1 AND l.classid = r.k2))
       AND l.pid = r.backend_pid
  )
  DELETE FROM udlock.registry r
   WHERE NOT EXISTS (SELECT 1 FROM live WHERE live.k1=r.k1 AND live.k2=r.k2 AND live.backend_pid=r.backend_pid)
  RETURNING 1 INTO n;
  RETURN COALESCE(n,0);
END $$;

-- Operational baselines (autovacuum)
-- Ensure aggressive autovacuum on hot partitions to prevent wraparound and bloat
ALTER TABLE audit_event SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);
ALTER TABLE delivery_receipt SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);
```


### 3.4 Upload session
* Ephemeral staging handle; RLS by `org_id`.

```sql
CREATE TABLE upload_session (
  id            UUID PRIMARY KEY,           -- UUIDv7
  org_id        UUID NOT NULL REFERENCES organization(id),
  case_id       UUID NOT NULL REFERENCES "case"(id),
  type          TEXT NOT NULL,              -- intended artifact.type (policy-validated)
  staging_uri   TEXT NOT NULL,
  upload_token  TEXT NOT NULL,              -- opaque, single-use
  expected_sha256 CHAR(64) NULL,            -- optional client-provided
  content_type  TEXT NULL,
  content_length BIGINT NULL,
  status        TEXT NOT NULL CHECK (status IN ('PENDING','UPLOADED','FINALIZED','ABORTED','EXPIRED')) DEFAULT 'PENDING',
  created_by    UUID NULL REFERENCES user_account(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at    TIMESTAMPTZ NOT NULL
);

CREATE INDEX upload_session_lookup ON upload_session (org_id, case_id, status, created_at DESC);
```


---

## 4) Storage & integrity

### 4.1 Object storage layout
```
/org/{org}/case/{case}/artifact/{artifact_id}/
  content.bin
  manifest.json
```

**QA_logs** (not artifacts):
```
/org/{org}/case/{case}/job/{job}/qa_logs/{qa_log}/
  notes.md
  issues.json
```

**Common Artifact Manifest**
```py
class ArtifactRef(BaseModel):
    artifact_id: UUID
    content_sha256: str | None = None     # optional pin

class ArtifactManifest(BaseModel):
    # Versioning/control surfaces
    schema_version: str | None = None   # e.g., "analyze@1.0" | "compose@1.0"
    graph_version: str | None = None    # e.g., "analyze@v1"
    # Identity & provenance
    case_id: UUID
    org_id: UUID
    source_job_id: UUID | None = None
    # Regions stamped by Policy Guard
    compute_region: str | None = None
    storage_region: str | None = None
    # Rendering/context
    template_version: str | None = None
    language: str | None = None         # e.g., "en"
    doc_type: str | None = None         # for COMPOSE/ASSEMBLED
    # Linkage
    source_artifacts: list[ArtifactRef] = []
```

### 4.2 Hashing

* Compute **SHA-256** on write; store in `artifact.content_sha256`.

> **Re-validate on read:** On mismatch, emit `ARTIFACT_INTEGRITY_MISMATCH` and call **Guardian quarantine** (see §5.2.1). Guardian records the decision and sets `state='QUARANTINED'`. No component other than Guardian changes artifact state.


### 4.3 Object storage security (binding)
* Buckets use **SSE-KMS** (per-org keys when `storage.kms.key_scoping='per_org'`).
* **Bucket versioning & Object Lock (WORM)** enabled for the immutable audit sink and FINOPS reports; retention per §20.1.
* Access is **content-addressable by default** (`content_sha256`) in key suffixes to simplify integrity probes.

---

## 5) Guardian service (artifact readiness gate)

### 5.1 Scope
* Evaluate **`DRAFT` artifact → `READY`** or **`QUARANTINED`**.
  Guardian never mutates content or performs demotions of other artifacts.


### 5.2 API (HTTP)

#### 5.2.1 Guardian Submit
* `POST /v1/guardian/submit`
  **Headers:**
  `Authorization: Bearer <service token>`
  `X-Signature-Key-Id: <key id>`
  `X-Timestamp: <RFC3339 UTC>`
  `X-Request-Signature: <hex>`
  `Idempotency-Key: <opaque>`
  (request signing per §49)

  **Body:**
  `{ "artifact_id":"UUID", "org_id":"UUID", "case_id":"UUID", "content_sha256":"hex (optional)" }`

  **Behavior:**
  * Load artifact + effective settings snapshot.
  * If `content_sha256` provided and mismatches DB → **412 INTEGRITY_ERROR** (and quarantine).
  * Evaluate rules; if pass → set state=`READY`; else `QUARANTINED`.
    ```sql
    -- Guardian state update: READY never overwrites QUARANTINED; never touches APPROVED/REJECTED
    UPDATE artifact
       SET state = CASE
                     WHEN state = 'QUARANTINED' THEN 'QUARANTINED'  -- quarantine wins
                     ELSE :decision                                 -- 'READY' or 'QUARANTINED'
                   END,
           version = version + 1
     WHERE id = :artifact_id
       AND state IN ('DRAFT','READY','QUARANTINED');
    -- rowcount=0 → artifact in terminal review state; record decision history only.
    ```
  * Idempotent per `(org_id, artifact_id, idempotency_key)`.

  **200 Response:**
  `{ "decision": "READY" | "QUARANTINED", "reasons": [...], "guardian_decision_id": "UUID" }`

  > If an `Idempotency-Key` is reused with a different raw body or signature (see §49), return **409 CONFLICT** and do not emit a new decision record. 
  > A `QUARANTINED` artifact may be resubmitted after remediation (e.g., rules/settings update) to transition to `READY`; immutability prohibits changing content in place.
  > **Decision order:** Record decision history first, then update artifact.state using the race rule above.

#### 5.2.2 Guardian Quarantine
* `POST /v1/guardian/quarantine`
  **Headers:**
  `Authorization: Bearer <service token>`
  `X-Signature-Key-Id: <key id>`
  `X-Timestamp: <RFC3339 UTC>`
  `X-Request-Signature: <hex>`
  `Idempotency-Key: <opaque>`
  **Body:**
  `{ "artifact_id":"UUID", "org_id":"UUID", "reason":"INTEGRITY_ERROR", "details":{...} }`
  **Behavior:**
  * Idempotent per (org_id, artifact_id, idempotency_key).
  * Record guardian_decision_history { decision='QUARANTINED', reasons=[reason], ... }.
  * Set artifact.state='QUARANTINED'.
    **Response 200:**
    `{ "decision":"QUARANTINED", "guardian_decision_id":"UUID" }`

* `GET /v1/guardian/decision/{artifact_id}` → last decision or 404.

* Health: `/healthz`, `/readyz`, `/rulesz`, `/synthetic/status`.


### 5.3 Rule evaluation
* **Policy format:** JSON by org; cached with version. Every rule set is **pinned to a source control commit SHA** and surfaced in decision traces.
* **Inputs:** `artifact.type`, `content_sha256`, `manifest.*`, **effective settings**, type patterns.
* **Outputs:** violated rule IDs, human-readable reasons, decision record with `rules_version` + `settings_snapshot_sha256`.


### 5.4 Side effects & state transitions
* On **READY**: set `artifact.state='READY'`, append to `guardian_decision_history`, emit `artifact_state` SSE.
* On **QUARANTINED**: set `artifact.state='QUARANTINED'`; producing job may be marked `PAUSED`/`QUARANTINED` per policy.
* **Guardian never mutates other artifacts** and never approves artifacts; exclusivity is enforced at approval time.
* If concurrent decisions disagree, `QUARANTINED` has precedence (see update rule above).
* **Re-evaluation path:** A previously `QUARANTINED` artifact may be **re-submitted** to Guardian. If rules/settings now pass, Guardian updates the state to `READY` (immutability preserved). `QUARANTINED` still **wins** on concurrent decisions.


### 5.5 SLOs & budgets (binding)
* Decision P95 ≤ **2s** (already in §41.5); error rate ≤ **0.5%/5m**; synthetic success ≥ **99%/1h**. Violations auto-scale or open circuit (see §41.6).

---

## 6) Digital Signature Service

* Produces **PDF/A** with embedded signature + **manifest**; verifies with status `{VALID, REVOKED, EXPIRED, TAMPERED, UNKNOWN}`.
* **LTV:** TSA token + OCSP/CRL (PAdES-LTV). Verification evidence retained ≥ doc retention.
* Keys in KMS/HSM; rotation & revocation per org.
* **Profiles:** PDF/A-2b target; PAdES-B-LT or better depending on org policy.
* **Clock discipline:** service nodes enforce NTP drift ≤ ±100ms; reject TSA/OCSP responses outside drift window.

**Manifest (Pydantic v2):**
```python
class SignManifest(BaseModel):
    case_id: UUID
    artifact_id: UUID
    org_id: UUID
    document_sha256: str
    key_version: int                      # KMS data-key version used for signature
    tsa_cert_thumbprint: str | None = None  # hex SHA-1/256 of TSA cert for LTV
    signed_at: datetime
    signer: dict  # {user_id, keycloak_subject, display_name}
    device_fingerprint: dict  # {ip, user_agent, ...}
    context: dict  # {document_type, representation_type}
```


### 6.1 Trust & Revocation Policy (normative)
* **Trusted issuers:** settings key `sign.trust_roots[]` lists CA/TSA trust anchors (PEM). Activation validator rejects unknown/expired anchors **and records trust-root version** in a public audit artifact (`SIGN_TRUST_ROOTS@<version>`).
* **Revocation checks:** OCSP/CRL required; cache responses for `min(max-age, 12h)` with soft-fail window 30m; after 30m → **HARD-FAIL** verify requests with `SIGN_REVOKE_STATUS_UNKNOWN`.
* **Time-stamping:** TSA drift ≤ ±5s; out-of-drift timestamps rejected.
* **Verification behavior:**
  * `tampered` → `TAMPERED` (hard-fail)
  * `revoked` → `REVOKED` (hard-fail)
  * `unknown` within soft window → `UNKNOWN_SOFT` (warn, allow preview) else **hard-fail**.
* **Metrics:** `sign_verify_status_total{status}`, `ocsp_latency_ms`, `tsa_latency_ms`.

---

## 7) LLM Provider & Model Management

**Registry (Settings-backed, Pydantic models)**
* `llm.providers[]`: `{ name, endpoint, auth, supported_languages[], regions[], rate_limits, pricing, default_model }`
* `llm.models[]`: `{ model_id, provider, max_tokens, temperature_bounds, languages[], regions[], fallback_priority }`
* **Scopes:** SYSTEM defaults; ORG overrides; CASE can refine preferences (`llm.model.preference`, token ceilings).

**Health & circuit breakers**
* Poll provider/model latency, error rates, throttling; **circuit breaker** per model.
* **Fallback** by `fallback_priority`, filtered by region & language.
* Selection logged (model chosen, reason, health snapshot).

**Selection algorithm**
1. Enforce **region allowlists** (Policy Guard).
2. Filter by **language** (case/section language).
3. Respect org/case preference if healthy; else fallback.
4. Cap tokens by `analyze.token_ceiling` / `compose.token_ceiling`.
5. Use variance-reduction settings (e.g., low temperature, top-p=1) where appropriate; content remains non-deterministic. Always record model/version and inputs for audit.

* Outputs may vary across runs. We enforce **schema validity**, **reference resolvability**, **forbidden-pattern policies**, and **length/structure bounds**. We capture prompts, effective settings snapshot, model ID/version, and key output hashes for audit and regression analysis.

**Prompt governance**
* Pydantic-validated prompt templates with version IDs; PII redaction hooks pre-call; truncated prompt/response excerpts to secure audit store.
* **Evidence store (separate):** Persist `{prompt_template_id, template_version, redaction_ruleset_id, redaction_stats, model_id, model_version, input_hashes, output_hashes, request_id, actor_id, case_id, timestamps}` to a hardened audit datastore with stricter retention than artifacts.
* **Access control:** Only `auditor|sysadmin` via dedicated endpoints; all reads are audited.
* **Retention:** Configurable (org/system); default ≥ 2× artifact retention for non-content metadata; no raw unredacted prompts stored beyond short-term troubleshooting TTL.


### 7.1 Safety harness & evals
* Prompt-injection redaction and structural guards applied pre-call.
* **Residency for embeddings:** vector stores/providers must match `regions.allowlist.compute|storage`; cross-region embeddings are blocked unless waiver (see §8.1).
* Golden-set jailbreak/bias tests run nightly; regressions block deploy. **Report metrics:** `%jailbreak_pass`, toxicity score deltas, and fairness deltas across language sets.


### 7.2 Provider exit & replay
* Content portability: store minimal control surfaces (model id/version, prompt template id/version, settings snapshot, input/output hashes) to re-run on alternate providers if required.
* Exit switch can re-route models per org without code changes (settings-backed).
* **Replay harness** verifies schema-equivalence on top-N cases monthly.


### 7.3 Cost caps (FinOps)
* Per-org budgets and monthly caps; calls fail with RATE_LIMIT and details when cap reached (policy-controlled).
* Cost metrics: llm_cost_per_job, llm_cost_per_artifact; estimated cost shown before long jobs.


### 7.4 Reproducibility Envelope (binding)
* For each LLM call we persist the **envelope** sufficient to faithfully re-run elsewhere:
```
{prompt_template_id, template_version, model_id, model_version, stop_sequences, truncation_policy_version,
 temperature, top_p, presence_penalty, frequency_penalty, redaction_ruleset_id,
 input_hashes, output_hashes, token_ceiling, settings_snapshot_sha256}
```
* This envelope is stored in the **evidence store** (see §48) and referenced by job/artifact IDs.


### 7.5 FinOps hard limits (enforcement)
* **Pre-call guard:** the LLM wrapper enforces:
  * `tokens_in <= analyze|compose.token_ceiling`
  * `estimated_cost_mtd(org) + estimated_cost_call <= llm.finops.monthly_cap_usd`
* **Breach mapping:** returns `429 RATE_LIMIT` with `details.reason ∈ {"TOKEN_CEILING","BUDGET_EXCEEDED"}` and `Retry-After`.
* **Showback:** export metrics to billing: `llm_cost_estimate_total{org,case,job,model}`; monthly CSV artifacts (`FINOPS_REPORT`) are generated per org.

### 7.6 Circuit breaker + fallback (normative)
* Half-open probing every 60s with capped concurrency.
* Fallback candidate selection honors **region**, **language**, and **preference**; decision trace recorded with reason codes: `PRIMARY_DEGRADED`, `RATE_LIMIT`, `POLICY_REGION_BLOCK`.

---

## 8) Region allowlist enforcement (Policy Guard)

* **Pre-flight checks** at job submission: transcription, LLM calls, object writes, notifications.
* On violation → **hard fail** + `audit_event('REGION_POLICY_BLOCK')`.
* Stamps **`compute_region`** / **`storage_region`** into `artifact.manifest`; Guardian verifies.
* **NetworkPolicies** + egress allowlists enforce region at network layer.


### 8.1 Canonical region tags & activation lints
* **Tags:** `NA`, `EU`, `APAC`, plus cloud-specific granular tags (e.g., `aws-us-east-1`, `gcp-europe-west4`). Settings must map granular → macro tag.
* **Lint rules (activation-time):**
  1) `compute_region ∈ regions.allowlist.compute`
  2) `storage_region ∈ regions.allowlist.storage`
  3) Cross-region reuse: a job in region **X** **MUST NOT** consume artifacts whose `compute_region` or `storage_region` are outside the intersection of allowlists unless `settings.regions.cross_region_waiver=true` (default false). When waived, Guardian stamps `cross_region=true` into manifest and emits `REGION_WAIVER_USED`. **Waivers require dual approval** (Security + Architecture) with step-up MFA and an audit rationale.
* **Validator API:** `/v1/settings/regions/validate` returns lint failures; activation rejects on any failure.
* **Network egress enforcement:** Kubernetes `EgressNetworkPolicy` or cloud egress firewall rules are provisioned from the allowlist to ensure runtime parity with policy.


### 8.2 Residency & Legal Matrix (binding)
* **Purpose:** Bind region tags to jurisdictional constraints (data residency, transfer restrictions, breach notice SLAs) and enforce them at settings activation and job pre-flight.
* **Matrix source:** See **Appendix G** for the authoritative matrix mapping `{region_tag → jurisdictions → constraints}`. The effective matrix version is pinned by `privacy.legal.matrix_version` (e.g., `"v1"`), which maps to a repository path such as `docs/privacy/residency/<version>/matrix.yaml`.
* **Enforcement points:**
  1) **Activation-time**: `settings.policy/regions.validate` rejects bundles where `regions.allowlist.*` violate the matrix for the org’s declared jurisdictions.
  2) **Runtime pre-flight**: Policy Guard denies jobs whose `{compute_region, storage_region}` would violate matrix constraints for the **case’s** jurisdictions (case metadata `jurisdictions[]`).
* **Signals & audit:** On denial: `audit_event('RESIDENCY_POLICY_BLOCK', {reason, region, jurisdiction})`; metric `residency_block_total{org,region,jurisdiction}`.
* **Settings (keys)**: `privacy.legal.org_jurisdictions[]` (ORG), `case.jurisdictions[]` (CASE), `privacy.legal.matrix_version` (SYSTEM).
* **Documentation pointers:** Appendix G summarizes constraint categories and provides examples; Appendix H outlines retention baselines referenced by residency decisions.

---

## 9) Transcription subsystem

### 9.1 Batch flow
1. Upload → `ffprobe` → hash; artifact `TRANSCRIPT_INPUT` (DRAFT).
2. Normalize (`ffmpeg`) → `AUDIO_NORMALIZED` (DRAFT).
3. Submit to provider; poll.
4. Emit `TRANSCRIPT` (text + timecodes) and `DIARIZATION` (JSON) (DRAFT).
5. Guardian submit → **READY**; **Review promotes to APPROVED**, and **Analyze only consumes APPROVED** transcripts/diarization.
6. WebVTT sidecar in manifest enables paragraph playback.


### 9.2 Real-time (optional)
* Browser stream → interim + final hypotheses; final `TRANSCRIPT` artifact; Guardian gating identical.


### 9.3 Multi-track
* Ingest mono/multi-channel/per-mic; merge with diarization to canonical transcript with `speaker_id`.

---

## 10) Analyze pipeline (LangGraph)

### 10.1 Derived IDs & non-deterministic content
* Generate deterministic **UUIDv8** for derived items via HMAC with org salt and stable anchors (see §27).
* Acceptance is by invariants (schema, references, policy) — content itself remains non-deterministic.


### 10.2 Graph
```
ContextBuilder
 ├─ Events ──┐
 ├─ Timeline ─┤
 ├─ Issues ───┤─ Lane QA → (bounded Revision loop)
 ├─ Entities ─┤
 └─ Facts  ───┘
       ↓
    Final QA (cross-lane)
       ↓
    Create artifacts: ANALYZE_* (state=DRAFT)
       ↓
    Guardian submit → state=READY
       ↓
    Human review → state=APPROVED  (only APPROVED is consumable)
```


### 10.3 Models (Pydantic v2)
```python
from uuid import UUID
from typing import Literal, Any
from datetime import datetime, date
from pydantic import BaseModel

class SourceSpan(BaseModel):
    start_ms: int
    end_ms: int

class TranscriptSupportRef(BaseModel):
    artifact_id: UUID          # TRANSCRIPT artifact
    spans: list[SourceSpan]    # one or more supporting spans

class AnalyzeEvent(BaseModel):
    id: UUID
    title: str
    datetime: datetime | None = None
    participants: list[UUID] = []          # entity UUIDs
    source_spans: list[SourceSpan] = []
    notes: str | None = None

class AnalyzeTimelineItem(BaseModel):
    id: UUID
    event_id: UUID
    sequence: int
    date: date | None = None
    certainty: Literal['LOW','MEDIUM','HIGH'] = 'MEDIUM'

class AnalyzeIssue(BaseModel):
    id: UUID
    label: str
    description: str
    related_events: list[UUID] = []        # event UUIDs
    risk: Literal['LOW','MEDIUM','HIGH'] = 'LOW'

class AnalyzeEntity(BaseModel):
    id: UUID
    kind: Literal['PERSON','ORG','ADDRESS','ACCOUNT','OTHER']
    name: str
    aliases: list[str] = []
    attributes: dict[str, Any] = {}

class AnalyzeFact(BaseModel):
    id: UUID
    statement: str
    support: list[TranscriptSupportRef] = []
    confidence: Literal['LOW','MEDIUM','HIGH'] = 'MEDIUM'

class AnalyzeGapsItem(BaseModel):
    id: UUID
    category: Literal['MISSING_DATE','MISSING_ID','INCONSISTENT','OTHER']
    description: str
    proposed_question: str | None = None
```

**Lane Outputs** wrap `list[...]` plus manifest metadata.


### 10.4 QA & review
* Lane QA validates structure & references; results recorded in **QA_logs**.
* **Revision loop** with directives; `analyze.max_retries` (Case/Org).
* **Reviewers** promote `READY → APPROVED` (see §21.1 Reviews). Compose **only** reads `APPROVED` Analyze outputs.
* **QA_logs** recorded for lane and final passes (Markdown + JSON); **internal only**.
* Only lane artifacts + GAPS go to Guardian.

---

## 11) Compose pipeline (LangGraph)

* Inputs: **only `APPROVED`** Analyze/ingest artifacts.
* Outputs: `COMPOSE_CLIENT` / `COMPOSE_LAWYER` as **`DRAFT` → Guardian `READY` → Reviewer `APPROVED`**.
* **Exclusive types:** enforced on approval — at most **one `APPROVED`** per `(case_id,type)`. Approving a new one **atomically demotes** any existing `APPROVED` of that type to `READY`.

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

* QA performs structure/policy checks; violations block approval.

**Artifacts:**
* `COMPOSE_CLIENT` → one JSON containing **all client sections**.
* `COMPOSE_LAWYER` → one JSON containing **all lawyer sections**.
* Start **DRAFT** → Guardian → **READY**.

**QA & revision**
* Per-section **Structure/Policy/Factuality** checks.
* **QA_logs** per section (`scope='COMPOSE_SECTION'`, `lane_or_section='client.<key>'| 'lawyer.<key>'`).
* Bounded revision loop: `compose.max_retries` (Case/Org).

---

## 12) Document Assembly

1. Load **`APPROVED`** `COMPOSE_CLIENT` / `COMPOSE_LAWYER` JSON + selected **Template**.
2. Lint placeholders; render DOCX; compute `SHA-256`; optional PDF/A conversion.
3. Emit `ASSEMBLED_DOC_CLIENT` / `ASSEMBLED_DOC_LAWYER` as `DRAFT`.
4. Guardian → `READY`; Reviewer → `APPROVED` (consumable/deliverable).
5. **Exclusive types:** same approval constraint as Compose.

**Template registry** (artifact `TEMPLATE`): jurisdiction/division/representation, version, brand assets, placeholder inventory.

---

## 13) Delivery

* Channels: Email (attachment or link), SMS (link), Portal (secure download).
* Links: time-limited; single-use optional; tenant-scoped.
* Evidence: `delivery_receipt`; bounces/complaints ingested; webhooks on open/download.
* Signed URLs include: `artifact_id`, `content_sha256`, `state`, `expiry`. Fetch guard enforces **`state='APPROVED'`**.

Accessory systems:
* **Email:** SPF/DKIM/DMARC required; per-org verified domains; bounce/complaint webhooks ingested.
* **DMARC policy** must be `quarantine` or `reject` for production domains; alignment verified during org onboarding.
* **SMS:** Region-compliant sender policies; opt-in state; STOP/HELP handling; protected short links.

```sql
CREATE TABLE download_token (
  id UUID PRIMARY KEY, artifact_id UUID NOT NULL, org_id UUID NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL, single_use BOOLEAN NOT NULL DEFAULT FALSE,
  consumed_at TIMESTAMPTZ NULL
);
CREATE INDEX download_token_lookup ON download_token (artifact_id, expires_at);
```

**Fetch check (single-use):**
```
UPDATE download_token
   SET consumed_at = now()
 WHERE id=:token_id
   AND single_use = TRUE
   AND consumed_at IS NULL
   AND expires_at > now()
RETURNING 1;
-- If 0 rows, reject (410/403).
-- Then validate artifact APPROVED + hash match as already specified.
```

**ETag/If-Match hardening**
* Serve downloads with ETag = artifact.content_sha256.
* Require If-Match = artifact.content_sha256 on GET; otherwise 412.
* **Region re-validation on fetch (binding):** On each GET, validate that `artifact.manifest.storage_region` (and, if present, `compute_region`) remain permitted by the current effective `regions.allowlist.storage`/`compute` for the requesting org. If a previously allowed region has become disallowed due to a newer settings bundle, deny with **403 `POLICY_BLOCK`** and emit `audit_event('REGION_POLICY_BLOCK', {artifact_id, region})`.


### 13.1 HTTP caching & range behavior (binding)
* Responses include:
  `Cache-Control: no-store`
  `Pragma: no-cache`
  `X-Content-Type-Options: nosniff`
  `ETag: <artifact.content_sha256>`
* **Range requests:** disallowed unless `settings.portal.downloads.allow_ranges=true`. If allowed, server validates `If-Match` against ETag for each `206` response; otherwise return `416`. **`If-Range` is not supported.**
* **Strong match on fetch:** clients MUST provide either
  1) `If-Match: <ETag>` **header**, **or**
  2) a signed `etag=<ETag>` query parameter embedded in the download URL.
  The server treats a valid signed `etag` param as equivalent to `If-Match` for browser-initiated downloads; missing/invalid match → **412**.
* **Intermediaries:** `Cache-Control: private` when ranges are allowed; otherwise `no-store` to prevent proxy caching.

---

## 14) Client Signoff

* Client reviews artifact + manifest; signs.
* Signer may operate **only on `APPROVED`** sources.
* Emits `SIGNATURE_CERT` (`DRAFT` → Guardian `READY` → Reviewer `APPROVED` if required by policy).
* Device fingerprint recorded in manifest; verification view shows status/evidence.

---

## 15) Retention & Destruction

* Scheduler selects eligible artifacts/cases from **settings**; **legal hold** blocks.
  ```
  Selector:
    SELECT id FROM artifact
     WHERE ...eligible...
     ORDER BY created_at
     FOR UPDATE SKIP LOCKED
     LIMIT :batch;

  Case archival:
    SELECT id FROM "case"
     WHERE ...eligible...
     FOR UPDATE SKIP LOCKED
     LIMIT :batch;
  ```
* Emit **DESTRUCTION_CERT** artifact on deletion; store receipts; delete objects and files; receipts stored; case `ARCHIVED`.
* **Data posture:** Destruction removes object storage **content** and emits **DESTRUCTION_CERT**. Database rows for artifacts and decisions are **retained** for audit/provenance unless a regulatorily required purge is configured via a future compliance bundle.


### 15.1 DSAR/Erasure Mode (Org setting)
* When settings.compliance.erasure_mode = 'hard_purge':
  * Purge artifacts and associated DB rows for subject scope; create an ERASURE_JOURNAL artifact capturing minimal proof (subject hash, scope, timestamps, operator).
  * Tombstone audit links preserve chain integrity without retaining content.
  * Legal hold supersedes erasure requests.

* Settings:
* compliance.erasure_mode ∈ {'off','hard_purge'}
* compliance.subject_hkdf_salt (KMS-managed) for subject hashing.

**ERASURE_JOURNAL manifest (schema, JSON)**
```json
{
  "schema_version": "erasure@1.0",
  "org_id": "UUID",
  "case_id": "UUID|null",
  "subject_hash": "hex-64",               // HKDF salt per settings.compliance.subject_hkdf_salt
  "scope": ["ARTIFACTS","QA_LOGS","EVIDENCE","PROMPTS"], 
  "requested_by_user_id": "UUID",
  "approved_by_user_ids": ["UUID","UUID"], // dual approval if policy requires
  "justification": "string",
  "executed_at": "RFC3339",
  "settings_snapshot_sha256": "hex-64"
}
```

---

## 16) Reference Engine & Questionnaire (international)

### 16.1 Court catalogs
* **Canonical IDs** per jurisdiction/court/division (stable GUIDs).
* **Aliases** for historical/vernacular names.
* **Labels** by locale (`labels { locale: string }`).
* **Provenance**: `source_url`, `fetched_at`, `checksum`.
* **Versioning & deprecation**: `effective_from`, `deprecated_at`; **back-compat maps** maintain historic validity.


### 16.2 Validators & questionnaires
* **Validators:** Pydantic per jurisdiction version (required fields, filing windows, ranges).
* **Layering:** global → country → state/province → court level/division → org overrides.
* **Localization:** questionnaire items localized; fallback to base locale if missing, flagged for admin.
* **Case snapshot:** Instantiated `QUESTIONNAIRE` artifact (**APPROVED**) to lock effective content.


### 16.3 Admin workflows
* Import preview, diff viewer, sandbox validation, staged→active promotion, rollback.

---

## 17) Notifications & communications

* Outbox with retries/backoff; providers gated by region allowlists.
* Templates tenant-brandable; PII scrubbing at render.
* Link signing & expiry governed by settings.
* Idempotency: Store provider external message IDs and enforce uniqueness: UNIQUE(org_id, channel, external_message_id)
* Resends first check this key; if present, treat as delivered; do not re-send.

```sql
ALTER TABLE outbox_delivery
  ADD COLUMN external_message_id TEXT,
  ADD COLUMN version INT NOT NULL DEFAULT 0,
  ADD CONSTRAINT outbox_unique_extmsg UNIQUE (org_id, channel, external_message_id);
-- Idempotent webhook consume
ALTER TABLE delivery_receipt
  ADD COLUMN provider_event_id TEXT,
  ADD CONSTRAINT receipt_provider_event_unique UNIQUE (org_id, channel, provider_event_id);
```

**Sender claim loop (with OCC):**
```
-- Claim a batch
SELECT id FROM outbox_delivery
 WHERE status='PENDING'
 ORDER BY created_at
 FOR UPDATE SKIP LOCKED
 LIMIT 100;

-- Transition each to SENDING atomically
UPDATE outbox_delivery
   SET status='SENDING', version=version+1, last_attempt_at=now()
 WHERE id=:row_id AND status='PENDING' AND version=:expected_version;
-- rowcount=0 → another worker won the race
```

---

## 18) Client Portal

* **AuthN/AuthZ:** Keycloak; clients see only their own cases.
* **Readable artifacts:** strictly **`APPROVED`** `ASSEMBLED_DOC_*` and `SIGNATURE_CERT`.
* **Endpoints:**
  * `GET /portal/cases`
  * `GET /portal/cases/{case_id}/artifacts?types=ASSEMBLED_DOC_*` (APPROVED only)
  * `POST /portal/cases/{case_id}/corrections` → creates `MEMO_TEXT_*` (`DRAFT` → Guardian `READY` → review)
  * `POST /portal/cases/{case_id}/sign/{artifact_id}` → Signer flow (source must be APPROVED)
* **Fetch guard:** download links verify `artifact.state=='APPROVED'`, id/hash match, unexpired.


### 18.1 Hardening & antifraud
* Adaptive MFA on high-risk auth and on first download from a new device/ASN (policy-controlled).
* Progressive challenges (captcha) after N failed logins or abnormal request rates.
* Device-bound refresh tokens (optional per org); short-lived access tokens.
* **Anomaly detection on downloads:** sudden spikes → auto-revoke outstanding tokens + banner.
* **Session security:** Inactivity timeout 15 minutes (configurable); absolute session lifetime 8 hours; device-bound refresh tokens (optional per org).


### 18.2 Accessibility (WCAG 2.2 AA — binding)
**Conformance target:** WCAG **2.2 AA** across Portal key flows (login, case list, artifact view/download, corrections, signoff).

**Requirements**
* **Keyboard**: All interactive elements reachable in a logical order (Tab/Shift+Tab); visible focus indicator (≥ 3:1 contrast vs adjacent colors); no keyboard traps.
* **Focus not obscured (2.4.11)**: Sticky headers/footers must not cover the focused element; ensure scroll-into-view aligns focus within the viewport.
* **Target size (2.5.8)**: Interactive targets ≥ **24×24 CSS px** (or 44×44 where practical) unless covered by WCAG exceptions.
* **Dragging alternatives (2.5.7)**: Any drag interaction has an equivalent **click/keyboard** alternative.
* **Consistent help (3.2.6)**: Help entry points (e.g., “Support” link) appear consistently in the same relative location across screens.
* **Motion/animation**: Respect `prefers-reduced-motion`; provide non-animated equivalents for loading and progress states.
* **Color & contrast**: Text contrast ≥ **4.5:1** (normal) / **3:1** (large). Color is **not** the sole means to convey state (e.g., include icons/labels).
* **Live regions (SSE updates)**: Use ARIA `aria-live="polite"` for non-critical updates (e.g., job progress) and `aria-live="assertive"` sparingly for critical events (e.g., `portal_link_invalidated`).
* **Forms**: Labels bound via `for`/`id`; error messaging programmatically associated; inline guidance announced via ARIA.
* **Auth**: MFA/step-up dialogs fully keyboard accessible; error summaries focus on first invalid field.
* **Docs/PDFs**: Assembled PDFs tagged for accessibility (reading order, headings, alt text for images).

**Acceptance & QA**
* **Automated**: axe and pa11y run in CI on Portal routes; failures block merge (see §23).
* **Manual**: Quarterly assistive tech spot checks (NVDA/JAWS/VoiceOver) on a sample; defects tracked as Sev-2 accessibility bugs.
* **Metrics**: Track CI a11y violations count; target 0 **blocking** issues.

---

## 19) Search & knowledge retrieval

* PostgreSQL FTS over artifacts and normalized transcript segments.
* RLS applies by `org_id` and **case membership**.
* Exports include provenance (artifact IDs, hashes).
* Index artifacts by `(id, state, type, language, created_at)` and content.
* Exports include `(artifact_id, content_sha256)` for provenance.

---

## 20) Observability & logging

* **Structured logs**: `ts, trace_id, org_id, case_id, user_id, job_id, artifact_id, action, result, latency_ms, settings_bundle_id`; PII redacted.
* **Metrics:** queue depth, job durations, Guardian latency/throughput, Signer verify latency, LLM model health/circuit state, delivery rates, integrity incidents, SSE reconnect rate, `artifacts_ready_total`, `artifacts_approved_total`, `time_to_approval_ms`.
* **FinOps metrics (unit economics):** `llm_cost_estimate_total{org,case,job,model}`, `finops_cost_per_case_usd{org,case}`, `finops_cost_per_org_usd{org,month}`, `delivery_events_total{org,channel,status}`, `finops_mom_regression_flag{org}`.
* **Privacy/Governance metrics:** `residency_block_total`, `dpia_records_total{status}`, `ropa_records_total`, `entitlement_snapshots_total`, `policy_unsafe_activations_blocked_total`.
* **Advisory locks:** `udlock_locks_held{scope,kind}`, `udlock_lock_age_seconds_p95{scope,kind}`, `udlock_watchdog_stale_total{action}` (`alert|terminate|ignored`), `udlock_registry_gc_total`.
* **Traces:** correlate web → workers → Guardian/Signer/LLM.
* **Runbooks:** backlog handling, provider degradation, integrity quarantine triage, Guardian unavailable protocol.
* **Timers:** review pending > N hours, job stuck in RUNNING > M minutes without checkpoint, Guardian decision latency P95 > threshold.
* **Actions:** alert + auto-reassign review, or **auto-pause** job with resume after operator acknowledgment.
* **Request IDs:** Ingress injects `X-Request-ID` if absent; all services echo it in logs and error responses.
* **API SLOs (Web/Portal):** Availability ≥ **99.9%/30d**; P95 latency targets — Web: **250ms** reads / **500ms** writes; Portal downloads start-to-first-byte **≤ 400ms** (in-region).
* **RBAC metrics:** `policy_allow_total{resource,action}`, `policy_deny_total{resource,action}`, `mask_applied_total{resource,field,mask}`; audit `POLICY_ACTIVATED`.

> For `action in ('APPROVE','REJECT')`, include `{prev_state, new_state}` in `payload`. Frontend already displays previous state; audit should record it too.


### 20.1 Immutable audit sink
* All audit_event writes are dual-streamed: (1) operational store (DB) and (2) WORM object storage with bucket-level retention lock.
* Every 1h we emit an AUDIT_SEAL artifact containing a hash-chain over the last window of audit events (rolling Merkle root + prior seal hash).
* Verification tool validates chain continuity and WORM presence.

* **Metrics:** audit_worm_lag_seconds, audit_seal_errors_total
* **Runbook:** If seal fails > 2 intervals, page on-call and halt destructive operations.
* **Privacy artifacts:** DPIA/RoPA records are included in the audit seal inventory (by artifact id only; no PII).


### 20.2 Named dashboards
**Dashboards (Grafana names, owners in parentheses)**
1. **Guardian SLO & Throughput** (SRE): decision latency P50/P95/P99, error rate, queue depth, synthetic success, SLO burn rate.
2. **Queues & KEDA** (SRE): Celery queue depth per lane, replicas, scaling events, DLQ intake and drain.
3. **LLM Cost & Circuit** (Platform): tokens in/out, estimated spend vs cap, circuit state per model/provider, fallback reason codes.
4. **Audit Seal & WORM** (SecEng): seal cadence, seal errors, WORM lag, verification status.
5. **Portal Security** (SecEng): download rate per org/user, anomaly triggers, link invalidations, adaptive MFA prompts.
6. **Advisory Locks** (SRE): locks held by scope/kind, age percentiles, stale detections, terminations; link to §41.8 runbook.
7. **Unit Economics & Delivery** (PM/SRE): cost per case/org; MoM deltas; top 10 expensive cases; delivery counts and failure rates; guard status.
8. **Portal Messaging** (PM/Support): messages sent/received, open threads, attachment failures, profanity flags, rate-limit denials; SSE fan-out health.

**Alert routing (high level)**
* Sev-1 pages on: Guardian SLO burn > 2x target 15m; audit seal missed 2 intervals; queue depth > 3× budget 10m.
* All alerts include `dashboard_url`, and last 5 relevant traces.

### 20.3 Runbooks
**Runbooks (IDs referenced in alerts)**
* `RB-GUARD-001` Guardian SLO breach
* `RB-QUEUE-002` Backlog saturation & KEDA tuning
* `RB-LLM-003` Provider degradation / circuit breaker
* `RB-AUDIT-004` Audit seal failure
* `RB-PORTAL-005` Download anomaly & link revoke
* `RB-LOCK-006` Advisory lock stale detection & remediation

**Alert routing (high level)**
* Sev-1 pages on: Guardian SLO burn > 2x target 15m; audit seal missed 2 intervals; queue depth > 3× budget 10m.
* All alerts include `runbook_id`, and last 5 relevant traces.


### 20.3.1 Runbook RB-LOCK-006 — Advisory-lock stale detection & remediation
**Purpose:** Detect and remediate session-scoped advisory locks that exceed the configured hold time without breaking correctness.

**Signals (any triggers page on-call):**
* Metric `udlock_watchdog_stale_total{action=alert}` increased in last 5m
* Lock age P95 > `udlock.max_session_hold_seconds`
* Repeated stale detections for the same `(scope,k)` within 15m

**Triage — 5-minute checklist**
1) _Confirm scope & blast radius_
   * Grafana → **Advisory Locks** dashboard: filter by `scope` and `node_id`.
   * Note affected `case_id`/`job_id` if `k` is of the form `caseId/jobkind` or `org/case/type`.
2) _Verify holder liveness_
   * `SELECT r.scope, r.k, r.node_id, r.backend_pid, now()-r.acquired_at AS age, a.state, a.query
        FROM udlock.registry r JOIN pg_stat_activity a ON a.pid=r.backend_pid
       WHERE now()-r.acquired_at > make_interval(secs => :threshold_seconds)
       ORDER BY age DESC;`
   * If `a.state IN ('idle','idle in transaction')` or heartbeat > 2× interval → stale.
3) _Check job/case impact_ (if `scope='jobkind'`)
   * `SELECT id, kind, status, started_at, finished_at FROM job WHERE case_id=:case LIMIT 1;`
   * If job still making progress (recent checkpoints) → prefer **notify** over terminate.

**Decision tree**
* **Prod default (`udlock.watchdog.kill_stale=false`)**
  * _Action:_ Alert only. Post a remediation note in incident channel; ask owner pod to release lock (rolling restart of that worker Deployment if needed).
  * _Evidence:_ attach top 5 rows from the query above and last job checkpoint id.
* **Staging / controlled prod exception** (approved by on-call SRE + service owner):
  * _Terminate session:_ `SELECT pg_terminate_backend(:backend_pid);`
  * _Verify release:_ lock disappears from `pg_locks`; `udlock.registry` row GC’d within 60s or by `SELECT udlock.gc_registry();`
  * _Resume:_ If a job was blocked, it resumes on next retry loop.

**Post-remediation**
* Confirm metrics return to baseline (`udlock_locks_held`, `udlock_watchdog_stale_total` plateau).
* Open a defect if the same `(scope,k)` reappears within 24h; include `node_id`, last 200 lines of the worker pod logs, and query plan of the blocking transaction (if any).

**Preventive actions**
* Ensure all session locks are taken via `udlock.try_lock_i(...)` (instrumented) and held < `udlock.max_session_hold_seconds`.
* Tune `udlock.heartbeat.interval_seconds` to 5–10s; avoid noisy heartbeats (<3s) in production.
* Add a short “finally” clause in workers to call `udlock.unlock(...)` on early abort paths.

**Field runbook snippets**
* Identify pod from `node_id`: `kubectl get pod -A | grep <node_id>`
* Bounce a single worker pod: `kubectl delete pod <pod> -n <ns> --grace-period=5`
* Force GC registry (safe): `SELECT udlock.gc_registry();`

---

## 21) APIs

### 21.1 Staff & Case (REST)

#### 21.1.1 Artifacts
**Upload protocol (with helper lock):**
1. `POST /api/v1/cases/{case_id}/uploads`
   * Body: `{ "type": "...", "content_type": "...", "content_length": N?, "expected_sha256": "hex"?, "manifest": {...}? }`
   * Server creates **upload_session** (no artifact yet) and returns `{ upload_session_id, staging_put_url, upload_token }`.
2. Client `PUT` object to `staging_put_url` (must include Content-MD5 or `x-amz-meta-sha256`/equivalent).
3. `POST /api/v1/uploads/{upload_session_id}/finalize`
   * Headers: `Idempotency-Key`, request signing per §49.
   * Body: `{ "sha256": "hex", "manifest": {...}, "auto_submit_guardian": true|false }`
   * Tx (single transaction):
     * Acquire advisory lock `with_idempotency_lock(org, 'uploadsession', upload_session_id)`.
     * Verify session active, not expired, and staging object exists.
     * Verify hash (`sha256` matches header/actual); size and type within policy.
     * **Server-side COPY** to final key: `/org/{org}/case/{case}/artifact/{new_artifact_id}/content.bin`
     * **INSERT** into `artifact` with **all immutable columns set**, `state='DRAFT'`, `id = UUIDv7()`.
     * Mark `upload_session.status='FINALIZED'`.
   * Response: `{ "artifact_id": "UUID" }`
   * If `auto_submit_guardian=true` (default), enqueue/perform `submit_guardian` immediately (idempotent).
4. Cleanup: delete staging object.

**Idempotency:** Reusing the same Idempotency-Key for the same session returns the same `artifact_id`; different signature → **409 CONFLICT** (as §49).

**SSE:** Emit `artifact_state` only **after** the artifact INSERT commits.

**Error mapping:**
* Hash mismatch → **412 INTEGRITY_ERROR**; session remains not finalized; nothing inserted.
* Finalize twice → **200** with same `artifact_id` (if idem key matches) or **409** (if not).
* Expired/aborted session → **409 CONFLICT**.

* **Create artifact:**
* `POST /api/v1/cases/{case_id}/artifacts`
  Body: `{ "type": "...", "file" | "json", "manifest": {...} }`
  → Creates **`DRAFT`**; returns `{ artifact_id }`.

* **Submit to Guardian (idempotent per artifact):**
* `POST /api/v1/artifacts/{artifact_id}/submit_guardian`
  Body: `{ "content_sha256": "hex" }`
  → Guardian evaluates: **`DRAFT→READY`** or `QUARANTINED`.

* **Get metadata:**
  `GET /api/v1/artifacts/{artifact_id}`

* **Download (must be APPROVED):**
* `GET /api/v1/artifacts/{artifact_id}/download`
  → Requires **`state='APPROVED'`**.

* **List artifacts:**
  `GET /api/v1/artifacts?case_id=&type=&state=&archived=&page=&page_size=`
  `GET /api/v1/artifacts?scope=org&type=&state=&archived=&page=&page_size=`   # org-wide list, scoped by token’s active_org_id
  * Per-case list requires **case_id**.
  * Org-wide list uses **scope=org** (implicitly scoped by the token’s **active_org_id**). `org_id` query param is not supported.
  * Optional: `consumable=true` (alias for `state=APPROVED`).


#### 21.1.2 Jobs
* `POST /api/v1/cases/{case_id}/jobs/{kind}` with `Idempotency-Key` (stored as `idemp:{org}:{key}` → job ID; TTL configurable, default 24h).
* `GET /api/v1/jobs/{id}` → status + links.
* **Control:** `POST /api/v1/jobs/{id}/pause`, `POST /api/v1/jobs/{id}/resume` (resumes from last **job_checkpoint**).
```sql
-- Add a version column for OCC (already present in §3)
-- Example resume:
UPDATE job
   SET status='RUNNING', version=version+1, started_at=COALESCE(started_at, now())
 WHERE id=:job_id
   AND status IN ('PAUSED','PENDING')
   AND version=:expected_version;
-- If rowcount=0 → 409 CONFLICT (stale view or illegal transition).
```

```sql
CREATE TABLE idempotency_keys (
  org_id UUID NOT NULL,
  scope  TEXT NOT NULL,                -- e.g., 'job:create'
  key    TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  result_ref TEXT NULL,                -- e.g., job_id
  PRIMARY KEY (org_id, scope, key)
);
```

* **Handler algorithm (job create) with helper lock:**
```
1) SELECT udlock.xact_lock('job-create', CONCAT(:org_id::text, '/', :key));
2) INSERT INTO idempotency_keys (org_id,scope,key,result_ref)
   VALUES (:org_id,'job:create',:key,:job_id)
   ON CONFLICT (org_id,scope,key) DO NOTHING;
3) If inserted → create job row and return it.
   Else → load result_ref (job_id) and return existing job.

-- Optional overlapping-run guard:
-- BEFORE marking RUNNING:
SELECT udlock.try_lock('jobkind', CONCAT(:case_id::text, '/', :kind)) AS ok;
-- if ok=false -> 409 JOB_KIND_BUSY; release via udlock.unlock(...) after transition or failure.
```

* **Janitor:** delete rows older than TTL (24h) hourly.

```sql
-- Optional guard: prevent overlapping runs of same kind per case
-- Try to acquire a short-lived advisory lock; fail with 409 if held.
SELECT udlock.try_lock_i(
  'jobkind',
  CONCAT(:case_id::text, '/', :kind),
  :node_id   -- caller-supplied logical worker id/pod name
) AS ok;
-- If ok=false → 409 CONFLICT "JOB_KIND_BUSY".
-- Hold the lock only through the transition to RUNNING, then release.
```


#### 21.1.3 Reviews (with OCC)
* `POST /api/v1/reviews/{artifact_id}/approve`
  Body: `{ "note": "...", "expected_version": INT }`
  Transaction (isolation: READ COMMITTED)

  1. Acquire case/type advisory lock:
    ```sql
    -- Approval/reject lock: scope 'case-approval' + "org/case/type"
    SELECT udlock.xact_lock(
      'case-approval',
      CONCAT(:org_id::text, '/', :case_id::text, '/', :type)
    );
    ```
  2. Demote any existing APPROVED for (org_id, case_id, type):
    ```sql
    UPDATE artifact
       SET state='READY', version=version+1
     WHERE org_id=:org_id AND case_id=:case_id AND type=:type AND state='APPROVED';
    ```
  3. Approve target if in READY and version matches:
     ```sql
     UPDATE artifact
        SET state='APPROVED', review_reason=:reason, approved_at=now(), approved_by=:user, version=version+1
      WHERE id=:artifact_id AND state='READY' AND version=:expected_version;
     ```
 4. If rowcount=0:
     * If the target is already `APPROVED`, return **200** (idempotent) regardless of `expected_version`.
      (Clients SHOULD send the current version, but servers MUST treat replays as idempotent.)
     * Else → **409 CONFLICT** (stale version or illegal state).
  5. Emit audit + SSE.

**Portal invalidation (binding):** If this approval demotes a previously `APPROVED` artifact of the same `(case,type)` or a rejection affects an artifact backing any active portal link, the server MUST:
  * emit `portal_link_invalidated` (see §47, §50) and
  * terminate in-flight downloads with **412 If-Match** or **403 state changed** per §47.

* `POST /api/v1/reviews/{artifact_id}/reject`
  **Body:**
  `{ "reason": "...", "expected_version": INT }` (required)
  Transaction (READ COMMITTED)

  1. Acquire lock as above.
  2. Update with OCC:
     ```sql
     UPDATE artifact
        SET state='REJECTED', review_reason=:reason, rejected_by=:user, rejected_at=now(), version=version+1
      WHERE id=:artifact_id AND state IN ('READY','APPROVED') AND version=:expected_version;
     ```
  3. If rowcount=0 → 409 CONFLICT (stale state/version).
  4. Emit audit + SSE.


#### 21.1.4 QA_logs (read-only)
* `GET /api/v1/jobs/{job_id}/qa-logs`
* `GET /api/v1/artifacts/{artifact_id}/qa-logs`
* `GET /api/v1/qa-logs/{id}`

**Implementation binding:** Handlers MUST select from `qa_log_secure` (not the base `qa_log` table).

**Handler skeleton (Django/psycopg3 example, with helpers):**
* Snippet is normative for OCC.
```python
with connection.cursor() as cur, transaction.atomic():
    cur.execute("""
        WITH demote AS (
            UPDATE artifact SET state='READY', version=version+1
                WHERE org_id=%s AND case_id=%s AND type=%s AND state='APPROVED'
				RETURNING id
        )
        UPDATE artifact
            SET state='APPROVED', approved_at=now(), approved_by=%s, version=version+1
        WHERE id=%s AND state='READY' AND version=%s;
    """, [org_id, case_id, atype, user_id, artifact_id, expected_version])
    if cur.rowcount == 0:
        raise Conflict("Approval preconditions not met")
```


#### 21.1.5 RBAC & field controls (API contract note)
* All read endpoints MUST select from secure views:
  * `case_secure`, `artifact_secure`, `qa_log_secure`, `guardian_decision_history_secure`, `delivery_receipt_secure`, `audit_event_secure`, `entitlement_snapshot_secure`.
  * SSE/WS reuse the same serializers to prevent leakage.* Serializers must not “re-hydrate” masked fields; SSE/WS reuse the same serializer pipeline to prevent leaking masked data.
* `sysadmin` (realm role) bypasses masking via `udocket_has_realm_role('sysadmin')`.
* **Gateway header linter (binding):** Protected routes **reject** org/role spoofing headers (e.g., `X-Org-ID`, `X-Active-Roles`). Authorization is derived **only** from the OIDC token claims; such headers are accepted **solely** as correlation on explicitly whitelisted diagnostic endpoints.


### 21.2 Real-time
* On org switch, server terminates existing SSE/WS; clients reconnect after re-auth with the new token.
* **SSE:**
  * `GET /sse/job/{job_id}` → `event: progress|state|error|artifact_state` (payload includes `artifact_id` when relevant).
  * `GET /sse/case/{case_id}` → artifact state & review updates.

> **Event ID (monotonic):** Use a per-case counter stored in Redis: key `sse:case:{case_id}:seq`. Each emission uses `INCR` and sets `id = "case/{case_id}/{seq}"`. This guarantees monotonicity across pods and restarts.

* **Channels:**
  * `/ws/editor/{artifact_id}` for collaborative editing on DRAFTs.


### 21.3 Guardian / Signer / Settings / LLM registry
* Guardian: §5.2 (plus `/healthz`, `/readyz`, `/rulesz`, `/synthetic/status`)
* Signer: `POST /v1/sign`, `POST /v1/verify` (with APPROVED source)
* Settings: §36 APIs
* LLM registry (read-only admin views): `GET /v1/admin/llm/providers`, `GET /v1/admin/llm/models`


### 21.4 Privacy & Governance APIs (admin/auditor)
* **DPIA (Data Protection Impact Assessment)**
  * `POST /v1/privacy/dpia` → create a DPIA record (produces `DPIA_RECORD` artifact; content stored in object storage; summary fields only in DB).
  * `GET /v1/privacy/dpia?org_id|case_id|status|page=...` → list (pagination per §52).
  * `GET /v1/privacy/dpia/{id}` → metadata + artifact refs.
* **RoPA (Record of Processing Activities)**
  * `POST /v1/privacy/ropa` → create/update a RoPA snapshot (produces `ROPA_RECORD` artifact).
  * `GET /v1/privacy/ropa?org_id|page=...`
* **Entitlements history**
  * `GET /v1/admin/entitlements/history?user_id&org_id&from&to&page=...`
* **Security & RBAC**
  * Security: `oidc` required; roles `auditor|sysadmin` (realm) or delegated `org_auditor` (org-scoped) may read; create/update endpoints require `sysadmin|privacy_officer`.
  * All responses include `X-Request-ID`; errors conform to `ApiError` (§21.9.1).
    * **OpenAPI tagging:** all operations under `/v1/privacy/*` MUST include the `privacy` tag for discoverability and linting (§21.11.1).


### 21.5 API error (Pydantic)
```python
class ApiError(BaseModel):
    code: Literal[
      'POLICY_BLOCK','QUARANTINED','INTEGRITY_ERROR',
      'VALIDATION_ERROR','AUTH_ERROR','NOT_FOUND','CONFLICT','RATE_LIMIT','PROVIDER_DEGRADED'
    ]
    message: str
    details: dict[str, Any] | None = None
    correlation_id: str
    # Server echoes "Idempotency-Key" (when provided) to aid safe retries.
```

*For `RATE_LIMIT`, set `Retry-After` header and include `details.retry_after_ms`.*


### 21.6 Header examples
* On 429 responses include:
  * Retry-After: <seconds>
  * X-RateLimit-Limit: <limit>
  * X-RateLimit-Remaining: <remaining>
  * X-RateLimit-Reset: <unix-epoch-seconds>
  * Idempotency-Key: <echoed-opaque-key-if-present>


#### 21.6.1 CORS exposure (binding)
**Canonical CORS contract:** This subsection is normative. Other sections (e.g., §23 tests, §29.4 security headers) reference this list rather than repeating it.
* Purpose: allow browser clients (Portal, Staff UI) to **read rate-limit and correlation headers**.
* Responses to CORS requests **MUST** include:
  * `Access-Control-Expose-Headers: X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After, ETag, Deprecation, Sunset`
* Preflight **MUST** allow required request headers for our contracts:
  * `Access-Control-Allow-Headers` includes: `Authorization, Content-Type, Idempotency-Key, X-Request-Signature, X-Signature-Key-Id, X-Timestamp, If-Match`
* Cache correctness:
  * Add `Vary: Origin, Access-Control-Request-Method, Access-Control-Request-Headers` to CORS responses.
* Normative restatement (authZ): **Org/role spoofing headers are correlation-only and never used for authorization**; see §21.1.5 and §2. All authorization derives from OIDC token claims.


### 21.7 Rate limits & antifraud
* Per-org: 600 rpm sustained, 1200 rpm burst; Per-IP: 300 rpm sustained.
* Portal downloads: 60 rpm per user, 200 rpm per org; anomaly trip → auto-expire all active links for the org and alert.
* 429 with Retry-After on limit breach; headers expose remaining tokens.


### 21.8 Idempotency TTL (binding)
* Unless explicitly overridden in settings (`api.idempotency.ttl_hours`, default **24h**), reusing the same `Idempotency-Key` within TTL returns the same result reference. After TTL, new execution occurs; **callers MUST NOT** assume dedupe beyond TTL.
* Error on key reuse with different signature: `409 CONFLICT` `details.reason="IDEMPOTENCY_SIGNATURE_MISMATCH"`.

### 21.9 OpenAPI
### 21.9.1 OpenAPI authoring rules (binding)
**Scope:** Applies to all uDocket OpenAPI documents (Web, Guardian, Signer, Settings, LLM Registry).

**Baselines**
* **OpenAPI version:** 3.0.3 (or newer minor) across all specs.
* **Servers:** MUST include a base server with `/api/v1` (or service-specific root) and environment variables documented.
* **Global security:** All operations require `oidc`. Mutating operations (`POST|PUT|PATCH|DELETE`) that cross service boundaries or are internally posted over HTTP MUST also require `hmacSignature`.
* **Error envelope:** Every 4xx/5xx response MUST reference `#/components/schemas/ApiError` (see §21.5) and include `X-Request-ID`.
* **Pagination contract:** List endpoints MUST use `#/components/parameters/page`, `page_size`, and `sort` and return the envelope in §52.
* **Headers:** Requests/responses MUST use the shared header components below; **org/role spoofing headers are forbidden** (see §21.1.5).

**Shared components (imported by all specs)**
```yaml
openapi: 3.0.3
components:
  securitySchemes:
    oidc:
      type: openIdConnect
      openIdConnectUrl: https://<keycloak>/.well-known/openid-configuration
    hmacSignature:
      type: apiKey
      in: header
      name: X-Request-Signature
  headers:
    X-Request-ID:
      schema: { type: string }
      description: Correlation ID echoed by the server.
    X-RateLimit-Limit:     { schema: { type: integer } }
    X-RateLimit-Remaining: { schema: { type: integer } }
    X-RateLimit-Reset:     { schema: { type: integer, description: "Unix epoch seconds" } }
    Retry-After:           { schema: { type: integer, description: "Seconds until safe retry" } }
  parameters:
    page:
      in: query
      name: page
      schema: { type: integer, minimum: 1, default: 1 }
    page_size:
      in: query
      name: page_size
      schema: { type: integer, minimum: 1, maximum: 200, default: 50 }
    sort:
      in: query
      name: sort
      schema: { type: string }
  schemas:
    ApiError:
      type: object
      required: [code, message, correlation_id]
      properties:
        code: { type: string }
        message: { type: string }
        details: { type: object, additionalProperties: true }
        correlation_id: { type: string }
```

**Authoring rules**
1) Each operation MUST declare at least one `2xx` and one `4xx` response.  
2) Mutating operations MUST include `Idempotency-Key` header when idempotency is defined (see §21.8.1).  
3) Response examples MUST avoid PII and use masked placeholders per §29.1.  
4) Specs MUST not define or accept `X-Org-ID`/`X-Active-Roles` headers except on whitelisted diagnostics (see §21.1.5).


### 21.9.2 OpenAPI exemplars (normative)

#### 21.9.2.1 Upload Finalize
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
components:
  securitySchemes:
    oidc:
      type: openIdConnect
      openIdConnectUrl: https://<keycloak>/.well-known/openid-configuration
    hmacSignature:
      type: apiKey
      in: header
      name: X-Request-Signature
```

#### 21.9.2.2 Guardian Submit
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
  securitySchemes:
    oidc:
      type: openIdConnect
      openIdConnectUrl: https://<keycloak>/.well-known/openid-configuration
    hmacSignature:
      type: apiKey
      in: header
      name: X-Request-Signature
  schemas:
    GuardianDecision:
      type: object
      required: [decision, guardian_decision_id]
      properties:
        decision: { type: string, enum: [READY, QUARANTINED] }
        reasons: { type: array, items: { type: string } }
        guardian_decision_id: { type: string, format: uuid }
```


#### 21.9.2.3 Review Approve (OCC)
```yaml
openapi: 3.0.3
components:
  schemas:
    ApiError:
      type: object
      required: [code, message, correlation_id]
      properties:
        code: { type: string }
        message: { type: string }
        details: { type: object, additionalProperties: true }
        correlation_id: { type: string }
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
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ApiError"
```


### 21.10 API versioning & deprecation
* Semantic versions in OpenAPI; additive changes only within minor.
* **Deprecation signaling (binding):** when an operation is deprecated, servers MUST emit `Deprecation: true` on all responses and `Sunset: <RFC 8594 HTTP-date>` for the endpoint. Clients SHOULD warn when `Sunset` is ≤ 30 days away. Minimum 90-day overlap between stable and deprecated routes.
* Contract tests in CI enforce non-breaking schema changes.
* **Stability matrix:** `stable`, `beta`, `experimental` tags in OpenAPI `x-stability`; clients must not rely on experimental endpoints in production.


### 21.11 API style & linting (Spectral; binding)
**Goal:** Enforce consistency and security across OpenAPI specs in CI.

**Tooling:** Spectral with a repo-local ruleset `ops/openapi/spectral.yaml`.

**Required rules (excerpt)**
* `oas3-valid-schema-example` — examples must validate against schemas.
* `operation-2xx-response` — every operation needs a success response.
* `no-undefined-server-variables` — all server variables documented.
* `udocket-global-security` — each operation includes `oidc`.
* `udocket-hmac-on-mutating` — `POST|PUT|PATCH|DELETE` require `hmacSignature` unless explicitly annotated `x-internal=false`.
* `udocket-error-envelope` — all 4xx/5xx reference `#/components/schemas/ApiError`.
* `udocket-pagination` — list endpoints use shared `page`, `page_size`, `sort` params and §52 envelope.
* `udocket-no-org-spoof-headers` — forbid `X-Org-ID`/`X-Active-Roles` request headers.

**Ruleset (snippet)**
```yaml
extends: ["spectral:oas", "spectral:asyncapi"]
rules:
  udocket-global-security:
    given: $.paths[*][*]
    then:
      field: security
      function: falsy
      functionOptions:
        not: true   # i.e., must exist
  udocket-hmac-on-mutating:
    given: $.paths[*].*[?(@key.match(/post|put|patch|delete/i))]
    then:
      function: schema
      functionOptions:
        schema:
          type: object
          properties:
            security:
              type: array
              contains:
                type: object
                required: [hmacSignature]
          required: [security]
  udocket-error-envelope:
    given: $.paths[*][*].responses[?(@property.match(/^4|5\d{2}$/))]
    then:
      field: content.application/json.schema.$ref
      function: pattern
      functionOptions: { match: "#/components/schemas/ApiError" }
  udocket-pagination:
    given: $.paths[*].get.parameters
    then:
      function: schema
      functionOptions:
        schema:
          type: array
          contains:
            anyOf:
              - { type: object, properties: { $ref: { const: "#/components/parameters/page" } }, required: [$ref] }
              - { type: object, properties: { $ref: { const: "#/components/parameters/page_size" } }, required: [$ref] }
  udocket-no-org-spoof-headers:
    given: $.paths[*][*].parameters[?(@.in=="header")].name
    then:
      function: pattern
      functionOptions: { notMatch: "^(X-Org-ID|X-Active-Roles)$" }

# --- Privacy API stubs
  udocket-privacy-security-stub:
    description: "Stub – Privacy endpoints must declare security; POST-like methods also require hmacSignature."
    severity: warn
    given: $.paths[/^\/v1\/privacy\/.*/]
    then:
      function: schema
      functionOptions:
        schema:
          type: object
          properties:
            get:
              type: object
              properties:
                security:
                  type: array
            post:
              type: object
              properties:
                security:
                  type: array
            put:
              type: object
              properties:
                security:
                  type: array
            patch:
              type: object
              properties:
                security:
                  type: array
            delete:
              type: object
              properties:
                security:
                  type: array
  udocket-privacy-tag-stub:
    description: "Stub – Privacy endpoints should be tagged 'privacy' for discoverability."
    severity: warn
    given: $.paths[/^\/v1\/privacy\/.*/][*].tags
    then:
      function: schema
      functionOptions:
        schema:
          type: array
          contains:
            type: string
            const: privacy
  udocket-privacy-error-envelope-stub:
    description: "Stub – Privacy endpoints should use ApiError envelope on 4xx/5xx."
    severity: warn
    given: $.paths[/^\/v1\/privacy\/.*/][*].responses[?(@property.match(/^4|5\\d{2}$/))]
    then:
      field: content.application/json.schema.$ref
      function: pattern
      functionOptions: { match: "#/components/schemas/ApiError" }
  udocket-privacy-no-pii-examples-stub:
    description: "Stub – Avoid raw PII in examples under privacy endpoints (enforce later with custom fn)."
    severity: warn
    given: $.paths[/^\/v1\/privacy\/.*/]..example
    then:
      function: falsy
      functionOptions:
        not: false  # placeholder: warns if any example is present; tighten with custom fn later
```

**CI binding:** `make openapi:lint` MUST run in PRs; failures block merge.


#### 21.11.1 Privacy API Spectral stub rules (notes)
* These stubs are **WARN**-level initially to surface drift without blocking merges while the privacy specs stabilize.
* **Escalation plan:** Within one quarter post-GA of the privacy APIs, raise severities to **ERROR** and replace the `no-pii-examples` stub with a custom function that rejects email/phone/National-ID patterns.

---

## 22) Frontend behavior

* **SSE** for status/progress; auto-reconnect with `Last-Event-ID`; backoff + jitter.
* **Channels** for interactive controls/editor.
* **Diff views:**
  * Transcript: word-level diff, timecode chips → playback.
  * Compose: section diff; references to Facts/Entities/Events resolve to Analyze IDs.
* **Review UI:** Approve/reject with rationale; show Guardian reasons if quarantined.
* **QA Logs panel:** Render Markdown + issues table with deep links; **export MD/JSON**; labeled *Internal*.
* **Delivery UI:** Link expiry; receipt statuses.
* **Signoff UI:** Manifest preview; verification result.
* **Visibility:** default lists prioritize `APPROVED`; toggle shows `READY/REJECTED`.
* **Masked fields:** Fields returned as `[REDACTED]` or `null` must be rendered as-is; the UI should not attempt client-side “unmasking,” and must hide copy-to-clipboard for masked values.
* **Masked value handling (binding):** Values masked by secure views (e.g., `'[REDACTED]'` or `null`) **must be rendered as-is**. API serializers and clients **must not** attempt to “unmask”, transform, or substitute sentinel values.

**Accessibility additions (binding):**
* **Global**: Provide “Skip to content” link; maintain logical heading hierarchy; ensure focus is restored sensibly after dialogs close.
* **Live updates**: Route SSE events to ARIA live regions:
  * `progress/state`: announce in a **polite** region with rate-limiting to avoid screen reader spam.
  * `portal_link_invalidated`: announce once in an **assertive** region and display a high-contrast banner with an actionable link.
* **Keyboard patterns**: Use roving `tabindex` for composite widgets (lists, menus); ensure Enter/Space activate, Arrow keys navigate.
* **Reduced motion**: Respect `prefers-reduced-motion`; swap spinners/shimmers with static alternatives.

**Artifacts:**
* **Artifact header:** show **Artifact (ID)** + **State** badge (e.g., “Client Brief — **APPROVED**”); show **Archived** chip when archived.
* **Default views** hide `archived=true` unless toggled; "Latest documents" uses **exclusive-type** latest semantics.
* **Status model:** `DRAFT` (work-in-progress) → `READY` (passed Guardian, awaiting review) → `APPROVED` (consumable) → `REJECTED` (with reason) / `QUARANTINED`.

---

## 23) Testing strategy

* **Unit:** validators, RLS, Settings precedence, Guardian rules, Signer manifest/hash, LLM selection & circuit breaker.
* **Contract:** Pydantic schema conformance, referential integrity, structure/length bounds, policy compliance, Guardian idempotency (per artifact).
* **API lints (binding):** Spectral ruleset (§21.10) passes for all OpenAPI specs; CI blocks on violations (global security, error envelope, pagination, forbidden headers).
* **Regression:** snapshot diffs on semantics (required sections presence/order, references resolvable, forbidden patterns absent). **No byte-equality** assertions for LLM content.
* **Integration:** E2E with fixture audio/templates; SSE & Channels paths; **approval gate** blocks consumption until `APPROVED`.
* **Security:** AuthZ boundaries, case membership enforcement, signed-URL misuse, break-glass audit.
* **SQL linter (binding):** CI fails if application code issues `FROM "case"` or `FROM artifact` (migrations/tests excluded).
* **DB privilege tests:** app role cannot `SELECT` base tables; can `SELECT` only `*_secure` views; attempts are denied even for table owner due to RLS+grants.
* **Performance:** Long-audio throughput, latency, READY backlog processing rate, approval lead times, concurrent jobs, SSE fan-out, Guardian/Signer/LLM latency.
* **Chaos & DR drills:** quarterly chaos experiments (pod kills, network latency injection, object store read throttling) and restoration dry-runs; SLO burn recorded.
* **Integrity:** corrupt file injection → quarantine path; downstream integrity scan from `manifest.source_artifacts[]`.
* **Security regression:** CSP/CORS headers present; cookies SameSite=strict; adaptive MFA flows exercised.
* **Supply chain:** CI blocks Critical CVEs; SBOM present in build artifacts.
* **LLM safety:** jailbreak golden-set run passes; cost cap enforcement returns RATE_LIMIT with details.
* **Accessibility:** axe/pa11y CI green; manual audit sample.

* **CORS & header exposure (rate limits):**
  * Contract tests assert presence of `Access-Control-Expose-Headers` per **§21.6.1** (includes `X-Request-ID, X-RateLimit-*, Retry-After, ETag, Deprecation, Sunset`).
  * Browser E2E verifies JS `fetch()` can read `X-RateLimit-Remaining` and `Retry-After` on 429 responses.
  * Negative test: Preflight includes `Idempotency-Key`, `X-Request-Signature`, `X-Signature-Key-Id`, `X-Timestamp`, `If-Match`; server allows them.

* **Fuzz/property tests (ingestion & policy compiler)**
  * **Scope:** Hypothesis corpora; CI job; seeds from real docs.
  * **DoD:** Reproducible failures; corpus persisted.
  * **Owner:** QA/BE
  * **Est:** 2d.

* **UUIDv8 test vectors (binding)**
  * A canonical vectors file lives at `spec/vectors/uuidv8.json` (repo-relative). CI loads and asserts that the deterministic packer in §27 reproduces IDs for the given anchors and salts.
  * **Contract:** Any change to packing/anchors must update vectors and bump the graph version (§54).

* **Diagram drift check (binding)**
  * CI job `diagram:diff` fails the build when `docs/erd/udocket-erd.svg` or `docs/diagrams/service-map.svg` hash changes without the corresponding source files (`.drawio`/`.mermaid`) and commit note.

* **Sysadmin recertification workflow**
  * Synthetic data job generates `SYSADMIN_RECERT_REPORT` artifacts quarterly (see §29.7). Contract tests assert artifact creation, audit trail, and dual-approval gate on exceptions.


### 23.1 Integrity flow
* On `INTEGRITY_ERROR`: call **§5.2.1** `/v1/guardian/quarantine`. Guardian validates and records the decision and sets `state='QUARANTINED'`.

  * For dependents, apply `integrity.downstream_action ∈ {mark_stale|quarantine}`; UI flags **NEEDS_REVIEW** where applicable.
* If `policy=mark_stale`, flag UI **NEEDS_REVIEW**.
* If `policy=quarantine`, set `state=QUARANTINED` and emit `audit_event('DOWNSTREAM_QUARANTINE')`.

```sql
CREATE TABLE integrity_scan_queue (
  org_id UUID NOT NULL,
  artifact_id UUID NOT NULL,
  enqueued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, artifact_id)
);
```

* **Enqueue (Idempotent):**

```sql
INSERT INTO integrity_scan_queue (org_id, artifact_id)
VALUES (:org_id, :artifact_id)
ON CONFLICT DO NOTHING;
```

* **Workers claim:**

```sql
  SELECT artifact_id FROM integrity_scan_queue
   FOR UPDATE SKIP LOCKED
   LIMIT :batch;
```


### 23.2 LangGraph Acceptance Tests
* **Node idempotency:** re-run a completed lane → zero new LLM calls; identical outputs or schema-equivalent.
* **Checkpoint resume:** kill between Lane QA and Final QA → resume at Final QA without re-calling LLM.
* **Cross-lane integrity:** create conflicting entity/event refs → Final QA rejects with actionable QA log.
* **Fallback correctness:** primary model forced open-circuit → fallback chosen; evidence shows circuit state.
* **Deterministic IDs:** same anchors → same UUIDv8 across reruns; changed spans → new IDs.
* **Policy block:** simulate region disallow → job fails early in ContextBuilder with `POLICY_BLOCK`.
* **Token ceilings:** construct oversized input → prompt truncation obeys ceiling; QA passes shape bounds.


### 23.3 More test hooks
* **Approve/Reject concurrency:** two reviewers racing → exactly one state transition; other gets 409.
* **Upload finalize race:** assert that **no artifact row exists** prior to finalize; finalize creates exactly one row; any further finalize attempts are idempotent or rejected.
* **Outbox claim:** two senders never process the same row (SKIP LOCKED proof + OCC).
* **Settings activation:** activating a bundle while one is ACTIVE swaps atomically; unique constraint + advisory lock + OCC enforce invariant.
* **Single-use token:** second fetch returns 410/403.
* **Artifact immutability:** attempt to UPDATE `content_uri`, `content_sha256`, or `manifest` on an existing row → rejected by trigger.
* **Guardian gate:** downstream consumers blocked until `APPROVED` as already specified.


### 23.4 Governance/Privacy acceptance
* **Residency matrix:** activating a bundle that violates Appendix G for the org’s jurisdictions is rejected with `VALIDATION_ERROR`; runtime pre-flight blocks cross-jurisdiction runs (`RESIDENCY_POLICY_BLOCK`).
* **DPIA:** creating a DPIA produces a `DPIA_RECORD` artifact; required fields validated per §H.2; artifact appears in audit seal window.
* **RoPA:** RoPA snapshot creation produces `ROPA_RECORD`; retention matches Appendix H; auditor can list and fetch metadata.
* **Entitlements:** login mints an entitlement snapshot; `GET /v1/admin/entitlements/history` returns rows scoped by RLS and role; pagination per §52.


### 23.5 Property & fuzz testing
* **Targets:** ingestion parsers (archive/ocr/email), policy compiler (settings→effective tables), SSE event schemas (§50), region validator (§8).
* **Method:** Hypothesis-based generators + curated corpora; invariants (idempotent compile, denial on malformed RBAC, parser safety limits, SSE schema round-trip).
* **CI:** `test:prop` job runs on PR + nightly; flakiness budget 0; failing examples minimized and checked in under `tests/corpora/`.
* **Artifacts on fail:** store failing payloads as INTERNAL test artifacts (non-PII) for triage.
* **Exit criteria:** no regressions across 1000 seeds per suite; mutation score ≥ 85% on compiler module.


### 23.6 Advisory-lock watchdog tests
* **Detection:** simulate over-threshold session-held `jobkind` lock via test worker; watchdog flags stale with correct `scope/kind`.
* **No false positives:** xact-scoped locks during approval swap never flagged (duration ≪ threshold).
* **Actions:** when `kill_stale=false` → alerts only; when `kill_stale=true` (test env) → holder backend terminated and lock released; job resumes on next retry.
* **Metrics/assertions:** `udlock_watchdog_stale_total{action=...}` increments; `udlock_locks_held` returns to baseline; registry GC removes orphans.

---

## 24) Operations

* **CI/CD:** type checks (mypy/pyright), lint/format (ruff/black), unit tests; image build; blue/green deploy; gated DB migrations; CycloneDX SBOM; image signing (cosign).
* **Backups/DR:** PostgreSQL base + WAL; object versioning; restore drills.
* **Secrets:** No secrets in code/artifacts; rotation cadence enforced.
* **Celery queue taxonomy & DLQ**
  * **Queues:** `q.transcribe`, `q.analyze`, `q.compose`, `q.assembly`, `q.delivery`, `q.sign`, `q.ingest`, `q.maintenance` (+ optional priority lanes).
  * **DLQ:** `q.deadletter` with `last_error`, `attempts`, `cause` (policy, integrity, provider).
  * **Poison handler:** configurable requeue after fix; manual purge tools.
* **DB migrations (Postgres) — zero-downtime playbook**
  * Use `CREATE INDEX CONCURRENTLY`; `ALTER TABLE ... ADD COLUMN NULL` (then backfill in chunks).
  * Backfills run in worker jobs with **`work_mem`** caps; verify bloat; `REINDEX CONCURRENTLY` post-migration if needed.
  * Kill-switch in migration runner if `pg_stat_activity` shows locks > 2s on hot tables.

### 24.1 DR Objectives & Drills
Targets: RTO ≤ 4h, RPO ≤ 15m.
* PostgreSQL: PITR + cross-region replica; quarterly restore drill with pass/fail SLO 99%.
* Object storage: cross-region replication for artifacts; verify replication lag < 5m P95.
* KMS: key replication or per-region keys with rotation parity.
* Region evacuation runbook (DNS, ingress, autoscale) tested twice yearly.

---

## 25) Vulnerability & Supply-Chain

* SCA/SAST/secret scanning on every PR; block on Criticals unless risk-accepted.
* Weekly dependency bump bot; CVE budget policy with exception register.
* Image hardening: distroless/non-root, seccomp, read-only FS; image signing (cosign) + provenance attestation (SLSA-like).
* IaC scanning (K8s/Terraform) with enforced policies.
* DAST on staging before prod promotion.
* SBOM (CycloneDX) published per build; stored with release artifacts.
* **Provenance & attestation:** supply SLSA-compatible provenance; verify image signatures (cosign) and attestations at deploy time; block if signature missing or key not trusted.
* **Runtime security:** enable Falco/Cloud IDS for syscall/network anomalies; alert on suspicious exec/syscalls in `web`, `workers`, `guardian`, `signer`.
* **Secret rotation cadences:** KMS data-keys rotated ≤ 90 days; request-signing keys ≤ 180 days; Web/Portal OAuth clients ≤ 365 days. Alerts if overdue.


### 25.1 Pentest & Vulnerability Disclosure (binding)
* **Cadence:** external penetration test **pre-GA** and **annually** thereafter; ad-hoc after material changes to auth, RBAC, or crypto.
* **Disclosure:** `/.well-known/security.txt` (SYSTEM setting keys below); coordinated vulnerability disclosure with safe-harbor language.
* **SLA:** triage within **2 business days**, fix plan within **7**, severity per CVSS v3.1.
* **Artifacts:** Each engagement generates `PENTEST_REPORT` (internal artifact) with executive summary + fix tracking linkage.
* **Metrics:** `disclosure_reports_open_total`, `pentest_findings_open_total{severity}`.
* **Settings keys:** `security.disclosure.contact`, `security.disclosure.encryption_key_url`, `security.pentest.cadence` (cron-ish), `security.pentest.allowed_scope`.

---

## 26) Failure taxonomy & job resilience

* `POLICY_BLOCK` (region allowlist) → 403 + audit.
* `QUARANTINED` (Guardian) → 409 with rule IDs.
* `INTEGRITY_ERROR` (hash mismatch) → 412; artifact quarantined; **Downstream Integrity Scan** enqueued:
  * Walk `source_artifacts` lineage; for dependents: mark **NEEDS_REVIEW** (UI banner) or **QUARANTINED** by policy (`integrity.downstream_action = mark_stale|quarantine`).
* `PROVIDER_DEGRADED` → **job `PAUSED`**; auto-resume when health recovers (workers subscribe to provider health).
* **Idempotency:** duplicate `Idempotency-Key` returns prior result (per artifact/job scope). TTL default 24h; after TTL, a new execution occurs—documented to callers.

**Job state saving & resume**
* Each task emits **checkpoints** (idempotent unit boundaries).
* On pause/failure, resume uses `job_checkpoint`.
* Manual resume endpoint available; auto-resume on provider recovery via watchdog signal.

---

## 27) Deterministic UUIDv8 generation

* **Use case:** stable IDs for Events/Entities/Facts/Timeline items **inside** Analyze/Compose artifacts.
* **Anchors** include stable selections (e.g., sorted transcript spans by `artifact_id`, key entity IDs).
* **Inputs:** `case_id`, `lane_or_section`, `anchors`, `org_salt`.
* **Digest:** `hmac_sha256(org_salt, json_canonical(payload))`.
* **Pack UUIDv8:** set version bits to 1000, RFC-4122 variant.
* **Note:** Artifact IDs remain **unique v7** per creation; **content is non-deterministic**; **derived IDs are deterministic**.

Pseudocode:
```py
def uuidv8_deterministic(
    case_id: UUID,
    lane_or_section: str,             # e.g., "analyze.events" or "compose.client.intro"
    anchors: dict,                    # e.g., {"spans":[[1000,1500],[3200,3600]], "entities":[...]}
    org_salt: bytes
) -> UUID:
    # Canonicalize anchors (sorted, normalized)
    anchor_bytes = json.dumps(anchors, separators=(',',':'), sort_keys=True).encode()
    payload = {
        "case": str(case_id),
        "scope": lane_or_section,
        "anchors_sha256": hashlib.sha256(anchor_bytes).hexdigest(),
    }
    msg = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()
    d = hmac.new(org_salt, msg, hashlib.sha256).digest()  # 32 bytes
    b = bytearray(d[:16])
    b[6] = (b[6] & 0x0F) | (0x8 << 4)   # version 8
    b[8] = (b[8] & 0x3F) | 0x80         # RFC 4122
    return UUID(bytes=bytes(b))
```

* Notes:
  * For Events/Facts, anchors should include sorted source_spans and (optionally) key entity UUIDs; for Compose
    sections, include outline position and referenced analyze UUIDs.

---

## 28) Content & template linting

* **Placeholder linter:** No unresolved markers before Assembly Guardian submit.
* **Policy linter:** Forbidden phrases/tone rules to reduce quarantine churn.

---

## 29) Security model (selected) & Privacy/Compliance

* MFA for privileged roles; **step-up** for sensitive actions (`security.org_switch.step_up_required`); enforce WebAuthn where available.
* Least-privilege storage per org; single-use signed URLs optional.
* Headers like `X-Org-ID` are **correlation only**; authorization derives from token claims.
* Global API requires `X-Request-ID`.
* `audit_event` retention ≥ **case retention** (org-configurable upward).
* Provide **export** API (filters + tamper-evident hash chain).
* Signed URLs embed `artifact_id`, `content_sha256`, `state`, `expiry`. Fetch must verify `state=='APPROVED'`. If the artifact transitions to `READY`, `REJECTED`, or `QUARANTINED`, fetch rejects.
* **Storage isolation (configurable by SysAdmin):**
  * `storage.isolation.mode ∈ {'per_org_bucket','shared_bucket_prefix'}`
  * `storage.kms.key_scoping ∈ {'per_org','global'}`
  * Documented trade-offs (ops overhead vs isolation).
* Rotate signing keys on a cadence; short access token lifetime with refresh; disable offline tokens for clients not requiring
  them; enforce WebAuthn for privileged roles where available.
* Org switch auditing: `audit_event('ORG_SWITCH', {from_org, to_org})` on successful token mint for a new `active_org_id`; optional step-up enforced by policy.
* Authorization derives solely from token **`active_org_id`** + `active_org_roles[]`; headers are correlation only.
* Step-up on org switch that raises privilege is policy-driven (setting: `security.org_switch.step_up_required`).
* Audit `{active_org_id, active_org_roles[], realm_roles[]}` per request; emit `ORG_SWITCH` on successful switch.
* **RBAC doctrine:** deny-by-default, policy-driven from Settings down to field level; **only** hardcoded bypass is realm `sysadmin` → full access. Enforced via RLS + security-barrier views.


### 29.1 Data classification
Classes: PUBLIC, INTERNAL, PII, SENSITIVE_PII. 
* SENSITIVE_PII must be encrypted at rest using envelope encryption (KMS). 
* Logs exclude PII by default; scrubbing middleware redacts email/phone/ID patterns and configurable PII classes.
* **Incident response (binding):** Triage within 24h, contain/eradicate within 72h, notify impacted orgs per jurisdictional SLA matrix (Appendix G). Dry-run semiannually; artifacts: `IR_REPORT`.


### 29.2 Field-level encryption
* For designated columns (e.g., client email/phone), use deterministic AEAD for equality filters and randomized AEAD otherwise. Keys scoped per org; key rotation supported via dual-decrypt window. Settings: security.field_encryption.enabled, security.field_encryption.key_scope.


### 29.3 DSAR & erasure (policy tie-in)
* See §15 for DSAR/erasure mode and erasure journal. When enabled, purge paths override “retain rows” default while preserving minimum provenance.


### 29.4 Browser security headers (portal & staff)
* CSP (default-src 'self'), COOP/COEP/CORP enabled, Referrer-Policy strict-origin-when-cross-origin, HSTS max-age≥180d, SameSite=strict cookies, CORS restricted to allowed origins per org.
**CORS exposure (binding):** responses must expose headers per the **canonical contract in §21.6.1** for cross-origin Portal/Staff UI access to rate-limit and deprecation metadata.


### 29.5 Field-level encryption — implementation
* **Approach:** Use randomized AEAD for ciphertexts + a separate deterministic **search token** (HMAC) for equality queries. This avoids weaknesses of deterministic encryption while still supporting `WHERE email=?` and `UNIQUE` constraints.

* **DB shape (example for client email/phone):**
```sql
-- Enable pgcrypto for HMAC
CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE user_account
  ADD COLUMN email_ct  BYTEA,          -- ciphertext (AEAD from app)
  ADD COLUMN email_eq  BYTEA,          -- deterministic HMAC token (for equality/unique)
  ADD COLUMN email_key_version SMALLINT,      -- data-key version used for AEAD
  ADD COLUMN email_eq_key_version SMALLINT,   -- eq-token key version
  ADD COLUMN phone_ct  BYTEA,
  ADD COLUMN phone_eq  BYTEA,
  ADD COLUMN phone_key_version SMALLINT,
  ADD COLUMN phone_eq_key_version SMALLINT;

-- Enforce per-org uniqueness on token (not plaintext)
CREATE UNIQUE INDEX user_email_unique_per_org
  ON user_account (coalesce(default_org_id, '00000000-0000-0000-0000-000000000000'::uuid), email_eq)
  WHERE email_eq IS NOT NULL;
```

* **Token derivation (in app):**
  * `eq_key_org = HKDF(KMS_key_org, info='udocket:eq:v1')`
  * `email_eq = HMAC-SHA256(eq_key_org, lower(trim(email)))` (store as `BYTEA`)
  * Same pattern for `phone_eq` (normalized E.164).

* **Ciphertext (in app):**
  * `AES-GCM` with per-row random nonce; store `{ct, nonce, aad}` inside `email_ct` (compact binary or JSON).
  * Record `*_key_version` alongside ciphertext and `*_eq_key_version` for tokens.

* **Queries:**
  * `SELECT ... WHERE email_eq = :HMAC(lower(email_input))`

* **App binding when `security.field_encryption.enabled=true`:**
  * Do **not** persist plaintext columns (`user_account.email`, `phone`) on writes; set them to NULL at rest.
  * Serializers hydrate plaintext **only** by decrypting `*_ct` in process memory; never log or persist the plaintext.

* **Rotation:**
  * Maintain `eq_key_org` versions in Settings; rotate by writing a **second** token column during migration, then swap indexes.

* **Logging:**
  * Log tokens never; scrub plaintext at ingress.
  * Emit metric `field_encrypt_rotation_overdue_total` if any key version exceeds org/system rotation SLO.

**KMS key naming & scoping examples (settings)**
  * `security.field_encryption.kms_key_alias_per_org`: JSON map of `{ "<org_id>": "alias/udocket/org/<org_id>/fieldenc" }`. If absent, fall back to a system default alias.
   Rotation playbook: see §29.5.2; ensure per-org key alias swap is coordinated with dual-write window and index migration for `*_eq` tokens.


#### 29.5.1 AEAD/AAD parameters & rotation SLOs (binding)
* **Cipher:** AES-256-GCM; library: OpenSSL EVP; tag length 128 bits.
* **Nonce:** 96-bit random; uniqueness guaranteed per write via CSPRNG.
* **AAD (associated data):** `org_id || ":" || table || ":" || column || ":" || row_id || ":" || schema_version`.
* **Key sizes & scope:** 256-bit data keys; per-org by default (`security.field_encryption.key_scope=per_org`).
* **Rotation SLO:** dual-write window **30 days**; alert if dual-write persists >45 days.
* **Test vectors:** maintained under `sec/test_vectors/field_encryption/*.json` with known plaintexts and ciphertexts for regression.
* **Metrics:** `field_encrypt_dualwrite_total`, `field_encrypt_decrypt_fail_total`.

#### 29.5.2 Backfill migration playbook (encryption)
1) Enable dual-write/decrypt with old+new keys.
2) Online job rewrites rows with new AEAD; writes both `*_ct` (new) and `*_eq` tokens; keeps old readable.
3) After coverage ≥99.9% and soak ≥7d, flip reads to new key only.
4) Remove legacy key material; finalize indexes on new `*_eq` if changed.


### 29.6 Entitlements history snapshots (binding)
* **Goal:** Immutable audit of the effective entitlements at token mint time for legal/audit queries.
* **Captured fields:** `{snapshot_id, user_id, active_org_id, active_org_roles[], realm_roles[], device_fp, ip, ua_hash, minted_at, token_id}`.
* **RLS:** Rows are visible only to `auditor|sysadmin` and (optionally) org-scoped `org_auditor` via policy.
* **Lifecycle:** Written at login/token refresh; retained per `privacy.entitlements.retention_days`.
* **Access:** `GET /v1/admin/entitlements/history` (see §21.4).


### 29.7 Admin governance & recertification (binding)
* **Quarterly recertification job/report:** A scheduled job (default cron `0 3 1 */3 *`) enumerates principals with realm `sysadmin` and elevated org roles and produces a `SYSADMIN_RECERT_REPORT` internal artifact per environment. Report schema: `{principal_id, roles[], last_login, justification?, reviewer_ids[], attested_at}`.
* **Workflow:** Security and Architecture reviewers must **attest** or revoke within 14 days. Unattested entries trigger alerts and (optionally) temporary suspension per org policy.
* **Approvals & audit:** Attestations require step-up MFA; actions are logged via `audit_event('SYSADMIN_RECERT', {principal_id, action})`. Exception grants or deadline extensions require **dual approval** as per §36.10.
* **Settings:** `security.recert.cron` (SYSTEM), `security.recert.escalate_after_days` (default 14), `security.recert.auto_suspend` (BOOL, default false).

---

## 30) Data migration & seeding

* Reference catalogs: checksum-verified import with provenance.
* Templates & questionnaires imported as artifacts; emit `REFERENCE_SNAPSHOT`.

---

## 31) Threat Model & Abuse Cases

### 31.1 Method
We maintain STRIDE-style threat models and data-flow diagrams per service (Web, Channels, Workers, Guardian, Signer).
Trust boundaries: browser⇄ingress, ingress⇄web/channels, web⇄workers, workers⇄providers, web/workers⇄DB/objstore.


### 31.2 Top threats & mitigations
* SSRF / path abuse on upload finalize → Strict object-key templating; server-side COPY only; deny user-supplied paths; VPC egress allowlists.
* Prompt injection via exhibits/emails → Pre-call sanitization, policy lints, forbidden patterns (§53), no external browsing/tools in batch.
* Credential stuffing / scraping (portal) → Rate limits (§21/§18), adaptive MFA (§18), anomaly detection + auto-revoke links.
* Link replay / token theft → Single-use tokens (§13), short TTL, device/IP heuristics, If-Match SHA guard.
* Cross-org data access → RLS+GUC fail-closed (§2.2), SSE/WS teardown on org switch (§21.2).
* Quota abuse / cost blowups → Org budgets & kill switches (§7, §40), token ceilings, job pausing on PROVIDER_DEGRADED (§25).
* Insider data browsing → RLS, case membership, immutable audit sink (§20), reviewer scope limits.
* Multi-tenant inference leakage (LLM) → prompt redaction, per-org model contexts, no cross-org embedding stores, replay harness tests.
* Confused deputy via Settings → all policy resolution server-side from Settings Service; callers cannot supply overrides; HMAC request signing on cross-service calls (§49).


### 31.3 Abuse controls
* **Rate limits:** API and portal caps (§21, §18).
* **Anomaly detection:** sudden download spikes → auto-expire links + alert.
* **Malware scanning:** ingest quarantine on detection (§37).
* **Adaptive MFA:** high-risk logins/downloads require step-up (§18).
* **Backpressure:** Queue depth/KEDA scaling with hard ceilings; fail-closed on Guardian down (§41.4).

---

## 32) Capacity & Performance Budgets

Targets (P95 unless noted):
* Analyze (1 hr audio, single lane end-to-end): ≤ 18 min; total job ≤ 35 min.
* Compose (10 sections): ≤ 6 min.
* Guardian decision: ≤ 2s (§41.5).
* SSE fan-out: up to 10k concurrent case streams per env; reconnect rate ≤ 3%/5min.
* Backlog burn-down: ≥ 2× ingest rate at scale-out N.

* Load tests emulate real distributions: audio lengths, languages, template complexities. KEDA triggers set from these budgets; alerts fire at 80/90% thresholds.

**Backpressure policy (binding):** When org exceeds `sse.max_events_per_sec_per_org`, queue drops oldest **non-critical** events (never `portal_link_invalidated`) and emits `sse.org_throttle_total{reason="rate_exceeded"}`.


### 32.1 Initial scale assumptions & autoscaling policies
**Traffic model (baseline):**
* Tenants: 10 pilot orgs; active cases/day: 150; median audio length: 45m; P95: 90m.
* Concurrent jobs (peak): 120 RUNNING; SSE clients: 2,000.

**K8s HPA:**
* `web`: CPU target 60%, min 3, max 15.
* `workers`: custom metric `queue_depth / replicas <= 200`; min 4, max 50.
* `guardian`: P95 latency target 2s; step scaling 1.5x when >2s for 5m.

**KEDA triggers:**
* `q.transcribe`: 1 replica per 20 queued items, max 40.
* `q.analyze`/`q.compose`: 1 per 50 queued, max 60.

**Cost guardrails:** alert when estimated monthly LLM cost > 80% of cap; automatically lower `*.token_ceiling` by 10% for non-privileged tenants when >95%.

---

## 33) Example flows

**Interview → Transcribe → Analyze → Compose → Assembly → Review → Delivery → Signoff**
Each stage creates **new artifacts** (`DRAFT`) → **Guardian** (`READY`) → **Review** (`APPROVED`) before downstream consumption. QA outputs are **QA_logs** (internal).

**Corrections loop**
Client correction → new Analyze/Compose run → emits **new artifacts** (`DRAFT`) → **Guardian** (`READY`) → **Review** (`APPROVED`). For exclusive types, approving a new artifact **demotes** any previously **APPROVED** same-type artifact to `READY` atomically.

---

## 34) Non-functional constraints

* Concurrency-safe (idempotency & dedupe).
* Guardian/Signer responsive under load; bulk work async.
* Scale horizontally on `workers` & `channels`; **SSE** scales via HTTP fan-out + event buffers.

---

## 35) Deliverables

* **OpenAPI** specs: Web, Guardian, Signer, Settings, LLM registry.
* **DB migrations** & seeders.
* **Helm charts** per service.
* **Runbooks** for common incidents.
* **Test suites** and **golden datasets**.
* **ERD (database diagram)** committed at `docs/erd/udocket-erd.svg` (+ source `docs/erd/udocket-erd.drawio`).
* **Service dependency graph** committed at `docs/diagrams/service-map.svg` (source `docs/diagrams/service-map.mmd`).

---

## 36) Centralized Settings Service

### 36.1 Responsibilities
* Define/validate settings; versioned **bundles** at `SYSTEM`/`ORG`/`CASE`; resolve effective map; snapshot into jobs; broadcast changes.


### 36.2 Definitions (Pydantic, selected)
```python
class SettingDefinition(BaseModel):
    key: str  # e.g., regions.allowlist.compute
    datatype: Literal['BOOL','INT','FLOAT','STRING','DURATION','ENUM','JSON','REGION','PERCENT']
    enum_values: list[str] | None = None
    default_value: Any
    mutable_scope: list[Literal['SYSTEM','ORG','CASE']]
    validation_schema: dict[str, Any] | None = None  # external-only
```

**Case-scoped keys (M1)**
* `compose.tone`, `compose.section.length_limits`, `compose.max_retries`, `compose.token_ceiling`, `analyze.max_retries`, `analyze.token_ceiling`, `portal.link.expiry`, `visibility.operators.scope` (`own_cases` | `all_org_cases`), `compose.language`, `llm.model.preference`

**Org/System keys (examples)**
* `regions.allowlist.*`, `retention.days`, `quotas.*`, `notifications.*`, `llm.providers[]`, `llm.models[]`, `tsa.endpoints[]`, `ocsp.endpoints[]`, `artifact.exclusive_types[]`, `reviews.required_types[]` (for artifacts that must be reviewed vs. auto-approve)
* `storage.isolation.mode`, `storage.kms.key_scoping`,
* `integrity.downstream_action` (`mark_stale`|`quarantine`)
* `security.org_switch.step_up_required` (`BOOL`, default `true`)
* `sse.replay.max_events` (INT, default 1000)
* `sse.replay.max_age` (DURATION, default `10m`)
* `sse.max_clients_per_org` (INT, SYSTEM; default 0 = unlimited)
* `sse.max_events_per_sec_per_org` (INT, SYSTEM; default 0 = unlimited)

**New/extended keys (scope → default)**
```
policy.rbac.v1: JSON (ORG/SYSTEM)         # resource/actions/roles + field masks
security.field_encryption.enabled: BOOL (SYSTEM false)
security.field_encryption.key_scope: ENUM['global','per_org'] (SYSTEM 'per_org')
security.org_switch.step_up_required: BOOL (SYSTEM true)
compliance.erasure_mode: ENUM['off','hard_purge'] (ORG 'off')
compliance.subject_hkdf_salt: STRING/KMS (SYSTEM)
retention.exempt_types: JSON (ORG [])                       # artifact types exempt from global retention
retention.legal_hold_required_roles: JSON (ORG ["org_manager","org_reviewer"])
api.rate_limits.org_rpm: INT (SYSTEM 600)
api.rate_limits.org_burst: INT (SYSTEM 1200)
api.rate_limits.ip_rpm: INT (SYSTEM 300)
api.tls.min_version: ENUM['1.2','1.3'] (SYSTEM '1.3')
api.tls.allowed_ciphers: JSON (SYSTEM ['TLS_AES_128_GCM_SHA256','TLS_AES_256_GCM_SHA384','ECDHE-ECDSA-AES128-GCM-SHA256','ECDHE-RSA-AES128-GCM-SHA256'])
ingestion.av.enabled: BOOL (SYSTEM true)
ingestion.archive.max_depth: INT (SYSTEM 5)
ingestion.archive.max_unpacked_mb: INT (SYSTEM 512)
dr.rto_hours: INT (SYSTEM 4)
dr.rpo_minutes: INT (SYSTEM 15)
llm.finops.monthly_cap_usd: INT (ORG 0 = unlimited)
finops.deploy_guard.mom_regression_pct: INT (SYSTEM 10)
finops.report.schedule_cron: STRING (SYSTEM "0 2 1 * *")
finops.report.enabled: BOOL (ORG true)
logging.immutable_sink.enabled: BOOL (SYSTEM true)
security.request_signing.rotation_days: INT (ORG 180)
security.tls.cert_ttl_hours: INT (SYSTEM 24)
portal.rate_limits.user_download_rpm: INT (ORG 60)
portal.rate_limits.org_download_rpm: INT (ORG 200)
portal.adaptive_mfa.enabled: BOOL (ORG true)
portal.downloads.allow_ranges: BOOL (ORG false)
portal.messaging.attachments.allow_ranges: BOOL (ORG false)
portal.messaging.enabled: BOOL (ORG true)
portal.messaging.rate_limits.user_msg_rpm: INT (ORG 20)
portal.messaging.attachments.max_mb: INT (ORG 50)
portal.messaging.allowed_attachment_types: JSON (ORG ["pdf","png","jpg","jpeg","docx"])
portal.messaging.profanity_filter.enabled: BOOL (ORG true)
portal.messaging.staff_auto_subscribe_roles: JSON (ORG ["org_operator","org_reviewer","org_manager"])
portal.messaging.archive_days: INT (ORG 180)
udlock.max_session_hold_seconds: INT (SYSTEM 30)
udlock.watchdog.kill_stale: BOOL (SYSTEM false)
udlock.heartbeat.interval_seconds: INT (SYSTEM 5)
privacy.legal.org_jurisdictions: JSON (ORG [])                     # e.g., ["EU","US-CA"]
privacy.legal.matrix_version: STRING (SYSTEM "v1")                 # Appendix G version pin
privacy.entitlements.retention_days: INT (SYSTEM 365)
privacy.dpia.required_flows: JSON (SYSTEM ["TRANSCRIPT","COMPOSE","ASSEMBLY"])
privacy.dpia.reviewers.roles: JSON (ORG ["privacy_officer","org_manager"])
privacy.ropa.enabled: BOOL (ORG true)
privacy.hipaa.enabled: BOOL (ORG false)                               # HIPAA mode bundle toggle
privacy.hipaa.bundle_version: STRING (SYSTEM "v1")
security.disclosure.contact: STRING (SYSTEM "[security@example.com](mailto:security@example.com)")
security.disclosure.encryption_key_url: STRING (SYSTEM "")
security.pentest.cadence: STRING (SYSTEM "annual")
security.pentest.allowed_scope: JSON (SYSTEM ["web","portal","api"])
security.mfa.webauthn_required_roles: JSON (ORG [])                    # enforced when HIPAA mode is on for staff roles
evidence_store.redacted_excerpts.enabled: BOOL (SYSTEM true)
```

### 36.3 Storage & APIs
* Tables:
  * `setting_definition`
  * `setting_bundle (scope, version, state, effective_from, org_id?, case_id?, version INT NOT NULL DEFAULT 0)`
  * `setting_value`
  * `setting_audit`
  * **Policy compilation targets:** `effective_permission`, `field_mask_rule` (see **§3.2**)

* APIs:
  * `GET /v1/settings/effective?org_id&case_id&format=yaml|json`
  * `POST /v1/settings/bundles`, `/validate`, `/activate`
  * `GET /v1/settings/history?org_id|case_id`
  * **Policy hooks:** `/v1/settings/policy/validate` (schema + referential checks), `/activate` compiles into `effective_permission` / `field_mask_rule` and publishes `settings.changed`.
  * **Messaging toggles:** `GET /v1/settings/effective` Web/Portal reads toggles to gate UI and rate limits.
  * **Residency validator:** `/v1/settings/regions/validate` enforces Appendix G against `privacy.legal.*` keys.
  * **Privacy helpers:** `/v1/settings/privacy/templates` returns DPIA/RoPA template metadata by matrix version.


### 36.4 SDK & snapshot
```python
settings = SettingsClient(request_context)
value = settings.get("analyze.max_retries", type=int)
snapshot = settings.snapshot()  # dict + bundle/version ids
# Workers embed snapshot in job payload; job.settings_snapshot_sha256 recorded.
```


### 36.5 Caching & distribution
* In-memory + Redis cache; pub/sub `settings.changed` with `{scope, org_id, case_id, bundle_id}` invalidation.


### 36.6 Enforcement points
* **Policy Guard:** `regions.allowlist.compute|storage`, `providers.*`
* **Security/Compliance:** `security.field_encryption.*`, `compliance.erasure_mode`
  * **RBAC/Fields:** `policy.rbac.v1 → effective_permission, field_mask_rule`


### 36.7 Acceptance
* Precedence resolution; scheduled activation; rollback; snapshot immutability; cross-process invalidation.


### 36.8 Activation Lock + Uniqueness (helpers + OCC)
```sql
ALTER TABLE setting_bundle
  ADD CONSTRAINT one_active_per_scope UNIQUE (scope, org_id, case_id)
  DEFERRABLE INITIALLY IMMEDIATE
  WHERE state = 'ACTIVE';
```

**Activate API transaction:**
```
1) SELECT pg_advisory_xact_lock(
     (("x" || replace(coalesce(:org_id,'-'),'-',''))::bit(128)::bigint >> 64),
     hashtextextended(CONCAT('settings:activate:', :scope, '/', coalesce(:case_id,'-')), 0)
   );
2) UPDATE setting_bundle SET state='INACTIVE', version=version+1 WHERE scope=... AND org_id ... AND state='ACTIVE';
3) UPDATE setting_bundle SET state='ACTIVE', effective_from=now(), version=version+1 WHERE id=:bundle_id AND version=:expected_version;
```


### 36.9 Policy bundle versioning & diff preview
* Bundles carry `bundle_id` (e.g., `rbac@1.2.0`) and `schema_version` (e.g., `rbac-schema@1.0`).
* `POST /v1/settings/policy/activate?dry_run=true` compiles into **shadow** tables and returns:
  * counts of grants added/removed,
  * resources widened to **write**,
  * “unsafe” flags (e.g., grant to `*`),
  * sample of affected rows.
* Dry-run produces a `diff_preview_id` usable for audit linkage and enumerates `unsafe_reasons[]` per **§36.11**.


### 36.10 Activation & rollback (binding)
* Two-phase activation: `DRY_RUN → ACTIVATE`.
* On ACTIVATE failure, system restores **last-good** bundle atomically and emits `POLICY_ROLLBACK`.
* APIs:
  * `POST /v1/settings/policy/activate` `{ bundle_id, expected_version, diff_preview_id? }`
  * `POST /v1/settings/policy/rollback` `{ to_bundle_id }` (auditor/sysadmin only)
    * **Dual-approval (binding):** Activations flagged as **unsafe** by dry-run (e.g., widened write access, wildcard grants) or any request with `--force` require **two distinct approvers**: one **Security** and one **Architecture** role (realm or delegated). Step-up MFA is enforced for both approvers and the activation is audit-logged with approver IDs.
* **Gates:** CI/CD blocks production deploy if any budget burn > 25% over trailing 7d. Staging promotion requires green **golden-set jailbreak** (§7.1) and **synthetic checks** (§41.2).


### 36.11 Unsafe Policy Change Rules (binding)
**Purpose:** Define changes that increase risk and therefore require **dual approval** and explicit `--force` on activation.

**RBAC widenings (effective_permission)**
* New grants that add any role to `action ∈ {'write','approve','delete'}` for resources `CASE|ARTIFACT|JOB|SETTINGS`.
* New grants that add **org-external** roles (e.g., `org_external_counsel`, `org_client`) to `read` on `QA_LOG`, `GUARDIAN_DECISION`, or other internal resources.
* Introduction of wildcard roles/resources (e.g., `role='*'` or `resource='*'`) — **always unsafe**.

**Field exposure (field_mask_rule)**
* Any change that:
  * moves a field from masked (`REDACT|NULL|HASH`) to visible for any additional role, or
  * weakens a mask (e.g., `NULL → LAST4`, `HASH → LAST4`).

**Region & residency**
* Enabling `regions.cross_region_waiver=true` (see §8.1) or widening `regions.allowlist.*` beyond prior union.

**Security posture toggles**
* Setting any of the following from secure→weaker defaults:
  * `security.org_switch.step_up_required: true → false`
  * `portal.adaptive_mfa.enabled: true → false`
  * `logging.immutable_sink.enabled: true → false`
  * `ingestion.av.enabled: true → false`
  * `security.field_encryption.enabled: true → false`
  * `storage.kms.key_scoping: 'per_org' → 'global'`
  * `api.tls.min_version: '1.3' → '1.2'` or **weakening ciphers** in `api.tls.allowed_ciphers`

**Signer & crypto**
* Trust root additions that are not present in the approved anchor registry.
* Lowering AEAD parameters (key size, tag length) below §29.5.1 baselines.

**Dry-run output (normative)**
```json
{
  "grants_added": 12,
  "grants_removed": 3,
  "fields_unmasked": ["CASE.legal_hold_reason"],
  "mask_weakened": ["ARTIFACT.content_sha256: HASH→LAST4"],
  "regions_widened": ["compute: +gcp-asia-southeast1"],
  "posture_toggles": ["portal.adaptive_mfa.enabled:false"],
  "unsafe_reasons": ["RBAC_WRITE_WIDENING","FIELD_UNMASK","REGION_WIDEN","MFA_TOGGLE"]
}
```

**Activation gate**
* If `unsafe_reasons[]` non-empty → API returns `422 VALIDATION_ERROR { unsafe_reasons[] }` unless `--force` AND **dual approval** (Security + Architecture) with step-up MFA are provided (see §36.10).

---

## 37) Document & Data Ingestion

### 37.1 Artifact type patterns
* Allowed types enforced by Settings + Guardian.
* Core: `EXHIBIT_RAW|TEXT`, `COURT_DOC_RAW|TEXT`, `EMAIL_RFC822|TEXT|ATTACHMENTS`, `FINANCIALS_RAW|TABLE`, `TRANSCRIPT`, `DIARIZATION`, `MEMO_TEXT_*`.


### 37.2 Pipelines
* Raw → parser/OCR → structured text/table (DRAFT) → Guardian (**READY**) → Review (**APPROVED**).
* Manifests include parse stats and link to originals via `source_artifacts`.


### 37.3 Malware & archive defenses
* All binary inputs (EXHIBIT_*, EMAIL_ATTACHMENTS, COURT_DOC_RAW) scanned with AV; positive → artifact QUARANTINED with reason MALWARE_DETECTED.
* Archive bomb guard: nested archive depth limits and decompressed size cap; reject on violation.
* OCR/parse sandboxes: per-task CPU/memory/time caps; untrusted content never executed.

---

## 38) Internationalization & Multilingual Support

### 38.1 Languages & locales
* Multiple locales (e.g., `en`, `fr`, `es`) supported; ICU message format; **RTL readiness**.
* Locale-aware analyzers; cross-language toggle; exports preserve language metadata.


### 38.2 Data & documents
* Templates have locale variants; placeholder linting per locale.
* **Compose** selects LLM model compatible with target language (LLM registry).
* Transcript/ingest language detection informs model selection.
* Output language set at case level.


### 38.3 Catalogs & questionnaires
* Courts/divisions carry localized names and verbiage; validators are language-agnostic; validation messages localized.
* Fallback to base locale with admin flag when translations are missing.


### 38.4 Search & indexing
* Locale-aware analyzers; language field on text payloads; cross-language toggle.
* Exports preserve language & locale metadata.


### 38.5 PHI posture
* uDocket is **not** a HIPAA Business Associate by default. PHI ingestion is **unsupported** unless an org enables the **HIPAA mode** bundle:
  * **Toggle:** `privacy.hipaa.enabled=true` (ORG). Version pinned via `privacy.hipaa.bundle_version`.
  * **Enforcements when enabled (binding):**
    - Force field-level encryption on designated SENSITIVE_PII tables (`security.field_encryption.enabled=true`; `security.field_encryption.key_scope='per_org'`).
    - Require WebAuthn for privileged staff roles: add `security.mfa.webauthn_required_roles` to include `["org_admin","org_manager","org_reviewer","org_operator"]`; reject session without WebAuthn on step-up actions.
    - Disable storage of **any** prompt/response excerpts in the Evidence Store: set `evidence_store.redacted_excerpts.enabled=false` (see §48).
    - Shorten retention for privacy artifacts per Appendix H; raise access logging verbosity for privacy endpoints.
    - Block portal messaging attachments marked as PHI from download by non-staff roles unless explicit case waiver exists.
* By default (HIPAA off), any attempt to upload content labeled `PHI=true` is **POLICY_BLOCK**.

---

## 39) Legal Hold

* Case fields: `legal_hold`, `legal_hold_reason`, `legal_hold_since`.
* Destruction jobs exclude held cases; emit `audit_event('LEGAL_HOLD_CHANGED')`.

---

## 40) Quotas & Metering

* `org_quota (org_id, key, limit_int)`, `org_usage (org_id, key, period, used_int)`.
* Enforced on job submit & storage writes; admin visibility.
* Unique key: UNIQUE(org_id, key, period)
* Atomic increment:
* INSERT INTO org_usage (org_id, key, period, used_int)
* VALUES (:org_id, :key, :period, :delta)
* ON CONFLICT (org_id, key, period)
* DO UPDATE SET used_int = org_usage.used_int + EXCLUDED.used_int;

---

## 41) Health, Watchdog & Self-healing

### 41.1 Liveness/Readiness
* All services expose `/healthz` (liveness) and `/readyz` (deps: DB, Redis, Settings).
* **Guardian/Signer** add `/rulesz` and `/keysz` probes.
* **Web/Portal** readiness asserts DB RLS GUC canary, `search_path` pinning, and that **CORS exposure list** (§21.6.1) matches expected (synthetic OPTIONS probe).


### 41.2 Synthetic checks
* **Guardian synthetic:** calls `/synthetic/status` + seeded test artifact in test org/case.
* **Signer synthetic**: sign/verify a test PDF; verify TSA/OCSP reachability.


### 41.3 Watchdogs
* **Guardian watchdog**: decision P95 latency, queue depth, synthetic success; auto-scale + page on breach.
* **Worker watchdog**: worker stall detection (no progress N min) → `PAUSED` + alert; **auto-resume** when health recovers.
* **Queue watchdog**: Celery depth triggers KEDA scale-out; hard ceiling pages on-call.
* **SSE/Channels watchdog**: reconnect/error spikes → alert; per-org throttling to protect service.
* **LLM watchdog**: per-model health; open/half-open/closed circuit metrics.


### 41.4 Fail-closed behavior
* If **Guardian** down/unready, artifacts remain **DRAFT**.
* If **Settings** down, new jobs cannot start; **running jobs continue** using embedded **settings snapshot**.


### 41.5 SLOs (internal guidance)
* Guardian decision P95 ≤ 2s; Signer verify P95 ≤ 500ms; worker heartbeat ≤ 30s; SSE reconnect ≤ 3% / 5 min.


### 41.6 Guardian synthetic runbook & auto-remediation (new)
* **SLO guardrails:**
  * Decision **P95 ≤ 2s** over 5-minute window
  * Error rate ≤ **0.5%** over 5-minute window
  * `/synthetic/status` success ≥ **99%** over rolling hour

* **On breach:**
  1. **Auto-scale** `guardian` (HPA step-up + max surge),
  2. **Open circuit** for degraded rulesets if detector signals rules load failures; serve 503 to submitters with retry-after,
  3. **Throttle** callers via token bucket tied to org quotas,
  4. **Page** on-call with last 100 decision traces attached.
* **Recovery:** Hold at elevated replicas for 15 minutes after SLO restoration; close circuits gradually.


### 41.7 Error budgets & deployment gates (binding)
* **Budgets:** Guardian decision SLO 99.5% over 30d; Signer verify SLO 99.9% over 30d; LLM wrapper availability 99.0%.
* **Gates:** CI/CD blocks production deploy if any budget burn > 25% over trailing 7d. Staging promotion requires green **golden-set jailbreak** (§7.1) and **synthetic checks** (§41.2).
* **Auto-rollback:** If Guardian SLO drops below target by >0.5% over 60m after a deploy, rollback to prior image automatically; page on-call.


#### 41.7.1 CI integration & deploy gates
**Gate implementation (reference GitHub Actions step)**
```yaml
- name: Error-budget gate

run: |
python ops/gates/check_error_budgets.py \
  --window 7d \
  --guardian_slo_burn_pct 25 \
  --signer_slo_burn_pct 25 \
  --llm_wrapper_availability_slo 99.0
```

* Gate **blocks** production deploy if any burn > 25% over trailing 7d.
* On block, the job emits a markdown summary (linked in PR) with panels to dashboards in §20.2 and runbook IDs.

**Auto-rollback hook**
* Release controller watches SLO streams; on breach post-deploy (≥60m), triggers rollback workflow and annotates the change with `RB-GUARD-001`.


### 41.8 Advisory-lock watchdog
**Goal:** Detect and remediate **session-scoped** advisory locks held over `udlock.max_session_hold_seconds`.

**Design:**
* **Attribution:** All session locks are created via `udlock.try_lock_i(...)`, which records `(scope,k,k1,k2,backend_pid,node_id,acquired_at)` in `udlock.registry` and heartbeats every `udlock.heartbeat.interval_seconds` via `udlock.registry_heartbeat()`.
* **Signal:** Watchdog loop (SRE job) joins `udlock.registry` with `pg_locks`/`pg_stat_activity`:
  * stale = `now() - r.acquired_at > max_session_hold` AND lock present AND `state` ∈ ('idle','idle in transaction') OR heartbeat older than 2× interval.
* **Actions (configurable):**
  * `kill_stale=false` (default): emit alert + metric; annotate job id if scope is `jobkind`; no unlock attempt.
  * `kill_stale=true` (test/staging only): `SELECT pg_terminate_backend(r.backend_pid)`; emit `udlock_watchdog_stale_total{action="terminate"}`.
* **GC:** Periodic `udlock.gc_registry()` cleans rows whose locks have disappeared.
* **SLOs:** 99% of stale detections within 60s; zero false positives on xact locks.
* **Runbook:** `RB-LOCK-006`—triage by scope, confirm job/jobkind, decide on termination, verify metrics return to baseline.

---

## 42) Settings usage map (traceability)

* **Policy Guard:** `regions.allowlist.compute|storage`, `providers.*`
* **Analyze:** `analyze.max_retries`, `analyze.token_ceiling`, `analyze.parallelism`, `llm.model.preference`
* **Compose:** `compose.max_retries`, `compose.section.length_limits`, `compose.token_ceiling`, `compose.language`, `compose.tone`, `compose.policy`
* **Assembly:** `templates.default`, `templates.branding`
* **Notifications:** `notifications.email|sms.enabled`, `notifications.providers.*`
* **Retention:** `retention.days`, `retention.exempt_types`, `retention.legal_hold_required_roles`
* **Portal:** `portal.enabled`, `portal.download.limits`, `portal.link.expiry`
* **Visibility:** `visibility.operators.scope`
* **Quotas:** `quotas.*`
* **LLM:** `llm.providers[]`, `llm.models[]`, `llm.default_model`
* **Crypto/Sign:** `tsa.endpoints[]`, `ocsp.endpoints[]`
* **Storage:** `storage.isolation.mode`, `storage.kms.key_scoping`
* **Integrity:** `integrity.downstream_action`
* **Reviews & exclusivity:** `artifact.exclusive_types[]`; optional `reviews.required_types[]`.
* **Security/Compliance:** `security.field_encryption.*`, `compliance.erasure_mode`
* **Portal/API:** `api.rate_limits.*`, `portal.rate_limits.*`, `portal.adaptive_mfa.enabled`
* **Ingestion:** `ingestion.av.enabled`, `ingestion.archive.*`
* **DR:** `dr.rto_hours`, `dr.rpo_minutes`
* **FinOps:** `llm.finops.monthly_cap_usd`
* **Logging:** `logging.immutable_sink.enabled`
* **Privacy/Governance:** `privacy.legal.org_jurisdictions`, `privacy.legal.matrix_version`, `privacy.entitlements.retention_days`, `privacy.dpia.required_flows`, `privacy.dpia.reviewers.roles`, `privacy.ropa.enabled`, `security.disclosure.*`, `security.pentest.*`

---

## 43) Additional acceptance tests

* **Settings precedence & case-scope:** org vs case overrides; snapshot immutability during jobs.
* **Visibility toggles:** operator scope (`own_cases` → `all_org_cases`) takes effect immediately.
* **Analyze + ingestion:** APPROVED `EXHIBIT_TEXT` / `EMAIL_TEXT` included in ContextBuilder; Compose references appear.
* **Compose output shape:** `COMPOSE_CLIENT` / `COMPOSE_LAWYER` JSON includes ordered **all sections**; Assembly consumes JSON.
* **SSE:** reconnect via `Last-Event-ID`; no loss; auth scoped correctly.
* **Guardian determinism:** same artifact twice → same decision (idempotent).
* **MEMO_TEXT_*:** accepted if prefix policy matches; Once APPROVED they are visible per RBAC.
* **Job resume:** kill worker mid-task → resume from **job_checkpoint** without duplication.
* **LLM fallback:** primary model circuit open → fallback model selected per rules; trace logs show decision.
* **LLM non-determinism:** repeated runs on identical inputs must still satisfy invariants: schema valid, required sections present,
  no unresolved placeholders, all references resolvable, policy/forbidden-pattern checks pass.
* **Malware:** upload EICAR sample → artifact QUARANTINED (`MALWARE_DETECTED`), audit logged.
* **Rate limits:** exceed portal and API RPM caps → 429 with Retry-After; anomaly → links auto-expire and audit event emitted.
* **DSAR:** enable hard_purge; issue erasure; rows removed; ERASURE_JOURNAL artifact created; portal denies now-missing items.
* **Audit seal:** verify 2 consecutive AUDIT_SEAL artifacts produce continuous hash chain; tamper breaks verification.
* **DR drill:** restore latest PITR backup into sandbox; object replicas present; RTO/RPO targets met.

**Artifacts:**
* **No mutation:** Attempting to update `content_uri`, `content_sha256`, or `manifest` on an existing artifact row is rejected at DAL and DB.
* **Guardian idempotency:** Submitting the same artifact with the same `Idempotency-Key` returns the prior decision.
* **Downstream integrity:** When a source artifact is quarantined for hash mismatch, the scanner walks `source_artifacts` and applies `integrity.downstream_action` to dependents; UI surfaces **NEEDS_REVIEW** where applicable.

**Multi-org:**
* Access with `active_org_id=A` to a case in org **B** → 403.
* Switcher re-auth to **B** → new token shows `active_org_id=B`; SSE/WS from **A** are closed; new streams open under **B**.
* Step-up is enforced on privilege-raising switches; `ORG_SWITCH` audit logged.
* Guardian idempotency, exclusive swap (approval-demote behavior), integrity scans behave identically across orgs (scoped by `active_org_id`).
* **Org directory sync:** With webhooks, renames propagate within **10 minutes**; with webhook outage, fallback poll updates within **6 hours**.

* **SSE tuning:** Changing `sse.replay.max_events` and `sse.replay.max_age` via Settings takes effect without restart; replay behavior matches configured limits.
* **Case enums:** API rejects `case.status` not present in `case.status.enum`; activating a new bundle allows the new values.
* **Portal guard:** A previously valid link fails after the artifact transitions away from `APPROVED`; denial is audited.
* **Accessibility (WCAG 2.2 AA):** Keyboard-only navigation completes core flows; focus not obscured by sticky UI; minimum target sizes verified; drag actions have keyboard/click alternatives; live updates announced via ARIA.
* **Rate-limit headers in browser:** JS clients can read `X-RateLimit-Remaining` and `Retry-After` after same-origin and cross-origin requests (CORS exposed).
* **Evidence PII posture:** No unredacted prompt/response content appears in storage scans; evidence reads are audited.
* **Approval gate:** Compose/Assembly/Delivery fail cleanly when inputs lack `APPROVED`.
* **Exclusive swap:** Approving new `COMPOSE_CLIENT` demotes prior `APPROVED` to `READY` in one transaction; unique index remains satisfied.
* **Idempotent approvals:** Re-approving an already `APPROVED` artifact returns 200 with no change.
* **Reject after approval:** `APPROVED→REJECTED` blocks delivery and portal; link denial audited.
* **Guardian quarantine:** `DRAFT→QUARANTINED`; review actions disallowed.
* **Metrics:** `time_to_approval_ms` recorded; dashboards show READY backlog vs APPROVED throughput.
* **Policy dry-run:** activating bundle with widened write access must produce `unsafe=true` and be blocked without `--force`.
* **Unsafe rules enumeration:** dry-run returns `unsafe_reasons[]` per §36.11 for (a) RBAC write widening, (b) field unmasking, (c) region widening, (d) posture toggles; activation requires dual approval when present.
* **OpenAPI lints:** all service specs pass Spectral pack (§21.10); any regression fails CI.
* **FinOps guard:** with `finops.deploy_guard.mom_regression_pct=10`, a simulated 12% MoM org-level cost increase blocks prod deploy; 8% passes. Monthly CSV `FINOPS_REPORT` artifacts appear with correct schema and manifest.

**RBAC & Field Controls:**
* Removing a role from org policy immediately revokes access to rows (RLS) and cleartext fields (views/serializers).
* Masking appears identically across REST, SSE, and WS payloads; no masked field is leaked in alt representations (CSV/PDF exports).
* `sysadmin` realm role bypass verified for rows and fields.
* Deny-by-default on malformed/missing `policy.rbac.v1`.
* Hot reload: activating a new policy updates decisions within ≤1s (cache invalidated via `settings.changed`).
* App role cannot `SELECT` from base tables (`"case"`, `artifact`, `qa_log`, `guardian_decision_history`, `delivery_receipt`); reads succeed via `case_secure`, `artifact_secure`, `qa_log_secure`, `guardian_decision_history_secure`, `delivery_receipt_secure`.

---

## 44) Organization Directory Sync (Ops)

**Purpose:** Keep `organization` table labels in sync with Keycloak Organizations for display and FK integrity, without modeling user↔org membership in our DB.

**Source of truth:** Keycloak Organizations.

**Triggers:**
* Webhook from IdP (preferred): `organization.created|updated|archived`.
* Fallback cron: poll every 6h (targets <6h freshness when webhooks are unavailable).

**Behavior:**
1. Upsert `organization (id, name, archived_at)` using the Keycloak Organization UUID and display name.
2. If an org is archived upstream, set `organization.archived_at = now()` locally (no hard delete).
3. Emit `audit_event('ORG_DIRECTORY_SYNC', {org_id, action})`.

**Failure handling:**
* Retries with exponential backoff.
* If sync is down > 24h, surface Ops alert.
* **Data hygiene:** name changes are logged to `audit_event` with prior/new values; collision on org names is tolerated (display only).

**Security:**
* Read-only service account allowed to list organizations; no user data or membership is read or stored.

---

## 45) SSE Replay Tuning (Settings)

**Goal:** Make the replay buffer tunable per environment/load profile.

**Settings (Org/System):**
* `sse.replay.max_events` (INT): default **1000**.
* `sse.replay.max_age` (DURATION): default **10m**.
* `sse.max_clients_per_org` (INT): default **0** (unlimited). If >0, new connections over the limit are throttled (HTTP 429) and an SSE `error` event is emitted to existing clients.
* `sse.max_events_per_sec_per_org` (INT): default **0** (unlimited). If >0, per-org event fan-out is rate-limited with token bucket; excess emissions are batched and delivered on the next interval.

**Server behavior:**
* Each stream maintains a ring buffer of `≤ max_events` and evicts entries older than `max_age`.
* If a client presents `Last-Event-ID` older than the window, send a **sync snapshot** then resume live.
* Changes are hot-reloaded via Settings pub/sub.
* When org-level throttles are enabled, the server enforces them before enqueueing to Redis Streams and surfaces `sse.org_throttle_total{org,reason}` metrics.

**Observability:**
* Metric: `sse.replay.evictions`.
* Alert if `sse.replay.evictions` spikes > P95 baseline for 15min (suggest increasing buffers).


### 45.1 Replay security checks
* Replay snapshot omits masked fields entirely; serializers reuse `*_secure` views.
* If `Last-Event-ID` predates retention window, server emits a **snapshot** then resumes live; snapshot generation is RLS-scoped to the caller.
* **DoS guard:** per-org token bucket for enqueue; when saturated, **drop** non-critical `progress` events first; never drop `artifact_state` or `portal_link_invalidated`.

---

## 46) Case Field Enumerations via Settings

**Objective:** Strongly type `case.status` and `case.representation_type` using centrally managed enums.

**Settings (Org/System):**
* `case.status.enum` (JSON array of strings)
* `case.representation_type.enum` (JSON array of strings)

**Validation:**
* API layer enforces membership in the active org/case effective enums.
* DB adds check constraints that are generated/migrated from the current system enum sets for baseline safety; app-level validation guards drift across versions.

**Admin workflow:**
* Enum changes go through Settings bundles (`/validate` → `/activate`) with scheduled activation.
* Backward compatibility: existing records are allowed; UI prevents selection of deprecated values.

**Testing:**
* Contract tests verify rejects on unknown enum values; history shows bundle/version that authorized each stored value.

---

## 47) Portal Fetch-time Guard (Explicit)

**Purpose:** Make the release-state guard unmistakable in the portal spec.
**Rule:** A signed URL or direct download **must** validate at fetch time:

* `artifact.state == 'APPROVED'`
* `artifact.id` and `content_sha256` match the signed parameters
* `expiry` is in the future

**Invalidation semantics (binding):**
* When an approval swap or rejection affects an artifact backing a live link, the server:
  1) **terminates** any in-flight transfers and responds **412 (If-Match)** or **403 (state changed)**,
  2) emits SSE event `portal_link_invalidated` with `{artifact_id, reason, ts}`,
  3) logs `audit_event('PORTAL_DOWNLOAD_DENIED', {artifact_id, reason})`.

If an artifact transitions away from `APPROVED` (e.g., **REJECTED** after approval), the fetch fails with `403` and the portal shows “This document is no longer available” banner.

**Telemetry:**
* Emit`audit_event('PORTAL_DOWNLOAD_DENIED', {artifact_id, reason})` on rejections.

---

## 48) LLM Evidence Store — PII Posture

**Principle:** Evidence is always redacted; unredacted prompts/responses never persist beyond transient execution memory.

**Storage contract:**
* Persist only: `{prompt_template_id, template_version, redaction_ruleset_id, redaction_stats, model_id, model_version, input_hashes, output_hashes, request_id, actor_id, case_id, timestamps}`.
* Store redacted prompt/response **excerpts** for debugging **when** `evidence_store.redacted_excerpts.enabled=true` (default). When `privacy.hipaa.enabled=true`, this setting MUST be **false**.

**Access:**
* Roles: `auditor`, `sysadmin` via dedicated endpoints.
* Every read emits `audit_event('EVIDENCE_READ', {request_id, actor_id})`.

**Retention:**
* Default ≥ **2× artifact retention** for non-content metadata; excerpts follow the same schedule.

**Tests:**
* Security tests assert no code path writes unredacted payloads to disk or object storage.
* Redaction unit tests validate that configured PII classes are removed with recall ≥ 0.99 on the golden set.

---

## 49) Request Signing & Key Rotation (Global)

**Purpose:** Standardize HMAC signing across internal POST/PUT endpoints for tamper-evidence and replay control.

**Headers:**
* `X-Signature-Key-Id`: opaque key identifier (from Settings).
* `X-Timestamp`: RFC3339 in UTC (e.g., 2025-01-01T12:00:00Z)
* `X-Request-Signature`: HMAC-SHA256( X-Signature-Key-Id || "\n" || X-Timestamp || "\n" || <raw body bytes> ) hex.

**Key management:**
* Keys are stored per org/client in Settings (`security.request_signing.keys[]`).
* Rotation: mark new key `active=true`, old key `active=true` for 24h overlap, then `active=false`.
* Audit: `audit_event('SIGNING_KEY_ROTATED', {key_id, org_id})`.

**Verification algorithm:**
1. Parse X-Timestamp; reject if |now - ts| > 300s (clock skew).
2. Look up key by `X-Signature-Key-Id`.
3. Compute HMAC as above; constant-time compare to `X-Request-Signature`.
4. On mismatch → `401 AUTH_ERROR`; on unknown key → `401 AUTH_ERROR` with `details.reason='UNKNOWN_KEY_ID'`.
5. Pair with Idempotency-Key for 24h replay protection (as already specified).

**Replay control:**
* Pair with `Idempotency-Key` and store `(org_id, endpoint, idempotency_key, signature_sha256)` for 24h.
* On duplicate with differing signature → `409 CONFLICT`.
* **Echo headers:** On success the server echoes `Idempotency-Key` and `X-Request-ID`; clients must display correlation.

**Acceptance:**
* Requests without both headers → `401`.
* Keys rotated remain valid per overlap window; after window expiry, requests fail with `UNKNOWN_KEY_ID`.

---

## 50) SSE Event Schema & Sync Snapshot

**Event types:**
* `progress`: `{ job_id, task, pct, ts }`
* `state`: `{ job_id, status, ts }`  // `PENDING|RUNNING|PAUSED|FAILED|COMPLETED`
* `error`: `{ job_id, code, message, correlation_id, ts }`
* `artifact_state`: `{ artifact_id, type, prev_state, state, ts }`
* `portal_link_invalidated`: `{ artifact_id, reason, ts }`  // emitted on approval swap/reject
* `message_new`: `{ thread_id, message_id, case_id, sender_id, ts }`  // Portal Messaging (§58)
* `message_read`: `{ thread_id, message_id, reader_id, ts }`          // read receipts (§58)

**Event ID:**
* **Monotonic, per-stream:** `case/{case_id}/{seq}` where `{seq}` is an atomically-incremented integer from Redis (key: `sse:case:{case_id}:seq`).
* **Transport buffer:**
  * Use Redis Streams per case: stream key sse:case:{case_id}
  * Emit with XADD sse:case:{case_id} MAXLEN ~ {max_events} * <fields...>
  * Replay: if client Last-Event-ID = "{case_id}/{seq}", translate to stream ID "{seq}-0" and XRANGE from there.
  * Evict by MAXLEN and by age with periodic XTRIM on server timer to honor max_age.
  * Store the monotonic {seq} alongside each XADD payload.

**Sync snapshot (sent when Last-Event-ID < window):**
```json
{
  "type": "snapshot",
  "case_id": "UUID",
  "jobs": [{ "id":"UUID", "status":"...", "updated_at":"..." }],
  "artifacts": [{ "id":"UUID", "type":"...", "state":"...", "updated_at":"..." }],
  "settings_snapshot_sha256": "hex",
  "ts": "RFC3339"
}
```

**Contract:**
* No PII in payloads.
* Clients may request replay from any `Last-Event-ID`; server returns replay or a one-time snapshot then resumes live.

* **Accessibility:** Servers emit human-friendly, single-sentence summaries alongside raw payloads for UI announcement in ARIA live regions (e.g., “Your download link was revoked; please refresh.”). UI MUST not announce high-frequency events more than once every 2s.

---

## 51) Case Enum Migration Playbook

**Goal:** Safely evolve `case.status` / `case.representation_type` without breaking existing rows.

**Steps:**
1. Add new values in Settings bundle; activate.
2. **DB migration:** add `CHECK ... NOT VALID` constraints reflecting the full current set.
3. Validate constraints after backfill (optional) using `ALTER TABLE ... VALIDATE CONSTRAINT`.
4. Deprecate values via Settings; UI hides deprecated items for new edits.
5. On final removal, run data migration to remap deprecated values, then regenerate constraints.

**Notes:**
* `NOT VALID` allows legacy rows to exist; updates/inserts must satisfy the new set.
* For auditability, history records bundle/version that authorized each stored value.

---

## 52) List Endpoint Contract (Pagination & Sorting)

**Applies to:** `/api/v1/artifacts`, `/api/v1/jobs`, `/api/v1/qa-logs`, `/portal/cases`.

**Query params:**
* `page` (INT, default 1), `page_size` (INT, default 50, max 200)
* `sort` (comma-list of `field:asc|desc`) — default:
  * artifacts: `created_at:desc`
  * jobs: `started_at:desc`
  * qa-logs: `created_at:desc`

**Response envelope:**
```json
{
  "items": [...],
  "page": 1,
  "page_size": 50,
  "total": 1234,
  "next_page": 2
}
```

**Errors:**
* Invalid `sort` field → `400 VALIDATION_ERROR` with `details.fields`.
  * Attempting to sort/filter on masked-only fields returns `400 VALIDATION_ERROR` (those fields are not queryable).

---

## 53) Compose/Policy Lint Settings (Declarative)

**Keys (Org/System):**
* `compose.policy.forbidden_patterns[]` — list of regex strings
* `compose.policy.required_sections[]` — list of section keys that must be present
* `compose.policy.max_links_per_section` — INT

**Enforcement:**
* Compose QA rejects artifacts violating forbidden patterns or missing required sections; Guardian reasons include `POLICY_FORBIDDEN_PATTERN`/`MISSING_SECTION`.

**Acceptance:**
* Contract tests assert Compose outputs fail when patterns match; success when lists are empty.


### 53.1 Additional acceptance tests (policy & regions)
* **Policy dry-run:** activating bundle with widened write access must produce `unsafe=true` and be blocked without `--force`.
* **Region lint:** settings activation with conflicting compute/storage regions is rejected; waiver path stamps manifests and emits audit events.

---

## 54) LangGraph Implementation Spec

### 54.1 Goals
* Deterministic control surfaces with non-deterministic content.
* Safe pause/resume/retry without duplication.
* Strong schema & referential guarantees at every node boundary.
* Full observability of LLM calls (tokens, latency, cost) under region allowlists.


### 54.2 Graph state (typed)
```python
# Python (pydantic v2) — shared by all nodes
from pydantic import BaseModel, Field
from typing import Any, Literal, Dict, List, Optional
from uuid import UUID

class GraphState(BaseModel):
    case_id: UUID
    job_id: UUID
    settings_snapshot_sha256: str
    inputs: Dict[str, Any]            # e.g., transcript indices, APPROVED artifact refs
    work: Dict[str, Any] = {}         # per-lane intermediate state
    outputs: Dict[str, Any] = {}      # lane -> validated list[...] (models in §10.3)
    qa_notes: List[Dict[str, Any]] = []
    rev_counters: Dict[str, int] = {} # lane -> attempts used
    traces: List[str] = []            # decision trace ids / correlation ids
    version: str = "analyze@v1"       # graph version id
```

**Persistence:** after each node, serialize `GraphState` to `job_checkpoint.checkpoint` with `checkpoint_hash`. On resume, load last checkpoint and continue.

### 54.3 Nodes & contracts

#### ContextBuilder
* **In:** `TRANSCRIPT`, `DIARIZATION`, **APPROVED** ingestion (`EXHIBIT_TEXT`, etc.), settings snapshot.
* **Out:** `inputs.transcript_index`, `inputs.knowledge_index`, normalized language metadata.
* **Checks:** region allowlist, minimum transcript coverage; emit `POLICY_BLOCK` if violated.


#### Lane nodes (Events, Timeline, Issues, Entities, Facts)
* **In:** `GraphState.inputs`, previous `work`.
* **Process:** chunking + retrieval; prompt build (template id+version recorded); LLM call; schema validate to the lane model list (§10.3).
* **Deterministic IDs:** generate UUIDv8 for each derived item using §27 anchors (transcript spans, referenced entities/events).
* **Out:** `outputs[LANE] = list[Model]`.
* **Retry:** bounded by `analyze.max_retries`. Categories:
  * `TRANSIENT` (provider 429/5xx/timeouts) → exponential backoff + jitter.
  * `SCHEMA` (validation fail) → 1 auto-repair attempt with corrective prompt; then fail lane.
  * `POLICY` (forbidden pattern) → fail lane (no auto-retry).


#### Lane QA node
* **In:** lane `outputs[...]`.
* **Checks:** schema, references (transcript spans resolve, entity/event IDs exist), policy lint, length bounds.
* **Side-effects:** write `qa_log` (`scope='ANALYZE_LANE'`) + upload notes to `/job/{job}/qa_logs/...`.
* **On fail:** if `rev_counters[lane] < max_retries`, write directive + loop back to lane node; else mark lane `FAILED`.


#### Final QA (cross-lane)
* **In:** all lane outputs.
* **Checks:** cross-references across lanes (e.g., Issues.related_events exist; Timeline items reference valid Events), no ID collisions, statistical anomalies (e.g., duplicate entities with very close names).
* **Out:** ready-for-artifact dicts per lane.
* **Side-effects:** `qa_log` (`scope='ANALYZE_FINAL'`).


#### Emit artifacts
* **Action:** create DRAFT artifacts for each lane (`ANALYZE_EVENTS|...|GAPS`), with manifests linking source artifacts + settings snapshot hash; submit each to Guardian (idempotent).
* **SSE:** emit `artifact_state` updates.


### 54.4 Concurrency & ordering
* `ContextBuilder` → barrier.
* Lanes run **in parallel** (Celery group) up to `analyze.parallelism` (settings); each lane internally may fan out per chunk but must **gather** and validate before writing to `outputs[LANE]`.
* `Final QA` waits for all lanes that did not hard-fail. If any required lane failed, job `FAILED` with reasons.


### 54.5 Checkpointing & idempotency
* **Checkpoint after:**
  * ContextBuilder completion,
  * each lane completion,
  * each QA pass,
  * each artifact emission.
* **Idempotency keys:** per node: `Idem:<job_id>:<node_name>:<rev#>`.
* Re-entrancy: re-running a completed node with same input hash returns prior result (no duplicate LLM calls) using a small result cache keyed by `(node,input_hash,template_version,model_id)` for TTL 24h.


### 54.6 LLM call wrapper (mandatory)
* Enforce region allowlist before call.
* Inputs redacted; record `prompt_template_id`, `template_version`, `model_id`, `model_version`, token usage, latency, and `output_hash`.
* Timeout and max tokens from settings (`*.token_ceiling`).
* Streaming disabled for batch; enabled only for interactive editors (Channels).
* Emits metrics: `llm_call_count`, `llm_latency_ms`, `llm_tokens_in/out`, `llm_cost_estimate`.
* Circuit breaker respected; fallback by `fallback_priority` filtered by language/region.


### 54.7 Memory & retrieval policy
* Transcript chunking: ~2–5k tokens per chunk, overlap 10–15%.
* Retrieval: BM25 + (optional) embedding index constrained to allowed regions; no external vectors if region disallowed.
* Map-reduce summarization only stores **redacted** map outputs transiently in `work`; never persisted unredacted.


### 54.8 Error classes & actions
| Class     | Examples                          | Action                           |
| --------- | --------------------------------- | -------------------------------- |
| TRANSIENT | 502/503/504/429, network timeouts | backoff retry (bounded)          |
| SCHEMA    | pydantic validation fail          | 1 repair attempt; else lane FAIL |
| POLICY    | forbidden pattern, region block   | hard FAIL (lane or job)          |
| INTEGRITY | missing referenced artifact       | hard FAIL + `INTEGRITY_ERROR`    |


### 54.9 Observability
* **Logs:** per node start/stop, input/output hashes, model selection decisions (and fallback reason).
* **Traces:** span per node (attributes: case_id, job_id, lane, model_id, template_version).
* **Metrics:** `analyze_lane_duration_ms`, `analyze_finalqa_duration_ms`, success/fail counters, retry counts, P95 per lane.
* **Prop tests hooks:** lanes expose pure functions for schema validation & ID determinism to the property-test harness (§23.5).


### 54.10 Security
* All reads happen under the worker’s **active_org_id** RLS session.
* `compute_region` stamped into manifests; verified by Guardian.
* No unredacted prompts/responses written to disk or object storage (per §48).

---

## 55) Graph Versioning & Migrations

* **IDs:** `analyze@v1`, `compose@v1` (semver allowed later).
* **Stored with:** `job.version`, artifact manifest (`graph_version`), QA logs.
* **Breaking change policy:** bump major; write a migration shim that:
  * maps prior lane outputs to the new schema,
  * or forces a re-run (recorded as **NEEDS_REVIEW** banner).
* **Runtime constraint:** do not mix outputs from different major versions within one job. Enforce at job start.

---

## 56) Compose Graph Details (parallels Analyze)

* Nodes: `OutlineBuilder` → `SectionWriter[*]` (parallel) → `SectionQA[*]` → `FinalWeave` → emit `COMPOSE_CLIENT|LAWYER`.
* **SectionWriter contract:** inputs are **APPROVED** Analyze refs + template section key; outputs a `ComposeSection` with deterministic references (IDs from Analyze).
* **QA:** structure + policy lint (per §53), forbidden patterns, reference resolvability.
* **Retries:** `compose.max_retries` with a repair prompt; then fail the section and surface in QA logs.
* **FinalWeave:** validates required sections (settings) and outline order; blocks Assembly until pass.

---

## 57) FinOps — Unit Economics & Deploy Guard (Epic G start)

### 57.1 Scope & definitions
* **Unit economics (initial):** Focus on LLM spend + delivery activity. Compute:
  * `finops_cost_per_case_usd = Σ(llm_call_cost_usd) per case` (tokens × model rate)
  * `finops_cost_per_org_usd = Σ(finops_cost_per_case_usd) per org per calendar month`
* **Delivery activity (visibility only, phase 1):** counts of `EMAIL|SMS|PORTAL` events by status; no carrier cost modeling in phase 1.


### 57.2 Data sources
* Metrics emitted by LLM wrapper (§7.6) and delivery subsystem (§17): `llm_tokens_in/out`, `llm_cost_estimate`, `delivery_receipt`.
* No DB schema changes required for phase 1 (greenfield).


### 57.3 Dashboard (Grafana)
Panels (org-scoped by variable):
1) **Cost per case (last 30d)**: `sum by (case) (finops_cost_per_case_usd{org="$org"})`
2) **MoM cost (org)**: current month vs prior; sparkline + % delta
3) **Top 10 cases by cost** (table): case id/title, cost, jobs, tokens
4) **Delivery activity**: stacked bar by channel/status for last 30d


### 57.4 Deploy guard — MoM regression
**Policy:** Block production deploy if org-level MoM cost regression exceeds threshold.
* Threshold: `finops.deploy_guard.mom_regression_pct` (default **10**)
* Window: compare **completed previous calendar month** to **month before it**

**CI gate (reference step)**
```yaml
- name: FinOps MoM regression gate
  run: |
    python ops/gates/check_finops_mom.py \
      --threshold_pct "${FINOPS_MOM_THRESHOLD:-10}" \
      --window_months 2 \
      --metric finops_cost_per_org_usd
```
* **Pass:** max(org MoM delta %) ≤ threshold → continue deploy
* **Fail:** gate blocks; job posts markdown summary with orgs exceeding threshold and links to the **Unit Economics & Delivery** dashboard


### 57.5 Monthly CSV artifact (FINOPS_REPORT)
**Purpose:** Per-org CSV for finance review and export.
* **Artifact type:** `FINOPS_REPORT` (already listed in Appendix F)
* **Cadence:** 1st of each month at 02:00 UTC (configurable via settings)
* **Layout:** `/org/{org}/reports/finops/{YYYY-MM}/finops_{org}_{YYYY-MM}.csv`
* **Columns (phase 1):**
  * `org_id, month, case_id, job_id, model_id, provider, tokens_in, tokens_out, llm_cost_usd, deliveries_email, deliveries_sms, portal_downloads, total_estimated_cost_usd`
* **Provenance:** manifest includes `{generator:"finops@v1", month, inputs:["metrics://llm","db://delivery_receipt"], settings_snapshot_sha256}`
* **Access:** scoped by RLS; visible to `org_admin|org_manager|auditor|sysadmin`


### 57.6 Acceptance
* Gate fails when simulated MoM delta > threshold; success otherwise.
* CSV artifact generated with >0 rows for active orgs on the 1st; manifest present and validates.
* Dashboard panels render for an org with test data; top 10 table populated.

---

## 58) Secure Portal Messaging

### 58.1 Scope & goals
Enable case-scoped, secure, rate-limited messaging between clients (`org_client`) and staff (`org_operator|org_reviewer|org_manager|org_admin`) inside the Portal/Staff UI, with attachments, profanity filtering, SSE updates, and strict RLS. Messaging is **internal** (non-email/SMS), stored in DB + object storage; attachments are **not** artifacts.


### 58.2 Data model & RLS
```sql
CREATE TABLE message_thread (
  id UUID PRIMARY KEY,                -- UUIDv7
  org_id UUID NOT NULL REFERENCES organization(id),
  case_id UUID NOT NULL REFERENCES "case"(id),
  title TEXT NOT NULL,
  created_by UUID NOT NULL REFERENCES user_account(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  archived BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE message (
  id UUID PRIMARY KEY,                -- UUIDv7
  org_id UUID NOT NULL REFERENCES organization(id),
  case_id UUID NOT NULL REFERENCES "case"(id),
  thread_id UUID NOT NULL REFERENCES message_thread(id),
  sender_id UUID NOT NULL REFERENCES user_account(id),
  body_md TEXT NOT NULL,
  profanity_flag BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  edited_at TIMESTAMPTZ NULL
);

CREATE TABLE message_attachment (
  id UUID PRIMARY KEY,                -- UUIDv7
  org_id UUID NOT NULL REFERENCES organization(id),
  case_id UUID NOT NULL REFERENCES "case"(id),
  thread_id UUID NOT NULL REFERENCES message_thread(id),
  message_id UUID NOT NULL REFERENCES message(id),
  content_uri TEXT NOT NULL,
  content_sha256 CHAR(64) NOT NULL,
  filename TEXT NOT NULL,
  content_type TEXT NOT NULL,
  content_length BIGINT NOT NULL,
  av_status TEXT NOT NULL CHECK (av_status IN ('PENDING','CLEAN','QUARANTINED')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE message_read_receipt (
  message_id UUID NOT NULL REFERENCES message(id),
  reader_id  UUID NOT NULL REFERENCES user_account(id),
  read_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (message_id, reader_id)
);

-- Indexes
CREATE INDEX message_thread_org_case ON message_thread (org_id, case_id, created_at DESC);
CREATE INDEX message_case_thread_time ON message (org_id, case_id, thread_id, created_at DESC);
CREATE INDEX message_attachment_status ON message_attachment (org_id, case_id, av_status, created_at DESC);

-- RLS (deny-by-default; case membership + policy driven)
ALTER TABLE message_thread ENABLE ROW LEVEL SECURITY; ALTER TABLE message_thread FORCE ROW LEVEL SECURITY;
ALTER TABLE message        ENABLE ROW LEVEL SECURITY; ALTER TABLE message        FORCE ROW LEVEL SECURITY;
ALTER TABLE message_attachment ENABLE ROW LEVEL SECURITY; ALTER TABLE message_attachment FORCE ROW LEVEL SECURITY;
ALTER TABLE message_read_receipt ENABLE ROW LEVEL SECURITY; ALTER TABLE message_read_receipt FORCE ROW LEVEL SECURITY;

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
  EXISTS (SELECT 1 FROM message m
           WHERE m.id = message_read_receipt.message_id
             AND m.org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
             AND udocket_can('MESSAGE','read',m.case_id,NULL,NULL))
)
WITH CHECK (FALSE); -- system-managed

-- AV + HIPAA gates (binding)
-- Attachments default av_status='PENDING'; downloads only when av_status='CLEAN'.
-- If privacy.hipaa.enabled=true, block attachments flagged PHI for non-staff roles.

-- Endpoints (Staff/Portal):
--  POST   /v1/portal/cases/{case_id}/threads
--  GET    /v1/portal/cases/{case_id}/threads?archived=
--  POST   /v1/portal/threads/{thread_id}/messages
--  GET    /v1/portal/threads/{thread_id}/messages?page=...           (pagination §52)
--  POST   /v1/portal/messages/{message_id}/attachments                (upload session + AV)
--  GET    /v1/portal/attachments/{attachment_id}/download             (If-Match/ETag; region re-check §13)
--  POST   /v1/portal/messages/{message_id}/read                       (idempotent)

-- SSE integration (§50)
--  Emit:
--   message_new  { thread_id, message_id, case_id, sender_id, ts }
--   message_read { thread_id, message_id, reader_id, ts }
--  Event ids follow `case/{case_id}/{seq}`.

-- Rate limits (settings §36.2)
--  portal.messaging.enabled (bool)
--  portal.messaging.rate_limits.user_msg_rpm (default 20)
--  portal.messaging.attachments.max_mb (default 50)
--  portal.messaging.allowed_attachment_types (default ["pdf","png","jpg","jpeg","docx"])
--  portal.messaging.attachments.allow_ranges (default false) – if true, apply §13.1 range checks to attachments.

-- Retention (settings)
--  portal.messaging.archive_days (default 180) – job auto-archives threads with no activity after N days.

-- Acceptance (additions)
--  * AV positive → attachment QUARANTINED; message remains; UI banner shown; audit logged.
--  * HIPAA on → PHI-tagged attachments downloadable by staff only; clients see POLICY_BLOCK.
```
**RLS policies (deny-by-default; reuse §2 helpers):**
```sql
-- Visibility constrained to active org and case membership
CREATE POLICY msg_thread_vis ON message_thread
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('MESSAGE_THREAD','read',case_id,NULL,NULL)
) WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('MESSAGE_THREAD','write',case_id,NULL,NULL)
);

CREATE POLICY msg_vis ON message
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('MESSAGE','read',case_id,NULL,NULL)
) WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('MESSAGE','write',case_id,NULL,NULL)
);

CREATE POLICY msg_att_vis ON message_attachment
USING (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('MESSAGE_ATTACHMENT','read',case_id,NULL,NULL)
) WITH CHECK (
  org_id = NULLIF(current_setting('udocket.active_org', true),'')::uuid
  AND udocket_can('MESSAGE_ATTACHMENT','write',case_id,NULL,NULL)
);
```
**Secure views (binding):** expose reads only via `message_secure`, `message_thread_secure`, `message_attachment_secure` with `(security_barrier=true)`; app role cannot `SELECT` base tables.


### 58.3 Object storage layout (attachments)
```
/org/{org}/case/{case}/messages/{thread_id}/attachments/{attachment_id}/content.bin
```
*AV scan:* reuse §37.3; `av_status='QUARANTINED'` blocks download (403) and emits `audit_event('MSG_ATTACHMENT_QUARANTINED', ...)`.


### 58.4 RBAC & policy
* **Participants:** any **case member** (staff roles) and the **client(s)** tied to the case (`org_client` membership).
* **Moderation:** when `portal.messaging.profanity_filter.enabled=true` (§36.2), server sets `profanity_flag=true` on detection; message still persists but the UI shows a moderation badge; orgs may flip to hard-block via settings later (not in M1).
* **Rate limits:** enforced via §36.2 (`portal.messaging.user_msg_rpm`, org rpm). 429 with Retry-After and exposed headers (CORS §21.6.1).


### 58.5 APIs (Portal/Staff)
* **Threads**
  * `GET /portal/cases/{case_id}/messages/threads` → list (pagination §52)
  * `POST /portal/cases/{case_id}/messages/threads` `{title}` → create
* **Messages**
  * `GET /portal/messages/threads/{thread_id}/messages`
  * `POST /portal/messages/threads/{thread_id}/messages` `{body_md, attachments[]?}`  
    * attachments created via **upload session** (§21.1.1), then bound to the new message
* **Attachments**
  * `GET /portal/messages/attachments/{attachment_id}/download` → requires `av_status='CLEAN'`
    * Responses include `Content-Disposition: attachment; filename="<sanitized>"`, `ETag: <content_sha256>`, `X-Content-Type-Options: nosniff`, and `Cache-Control: private` (or `no-store`).
    * **Strong match on fetch (binding):** require `If-Match: <ETag>` or a signed `etag=<ETag>` URL parameter, mirroring §13.1. Return **412** on mismatch.
    * **Ranges:** disallowed unless `portal.messaging.attachments.allow_ranges=true`. If allowed, validate `If-Match` for each `206` response; otherwise return `416`.

* **Read receipts**
  * `POST /portal/messages/{message_id}/read`

**SSE (Portal):**
* Stream: `GET /sse/case/{case_id}` already exists; emit `message_new` and `message_read` (§50).


### 58.6 Settings enforcement
* `portal.messaging.enabled` (ORG, default true): disables routes and hides UI when false.
* `portal.messaging.allowed_attachment_types`, `portal.messaging.attachments.max_mb`: validated at finalize; reject with `VALIDATION_ERROR`.
* `portal.messaging.staff_auto_subscribe_roles`: on thread creation, auto-subscribe roles for notifications (email/in-app via §17).


### 58.7 Frontend & accessibility
* WCAG 2.2 AA per §18.2; message list uses roving tabindex; “New message” announced in a **polite** ARIA live region; throttle announcements to ≤ 1 per 2s.
* Keyboard accessible attachment picker; drag-drop has click/keyboard alternative (2.5.7).


### 58.8 Observability & alerts
* Metrics: `portal_msg_sent_total{org,case}`, `portal_msg_attachment_quarantined_total`, `portal_msg_rate_limit_total`, `portal_msg_sse_clients{case}`.
* Dashboard added in §20.2.
* Alert: spike in `portal_msg_rate_limit_total` or `attachment_quarantined_total` P95 over 15m → notify Support with top offending orgs.


### 58.9 Acceptance tests
* RLS: client cannot read messages from another case; staff restricted by operator scope.
* Rate limit: exceed user rpm → 429 with exposed headers.
* Attachments: EICAR upload → `QUARANTINED` and blocked download; clean file succeeds.
* SSE: sender posts → recipient receives `message_new`; read event emits `message_read`.
* Profanity flag: when enabled, flagged message stored with `profanity_flag=true`; UI badge visible.

---

## Appendix A — System context & sequence diagrams (normative)

### A.1 System context
```
[Client/Staff UIs] --OIDC--> [Keycloak]
[Client/Staff UIs] --REST/SSE--> [Web/Channels] --RPC--> [Workers]
[Workers] <--> [Guardian] <--> [Postgres (RLS)]
[Workers] <--> [Signer]   <--> [KMS/TSA/OCSP]
[All services] <--> [Object Storage]
[All services] --> [Logs/Metrics/Traces]
```

### A.2 Upload → Guardian → Approve (sequence)
```
Client -> Web: POST /uploads (create session)
Client -> Storage: PUT content (staging)
Client -> Web: POST /uploads/{id}/finalize (Idempotency-Key)
Web -> DB: COPY object + INSERT artifact(DRAFT)
Web -> Guardian: submit(artifact_id, snapshot)
Guardian -> DB: UPDATE state READY|QUARANTINED; INSERT decision
Reviewer -> Web: POST /reviews/{artifact}/approve (OCC)
Web -> DB: demote prior APPROVED (type); approve target
```

## Appendix B — Threat model (summary)
### B.1 DFD (text)
```
External Entities: Users, Providers(TSA/LLM/Email/SMS)
Processes: Web, Channels, Workers, Guardian, Signer
Data Stores: Postgres(RLS), ObjectStore(WORM for audit seals), Redis
Trust Boundaries: Browser<->Ingress, Ingress<->Web/Channels, Web<->Workers, Services<->DB/Obj
```
### B.2 Top threats & mitigations
| Threat | Vector | Mitigation |
|---|---|---|
| RLS bypass | missing GUC / pooling | §2.2.2 canaries, fail-closed, health gates |
| Signed URL replay | token theft | single-use tokens, If-Match ETag, anomaly revocation |
| Prompt exfiltration | exhibits/emails | redaction pre-call, forbidden patterns, no raw persistence (§48) |
| Guardian rule poison | bad policy | policy dry-run/diff + rollback (§36.9–36.10) |
| Region leak | cross-region reuse | §8.1 lints & waiver stamping |

## Appendix C — Data classification matrix
| Data class | Storage | At rest | In transit | Masking | Retention | Roles |
|---|---|---|---|---|---|---|
| PUBLIC | DB | n/a | TLS | n/a | 365d | all |
| INTERNAL | DB | disk enc | TLS | none | 365d | org roles |
| PII | DB + Obj | field AEAD (where flagged) | TLS | view masking | per org | least privilege |
| SENSITIVE_PII | DB + Obj | field AEAD + KMS | TLS | masking | stricter (§15) | reviewers/auditors |

## Appendix D — Tenant lifecycle runbooks
**Provisioning:** create org, verify domain (SPF/DKIM), configure regions, set budgets, import templates, rotate initial keys.  
**Offboarding:** disable logins, export data (tamper-evident), revoke keys, purge per retention/erasure mode, archive audit seals.

## Appendix E — Privacy & Security control mapping
**SOC2/ISO anchors (excerpt):**  
* A.9 Access Control → §2, §36  
* A.12 Logging & Monitoring → §20, §20.1  
* A.14 System acquisition, development → §21, §23  
* A.17 Business continuity → §24.1  
Owners noted in runbooks repository.

## Appendix F — Canonical artifact type guidance (non-exhaustive; validated by policy)

```
INTAKE,
TRANSCRIPT_INPUT, AUDIO_NORMALIZED, TRANSCRIPT, DIARIZATION,
ANALYZE_EVENTS, ANALYZE_TIMELINE, ANALYZE_ISSUES, ANALYZE_ENTITIES, ANALYZE_FACTS, ANALYZE_GAPS,
COMPOSE_CLIENT, COMPOSE_LAWYER,				# EXCLUSIVE
ASSEMBLED_DOC_CLIENT, ASSEMBLED_DOC_LAWYER, # EXCLUSIVE
SIGNATURE_CERT, DESTRUCTION_CERT,			# EXCLUSIVE
TEMPLATE, QUESTIONNAIRE, REFERENCE_SNAPSHOT,
EXHIBIT_RAW, EXHIBIT_TEXT,
COURT_DOC_RAW, COURT_DOC_TEXT,
EMAIL_RFC822, EMAIL_TEXT, EMAIL_ATTACHMENTS,
FINANCIALS_RAW, FINANCIALS_TABLE,
MEMO_TEXT_*							# multiple memos by suffix (enforced by Guardian policy)
AUDIT_SEAL, ERASURE_JOURNAL, `SYSADMIN_RECERT_REPORT`
PENTEST_REPORT,                       # internal governance artifact
FINOPS_REPORT,                        # monthly per-org CSV (FinOps §57.5)
DPIA_RECORD, ROPA_RECORD              # privacy governance artifacts
* Settings key `artifact.exclusive_types[]` MUST be a subset of the above (or added via extensions with Guardian rules).
```

> Guardian & Settings enforce allowable values/patterns; database accepts `TEXT` types matching `^[A-Z0-9_]+$`.

---

## Appendix G — Data Residency & Legal Matrix (pointer & shape)

**Version:** `v1` (referenced by `privacy.legal.matrix_version`)

**Scope:** Maps `region_tag` → `jurisdictions[]` → constraints.

**Example (excerpt):**
| region_tag | jurisdictions           | storage_constraints                               | transfer_rules                          | breach_notice_sla |
|-----------:|-------------------------|----------------------------------------------------|-----------------------------------------|-------------------|
| EU         | EU, EEA                 | At-rest within EU; cross-region waiver required    | SCC/adequacy required for 3rd countries | 72h               |
| NA         | US (federal), CA        | At-rest in NA                                      | CCPA/CPRA contractual controls          | state-dependent   |
| APAC       | AU, SG, JP (varies)     | Country-specific allowlists (org policy driven)    | Local statutes                           | varies            |

**Binding rules:**
1) `compute_region` and `storage_region` MUST be subsets permitted by the **intersection** of org- and case-jurisdictions.
2) When `cross_region_waiver=true` (§8.1), a waiver record is required; Guardian stamps `cross_region=true`.
3) Settings activation fails if org declares jurisdictions incompatible with configured allowlists.

**Change control:** Matrix updates bump `privacy.legal.matrix_version` and require Security + Privacy dual approval.

**Shape (YAML excerpt):**
```yaml
matrix_version: v1
regions:
  EU:
    jurisdictions: [EEA, UK]
    constraints:
      residency_required: true
      cross_border_allowed: false
      breach_notice_sla_days: 3
  NA:
    jurisdictions: [US, CA]
    constraints:
      residency_required: false
      cross_border_allowed: true
      breach_notice_sla_days: 30
```

**Usage:** §8.2 validators resolve `privacy.legal.matrix_version` → this file; activation and runtime checks consult its constraints.

---

## Appendix H — DPIA & RoPA Process (new)

### H.1 Triggers
* New or materially changed processing of PII/SENSITIVE_PII (see Appendix C).
* Introduction or change of LLM providers/models handling PII.
* Cross-region data transfers outside current allowlists.

### H.2 DPIA minimum fields (stored in `DPIA_RECORD` artifact)
* `{org_id, case_scope?, processing_purposes[], data_categories[], lawful_basis, risks[], mitigations[], residual_risk, reviewers[], approved_at?, next_review_due}`
* Redaction: free-text fields pass through PII scrubbers (§29.1) before persistence.

### H.3 RoPA snapshot (stored in `ROPA_RECORD`)
* `{org_id, activities[], controllers, processors, data_subjects[], data_categories[], recipients[], retention, transfers[], dpo_contact}`

### H.4 Roles & access
* Create/update: `privacy_officer|sysadmin`.
* Read: `auditor|sysadmin` (realm) and org-scoped `org_auditor` if enabled.

### H.5 Retention
* DPIA/RoPA artifacts retained ≥ **case retention** and not less than **2 years** (org-configurable via Settings).

### H.6 Audit & metrics
* `audit_event('DPIA_CREATED'|'ROPA_CREATED', {...})`; metrics per §20.

---

## Appendix I — ERD & Service Map
* **ERD:** `docs/erd/udocket-erd.svg` (source `docs/erd/udocket-erd.drawio`)
* **Service dependency graph:** `docs/diagrams/service-map.svg` (source `docs/diagrams/service-map.mmd`)
* **CI:** `diagram:diff` blocks merges on un-sourced SVG changes (see §23).

---

## Appendix J — State machines
* **Artifact lifecycle state diagram:** `docs/diagrams/state-machine-artifact.svg`
* **Job state diagram:** `docs/diagrams/state-machine-job.svg`
* **Compose section flow:** `docs/diagrams/state-machine-compose.svg`
* **UUIDv8 vectors:** `spec/vectors/uuidv8.json` (consumed in §23 tests).

---

## Appendix K — TLS Policy (normative)
* Min version: configurable via `api.tls.min_version` (default 1.2); prefer 1.3.
* Allowed ciphers are governed by `api.tls.allowed_ciphers`; CBC suites are forbidden.
* HSTS `max-age >= 180d`, includeSubDomains for staff domains.

---

## Appendix L — DB Autovacuum Baselines (ops cheat-sheet)
* HOT partitions (audit_event, delivery_receipt, guardian_decision_history): `vacuum_scale_factor=0.05`, `analyze_scale_factor=0.02`, `naptime=30s`.
* Monitor `pg_stat_all_tables.n_dead_tup` and alert at 80th percentile of historic baseline.

---

## Appendix M — Privacy Artifacts Retention (pointer)

**Path (repo):** `docs/privacy/retention/<version>/retention.yaml` (e.g., `v1`).

**Contents:** Baseline retention periods (days) for `DPIA_RECORD`, `ROPA_RECORD`, `ENTITLEMENT_SNAPSHOT`, `AUDIT_SEAL`, and HIPAA overrides. §38.5 references Appendix H when HIPAA mode is enabled.

---

## Appendix N — Retention Baselines
* Baseline (can be raised per org): artifacts ≥ 365d; audit_event ≥ case retention; privacy artifacts (DPIA/RoPA) ≥ 730d;
  evidence-store metadata ≥ 2× artifact retention; object-store WORM lock for immutable audit sink per §20.1.
* HIPAA mode overrides: shorter excerpt retention (excerpts disabled), stricter access logging (§38.5).

---

## Glossary

* **Artifact:** Immutable content object (unique UUID) plus state.
* **Exclusive type:** Artifact type for which a case may have at most one **APPROVED** artifact at a time (enforced at approval).
* **Approval:** Human action that promotes `READY → APPROVED`; **only APPROVED is consumable** by downstream and portal.
* **Archived:** Visibility flag to remove from default lists.
* **Settings snapshot:** Frozen map of effective settings recorded with jobs/decisions.
* **Derived ID (UUIDv8):** Deterministic ID for in-document entities generated from stable anchors.
