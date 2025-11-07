---
title: uDocket — Localization & Policy Engine Technical Design
subtitle: Localization, Residency, and Policy Enforcement Specification
author:
  - uDocket Platform Architecture Team
  - Localization & Policy Program Leads
version: 0.1-draft
status: implementable
classification: Confidential
last_updated: 2025-10-29
updated_by: Documentation Team
owners:
  - Platform Architecture
  - Security Engineering
  - Localization & Policy Program
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
  - <header class="page-header">uDocket — Localization & Policy Engine Technical
    Design <br> Localization, Residency, and Policy Enforcement 
    Specification</header>
  - <footer class="page-footer">Confidential · Last updated 2025-10-23 · Page 
    <span class="page-number"></span> of <span 
    class="page-count"></span></footer>
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | uDocket Platform Architecture Team; Localization & Policy Program Leads |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-29 |
| Updated by | Documentation Team |
| Owners | Platform Architecture; Security Engineering; Localization & Policy Program |
| Reviewers | QA Engineering Lead; SRE Manager |
| Approvers | Architecture Steering Committee; Security Review Board |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

**Status:** KEP: Provisional → Implementable → Implemented

______________________________________________________________________

## Reading Guide

- **Scope:** Service charter, compiler/runtime internals, API contracts, observability, OPA bundle management, rollout controls, and runbooks for LPE.
- **Structure:** Sections follow the standard 0–10 outline; §8 contains the operational posture, alert triggers, runbook summaries, migrations, and workflows that previously lived in Appendix R.
- **Cross-references:** Use `§<number>` for this document, `TDD §<number>` for the platform TDD, and `App.<letter>` when pointing at shared appendices (for example TDD App.J for FIPS tracing).
- **Maintenance:** Run `python -m doc_tools.manage_docs --lint` before submitting edits. Localization and policy schema snippets must match `spec/schemas/*`; CI enforces localization completeness, policy coverage, and decision-log schema validation.
- **Change protocol:** PRs touching localization packs, residency policies, OPA bundles, or PolicyContext generation must cite this spec and ADR-0003 in the review summary. Architecture + Security approvals are required when SDKs, Settings bundles, or compiler behaviour change.

______________________________________________________________________

## 1) Purpose

**Purpose:** Establish LPE as the single enforcement surface for localization, residency, privacy, and policy bundles consumed throughout uDocket. **|**
**Contract:** LPE produces deterministic `PolicyContext`, localization packs, and OPA bundles for every `(org_id, case_id?, locale, privacy_flags)` tuple; downstream services must record digests and respect residency/privacy directives. **|**
**State:** Compiled artifacts persist in Postgres `compiled_*` schemas and signed bundles in object storage; Settings snapshots embed digests and version IDs. **|**
**Failures & handling:** Compiler regressions, residency drift, or OPA discovery failures freeze bundle promotion until runbooks in §8.3 restore safe posture. **|**
**Observability:** “LPE – Enforcement & Residency”, “LPE Compiler”, and “Localization QA” dashboards track latency, adoption, and localization completeness; OPA discovery emits decision logs with guaranteed schema. **|**
**Breadcrumbs:** Service entry `packages/core/lpe/service.py`, compiler pipeline `packages/core/lpe/compiler.py`, tests `tests/specs/test_policy_context_contract.py`, observability config `infra/observability/dashboards/lpe.json`. **|**
**References:** §2 Responsibilities, §4 State management, §8 Operational notes, ADR-0003.

- Runtime availability target: 99.9 % with a 43 minute monthly error budget; compiler jobs P95 ≤ 6 minutes. Burn-rate breaches freeze new bundle activations and OPA discovery pushes until stabilization.
- Policy artifacts remain hash-stable for identical inputs; `/reference/*` shims stay read-only with RFC 8594 `Sunset`/`Deprecation` headers until §8.4 migration completes.
- OPA bundles are dual-signed (Ed25519 + ECDSA) from HSM-backed automation; discovery latencies and signature errors are critical signals feeding §5 and §8.2 triggers.
- LPE is the single enforcement source for locale packs, residency allowlists, privacy frameworks, masking profiles, disclaimer copy, and logging directives consumed by Guardian, Portal, Settings, Compose/Analyze, and workers.
- Deterministic `PolicyContext` payloads cover every `(org_id, case_id?, locale, privacy_flags)` tuple; Settings snapshots embed digests so downstream services can prove which context they used.
- Compiler outputs and localization packs inherit Reference Manager licensing metadata; deployments fail closed if unsigned bundles or stale manifests reach the pipeline.
- Service lifecycle mirrors ADR-0003 transitions: rename from the legacy Reference Engine completes only after compiler parity, production cutover verification, and documentation updates referenced in §8.4.
- Synthetic monitors invoke `GET /api/v1/lpe/policy_context` for HIPAA/PHIPA/PIPA cases after each deploy to validate Guardian and Portal behaviour end-to-end.
- Synthetic tenant “EU-REFERENCE” exercises EU-only paths quarterly to confirm residency posture across Azure endpoints, storage buckets, vector shards, and TSA integrations.

______________________________________________________________________

## 2) Responsibilities

**Purpose:** Enumerate functional responsibilities and non-goals. **|**
**Contract:** Spell out mandatory behaviours, idempotency, regulatory duties. **|**
**State:** Describe ownership of state transitions or data stewardship. **|**
**Failures & handling:** Identify responsibility gaps and escalation paths. **|**
**Observability:** Checks proving each responsibility works. **|**
**Breadcrumbs:** Implementation/tests supporting each responsibility. **|**
**References:** Service/TDD sections that expand on responsibilities.

### 2.1 Policy & residency enforcement (binding)

**Purpose:** Capture the enforcement scope LPE owns so downstream services understand the guarantees. **|**
**Contract:** LPE defines privacy frameworks (HIPAA/PHIPA/PIPA/GDPR), residency allowlists, masking profiles, disclaimer copy, and logging directives; org-level Settings may tighten requirements but cannot undercut jurisdictional baselines compiled from Reference Manager (RM). **|**
**State:** `compiled_policy_context` rows store `{policy_context_version, frameworks_enabled[], hipaa_required, residency_regions{compute[], storage[], vector[]}, storage_requirements{preferred_classes[], hipaa_capable_providers[]}, retention_days, portal_rules{disclaimer_key, banner_key}, masking_profile, logging_rules, digest_sha256}`. **|**
**Failures & handling:** Digest drift, unsafe residency overrides, or waived frameworks without approvals trigger §5.1 and §5.3 scenarios; automation blocks Settings activation until remediated. **|**
**Observability:** Metrics `lpe_policy_block_total`, `lpe_privacy_framework_enabled_total`, OPA decision logs, and adoption lag dashboards prove enforcement health. **|**
**Breadcrumbs:** `packages/core/lpe/policy_context.py`, `packages/core/lpe/residency.py`, tests `tests/specs/test_residency_policy.py`, scripts `ops/scripts/lpe/check_waivers.py`.

- LPE compiles deterministic `PolicyContext` payloads capturing frameworks, residency, masking, disclaimers, logging directives, and digests. Consumers must persist the digests in audit logs and manifests.
- Guardian and workers honor `POLICY_BLOCK`, `HIPAA_REQUIRED`, `RESIDENCY_POLICY_BLOCK`, and `WAIVER_REQUIRED` codes emitted by OPA/PolicyContext; Portal and Compose surface localized disclaimers using the same payload.
- Database masking integrates via `masking_profile` fields; `db.set_rls_mask_profile(ctx.masking_profile)` applies row-level security mask rules compiled during Settings activation (§4.3).
- Residency posture includes deployment classes (`shared`, `dedicated`, `perimeter`) so Guardian, Portal, and automation respect residency, logging, and support boundaries.

### 2.2 Localization domains (normative)

**Purpose:** Enumerate localization responsibilities and editorial integrations. **|**
**Contract:** Locale packs include ICU tags, fallback chains, attribution metadata, messageformat payloads, and accessibility copy; localization QA evidence must accompany new locales before activation (see §8.5.1). **|**
**State:** Localization packs persist in `compiled_l10n_locale`, with fallback evaluation `requested → base_language → platform_default (default en-CA unless overridden in Settings)`. **|**
**Failures & handling:** Missing locales or pseudolocale regressions raise `lpe_localization_gap_total`, invoking §5.2 and §8.3.6 RB-LPE-LOCALE-GAP. **|**
**Observability:** “Localization QA” dashboard, pseudolocale CI, Playwright RTL snapshots, and ICU boundary tests monitor coverage. **|**
**Breadcrumbs:** `packages/core/lpe/localization.py`, tests `tests/i18n/test_localization_contract.py`, localization tooling `scripts/i18n/pseudolocale.sh`.

- **Managed domains**

| Domain | Examples / keys | Primary consumers |
| --- | --- | --- |
| Localization packs | Approval banners, invalidation copy, intake flows, accessibility copy, formatting helpers (date/time, number, currency, measurement units), legal disclaimers keyed by locale | Staff UI, client portal, notifications, Compose/Analyze agents |
| Residency policies | Compute/storage/vector region allowlists, waiver metadata, deployment type annotations | Guardian, workers, storage adapters, Search/Vector |
| Privacy frameworks | HIPAA/PHIPA/PIPA/GDPR toggles, retention defaults, DSAR requirements, PHI posture | Guardian, workers, Portal, Settings activation |
| Court catalogs | Jurisdiction hierarchies, court names, filing instructions, identifier crosswalks | Web/Portal selection UIs, Compose agents |
| Masking profiles | `default`, `hipaa_strict`, `legal_hold` plus column mask instructions | Database RLS enforcement, audit redaction |
| Logging & observability hints | Never-log keys, sampling budgets, FinOps hints | Observability fabric, FinOps dashboards |

- Locale packs derive from Unicode CLDR releases and store ICU tags, fallback chains, MessageFormat 2 payloads, attribution metadata, and accessibility copy. Missing locales create `LOCALIZATION_MISSING_LOCALE` tasks until resolved.
- `i18n.fallback_chain` enforces deterministic order `requested_locale` → base_language → platform_default (default `en-CA`, overridable per org)` with org overrides applied before fallback evaluation.
- RTL readiness remains mandatory for locales declared in `i18n.required_rtl_locales[]`; regression coverage exercises at least two non-English locales per release (one RTL) to validate accessibility announcements, hotkey parity, and localized error copy readability.
- Localization QA syncs weekly with the Localization program to coordinate glossary updates and locale expansion; editorial QA approves tone guides. Release checklist references Appendix L snapshots and assistive-technology recordings.
- UI integrations honor `i18n.supported_locales[]` toggles; contract tests cover ICU boundaries (numbers, dates, currency, measurement units) via `tests/i18n/test_icu_boundaries.py` and Playwright RTL snapshots (`tests/ui/test_rtl_layout.spec.ts`). Missing keys fail CI rather than rendering raw identifiers.
- Pseudolocalization (`scripts/i18n/pseudolocale.sh`, `npm run test:pseudolocale`) runs in CI and release hardening; regressions emit `localization_pseudolocale_regression_total` and block activation.
- Localization ops capture glossary/tone guide approvals, localized UX snapshots, and AT recordings under `ops/localization/<date>/`; product sign-off precedes Settings activation when new locales go live.

### 2.3 Integration with Reference Manager & Settings (binding)

**Purpose:** Describe upstream inputs and coordination expectations. **|**
**Contract:** RM signed bundles (catalogs, residency metadata, localization strings, licensing info) and Settings activation payloads are required inputs; unsigned or stale bundles are rejected, and unsafe Settings diffs require dual approval per §4.2. **|**
**State:** RM publishes `reference_manager.catalog.{published,updated}` events with bundle hashes; LPE records versions in compiled artifacts and OPA manifests. Settings activation triggers dry-run compiles, diff artifacts, and event fan-out `lpe.policy_context.updated`. **|**
**Failures & handling:** Adoption lag (`reference_bundle_adoption_seconds` > SLA) or RM drift triggers §5.1 RB-LPE-COMPILER or RB-LPE-OPA-ROLLBACK. **|**
**Observability:** “Reference Adoption” dashboard, event audit logs, and `lpe_legacy_request_total` (shim usage). **|**
**Breadcrumbs:** `packages/core/lpe/events.py`, `packages/core/reference_manager/integration.py`, tests `tests/specs/test_lpe_event_bridge.py`, change calendar `ops/change/lpe_cutover.ics`.

- RM operates as the editorial/source-of-truth service; LPE consumes only signed RM bundles and rejects unsigned or stale payloads.
- RM publishes `reference_manager.catalog.{published,updated}` events `{domain, version, effective_at, hash, affected_keys[], bundle_uri}`. LPE invalidates cached compiles, records bundle versions in each `PolicyContext`, and updates OPA discovery manifests in lockstep.
- Settings activation runs a dry-run compile, surfaces structured diffs for review, and blocks unsafe changes (loosening residency, missing localization strings) pending dual approval per §4.2.
- Infrastructure catalogue entries from RM document deployment footprints (SaaS shared, SaaS dedicated, customer perimeter). LPE injects `deployment_type` into `PolicyContext` so Guardian, Portal, and automation respect residency, logging, and support boundaries.
- Baseline controls: RM captures jurisdiction-specific minimum requirements for PII, SPI, and PHI; LPE encodes these baselines and prevents org-level Settings from weakening them.

### 2.4 SDKs & consumers (normative)

**Purpose:** Frame expectations for first-party SDKs and dependent services. **|**
**Contract:** Python `udocket_lpe` and TypeScript `@uDocket/lpe-client` SDKs provide deterministic caches, ETag revalidation, and `on_policy_context_updated` hooks; consumers (Guardian, workers, Portal, Compose/Analyze) must log digests and respect residency/masking directives. **|**
**State:** SDK caches default to 5 minute TTL with background refresh; cache misses emit `lpe_cache_refresh_total` and structured logs. **|**
**Failures & handling:** Cache staleness or signature mismatches escalate via §5.1 and §5.3; SDK CI enforces contract tests prior to release. **|**
**Observability:** “SDK Health” dashboard (metrics `lpe_cache_hit_ratio`, `lpe_sdk_cache_error_total`) and synthetic probes hitting HIPAA/PHIPA/PIPA contexts post-deploy. **|**
**Breadcrumbs:** SDK repos `packages/core/lpe/sdk/`, `packages/js/lpe-client/`, tests `tests/sdk/test_lpe_client.py`.

- `udocket_lpe.PolicyContext` and `@uDocket/lpe-client` expose immutable contexts recording `generated_at`, `source_settings_version`, `policy_context_version`, and digests; helpers enforce conditional GET/ETag semantics and record telemetry.
- SDKs surface `on_policy_context_updated` hooks so Guardian, Portal, Compose, and workers flush caches deterministically; offline operation is limited to cached contexts with valid TTL.
- `policy_context_version` and digest telemetry appear in Guardian judgments, Signer manifests, Compose deliverables, and storage manifests to prove enforcement lineage.

### 2.5 Inputs & outputs (binding)

**Purpose:** Summarize compiler inputs, emitted artifacts, and determinism guarantees. **|**
**Contract:** Reference Manager bundles, Settings activation payloads, waiver manifests, and feature flags form the immutable inputs for each compile; outputs must remain hash-stable given identical inputs. **|**
**State:** Compiled tables (`compiled_policy_context`, `compiled_l10n_locale`, `compiled_policy_bundle`) retain `{policy_context_version, digest_sha256, generated_at, source_settings_version}` metadata and reference bundle/license hashes. **|**
**Failures & handling:** Missing locales, unsigned bundles, expired waivers, or digest drift block activation and trigger §4.2 validation gates plus §5 runbooks. **|**
**Observability:** CI jobs `ci-lpe-validation`, `ci-opa-bundle-signatures`, and metrics `lpe_compiler_duration_seconds`, `lpe_policy_block_total`, `lpe_bundle_signature_error_total`. **|**
**Breadcrumbs:** Compiler pipeline `packages/core/lpe/compiler.py`, schema fixtures `spec/schemas/policy_context.schema.json`, bundle manifests `ops/lpe/opa_bundles/`.

- **Inputs**
  - Reference Manager signed bundles: jurisdiction catalogs, residency metadata, localization strings, questionnaires/forms, provider allowlists, licensing and attribution metadata.
  - Settings activation payloads: `localization.*`, `privacy.*`, `regions.*`, waiver manifests, HIPAA toggles, deployment metadata, feature flags.
  - Manual waivers and change approvals captured in App.O; unsafe diffs require Architecture + Security sign-off.
- **Outputs**
  - `compiled_policy_context` keyed by `(org_id, case_id, locale, privacy_flags_hash)` detailing residency, privacy frameworks, retention defaults, disclaimer keys, masking profiles, logging rules, and digests.
  - `compiled_l10n_locale` locale metadata (ICU tags, fallback chains, attribution, accessibility copy, MessageFormat payloads).
  - `compiled_policy_bundle` entries listing bundle digests, signature manifests, rollout channels, expiry, and dual-signature fingerprints.
  - API responses include `policy_context_version`, `settings_snapshot_version`, `generated_at`, `digest_sha256`, and deterministic ordering for caching.

### 2.6 Residency posture & waivers (binding)

**Purpose:** Capture residency guardrails, waiver scope, and enforcement semantics. **|**
**Contract:** Residency allowlists originate from RM catalogs; Settings may restrict further but cannot widen without dual-approved waivers. Waivers embed `waiver_id`, scope, expiry, and remediation plan and propagate to manifests and OPA bundles. **|**
**State:** Residency metadata persists in `compiled_policy_context.residency_regions{compute[], storage[], vector[]}` and `regions.egress.waiver{}` fields; waiver ledger lives in `ops/lpe/waivers.yaml` with evidence directories per review. **|**
**Failures & handling:** Expired waivers, provider drift, or allowlist gaps trigger §5.3 RB-LPE-WAIVER, freeze Settings activation, and require Guardian confirmation before resuming traffic. **|**
**Observability:** Alerts `lpe_policy_block_spike`, `residency_endpoint_drift_total`, `waiver_expiring_total`, `residency_block_total`; synthetic tenant “EU-REFERENCE” validates posture weekly. **|**
**Breadcrumbs:** Residency tooling `ops/scripts/lpe/audit_residency.py`, Guardian enforcement `packages/core/guardian/policy.py`, waiver reviews `ops/lpe/waiver_reviews/<date>/`.

- Waiver enforcement: active waivers embed `waiver_id`/expiry into `PolicyContext`; Guardian and workers relay this to OPA, stamp manifests with `cross_region=true`, and document `RESIDENCY_WAIVER_USED`. Absent or expired waivers force `POLICY_BLOCK` responses until remediation.
- Network and provider enforcement: mesh `AuthorizationPolicy` denies egress outside compiled allowlists; nightly scanner validates provider SANs, CIDRs, and residency metadata alongside RM catalogs (§8.3.3).
- Availability posture: compliance trumps uptime—jobs pause when all in-region providers are unhealthy instead of spilling to non-compliant regions. RM catalogs must approve ≥2 providers per region for core services (speech, LLMs); Guardian raises `REGION_PROVIDER_DEGRADED` when redundancy falls below the floor.

```yaml
jurisdictions:
  US:
    CA:
      frameworks: [CCPA_CA]
      retention_overrides:
        QA_LOGS: 365d
        PRIVACY_ARTIFACTS: 730d
      residency:
        compute: [na-us-1, na-us-2]
        storage: [na-us-1]
      portal:
        disclaimer_key: portal.disclaimer.ca
  EU:
    DE:
      frameworks: [GDPR_DE]
      residency:
        compute: [eu-central-1]
        storage: [eu-central-1]
frameworks:
  HIPAA:
    phi_allowed: true
    requires_mode_enable: true
localization:
  default_locale: en-US
  time_format: "yyyy-MM-dd HH:mm z"
  number_system: "latn"
```

```python
ctx = lpe.get_policy_context(
    org_id=org_id,
    case_id=case_id,
    privacy_flags={"PHI": True},
    locale="en-US",
)
if ctx.frameworks.HIPAA.required and not ctx.frameworks.HIPAA.enabled:
    raise PolicyBlock("HIPAA_REQUIRED", context_digest=ctx.digest_sha256)
db.set_rls_mask_profile(ctx.masking_profile)
vector_client = vector_pool.for_regions(ctx.residency_regions.compute)
formatter = lpe.get_locale("en-US").formatters
rendered_date = formatter.date_short(approved_at)
```

Residency outcomes derive from `PolicyContext` allowlists while OPA enforces deny-by-default egress rules and returns structured deny codes (`REGION_NOT_ALLOWED`, `WAIVER_REQUIRED`). Waivers embed `{waiver_id, expires_at, justification}` into contexts; Guardian, Portal, and manifest pipelines propagate the waiver reference when used. Continuous scanners compare active contexts against mesh egress manifests and provider regions; drift raises `residency_policy_block_total` alerts and references §8.3.3 for remediation. Refer to `docs/automation/lp-engine/diagrams/residency-policy-enforcement-v1.mmd` for the activation → evaluation → enforcement sequence.

- Drift scanner compares active residency allowlists with mesh egress policies, DNS resolution, and provider metadata, writing findings to `ops/residency/findings/<timestamp>.jsonl` (`{org_id, service, endpoint, allowed, waiver_id?, severity}`) and paging on `residency_drift_detected_total`.
- Waiver ledger entries (`ops/waivers/WAIVER-*.json`) must include scope, approved regions, expiry, remediation plan, and dual approvals (Security + Architecture); expired entries trigger `waiver_expiring_total` and block activations until resolved.
- Quarterly residency council reviews scanner coverage, waiver usage, and drift findings; minutes live in `ops/residency/reviews/<quarter>.md` and feed FinOps regional budgeting.

### 2.7 Database masking integration (binding)

**Purpose:** Tie masking profiles to database policies and validation suites. **|**
**Contract:** LPE emits `masking_profile` values (`default`, `hipaa_strict`, `legal_hold`). Settings activation compiles profiles into `field_mask_rule` rows covering `CASE`, `ARTIFACT`, `QA_LOG`, `GUARDIAN_JUDGMENT`, and `DELIVERY_RECEIPT`; database guard rails enforce FORCE RLS on relevant tables. **|**
**State:** Masking metadata lives alongside PolicyContext digests and Settings snapshots; helper functions translate profiles into concrete mask rules during activation. **|**
**Failures & handling:** Mismatched mask profiles or missing RLS contexts raise `mask_profile_mismatch_total` and `rls_context_missing_total`, invoking §5.1 RB-LPE-COMPILER. **|**
**Observability:** Grafana “Postgres RLS & Masking” dashboard plus CI tests `tests/platform/db/test_mask_profiles.py::test_mask_profile_matches_policy` and `tests/platform/db/test_rls_guard.py::test_guard_blocks_missing_context`. **|**
**Breadcrumbs:** Database migrations `db/migrations/tenant/002_masking_profile_policies.sql`, implementation `packages/core/lpe/policy_context.py`, helpers `db/utils/masking.py`.

- `db.set_rls_mask_profile(ctx.masking_profile)` writes the profile to `udocket.mask_profile`; triggers translate the profile into column-level masking instructions during activation.
- LPE prevents activation when `masking_profile` coverage fails for HIPAA-required contexts; tests replay masked queries to ensure Guardian and Portal consumers respect row-level security.

______________________________________________________________________

## 3) API Contract

**Purpose:** Document public and internal interfaces. **|**
**Contract:** Define required inputs/outputs, authentication, and versioning. **|**
**State:** Highlight persisted payloads, schemas, queues, or files produced. **|**
**Failures & handling:** Enumerate error codes, retries, and backoffs. **|**
**Observability:** Metrics/logs/traces covering API health. **|**
**Breadcrumbs:** Controller handlers, schema definitions, integration tests. **|**
**References:** Link to schema fixtures or appendices.

### 3.1 External Interfaces (binding)

- Runtime helpers supply immutable `PolicyContext` payloads carrying `generated_at`, `policy_context_version`, `settings_snapshot_version`, digests, residency allowlists, masking profiles, disclaimer keys, retention defaults, and logging directives.
- Enforcement consumers: Guardian, workers, Portal bootstrap, Compose/Analyze, Notifications, Search/Vector, and Signer manifests read contexts to enforce PHI posture, disclaimers, DSAR retention, and region placement.
- Responses echo `Idempotency-Key` plus headers `X-PolicyContext-Version` and `X-PolicyContext-Digest`; conditional GETs use `If-None-Match` with digest ETags. Stale requests receive `412 Precondition Failed` with remediation hints.
- Error envelope codes map to dependency actions: `POLICY_CONTEXT_NOT_FOUND`, `WAIVER_REQUIRED`, `HIPAA_REQUIRED`, `VALIDATION_ERROR`, `LOCALE_NOT_AVAILABLE`, `JURISDICTION_NOT_SUPPORTED`.

- Authentication: Keycloak service tokens + HMAC signature; middleware records `policy_context_version` and `settings_snapshot_version` for audit.
- Conditional GETs: clients reuse digests via `If-None-Match`; stale requests receive `412 Precondition Failed` with hints to refresh caches.
- Discovery hints: responses include `Link: <https://docs.udocket.io/reference-migration>; rel="successor-version"` while legacy shims operate.

### 3.2 Internal Interfaces (normative)

- Discovery endpoint `/api/v1/lpe/opa/discovery` serves signed manifests with bundle URIs per region, SHA-256 digests, rollout windows, and rollback pointers; clients poll every 60 seconds with `If-None-Match` and fail closed when manifests stale.
- Bundles require mTLS + HMAC headers and carry dual signatures (Ed25519 + ECDSA P-256 for FIPS). When `security.crypto.fips_mode|required`, clients invoke `opa_verify_dual_signature()`; missing ECDSA signatures raise `FipsBundleSignatureError` and block activation.
- Decision logs conform to `spec/schemas/opa_decision_log.schema.json`; `reason_code` values (`REGION_NOT_ALLOWED`, `WAIVER_REQUIRED`, `HIPAA_REQUIRED`, `ATTACHMENT_FORBIDDEN`, `OPA_ERROR`) map to PolicyContext `policy_block_code` fields surfaced to Guardian/Portal.
- Policy Agent (OPA) deployments: sidecars colocated with Guardian, Portal, and workers for low latency; centralized cluster distributes discovery bundles. Metrics `opa_decision_latency_seconds`, `opa_bundle_status`, `opa_denied_total` feed the “OPA Policy Plane” dashboard.
- Local hot-reload tooling (`scripts/dev/run_lpe_hot_reload.py`) compiles sandbox bundles, pushes to a developer OPA, and diffs PolicyContext digests without staging deploys; snapshots attach to PRs modifying policy or locale packs.

### 3.3 API Error Codes (binding)

**Purpose:** Enumerate LPE-specific `ApiError.code` values so downstream services and automation interpret failures consistently. **|**
**Contract:** LPE APIs reuse the platform catalog in [`Platform Runtime §3.3`](../platform/runtime.md#33-api-error-codes-binding); the scenarios below describe how those codes manifest during policy compilation and evaluation. **|**
**State:** Error envelopes originate from `/api/v1/lpe/policy-contexts`, `/api/v1/lpe/compile`, and `/api/v1/lpe/evaluate`; schema parity maintained via `spec/schemas/api_error.schema.json`. **|**
**Failures & handling:** Unknown codes fail Spectral lint and `tests/platform/policy/test_api_errors.py`; runtime emissions trigger `lpe_api_error_total{code="unknown"}` alerts. **|**
**Observability:** Dashboards “LPE – Compilation” and “LPE – Policy Evaluation” track `lpe_api_error_total{code}`, `lpe_compiler_duration_seconds`; synthetic evaluations verify waivers/residency scenarios. **|**
**Breadcrumbs:** Controllers `apps/platform/policy/views.py`, compiler `packages/core/policy/compiler.py`, runtime `packages/core/policy/runtime.py`, tests `tests/platform/policy/test_compile_api.py`, `tests/platform/policy/test_evaluate_api.py`. **|**
**References:** Platform Runtime §3.3, Reference Manager spec §3.4, Settings spec §3.4, Guardian spec §2.2.

> _Full listing:_ [API error codes index](../overview/tdd/appendices/api_error_codes.md#localization-policy-engine)

<!-- BEGIN AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->
| Code | Scenario | Client guidance |
| --- | --- | --- |
| `CONFLICT` | Concurrent activation changed the same PolicyContext version or hash. | Refresh digests via conditional GET, merge changes, and retry with updated If-Match or Idempotency-Key headers. |
| `POLICY_BLOCK` | Evaluation detected residency, waiver, or privacy violations that must block the requested action. | Present policy_block_code and waiver metadata to operators, remediate configuration, or obtain a waiver before retrying. |
| `PROVIDER_DEGRADED` | Reference Manager or policy bundle fetch unavailable; fallback chain exhausted. | Pause rollouts, retry once dependencies are healthy, and notify Ops of the degraded state. |
| `RATE_LIMIT` | Org exceeded compilation or evaluation budget or concurrency ceiling. | Honor Retry-After headers, stagger batch compiles, and request higher limits through governance. |
| `VALIDATION_ERROR` | Policy bundle or context payload failed schema or semantic validation. | Inspect details[], correct inputs such as missing locales or duplicate rules, and resubmit compile/evaluate. |
<!-- END AUTO-GENERATED: api-error-codes:summary (error_codes.yaml) -->

<!-- BEGIN AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->
| Code | HTTP Status | Audit Required | Metrics |
| --- | --- | --- | --- |
| `CONFLICT` | 409 | No | lpe_api_error_total |
| `POLICY_BLOCK` | 403 | Yes | lpe_policy_block_total<br>guardian_policy_block_total |
| `PROVIDER_DEGRADED` | 503 | Yes | lpe_api_error_total<br>lpe_compiler_duration_seconds |
| `RATE_LIMIT` | 429 | No | lpe_api_error_total<br>lpe_rate_limit_total |
| `VALIDATION_ERROR` | 400 | No | lpe_api_error_total |
<!-- END AUTO-GENERATED: api-error-codes:catalog (error_codes.yaml) -->

### 3.4 Downstream service integrations (normative)

**Purpose:** Map LPE touchpoints across the platform. **|**
**Contract:** Downstream services must consume PolicyContext digests, honor residency/masking directives, and record versions in audit logs. **|**
**State:** Guardian, workers, Portal, Compose, Notifications, Search, and storage adapters persist digests alongside manifests and telemetry. **|**
**Failures & handling:** Digest mismatches or stale contexts surface via `guardian_policy_context_version_mismatch_total` and integration contract tests; responders follow §5 and §8.3 runbooks. **|**
**Observability:** Grafana “Integration Health” dashboard (metrics `lpe_cache_refresh_total`, `guardian_policy_context_version_mismatch_total`) plus synthetic bootstrap checks. **|**
**Breadcrumbs:** Service adapters `packages/core/lpe/integrations.py`, Guardian integration `packages/core/guardian/api.py`, tests `tests/specs/test_policy_context_contract.py::test_downstream_consumers_record_digest`.

- Web/Portal: bootstrap sessions with PolicyContext, replace ad-hoc localization/policy banners with LPE strings, and log digests for audit.
- Guardian & workers: block PHI artifacts unless frameworks enable PHI; record `policy_context_version` and digests per judgment.
- Search/Retrieval: choose locale analyzers and residency for vector storage using context metadata.
- Notifications: derive template selection, disclaimers, and delivery restrictions from contexts while preserving outbox idempotency.
- Settings UI: renders diff previews and unsafe-change warnings produced by the compiler.
- Storage adapters: enforce residency choices and annotate manifests with waiver usage.

### 3.5 Reference Manager alignment (normative)

**Purpose:** Describe bundle adoption and editorial feedback loops. **|**
**Contract:** LPE rejects bundles lacking license metadata, sanitization attestations, or signatures; adoption lag SLO P95 ≤ 10 minutes between RM publish and LPE compile. **|**
**State:** RM adoption telemetry (`reference_manager_bundle_adoption_seconds`), localization coverage heatmaps, and deprecation metadata feed LPE compiler decisions. **|**
**Failures & handling:** Adoption lag or missing locales raise `reference_bundle_stale_total` and block deploy `deploy:reference-adoption`; responders coordinate per §8.3.1. **|**
**Observability:** “Reference Adoption” dashboard, localization coverage reports, and App.O ledger entries. **|**
**Breadcrumbs:** RM subscriber `packages/core/reference_manager/subscribers/lpe.py`, adoption tests `tests/specs/test_reference_adoption.py`, reports `ops/reference/reports/adoption_lag.csv`.

- Localization coverage heatmaps from RM feed completeness checks; missing locales open tasks for Content Ops and freeze activations until closed.
- Deprecations record replacements and effective dates; contexts surface deprecation hints until the effective date passes.

### 3.6 Tools & developer workflows (informative)

**Purpose:** Capture local testing and hot-reload harnesses. **|**
**Contract:** Developers must attach hot-reload manifest snapshots to PRs touching policy or locale packs; local tooling mirrors production validation. **|**
**State:** Sandbox bundles, manifest diffs, and decision-log validations persist under `ops/lpe/hot_reload/` and PR artifacts. **|**
**Failures & handling:** Hot-reload drift or validation failures block merges until reconciled with production manifests. **|**
**Observability:** CI job `ci-lpe-hot-reload`, scripts `scripts/dev/run_lpe_hot_reload.py`, `scripts/opa/validate_decision_logs.py`. **|**
**Breadcrumbs:** Local stack compose files `docker-compose.yml`, docs `docs/automation/lp-engine/diagrams/*`.

- `scripts/dev/run_lpe_hot_reload.py` compiles bundles, pushes to sandbox OPA, and diffs digests without staging deploys.
- `PROJECT_NAME=udocket-dev make stack.up SERVICES="lpe opa settings reference-manager"` mirrors production dependencies for manual verification (the raw compose invocation remains available if you prefer it).
- `scripts/opa/validate_decision_logs.py` asserts decision logs remain schema-compliant during development.

______________________________________________________________________

## 4) State Management

**Purpose:** Explain storage and configuration strategy. **|**
**Contract:** Define persistence guarantees, migration expectations, and retention. **|**
**State:** Describe schemas, caches, and configuration sources. **|**
**Failures & handling:** Cover corruption, drift, and reconciliation flows. **|**
**Observability:** Metrics for storage health, cache hit rates, or config parity. **|**
**Breadcrumbs:** ORM models, migrations, infrastructure manifests. **|**
**References:** TDD appendices or diagrams related to state.

### 4.1 Runtime topology (normative)

**Purpose:** Summarize deployment footprint, scaling levers, and observability anchors. **|**
**Contract:** LPE API, compiler workers, and bundle signer operate as independent components with shared release windows; replicas must stay within residency-approved regions. **|**
**State:** Kubernetes manifests under `infra/kubernetes/lpe/` define Deployments, CronJobs, and HSM integrations; queue depth and adoption telemetry drive autoscaling. **|**
**Failures & handling:** Replica drift, queue starvation, or signer outages page SRE via §8.2 triggers and pause activations until parity restored. **|**
**Observability:** Dashboards “LPE – Enforcement & Residency”, “LPE Compiler”, metrics `lpe_cache_hit_ratio`, `lpe_compiler_duration_seconds`, `lpe_bundle_sign_total`; synthetic tests `tests/synthetics/test_lpe_runtime_topology.py`. **|**
**Breadcrumbs:** Manifests `infra/kubernetes/lpe/`, Helm charts `infra/helm/lpe/`, tests `tests/synthetics/test_lpe_runtime_topology.py`.

| Component | Runtime | Responsibilities | Scaling & notes | Observability anchors |
| --- | --- | --- | --- | --- |
| LPE API | FastAPI | PolicyContext lookup, localization pack retrieval, court/jurisdiction search | Horizontally replicated Deployment; caches warmed via activation events | `lpe_lookup_latency_seconds`, `lpe_cache_hit_ratio`, `lpe_policy_context_version` |
| Compiler jobs | Celery/worker cron | Compile policy contexts, localization packs, OPA bundles | Auto-scales on activation queue depth; throttled to deployment window | `lpe_compiler_duration_seconds`, `lpe_policy_block_total` |
| Bundle signer | Managed HSM clients | Dual-sign Ed25519 + ECDSA bundles, rotate keys | Runs on demand with queue depth alerts | `lpe_bundle_sign_total`, `lpe_bundle_signature_error_total` |

Settings-driven compiler runs as part of activation; background cron validates digests against RM bundles and Settings snapshots to ensure parity.

### 4.2 Compiler pipeline & validation gates (binding)

**Purpose:** Explain how Settings activation drives compiler stages and guardrails. **|**
**Contract:** Activation pipeline runs dry-run compile, produces diff artefacts, validates localization coverage, residency allowlists, waiver metadata, and digests; unsafe changes require dual approval (`org_admin` + Platform `sysadmin`) before publication. **|**
**State:** Pipeline sequence: dry-run → validation → unsafe diff classification → evidence packaging → event fan-out. Inputs include RM bundles, Settings payloads (`localization.*`, `privacy.*`, `regions.*`, waiver manifests), and feature flags. **|**
**Failures & handling:** Schema drift, missing locales, or expired waivers reject activations and trigger §5.1/§5.2 mitigation. **|**
**Observability:** “LPE Compiler” dashboard (metrics `lpe_compiler_duration_seconds`, diff volume, unsafe flags) and CI job `ci-lpe-validation`. **|**
**Breadcrumbs:** `packages/core/lpe/compiler.py::run_activation_pipeline`, tests `tests/specs/test_lpe_compiler.py`, diff artefacts `ops/lpe/activations/<id>/`.

### 4.3 Data stores & determinism (binding)

**Purpose:** Capture persistence strategy and guarantees. **|**
**Contract:** Compiled tables (`compiled_policy_context`, `compiled_l10n_locale`, `compiled_policy_bundle`) remain immutable per version; re-compiles with identical inputs reproduce identical digests. **|**
**State:** Postgres schemas store compiled rows with digests and provenance; object storage holds signed bundles; Settings snapshots embed digests to prove lineage. **|**
**Failures & handling:** Digest mismatch vs Settings snapshot raises `lpe_policy_context_digest_mismatch_total` (future metric) and invokes §5.1 RB-LPE-COMPILER. **|**
**Observability:** Adoption dashboards, audit JSONL (`ops/lpe/discovery_audit.jsonl`), and synthetic tenant checks (“EU-REFERENCE”) validate residency posture. **|**
**Breadcrumbs:** Schema definitions `packages/core/lpe/models.py`, migrations `ops/lpe/migrations/`, replay tooling `ops/scripts/lpe/replay_adoption.py`.

### 4.4 PolicyContext caching & SDK lifecycle (normative)

**Purpose:** Describe cache behaviour and invalidation semantics. **|**
**Contract:** SDK caches respect 5 minute TTL and ETag-based revalidation; Settings or RM events invalidate caches via `lpe.invalidate` broadcasts. Manual overrides require incident documentation per §8.5.3. **|**
**State:** SDK caches keep digests, TTLs, and telemetry counters; Portal & Guardian embed `policy_context_version` in audit events. **|**
**Failures & handling:** Cache staleness surfaces as `POLICY_CONTEXT_STALE`; responders inspect digests and follow §5.1 runbooks. **|**
**Observability:** Metrics `lpe_cache_hit_ratio`, `lpe_cache_refresh_total`, and synthetic GETs verify caching paths. **|**
**Breadcrumbs:** `packages/core/lpe/sdk/cache.py`, tests `tests/sdk/test_lpe_client.py::test_cache_refresh`.

### 4.5 Localization QA artefacts (normative)

**Purpose:** Track localization assets and evidence required for release. **|**
**Contract:** Prior to Settings activation, teams must supply pseudolocale results, ICU boundary snapshots, assistive-technology recordings, localized UX captures, and editorial QA sign-off. Waivers require `LOCALIZATION_EXCEPTION` artefacts with ≤30 day expiry. **|**
**State:** Artefacts stored under `ops/localization/*` (pseudolocale runs, ICU snapshots, ATR recordings, approvals). **|**
**Failures & handling:** Missing artefacts block activation; escalate via §8.5.1 checklist and §8.3.6 RB-LPE-LOCALE-GAP if gaps persist. **|**
**Observability:** CI (`npm run test:pseudolocale`, `tests/i18n/test_icu_boundaries.py`, Playwright RTL snapshots) and “Localization QA” dashboard. **|**
**Breadcrumbs:** Checklist `ops/localization/checklists/lpe_release.yaml`, tests `tests/i18n/test_release_checklist.py`.

### 4.6 PolicyContext fixtures & validation harness (binding)

**Purpose:** Maintain golden snapshots, schemas, and validation tools guaranteeing deterministic PolicyContext outputs. **|**
**Contract:** Schema updates require ADR review, synchronized SDK releases, regenerated fixtures, and semantic versioning aligned with `/reference/*` sunset plan. **|**
**State:** Golden fixtures covering HIPAA, PHIPA, PIPA, GDPR, and waiver combinations live in `spec/fixtures/lpe/policy_context/<jurisdiction>/` with digests recorded in `fixtures.yml`; audit evidence stored under `ops/lpe/activations/<activation_id>.json`. **|**
**Failures & handling:** Fixture drift or schema mismatch fails CI (`ci-policy-context-fixtures`) and blocks merges until fixtures and rationale updated. **|**
**Observability:** CI job `ci-policy-context-fixtures`, script `scripts/lpe/verify_policy_context.py`, and schema `spec/schemas/policy_context.schema.json`. **|**
**Breadcrumbs:** `spec/schemas/policy_context.schema.json`, fixtures `spec/fixtures/lpe/policy_context/`, validation script `scripts/lpe/verify_policy_context.py`.

- Validation harness executes compiles and diffs resulting contexts; failures require updated fixtures plus PR rationale.
- Settings activations persist `{policy_context_version, digest_sha256, settings_snapshot_version}` for DSAR replay and residency audits.

______________________________________________________________________

## 5) Failure Modes

**Purpose:** Provide the resilience profile and default mitigations. **|**
**Contract:** Identify what must fail closed vs. degraded. **|**
**State:** Note circuit breakers, queues, or compensating transactions. **|**
**Failures & handling:** Enumerate incidents, fallback procedures, and manual runbooks. **|**
**Observability:** Alerts, dashboards, and SLOs tied to failure handling. **|**
**Breadcrumbs:** Runbooks, incident retros, chaos tests. **|**
**References:** Link to ops docs or ADRs describing failure strategy.

### 5.1 Policy context drift & OPA discovery regression (binding)

**Purpose:** Contain compiler and OPA bundle failures. **|**
**Contract:** Burn-rate breaches, adoption lag, or OPA discovery errors freeze bundle activations until RB-LPE-COMPILER or RB-LPE-OPA-ROLLBACK steps execute. Bundles must roll back to last-known-good, caches flushed, and discovery audits attached to the incident. **|**
**State:** Evidence stored under `ops/lpe/opa_bundles/`, `ops/lpe/discovery_audit.jsonl`, and activation diff artefacts. **|**
**Failures & handling:** Compiler mismatches, missing signatures, discovery latency, or stale digests; responders follow §8.3.2 and §8.3.3 runbooks. **|**
**Observability:** Alerts `lpe_compiler_duration_overrun`, `lpe_bundle_signature_error`, `opa_discovery_stale_total`, `reference_bundle_stale_total`. **|**
**Breadcrumbs:** Runbooks `ops/runbooks/lpe/compiler.md`, `ops/runbooks/lpe/opa_bundle_rollback.md`, automation `ops/scripts/lpe/deploy_opa_bundle.py`, `scripts/opa/flush_cache.py`.

### 5.2 Localization coverage gap (binding)

**Purpose:** Restore localization completeness when packs regress. **|**
**Contract:** Alerts `lpe_localization_gap_total` and pseudolocale regressions halt releases until missing translations, accessibility artefacts, and QA evidence are restored per RB-LPE-LOCALE-GAP. **|**
**State:** Locale inventories (`ops/lpe/locales.csv`), QA artefacts, and localization approvals tracked in App.O. **|**
**Failures & handling:** Missing pseudolocale output, accessibility evidence, or localization tests; responders coordinate with Localization program per §8.3.6. **|**
**Observability:** “Localization QA” dashboard, Playwright RTL snapshots, pseudolocale pipelines. **|**
**Breadcrumbs:** Runbook `ops/runbooks/lpe/locale_gap.md`, automation `ops/scripts/lpe/audit_locales.py`.

### 5.3 Waiver expiry & residency drift (binding)

**Purpose:** Prevent expired residency waivers or misaligned endpoints from violating policy. **|**
**Contract:** Waiver ledger entries (`ops/lpe/waivers.yaml`) require dual approvals (Security + Architecture), scope, expiry, and remediation plan; expiring waivers trigger RB-LPE-WAIVER. Provider endpoint drift drives coordination with RM to refresh catalogs. **|**
**State:** Waiver reviews stored under `ops/lpe/waiver_reviews/<date>/`; residency findings logged in `reference_provider_endpoint_finding`. **|**
**Failures & handling:** Expired waivers, missing approvals, or residency catalog gaps escalate via §8.3.4 RB-LPE-WAIVER and §8.3.6; Settings activations freeze until resolved. **|**
**Observability:** Alerts `lpe_policy_block_spike`, `reference_manager_provider_endpoint_violation_total`, `waiver_expiring_total`. **|**
**Breadcrumbs:** Runbook `ops/runbooks/lpe/waiver_expiry.md`, RM residency tooling `ops/reference/runbooks/residency_alignment.md`.

______________________________________________________________________

## 6) Observability

**Purpose:** Summarize telemetry, logging, and SLO governance. **|**
**Contract:** Metrics enumerated here must exist in production; removal requires Observability review and equivalent replacements. LPE honours the platform “never log” policy ([`Logging §4`](../platform/observability.md#4-state-management-binding)) and maintains decision-log schema guarantees. **|**
**State:** Grafana dashboards (“LPE – Enforcement & Residency”, “LPE Compiler”, “Localization QA”, “FinOps – LPE”, “SDK Health”) alongside PagerDuty service “Localization & Policy Engine”. Decision logs stored ≥365 days. **|**
**Failures & handling:** Missing metrics or runbook linkage trigger docs lint failures; SLO burn-rate alerts feed §8.2 triggers. **|**
**Observability:** Metrics `lpe_lookup_latency_seconds`, `lpe_policy_context_version`, `lpe_cache_hit_ratio`, `lpe_compiler_duration_seconds`, `lpe_policy_block_total`, `lpe_bundle_signature_error_total`, `opa_bundle_status`, `lpe_privacy_framework_enabled_total`, `lpe_compiler_resource_seconds`, `lpe_sdk_cache_error_total`. **|**
**Breadcrumbs:** Observability config `infra/observability/dashboards/lpe.json`, FinOps workbook `ops/finops/lpe_cost_model.xlsx`, tests `tests/observability/test_lpe_metrics.py`, `tests/finops/test_lpe_budget.py`. **|**
**References:** Observability standards or shared appendices.

- Cost posture: FinOps alerts trigger when rolling 7-day spend exceeds 80 % of monthly budget; localization QA tracks translation spend per locale.
- Synthetic monitors run after each deploy against HIPAA/PHIPA/PIPA contexts; failures block rollout.
- Decision-log validator `scripts/opa/validate_decision_logs.py` runs in CI and after major releases.
- Pre-release stress tests (k6 + Locust) exercise Guardian, LPE/OPA evaluation, and RLS-heavy API paths; results store under `ops/runbooks.md` and must meet Appendix L baselines before shipping.
- Logs honour the never-log list ([`Logging §4`](../platform/observability.md#4-state-management-binding)); sampling budgets follow dynamic controls in [`Logging §7`](../platform/observability.md#7-cost-management--budgets), and structured logging adapters prevent ad-hoc stdout noise.

### 6.1 SLOs & Targets (binding)

**Purpose:** Capture PolicyContext availability, compile latency, and residency enforcement expectations. **|**
**Contract:** Lookups, compiles, and policy blocks must satisfy the thresholds below before activations or bundle promotions proceed. **|**
**State:** Metrics `lpe_lookup_latency_seconds`, `lpe_compiler_duration_seconds`, `lpe_policy_block_total`; dashboards “LPE – Enforcement & Residency”, “LPE Compiler”, synthetic HIPAA/PIPEDA probes. **|**
**Failures & handling:** Breaches invoke RB-LPE-CONTEXT, RB-LPE-COMPILER, or residency runbooks before unfreezing activations. **|**
**Observability:** Grafana dashboards, Alertmanager burn-rate alerts, synthetic activation jobs, and decision-log audits provide evidence. **|**
**Breadcrumbs:** Telemetry `packages/core/lpe/telemetry.py`, synthetic definitions `synthetics/lpe_*`, runbooks `docs/ops/runbooks/lpe/*.md`. **|**
**References:** TDD §6, Settings spec §7.3, Guardian spec §7.

- **PolicyContext availability:** ≥99.9% of lookups succeed each month (`lpe_lookup_latency_seconds` + synthetic HIPAA/PIPEDA probes). Breaches trigger RB-LPE-CONTEXT and block Settings activations.
- **Compile latency:** 95th percentile `lpe_compiler_duration_seconds` ≤ 2 seconds; exceeding the budget pauses rollout until regression is resolved and documented.
- **Residency enforcement responsiveness:** `lpe_policy_block_total` records blocks within 60 seconds of unsafe activation; missed blocks escalate to Security and halt bundle promotion.

______________________________________________________________________

## 7) Security & Compliance

**Purpose:** Capture security posture, privacy obligations, and compliance artefacts. **|**
**Contract:** STRIDE-by-component threat model artefacts must stay current; activations referencing risky controls cite threat IDs. Dual-signed bundles, waiver governance, HIPAA/PHIPA/PIPA retention overrides, and DPIA/RoPA linkage remain mandatory. **|**
**State:** Threat models stored under `ops/security/threat_models/lpe/*.md`; waiver ledger `ops/lpe/waivers.yaml`; compliance artefacts (DPIA/RoPA) tracked in `ops/compliance/`. **|**
**Failures & handling:** Missing threat model updates, expired waivers, or unverified retention overrides block deploy approvals and trigger §5.3 runbooks. **|**
**Observability:** Security dashboards (“Residency & Enforcement”), alerts `lpe_policy_block_total`, `lpe_privacy_framework_enabled_total`, and compliance checklists in App.O. **|**
**Breadcrumbs:** `packages/core/lpe/security.py`, compliance scripts `ops/scripts/lpe/audit_compliance.py`, tests `tests/compliance/test_lpe_retention.py`. **|**
**References:** Link to residency or policy appendices/ADRs.

- Never-log enforcement: Logging middleware strips PII/PHI; sampling budgets follow [`Logging §7`](../platform/observability.md#7-cost-management--budgets) dynamic controls.
- Key management: HSM-backed signing keys rotate per policy; evidence stored with bundle manifest records.
- DSAR & erasure: §8.5.3 workflow captures PolicyContext replay evidence after DSAR operations.
- FIPS enforcement: When `security.crypto.fips_mode|required`, services consuming OPA bundles invoke `opa_verify_dual_signature()` to assert Ed25519 + ECDSA P-256 signatures. Missing or invalid ECDSA signatures raise `FipsBundleSignatureError`, fire `opa_bundle_fips_signature_missing_total`, and block activation; CI job `ci-opa-bundle-signatures` validates artifacts under `ops/lpe/opa_bundles/*.tar.gz`.
- Risk mitigations:
  - **Policy drift between Settings and runtime:** compiler dry-run diff, activation unsafe classification, and golden-case monitors prevent divergence.
  - **Performance regressions on hot paths:** in-process caches with TTLs, async refresh, and P95 alerting; feature flag enables neutral fallback `PolicyContext` while triaging.
  - **Logging leaks of sensitive policy detail:** never-log enforcement, log redaction filters, and audit seal reviews per App.O checklist.

______________________________________________________________________

## 8) Operational Notes (binding)

**Purpose:** Summarize deployments, maintenance windows, readiness posture, and day-2 workflows that keep the service healthy. **|**
**Contract:** Capture SLAs, rollout gates, and operational ownership, including how alerts map to playbooks. **|**
**State:** Note infrastructure manifests, automation scripts, runbook repositories, and evidence storage. **|**
**Failures & handling:** Document rollback paths, drill cadence, and how gaps in operational readiness are remediated. **|**
**Observability:** Release dashboards, deployment checks, synthetic monitors, and runbook execution tracking. **|**
**Breadcrumbs:** Helm charts, Terraform modules, runbooks, incident templates. **|**
**References:** Ops appendices, deployment ADRs, alert catalogs.

### 8.1 Operational Posture

**Purpose:** Document staffing, maintenance windows, and readiness expectations. **|**
**Contract:** Shared on-call rotation with Guardian/Settings monitors LPE dashboards, attends weekly localization syncs, and enforces blue/green deployment windows (weekday 16:00–18:00 UTC). Burn-rate breaches freeze new activations automatically. **|**
**State:** Roster `ops/reference/oncall.yaml`, change calendar `ops/change/lpe_cutover.ics`, localization sync notes in `ops/localization/sync_logs/`. **|**
**Failures & handling:** Missing rota coverage or ignored deployment freezes trigger management review and follow-up tasks. **|**
**Observability:** PagerDuty response metrics, deployment dashboards, and freeze indicators. **|**
**Breadcrumbs:** Roster `ops/reference/oncall.yaml`, deployment scripts `ops/reference/deploy.py`, App.O readiness reviews. **|**
**References:** Incident management playbooks, HR/ops policies.

- Editorial shifts overlap to keep localization queue staffed; quarterly readiness reviews audit roster coverage and runbook adherence.
- Synthetic tenant “EU-REFERENCE” runs weekly to confirm residency baseline across Azure endpoints and TSA integrations.

### 8.2 Incident Triggers

**Purpose:** Map alerts to runbooks so responders start with the correct context. **|**
**Contract:** Alert definitions in `infra/monitoring/lpe-prometheus-rules.yaml` embed RB-LPE identifiers; responders must attach evidence before clearing alerts. **|**
**State:** Incident logs stored under `ops/lpe/incidents/<date>.jsonl` with referenced bundle hashes, diff artefacts, and screenshots. **|**
**Failures & handling:** Misaligned alert→runbook mapping or suppressed routes require Ops sign-off and backlog work before release. **|**
**Observability:** Grafana dashboards, Alertmanager routing, PagerDuty service “Localization & Policy Engine”, and post-incident reviews. **|**
**Breadcrumbs:** Alert rules `infra/monitoring/lpe-prometheus-rules.yaml`, incident template `ops/lpe/incident_template.md`. **|**
**References:** Runbook sections, observability standards.

- `lpe_lookup_latency_p95_breach` → RB-LPE-COMPILER.
- `lpe_compiler_duration_overrun` → RB-LPE-COMPILER.
- `lpe_bundle_signature_error` or `opa_discovery_stale_total` → RB-LPE-OPA-ROLLBACK.
- `lpe_localization_gap_total` or pseudolocale failure → RB-LPE-LOCALE-GAP.
- `lpe_policy_block_spike` or `waiver_expiring_total` → RB-LPE-WAIVER.
- `reference_bundle_stale_total` → RB-LPE-COMPILER.

### 8.3 Runbooks & Drills (binding)

**Purpose:** Maintain authoritative recovery guides and drill expectations. **|**
**Contract:** Alerts in §8.2 map to RB-LPE identifiers; responders update the runbook index after each incident or quarterly tabletop. **|**
**State:** Runbooks live in `ops/runbooks/lpe/` with automation scripts under `ops/scripts/lpe/`; incident evidence attaches to App.O decision logs. **|**
**Failures & handling:** Missing or stale steps block deploy sign-off until the runbook is refreshed. **|**
**Observability:** Docs lint validates references; quarterly drill calendar tracks execution. **|**
**Breadcrumbs:** Runbooks `ops/runbooks/lpe/*.md`, automation `ops/scripts/lpe/*.py`, tests `tests/ops/test_runbook_integrity.py`. **|**
**References:** §5 Failure modes, §8.1 Operational posture, §6 Observability.

#### 8.3.1 Runbook Index (informative)

- `RB-LPE-COMPILER` — Compiler regression / adoption freeze
- `RB-LPE-OPA-ROLLBACK` — OPA bundle rollback
- `RB-LPE-WAIVER` — Waiver expiry response
- `RB-LPE-LOCALE-GAP` — Localization coverage gap

#### 8.3.2 Primary Runbooks (binding)

**Purpose:** Document localization & policy engine runbooks executed during incidents or drills. **|**
**Contract:** Alerts map to specific RB-LPE identifiers with evidence requirements; responders update runbooks after each incident or drill. **|**
**State:** Runbook markdown and automation scripts live under `ops/runbooks/lpe/` and `ops/scripts/lpe/`; incident evidence persists in `ops/lpe/incidents/`. **|**
**Failures & handling:** Missing or stale instructions block deployment approvals until refreshed. **|**
**Observability:** Docs lint, PagerDuty analytics, and Ops governance dashboards provide freshness metrics. **|**
**Breadcrumbs:** `ops/runbooks/lpe/*.md`, `ops/scripts/lpe/*.py`, incident templates `ops/lpe/incidents/*.md`. **|**
**References:** Alert catalog, Settings governance policy, FinOps handbook.

- `RB-LPE-COMPILER`: Freeze compiler, roll back to last-known-good bundle, run regression suite, and capture adoption evidence before resuming publishes.
- `RB-LPE-OPA-ROLLBACK`: Deploy prior OPA bundle, flush discovery caches, validate `/status` endpoints, and document digests and validation output.
- `RB-LPE-WAIVER`: Renew or retire residency waivers, update Settings allowlists, run waiver verification scripts, and log approvals in App.O.
- `RB-LPE-LOCALE-GAP`: Restore localization coverage by delivering translations/QA artefacts, executing locale audits, and rebuilding compiler outputs.

#### 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover compiler regression, OPA rollback, waiver expiry, and localization gap scenarios; evidence stored in `ops/lpe/drills/<date>/` with retrospective notes.
- Docs lint (`make docs.check.runbooks`) and PagerDuty analytics confirm drill execution; missed drills trigger remediation before releases proceed.
- Compliance reviews reference drill artefacts, waiver ledgers, and compiler adoption metrics to demonstrate readiness.

### 8.4 Migrations & Backfills (binding)

**Purpose:** Govern schema migrations, bundle backfills, and cutover from `/reference/*` shims. **|**
**Contract:** Run migrations with `ops/scripts/lpe/migrate.py --dry-run` prior to production, capture digests, and retain rollback checkpoints. Shim retirement occurs when adoption metrics show <5 % shim usage for 30 days and all clients record modern endpoints. **|**
**State:** Migration manifests `ops/lpe/migrations/`, replay tooling `ops/scripts/lpe/replay_adoption.py`, shim telemetry `lpe_legacy_request_total`. **|**
**Failures & handling:** Partial migrations, adoption drift, or residual shim traffic; escalate via RB-LPE-COMPILER and record remediation tasks in App.O. **|**
**Observability:** Dashboards “Reference Adoption”, `lpe_legacy_request_total`, and reports from `scripts/reference/report_shim_usage.py`. **|**
**Breadcrumbs:** Migration README `ops/lpe/migrations/README.md`, change calendar `ops/change/lpe_cutover.ics`, shim implementation `packages/core/reference/__init__.py`. **|**
**References:** ADRs or ops docs governing migrations.

- Cutover timeline (executed starting Mon 2025-10-20 America/Vancouver):
  - **Weeks 1–2:** ADR + doc updates, schema/compiler scaffolding, seed jurisdiction data, `PolicyContext` draft, Threat Model v1.
  - **Weeks 3–4:** Integrations with Web/Portal, Guardian/Workers, Search; vector residency enforcement live.
  - **Week 5:** Accessibility CI gates, Notifications templates via LPE, dashboards, synthetic monitors.
  - **Week 6:** Cutover flag enabled, `/reference/*` deprecation notices, BCDR + DSAR replay drill, publish lessons-learned artifact.
- Migration deliverables required for sign-off:
  - Updated ADR, this document, refreshed diagrams, and OpenAPI bundle.
  - SDK releases and contract tests with golden PolicyContext fixtures.
  - Compiler outputs with diff artefacts and signed bundle manifests.
  - Enforcement matrix wired through API/Workers/Portal/RLS plus accessibility CI gates.
  - Provincial privacy mappings with DPIA/RoPA linkage and FinOps compute dashboards tied to LPE hints.
  - BCDR drill + DSAR replay evidence recorded under `ops/lpe/cutover_checklist.md`.

### 8.5 Operational Workflows (normative)

**Purpose:** Describe recurring operational tasks (manual review, quarterly audits, data purges). **|**
**Contract:** Define who executes each workflow, prerequisites, and escalation thresholds. **|**
**State:** Point to checklists, run sheets, or automation supporting the workflow. **|**
**Failures & handling:** Explain how skipped or incomplete workflows are detected and corrected. **|**
**Observability:** Track workflow health via dashboards, audit logs, or retrospectives. **|**
**Breadcrumbs:** Workflow documentation, automation scripts, staffing rosters. **|**
**References:** Incident management playbooks, staffing guides.

#### 8.5.1 Localization release checklist

- Weekly localization sync (Localization Ops + Product Localization + Accessibility) reviews glossary diffs, tone guide approvals, and pending locale launches; minutes stored under `ops/localization/meetings/<iso-week>.md`.
- Latest pseudolocale run results (`ops/localization/pseudolocale/<date>.json`) with zero blocking regressions.
- ICU boundary snapshots for numbers/dates/currency/measurement units (`ops/localization/icu_snapshots/<date>/`).
- Assistive-technology recordings (NVDA/JAWS/VoiceOver/TalkBack) and localized UX screenshots captured prior to activation.
- Editorial QA sign-off on tone guides and glossary updates (`ops/localization/approvals/<ticket>.md`).
- CI enforcement: `npm run test:pseudolocale`, `scripts/i18n/pseudolocale.sh`, `tests/i18n/test_icu_boundaries.py`, and Playwright RTL snapshots (`tests/ui/test_rtl_layout.spec.ts`) must pass.
- Merge-stop criteria: missing accessibility evidence, unresolved localization gaps, or failing localization CI jobs block activation; waivers require `LOCALIZATION_EXCEPTION` artefacts with ≤30 day expiry.
- Post-launch verification: run `tests/e2e/test_portal_policy_context.py::test_disclaimer_l10n` against production-like tenants and archive evidence under `ops/localization/post_launch/<release>.md`.

#### 8.5.2 DSAR replay & audit workflow

- Post-DSAR, execute `ops/scripts/lpe/replay_policy_context.py` to confirm PolicyContext replay integrity.
- Attach evidence (decision logs, replay outputs) to the incident record and App.O decision log.
- Quarterly BCDR drills review DSAR replay artefacts and update preventive tasks.

#### 8.5.3 Program gap closure tracking

- **Security:** Maintain STRIDE threat model updates; reference threat IDs in unsafe activation reports.
- **UX/QA:** Integrate WCAG 2.2 AA checks (axe-core/Pa11y); dashboards expose accessibility defect rate.
- **Compliance:** Encode PHIPA/PIPA retention overrides with DPIA/RoPA linkage; verify portal and Guardian flows reflect provincial flags.
- **FinOps/SRE:** Extend cost dashboards using LPE hints and ensure back-pressure controls operate; track `lpe_compiler_resource_seconds` against budgets.
- **SRE:** Execute BCDR drills capturing PolicyContext replay evidence after DSAR erasures and ensure watchdog automation records results in App.O.

#### 8.5.4 Validation coverage

- Contract tests validate OpenAPI schemas, golden `PolicyContext` fixtures for HIPAA/PHIPA/PIPA/GDPR combinations, and compiler diff outputs via `scripts/lpe/verify_policy_context.py`.
- `tests/e2e/test_portal_policy_context.py::test_disclaimer_l10n` verifies localized banners and attribution; `tests/platform/db/test_mask_profiles.py` ensures masking alignment.
- CI job `.github/workflows/lpe-validation.yml` runs `lint-artifact-vocabulary`, `python -m doc_tools.check_structure docs/automation docs/platform docs/overview`, and localization CI suites; failures block rollout.
- Synthetic monitors run after each deploy for HIPAA/PHIPA/PIPA contexts; failures keep cutover flags disabled until remediation.

______________________________________________________________________

## 9) Dependencies

**Purpose:** Map upstream inputs and downstream consumers. **|**
**Contract:** RM must publish signed bundles; Settings provides activation payloads; Guardian, workers, Portal, Compose/Analyze, and Observability rely on PolicyContext digests and localization packs. Breaking changes require joint rollout plans and documentation updates. **|**
**State:** Adoption tables `reference_bundle_adoption`, SDK telemetry, and integration harness tests prove alignment. **|**
**Failures & handling:** Source outages, adoption lag, or misaligned digests trigger §5 runbooks and freeze releases. **|**
**Observability:** Dashboards “Reference Manager – Adoption”, “Guardian Residency Enforcement”, `lpe_legacy_request_total`, and synthetic monitors. **|**
**Breadcrumbs:** Integration code `packages/core/reference_manager/integration.py`, Settings activation pipeline `apps/platform/settings/service.py`, Guardian integration `packages/core/guardian/api.py`. **|**
**References:** Link to other service docs or appendices.

- Upstream: Reference Manager (catalogs, localization, licensing), Settings (activation payloads), OPA discovery infrastructure, HSM signing services.
- Downstream: Guardian/portal/workers/Compose rely on PolicyContext digests; Observability consumes logging directives; FinOps uses cost hints.

| Dependency | Runtime / interface | Responsibilities | Integration notes | Observability anchors |
| --- | --- | --- | --- | --- |
| Reference Manager | RM publish events + signed bundles | Provides jurisdiction catalogs, residency metadata, localization strings, licensing attestations | Adoption lag SLO P95 ≤ 10 min; unsigned bundles rejected; diff artefacts stored with activations | `reference_manager_bundle_adoption_seconds`, `reference_bundle_stale_total` |
| Settings Service | Activation API + Celery workers | Supplies `localization.*`, `privacy.*`, `regions.*`, waiver manifests, feature flags | Unsafe diffs require Architecture + Security approvals; emits activation events for cache invalid | `settings_activation_duration_seconds`, diff artefact checks |
| Policy Agent (OPA) | Sidecar / centralized OPA cluster | Evaluates signed bundles for residency, HIPAA, egress, attachment rules; emits decision logs | Bundles dual-signed (Ed25519 + ECDSA); clients poll discovery with ETag; failures trigger fail-closed | `opa_decision_latency_seconds`, `opa_bundle_status`, `opa_denied_total` |
| Guardian | REST + gRPC integrations | Applies `POLICY_BLOCK`, `HIPAA_REQUIRED`, waiver enforcement, residency judgments | Must log `policy_context_version`/digest per judgment; requires fresh contexts before processing | `guardian_policy_context_version_mismatch_total`, `guardian_judgment_latency_seconds` |

______________________________________________________________________

## 10) References

- Residency policy enforcement diagram — `docs/automation/lp-engine/diagrams/residency-policy-enforcement-v1.mmd`.
- FIPS tracing for dual-signed policy bundles — TDD App.J.
- Localization QA evidence templates — `ops/localization/checklists/lpe_release.yaml`.
- OPA toolkit — `ops/scripts/lpe/deploy_opa_bundle.py`, `scripts/opa/validate_decision_logs.py`.
- Open Policy Agent — Bundles: <https://www.openpolicyagent.org/docs/latest/management-bundles/>
- Open Policy Agent — Discovery: <https://www.openpolicyagent.org/docs/latest/management-discovery/>
- Open Policy Agent — Decision Logs: <https://www.openpolicyagent.org/docs/latest/management-decision-logs/>
- LPE lifecycle ADR — `docs/adr/ADR-0003-localization-and-policy-engine.md`.
- Reference migration guide — `https://docs.udocket.io/reference-migration`.
