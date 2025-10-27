# ADR-0003 — Public API versioning & sunset policy

- **Status:** Accepted
- **Date:** 2025-04-02
- **Deciders:** Architecture Steering Committee, Product Council
- **Tags:** api, versioning, sunset, compatibility

## Context

External integrations and customer-facing UI clients depend on the platform APIs. Ad-hoc changes caused regressions and unpredictable sunset timelines. We required a formal versioning policy that:

- Balances rapid SLO-driven fixes with customer compatibility.
- Establishes notification windows and sunset cadence.
- Aligns documentation (OpenAPI) with the deployed surface.
- Supplies tooling to detect breaking changes before merge.

## Decision

Adopt calendar-based versioning with a dual-track API lifecycle:

- **Monthly compatible release**: `YYYY-MM` header value. Batches additive fields/operations; backwards compatible by contract.
- **Major change window**: at most twice per year. Requires 90-day advance notice, migration guides, and deprecation headers.
- API responses include `X-uDocket-API-Version`, `Deprecation`, and `Sunset` headers when applicable (RFC 8594).
- OpenAPI specs (`ops/openapi/*.yaml`) are the single source of truth. `make lint-openapi` (Spectral) runs in CI to catch diff/compat issues.
- Breaking changes demand a new ADR plus Product & Security sign-off.

## Consequences

- Customers can pin to a monthly version by sending `X-uDocket-API-Version`. We support the last 6 monthly releases at any time.
- Sunsetting an endpoint requires: documentation update, migration guide link, deprecation headers, and sunset monitor in staging/prod.
- Engineering teams must update OpenAPI + changelog in the same PR as code changes.
- Releases carry automated verifiers (`tests/e2e/test_rate_limit_headers.py`, `spectral lint`) to guard the contract.
- Additional process overhead: change tickets with runtime validation, but we avoid uncontrolled drift and reduce support escalations.
