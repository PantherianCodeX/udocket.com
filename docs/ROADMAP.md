uDocket Platform Roadmap — Option 3 (Django Consolidation)

Context
- The repository now ships the Django platform (`apps/platform`) Artifacts continue to live under `storage/media/cases/<CASE_ID>/...` on disk while Postgres stores metadata (`cases`, `jobs`, etc.).

Target End State (Option 3)
- A single Django 5.2 LTS project providing both admin UI and public APIs (via Django REST Framework) with asynchronous updates delivered through Django Channels.
- Authentication and session management delegated to an external IAM (Keycloak on Azure) using OpenID Connect for the browser/admin UI and bearer‑token validation for the APIs.
- A centralized authorization layer powered by Oso (Polar policies) backed by our capability catalog, replacing ad-hoc checks while preserving defense-in-depth with Postgres row-level security.
- A normalized relational schema that captures core case workflow plus extensible artifacts (summaries, timelines, relationship graphs, exhibits, etc.) while retaining the existing on‑disk storage contract for binary artifacts.
- Background processing (transcription/analysis) executed as Django‑managed Celery workers that call the importable `TranscriptionAgent` interface.

Implementation Roadmap
All roadmap slices must maintain or improve our strong typing baseline—see `docs/typing_refactor_plan.md` before tackling any refactor or new feature.
1) Repository Preparation
   - Create a new Django project under `apps/platform/` (done)
   - Maintain the root `manage.py`, `apps/platform/config/` settings package, and Django apps (`accounts`, `cases`, `artifacts`, `operations`, etc.).

2) Dependencies & Tooling
   - Update requirements to include: Django 5.2, django‑environ, djangorestframework, drf‑spectacular, django‑filter.
   - Authorization: `oso`, `django-oso` (primary policy runtime); keep `django-guardian` only if object-level fallback remains required.
   - IAM/SSO: `mozilla-django-oidc` (or `python-keycloak` + `django-keycloak-auth`) for Keycloak SSO; pair with `djangorestframework-simplejwt[crypto]` for validating API tokens.
   - Realtime: `channels` 4, `channels-redis`, `asgiref`, Redis.
   - Background: Celery, `django-celery-beat`, `django-celery-results`.
   - Integrity/audit helpers: `django-auditlog`, `django-simple-history`, `django-cleanup`, `django-anymail` (if notifications), `django-axes`.
   - Testing: pytest, pytest‑django, factory‑boy, model‑bakery, pytest‑asyncio.
   - Dev quality gates: mypy, django‑stubs, flake8, black, bandit, django‑upgrade.
   - Strong typing program: adhere to `docs/typing_refactor_plan.md`; refactors must not regress mypy/pyright and should chip away at the remaining errors.

3) Django Project & Settings
   - Run `django-admin startproject udocket_platform apps/platform` and configure `apps/platform/config/settings/` with `base.py`, `dev.py`, `prod.py`.
   - Use `django-environ` to load `.env` values; reuse existing environment variables where possible (`DATABASE_URL`, storage paths, etc.).
   - Enforce security defaults: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `CSRF_TRUSTED_ORIGINS`, `SECURE_HSTS_SECONDS`, `SECURE_CONTENT_TYPE_NOSNIFF`.
   - Configure `INSTALLED_APPS` with Django core apps, DRF, Channels, and the custom apps.
   - Set `AUTH_USER_MODEL = "accounts.User"` to store Keycloak UUIDs and local profile data.
   - Define `ASGI_APPLICATION = "config.asgi.application"` and configure Channels routing.

4) Database Design
   - Replace the prior schema with these core models (build with migrations):
     - `accounts.User`: Keycloak subject ID, email, display name, staff flags, status, MFA requirements, timestamps.
     - `accounts.Organization`: ManyToMany between users and organizations with role metadata.
     - `cases.Case`: owner organization, status, retention dates, classification level.
     - `cases.CaseMembership`: associates users with cases and roles (e.g., owner, contributor, reviewer, auditor); integrate with `django-guardian` for object‑level permissions.
     - `jobs.Job`: agent type, status, payload metadata, `storage_key`.
     - `artifacts.CaseArtifact`: generic artifact table with fields (id, case, job, type, title, description, path, checksum, schema_version, created_by, created_at, metadata JSONField). Provide typed proxy models per artifact flavor.
     - `operations.AuditEvent`: captures read/write events, policy evaluations, and agent runs.
   - Ensure referential integrity via `on_delete=PROTECT` where necessary; add DB‑level unique constraints and indexes (e.g., `(case, type, title)`).
   - Use Postgres JSONB for flexible artifact metadata while keeping searchable columns normalized.
   - Implement Simple History or Auditlog on critical models (Case, CaseMembership, CaseArtifact) for versioning and tamper detection.

5) Authentication & IAM Integration
   - Provision Keycloak realm, clients, and roles for the MVP (Azure-managed Postgres backend, Keycloak Operator on AKS).
   - Configure Django to use OIDC:
   - Browser sessions: integrate `mozilla-django-oidc` for login/logout. Map Keycloak organization roles to local Role bindings and feed them into Oso context.
     - API access: configure DRF authentication classes to validate JWT access tokens from Keycloak using SimpleJWT with remote JWKs.
     - Service-to-service: create Keycloak service accounts for agents/workers and store credentials in Azure Key Vault.
   - Middleware syncs Keycloak claims (organization memberships, case membership ids/roles, MFA status) into local User and CaseMembership on each login so Polar policies can evaluate up-to-date membership.
   - Enforce session timeout, reauth, and CSRF; rely on Keycloak for MFA/policy but add `django-axes` as fallback if local login ever enabled.

6) Authorization Overhaul (High Security / High Isolation)
   - Introduce `django-oso`; register Case, Job, Artifact, Organization, Role, and PermissionPreset models for policy evaluation and expose helper functions (e.g., `has_capability`) to Polar.
   - Author Polar policies that encode CRUD, download, review, and timeline actions plus `allow_field` rules for sensitive attributes (checksums, transcript hashes, notes) with default-deny posture.
   - Replace DRF permission classes with an Oso-backed implementation, wrap serializers and Django admin forms with mixins that enforce `allow_field` decisions, and guard artifact downloads/exports via explicit `oso.authorize` checks.
   - Keep Postgres row-level security enabled; extend the existing `enable_rls` management command to apply `FORCE ROW LEVEL SECURITY` and include new tables introduced during the migration.
   - Emit structured audit events for each policy decision (allow/deny) and surface them in the operations app for compliance reviews.

7) Admin Experience & Preset Consolidation
   - Update `UserAdmin` to assign roles per organization (leveraging inlines) and show effective capabilities; update `RoleAdmin` to display linked users and organization scope.
   - Merge the historical “group” concept into permission presets so admins manage a single entity; build a capability composer widget (object → action → field) to generate capability strings without manual typing.
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
   - Replace the old `apps/worker` process with the Django `operations` app containing Celery tasks (complete).
   - Task to launch transcription agent via existing CLI (subprocess), capturing stdout JSON and logs.
   - Tasks for future analysis agents (summary, timeline, relationships) using the documented agent contract.
   - Configure Celery with Redis or Azure Service Bus as broker; store results in Postgres with `django-celery-results`.
   - Ensure tasks write outputs to the same file layout; register new `CaseArtifact` entries when new files appear.
   - Provide admin commands (`manage.py sync_legacy_cases`) to migrate existing jobs/cases from the retired API.

11) Storage & Media Handling
   - Keep `storage/media/cases/<CASE_ID>/...` directory conventions unchanged for compatibility.
   - Wrap file interactions with Django’s `FileSystemStorage` pointing to `MEDIA_ROOT` (`/app/storage/media` by default).
   - Compute SHA‑256 for each artifact file and store it on `CaseArtifact.checksum`.
   - Optional: publish artifacts to Azure Blob Storage using SAS tokens aligned with current conventions.

12) Testing & Quality Gates
   - Expand DRF tests (APITestCase / pytest) covering auth flows, permissions, and field redaction.
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
- Authentication experience: `/login/` now serves a branded welcome screen with SSO entry points, and post-login flows enforce an organization chooser with automatic selection when only one workspace is available.
- Dashboard foundation: the cases landing page has been rebuilt around configurable widgets (metrics, case table, job summary, deadlines, case creation) so organizations can layer on custom analytics and layouts.
- Next slices under consideration:
  - Create and apply migrations for `simple_history` changes; admin filters for user/date/action.
  - Expand tests for capability resolution, policies, and field-level redaction.
  - IAM wiring (Keycloak OIDC + API JWT validation) and role mapping on login.
  - Admin guardrails: allow-listed capability choices; read-only API for effective capabilities.
  - Agents/LLM: extend shared chat client runtime as new providers are onboarded (ensure tests cover non-Azure adapters).
    - TODO: implement first-class chat clients for AWS Bedrock and Google Gemini providers in `packages/udocket_core/llm/runtime.py` so organization configs can activate them without Azure-specific fallbacks.


Compose + Review & Edit Program (New)
- Goal: unify final document assembly and review, migrate timeline/graph into Compose, and standardize approvals + artifact versioning.
- Milestones:
  1) Compose Agent (target="compose")
     - Implement Compose pipeline (LLM-only) that consumes: summary.json, timeline JSON, graph JSON, intake, and attached artifacts (letters, statements, forms).
     - Stages: input discovery → context builder → timeline (LLM) → graph (LLM) → drafting (audience variants: client grade-6 voice; lawyer professional) → QA & finalize → render (Markdown + DOCX) → ops/audit.
     - Artifacts: `<job>__compose_client_v1.md/.docx`, `<job>__compose_lawyer_v1.md/.docx`; embed timeline/graph SVG/PNG; link JSON in ops.
     - Templates: per-organization DOCX template with uDocket default fallback; configurable in Org Settings.
  2) Migrate Timeline/Graph into Compose
     - Remove timeline/graph generation from Analyze; Compose owns LLM timeline/graph sub-stages and their outputs (`timeline_v2.json/html/png`, `graph_v2.json/html/png`).
     - Keep existing Timeline/Graph tasks as thin wrappers that delegate to Compose sub-stages (optional; may be removed once UI is switched).
  3) Approvals & Versioning
     - Manual Edit tool: creates a child job action on save, writes a new versioned artifact with diff metadata; requires Reviewer approval. Approval promotes the new version to the parent task’s current output.
     - Agent Edit tool: interactive chat editor that modifies artifacts via prompts; identical approval/versioning semantics.
     - Configurable reviewer policy: required reviewer count and allowed roles per page/tool, set in Org Settings; defaults seeded from file.
     - Modal text viewer: standard version history access (browse/compare) for all text artifacts.
  4) Parent/Child Job Actions
     - Parent rows represent a tool (Transcribe, Analyze, Compose); children represent steps (e.g., Upload → Convert → Transcribe Agent → Manual Edit).
     - Parent status reflects the next blocking child action; cancelled children are skipped.


Analyze Enhancements (LLM-only)
- Deliverables: standardize mandatory sections across outputs, including a Staff Report.
- Staff Report: gaps/flags/discrepancies; questionnaire completion score; next steps. Stored as `analysis/<job>__staff_report_v1.md` + JSON payload.
- Discrepancy detection: compare all intake/case fields to transcript; categorize severity and emit alerts.
- Speaker mapping proposals: propose role/identity per speaker; UI modal for approval; approved changes back-propagate to case metadata (always require confirmation).
- Remove timeline/graph seeding from Analyze (moved to Compose).


Questionnaire & Interview Guidance
- Questionnaire Tool (Intake panel)
  - Common LLM tool panel with jobs list + Manual Edit; generate questionnaire from intake and per-org question seeds/forms; store as Markdown; compute a transcript completion score.
  - Seed files: per-org base questions + default seed for new orgs.
- Interview Page
  - Per-case central hub with live checklist (consent/content), notes, call start/end logging, links to questionnaire/intake/artifacts; multiple sessions supported; append minimal ops JSONL audit lines.


Alerts System (LLM-controllable)
- Alert tool available to LLMs and staff: fields include severity (info/warn/critical), category, message, suggested action.
- Visibility: case banner + Alerts tab; acknowledgement system out of scope for now; record creation in ops JSONL.
- Org Settings: thresholds and behavior per severity, file-driven defaults.


Org & User UX Improvements
- Sign-in & branding: extend the new welcome/sign-in page with per-organization theming assets; document where brand files live; keep default theme colors configurable per org.
- Org selection: continue hardening edge cases (e.g., websocket reconnects) now that the chooser gate auto-selects single-org members.
- Org settings: DOCX templates, data retention, default LLM configs, reviewer policies, questionnaire seeds, permissions config, org profile.
- User profile: view/edit profile, password/MFA/preferences.


LLM Execution Policy & Regions
- LLM-only generation: remove local/offline fallbacks for content; fail fast with descriptive errors on missing credentials or capacity.
- Region policy: keep Canada-only Azure default for now; add TODO to design cross-provider region enforcement that’s adjustable per org.


Data Retention & Deletion Certificates
- Default retention 90 days (file-driven defaults). Per-org settings by artifact class (audio, transcripts, analysis, composed docs, logs).
- Early deletion: requires two-party confirmation (client + reviewer). Always produce a deletion certificate artifact for any removal, including maintenance.
- Backups: purge deleted data from backups; make purge behavior configurable in backup settings; TODO: define what to anonymize vs. delete.
- Audit logs: independent retention settings per org; deletion certificate also required if purged.


Seeds & Defaults (File-driven)
- Maintain default seed files for: roles (including Reviewer), LLM stage maps by target, reviewer policy, template selection, alert thresholds, data retention, questionnaire seeds, branding/theme.
- Roadmap item: bootstrap new orgs from these defaults and expose them in Org Settings for later adjustment.

Cross‑References
- Agents contract and analysis roadmap: see `AGENTS.md`.
