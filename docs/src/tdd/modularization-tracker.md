---
title: "TDD Modularization Tracker"
status: draft
classification: Internal
last_updated: 2025-10-25
---

# TDD Modularization Plan Tracker

This tracker grounds the execution plan for refactoring `docs/src/tdd/TDD.md` into modular service specifications, appendices, and diagrams. Use it to coordinate work, record decisions, and avoid duplicate effort. Update statuses as tasks move forward; add links to supporting PRs or ADRs when work lands.

## Legend

- ✅ Completed
- ⏳ In progress or partially completed
- ⛔ Not started / blocked

## Phase Snapshot

| Phase | Overall status | Highlights |
|-------|----------------|------------|
| Phase 0 — Groundwork | ⏳ | Doc CI is live (`.github/workflows/docs-ci.yml`); directory layout decision and scaffolding remain unfinished. |
| Phase 1 — OPA into `tdd-lpe.md` | ⏳ | LPE doc hosts a full OPA section (`docs/src/services/lpe.md:294`); `TDD.md` still contains deep OPA detail such as FIPS enforcement notes (`docs/src/tdd/TDD.md:1949`). |
| Phase 2 — Modularize services/apps | ⏳ | Guardian, Settings Registry, Reference Manager, and LPE docs exist; other services/apps still rely on `TDD.md`. |
| Phase 3 — De-duplicate & centralize | ⛔ | Appendix layout only covers glossary/status tables; interface index and shared table migration remain open. |
| Phase 4 — Diagrams | ✅ | Required Mermaid sources live under `docs/src/tdd/appendices/diagrams/` (e.g., `system-context-v1.mmd`, `signing-delivery-v1.mmd`). |
| Phase 5 — Compliance & policy clarity | ⛔ | Binding/normative labeling still inconsistent across service docs and TDD sections. |
| Phase 6 — CI & contributor experience | ⏳ | Docs CI and contributor guide exist; CODEOWNERS still missing. |
| Phase 7 — PRs, review, release | ⛔ | No workstreams split into reviewable PRs yet. |

---

## Phase 0 — Groundwork

- ⛔ Create “Docs Work” branch `docs/refactor-tdd-modularization` — current local branches do not include the requested name (`git branch` output; active branch `docs/stack`).
- ⛔ Freeze current `docs/src/tdd/TDD.md` and dependent service docs for diffing — no scratch exports committed.
- ⏳ Decide directory layout — `docs/mkdocs.yml` routes to `docs/src/services/*` and `docs/src/tdd/*`, but planned targets like `docs/src/services/digital-signer.md` and `docs/src/apps/` are absent.
- ⏳ Adopt uniform service-spec scaffold — Guardian (`docs/src/services/guardian.md`) follows the template, yet newer files (for example, `docs/src/services/lpe.md`, `docs/src/services/settings-registry.md`) still lack the explicit canonical banner language and some sections omit the Purpose/Contract scaffold.
- ✅ Add CI doc checks (markdownlint, link checker, Mermaid render, optional Vale) — enforced via `.github/workflows/docs-ci.yml` and `docs-validation.yml`.

---

## Phase 1 — Move OPA into `tdd-lpe.md`

- ⏳ Identify OPA content in `TDD.md` — significant implementation detail remains (e.g., signature enforcement at `docs/src/tdd/TDD.md:1949` and policy escalation guards at `docs/src/tdd/TDD.md:1698`).
- ✅ Port detailed OPA content into `docs/src/services/lpe.md` — see §3.1 (`docs/src/services/lpe.md:294`).
- ⛔ Replace `TDD.md` sections with concise pointers — deep sections still inline across §8 and §12 (`docs/src/tdd/TDD.md:270`, `docs/src/tdd/TDD.md:463`).
- ⛔ Update cross-references/anchors — other docs still reference `TDD` sections instead of `services/lpe.md`.
- ✅ ADR capturing ownership — `docs/src/adr/ADR-0005-opa-policy-plane.md` is in place.

---

## Phase 2 — Modularize remaining services/apps

### Guardian

| Task | Status | Notes |
|------|--------|-------|
| Dedicated doc using scaffold | ✅ | `docs/src/services/guardian.md` |
| Remove deep Guardian detail from `TDD.md` | ⛔ | Guardian-specific tables and prose remain (`docs/src/tdd/TDD.md:5xx` range). |
| Canonical banner inserted | ✅ | “This specification is the canonical source…” (`docs/src/services/guardian.md:344`). |
| `TDD.md` reduced to summary + link | ⛔ | Longform Guardian content persists in §5 and §7. |
| Shared tables moved to appendices | ⏳ | Status mapping lives in `docs/src/tdd/appendices/status-mapping.md`, but Guardian remediation tables still in TDD. |

### Digital Signer

| Task | Status | Notes |
|------|--------|-------|
| Dedicated doc using scaffold | ⛔ | Missing (`docs/src/services/digital-signer.md` not present). |
| Remove deep Signer detail from `TDD.md` | ⛔ | Signer flows remain embedded in TDD §7. |
| Canonical banner inserted | ⛔ | Blocked until doc exists. |
| `TDD.md` reduced to summary + link | ⛔ | Pending doc creation. |
| Shared tables moved to appendices | ⛔ | Pending doc creation. |

### Settings Registry

| Task | Status | Notes |
|------|--------|-------|
| Dedicated doc using scaffold | ✅ | `docs/src/services/settings-registry.md` |
| Remove deep SR detail from `TDD.md` | ⛔ | TDD retains activation and telemetry walkthroughs (§9). |
| Canonical banner inserted | ⛔ | Missing explicit “canonical source” statement. |
| `TDD.md` reduced to summary + link | ⛔ | Content unchanged in §9. |
| Shared tables moved to appendices | ⏳ | Key tables still co-reside in TDD. |

### LLM Registry

| Task | Status | Notes |
|------|--------|-------|
| Dedicated doc using scaffold | ⛔ | File absent (`docs/src/services/llm-registry.md`). |
| Remove deep Registry detail from `TDD.md` | ⛔ | Detailed registry pipelines remain in §8. |
| Canonical banner inserted | ⛔ | Blocked until doc exists. |
| `TDD.md` reduced to summary + link | ⛔ | Pending doc creation. |
| Shared tables moved to appendices | ⛔ | Pending doc creation. |

### Localization & Policy Engine (LPE)

| Task | Status | Notes |
|------|--------|-------|
| Dedicated doc using scaffold | ✅ | `docs/src/services/lpe.md` |
| Remove deep LPE detail from `TDD.md` | ⛔ | Extensive runtime notes still reside in §8 (`docs/src/tdd/TDD.md:270`, `docs/src/tdd/TDD.md:3220`). |
| Canonical banner inserted | ⛔ | Lacks explicit canonical language near top. |
| `TDD.md` reduced to summary + link | ⛔ | TDD still narrates residency and policy internals. |
| Shared tables moved to appendices | ⏳ | Some migration occurs; remaining matrices still within TDD. |

### Reference Manager

| Task | Status | Notes |
|------|--------|-------|
| Dedicated doc using scaffold | ✅ | `docs/src/services/reference-manager.md` |
| Remove deep RM detail from `TDD.md` | ⛔ | TDD maintains catalog and checksum sections (§9/§10). |
| Canonical banner inserted | ⛔ | Document lacks explicit canonical notice. |
| `TDD.md` reduced to summary + link | ⛔ | TDD continues to host reference ingest steps. |
| Shared tables moved to appendices | ⏳ | Jurisdiction tables still duplicated. |

### Notifications Service

| Task | Status | Notes |
|------|--------|-------|
| Dedicated doc using scaffold | ⛔ | File absent (`docs/src/services/notifications.md`). |
| Remove deep Notifications detail from `TDD.md` | ⛔ | Queues and retry tables live in §10. |
| Canonical banner inserted | ⛔ | Blocked until doc exists. |
| `TDD.md` reduced to summary + link | ⛔ | Pending doc creation. |
| Shared tables moved to appendices | ⛔ | Pending doc creation. |

### Web App

| Task | Status | Notes |
|------|--------|-------|
| Dedicated doc using scaffold | ⛔ | `docs/src/apps/web-app.md` not present. |
| Remove deep Web App detail from `TDD.md` | ⛔ | UI/portal narratives still in §11. |
| Canonical banner inserted | ⛔ | Blocked until doc exists. |
| `TDD.md` reduced to summary + link | ⛔ | Pending doc creation. |
| Shared tables moved to appendices | ⛔ | Pending doc creation. |

### Worker Cluster

| Task | Status | Notes |
|------|--------|-------|
| Dedicated doc using scaffold | ⛔ | `docs/src/apps/worker-cluster.md` not present. |
| Remove deep Worker detail from `TDD.md` | ⛔ | Worker orchestration still in §12. |
| Canonical banner inserted | ⛔ | Blocked until doc exists. |
| `TDD.md` reduced to summary + link | ⛔ | Pending doc creation. |
| Shared tables moved to appendices | ⛔ | Pending doc creation. |

### LLM Agents

| Task | Status | Notes |
|------|--------|-------|
| Dedicated doc using scaffold | ⛔ | `docs/src/services/llm-agents.md` not present. |
| Remove deep Worker detail from `TDD.md` | ⛔ | Worker orchestration still in §12. |
| Canonical banner inserted | ⛔ | Blocked until doc exists. |
| `TDD.md` reduced to summary + link | ⛔ | Pending doc creation. |
| Shared tables moved to appendices | ⛔ | Pending doc creation. |

---

## Phase 3 — De-duplicate & centralize

- ⏳ Create canonical appendices — Glossary and status mapping exist (`docs/src/tdd/appendices/glossary.md`, `docs/src/tdd/appendices/status-mapping.md`), yet architecture maps, interface index, and additional shared tables remain to be carved out.
- ⛔ Repo-wide deduplication — `TDD.md` still duplicates residency, Guardian, and pipeline content that now lives (or should live) in service docs.
- ⛔ Normalize section labels/link style — Mixed usage of `§` references vs inline hyperlinks persists.
- ⛔ Dead link & drift check after dedup — To be re-run post-migration; current CI passes but content parity not achieved.

---

## Phase 4 — Diagrams

- ✅ System context/container diagram — `docs/src/tdd/appendices/diagrams/system-context-v1.mmd` (rendered SVG referenced in `docs/src/tdd/TDD.md:326`).
- ✅ Artifact lifecycle set — `artifact-lifecycle-overview-v1.mmd`, `artifact-wp-lifecycle-v1.mmd`, `artifact-cd-lifecycle-v1.mmd`.
- ✅ Residency & policy enforcement — `residency-policy-enforcement-v1.mmd`.
- ✅ Digital signing & delivery — `signing-delivery-v1.mmd`.
- ✅ LLM failover orchestrator — `llm-failover-v1.mmd`.

---

## Phase 5 — Compliance & policy clarity

- ⛔ Tag binding/normative/informative sections consistently — Many service docs (e.g., `docs/src/services/reference-manager.md`) lack explicit tags.
- ⛔ Add illustrative policy examples — Pending across Guardian/LPE docs.
- ⛔ SME review pass — Awaiting document migration completion.

---

## Phase 6 — CI hardening & contributor experience

- ✅ Enforce docs CI on PRs — Workflows `docs-ci.yml`, `docs-validation.yml`, and `render-mermaid.yml` run on pull requests.
- ✅ Provide contributor template — `docs/CONTRIBUTING-docs.md` includes service-drafting guidance.
- ⛔ CODEOWNERS for service docs — No `.github/CODEOWNERS` present.

---

## Phase 7 — PRs, review, release

- ⛔ Split changes into reviewable PRs — Work pending.
- ⛔ Define review rubric — Not yet documented beyond plan.
- ⛔ Tag docs release (`docs-vX.Y.Z`) — Pending completion of earlier phases.

---

## Immediate Next Steps

1. Finish Phase 1 cleanup by trimming OPA detail out of `docs/src/tdd/TDD.md` and replacing it with a concise pointer to `services/lpe.md`.
2. Draft missing service specs (`digital-signer.md`, `notifications.md`, `llm-registry.md`) using the scaffold and include explicit canonical banners.
3. Add CODEOWNERS entries for existing service docs so reviews route to the right owners.

