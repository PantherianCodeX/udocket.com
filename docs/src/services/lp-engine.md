______________________________________________________________________

title: "uDocket — Localization & Policy Engine Technical Design" subtitle: "Localization, Residency, and Policy Enforcement Specification" author:

- uDocket Platform Architecture Team
- Localization & Policy Program Leads version: 0.1-draft status: implementable classification: Confidential last_updated: 2025-10-23 owners:
- Platform Architecture
- Security Engineering
- Localization & Policy Program approvers:
- Architecture Steering Committee
- Security Review Board reviewers:
- QA Engineering Lead
- SRE Manager adr_index: docs/adr/README.md related_adrs:
- ADR-0004-localization-and-policy-engine.md header-includes:
- '<base href="..">'
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
- '<header class="page-header">uDocket — Localization & Policy Engine Technical Design <br> Localization, Residency, and Policy Enforcement Specification</header>'
- '<footer class="page-footer">Confidential · Last updated 2025-10-23 · Page <span class="page-number"></span> of <span class="page-count"></span></footer>'

______________________________________________________________________

**Audience:** Platform engineering, Reference Manager, Settings, Guardian, SRE, QA, Product Localization\
**Purpose:** Define Localization & Policy Engine (LPE) behaviour, contracts, and rollout controls so platform services consume consistent localization, residency, and compliance data.

______________________________________________________________________

## Document controls

| Field           | Value                                                                                                                |
| --------------- | -------------------------------------------------------------------------------------------------------------------- |
| Version         | 0.1-draft                                                                                                            |
| Status          | Implementable (mirrors front matter `status`; KEP lifecycle applies: Provisional → Implementable → Implemented)      |
| Last updated    | 2025-10-23 (source of truth is the front matter `last_updated`)                                                      |
| Primary owners  | Platform Architecture; Security Engineering; Localization & Policy Program                                           |
| Approvers       | Architecture Steering Committee; Security Review Board                                                               |
| Reviewers       | QA Engineering Lead; SRE Manager                                                                                     |
| ADR index       | `docs/adr/README.md` (immutable ADRs referenced in front matter `related_adrs`)                                      |
| Migration plan  | Supersede legacy Reference Engine docs once §6.4 cutover completes; `/reference/*` shims remain read-only until then |
| Docs validation | `python scripts/docs/lint_docs.py` (see `docs/README.md` for tooling)                                                |
| Link lint       | `python scripts/docs/link_check.py --strict` (CI `docs-link-check` stage blocks unresolved §/App./ADR refs)          |

Body sections follow the Purpose/Contract/State/Failure/Observability/Breadcrumb scaffold required by `scripts/docs/lint_docs.py --check-template`. Section tags `(binding)` and `(normative)` have the same meaning as the platform TDD.

______________________________________________________________________

## 0) Reading guide

- **Scope:** Service charter, compiler/runtime internals, contracts, integrations, rollout controls, and observability for LPE.
- **Structure:** Numbered sections limited to three levels of depth; appendices referenced from the main platform TDD remain authoritative for shared diagrams (App.A.9 residency sequence, App.J FIPS tracers).
- **Cross-references:** Use `§<number>` for this document, `TDD §<number>` for the platform TDD, and `App.<letter>` when pointing at shared appendices.
- **Maintenance:** Run `python scripts/docs/lint_docs.py` before submitting edits. Schema snippets must match `spec/schemas/*` fixtures and CI lints for localization completeness and policy coverage.
- **Doc change protocol:** Any PR touching localization packs, residency policies, or policy bundles must include this document in the review summary alongside `ADR-0004` diffs. Architecture/Security reviewers block merges when SDKs, Settings bundles, or policy compilers diverge from these contracts.

______________________________________________________________________

## 1) Service overview

### 1.1 Charter & mandate (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/lpe/service.py`, Tests `tests/specs/test_policy_context_contract.py::test_charter_scope`, Observability Grafana “LPE – Enforcement & Residency” dashboard (metrics `lpe_policy_context_version`, `lpe_policy_block_total`).

*Purpose: Describe LPE responsibilities, success criteria, and lifecycle expectations.*

- LPE is the single enforcement source for locale packs, jurisdictional policy, residency allowlists, privacy frameworks, disclaimers, and enforcement hints consumed across the platform.
- The service compiles deterministic `PolicyContext` payloads and localization bundles for every `(org_id, case_id?, locale, privacy_flags)` tuple. Snapshots embed digests and version metadata so downstream consumers prove which context they used.
- Runtime APIs stay versioned and publicly documented; `/reference/*` routes remain read-only shims emitting RFC 8594 `Sunset`/`Deprecation` headers until §6.4 migration completes.
- OPA sidecars evaluate Rego bundles signed and published by LPE. Bundles, contexts, and localization packs must remain hash-stable across recompiles given the same inputs.
- Service lifecycle mirrors ADR state transitions; rename from the deprecated Reference Engine completes only after ADR acceptance, compiler parity, and production cutover verification.

### 1.2 Inputs & outputs (normative)

**Breadcrumbs:** Implementation `packages/udocket_core/lpe/compiler.py`, Tests `tests/specs/test_lpe_compiler.py::test_compiled_artifacts_match_schema`, Observability “LPE Compiler” dashboard (metric `lpe_compiler_duration_seconds`).

*Purpose: Summarize compiled artifacts, storage layout, and consumer expectations.*

- **Inputs:**
  - Reference Manager (RM) signed bundles: jurisdiction catalogs, residency policy metadata, localization strings, questionnaires/forms, provider allowlists, licensing and attribution metadata.
  - Settings activation payloads: `localization.*`, `privacy.*`, `regions.*`, infrastructure deployment metadata, waiver manifests, HIPAA toggles.
  - Feature flags: cutover toggles, waiver expiries, sunset schedules for legacy APIs.
- **Outputs:** Immutable tables under `compiled_*` schemas and API responses:
  - `compiled_policy_context` keyed by `(org_id, case_id, locale, privacy_flags_hash)` storing `{policy_context_version, frameworks_enabled[], hipaa_required, residency_regions{compute[], storage[], vector[]}, storage_requirements{hipaa_required?, hipaa_capable_providers[], preferred_classes[]}, retention_days, portal_rules{disclaimer_key, banner_key}, logging_rules, masking_profile, i18n_keys[], digest_sha256}`.
  - `compiled_l10n_locale` with locale metadata, formatting rules, ICU tags, fallback chains, attribution, and MessageFormat 2 payloads.
  - `compiled_policy_bundle` entries describing bundle digests, signing keys, rollout channels, and expiries used by OPA discovery.
  - API responses include `policy_context_version`, `settings_snapshot_version`, `generated_at`, SHA‑256 digests, and deterministic ordering for caching.
- **Determinism:** LPE persists each compiled artifact with digests; Settings snapshots embed the digests and version IDs. Clients must record the digest in telemetry and audit trails.

### 1.3 Data domains & localization surface (normative)

**Breadcrumbs:** Implementation `packages/udocket_core/lpe/domains.py`, Tests `tests/specs/test_policy_context_contract.py::test_domain_coverage`, Observability “Localization Coverage” dashboard (metric `lpe_privacy_framework_enabled_total`).

*Purpose: Enumerate managed data categories and consumers.*

| Domain                        | Examples / keys                                                                                                                                                               | Primary consumers                                              |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Localization packs            | Approval banners, invalidation copy, intake flows, accessibility copy, formatting helpers (date/time, number, currency, measurement units), legal disclaimers keyed by locale | Staff UI, Client Portal, Notifications, Compose/Analyze agents |
| Residency policies            | Compute/storage/vector region allowlists, waiver metadata, deployment type annotations                                                                                        | Guardian, Workers, Search, storage adapters                    |
| Privacy frameworks            | HIPAA/PHIPA/PIPA/GDPR toggles, retention defaults, DSAR requirements, PHI posture                                                                                             | Guardian, Workers, Portal, Settings activation                 |
| Court catalogs                | Jurisdiction hierarchies, court names, filing instructions, identifier crosswalks                                                                                             | Web/Portal selection UIs, Compose agents                       |
| Masking profiles              | `default`, `hipaa_strict`, `legal_hold` plus column mask instructions                                                                                                         | Database RLS enforcement, audit redaction                      |
| Logging & observability hints | Never-log keys, sampling budgets, FinOps hints                                                                                                                                | Observability fabric, FinOps dashboards                        |

Localization strings store locale, text, fallback locale, source attribution, and licensing; missing locales create editorial follow-up tasks. BCP-47 normalization (`localization.normalize_locale()`) enforces casing and hyphenation; mismatches raise `LOCALIZATION_INVALID_LOCALE` at activation.

### 1.4 Relationship to Reference Manager & Settings (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/lpe/events.py`, Tests `tests/specs/test_lpe_event_bridge.py::test_catalog_publish_invalidation`, Observability “Reference Adoption” dashboard (metric `reference_manager_bundle_adoption_seconds`).

*Purpose: Define upstream dependencies and event-driven coordination.*

- RM operates as the editorial/source-of-truth service. LPE consumes signed RM bundles as read-only inputs; unsigned or stale bundles are rejected.
- RM publishes `reference_manager.catalog.published` and `.updated` events `{domain, version, effective_at, hash, affected_keys[], bundle_uri}`. LPE listens, invalidates cached compiles, and records bundle versions used in each `PolicyContext`; OPA discovery manifests update in lockstep.
- Settings activation triggers an LPE dry-run compile, surfaces diffs for review, and blocks unsafe changes (loosening residency, missing localization strings) pending dual approval per §4.2.
- Infrastructure catalogue entries from RM describe deployment footprints (SaaS shared, SaaS dedicated, customer perimeter). LPE injects `deployment_type` into `PolicyContext` so Guardian, Portal, and automation respect residency, logging, and support boundaries.
- Baseline enforcement: RM captures jurisdiction-specific minimum controls for PII, SPI, and PHI. LPE encodes these baselines; org-level Settings may tighten requirements but cannot fall below the jurisdiction baseline.

### 1.5 Service-level objectives & availability (binding)

**Breadcrumbs:** Implementation Helm charts `infra/kubernetes/lpe/`, Tests `tests/synthetics/test_lpe_slo.py::test_lookup_latency_budget`, Observability Grafana “LPE – Enforcement & Residency” dashboard (metric `lpe_lookup_latency_seconds`).

*Purpose: State reliability targets and deployment guardrails.*

- Runtime availability 99.9% with a 43 minute/month error budget. Breaches freeze bundle activations and OPA discovery pushes until stabilization; deploy gates block promotion when burn rate exceeds 1.0 for 60 minutes.
- Compiler jobs P95 ≤ 6 minutes. New bundles may roll out only during the shared OPA/LPE deployment window (weekday 16:00–18:00 UTC) once telemetry shows ≥50% remaining error budget.
- Synthetic monitors invoke `GET /api/v1/lpe/policy_context` for HIPAA/PHIPA/PIPA cases post-deploy and verify Guardian/Portal behaviour end-to-end.
- Synthetic tenant “EU-REFERENCE” exercises EU-only paths quarterly to confirm residency posture across Azure endpoints, storage buckets, vector shards, and TSA integrations.

______________________________________________________________________

## 2) Architecture & compiler pipeline

### 2.1 Runtime topology (normative)

**Breadcrumbs:** Implementation Kubernetes manifests `infra/kubernetes/lpe/`, Tests `tests/synthetics/test_lpe_runtime_topology.py::test_replicas_ready`, Observability Grafana “LPE – Enforcement & Residency” dashboard (metric `lpe_cache_hit_ratio`).

*Purpose: Summarize deployments, scaling, and observability anchors.*

| Component     | Runtime             | Responsibilities                                                             | Scaling & notes                                                         | Observability anchors                                                             |
| ------------- | ------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| LPE API       | FastAPI             | PolicyContext lookup, localization pack retrieval, court/jurisdiction search | Horizontally replicated Deployment; caches warmed via activation events | `lpe_lookup_latency_seconds`, `lpe_cache_hit_ratio`, `lpe_policy_context_version` |
| Compiler jobs | Celery/worker cron  | Compile policy contexts, localization packs, OPA bundles                     | Auto-scales on activation queue depth; throttled to deployment window   | `lpe_compiler_duration_seconds`, `lpe_policy_block_total`                         |
| Bundle signer | Managed HSM clients | Dual-sign Ed25519 + ECDSA bundles, rotate keys                               | Runs on demand with queue depth alerts                                  | `lpe_bundle_sign_total`, `lpe_bundle_signature_error_total`                       |

Settings-driven compiler runs as part of activation; background cron validates digests against RM bundles and Settings snapshots to ensure parity.

### 2.2 Compiler stages & validation gates (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/lpe/compiler.py::run_activation_pipeline`, Tests `tests/specs/test_lpe_compiler.py::test_activation_diff_blocks_unsafe_changes`, Observability Grafana “LPE Compiler” dashboard (metric `lpe_compiler_duration_seconds`).

*Purpose: Connect Settings activation to compiler safeguards and approval workflow.*

- New or consolidated keys:
  - `localization.default_locale`, `localization.timezone_default`, `localization.units` (`metric|imperial`).
  - `privacy.frameworks.enabled[]`, `privacy.retention_overrides{jurisdiction -> duration}`, `privacy.portal.disclaimer_key`.
  - `regions.allowlist.compute|storage|vector[]`, `regions.egress.waiver{id, scope, expires_at}`, `regions.egress.policy`.
- Activation pipeline sequence:
  1. Dry-run compile for affected scopes; produce structured diff artifacts.
  1. Validate localization coverage, residency allowlists, waiver metadata, and deterministic digests.
  1. Flag unsafe changes (loosening residency, missing required locales) requiring dual approval (`org_admin` + Platform `sysadmin`) before publish.
  1. Emit `lpe.policy_context.updated` events with digests and affected keys.
- Validation suite rejects activations when:
  - Localization packs lack required locales or fallback chains.
  - Residency overrides omit waiver references or expired waivers remain attached.
  - HIPAA-required contexts lack matching `masking_profile` coverage.
  - Compiler digests drift from golden fixtures.

### 2.3 PolicyContext contract (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/lpe/api.py::get_policy_context`, Tests `tests/specs/test_policy_context_contract.py::test_digest_and_cache_headers`, Observability tracing “PolicyContext Lookup” span (attributes `policy_context_version`, `context_digest`).

*Purpose: Define structure, caching, and enforcement expectations for PolicyContext.*

- Runtime helpers (`udocket_lpe.PolicyContext`, `@uDocket/lpe-client`) expose immutable contexts recording `generated_at`, `source_settings_version`, and `policy_context_version`.
- Enforcement points consuming `PolicyContext`:
  - Guardian and workers gate PHI and residency decisions (`POLICY_BLOCK`, `HIPAA_REQUIRED`, `RESIDENCY_POLICY_BLOCK`).
  - Web/Portal bootstrap caches contexts for localization banners, disclaimers, and waiver prompts.
  - Search & retrieval choose locale-aware analyzers and vector residency.
  - Database layer selects masking profiles (`masking_profile`) for secure views.
- Caching: In-process caches default TTL 5 minutes. Invalidation triggers on Settings activation events, RM publishes, or explicit `lpe.invalidate` calls. Clients reuse digest-based `ETag`s for conditional GETs; background refresh keeps hot tenants current.
- Error model follows shared API envelope (§5.1) with codes `POLICY_CONTEXT_NOT_FOUND`, `POLICY_CONTEXT_STALE`, `WAIVER_REQUIRED`, `VALIDATION_ERROR`. Responses include `Idempotency-Key` echo, `X-PolicyContext-Version`, and deprecation headers when legacy routes remain active.
- Retention metadata: contexts embed baseline retention (`retention_days`) plus artifact overrides; Settings UI and portal surfaces read these values directly so user-facing copy and erasure workflows stay aligned with compiled policy. Activation fails when overrides fall below jurisdictional minimums defined in RM bundles.

### 2.4 Localization packs & formatting helpers (normative)

**Breadcrumbs:** Implementation `packages/udocket_core/lpe/localization.py`, Tests `tests/specs/test_localization_contract.py::test_required_locales_present`, Observability Grafana “Localization QA” dashboard (metrics `lpe_localization_gap_total`, `localization_pseudolocale_regression_total`).

*Purpose: Capture localization data contracts, attribution, and QA obligations.*

- Locale packs derived from Unicode CLDR releases, stored with ICU tags, fallback chains, and MessageFormat 2 payloads. Packs include attribution metadata; missing locales create `LOCALIZATION_MISSING_LOCALE` tasks.
- `i18n.fallback_chain` defines deterministic fallback: `requested_locale → base_language → platform_default` (default `en-CA`, override via Settings). Org overrides apply before fallback evaluation.
- RTL readiness mandatory for locales listed in `i18n.required_rtl_locales[]`; regression coverage includes at least two non-English locales per release (one RTL) verifying accessibility announcements, hotkey parity, and localized error copy readability.
- Localization QA: weekly sync with LPE coordinates glossary updates and locale expansion; editorial QA approves tone guides. Release checklist references Appendix L snapshots and assistive-technology recordings. Contract test `tests/e2e/test_portal_policy_context.py::test_disclaimer_l10n` validates banner rendering and attribution across rotating locales (`en-CA`, `fr-CA`, `es-MX`, `ar-SA`).
- UI integrations respect locales declared in `i18n.supported_locales[]`; toggles persist per user. Contract tests cover ICU boundaries for numbers, dates, currency, and measurement units via `tests/i18n/test_icu_boundaries.py` and Playwright RTL snapshots (`tests/ui/test_rtl_layout.spec.ts`). Missing keys fail CI rather than rendering raw identifiers.
- Pseudolocalization (`scripts/i18n/pseudolocale.sh`, `npm run test:pseudolocale`) runs in CI and during release hardening; regressions emit `localization_pseudolocale_regression_total` and block activation until resolved.
- Localization operations capture glossary/tone guide approvals, localized UX snapshots, and assistive-technology recordings as artifacts stored under `ops/localization/<date>/`. Product sign-off precedes Settings activation when new locales go live.

### 2.5 Residency and egress enforcement (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/lpe/residency.py`, Tests `tests/specs/test_residency_policy.py::test_waiver_enforcement`, Observability Grafana “Residency Compliance” dashboard (metrics `reference_bundle_stale_total`, `lpe_policy_block_total`).

*Purpose: Illustrate residency lookups, OPA integration, and waiver propagation.*

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
  default_locale: en-US (org override)
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

Residency outcomes derive from LPE `PolicyContext` allowlists while OPA enforces deny-by-default egress rules and returns structured deny codes (`REGION_NOT_ALLOWED`, `WAIVER_REQUIRED`). Waivers embed `{waiver_id, expires_at, justification}` into contexts; Guardian, Portal, and manifest pipelines propagate the waiver reference when used. Continuous scanners compare active contexts against mesh egress manifests and provider regions; drift raises `residency_policy_block_total` alerts and references Appendix B for the remediation guidance. See App.A.9 for the activation → evaluation → enforcement sequence.

### 2.6 Database masking integration (binding)

**Breadcrumbs:** Implementation `db/migrations/tenant/002_masking_profile_policies.sql`, Tests `tests/platform/db/test_mask_profiles.py::test_mask_profile_matches_policy`, Observability Grafana “Postgres RLS & Masking” dashboard (metrics `mask_profile_mismatch_total`, `rls_context_missing_total`).

*Purpose: Tie masking profiles to database policies and validation suites.*

- LPE emits `masking_profile` values (`default`, `hipaa_strict`, `legal_hold`). Settings activation compiles profiles into `field_mask_rule` rows covering `CASE`, `ARTIFACT`, `QA_LOG`, `GUARDIAN_JUDGMENT`, `DELIVERY_RECEIPT`.
- Database guard rails enforce FORCE RLS on relevant tables. `db.set_rls_mask_profile(ctx.masking_profile)` writes `udocket.mask_profile`; helper functions translate the profile into concrete mask rules during activation.
- CI tests `tests/platform/db/test_mask_profiles.py::test_mask_profile_matches_policy` and `tests/platform/db/test_rls_guard.py::test_guard_blocks_missing_context` ensure profile coverage. Grafana “Postgres RLS & Masking” monitors `rls_context_missing_total` and `mask_profile_mismatch_total`.

______________________________________________________________________

## 3) Integrations & dependencies

### 3.1 Policy Agent (OPA) integration (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/lpe/opa.py`, Tests `tests/specs/test_opa_discovery_manifest.py::test_dual_signature_required`, Observability Grafana “OPA Policy Plane” dashboard (metrics `opa_discovery_stale_total`, `lpe_bundle_signature_error_total`).

*Purpose: Document bundle publishing, signature requirements, and fail-safe behaviour.*

- Discovery endpoint `/api/v1/lpe/opa/discovery` advertises region-specific bundle URIs, SHA‑256 digests/ETags, rollout windows, and rollback pointers. Clients poll every 60 seconds with `If-None-Match`; stale manifests force policy-deny with `OPA_ERROR` (`reason="DISCOVERY_STALE"`).
- Bundle downloads require mTLS + HMAC headers. Bundles carry dual signatures: Ed25519 (default) and ECDSA P-256 for FIPS. When `security.tls.fips_mode=true`, clients require both signatures; missing signatures raise `OPA_FIPS_SIGNATURE_MISSING` and block rollout.
- Decision logs validate against `spec/schemas/opa_decision_log.schema.json`. `reason_code` values map to downstream actions:

| `reason_code`          | `policy_block_code` exposed to callers    |
| ---------------------- | ----------------------------------------- |
| `OK`                   | `null`                                    |
| `REGION_NOT_ALLOWED`   | `RESIDENCY_POLICY_BLOCK`                  |
| `WAIVER_REQUIRED`      | `POLICY_BLOCK` (UI prompts for waiver)    |
| `HIPAA_REQUIRED`       | `HIPAA_REQUIRED`                          |
| `ATTACHMENT_FORBIDDEN` | `ATTACHMENT_BLOCK`                        |
| `OPA_ERROR`            | `POLICY_BLOCK` (with remediation message) |

- Bundles failing signature verification trigger immediate rollback to the previous `bundle_etag`. If no valid bundle exists, clients fail closed and page `opa_bundle_status` alerts. Runbook App.H RB-OPA-ROLLBACK covers recovery steps.

### 3.2 Downstream service integrations (normative)

**Breadcrumbs:** Implementation service adapters `packages/udocket_core/lpe/integrations.py`, Tests `tests/specs/test_policy_context_contract.py::test_downstream_consumers_record_digest`, Observability Grafana “Integration Health” dashboard (metrics `lpe_cache_refresh_total`, `guardian_policy_context_version_mismatch_total`).

*Purpose: Map LPE touchpoints across the platform.*

- **Web/Portal:** Replace ad-hoc localization and policy banners with LPE-provided strings and formatting helpers; session bootstrap fetches PolicyContext.
- **Guardian & workers:** Block PHI artifacts unless frameworks enable PHI; log `policy_context_version` and `digest` with each judgment.
- **Search/Retrieval:** Choose locale analyzers and residency for vector storage.
- **Notifications:** Template selection, disclaimers, and delivery restrictions derive from contexts; outbox maintains idempotency semantics.
- **Settings UI:** Displays diff previews and unsafe-change warnings produced by the compiler.
- **Storage adapters:** Enforce residency choices from contexts and annotate manifests with waiver usage.

### 3.3 Reference Manager alignment (normative)

**Breadcrumbs:** Implementation `packages/udocket_core/reference_manager/subscribers/lpe.py`, Tests `tests/specs/test_reference_adoption.py::test_publish_triggers_compile`, Observability Grafana “Reference Adoption” dashboard (metric `reference_manager_bundle_adoption_seconds`).

*Purpose: Describe bundle adoption and editorial feedback loops.*

- LPE rejects bundles lacking license metadata, sanitization attestations, or signed manifests.
- Adoption lag SLO: RM publish → LPE compile P95 ≤ 10 minutes. Metric `reference_manager_bundle_adoption_seconds` tracks compliance; alert `reference_bundle_stale_total` blocks deploy `deploy:reference-adoption` when lag persists >10 minutes.
- Localization coverage heatmaps from RM feed LPE completeness checks; missing locales open tasks to Content Ops.
- Deprecations capture replacements and effective dates. LPE surfaces deprecation hints in contexts until the effective date passes.

### 3.4 Tools & developer workflows (informative)

**Breadcrumbs:** Tooling `scripts/dev/run_lpe_hot_reload.py`, Tests `tests/scripts/test_lpe_hot_reload.py::test_manifest_snapshot_generated`, Observability CI job `ci-lpe-hot-reload` artifacts stored under `ops/lpe/hot_reload/`.

*Purpose: Capture local testing and hot-reload harnesses.*

- `scripts/dev/run_lpe_hot_reload.py` compiles bundles, pushes to sandbox OPA, and diffs digests without staging deploys. PRs touching policy or locale packs attach manifest snapshots from the harness.
- Local stack via `docker compose` mirrors production dependencies (`lpe`, `opa`, `settings`, `reference-manager`). Developers run `docker compose up --build lpe` to exercise APIs and `scripts/opa/validate_decision_logs.py` to confirm decision logs.

______________________________________________________________________

## 4) APIs & SDKs

### 4.1 Public endpoints (binding)

**Breadcrumbs:** Implementation `apps/platform/lpe/api.py`, Tests `tests/api/test_lpe_policy_context.py::test_etag_contract`, Observability Grafana “LPE API” dashboard (metrics `lpe_lookup_latency_seconds`, `lpe_cache_hit_ratio`).

*Purpose: Publish the formal interface for retrieving PolicyContext, localization packs, and catalogs.*

- `GET /api/v1/lpe/policy_context?org_id&case_id?&privacy_flags?&locale?`
- `GET /api/v1/lpe/courts?jurisdiction=&q=`
- `GET /api/v1/lpe/locales/{locale}`

Responses include `policy_context_version`, `settings_snapshot_version`, `generated_at`, and digest. `privacy_flags` accepts deterministic sorted key/value pairs to preserve cacheability.

- **Versioning:** Dedicated OpenAPI bundle with `x-surface: lpe`. Breaking changes require ADR + major version bump. `/reference/*` proxies remain read-only until §6.4 migration, attaching `Sunset`, `Deprecation`, and successor `Link` headers.
- **Headers:** `Cache-Control: private, max-age=300`, `ETag: <digest>`. Clients must revalidate on `412` responses.
- **Authentication:** Keycloak service tokens plus HMAC signature. Middleware records `policy_context_version` alongside `settings_snapshot_version` for auditing.
- **Error codes:** `POLICY_CONTEXT_NOT_FOUND`, `LOCALE_NOT_AVAILABLE`, `JURISDICTION_NOT_SUPPORTED`, `WAIVER_REQUIRED`, `VALIDATION_ERROR`.

### 4.2 SDK responsibilities (normative)

**Breadcrumbs:** Implementation `packages/udocket_core/lpe/sdk/` (Python) & `packages/js/lpe-client/`, Tests `tests/sdk/test_lpe_client.py::test_cache_refresh`, Observability Grafana “SDK Health” dashboard (metrics `lpe_cache_refresh_total`, `lpe_sdk_cache_error_total`).

*Purpose: Outline helper library behaviour and telemetry.*

- Python `udocket_lpe` and TypeScript `@uDocket/lpe-client` provide LRU caches, Settings activation hooks, and typed helpers (`policy_context()`, `get_locale()`, `lookup_court()`).
- SDKs emit metrics `lpe_cache_hit_ratio`, `lpe_cache_refresh_total`, and structured logs with `context_digest`. Background refresh warms caches prior to expiry; cache misses trigger synchronous fetch with exponential backoff.
- SDKs expose `on_policy_context_updated` events so workers can rehydrate context-dependent state without restarts.

### 4.3 Legacy shim & migration (binding)

**Breadcrumbs:** Implementation `packages/udocket_core/reference/__init__.py`, Tests `tests/api/test_reference_shim.py::test_deprecation_headers`, Observability Grafana “Reference Shim Sunset” dashboard (metric `lpe_legacy_request_total`).

*Purpose: Govern the `/reference/*` compatibility period.*

- `/reference/*` routes proxy to LPE read APIs while shims remain enabled. Responses include `Deprecation`, `Sunset`, and successor `Link` headers pointing to `https://docs.udocket.io/reference-migration`.
- Compatibility shim in `packages.udocket_core.reference` delegates to RM or LPE modules. Removal occurs after §6.4 cutover when SDKs consume new bundles exclusively.
- Monitoring tracks shim usage via `lpe_legacy_request_total`; alerts fire when usage remains above 5% of traffic beyond the announced sunset date.

______________________________________________________________________

## 5) Observability & operations

### 5.1 Metrics, logs, and dashboards (binding)

**Breadcrumbs:** Implementation observability config `infra/observability/dashboards/lpe.json`, Tests `tests/observability/test_lpe_metrics.py::test_metric_registration`, Observability Grafana “LPE – Enforcement & Residency” and “LPE Compiler” dashboards.

*Purpose: Define telemetry coverage and governance.*

- Metrics: `lpe_lookup_latency_seconds`, `lpe_policy_context_version`, `lpe_compiler_duration_seconds`, `lpe_cache_hit_ratio`, `lpe_policy_block_total`, `lpe_privacy_framework_enabled_total`, `lpe_bundle_signature_error_total`.
- Dashboards: “LPE – Enforcement & Residency” (latency, cache hits, decision distribution, `opa_bundle_status`, OPA decision P95 ≤ 20 ms) and “LPE Compiler” (diff volume, unsafe flags). Both listed in TDD §12.6.
- Logs honour the never-log list (TDD §12.1.3); responses contain identifiers/flags only. Sampling budgets follow dynamic controls in TDD §12.1.6.
- Decision logs from OPA feed immutable storage with ≥365 day retention. `scripts/opa/validate_decision_logs.py` verifies schema compliance in CI.

### 5.2 Alerting & escalation (normative)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/`, Tests `tests/ops/test_runbook_integrity.py::test_lpe_runbook_links`, Observability PagerDuty service “Localization & Policy Engine”.

*Purpose: Capture operational guardrails and direct responders to the maintained playbooks.*

- Burn-rate alerts freeze new bundle activations and OPA discovery pushes automatically until Appendix R procedures certify recovery.
- Alert catalog includes `lpe_lookup_latency_p95_breach`, `lpe_compiler_duration_overrun`, `lpe_bundle_signature_error`, `opa_discovery_stale_total`, `reference_bundle_stale_total`, `lpe_policy_block_spike`; each alert payload cites its RB-LPE identifier.
- Runbooks: Appendix R tracks RB-LPE-COMPILER (diff triage), RB-OPA-ROLLBACK (bundle rollback), RB-LPE-WAIVER (waiver expiry response), RB-LPE-LOCALE-GAP (missing localization coverage), with automation hooks and evidence requirements.
- DSAR replay drills log restoration evidence and `PolicyContext` replays to confirm erasure propagation post-restore; outcomes attach to the Appendix R audit checklist.

### 5.3 Cost posture & FinOps (normative)

**Breadcrumbs:** Implementation FinOps workbook `ops/finops/lpe_cost_model.xlsx`, Tests `tests/finops/test_lpe_budget.py::test_budget_thresholds`, Observability Grafana “FinOps – LPE” dashboard (metrics `lpe_compiler_resource_seconds`, `finops_budget_consumed_ratio`).

*Purpose: Outline cost controls and forecasting hooks.*

- `lpe_compiler_duration_seconds` and `lpe_compiler_resource_seconds` feed FinOps dashboards. Budgets defined per deployment; alerts fire when rolling 7-day cost exceeds 80% of monthly cap.
- Residency hints include preferred provider classes; FinOps automation uses hints to budget compute/storage costs per jurisdiction.
- Localization QA automation tracks translation spend per locale; budgets escalate when weekly sync exceeds forecast.

______________________________________________________________________

## 6) Testing, rollout, and migration

### 6.1 Validation coverage (binding)

**Breadcrumbs:** Implementation GitHub workflow `.github/workflows/lpe-validation.yml`, Tests enumerated in this section, Observability CI dashboard “Docs & Contract Validation”.

*Purpose: Enumerate automated tests required for launch and regression.*

- Contract tests validate OpenAPI schemas, golden `PolicyContext` fixtures for HIPAA/PHIPA/PIPA/GDPR combinations, and compiler diff outputs.
- `tests/e2e/test_portal_policy_context.py::test_disclaimer_l10n` verifies localized banners and attribution; `tests/platform/db/test_mask_profiles.py` ensures masking alignment.
- Synthetic monitors run after each deploy for HIPAA/PHIPA/PIPA contexts; failures block rollout.
- CI job `lint-artifact-vocabulary` scans diffs for stray status/judgment terms; `scripts/docs/lint_docs.py --check-template` enforces documentation scaffolding.

### 6.2 Gap-closure owners (normative)

**Breadcrumbs:** Implementation program tracker `ops/programs/lpe-gap-closure.yaml`, Tests `tests/programs/test_gap_closure_registry.py::test_owner_alignment`, Observability Quarterly review doc `ops/reviews/lpe_gap_closure.md`.

*Purpose: Assign accountable owners for outstanding gaps.*

- **Security:** Deliver STRIDE-by-component threat model artifacts; unsafe activations reference threat IDs.
- **UX/QA:** Integrate WCAG 2.2 AA checks (axe-core/Pa11y); approval/invalidation copy reads from localization packs; dashboards expose accessibility defect rate.
- **Compliance:** Encode PHIPA/PIPA retention overrides with DPIA/RoPA linkage; portal and Guardian flows reflect provincial flags.
- **SRE/Product:** Extend FinOps compute/token SLO dashboards and enforce back-pressure using LPE hints; alerts route with RB identifiers.
- **SRE:** Execute BCDR drills capturing `PolicyContext` replay evidence after DSAR erasures.

### 6.3 Rollout plan & cutover (binding)

**Breadcrumbs:** Implementation change calendar `ops/change/lpe_cutover.ics`, Tests `tests/programs/test_cutover_dependencies.py::test_sequence_dependencies`, Observability Launch checklist artifact `ops/lpe/cutover_checklist.md`.

*Purpose: Capture sequencing and feature-flag transitions.*

- Target timeline (starting Mon 2025-10-20, America/Vancouver):
  - **Weeks 1–2:** ADR + doc updates, schema/compiler scaffolding, seed jurisdiction data, `PolicyContext` draft, Threat Model v1.
  - **Weeks 3–4:** Integrations with Web/Portal, Guardian/Workers, Search; vector residency enforcement live.
  - **Week 5:** Accessibility CI gates, Notifications templates via LPE, dashboards, synthetic monitors.
  - **Week 6:** Cutover flag enabled, `/reference/*` deprecation notices, BCDR + DSAR replay drill, publish lessons-learned artifact.
- Repository migration: `packages/udocket_core/reference/*` modules transition into `packages.udocket_core.reference_manager`; new `packages.udocket_core.lpe` namespace houses compilers/access helpers. Compatibility shim remains until `/reference/*` sunset completes.
- Exit criteria: `/reference/*` shims read-only; adoption lag SLO green for 30 days; golden snapshots validate each publish; rollback tooling exercised quarterly (`BUNDLE_ROLLBACK_REPORT`).

### 6.4 Deliverables at cutover (binding)

**Breadcrumbs:** Implementation release tracker `ops/releases/lpe_cutover.yaml`, Tests `tests/releases/test_lpe_cutover.py::test_required_artifacts_present`, Observability Launch review Confluence page `LPE Cutover Review`.

*Purpose: List artifacts required to declare migration complete.*

- Updated ADR + this document + refreshed diagrams.
- OpenAPI bundle, SDK releases, and contract tests.
- Compiler outputs with diff artifacts and signed bundle manifests.
- Enforcement matrix wired through API/Workers/Portal/RLS.
- Accessibility CI gates and dashboards live.
- Provincial privacy mappings with DPIA/RoPA linkage.
- FinOps compute SLO dashboards tied to LPE hints.
- BCDR drill + DSAR replay artifact recorded.

### 6.5 Risks & mitigations (normative)

**Breadcrumbs:** Implementation risk register `ops/risk/lpe_risk_register.xlsx`, Tests `tests/risk/test_lpe_mitigations.py::test_controls_linked`, Observability Quarterly risk review minutes `ops/risk/review_minutes.md`.

*Purpose: Capture service-specific risks and responses.*

- **Policy drift between Settings and runtime:** Compiler diff + activation dry-run block inconsistent deployments; golden-case monitors detect divergence early.
- **Performance regressions on hot paths:** In-process caches with TTLs, async refresh, and P95 alerting; feature flag allows neutral fallback `PolicyContext` while triaging.
- **Logging leaks of sensitive policy detail:** Never-log enforcement, log redaction filters, audit seals review.

______________________________________________________________________

## 7) Appendices & references

### Appendix A — Localization QA & release checklist (binding)

**Breadcrumbs:** Implementation `ops/localization/checklists/lpe_release.yaml`, Tests `tests/i18n/test_release_checklist.py::test_required_artifacts_attached`, Observability Grafana “Localization QA” dashboard (metrics `lpe_localization_gap_total`, `localization_pseudolocale_regression_total`).

*Purpose: Provide the gating criteria and evidence trail required before enabling new locales or tone updates.*

- Weekly localization sync (Localization Ops + Product Localization + Accessibility) reviews glossary diffs, tone guide approvals, and pending locale launches. Minutes stored under `ops/localization/meetings/<iso-week>.md`.
- Required release artifacts prior to Settings activation:
  - Latest pseudolocale run (`ops/localization/pseudolocale/<date>.json`) with zero blocking regressions.
  - ICU boundary snapshots for numbers/dates/currency/measurement units (`ops/localization/icu_snapshots/<date>/`).
  - Assistive-technology recordings (NVDA/JAWS/VoiceOver/TalkBack) and localized UX screenshots per Appendix A checklist.
  - Editorial QA sign-off on tone guides and glossary updates (`ops/localization/approvals/<ticket>.md`).
- CI enforcement: `npm run test:pseudolocale`, `scripts/i18n/pseudolocale.sh`, `tests/i18n/test_icu_boundaries.py`, Playwright RTL snapshots (`tests/ui/test_rtl_layout.spec.ts`) must pass before merging localization packs.
- Merge-stop criteria: missing accessibility evidence, unresolved localization gaps, or failing localization CI jobs block activation. Waivers require `LOCALIZATION_EXCEPTION` artifacts with expiry ≤ 30 days.
- Post-launch verification: run `tests/e2e/test_portal_policy_context.py::test_disclaimer_l10n` against production-like tenants and archive evidence under `ops/localization/post_launch/<release>.md`.

### Appendix B — Residency drift monitors & waiver governance (normative)

**Breadcrumbs:** Implementation `ops/residency/drift_scanner/`, Tests `tests/residency/test_drift_scanner.py::test_detects_unapproved_endpoint`, Observability Grafana “Residency Compliance” dashboard (metrics `residency_policy_block_total`, `reference_bundle_stale_total`).

*Purpose: Capture automated residency checks, waiver tracking, and remediation flows supporting PolicyContext enforcement.*

- Drift scanner compares active PolicyContext residency allowlists with mesh egress manifests, DNS resolution, and provider metadata. Findings write to `ops/residency/findings/<timestamp>.jsonl` with `{org_id, service, endpoint, allowed, waiver_id?, severity}`.
- Alerts: `residency_policy_block_total` (policy denies) and `residency_drift_detected_total` (scanner findings) route to PagerDuty service “Residency & Policy Enforcement” and reference App.H RB-RES-ENDPOINT / RB-RES-BLOCK.
- Waiver ledger entries (`ops/waivers/WAIVER-*.json`) must include scope, approved regions, expiry, remediation plan, and dual approvals (Security + Architecture). Expired waivers trigger `waiver_expiring_total` alerts and block Settings activation until resolved.
- Remediation checklist: verify endpoint configuration, update provider region, re-run scanner, confirm PolicyContext digests refresh, and append decision log entry with evidence.
- Quarterly review: Residency council audits drift findings, waiver usage, and scanner coverage; minutes stored in `ops/residency/reviews/<quarter>.md` and feed FinOps regional budgeting.

### Appendix C — PolicyContext fixtures & validation harness (binding)

**Breadcrumbs:** Implementation `spec/schemas/policy_context.schema.json`, Tests `tests/specs/test_policy_context_contract.py::test_golden_snapshots`, Observability CI job `ci-policy-context-fixtures` (artifacts `ops/lpe/fixtures/<commit>.zip`).

*Purpose: Maintain golden snapshots, schemas, and validation tools guaranteeing deterministic PolicyContext outputs.*

- Golden fixtures cover HIPAA, PHIPA, PIPA, GDPR, and waiver combinations across SaaS multi-tenant, dedicated, and customer-managed deployments. Snapshots live in `spec/fixtures/lpe/policy_context/<jurisdiction>/` with digests recorded in `fixtures.yml`.
- Validation harness (`scripts/lpe/verify_policy_context.py`) loads fixtures, executes compiles, and diffs resulting contexts. Failures block CI and require updating fixtures plus documenting rationale in the PR summary.
- Schema governance: updates to `policy_context.schema.json` require ADR review, synchronized SDK releases, and regenerated fixtures. Breaking changes adopt semantic versioning and coordinate with `/reference/*` shim sunset plan (§4.3).
- Audit evidence: Each Settings activation stores `{policy_context_version, digest_sha256, settings_snapshot_version}` under `ops/lpe/activations/<activation_id>.json` to support DSAR replay and residency audits.

______________________________________________________________________

## Appendix R — Runbooks & drills (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/`, Tests `tests/ops/test_runbook_integrity.py::test_lpe_runbook_links`, Observability PagerDuty service “Localization & Policy Engine” with Grafana dashboards “LPE – Enforcement & Residency” and “LPE Compiler”.\\ *Purpose: Maintain actionable recovery guides for LPE incidents and drills.*\\ *Contract: Every alert enumerated in §5.2 maps to an RB-LPE identifier here; responders keep procedures evergreen through quarterly tabletop reviews.*\\ *State: Runbooks live beside automation scripts in `ops/runbooks/lpe/`; this appendix summarizes triggers, decision trees, and evidence requirements.*\\ *Failure modes & retries: Missing or stale runbooks trigger corrective action items and block deploy sign-off.*\\ *Observability: Docs lint checks confirm Appendix R coverage; PagerDuty postmortems must reference the executed RB-LPE ID.*

### R.1 Runbook index (informative)

- RB-LPE-COMPILER — Compiler diff escalation and rollback workflow.
- RB-OPA-ROLLBACK — OPA bundle rollback and policy cache validation.
- RB-LPE-WAIVER — Waiver expiry, renewal, and containment response.
- RB-LPE-LOCALE-GAP — Missing localization coverage remediation.

### R.2 RB-LPE-COMPILER — Compiler diff triage (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/compiler_diff_triage.md`, Automation `ops/scripts/lpe/run_compiler_diff.py`, Tests `tests/ops/test_runbook_integrity.py::test_compiler_diff_runbook`, Observability Grafana “LPE Compiler” (alerts `lpe_compiler_duration_overrun`, `lpe_bundle_signature_error`).\\ *Purpose: Contain defective compiler outputs and restore last-known-good bundles without service disruption.*\\ *Contract: Any compiler diff flagged unsafe or breaking must follow this procedure prior to promotion.*\\ *State: Diff artifacts reside in `ops/lpe/compiler_diffs/<date>/`; rollback bundles stored in `ops/lpe/rollback/<bundle_id>.json`.*\\ *Failure modes & retries: Skipping regression replays risks reintroducing invalid localization contexts; failing to rollback promptly blocks Settings activations.*\\ *Observability: Alert clears once safe bundle promoted and diff backlog returns to zero.*

Triggers: `lpe_compiler_duration_overrun`, `lpe_bundle_signature_error`, change tickets tagged `LPE-COMPILER`, manual escalations from QA.

Execution checklist:

1. Freeze compiler pipeline (`lpe.compiler.enabled=false`) and announce in `#ops-announcements`.
1. Inspect diff artifacts; confirm affected locales/regions and whether unsafe flags were raised.
1. Promote previous good bundle via `ops/scripts/lpe/promote_bundle.py --bundle <id>` and capture hash evidence.
1. Re-run regression suite (`make lpe-compiler-regressions`) and snapshot Grafana panels for incident ticket.
1. Coordinate Settings activation replay once bundle validated; update change ticket with evidence.

Post-remediation:

- Resume compiler pipeline and monitor `lpe_compiler_duration_seconds` for two cycles.
- File corrective tasks (root cause, automation gaps) and attach diff artefacts to App.O decision log.

### R.3 RB-OPA-ROLLBACK — OPA bundle rollback (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/opa_bundle_rollback.md`, Automation `ops/scripts/lpe/deploy_opa_bundle.py`, Tests `tests/ops/test_runbook_integrity.py::test_opa_rollback_runbook`, Observability Grafana “OPA Discovery” (alerts `opa_discovery_stale_total`, `reference_bundle_stale_total`).\\ *Purpose: Restore healthy Open Policy Agent bundles when discovery or validation failures occur.*\\ *Contract: Any production rollback must document bundle hashes, discovery health, and post-rollback validation.*\\ *State: Bundle manifests stored in `ops/lpe/opa_bundles/`; discovery checks recorded in `ops/lpe/discovery_audit.jsonl`.*\\ *Failure modes & retries: Deploying stale bundles without discovery verification risks policy drift; skipping cache flush leaves workers on outdated decisions.*\\ *Observability: Alert resolves when discovery latency normalizes and signature validation succeeds twice consecutively.*

Response steps:

1. Capture failing discovery IDs and affected services from alert payload.
1. Roll back via `ops/scripts/lpe/deploy_opa_bundle.py --bundle <last_good>` and flush worker caches (`scripts/opa/flush_cache.py`).
1. Validate OPA `/status` and `/health` endpoints plus policy unit tests (`pytest tests/opa/test_policy_context.py`).
1. Notify dependent teams (Settings, Guardian, Reference Manager) and confirm cached digests refresh.
1. Attach bundle hashes, validation output, and Grafana snapshots to incident ticket.

Follow-up:

- Run `ops/scripts/lpe/discovery_audit.py` to confirm discovery parity within 30 minutes.
- File preventive tasks for root cause (compiler bug, Settings drift, CDN failure).

### R.4 RB-LPE-WAIVER — Waiver expiry response (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/waiver_expiry.md`, Automation `ops/scripts/lpe/check_waivers.py`, Tests `tests/ops/test_runbook_integrity.py::test_waiver_runbook`, Observability Grafana “Residency & Enforcement” (alerts `lpe_policy_block_spike`, `lpe_privacy_framework_enabled_total`).\\ *Purpose: Maintain compliant waiver coverage and prevent unauthorized cross-jurisdiction traffic.*\\ *Contract: Expiring waivers must either be renewed with dual approval or decommissioned before expiry.*\\ *State: Waiver ledger maintained in `ops/lpe/waivers.yaml`; renewal evidence archived under `ops/lpe/waiver_reviews/<date>/`.*\\ *Failure modes & retries: Letting waivers lapse without containment can block activations or violate residency commitments.*\\ *Observability: Alert clears once waiver renewal recorded and `lpe_policy_block_total` returns to baseline.*

Checklist:

1. Review waiver ledger for entries expiring within alert window; confirm impacted locales and providers.
1. Engage Security + Architecture for renewal decision; capture approvals in decision log.
1. If waiver retired, update Settings allowlists and trigger Appendix R RB-LPE-LOCALE-GAP if localization fallback required.
1. Run `ops/scripts/lpe/check_waivers.py --verify` to ensure updated posture and attach output to incident ticket.
1. Communicate outcome to affected product owners and document customer impact, if any.

Audit trail:

- Store approvals, renewal artefacts, and communication templates alongside incident log.
- Schedule follow-up review to validate long-term remediation (automation fix, localization updates).

### R.5 RB-LPE-LOCALE-GAP — Localization coverage gap (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/locale_gap.md`, Automation `ops/scripts/lpe/audit_locales.py`, Tests `tests/ops/test_runbook_integrity.py::test_locale_gap_runbook`, Observability Grafana “Localization QA” (alerts `lpe_locale_gap_total`, `lpe_lookup_latency_p95_breach`).\\ *Purpose: Restore locale coverage when translations, policy text, or metadata go missing.*\\ *Contract: New locales must publish translations, disclaimer copy, and QA artefacts before re-enabling bundles.*\\ *State: Locale inventories in `ops/lpe/locales.csv`; QA recordings referenced in Appendix A.*\\ *Failure modes & retries: Re-enabling locales without QA sign-off risks incorrect or missing compliance copy.*\\ *Observability: Alert resolves once locale gap metric returns to zero and QA artefacts uploaded.*

Resolution steps:

1. Identify affected locales and impacted surfaces (portal, Guardian, notifications) from alert payload.
1. Coordinate with Localization program to deliver missing translations and QA recordings; update Appendix A checklist items.
1. Validate `ops/scripts/lpe/audit_locales.py` passes for affected locales and attach proof to ticket.
1. Run synthetic checks (`tests/e2e/test_portal_policy_context.py::test_disclaimer_l10n`) to confirm correct copy rendering.
1. Update Settings bundles and trigger LPE compiler rebuild; monitor `lpe_lookup_latency_p95_breach` for regression.

Post-checks:

- Log decision record in App.O with locale IDs, remediation timeline, and QA sign-offs.
- Schedule follow-up audit within one release cycle to verify coverage remains intact.

______________________________________________________________________

## References

- Residency policy enforcement sequence diagram — `services/lp-engine/diagrams/residency-policy-enforcement-v1.mmd`.
- FIPS tracing for dual-signed policy bundles — App.J in the platform TDD.
- LPE lifecycle ADR — `docs/adr/ADR-0004-localization-and-policy-engine.md`.
- Reference migration guide — `https://docs.udocket.io/reference-migration` (legacy API consumers).
