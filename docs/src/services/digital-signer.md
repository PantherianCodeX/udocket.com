---
title: uDocket — Digital Signer Technical Design
subtitle: Platform Signing, Trust Roots, and Attestation Specification
author:
  - Document Signing Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Security Engineering
  - Platform Architecture
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - QA Engineering Lead
  - SRE Manager
approved_by: 
approved_date: 
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
      figure svg text,
      figure svg tspan {
        fill: #111 !important;
      }
      figure svg text {
        font-family: "DejaVu Sans", "Trebuchet MS", Arial, sans-serif !important;
      }
      figure.full-width-diagram img {
        width: 100%;
        height: auto;
        display: block;
      }
    </style>
  - <header class="page-header">uDocket — Digital Signer Technical Design <br>
    Platform Signing, Trust Roots, and Attestation Specification</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

| Field | Value |
| --- | --- |
| Authors | Document Signing Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Security Engineering; Platform Architecture |
| Reviewers | QA Engineering Lead; SRE Manager |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by | |
| Approved date | |

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Document Signer service responsible for platform signatures, client attestation workflows, TSA/OCSP validation, trust-root management, and FIPS enforcement.
- **Structure:** Sections follow the standard 0–10 service template; appendices referenced here live in the ops runbook catalog and Settings registry key maps.
- **Maintenance:** Run `python scripts/docs/lint_docs.py` and `python scripts/docs/link_check.py --strict` before proposing signer changes. Signing policy or PKI updates require ADR references in the PR.
- **Change protocol:** Modifying signature policies, TSA/OCSP profiles, or trust-root rotations demands dual approval (Security + Architecture) and an update to this spec plus the relevant runbooks.
- **References:** TDD §7.2 (summary), ADR-0001, ADR-0002, ADR-0003, Ops runbooks `RB-SIGN-*`.
- **Contacts:** Security Engineering (service owner), Platform Architecture (co-owner), on-call list `signer-oncall@`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Provide tamper-evident deliverables with verifiable trust anchors for every platform artifact. **|**
**Contract:** Digital Signer accepts canonical content, produces PDF/A (or COSE/JWS) outputs with platform signatures, validates TSA/OCSP responses, and enforces deliverable-specific signature policies. **|**
**State:** Signed artifacts persist in object storage with manifests recording signature metadata, TSA tokens, OCSP results, and FIPS posture; auxiliary records track client attestations. **|**
**Failures & handling:** TSA/OCSP outages, trust-root drift, or FIPS attestation failures block portal release and trigger runbooks (§5, §8). **|**
**Observability:** Grafana “Signer & TSA” and “Deliverable Signatures” dashboards monitor latency, TSA drift, OCSP freshness, and policy violations; CI jobs verify FIPS posture. **|**
**Breadcrumbs:** Implementation `apps/platform/operations/signer.py`, policy resolver `apps/platform/operations/signer_policy.py`, security guard `packages/udocket_core/security/fips_guard.py`, tests `tests/platform/operations/test_signer_modes.py`, `tests/platform/operations/test_signature_policy.py`. **|**
**References:** §2 Responsibilities, §4 State management, §5 Failure modes, §7 Security & compliance, ADR-0002.

- Signing pipeline converts canonical TXT/MD/JSON into PDF/A (or JWS) envelopes, applies platform signature + TSA token, and records signature manifests for Guardian, portal, and audit surfaces.
- Trust roots (`sign.trust_roots[]`) and signature policies (`sign.signature_policies[]`) are governed via Settings activations; rotations emit audit artifacts `SIGN_TRUST_ROOTS@<version>`.
- OCSP/CRL checks and TSA validation happen per signature with cached soft-fail windows; failures quarantine deliverables and page on-call.
- Output artifacts include signed PDF/A files, `SIGNATURE_CERT` records, and optional client attestations; manifests capture `{policy_id, key_version, tsa_token_hash, ocsp_status, fips_mode}` for provenance.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Enumerate functional responsibilities and non-goals. **|**
**Contract:** Spell out mandatory behaviours, idempotency, regulatory duties. **|**
**State:** Describe ownership of state transitions or data stewardship. **|**
**Failures & handling:** Identify responsibility gaps and escalation paths. **|**
**Observability:** Checks proving each responsibility works. **|**
**Breadcrumbs:** Implementation/tests supporting each responsibility. **|**
**References:** Service/TDD sections that expand on responsibilities.

### 2.1 Signing pipeline & deliverable integration (binding)

**Purpose:** Describe how canonical content progresses through signing so downstream flows remain deterministic. **|**
**Contract:** Deliverables follow a fixed pipeline: produce canonical content → render envelope → sign + timestamp → persist manifests → promote deliverable. Raw artifacts remain stored but marked `requires_signature=true` to block release without the signed companion. **|**
**State:** `deliverable` rows capture `{status, signature_manifest, tsa_token_hash, policy_id}`; auxiliary tables store TSA/OCSP evidence and client acknowledgement artifacts. **|**
**Failures & handling:** Pipeline stages failing validation leave deliverables in `PENDING_SIGNATURE`, emit `SIGNING_PIPELINE_BLOCKED`, and trigger §5.1 remediate-or-rollback steps. **|**
**Observability:** Metrics `signer_request_latency_seconds`, `signer_queue_depth`, `signature_manifest_error_total` plus audit JSONL records; dashboards highlight pipeline stage latency and error distribution. **|**
**References:** §3 API contract, §4 State management, `ops/runbooks/signer/pipeline_block.md`. **|**
**Breadcrumbs:** Implementation `apps/platform/operations/signer.py::issue_signed_document`, packager `packages/udocket_core/signer/packager.py`, tests `tests/platform/operations/test_signer_pipeline.py`.

- Canonical stages:
  1. Producing agent emits TXT/MD/JSON (`class='DL'`, `status='GENERATED'`).
  2. Packager renders PDF/A or COSE/JWS envelope according to signature policy.
  3. Document Signer applies platform signature + TSA token; OCSP/CRL validation occurs inline.
  4. Manifest records `signatures[]` with `{policy_id, key_version, tsa_token_hash, ocsp_status, fips_mode}` and persists auxiliary evidence.
  5. Deliverable transitions to `status='SIGNED'` and, after Guardian verification, to `status='RELEASED'`.
- Staff UI and portal download flows leverage the same manifest metadata ensuring enforcement matches the delivered copy.
- Deliverable toggles cannot enable artifacts whose signature policy outranks the org’s configured `sign.trust_mode`.
- Signing jobs run on a dedicated Celery queue sized for predictable latency; queue depth and worker autoscaling knobs live in `infra/kubernetes/digital-signer/`. Metrics `signer_queue_depth` and `signer_worker_ready` (Prometheus) drive the scaling policy.
- Idempotency is scoped per artifact via `Idempotency-Key`; repeat submissions with identical payloads replay cached results, whereas mismatched payloads raise `IDEMPOTENCY_SIGNATURE_MISMATCH` and emit audit `SIGN_IDEMPOTENCY_CONFLICT`.

### 2.2 Signature policies & client affirmation (binding)

**Purpose:** Bind deliverable definitions to signing and acknowledgement behaviour. **|**
**Contract:** Settings `sign.signature_policies[]` define reusable policies with fields `{platform_signature, client_signature, tsa_profile_id, ocsp_profile_id, fips_required, ack_template_id?}`. Deliverables reference `signature_policy_id`; switching policies emits `SIGNATURE_POLICY_CHANGE` events and regenerates signed copies. **|**
**State:** Policies reside in Settings bundles and are denormalized into manifests; client attestations create `CLIENT_SIGNATURE_CERT` or `CLIENT_ATTESTATION` records linked to deliverables. **|**
**Failures & handling:** Missing attestations, expired SLAs, or policy downgrades block release and route through `RB-SIGN-ACK` (§8.1). **|**
**Observability:** Metrics `signature_policy_violation_total`, `client_ack_pending_total`, dashboards “Deliverable Signatures” and “Portal Acknowledgements”; SSE events `deliverable.client_ack_required`. **|**
**References:** §4.2 Certificate storage, §5.3 Policy mismatch failure mode, Guardian spec §5.2. **|**
**Breadcrumbs:** Policy resolver `apps/platform/operations/signer_policy.py`, portal workflow `apps/platform/portal/acknowledgement.py`, tests `tests/platform/operations/test_signature_policy.py::test_client_ack_enforced`.

- Default mappings:
  - `SIGN_POLICY_PLATFORM_REQUIRED` → platform signature required, client attestation optional (transcripts, Analyze summaries).
  - `SIGN_POLICY_PLATFORM_REQUIRED_CLIENT_OPTIONAL` → platform signature required, portal exposes acknowledgement toggle (Compose client deliverable).
  - `SIGN_POLICY_PLATFORM_REQUIRED_CLIENT_REQUIRED` → platform signature + mandatory client countersignature prior to release.
- Client acknowledgement workflow prompts for `ack_template_id`; portal captures attestations and writes auxiliary records. Deliverables remain `PENDING_CLIENT_ACK` until auxiliary status becomes `completed`; Guardian cancels portal URLs if SLA expires.
- Additional deliverables inherit `SIGN_POLICY_PLATFORM_REQUIRED` unless their catalog entry overrides it; policy upgrades require dual approval.
- Waivers follow Approval Swap semantics and produce audit artifacts; previous releases are revoked when policies change.
- Deliverable catalog governance: `deliverables.catalog[]` (SYSTEM) enumerates every deliverable with metadata `{stage, artifact_type, default_formats[], template_id, signature_policy_id, client_visibility, requires_client_ack, default_state, implementation_tier}`. Settings activation linting ensures signature policies exist, Guardian understands approval flows, and localization assets are present before enabling new deliverables.

### 2.3 Trust roots, PKI, and HSM integration (binding)

**Purpose:** Anchor signatures to certified cryptographic domains. **|**
**Contract:** Document Signer operates with Azure Key Vault Managed HSM (FIPS 140-3). Trust roots include an offline RSA-4096 root (`uDocket-root`), online ECDSA P-384 intermediate (`uDocket-deliverable`), and per-tenant leaf certificates; rotations require dual approval and automated validation. **|**
**State:** Certificates + key identifiers persist in Settings (`sign.trust_roots[]`, `sign.hsm.key_id`), manifest metadata, and audit artifacts `SIGN_TRUST_ROOTS@<version>`. **|**
**Failures & handling:** Attestation failure, expired CMVP certificate, or key drift halts signing, triggers `RB-SIGN-TRUSTROTATE`, and pages Security. **|**
**Observability:** Metrics `sign_hsm_attestation_status`, `sign_trust_root_version`, CI job `ci-fips-scan`, and runbook evidence stored under `ops/security/key_rotation/`. **|**
**References:** §7 Security & compliance, §8 Operational notes, ADR-0002. **|**
**Breadcrumbs:** HSM integration `apps/platform/operations/signer_hsm.py`, trust-root rotation script `ops/scripts/security/rotate_signing_keys.py`, tests `tests/platform/operations/test_signer_modes.py::test_pkcs7_and_cades`.

- Settings `sign.trust_mode ∈ {internal, hybrid, external}` controls certificate exposure. Default `hybrid` issues platform signatures plus qualified provider cross-certification; `external` restricts to public PKI for regulated deployments; `internal` reserved for sandbox/private clusters.
- `sign.fips_mode ∈ {optional, required}` per org controls algorithm enforcement; Guardian blocks promotion when policy conflicts with org FIPS requirements.
- OCSP/TSA profiles (`sign.ocsp.profiles[]`, `sign.tsa.profiles[]`) include endpoint URLs, SLAs, and soft-fail windows; health probes monitor last-success times.
- Non-production environments employ distinct roots/TSA sandboxes; manifests stamp `trust_level=nonprod`.

### 2.4 OCSP, TSA, and soft-fail windows (normative)

**Purpose:** Maintain signature revocation posture without blocking legitimate releases unnecessarily. **|**
**Contract:** OCSP/CRL checks run per signing request with cached responses respecting provider `max-age`; soft-fail window defaults to 30 minutes before portal download blocks. **|**
**State:** TSA tokens and OCSP proofs persist alongside signatures in manifests; cached responses stored in Redis with TTL. **|**
**Failures & handling:** Expired responses or unreachable responders raise `SIGN_VERIFY_SOFT_FAIL` (deliverable still available) and escalate to `SIGN_REVOKE_STATUS_UNKNOWN` after the soft window, quarantining portals (§5.1). **|**
**Observability:** Metrics `ocsp_latency_seconds`, `ocsp_staple_age_seconds`, `tsa_latency_seconds`, `tsa_time_drift_seconds`; alerts `ocsp_unreachable_total`, `tsa_drift_seconds`. **|**
**References:** §5.1 OCSP/TSA outage, §8.1 Runbooks & rotations. **|**
**Breadcrumbs:** Validator `packages/udocket_core/signer/verification.py`, cache `packages/udocket_core/signer/cache.py`, tests `tests/platform/operations/test_signer_verification.py`.

<figure class="full-width-diagram">
  <img class="diagram" src="../../build/mermaid/services/digital-signer/diagrams/signing-delivery-v1.svg" alt="Signing and delivery flow">
  <figcaption style="font-size: 0.9em; color: #555;">Signing and delivery flow</figcaption>
</figure>

______________________________________________________________________

## 3) API Contract

**Purpose:** Document public and internal interfaces. **|**
**Contract:** Define required inputs/outputs, authentication, and versioning. **|**
**State:** Highlight persisted payloads, schemas, queues, or files produced. **|**
**Failures & handling:** Enumerate error codes, retries, and backoffs. **|**
**Observability:** Metrics/logs/traces covering API health. **|**
**Breadcrumbs:** Controller handlers, schema definitions, integration tests. **|**
**References:** Link to schema fixtures or appendices.

<a id="digital-signer-external-interfaces"></a>

### 3.1 External Interfaces (binding)

| Endpoint / Stream | Purpose | Contract notes |
| --- | --- | --- |
| `POST /api/v1/sign` | Submit signing job for canonical content | Idempotent via `Idempotency-Key`; requires manifest digest + signature policy; returns signed artifact |
| `POST /api/v1/sign/verify` | Re-validate signatures and TSA for auditing | Used by Guardian + QA when rehydrating deliverables |
| `GET /api/v1/sign/certificates/{artifact_id}` | Fetch signature certificate chain / attestations | Requires reviewer or portal token; response includes platform and client certificates |
| SSE `sign.status` | Broadcast signing state transitions | Emits `queued`, `signing`, `signed`, `soft_fail`, `quarantined` |

Example request (service-to-service):

```bash
curl -X POST https://platform.local/api/v1/sign \
  -H "Authorization: Bearer ${SERVICE_TOKEN}" \
  -H "Idempotency-Key: dl-${artifact_id}" \
  -H "X-Signature-Key-Id: svc-guardian-signer-v2" \
  -H "X-Timestamp: $(date --utc +%FT%TZ)" \
  -H "X-Request-Signature: $(scripts/security/hmac_sign.sh body.json)" \
  -H "Content-Type: application/json" \
  -d @body.json
```

### 3.2 Internal Interfaces (normative)

- Celery worker orchestration uses dedicated queues (`signature.high`, `signature.bulk`) and relies on Worker Cluster job controllers; retries, backoff, and idempotency enforcement flow through `apps/platform/operations/signer_job.py`.
- Guardian integration submits deliverable manifests for judgment prior to release; acknowledgements and portal invalidation messages route through Notifications topics `deliverable.ready` and `deliverable.revoked`.
- Settings activation (`sign.*`) pushes trust-root, TSA/OCSP, and waiver configuration; activation lints invoke signer contract tests before enabling changes.
- Evidence store writers, manifest generators, and ack processors share the internal API layer `packages/udocket_core/signer/*`, ensuring deterministic manifests and audit append-only logs.

______________________________________________________________________

## 4) State Management

**Purpose:** Explain storage and configuration strategy. **|**
**Contract:** Define persistence guarantees, migration expectations, and retention. **|**
**State:** Describe schemas, caches, and configuration sources. **|**
**Failures & handling:** Cover corruption, drift, and reconciliation flows. **|**
**Observability:** Metrics for storage health, cache hit rates, or config parity. **|**
**Breadcrumbs:** ORM models, migrations, infrastructure manifests. **|**
**References:** TDD appendices or diagrams related to state.

### 4.1 Artifact manifests & evidence (binding)

**Purpose:** Capture persistence layout for signed deliverables and proofs. **|**
**Contract:** Manifests store signature metadata, TSA tokens, OCSP status, FIPS posture, waiver flags, and hash digests linking back to canonical content. Evidence store retains raw TSA/OCSP payloads and acknowledgement artifacts. **|**
**State:** Postgres tables `deliverable`, `signatures`, `auxiliary_artifact`, plus object storage buckets `deliverables/<case>/<artifact_id>/signed.pdf`. Redis caches short-lived OCSP responses. **|**
**Failures & handling:** Missing manifest fields or mismatched digests cause `SIGNATURE_MANIFEST_INVALID`; deliverable promotion blocked until corrected. **|**
**Observability:** Metric `signature_manifest_invalid_total`, audits `MANIFEST_FIX_APPLIED`; nightly validators (`scripts/signer/validate_manifests.py`) ensure schema parity. **|**
**References:** §2.1 Pipeline, §5 Failure modes, Appendix D schemas. **|**
**Breadcrumbs:** Manifest writer `packages/udocket_core/signer/manifest.py`, evidence store `packages/udocket_core/signer/evidence.py`, tests `tests/platform/operations/test_manifest_integrity.py`.

### 4.2 Key, certificate, and waiver records (binding)

**Purpose:** Track cryptographic materials and compliance waivers. **|**
**Contract:** Trust roots, TSA/OCSP profiles, and waivers persist via Settings; rotation artifacts stored under `ops/security/key_rotation/`. Waivers (`FIPS_MODE_EXCEPTION`, `SIGNATURE_POLICY_EXCEPTION`) require approval metadata, expiry, and remediation plans. **|**
**State:** Settings snapshots embed `sign.trust_roots[]`, `sign.ocsp.profiles[]`, `sign.tsa.profiles[]`; waiver ledger stored in `ops/security/waivers/signing/*.yaml` and mirrored in App.O decision logs. **|**
**Failures & handling:** Expired waivers trigger `signature_waiver_expiring_total` alerts; signing disabled until renewed or removed. **|**
**Observability:** Dashboard “Signer & TSA” exposes trust-root version, waiver counts; alerts `sign_trust_root_expiring_total`, `signature_waiver_active_total`. **|**
**References:** §7 Security & compliance, §8 Operational notes. **|**
**Breadcrumbs:** Settings activation pipeline `apps/platform/settings/services/signature.py`, waiver automation `ops/scripts/security/check_signer_waivers.py`, tests `tests/platform/operations/test_signer_waivers.py`.

### 4.3 Caching, idempotency, and replay tooling (normative)

**Purpose:** Preserve determinism for retries and support post-incident verification without mutating artifacts. **|**
**Contract:** Redis caches OCSP/TSA responses alongside expiry metadata, Postgres `idempotency_keys` enforces request replay semantics, and replay utilities validate signatures without re-issuing them. **|**
**State:** Namespaces `ocsp:<cert_fingerprint>` and `tsa:<profile>` (Redis), `idempotency_keys` rows scoped to `artifact:sign`, replay logs under `ops/signer/replays/<date>/`. **|**
**Failures & handling:** Cache poisoning or mismatched request hashes trigger `SIGN_IDEMPOTENCY_CONFLICT` alerts; replay mismatches output `SIGNATURE_REPLAY_MISMATCH` and route to RB-SIGN-VERIFY. **|**
**Observability:** Metrics `ocsp_cache_hit_ratio`, `idempotency_replay_total`, audit event `SIGN_REPLAY_EXECUTED`; CI task `scripts/signer/check_replay_fixture.py` validates fixtures. **|**
**Breadcrumbs:** Idempotency service `packages/udocket_core/idem/service.py`, cache helpers `packages/udocket_core/signer/cache.py`, replay tooling `ops/scripts/signer/replay_signature.py`.

______________________________________________________________________

## 5) Failure Modes

**Purpose:** Provide the resilience profile and default mitigations. **|**
**Contract:** Identify what must fail closed vs. degraded. **|**
**State:** Note circuit breakers, queues, or compensating transactions. **|**
**Failures & handling:** Enumerate incidents, fallback procedures, and manual runbooks. **|**
**Observability:** Alerts, dashboards, and SLOs tied to failure handling. **|**
**Breadcrumbs:** Runbooks, incident retros, chaos tests. **|**
**References:** Link to ops docs or ADRs describing failure strategy.

### 5.1 OCSP/TSA outage (binding)

**Purpose:** Contain revocation-check outages without jeopardizing compliance. **|**
**Contract:** Soft-fail window (default 30 minutes) allows downloads while responders recover; beyond that deliverables quarantine and portal links revoke until verification succeeds. **|**
**State:** Soft-fail incidents recorded in `ops/security/incidents/`, deliverables flagged `SIGN_REVOKE_STATUS_UNKNOWN`. **|**
**Handling:** Follow `RB-SIGN-TSA`—invalidate cache, switch to secondary responder, coordinate with vendor, and re-run verification before restoration. **|**
**Observability:** Alerts `ocsp_unreachable_total`, `tsa_drift_seconds`, `sign_soft_fail_active_total`; dashboards highlight responder status. **|**
**Breadcrumbs:** Runbook `ops/runbooks/signer/tsa_ocsp_outage.md`, automation `ops/scripts/security/failover_tsa.py`.

### 5.2 FIPS attestation failure (binding)

**Purpose:** Ensure cryptographic compliance before accepting traffic. **|**
**Contract:** Service aborts on failed attestation (`EXIT_FIPS_ATTESTATION_FAILED`); no signatures issued until `fips_healthcheck.verify()` passes. **|**
**State:** Failure evidence stored under `ops/security/fips/attestation_failures/`; incidents logged with waiver references if temporary downgrade approved. **|**
**Handling:** Execute `RB-SIGN-FIPS`—verify module certificate, reseed HSM/DRBG, rotate modules if required, and document remediation. **|**
**Observability:** Metrics `crypto_fips_selftest_fail_total`, `crypto_fips_module_cert_id`, alerts `fips_attestation_failure_total`. **|**
**Breadcrumbs:** Security guard `packages/udocket_core/security/fips_guard.py`, tests `tests/security/test_fips_guard.py`.

### 5.3 Signature policy mismatch or client SLA breach (normative)

**Purpose:** Prevent release when policies or acknowledgements fall out of alignment. **|**
**Contract:** Deliverables remain blocked if signature policy conflicts with org trust mode or client acknowledgement window expires. **|**
**State:** Portal stores SLA timestamps; Guardian queue marks deliverables with `SIGNATURE_POLICY_MISMATCH` or `CLIENT_ACK_OVERDUE`. **|**
**Handling:** Follow `RB-SIGN-ACK`—update policy, regenerate signed deliverables, or secure client countersignature before reopening portal access. **|**
**Observability:** Metrics `signature_policy_violation_total`, `client_ack_timeout_total`; SSE events notify staff of overdue acknowledgements. **|**
**Breadcrumbs:** Portal workflow `apps/platform/portal/client_ack.py`, Guardian integration `apps/platform/operations/guardian_signer_bridge.py`.

______________________________________________________________________

## 6) Observability

**Purpose:** Summarize telemetry and reliability expectations. **|**
**Contract:** SLO: signing request success ≥ 99.9 %, TSA drift ≤ 5 seconds, OCSP latency P95 ≤ 5 seconds. Removal of metrics requires Observability review. **|**
**State:** Dashboards “Signer & TSA”, “Deliverable Signatures”, and “Client Attestations” aggregate Prometheus metrics and audit events; PagerDuty service “Digital Signer & TSA” handles alerts. **|**
**Failures & handling:** Missing metrics or stale dashboards block releases per docs lint and Observability checklists. **|**
**Observability:** Metrics `signer_request_latency_seconds`, `signer_error_total`, `tsa_time_drift_seconds`, `ocsp_latency_seconds`, `signature_policy_violation_total`, `client_ack_pending_total`, `crypto_fips_mode{service}`. **|**
**Breadcrumbs:** Observability config `infra/observability/dashboards/signer.json`, alert rules `infra/monitoring/signer-prometheus-rules.yaml`, tests `tests/observability/test_signer_metrics.py`. **|**
**References:** §5 Failure modes, §8 Operational notes, Appendix D telemetry schema.

### 6.1 SLOs & Targets (binding)

**Purpose:** Define reliability expectations for signing, TSA, and OCSP operations. **|**
**Contract:** Signing requests, timestamping, and OCSP validation must meet the thresholds below before releases continue. **|**
**State:** Metrics `signer_request_latency_seconds`, `signer_error_total`, `tsa_time_drift_seconds`, `ocsp_latency_seconds`; dashboards “Signer & TSA” and “Deliverable Signatures”; audit artifacts for key rotations. **|**
**Failures & handling:** Breaches trigger RB-SIGN-INCIDENT, RB-SIGN-TSA, or RB-SIGN-OCSP as appropriate before new deliverables are approved. **|**
**Observability:** Grafana dashboards “Signer & TSA”, Alertmanager routes for signer/TSA/OCSP, synthetic signing tests. **|**
**Breadcrumbs:** Observability config `infra/observability/dashboards/signer.json`, Prometheus rules `infra/monitoring/signer-prometheus-rules.yaml`, runbooks `docs/src/ops/runbooks/signer/*.md`. **|**
**References:** TDD §12, Audit spec §4, Settings spec §7.3.

- **Signing success:** ≥99.9% of signing requests complete successfully each month; enforced via `signer_request_latency_seconds` P95 ≤ 5 seconds and `signer_error_total` burn-rate alerts tied to RB-SIGN-INCIDENT.
- **Timestamp authority drift:** `tsa_time_drift_seconds` remains ≤ 5 seconds absolute; violations trigger RB-SIGN-TSA and pause releases until corrected.
- **OCSP responsiveness:** OCSP round-trip P95 ≤ 5 seconds (`ocsp_latency_seconds`); sustained breaches escalate to RB-SIGN-OCSP before deliverables can be promoted.

______________________________________________________________________

## 7) Security & Compliance

**Purpose:** Detail cryptographic, residency, and regulatory controls enforced by the signer. **|**
**Contract:** FIPS 140-3 compliance enforced when `security.crypto.fips_requirement` or deliverable policy demands it; waivers require dual approval and time-boxed scope. Residency/policy waivers documented alongside `waiver_id` in manifests. **|**
**State:** Waiver artifacts (`FIPS_MODE_EXCEPTION`, `SIGNATURE_POLICY_EXCEPTION`) stored in `ops/security/waivers/`; manifests include `{fips_mode, fips_module_cert_id, waiver_id?}`. **|**
**Failures & handling:** Waiver expiry, certificate drift, or module deprecation escalate to Security incidents; traffic halted until compliance restored. **|**
**Observability:** Alerts `crypto_fips_waiver_active_total`, `signature_policy_waiver_expiring_total`, `sign_trust_root_expiring_total`; CI job `ci-fips-scan` validates code changes. **|**
**Breadcrumbs:** Security guard `packages/udocket_core/security/fips_guard.py`, waiver automation `ops/scripts/security/check_signer_waivers.py`, tests `tests/security/test_fips_guard.py`. **|**
**References:** ADR-0002, §5 Failure modes, §8 Operational notes.

- Startup attestation validates module self-tests, CMVP certificate ID (`security.crypto.expected_cert_id`), and DRBG source; failures abort boot.
- Only FIPS-approved algorithms permitted under FIPS mode; static analysis (`scripts/security/fips_cipher_lint.py`) blocks disallowed primitives.
- Disaster recovery runbooks verify FIPS attestation before region cutover; `crypto_fips_cert_expiry_days` provides 90/30/7-day alert thresholds.
- Cross-region waivers require rationale, expiry ≤ 7 days, and Security + Architecture approval; Guardian blocks deliverables during active waivers unless explicitly permitted.
- Inter-service authentication: All mutating signer APIs require HMAC headers and `Idempotency-Key`; clients must maintain clock skew ≤ 120 seconds and reuse the same key for retries. Request signing guidance aligns with platform policy in TDD §7.3.

______________________________________________________________________

## 8) Operational Notes

**Purpose:** Keep signing operations, drills, and release gates aligned with policy and security expectations. **|**
**Contract:** On-call rotations, runbooks, and release evidence must stay current; signing halts when FIPS, TSA/OCSP, or waiver gates fail until remediation completes. **|**
**State:** Runbooks under `ops/runbooks/signer/`, key-rotation evidence in `ops/security/key_rotation/`, release checklists `ops/releases/signing_release_checklist.md`, waiver records in App.O. **|**
**Failures & handling:** Stale playbooks, missing rotation artifacts, or failed release gates block deployment until remediation and evidence capture. **|**
**Observability:** Docs lint (`build_runbook_catalog.py --check`), PagerDuty analytics, dashboards “Signer & TSA” / “Deliverable Signatures”, alert `signer_release_gate_blocked_total`. **|**
**Breadcrumbs:** Runbooks `ops/runbooks/signer/`, automation `ops/scripts/security/rotate_signing_keys.py`, release tooling `ops/scripts/deploy/signing_release_gate.py`, drill tracker `ops/change/signer_rotations.ics`. **|**
**References:** §5 Failure modes, §6 Observability, §7 Security & compliance, Ops runbooks `RB-SIGN-*`.

### 8.1 Operational Posture (binding)

**Purpose:** Capture staffing, freeze windows, and attestation requirements that keep signing services ready. **|**
**Contract:** Security Engineering and Platform Architecture share PagerDuty “Signer SLO”, maintain FIPS-certified operators on-call, enforce change freezes during rotations, and document startup attestation evidence. **|**
**State:** Rosters `ops/security/signer_roster.yaml`, freeze calendar `ops/security/key_rotation/freeze_windows.ics`, attestation reports `ops/security/fips_attestation/<date>.json`. **|**
**Failures & handling:** Missing evidence or unstaffed rotations trigger incident review; signing remains paused until posture restored. **|**
**Observability:** PagerDuty response metrics, dashboards “Signer & TSA”, alert `signer_operator_coverage_gap_total`. **|**
**Breadcrumbs:** Roster files, freeze calendar, App.O decision logs. **|**
**References:** §7 Security & compliance, `RB-SIGN-FIPS`.

- Startup attestation validates CMVP certificate IDs (`security.crypto.expected_cert_id`), DRBG source, and HSM availability before pods accept work; failures abort boot.
- FIPS-required tenants pin signer pods to dedicated node pools and verify hardware AES, DRBG, and HSM slots via readiness probes.
- Cross-region waivers require ≤7 day expiry with dual approval; Guardian blocks deliverables while waivers remain active.
- Mutating APIs require mTLS, HMAC headers, and `Idempotency-Key`; clients maintain ≤120 s clock skew and reuse idempotency tokens for retries.

### 8.2 Incident Triggers (binding)

**Purpose:** Map alerts and dashboards to signer playbooks so responders act immediately. **|**
**Contract:** Alert definitions (`infra/monitoring/signer-prometheus-rules.yaml`) embed `RB-SIGN-*` identifiers; on-call documents evidence before clearing incidents. **|**
**State:** Alert payloads record activation IDs, key versions, and waiver references under `ops/security/incidents/signer_<date>.jsonl`. **|**
**Failures & handling:** Missing annotations or misrouted alerts require follow-up tasks and lint updates. **|**
**Observability:** Grafana “Signer & TSA”, PagerDuty routing, synthetic TSA/OCSP checks. **|**
**Breadcrumbs:** Alert rule files, PagerDuty service configs, runbook catalog. **|**
**References:** §5 Failure modes, §6 Observability, `RB-SIGN-TSA`.

- `signer_tsa_error_total` / `signer_ocsp_unknown_total` → `RB-SIGN-TSA` for TSA/OCSP outage response.
- `signer_hsm_attestation_status{status="failed"}` → `RB-SIGN-FIPS` before restoring queue processing.
- `signer_waiver_active_total` / `signer_release_gate_blocked_total` → review waivers via `RB-SIGN-ACK` or `RB-SIGN-TRUSTROTATE` and update App.O.
- `signer_queue_depth_high` and latency SLO breaches trigger backlog remediation via RB-SIGN-PIPELINE and scaling playbooks.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Maintain executable runbooks and drill cadence for key signing scenarios. **|**
**Contract:** Alerts map to `RB-SIGN-*` playbooks; quarterly drills rehearse trust-root renewal, TSA failover, FIPS recovery, and client acknowledgement remediation. **|**
**State:** Runbooks `ops/runbooks/signer/`, drill evidence `ops/security/key_rotation/<timestamp>/`, tabletop notes `ops/change/signer_rotations.ics`. **|**
**Failures & handling:** Stale runbooks or missing drill evidence block release sign-off until refreshed. **|**
**Observability:** Docs lint, PagerDuty analytics, Ops governance dashboards. **|**
**Breadcrumbs:** Runbook files, rotation scripts, drill tracker. **|**
**References:** `RB-SIGN-TSA`, `RB-SIGN-FIPS`, `RB-SIGN-ACK`, `RB-SIGN-TRUSTROTATE`.

#### 8.3.1 Runbook Index (informative)

| Runbook code | Scenario | Notes |
| --- | --- | --- |
| `RB-SIGN-TSA` | TSA/OCSP outage response | Rotates TSA credentials, fails over to backup TSA, captures evidence |
| `RB-SIGN-FIPS` | FIPS attestation recovery | Validates CMVP IDs, reinstates HSM slots, restores queue processing |
| `RB-SIGN-ACK` | Client acknowledgement remediation | Reconciles acknowledgements, notifies stakeholders, updates App.O |
| `RB-SIGN-TRUSTROTATE` | Trust-root / certificate rotation | Executes dual-publish rotation, records evidence, updates manifests |

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarise the signer runbooks executed during incidents and drills so responders act consistently. **|**
**Contract:** Each runbook ties to specific alerts and evidence requirements; responders update playbooks after every incident or drill. **|**
**State:** Runbook markdown lives under `ops/runbooks/signer/`, automation scripts under `ops/scripts/security/`, and evidence in `ops/security/key_rotation/`. **|**
**Failures & handling:** Missing or stale steps block deployment sign-off until refreshed. **|**
**Observability:** Docs lint, PagerDuty analytics, and drill dashboards track completion. **|**
**Breadcrumbs:** `ops/runbooks/signer/*.md`, `ops/scripts/security/*.py`, incident templates `ops/security/incidents/signer_*.md`. **|**
**References:** Alert catalog, Ops governance policy, §5 Failure modes.

- `RB-SIGN-TSA` — TSA/OCSP outage response with rollback steps for deliverable signing and synthetic verification.
- `RB-SIGN-FIPS` — FIPS attestation recovery including startup attestations, HSM validation, and waiver handling.
- `RB-SIGN-ACK` — Client acknowledgement remediation, backlog clearing, and App.O waiver coordination.
- `RB-SIGN-TRUSTROTATE` — Trust-root/certificate rotation workflow covering dual publish, smoke tests, and evidence upload.

#### 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover trust-root renewal, TSA failover, FIPS recovery, and acknowledgement remediation; evidence lands in `ops/security/key_rotation/<timestamp>/`.
- Drill scheduler `ops/change/signer_rotations.ics` tracks cadence and ownership; missed drills block release sign-off until completed.
- Docs lint and Ops governance dashboards verify evidence uploads and runbook freshness before closing audits.

### 8.4 Migrations & Backfills (normative)

**Purpose:** Govern trust-root rotations, HSM migrations, and manifest replays. **|**
**Contract:** Rotations follow dual publish (current/next) with ≤24 h overlap; manifest replays verify signatures after migrations before reopening queues. **|**
**State:** Rotation scripts `ops/scripts/security/rotate_signing_keys.py`, evidence directories `ops/security/key_rotation/<timestamp>/`, replay outputs `ops/signing/replay/<date>/`. **|**
**Failures & handling:** Rotation failures revert to prior key version and execute `RB-SIGN-TRUSTROTATE`; failed replays quarantine affected deliverables until resolved. **|**
**Observability:** Metrics `sign_trust_root_version`, replay divergence counters, CI job `ci-fips-scan`. **|**
**Breadcrumbs:** Rotation scripts, replay tooling, evidence archives. **|**
**References:** §4 State management, `RB-SIGN-TRUSTROTATE`.

- Pre-rotation checklist ensures HSM slot capacity, certificate bundles, and change approval before promoting new keys.
- Post-rotation smoke tests re-sign representative artifacts and validate OCSP/TSA status before releasing queue holds.
- Replay tooling supports manifest regeneration when signature policies or templates change, preserving audit trails.

### 8.5 Operational Workflows (normative)

**Purpose:** Document recurring signing tasks and release gating requirements. **|**
**Contract:** Releases require green TSA/OCSP dashboards, no outstanding waivers without expiry/mitigation, and signer backlog SLO compliance; acknowledgment workflows must close before client delivery. **|**
**State:** Release checklist `ops/releases/signing_release_checklist.md`, waiver logs in App.O, acknowledgement jobs `ops/signing/acknowledgement_checks.py`. **|**
**Failures & handling:** Missing checklist evidence or overdue waivers halt deployment until mitigated; acknowledgement backlog triggers `RB-SIGN-ACK`. **|**
**Observability:** Deployment guard `scripts/ci/check_signer_release.py`, metrics `signer_release_gate_blocked_total`, `signer_ack_pending_total`. **|**
**Breadcrumbs:** Release tooling, waiver logs, acknowledgement workflows. **|**
**References:** §7 Security & compliance, Notifications spec §7, Guardian spec §5.

- Release gate automation validates TSA/OCSP dashboards, signer queue depth, and waiver status before allowing cutover.
- Daily jobs reconcile client acknowledgement SLAs and notify Portal when outstanding signatures remain.
- Waiver reviews document mitigation and expiry in App.O; automation blocks new jobs when waivers lapse without renewal.

______________________________________________________________________

## 9) Dependencies

**Purpose:** Map upstream inputs and downstream consumers. **|**
**Contract:** Settings registry must supply trust roots, signature policies, TSA/OCSP profiles; Guardian enforces promotion checks; Portal executes acknowledgement flows; Reference Manager provides catalog metadata. **|**
**State:** Adoption telemetry `signer_adoption_status`, Guardian manifests, and portal logs record digest references and acknowledgement outcomes. **|**
**Failures & handling:** Upstream configuration drift or downstream enforcement gaps trigger runbooks (Settings diff, Guardian quarantine, Portal ack remediation). **|**
**Observability:** Dashboards “Settings Adoption”, “Guardian Residency Enforcement”, “Portal Acknowledgements”, alerts `signer_dependency_drift_total`. **|**
**Breadcrumbs:** Integration code `apps/platform/operations/signer_guardian_bridge.py`, Settings activation `apps/platform/settings/services/signature.py`, Portal ack controller `apps/platform/portal/client_ack.py`. **|**
**References:** Settings spec §6, Guardian spec §5, Reference Manager spec §4.

| Dependency | Interface / artifact | Responsibilities | Notes |
| --- | --- | --- | --- |
| Settings Registry | Activation bundles (`sign.*`, `privacy.*`) | Provides trust roots, policies, TSA/OCSP profiles, waiver metadata | Unsafe diff blocks activations; diff artifacts stored with release checklist |
| Guardian | Promotion hooks, SSE events | Blocks deliverable release until signatures validated; records manifest digests and waiver usage | Integration is synchronous; Guardian quarantines on signer soft-fail escalation |
| Portal | Client acknowledgement UI/API | Captures client attestations, generates auxiliary artifacts, enforces acknowledgement SLAs | Step-up auth for attestation; portal revokes URLs on SLA breach |
| Reference Manager | Deliverable templates & metadata | Supplies deliverable catalog, default signature policies, localization assets | Catalog changes go through RM publish pipeline; signer consumes bundle digests |

______________________________________________________________________

## 10) References

- Signing & delivery diagram — `docs/src/services/digital-signer/diagrams/signing-delivery-v1.mmd`.
- TSA/OCSP outage runbook — `ops/runbooks/signer/tsa_ocsp_outage.md`.
- FIPS attestation guard — `packages/udocket_core/security/fips_guard.py`.
- Signature policy resolver — `apps/platform/operations/signer_policy.py`.
- Guardian integration — `apps/platform/operations/guardian_signer_bridge.py`.
- Key rotation artifacts — `ops/security/key_rotation/`.
- Release checklist — `ops/releases/signing_release_checklist.md`.
