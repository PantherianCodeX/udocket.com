uDocket Platform Roadmap — Option 3 (Django Consolidation)

Context
- The repository now ships the Django platform (`apps/platform`) Artifacts continue to live under `storage/media/cases/<CASE_ID>/...` on disk while Postgres stores metadata (`cases`, `jobs`, etc.).

Target End State (Option 3)
- A single Django 4.2 LTS project providing both admin UI and public APIs (via Django REST Framework) with asynchronous updates delivered through Django Channels.
- Authentication and session management delegated to an external IAM (Keycloak on Azure) using OpenID Connect for the browser/admin UI and bearer‑token validation for the APIs.
- A centralized authorization layer powered by Oso (Polar policies) backed by our capability catalog, replacing ad-hoc checks while preserving defense-in-depth with Postgres row-level security.
- A normalized relational schema that captures core case workflow plus extensible artifacts (summaries, timelines, relationship graphs, exhibits, etc.) while retaining the existing on‑disk storage contract for binary artifacts.
- Background processing (transcription/analysis) executed as Django‑managed Celery workers that call the importable `TranscriptionAgent` interface.

Implementation Roadmap
1) Repository Preparation
   - Create a new Django project under `apps/platform/` (done)
   - Maintain the root `manage.py`, `apps/platform/config/` settings package, and Django apps (`accounts`, `cases`, `artifacts`, `operations`, etc.).

2) Dependencies & Tooling
   - Update requirements to include: Django 4.2, django‑environ, djangorestframework, drf‑spectacular, django‑filter.
   - Authorization: `oso`, `django-oso` (primary policy runtime), retain `django-guardian` only for legacy compatibility during migration.
   - IAM/SSO: `mozilla-django-oidc` (or `python-keycloak` + `django-keycloak-auth`) for Keycloak SSO; pair with `djangorestframework-simplejwt[crypto]` for validating API tokens.
   - Realtime: `channels` 4, `channels-redis`, `asgiref`, Redis.
   - Background: Celery, `django-celery-beat`, `django-celery-results`.
   - Integrity/audit helpers: `django-auditlog`, `django-simple-history`, `django-cleanup`, `django-anymail` (if notifications), `django-axes`.
   - Testing: pytest, pytest‑django, factory‑boy, model‑bakery, pytest‑asyncio.
   - Dev quality gates: mypy, django‑stubs, flake8, black, bandit, django‑upgrade.

3) Django Project & Settings
   - Run `django-admin startproject udocket_platform apps/platform` and configure `apps/platform/config/settings/` with `base.py`, `dev.py`, `prod.py`.
   - Use `django-environ` to load `.env` values; reuse existing environment variables where possible (`DATABASE_URL`, storage paths, etc.).
   - Enforce security defaults: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `CSRF_TRUSTED_ORIGINS`, `SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`.
   - Configure `INSTALLED_APPS` with Django core apps, DRF, Channels, and the custom apps.
   - Set `AUTH_USER_MODEL = "accounts.User"` to store Keycloak UUIDs and local profile data.
   - Define `ASGI_APPLICATION = "config.asgi.application"` and configure Channels routing.

4) Database Design
   - Replace the legacy schema with these core models (build with migrations):
     - `accounts.User`: Keycloak subject ID, email, display name, staff flags, status, MFA requirements, timestamps.
     - `accounts.Organization`: ManyToMany between users and organizations with role metadata.
     - `cases.Case`: owner organization, status, retention dates, classification level.
     - `cases.CaseMembership`: associates users with cases and roles (e.g., owner, contributor, reviewer, auditor); integrate with `django-guardian` for object‑level permissions.
     - `jobs.Job`: agent type, status, payload metadata, `storage_key`.
     - `artifacts.CaseArtifact`: generic artifact table with fields (id, case, job, type, title, description, path, checksum, schema_version, created_by, created_at, metadata JSONField). Provide typed proxy models per artifact flavor.
     - `operations.AuditEvent`: captures read/write events, policy evaluations, and agent runs.
     - `operations.TaskRun`: tracks Celery executions (tie back to jobs).
   - Ensure referential integrity via `on_delete=PROTECT` where necessary; add DB‑level unique constraints and indexes (e.g., `(case, type, title)`).
   - Use Postgres JSONB for flexible artifact metadata while keeping searchable columns normalized.
   - Implement Simple History or Auditlog on critical models (Case, CaseMembership, CaseArtifact) for versioning and tamper detection.

5) Authentication & IAM Integration
   - Provision Keycloak realm, clients, and roles for the MVP (Azure-managed Postgres backend, Keycloak Operator on AKS).
   - Configure Django to use OIDC:
     - Browser sessions: integrate `mozilla-django-oidc` for login/logout. Map Keycloak roles/groups to local Role bindings and feed them into Oso context.
     - API access: configure DRF authentication classes to validate JWT access tokens from Keycloak using SimpleJWT with remote JWKs.
     - Service-to-service: create Keycloak service accounts for agents/workers and store credentials in Azure Key Vault.
   - Middleware syncs Keycloak claims (roles, groups, MFA status) into local User and CaseMembership on each login so Polar policies can evaluate up-to-date membership.
   - Enforce session timeout, reauth, and CSRF; rely on Keycloak for MFA/policy but add `django-axes` as fallback if local login ever enabled.
   - During transition, keep legacy FastAPI login surfaces read-only and plan their removal once Django/Oso parity is achieved.

6) Authorization Overhaul (High Security / High Isolation)
   - Introduce `django-oso`; register Case, Job, Artifact, Organization, Role, and PermissionPreset models for policy evaluation and expose helper functions (e.g., `has_capability`) to Polar.
   - Author Polar policies that encode CRUD, download, review, and timeline actions plus `allow_field` rules for sensitive attributes (checksums, transcript hashes, notes) with default-deny posture.
   - Replace DRF permission classes with an Oso-backed implementation, wrap serializers and Django admin forms with mixins that enforce `allow_field` decisions, and guard artifact downloads/exports via explicit `oso.authorize` checks.
   - Keep Postgres row-level security enabled; extend the existing `enable_rls` management command to apply `FORCE ROW LEVEL SECURITY` and include new tables introduced during the migration.
   - Emit structured audit events for each policy decision (allow/deny) and surface them in the operations app for compliance reviews.

7) Admin Experience & Preset Consolidation
   - Update `UserAdmin` to assign roles per organization (leveraging inlines) and show effective capabilities; update `RoleAdmin` to display linked users and organization scope.
   - Merge the legacy “group” concept into permission presets so admins manage a single entity; build a capability composer widget (object → action → field) to generate capability strings without manual typing.
   - Refresh the `/permissions/` catalog page to read effective permissions through Oso, highlighting field visibility rules and preset provenance for auditability.
   - Add change-history logging for Role/PermissionPreset edits using `django-simple-history` or `django-auditlog` to prove who modified policies.

8) API & Admin Surface
   - Implement DRF viewsets for Case, Job, CaseArtifact, CaseMembership under `/api/v1/`.
   - Provide serializers that surface only allowed fields; add nested serializers for artifacts.
   - Expose endpoints for uploading audio, triggering agents, downloading transcripts; keep storage paths compatible (`storage/media/cases/<CASE_ID>/...`).
   - Use Django admin (hardened with `django-admin-honeypot`, `django-admin-ip-restrictor`) for ops tasks; customize dashboards to show case status, audit events, and artifact history.
   - Optional: server-rendered templates for custom admin UI pages (Django templates + HTMX).

9) Real-Time Updates with Channels
   - Configure Redis (Azure Cache for Redis) as the Channels layer.
   - Routing:
     - Case room updates (`cases/<case_id>`),
     - Job progress (`jobs/<job_id>`),
     - Artifact updates (`cases/<case_id>/artifacts`).
   - Use Celery task signals to push WebSocket messages when job status or artifacts change.
   - Frontend (admin UI): consume Channels via JS and refresh views in real time.
   - Authenticate Channels using the same OIDC session; validate permissions before group subscription.

10) Background Processing & Agent Integration
   - Replace the legacy `apps/worker` process with the Django `operations` app containing Celery tasks (complete).
   - Task to launch transcription agent via existing CLI (subprocess), capturing stdout JSON and logs.
   - Tasks for future analysis agents (summary, timeline, relationships) using the documented agent contract.
   - Configure Celery with Redis or Azure Service Bus as broker; store results in Postgres with `django-celery-results`.
   - Ensure tasks write outputs to the same file layout; register new `CaseArtifact` entries when new files appear.
   - Provide admin commands (`manage.py sync_legacy_cases`) to migrate existing jobs/cases.

11) Storage & Media Handling
   - Keep `storage/media/cases/<CASE_ID>/...` directory conventions unchanged for compatibility.
   - Wrap file interactions with Django’s `FileSystemStorage` pointing to `MEDIA_ROOT` (`/app/storage/media` by default).
   - Compute SHA‑256 for each artifact file and store it on `CaseArtifact.checksum`.
   - Optional: publish artifacts to Azure Blob Storage using SAS tokens aligned with current conventions.

12) Testing & Quality Gates
   - Port FastAPI tests to DRF (APITestCase / pytest) covering auth flows, permissions, and field redaction.
   - Add contract tests verifying agent CLI output parsing, artifact creation, and field‑level policies.
   - Add async tests for Channels consumers (pytest‑asyncio).
   - Integrate static analysis (mypy, black, flake8, bandit) and run in CI.
   - Create load/perf tests to validate Channels and API scaling on Azure.

13) Deployment Updates
   - Update Dockerfiles in `infra/docker/` to build the Django image (gunicorn + uvicorn workers for ASGI) with multi‑stage builds.
   - Modify `docker-compose.yml` to include Django ASGI service, Celery worker, Celery beat, Redis.
   - Azure production:
     - Deploy Django ASGI app on AKS or Azure App Service for Containers.
     - Use Azure Postgres Flexible Server, Azure Cache for Redis.
     - Store secrets in Azure Key Vault; mount via CSI.
     - Set up CI to run tests, build images, push to ACR, and deploy via Helm/Bicep.
     - Configure Keycloak as managed AKS deployment and integrate with Azure AD for SSO if required.

14) Documentation & Handover
   - Update `README.md` and create developer docs describing the new architecture, IAM integration, and deployment.
   - Document the data model (ER diagrams), permission matrices, Channels event contracts, Celery task flow, and Keycloak realm configuration.
   - Provide runbooks for onboarding, rotating secrets, audit requests, and disaster recovery.

Progress To Date
- Consolidation has been in progress since commit `6d5fc0630fea1ce9feac36445eadf775880e6c51`.
- Provenance (history): enabled `django-simple-history` and integrated with admin for Cases and Artifacts.
- Configurable RBAC scaffolding: Role and RoleCapability models, capability resolver, and seeded default roles; admin page for Effective Capabilities.
- Stability and resilience improvements: AccessPolicy fallback, resilient migrations in `artifacts`.
- Case insights: Django UI now consumes DRF telemetry endpoints (`/api/v1/jobs/<id>/detail/`, `/api/v1/cases/<id>/jobs/summary|detail/`) to surface per-job diagnostics, transcript artifacts, and modal drill-downs sourced from ops metadata.
- Next slices under consideration:
  - Create and apply migrations for `simple_history` changes; admin filters for user/date/action.
  - Expand tests for capability resolution, policies, field-level redaction, and TaskRun lifecycle.
  - IAM wiring (Keycloak OIDC + API JWT validation) and role mapping on login.
  - Admin guardrails: allow-listed capability choices; read-only API for effective capabilities.
  - Agents/LLM: untangle Azure-only dependencies in summarization so stage providers can invoke configured non-Azure chat adapters (TODO — requires shared client abstraction).

Cross‑References
- Agents contract and analysis roadmap: see `AGENTS.md`.
