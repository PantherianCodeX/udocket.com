---
title: uDocket — Platform Runtime Specification
subtitle: Environments, Kubernetes Guardrails, and Service Catalog
author:
  - Platform Architecture Working Group
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Engineering
  - Site Reliability Engineering
approvers:
  - Architecture Steering Committee
  - Security Review Board
reviewers:
  - Operations Engineering
  - Security Engineering
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
      figure.full-width-diagram img {
        width: 100%;
        height: auto;
        display: block;
      }
    </style>
  - <header class="page-header">uDocket — Platform Runtime Specification <br>
    Environments, Kubernetes Guardrails, and Service Catalog</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-29 · Page
    <span class="page-number"></span> of <span class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Platform Architecture Working Group |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Engineering; Site Reliability Engineering |
| Reviewers | Operations Engineering; Security Engineering |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Captures the shared runtime footprint for all platform services: Kubernetes environments, service mesh guardrails, ingress/egress policy, TLS posture, pod security, and the authoritative service catalog used for capacity planning. The detailed mechanics that individual services implement remain within their dedicated specifications.
- **Structure:** Sections follow the standard 0–10 template. Responsibilities (§2) summarise environment guardrails; §3 documents binding deployment policies and reference manifests; §4 inventories first-party services. Operations, observability, and dependencies surface the runbooks and systems that keep the runtime compliant.
- **Maintenance:** Run `python -m doc_tools.manage_docs --lint docs/platform/runtime.md docs/overview/tdd.md docs/tdd_modularization.md` plus `make docs.check.runbooks` before landing infra changes. Update diagrams via `uv run --project packages/docs_tooling python -m doc_tools.render_mermaid` whenever topology shifts.
- **Change protocol:** Alterations to TLS policy, pod security baselines, mesh egress allowlists, or the service catalog require Architecture + Security review. Any change that widens residency exposure must also update LPE contexts and App.O waiver entries.
- **References:** TDD §3 (summary), Settings Registry (`security.tls.*`, `network.egress.allowed_hosts`), Worker Cluster spec (§2), LPE spec (§2.6), Reference Manager spec (§2.1), Ops runbooks `RB-TLS-LEGACY`, `RB-RES-BLOCK`, `RB-K8S-FENCE`.
- **Contacts:** Platform Engineering (cluster operations), Site Reliability Engineering (mesh & observability), Security Engineering (TLS/FIPS posture), `#platform-runtime` Slack, on-call alias `platform-runtime@`.

______________________________________________________________________

## 1) Purpose

**Purpose:** Define the shared runtime architecture and guardrails that all platform services rely on (environments, mesh policy, TLS posture, pod security) and publish the authoritative service catalog. **|**
**Contract:** Environments must conform to the policies in this document; deviations require documented waivers and automated enforcement. Service owners consume this catalog for capacity planning and dependency analysis. **|**
**State:** Kubernetes manifests, mesh policies, Settings bundles, service inventory metadata, and rendered diagrams (`overview/tdd/diagrams/*.mmd`). **|**
**Failures & handling:** Drift detection and runtime probes fail closed—traffic halts rather than violating residency/TLS policy; recovery follows the runbooks referenced in §8. **|**
**Observability:** Dashboards “Platform Runtime” (TLS, mesh egress), “Service Catalog Adoption”, “Residency & Endpoint Posture”, and “Kubernetes Guardrails” plus synthetic probes (`scripts/security/check_tls_ciphers.py`, `scripts/residency/scan_endpoints.py`). **|**
**Breadcrumbs:** Terraform/Helm sources (`infra/kubernetes/`), mesh policies (`infra/service-mesh/`), Settings bundles (`config/settings/*.json`), diagrams `overview/tdd/diagrams/*.mmd`, tests `tests/infra/test_mesh_policies.py`. **|**
**References:** TDD §3 summary, Settings spec §2.4, LPE spec §2.6, Worker Cluster spec §2.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Enumerate the shared runtime duties owned by Platform Engineering and SRE. **|**
**Contract:** Guardrails defined here are mandatory; any relaxation requires documented waivers and automated enforcement updates. **|**
**State:** Kubernetes manifests, mesh policies, Settings bundles, service inventory metadata, and automation evidence. **|**
**Failures & handling:** Guardrail drift pages on-call and triggers the runbooks in §8. **|**
**Observability:** Dashboards “Platform Runtime”, “Service Catalog Adoption”, residency/TLS scanners, and Flux health checks verify duties remain satisfied. **|**
**Breadcrumbs:** Mesh renderers (`infra/service-mesh/`), Flux/Helm configs, residency scanners, Settings bundles, service catalog metadata. **|**
**References:** TDD §3 summary, Settings spec §2.4, LPE spec §2.6, Reference Manager spec §2.1.

- Maintain environment topology (namespaces, deployments, mesh identity) and ensure pod security, TLS posture, and residency guardrails stay aligned with policy.
- Publish and maintain the first-party service catalog with scaling guidance and observability anchors for SRE, FinOps, and onboarding.
- Coordinate Settings bundles and automation (mesh policy renderers, TLS scanners, residency scanners) so runtime enforcement and documentation never drift.
- Provide runbooks and automated checks for key guardrails: TLS/FIPS compliance, egress allowlists, pod security baseline, image provenance, and region failover.

______________________________________________________________________

## 3) API Contract (binding)

**Purpose:** Capture the shared runtime “interfaces” that other services consume—cluster topology, mesh/TLS requirements, and residency-aware egress controls. **|**
**Contract:** All services must deploy behind these guardrails; Settings and automation enforce compliance before traffic flows. **|**
**State:** Manifest repositories, mesh policies, Settings bundles, and residency catalogs render the contract. **|**
**Failures & handling:** Drift detection fails closed and routes to §5 failure modes. **|**
**Observability:** TLS/residency scanners, mesh policy dashboards, and Flux status feeds provide contract health. **|**
**Breadcrumbs:** Mesh renderers, `infra/kubernetes/`, Settings bundles, residency scanners. **|**
**References:** TDD §3 summary, Settings spec §2.4, LPE spec §2.6.

### 3.1 External Interfaces (binding)

- Kubernetes namespaces per environment (`dev`, `staging`, `prod`, `audit`) host deployments for `web`, `channels`, `workers`, `guardian`, `signer`, `llm-registry`, `reference`, `notifications`, `settings`, ingress controllers, Redis broker/cache, and object-storage sidecars.
- Service mesh (SPIFFE/SPIRE) issues workload identities; certificates rotate with TTL ≤ 24 h and SLO of 99.9 % renewals within five minutes of expiry. Certificates that overrun `security.tls.cert_ttl_minutes + 5` minutes trigger deny-by-default behaviour and page on-call; soft warnings fire 30 minutes before expiry.
- Mutating RPCs require both mTLS and HMAC headers. The mesh validates SANs against `spiffe://uDocket/<service>` (or an allowlisted CN) while the receiving service reconstructs the shared-secret signature. Requests missing either guardrail return `401 AUTH_ERROR` and increment `auth_layer_violation_total`.
- Network policy: ingress terminates TLS, egress defaults to deny except for kube-dns and the mesh egress gateway. The gateway applies allowlists rendered from `network.egress.allowed_hosts`; nightly drift detection resolves each host and compares resolved SANs against the catalog produced by Reference Manager.
- Platform services use managed secrets (Vault or Azure Key Vault). Nodes run chrony/NTP with ±100 ms drift to satisfy TSA requirements. Redis provides broker/cache layers; Postgres (regional HA) backs relational state. Object storage buckets (Azure Blob or S3-compatible) enable versioning, SSE-KMS, and immutable retention for audit sinks.
- Residency isolation: storage buckets, queues, and replicas live within the regions declared in `regions.allowlist.storage`/`regions.allowlist.compute`. Replication outside allowlists requires dual-approved waivers; manifests record the storage topology and key vault backing each cohort.
- Database encryption at rest leverages cloud TDE. Customer-managed keys (`security.db.cmk_id`) route through Key Vault, emit `DB_TDE_ROTATION` artifacts, and trigger automated smoke tests prior to replica propagation.
- Container runtime: production runs on AKS with Flux CD applying Helm releases; PodSecurity admission enforces the restricted baseline (no privileged pods, `readOnlyRootFilesystem` where feasible), and cosign attestations gate image promotion. Local development uses `make stack.up` (the target wraps the dev compose overlay) to mirror service topology and health checks while sharing the `.env` schema.
- Identity provider: Keycloak ships in the stack for local parity, while production instances run behind the platform reverse proxy. TLS terminates at that proxy; Keycloak listens on its internal port (8085 in the prod overlay), and external hosts must forward HTTPS traffic to the container without bypassing the proxy guardrails.
- Multi-region posture: each environment operates within a primary/secondary region pair. Database replicas, blob replication, and queue failover respect organization allowlists. Disaster recovery runbooks document region cut-over and data rehydration using only approved regions (§8).

<a id="platform-runtime-conditional-download"></a>

#### 3.1.1 Artifact download conditional requests (binding)

**Purpose:** Ensure artifact downloads honour caching and integrity requirements while protecting evidence. **|**
**Contract:** Clients send `If-None-Match`/`Range` headers and respect `ETag` responses; servers enforce signed URLs and residency before streaming content. **|**
**State:** Artifact metadata (`artifact.etag`, `artifact.sha256`) and staging buckets back conditional requests; audit logs capture download attempts with headers. **|**
**Failures & handling:** Stale or mismatched `ETag` values return `412 PRECONDITION_FAILED`; unauthorized downloads respond with `403` and log `DOWNLOAD_TOKEN_DENIED`. **|**
**Observability:** Metrics `artifact_download_total{cache_state}`, `artifact_download_bandwidth_bytes`, and audit JSONL monitor usage. **|**
**Breadcrumbs:** Download handler `apps/platform/artifacts/views.py::download`, tests `tests/platform/artifacts/test_download.py`. **|**
**References:** Settings keys `artifact.download.*`, Ops runbook `RB-ETAG`.

```bash
curl -I -H "Authorization: Bearer $TOKEN" \
  https://platform.local/api/v1/artifacts/$A/download

curl -L -H "Authorization: Bearer $TOKEN" \
  -H "If-None-Match: \"$ETAG\"" \
  -H "Range: bytes=0-1048575" \
  https://platform.local/api/v1/artifacts/$A/download
```

<a id="platform-runtime-cors-preflight"></a>

#### 3.1.2 CORS preflight (binding)

**Purpose:** Document the preflight flow portal clients use when calling authenticated APIs behind the platform ingress. **|**
**Contract:** Preflight requests advertise required headers (including HMAC and idempotency headers); ingress responds with allowlists derived from Settings. **|**
**State:** CORS policy templates render from `settings.cors.*` keys; responses include `Access-Control-Allow-*` headers recorded in access logs. **|**
**Failures & handling:** Requests missing required headers (`Authorization`, signature fields) receive `403`; misconfigured origins trigger alerts in the CORS dashboard. **|**
**Observability:** Metrics `cors_preflight_total`, `cors_preflight_denied_total`, and structured logs track origin/header mismatches. **|**
**Breadcrumbs:** Ingress templates `infra/kubernetes/ingress/cors.tpl`, tests `tests/platform/web/test_cors.py`. **|**
**References:** Settings spec §6 (CORS), Portal spec §4.

```bash
curl -i -X OPTIONS \
  -H "Origin: https://portal.local" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization, Idempotency-Key, X-Request-Signature, X-Signature-Key-Id, X-Timestamp, If-Match" \
  https://platform.local/api/v1/artifacts/$A/download
```

#### 3.1.3 API error schema (binding)

**Purpose:** Keep HTTP error envelopes aligned with the shared schema so SDKs and dashboards remain consistent. **|**
**Contract:** Responses conform to `spec/schemas/api_error.schema.json`; services emit one of the enumerated `ApiError.code` values. **|**
**State:** Schema lives in `spec/schemas/api_error.schema.json`; generated clients (Python/TypeScript) consume it; Spectral rules lint OpenAPI bundles. **|**
**Failures & handling:** Divergent error codes fail the docs lint and Spectral checks; releases block until fixed. **|**
**Observability:** Metrics `api_error_total{code}` and audit events record frequency; dashboards alert on unknown codes. **|**
**Breadcrumbs:** Schema `spec/schemas/api_error.schema.json`, lint rules `ops/openapi/rules/apierror-enum.yaml`, tests `tests/platform/api/test_api_error_schema.py`. Canonical code definitions live in §3.3.

#### 3.1.4 Rate-limit response (normative)

```http
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

**Purpose:** Provide an authoritative example for SDKs and monitoring. **|**
**Contract:** Services must emit `Retry-After`, rate-limit headers, and the structured body when throttling requests. **|**
**Observability:** Metrics `api_rate_limit_header_miss_total` and synthetic checks ensure headers remain present; SDK regressions trigger CI failures. **|**
**References:** Settings keys `api.rate_limits.*`, Portal/Web App §2.5.

#### 3.1.5 Deprecation response (normative)

```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Request-ID: 7d1f1dba-1d6f-4f6a-a7ef-2d2f1c2e9bd3
Deprecation: @1780272000; sunset="Mon, 01 Jun 2026 00:00:00 GMT"
Sunset: Mon, 01 Jun 2026 00:00:00 GMT
Link: </api/v1/migrations/2026-06-case-export>; rel="deprecation"; type="text/html"
X-uDocket-API-Version: 2025-01

{ "id": "...", "status": "deprecated", "sunset_at": "2026-06-01T00:00:00Z" }
```

**Purpose:** Demonstrate the RFC 8594/RFC 9333 headers clients must respect when an endpoint approaches end-of-life. **|**
**Contract:** Deprecations require paired `Deprecation`, `Sunset`, and `Link` headers plus a machine-readable payload. **|**
**Observability:** Metric `api_sunset_header_missing_total` and Spectral rule `sunset-header` enforce compliance. **|**
**References:** ADR-0002, Portal spec §2.5 (UI cues).

#### 3.1.6 Required response headers (binding)

| Category | Header(s) | Enforcement & reference | Notes |
|---|---|---|---|
| Exposed response headers | `X-Request-ID`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`, `ETag`, `Deprecation`, `Sunset` | `config/settings.py::CORS_EXPOSE_HEADERS`; validated by `scripts/security/verify_cors_headers.py` | Aligns with §10.5 expectations; deviations require Security approval. |
| Allowed preflight headers | `Authorization`, `Content-Type`, `Idempotency-Key`, `X-Request-Signature`, `X-Signature-Key-Id`, `X-Timestamp`, `If-Match`, `If-None-Match`, `If-Range`, `X-Style-Nonce`, `X-Script-Nonce` | Settings bundle `security.cors.allowed_headers`; test `scripts/security/verify_cors_headers.py` | Nonce headers support CSP requirements (§11.5 Web App). |
| Security baseline | `Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` | Middleware `apps/platform/ui/security/csp.py`; tests `tests/e2e/test_security_headers.py` | CSP enforces per-response script/style nonces. |
| Download guard contract | `If-Match`, `If-None-Match`, `Range`, `If-Range` | Download handler `apps/platform/portal/downloads.py::enforce_if_match` | Clients must echo `If-Match` ETag; mismatches return `412`. |
| Rate-limit headers | `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` | Middleware `apps/platform/api/middleware/rate_limiting.py`; monitored via `api_rate_limit_header_miss_total` | Contract referenced in §3.1.4. |

#### 3.1.7 REST and WebSocket conventions (binding)

**Purpose:** Standardize cross-service behaviour for REST resources, pagination, idempotency, and real-time channels. **|**
**Contract:** All platform APIs expose plural resource paths under `/api/v1/`, enforce optimistic concurrency via `version`, and require `Idempotency-Key` headers for mutating operations. **|**
**State:** OpenAPI components (`ops/openapi/**/*.yaml`), shared middleware (`apps/platform/api/middleware/*.py`), and generated clients consume the same conventions. **|**
**Failures & handling:** Spectral lint (`make lint-openapi`) and contract tests fail when responses deviate; runtime emits `Idempotency-Status` on replays and raises `details.reason="IDEMPOTENCY_SIGNATURE_MISMATCH"` for hash drift. **|**
**Observability:** Metrics `api_request_total{method}`, `idempotency_replay_total`, `api_pagination_page_total`, SSE health monitors `job_sse_schema_mismatch_total`; dashboards “API Gateway” and “Job SSE Health”. **|**
**Breadcrumbs:** Middleware `apps/platform/api/middleware/idempotency.py`, pagination helpers `apps/platform/api/pagination.py`, SSE publisher `apps/platform/events/jobs.py`, tests `tests/platform/api/test_pagination.py`, `tests/platform/events/test_jobs_sse.py`.

- **Base paths:** `/api/v1/<resource>` with plural nouns (`/cases`, `/artifacts`, `/jobs`). RPC-style controls append `:action` (`POST /api/v1/jobs/{id}:cancel`).
- **Idempotency:** Mutations (`POST`, `PUT`, `PATCH`, `DELETE`) require UUIDv7 `Idempotency-Key` headers (TTL ≥ 24 h). Servers replay cached responses on identical payloads and emit `Idempotency-Status: replay`.
- **Optimistic concurrency:** Payloads include `version`; mismatches raise `409 CONFLICT` with `details.reason="REVISION_CONFLICT"`.
- **Pagination:** Envelope `{items, page, page_size, total, next_page}`; sorting uses `?sort=field:asc`. Invalid fields or masked columns return `400`.
- **Filtering:** Query params map to whitelisted fields; masked columns remain non-filterable.
- **Error envelope:** Conforms to `spec/schemas/api_error.schema.json`; clients rely on deterministic `code` values.

Example error payload:

```json
{
  "error": {
    "code": "CASE_NOT_FOUND",
    "message": "Case 22222222-2222-2222-2222-222222222222 is archived",
    "details": [{"field": "case_id", "message": "archived cases are read-only"}]
  },
  "trace_id": "4f4c9f7d09e141d8be6d1f8d0d6d88e4"
}
```

- **Real-time:** Jobs and cases stream progress via SSE; each event carries `{schema_version, emitted_at, id, payload}`. Clients reconnect with `Last-Event-ID` to resume. Channels/WebSockets support collaborative editing with OIDC-authenticated topics scoped by case/job.
- **RBAC & masking:** API serializers only read from secure views (`*_secure`); the gateway rejects spoofed headers (`X-Org-ID`, `X-Active-Roles`).
- **Examples:** `?sort=created_at:desc,type:asc&page=2&page_size=50`, `?case_id=<uuid>&type=SUMMARY_MD`.

#### 3.1.8 Artifact endpoints (binding)

**Purpose:** Document the canonical artifact CRUD flows exposed by the platform API. **|**
**Contract:** Artifact endpoints enforce RLS, optimistic concurrency, and Guardian gating while delegating job orchestration to worker services. **|**
**State:** Controller `apps/platform/artifacts/views.py`, serializers `apps/platform/artifacts/serializers.py`, OpenAPI components `ops/openapi/components/artifacts.yaml`. **|**
**Failures & handling:** Integrity failures raise `INTEGRITY_ERROR`; Guardian blocks raise `POLICY_BLOCK`; SSE `artifact.status` broadcasts keep UI in sync. **|**
**Observability:** Metrics `artifact_request_total{action}`, `artifact_download_total{cache_state}`, audit events `ARTIFACT_CREATED`, `ARTIFACT_STATUS_CHANGED`. **|**
**Breadcrumbs:** Tests `tests/platform/artifacts/test_artifact_api.py`, download guard `apps/platform/portal/downloads.py`, manifest helpers `packages/core/artifacts/service.py`.

- `GET /api/v1/artifacts?case_id=&type=&class=&status=&archived=&page=&page_size=` — lists artifacts with RLS; `scope=org` query leverages `active_org_id`.
- `POST /api/v1/cases/{case_id}/artifacts` — creates artifacts from uploads or generated content; derived artifacts start in `status='PROCESSING'` until workers complete content writes.
- `GET /api/v1/artifacts/{artifact_id}` — retrieves metadata/manifests; response filtered via masking.
- `GET /api/v1/artifacts/{artifact_id}/download` — enforces conditional requests (If-Match/If-None-Match), signed URLs, and Guardian checks (`status='APPROVED'` for CDs, `status='RELEASED'` for DLs).

- Mutations emit audit events, append to `ops_<agent>.jsonl`, and trigger Guardian or Signer workflows as appropriate.

### 3.2 Internal Interfaces (binding)

#### 3.2.1 Mesh egress allowlist (illustrative)

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata: { name: mesh-egress-allowlist, namespace: platform }
spec:
  action: ALLOW
  rules:
    - to:
        - operation:
            hosts:
              - "na-us-1.api.cognitive.microsoft.com"
              - "eu-west-2.api.cognitive.microsoft.com"
              - "na-us-1.ocsp.msocsp.com"
              - "tsa.partner.example.com"
    - to:
        - operation:
            hosts: ["signing-root.example.com"]
```

Rendered host lists come from the Reference Manager residency catalog and the Settings bundle (`network.egress.allowed_hosts`). Wildcards are rejected; the renderer produces exact FQDNs for each approved endpoint and writes the corresponding `ServiceEntry` resources for traffic mediation.

#### 3.2.2 Baseline NetworkPolicy

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
    # External destinations are mediated by the mesh AuthorizationPolicy allowlist.
```

#### 3.2.3 Pod security baseline (binding)

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: platform
  labels:
    pod-security.kubernetes.io/enforce: "restricted"
    pod-security.kubernetes.io/enforce-version: "latest"
```

All namespaces must declare the restricted baseline; violations are blocked by admission controllers and surfaced via `pod_security_violation_total`.

### 3.3 API Error Codes (binding)

**Purpose:** Keep API consumers, SDKs, and monitoring dashboards aligned on the standardized `ApiError.code` values. **|**
**Contract:** All REST and GraphQL surfaces emit one of the enumerated codes below; additions require schema (`spec/schemas/api_error.schema.json`) and Spectral rule (`ops/openapi/rules/apierror-enum.yaml`) updates before deployment. **|**
**State:** Platform Runtime owns the canonical code catalog; generated clients consume the same enumeration and raise on unknown values. **|**
**Failures & handling:** Emitting an unknown code fails Spectral lint, triggers `api_error_unknown_total`, and blocks rollout until the catalog updates. **|**
**Observability:** Metrics `api_error_total{code}`, synthetic probes, and alert rules `api_error_unknown_total`/`api_error_rate_spike_total` track drifts. **|**
**Breadcrumbs:** Schema `spec/schemas/api_error.schema.json`, middleware `apps/platform/api/errors.py`, tests `tests/platform/api/test_api_error_schema.py`, dashboards “API Gateway – Errors”. **|**
**References:** Settings spec §3.4, Guardian spec §2.2, Communications spec §3.3, Ops runbooks `RB-API-GATEWAY-ERROR`.
> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#platform-runtime)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `AUTH_CLOCK_SKEW` | X-Timestamp fell outside the permitted ±120 second window. | Synchronize system clocks (NTP/Chrony) and retry with an accurate timestamp. |
| `AUTH_ERROR` | Caller failed authentication or presented an expired token. | Re-authenticate, ensure the correct audience, and retry with a fresh credential. |
| `AUTH_SIGNATURE_INVALID` | HMAC signature mismatch or revoked key identifier. | Regenerate the canonical string, rotate keys if necessary, and retry with a valid signature. |
| `CONFLICT` | Optimistic concurrency or idempotency conflict detected. | Fetch the latest state, update the payload or Idempotency-Key, and retry once. |
| `INTEGRITY_ERROR` | Hash or ETag validation failed for the submitted content. | Recompute digests, re-upload content, and avoid blind retries without correcting the payload. |
| `NOT_FOUND` | Resource missing, masked by RLS, or already archived. | Treat as terminal; refresh indices or scope before retrying with a new identifier. |
| `POLICY_BLOCK` | Guardian, residency, or settings policy prevented the action. | Surface details.reason, remediate policy or obtain an approved waiver before retrying. |
| `PROVIDER_DEGRADED` | Downstream dependency unavailable or circuit breaker open. | Implement retry with jitter respecting Retry-After; surface degraded status to operators. |
| `QUARANTINED` | Artifact quarantined for manual review or remediation. | Hold follow-on actions until Guardian releases the artifact; do not retry automatically. |
| `RATE_LIMIT` | Rate, quota, or budget exceeded for the caller. | Honor Retry-After, apply exponential backoff, and present throttling feedback to operators. |
| `VALIDATION_ERROR` | Request payload failed schema or semantic validation. | Inspect details[], correct the offending fields, and resubmit the request. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `AUTH_CLOCK_SKEW` | 401 | No | api_error_total |
| `AUTH_ERROR` | 401 | Yes | api_error_total |
| `AUTH_SIGNATURE_INVALID` | 401 | Yes | api_error_total |
| `CONFLICT` | 409 | No | api_error_total |
| `INTEGRITY_ERROR` | 412 | Yes | api_error_total |
| `NOT_FOUND` | 404 | No | api_error_total |
| `POLICY_BLOCK` | 403 | Yes | api_error_total<br>api_error_unknown_total |
| `PROVIDER_DEGRADED` | 503 | Yes | api_error_total<br>api_error_rate_spike_total |
| `QUARANTINED` | 423 | Yes | api_error_total |
| `RATE_LIMIT` | 429 | No | api_error_total |
| `VALIDATION_ERROR` | 400 | No | api_error_total |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

### 3.4 TLS posture (binding)

- TLS 1.3 is the platform default (`security.tls.min_version=TLSv1.3`). TLS 1.2 appears only when `security.tls.legacy_exceptions[]` entries specify endpoint, justification, and expiry ≤ 30 days. Settings activation rejects longer windows and alerts seven days before expiry to force review.
- FIPS mode (`security.tls.fips_mode=true`) restricts cipher suites to AES-GCM (`TLS_AES_128_GCM_SHA256`, `TLS_AES_256_GCM_SHA384`). Performance mode (`security.tls.performance_mode=true`) may enable `TLS_CHACHA20_POLY1305_SHA256` but must record the exception in release checklists. Synthetic handshake job `scripts/security/check_tls_ciphers.py` runs per deploy and nightly to enforce the profile.
- OCSP stapling remains enabled on ingress. TLS certificates rotate via mesh/ingress automation; expiration or misconfiguration triggers `tls_cert_expiry_hours` alerts and fails closed.
- Illustrative ingress annotation:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: platform
  annotations:
    nginx.ingress.kubernetes.io/ssl-protocols: "TLSv1.3 TLSv1.2"
    nginx.ingress.kubernetes.io/ssl-ciphers: "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
```

Mesh and ingress templates consume the same Settings bundles so routing surfaces stay consistent across services.

### 3.5 Service-to-service request signing (binding)

**Purpose:** Authenticate privileged inter-service calls that traverse trust boundaries. **|**
**Contract:** All mutating requests between platform services (Guardian, Signer, Settings activation, worker control APIs, etc.) MUST include the HMAC headers defined here; receivers validate the signature, enforce timestamp skew, and pair the request with an `Idempotency-Key` when present. **|**
**State:** Shared secrets reside in managed stores (Key Vault/Vault) and mirror Settings keys under `security.hmac.*`; Settings activation distributes key IDs to clients and services. Canonicalization uses `{method, path, timestamp, body_sha256}` scoped to the requesting service/tenant. **|**
**Failures & handling:** Timestamp drift greater than `security.hmac.max_clock_skew_seconds` returns `401 AUTH_CLOCK_SKEW`; digest mismatches raise `401 AUTH_SIGNATURE_INVALID`; missing headers fail closed. Clients retry after syncing clocks and recomputing the signature; repeated violations escalate via Security runbook `RB-HMAC-ROTATE`. **|**
**Observability:** Metrics `auth_request_signed_total`, `auth_signature_invalid_total`, and `auth_clock_skew_total` feed the “API Gateway – Auth” dashboard; audit events `AUTH_SIGNATURE_INVALID` include the offending key ID for forensics. **|**
**Breadcrumbs:** Signature middleware `apps/platform/api/middleware/hmac_signature.py`, helpers `packages/core/security/hmac.py`, tests `tests/platform/api/test_hmac_signature.py`, Settings schema `packages/core/settings/security.py`.

Required headers for signed requests:

- `X-Signature-Key-Id` — identifies the shared secret (for example, `svc-guardian/current`).
- `X-Timestamp` — RFC3339 timestamp in UTC; services reject absolute skew greater than `security.hmac.max_clock_skew_seconds` (default 120 seconds).
- `X-Request-Signature` — Base64-encoded HMAC over the canonical request string.
- `Idempotency-Key` — required for mutating operations to guarantee replay safety; the value is included in the canonical string when supplied.

Canonical string (pseudocode):

```pseudocode
canonical = [
  request.method.upper(),
  request.path,
  timestamp_iso8601,
  sha256_hex(request.body or "")
].join("\n")
```

Receivers recompute the digest with the secret referenced by `X-Signature-Key-Id`, compare using constant-time equality, and record signature metrics. Replay protection combines the `Idempotency-Key` with a short-lived cache (default TTL 24 hours) so identical requests return cached responses.

#### 3.5.1 Key rotation flows (binding)

**Purpose:** Rotate HMAC credentials without interrupting signed traffic. **|**
**Contract:** Rotations follow a dual-publish → cutover → revoke pattern; evidence lands in `ops/security/key_rotation/` alongside Grafana snapshots. **|**
**State:** Secrets live under `{service}/current` and `{service}/next` in the secret store; Settings activation advertises active key IDs so clients can dual-publish signatures. **|**
**Failures & handling:** Spikes in `auth_signature_invalid_total` or canary failures trigger rollback (restore the previous key) and open a Security incident; compromised keys are denylisted immediately. **|**
**Observability:** Metrics `hmac_key_rotation_total`, `hmac_key_rotation_failure_total`, and synthetic canary job `scripts/security/key_rotation_canary.py`; dashboards show rotation status and failure ratios.

Rotation steps:

1. **Dual publish:** Generate a new secret, store it under `{service}/next`, and update Settings to advertise both `current` and `next` IDs. Canary requests sign with the new key while production continues with the current secret.
2. **Cutover:** After canaries succeed, swap pointers so `{service}/current` references the new secret and create a fresh `{service}/next`. Monitor signature error metrics for anomalies.
3. **Revoke:** Retire the previous secret, prune denylisted IDs, and archive rotation evidence (`key_rotation_report.json`) with Grafana snapshots.
4. **Emergency revoke:** If compromise is suspected, denylist the affected key ID immediately, rotate secrets, and verify error rates return to baseline before closing the incident.

Cadence: API HMAC keys rotate quarterly, Guardian/Signer service keys rotate semi-annually, and customer-supplied keys rotate per contract (≤90 days). Overdue keys page Security Engineering; the platform change calendar tracks upcoming rotations.

______________________________________________________________________

## 4) State Management (binding)

**Purpose:** Maintain the authoritative service inventory and provider metadata that other docs and onboarding workflows consume. **|**
**Contract:** The inventory must stay in sync with service specifications; updates require corresponding changes to owners’ docs and dashboards. **|**
**State:** Service catalog tables, provider notes, FinOps metrics, and residency metadata captured in Reference Manager/LPE bundles. **|**
**Failures & handling:** Drift detection (docs vs catalog) triggers §5 runbooks; catalog automation blocks releases when stale. **|**
**Observability:** “Service Catalog Adoption”, FinOps dashboards, and residency scanners reference this catalog. **|**
**Breadcrumbs:** Catalog source `docs/platform/runtime.md`, settings keys, Reference Manager catalog, LPE bundles. **|**
**References:** Individual service specifications (`../services/*.md`), Appendix Q, App.L benchmarks.

| Service | Runtime | Responsibilities | Scaling & notes | Observability anchors |
| --- | --- | --- | --- | --- |
| Web | Django ASGI (uvicorn + gunicorn) | REST APIs, staff UI, client portal, SSE endpoints, approval workflows | HPA on CPU + request latency; sticky sessions avoided | `web_http_*`, `frontend_latency_seconds`, `audit_event_total` |
| Channels | Django Channels (Redis-backed) | Real-time editors, approvals, QA feedback | Separate deployment with autoscale on WebSocket connections | `channels_active_connections`, `channels_msg_latency_seconds` |
| Workers | Celery (prefork) | Media normalization, agent orchestration, notifications, ingestion, destruction | Queue length auto-scaling; dedicated queues per agent class | `celery_queue_depth`, `job_duration_seconds`, `task_retry_total` |
| Guardian | FastAPI | PASS/WARN/BLOCK/WAIVED judgments, policy evaluation, audit history | Pod HPA on latency; 99.9 % SLO | `guardian_judgment_latency_seconds`, `guardian_cleared_ratio` |
| Digital Signer | FastAPI | PDF/A signing, OCSP/CRL/TSA validation, bundle creation | Scales with signing queues; relies on KMS/TSA connectors | `signer_request_latency_seconds`, `tsa_drift_seconds` |
| LLM Registry | FastAPI | Provider catalog, health probes, token accounting, fallback logic | Low QPS; run ≥ 2 replicas | `llm_provider_health`, `llm_circuit_state` |
| Settings Service | FastAPI | Hierarchical settings APIs, bundle activation, diff previews | Autoscale on QPS; Redis pub/sub for cache invalidation | `settings_activation_total`, `settings_cache_hit_ratio` |
| Localization & Policy Engine | FastAPI + compiler workers | Localization bundles, residency policy contexts, privacy frameworks | Compiler pods scale on activation; lookup API replicated for low latency | `lpe_lookup_latency_seconds`, `lpe_policy_context_version`, `lpe_cache_hit_ratio` |
| Reference Manager | FastAPI + Celery ingest workers | Source connectors, catalog lifecycle, questionnaires/forms administration | Ingest workers autoscale on harvest queues; reviewer backlog monitored | `reference_manager_ingest_duration_seconds`, `reference_manager_pending_reviews`, `reference_catalog_version` |
| Notifications | FastAPI + Celery | Outbox delivery (email/SMS/in-app), receipt tracking | Scales with delivery volume; provider-specific adapters | `delivery_success_ratio`, `delivery_retry_total` |
| Worker cluster | Celery + beat | Agent orchestration, watchdog automation, data hygiene | Queue depth and KEDA triggers govern scale | `celery_queue_depth`, `watchdog_runner_lag_seconds`, `task_retry_total` |
| Storage adapters | Sidecar jobs | Object storage integrity checks, audio normalization, manifest sealing | Run as init/sidecar jobs alongside worker pods | `storage_integrity_scan_total`, `audio_normalize_duration_seconds` |
| Guardian-ready quarantine tooling | FastAPI utilities + batch jobs | Human review portal, quarantine actions, waiver ledger | Scales with review queue load | `guardian_pending_total`, `guardian_quarantine_reason_total` |
| Staff/Client assistants | LangGraph pipelines + SSE bridge | Conversational workflows with retrieval, moderation, Guardian integration | Autoscale on worker pools; concurrency limited per org | `chat_sessions_total{audience}`, `chat_policy_block_total`, `chat_latency_seconds` |
| Speech providers (primary + failover) | External REST APIs | On-demand and batch transcription | Pooled via capability registry; WER/diarization parity enforced | `speech_provider_latency_seconds`, `speech_failover_attempt_total` |
| LLM providers | External REST APIs | Model inference for Analyze/Compose, assistants | Selected via capability registry with fallback chains | `llm_provider_health`, `llm_cost_estimate_total`, `finops_budget_hold_active_total` |
| Digital trust services | External TSA/OCSP | Timestamping, certificate revocation checks | Cached and rate-limited via notifier sidecar | `tsa_latency_seconds`, `ocsp_latency_seconds`, `signer_ocsp_error_total` |
| Notification providers | Email/SMS gateways | Email, SMS, and webhook delivery | Configured per organization; throttled per provider contracts | `notification_provider_latency_seconds`, `notifications_rate_limit_total` |
| Localization & Policy Engine sources | Reference Manager connectors | Localization packs, policy frameworks, residency bundles | Ingest workers autoscale on catalog backlog | `lpe_compiler_duration_seconds`, `reference_manager_pending_reviews` |

- Speech fallback providers must expose REST APIs with parity guarantees (WER/diarisation deltas within policy thresholds) and residency attestations equivalent to Azure Speech Canada regions; workers consume them through the shared `TranscriptionAgent` interface so jobs remain provider-agnostic.
- LLM provider selection honours organization allowlists and fallback chains; the capability registry records evaluation hashes and residency metadata for every switchover.
- Digital trust services (`sign.trust_roots[]`) enforce OCSP/TSA drift ≤ ±5 s and cache responses ≤ 12 h; incidents anchor to Signer runbooks.
- Notification channels mirror org-specific provider choices; webhook adapters mask PII in request/response payloads while retaining receipts.
- Localization & Policy Engine and Reference Manager specifications document compiler workflows, residency bundles, and source catalogs that feed mesh policy renderers.
- Optional analytics sinks export metrics to Grafana/Prometheus; FinOps dashboards consume cost metrics for monthly guardrails.
- Sub-processor directory and residency posture remain tracked in Appendix Q and the LPE/Reference Manager specifications.

______________________________________________________________________

## 5) Failure Modes

**Purpose:** Document the runtime failure scenarios and default remediation steps. **|**
**Contract:** Guardrails fail closed—traffic halts rather than violating policy. Recovery must follow the runbooks listed here. **|**
**State:** TLS certificates, mesh policies, Flux releases, residency catalogs, and DR artifacts. **|**
**Failures & handling:** Enumerated below. **|**
**Observability:** Alerts `tls_cert_expiry_hours`, `platform_flux_sync_failed_total`, `residency_drift_detected_total`, `pod_security_violation_total`. **|**
**Breadcrumbs:** Runbooks `RB-TLS-LEGACY`, `RB-RES-BLOCK`, `RB-K8S-FENCE`, `RB-REGION-CUTOVER`, `RB-FLUX-ROLLBACK`. **|**
**References:** TDD §12, Settings spec §2.4, LPE spec §2.6.

- **TLS drift:** Handshake tests or certificate expirations fail closed; follow `RB-TLS-LEGACY` for remediation, update Settings bundles, and rerun scanners before reopening traffic.
- **Mesh/egress policy drift:** Residency scanner detects hosts outside allowlist; automation blocks traffic via mesh policy while Reference Manager and LPE update catalogs or obtain waivers (see `RB-RES-BLOCK`).
- **Pod security violation:** Admission webhook rejects non-compliant workloads; deployment pipeline fails until pod spec complies with restricted baseline.
- **Region outage:** Follow DR playbooks to promote the secondary region; manifests ensure failover stays inside approved region pairs.
- **Flux/Helm deployment failure:** Changes fail fast with per-environment rollback; alerts `platform_flux_sync_failed_total` and `k8s_deploy_rollout_stuck_total` guide operators to reapply or revert.

______________________________________________________________________

## 6) Observability

**Purpose:** Ensure the runtime guardrails remain visible and actionable. **|**
**Contract:** Dashboards, synthetic probes, and alerts listed here are mandatory; removals require SRE + Security approval. **|**
**State:** Grafana dashboards, Prometheus rules, residency scanner logs, TLS probe reports. **|**
**Failures & handling:** Blind spots logged in §5 incident follow-ups. **|**
**Observability:** Enumerated below. **|**
**Breadcrumbs:** Monitoring configs `infra/monitoring/`, synthetic definitions `synthetics/`, scripts under `scripts/security/` and `scripts/residency/`. **|**
**References:** TDD §12, Settings spec §2.4.

- Dashboards: “Platform Runtime” (TLS/mTLS), “Kubernetes Guardrails”, “Service Catalog Adoption”, “Residency & Endpoint Posture”.
- Metrics: `tls_cert_expiry_hours`, `auth_layer_violation_total`, `pod_security_violation_total`, `mesh_policy_violation_total`, `residency_block_total`, `residency_drift_detected_total`.
- Synthetic probes: `scripts/security/check_tls_ciphers.py`, `scripts/residency/scan_endpoints.py`, `synthetics/platform_runtime_podsecurity.yaml`.
- Logs: mesh ingress/egress logs (masked), Kubernetes audit logs, residency scanner findings (`ops/residency/findings/*.jsonl`).
- Alerts: TLS expiry, mesh policy drift, residency drift, pod security violations, Flux sync failures.

### 6.1 SLOs & Targets (binding)

**Purpose:** Define reliability expectations for the shared runtime footprint. **|**
**Contract:** Kubernetes control plane, Flux convergence, and guardrail enforcement must meet the thresholds below before releases proceed. **|**
**State:** Metrics `platform_control_plane_up`, `platform_flux_sync_seconds`, `pod_security_violation_total`, `mesh_policy_violation_total`, `residency_drift_detected_total`; dashboards “Platform Runtime”, “Kubernetes Guardrails”, “Residency & Endpoint Posture”. **|**
**Failures & handling:** Breaches invoke RB-K8S-FENCE and the residency runbooks before automation resumes. **|**
**Observability:** Grafana SLO dashboards with burn-rate alerts, synthetic `/readyz` checks, and residency scanners provide evidence. **|**
**Breadcrumbs:** Monitoring configs `infra/monitoring/platform-runtime-prometheus-rules.yaml`, synthetic scripts `scripts/security/check_tls_ciphers.py`, `scripts/residency/scan_endpoints.py`. **|**
**References:** TDD §12, Settings spec §7.2, Logging spec §6.

- **Control plane availability:** ≥99.9% monthly uptime for the managed Kubernetes API and ingress endpoints, measured via synthetic `/readyz` probes and `platform_control_plane_up`. Burn-rate alerts (1×/6×) page platform runtime on-call via RB-K8S-FENCE.
- **Flux convergence:** 95th percentile reconciliation latency ≤5 minutes as captured by `platform_flux_sync_seconds`; breaches block releases until drift is resolved and recorded in RB-K8S-FENCE.
- **Guardrail enforcement:** Policy enforcement alerts (`pod_security_violation_total`, `mesh_policy_violation_total`, `residency_drift_detected_total`) must remain at zero sustained; any recurring breach triggers incident review prior to release sign-off.

______________________________________________________________________

## 7) Security & Compliance

**Purpose:** Capture the runtime controls that enforce residency, TLS, pod security, and provenance requirements. **|**
**Contract:** These controls must remain active in all environments; waivers require dual approval and App.O entries. **|**
**State:** Settings bundles (`security.*`), mesh policies, cosign attestations, residency waivers, audit sink records. **|**
**Failures & handling:** Security incidents raise `SEC-*` tickets and follow §5 runbooks. **|**
**Observability:** Security dashboards, residency scanners, TLS probes, admission controller metrics. **|**
**Breadcrumbs:** Settings spec, LPE spec, Reference Manager spec, Security runbooks. **|**
**References:** TDD §3, Appendix Q, App.O waivers.

- FIPS posture enforced by Settings `security.tls.fips_mode`; changes require Security approval and updated attestation.
- Mesh identity and HMAC headers ensure mutual authentication for mutating RPCs.
- Pod security baseline prevents privileged escalation and enforces read-only root file systems where feasible.
- Image provenance uses cosign attestations; unsigned images are rejected by admission webhook `cosign-verify`.
- Residency enforcement integrates with LPE contexts and Guardian; waivers tracked in App.O with expiry and remediation plans.
- Immutable audit sink retains logs, residency findings, TLS waiver records, and service catalog updates for ≥ 365 days.

______________________________________________________________________

## 8) Operational Notes

**Purpose:** Detail day-2 operations, staffing, alerting, and evidence expectations for the runtime platform. **|**
**Contract:** Runbooks, maintenance windows, and automation described here must remain current; missing evidence blocks releases. **|**
**State:** Rosters, freeze calendars, runbooks, automation artifacts under `ops/platform-runtime/`. **|**
**Failures & handling:** Incident triggers map directly to runbooks and drills in this section. **|**
**Observability:** PagerDuty analytics, runbook execution tracker, automation reports. **|**
**Breadcrumbs:** Ops catalog, runbooks `docs/ops/runbooks/*.md`, automation scripts `ops/scripts/platform-runtime/`. **|**
**References:** TDD §12, Ops governance policies, platform-runtime runbooks.

### 8.1 Operational Posture (binding)

**Purpose:** Define staffing expectations and readiness posture. **|**
**Contract:** Platform Engineering and SRE share 24/7 pager coverage (`platform-runtime@`) with 15 minute response; freeze windows follow the calendar noted below. **|**
**State:** Roster `ops/platform-runtime/roster.yaml`, freeze calendar `ops/platform-runtime/freeze_windows.ics`, escalation matrix. **|**
**Failures & handling:** Staffing gaps trigger `platform_oncall_gap_total`; releases pause until coverage restored. **|**
**Observability:** PagerDuty analytics, staffing dashboards. **|**
**Breadcrumbs:** Ops governance policies, runbooks referenced above. **|**
**References:** Ops governance policies, staffing procedures.

### 8.2 Incident Triggers (binding)

**Purpose:** Map monitoring signals to operational playbooks. **|**
**Contract:** Alerts listed below must page on-call and link to the corresponding runbook. **|**
**State:** Prometheus alert rules, PagerDuty services, suppression policies. **|**
**Failures & handling:** False positives reviewed weekly; suppression adjustments logged in the Ops catalog. **|**
**Observability:** Alert dashboards, PagerDuty analytics. **|**
**Breadcrumbs:** Alert definitions in `infra/monitoring/platform-runtime-prometheus-rules.yaml`. **|**
**References:** Ops runbook catalog, alert catalog.

- TLS expiry (`tls_cert_expiry_hours`) → `RB-TLS-LEGACY` (certificate rotation & validation).  
- Residency drift (`residency_drift_detected_total`) → `RB-RES-BLOCK`.  
- Pod security or admission failures (`pod_security_violation_total`) → `RB-K8S-FENCE`.  
- Flux rollout failure (`platform_flux_sync_failed_total`) → `RB-FLUX-ROLLBACK`.  
- Region degradation → `RB-REGION-CUTOVER`.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Keep operational playbooks aligned with alerts and exercised on schedule. **|**
**Contract:** Runbooks must exist, include automation evidence, and be rehearsed per cadence. **|**
**State:** Runbook files and automation outputs under `ops/platform-runtime/<date>/`. **|**
**Failures & handling:** Missing or stale runbooks block releases until updated. **|**
**Observability:** Runbook execution tracker, drill summaries. **|**
**Breadcrumbs:** Ops catalog, automation scripts. **|**
**References:** Ops runbook catalog, drill scheduler documentation.

#### 8.3.1 Runbook Index (informative)

| Signal / Scenario | Runbook | Notes |
| --- | --- | --- |
| TLS expiry | `RB-TLS-LEGACY` | Temporary TLS 1.2 fallback, validation, rollback |
| Residency drift | `RB-RES-BLOCK` | Mesh policy hardening and waiver review |
| Pod security violation | `RB-K8S-FENCE` | Admission webhook remediation |
| Region outage | `RB-REGION-CUTOVER` | DR failover/failback workflow |
| Flux/Helm rollout stuck | `RB-FLUX-ROLLBACK` | Flux sync investigation and rollback |

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarize the critical runbooks responders execute during incidents. **|**
**Contract:** Each runbook must remain up to date and linked from alert definitions. **|**
**State:** Runbook Markdown files, automation scripts, evidence directories. **|**
**Failures & handling:** Missing steps discovered during drills trigger immediate updates and retro documentation. **|**
**Observability:** Runbook execution tracker, drill reports. **|**
**Breadcrumbs:** Runbook catalog entries (`docs/ops/runbooks/*.md`). **|**
**References:** Ops runbook catalog, incident retrospectives.

- `RB-TLS-LEGACY` — enable/disable TLS 1.2 fallback, confirm scanners, capture evidence.  
- `RB-RES-BLOCK` — tighten mesh allowlists, coordinate Reference Manager/LPE updates, review waivers.  
- `RB-K8S-FENCE` — remediate PodSecurity violations or admission webhook outages.  
- `RB-REGION-CUTOVER` — execute disaster-recovery cutover and failback within approved region pairs.  
- `RB-FLUX-ROLLBACK` — handle Flux/Helm deployment failures, ensure service availability.

#### 8.3.3 Drill Cadence & Evidence (informative)

- Quarterly drills rehearse TLS fallback, residency drift remediation, and region cutover; evidence stored in `ops/platform-runtime/drills/<date>/summary.md`.  
- Buildkite “platform-runtime-guardrails” step verifies runbook execution dates and evidence directories; failures page ownership teams.

### 8.4 Migrations & Backfills (informative)

**Purpose:** Track schema/config migrations that affect runtime guardrails. **|**
**Contract:** Migrations require change approval, staging validation, and signed artifacts before promotion. **|**
**State:** Helm/Flux manifests, change tickets, migration scripts. **|**
**Failures & handling:** Failed migrations invoke `RB-FLUX-ROLLBACK`; releases pause until reconciliation completes. **|**
**Observability:** Migration dashboard, Flux change reports. **|**
**Breadcrumbs:** Flux manifests (`infra/kubernetes/`), change tickets, migration scripts. **|**
**References:** Ops change-management policy, Flux runbooks.

- Infrastructure migrations (cluster upgrades, mesh policy schema changes) run through staging dry-runs and produce signed manifests attached to change tickets.

### 8.5 Operational Workflows (informative)

**Purpose:** Capture recurring tasks that maintain runtime hygiene. **|**
**Contract:** Workflows must produce evidence stored under `ops/platform-runtime/<date>/`; missed runs block releases. **|**
**State:** Maintenance checklists, automation scripts, reporting dashboards. **|**
**Failures & handling:** Missed workflows generate backlog tickets and escalate to Ops leadership. **|**
**Observability:** Workflow completion dashboard, automation logs. **|**
**Breadcrumbs:** Workflow documentation, automation scripts, staffing rosters. **|**
**References:** Ops governance policies, workflow checklists.

- Weekly review of residency scanner findings and TLS probe reports.  
- Monthly validation of pod security policies and cosign attestation coverage.  
- Quarterly audit of freeze windows, Flux sync health, and runbook freshness.

## 9) Dependencies

**Purpose:** List upstream/downstream systems required to enforce runtime guardrails. **|**
**Contract:** Dependencies must publish compatible interfaces; runtime automation validates alignment before rollout. **|**
**State:** Settings bundles, residency catalogs, mesh renderers, runbook integrations. **|**
**Failures & handling:** Dependency regressions surface via §5 failure modes and Ops runbooks. **|**
**Observability:** Dashboards track sync status with Settings, LPE, Reference Manager, and Flux. **|**
**Breadcrumbs:** Dependency specifications referenced in the table. **|**
**References:** Settings, LPE, Reference Manager, Worker Cluster, Communications specs.

| Dependency | Role | Notes |
| --- | --- | --- |
| Settings Registry | Source of TLS, mesh, residency, and pod security configuration (`security.*`, `network.egress.*`, `regions.allowlist.*`) | Activation pipeline validates guardrails before publishing |
| Localization & Policy Engine | Compiles residency contexts and waiver metadata consumed by mesh policy renderers | Residency scanners and Guardian rely on compiled bundles |
| Reference Manager | Provides provider endpoint catalog, residency attestations, waiver ledger | Renderers consume catalog to build mesh allowlists |
| Worker Cluster | Executes residency scanners, TLS probes, and DR automation via periodic tasks | Exposes metrics/logs consumed by dashboards |
| Guardian & Signer | Depend on TLS/mTLS posture and residency guarantees for artifact promotion | Manifest fields include TLS/residency hashes |
| Notifications | Emits alerts when guardrails breach (TLS expiry, residency drift) | Integrates with Ops runbooks |

______________________________________________________________________

## 10) References

- TDD §3 Platform architecture summary.
- Settings Registry specification — `../platform/settings.md §2.4`, `§3`.
- Worker Cluster specification — `../automation/worker-cluster.md §2`.
- Localization & Policy Engine specification — `../automation/lp-engine.md §2.6`.
- Reference Manager specification — `../data/ref-manager.md §2.1`.
- Ops runbook catalog — `../ops/runbooks.md`.
- JSON Schema — <https://json-schema.org/>
- RFC 8594 — Deprecation HTTP Header: <https://www.rfc-editor.org/rfc/rfc8594>
