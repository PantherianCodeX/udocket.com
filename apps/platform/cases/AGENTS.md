# uDocket — Cases (Domain & Membership) Guide

Scope: `apps/platform/cases/` (Case model, membership, case views/serializers).

## Domain Model
- `Case` captures matter metadata and ownership; history tracked via `simple_history`.
- Memberships (`CaseMembership`) control access; roles gate capabilities (OWNER/CONTRIBUTOR/CLIENT/REVIEWER...).

## Query Scoping
- Use `Case.objects.for_user(user)` which delegates to tenancy scoping.
- Views must resolve `active_org` and restrict to it. See view helpers under `apps.platform.ui.views.contexts` and tenancy.

## Mutations
- For reviewer/client assignment or title updates, check `user_can_review_case` or `has_capability` before writes.
- Prefer small, explicit view functions; push formatting to presenters in platform‑ui.

## Artifacts Integration
- Transcript and analysis artifacts link to `Case` via `case_id`. Do not write paths directly; use artifact helpers under UI or operations layer for promotion.

