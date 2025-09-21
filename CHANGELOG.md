# Changelog

## 2025-09-21

- added organization-aware admin controls including session-scoped org selector and guarded querysets
- refactored authorization models to use per-organization names with UUID identifiers and introduced client-facing role preset
- extended field visibility controls to support case metadata alongside artifacts and tightened serializers to respect new policies
- enriched account administration with tenant-ready user creation wizard, organization metadata, and shared helpers
- expanded test coverage and data migrations to support the updated RBAC and visibility model
