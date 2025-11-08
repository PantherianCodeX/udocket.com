---
title: "uDocket — Ops Checklist: Production Overlay"
subtitle: "Keycloak proxy placement and operational runbook"
authors:
  - "Platform Operations Team"
version: "0.1-draft"
status: implementable
classification: Confidential
last_updated: "2025-11-02"
updated_by: "Platform Operations Team"
owners:
  - "Platform Operations Team"
reviewers:
  - "Platform Operations Team"
approvers:
  - "Operations Steering Committee"
approved_by:
approved_date:
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Platform Operations Team |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-11-02 |
| Updated by | Platform Operations Team |
| Owners | Platform Operations Team |
| Reviewers | Platform Operations Team |
| Approvers | Operations Steering Committee |
| Approved by |  |
| Approved date |  |
<!-- END AUTO-GENERATED: document-controls -->

______________________________________________________________________

## Overview

This checklist captures the minimum steps required to operate the production overlay (`docker-compose.prod.yml`). It emphasises Keycloak’s network placement, reverse-proxy expectations, and the health checks that accompany every deployment and on-call handoff.

Use this guide together with the stack Make targets and the service-specific runbooks in `docs/ops/runbooks.md`.

## Network & proxy placement

- **Keycloak remains internal**: the container listens on port `8085` inside the compose network. External traffic must terminate at the organisation’s front proxy (Nginx, Traefik, ALB, etc.) and be forwarded to the Keycloak service.
- **TLS terminates at the proxy**: do not expose port `8085` directly on the public internet. The proxy presents the certificate and forwards HTTPS → HTTP traffic over the internal bridge network.
- **Shared filesystem layout**: every service (platform web, worker, beat, docs toolbox, Keycloak) runs with `/udocket` as the working directory and mounts `/udocket/storage` to the same persistent volume. Verify custom overlays preserve those mount paths before deploying.

## Pre-deployment checklist

1. **Secrets & configuration**
   - Populate the production `.env` with database URLs, Keycloak admin credentials, storage endpoints, and Azure/LLM secrets.
   - Confirm `PLATFORM_BOOTSTRAP_ENABLED=0` and `RUN_PLATFORM_BOOTSTRAP=0` to avoid seeding demo data in production.
   - Provide Keycloak realm export files or automation tailored for the target organisation (seed scripts or API calls).
2. **Certificates & proxy rules**
   - Install or renew TLS certificates in the front proxy.
   - Map `/auth/*` and `/realms/*` routes to the Keycloak container while keeping `/` routed to the platform web service.
   - Apply HTTP → HTTPS redirects and ensure HSTS matches the organisation’s policy.
3. **Storage & backups**
   - Attach the persistent volume or NFS share to `/udocket/storage`.
   - Verify database backups (Postgres + Keycloak database) are scheduled and test an automated restore prior to go-live.
4. **Observability hooks**
   - Register stack logs with the central logging pipeline (e.g., ship `/var/log/containers/*.log` via Fluent Bit).
   - Ensure health checks exist for `https://<host>/readyz`, `https://<host>/synthetic/status`, and the Keycloak OpenID configuration endpoint.

## Post-deployment verification

Run these steps after each deployment or configuration change:

1. Bring the stack up with the overlay:

   ```bash
   PROJECT_NAME=udocket docker compose \
       -f docker-compose.yml \
       -f docker-compose.prod.yml \
       up -d
   ```

2. Confirm container health and port bindings:

   ```bash
   PROJECT_NAME=udocket make stack.prod.ps
   PROJECT_NAME=udocket make stack.smoke
   ```

3. Inspect logs for regressions (5–10 minutes tail):

   ```bash
   PROJECT_NAME=udocket make stack.prod.logs SERVICES="platform keycloak"
   PROJECT_NAME=udocket make stack.prod.logs SERVICES="platform_worker platform_beat"
   ```

4. Check Keycloak via the proxy and internally:

   ```bash
   curl -fsS https://<external-host>/realms/master/.well-known/openid-configuration
   docker compose -f docker-compose.yml exec keycloak \
     curl -fsS http://localhost:8085/realms/master/.well-known/openid-configuration
   ```

5. Validate platform routes and admin login through the proxy with a smoke-test account.

Record outcomes in the deployment log, including links to Grafana dashboards and Kibana searches used during verification.

## Ongoing operations

- **Daily checks**: `make stack.prod.ps`, review `platform` and `keycloak` log streams, confirm Keycloak token issuance by sampling `/realms/<realm>/.well-known/openid-configuration`.
- **Weekly tasks**: verify database backups complete, rotate Keycloak admin credentials, and export client configuration for disaster recovery.
- **Incident response**: for auth failures, collect the Keycloak pod logs, proxy access logs, and recent Keycloak events (`docker compose ... exec keycloak kc.sh show-events --days=1`). Reference the Guardian and Compose runbooks for downstream remediation.
- **Upgrades**: when bumping Keycloak versions, rehearse the migration in staging with the same front-proxy configuration before modifying production.

## Reference commands

| Purpose | Command |
| --- | --- |
| Start prod stack | `PROJECT_NAME=udocket docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` |
| Health snapshot | `PROJECT_NAME=udocket make stack.prod.ps` |
| Smoke check | `PROJECT_NAME=udocket make stack.smoke` |
| Tail logs | `PROJECT_NAME=udocket make stack.prod.logs SERVICES="platform keycloak"` |
| Restart Keycloak | `PROJECT_NAME=udocket docker compose restart keycloak` |
| Sync docs toolbox (optional) | `PROJECT_NAME=udocket docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm docs bash -lc "make docs.lint"` |

Keep this checklist in the on-call binder. Update the document after every production exercise or incident to reflect new learnings.
