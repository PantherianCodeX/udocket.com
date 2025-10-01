# uDocket — Authorization (Roles/Capabilities) Guide

Scope: `apps/platform/authorization/` (roles, presets, capability checks).

## Capabilities
- Default role → capabilities mapping lives in `capabilities.py` with DB overrides via Roles/Presets.
- Always use `has_capability(user, case_id, "cap.name")` in views and tasks that enforce permissions.

## Organization Context
- Capability resolution can include organization scoping; pass `organization_id` where required.
- Case membership (`CaseMembership`) is the primary bridge from user to case.

## Extending
- Add new capabilities to defaults only if broadly applicable; otherwise, use PresetCapability rows and RoleCapability relations.
- Update UI affordances to hide actions where capability is absent.

