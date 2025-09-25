# uDocket — Accounts (Organizations/Users/Auth) Guide

Scope: `apps/platform/accounts/` (User/Organization models, OIDC auth, utils).

## Models
- `Organization` is a logical tenant; string `id` plus a generated `uid` for external mapping (apps/platform/accounts/models.py:14).
- `User` extends `AbstractUser` and stores Keycloak subject (`kc_sub`) plus optional `display_name`.
- `OrganizationMembership` grants roles within an organization.

## Auth & Org Resolution
- Use utilities under `apps.platform.accounts.utils` to resolve the active organization from session or headers before accessing case/job data.
- Middlewares manage org session and tie requests to tenants.

## Capabilities
- Authorization combines membership roles with preset/dynamic capabilities (apps/platform/authorization/capabilities.py:1). Never hardcode per‑view exceptions; ask for the relevant capability.

## Organization Settings
- Define per‑organization policy in a dedicated model (proposal):
  - Retention: transcript/analysis retention days, audit retention, auto‑purge flags
  - Artifact policy: hashing required (always on), approval requirements, destruction certificate policy
  - URL slug: canonical org slug used in URL prefixes (`/{org_slug}/...`)
- Deletion flows:
  - Support user‑initiated deletion requests via the portal (future); queue a policy‑aware task that enforces retention and writes a destruction certificate artifact.
  - All deletions append JSONL events and store a certificate artifact under `ops/`.
