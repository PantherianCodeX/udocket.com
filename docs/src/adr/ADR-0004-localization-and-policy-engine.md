# ADR-0004 — Localization & Policy Engine (LPE) control/data plane split

- **Status:** Accepted
- **Date:** 2025-10-12
- **Deciders:** Architecture Steering Committee, Security Review Board, Platform AI Lead
- **Tags:** localization, policy, residency, bundles, reference-manager

## Context

The "Reference Engine" mixed multiple concerns:

1. Curating court/jurisdictional datasets, questionnaires, localization strings, and licensing metadata.
1. Compiling runtime policy/material for staff UI, workers, and database RLS.
1. Serving real-time lookups under tight latency guarantees.

This coupling made schema changes risky, prevented independent scaling, and offered no clear place to enforce residency or HIPAA toggles. In addition, we need deterministic localization data (CLDR/ICU) and stable policy artifacts to support agents, Guardian, and Settings activations.

## Decision

Introduce a formal control/data plane split:

- **Reference Manager (RM)** becomes the control plane. It curates sources (Wikipedia, Wikidata, court sites, vendor feeds), enforces licensing (CC BY-SA vs CC0), provides editorial workflows, and publishes signed, versioned bundles for catalogs, localization packs, and policy datasets. Bundles follow a content-addressed manifest format (SHA-256 digest, semantic version, compatibility range, license ledger).
- **Localization & Policy Engine (LPE)** is the runtime data plane. It consumes RM bundles plus Settings inputs, compiles deterministic `PolicyContext` payloads, and exposes a low-latency API/SDK for services to fetch residency allowlists, masking profiles, localization strings, retention defaults, and disclaimers.
- LPE emits immutable outputs (`compiled_*` tables, JSON manifest digests) and caches results per `(org_id, case_id?, locale, privacy_flags)` tuple. Deterministic UUIDv8-HMAC IDs ensure downstream artifacts maintain stable references.
- Settings activations run the LPE compiler in dry-run mode, produce diff artifacts, and require dual approval for unsafe changes (loosening residency/HIPAA). Cached contexts are invalidated via Redis/pub-sub events.
- `/reference/*` HTTP routes become read-only shims that delegate to LPE until sunset; new `/api/v1/lpe/*` endpoints serve policy/l10n requests.

## Consequences

- RM can evolve schema ingestion/adapters without impacting runtime latency. Editorial teams get richer tooling (diffs, license ledger, rollback).
- LPE scales independently (compiler workers vs lookup API) and enforces strict SLOs (lookup P95 ≤ 50 ms).
- Guardian, workers, UI, and database RLS consume the same `PolicyContext`, reducing drift and simplifying audits.
- Bundled CLDR/ICU data and MessageFormat 2 metadata centralize localization logic; frontend/compose agents no longer hard-code locale rules.
- Additional operational work: bundle signing/rotation, compiler monitoring, and cache health alerts. The split also mandates migration work for legacy modules (`packages.udocket_core.reference` → `reference_manager`/`lpe`) and temporary compatibility shims.
