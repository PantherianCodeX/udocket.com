# uDocket Runbook Catalog

<!-- AUTO-GENERATED: Run `python scripts/docs/build_runbook_catalog.py` to refresh. -->

## Digital Signer — 8.3 Runbooks & Drills (binding)

**Purpose:** Maintain executable runbooks and drill cadence for key signing scenarios. **|**
**Contract:** Alerts map to `RB-SIGN-*` playbooks; quarterly drills rehearse trust-root renewal, TSA failover, FIPS recovery, and client acknowledgement remediation. **|**
**State:** Runbooks `ops/runbooks/signer/`, drill evidence `ops/security/key_rotation/<timestamp>/`, tabletop notes `ops/change/signer_rotations.ics`. **|**
**Failures & handling:** Stale runbooks or missing drill evidence block release sign-off until refreshed. **|**
**Observability:** Docs lint, PagerDuty analytics, Ops governance dashboards. **|**
**Breadcrumbs:** Runbook files, rotation scripts, drill tracker. **|**
**References:** `RB-SIGN-TSA`, `RB-SIGN-FIPS`, `RB-SIGN-ACK`, `RB-SIGN-TRUSTROTATE`. *

### Digital Signer — 8.3.1 Runbook Index (informative)

| Runbook code | Scenario | Notes |
| --- | --- | --- |
| `RB-SIGN-TSA` | TSA/OCSP outage response | Rotates TSA credentials, fails over to backup TSA, captures evidence |
| `RB-SIGN-FIPS` | FIPS attestation recovery | Validates CMVP IDs, reinstates HSM slots, restores queue processing |
| `RB-SIGN-ACK` | Client acknowledgement remediation | Reconciles acknowledgements, notifies stakeholders, updates App.O |
| `RB-SIGN-TRUSTROTATE` | Trust-root / certificate rotation | Executes dual-publish rotation, records evidence, updates manifests |

### Digital Signer — 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarise the signer runbooks executed during incidents and drills so responders act consistently. **|**
**Contract:** Each runbook ties to specific alerts and evidence requirements; responders update playbooks after every incident or drill. **|**
**State:** Runbook markdown lives under `ops/runbooks/signer/`, automation scripts under `ops/scripts/security/`, and evidence in `ops/security/key_rotation/`. **|**
**Failures & handling:** Missing or stale steps block deployment sign-off until refreshed. **|**
**Observability:** Docs lint, PagerDuty analytics, and drill dashboards track completion. **|**
**Breadcrumbs:** `ops/runbooks/signer/*.md`, `ops/scripts/security/*.py`, incident templates `ops/security/incidents/signer_*.md`. **|**
**References:** Alert catalog, Ops governance policy, §5 Failure modes.

- `RB-SIGN-TSA` — TSA/OCSP outage response with rollback steps for deliverable signing and synthetic verification.
- `RB-SIGN-FIPS` — FIPS attestation recovery including startup attestations, HSM validation, and waiver handling.
- `RB-SIGN-ACK` — Client acknowledgement remediation, backlog clearing, and App.O waiver coordination.
- `RB-SIGN-TRUSTROTATE` — Trust-root/certificate rotation workflow covering dual publish, smoke tests, and evidence upload.

### Digital Signer — 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover trust-root renewal, TSA failover, FIPS recovery, and acknowledgement remediation; evidence lands in `ops/security/key_rotation/<timestamp>/`.
- Drill scheduler `ops/change/signer_rotations.ics` tracks cadence and ownership; missed drills block release sign-off until completed.
- Docs lint and Ops governance dashboards verify evidence uploads and runbook freshness before closing audits.

## Guardian Service — 8.3 Runbooks & Drills (binding)

**Purpose:** Maintain authoritative Guardian recovery guides, drills, and manual review procedures executed during incidents. **|**
**Contract:** Alerts enumerated in §§5–8 map to RB-GUARD identifiers documented here; responders update these runbooks after every incident or drill. **|**
**State:** Procedures live alongside automation scripts in `ops/runbooks/guardian/`, with this section summarizing triggers, decision trees, and evidence requirements. **|**
**Failures & handling:** Missing or stale steps block deployment sign-off; responders raise follow-up tasks to refresh runbooks before closing incidents. **|**
**Observability:** Post-incident retros attach the executed RB-GUARD identifier and confirm coverage during quarterly reviews; docs CI checks referenced runbook files exist. **|**
**Breadcrumbs:** Runbooks `ops/runbooks/guardian/*.md`, automation `ops/scripts/guardian/`, tests `tests/ops/test_runbook_integrity.py::test_guardian_runbooks`, PagerDuty service “Guardian SLO”, Grafana dashboard “Guardian SLO”. **|**
**References:** §5 Failure modes, §8.1 Operational posture, §8.3, ADR-0001. *

### Guardian Service — 8.3.1 Runbook Index (informative)

- `RB-GUARD-001` — Guardian SLO breach stabilisation
- `RB-GUARD-QUAR` — Quarantine spike investigation
- `RB-GUARD-QUEUE` — Submission backlog watchdog
- `RB-GUARD-MANUAL` — Manual review reconciliation

### Guardian Service — 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarise Guardian runbooks responders execute during incidents or exercises. **|**
**Contract:** Each runbook maps to specific alerts and evidence expectations; responders update the playbook after incidents or drills. **|**
**State:** Runbook markdown, automation scripts, and ledger templates live under `ops/runbooks/guardian/` and `ops/scripts/guardian/`. **|**
**Failures & handling:** Missing steps or stale guidance block deployment sign-off until refreshed. **|**
**Observability:** Docs lint, PagerDuty analytics, and retrospective checklists track coverage. **|**
**Breadcrumbs:** `ops/runbooks/guardian/*.md`, `ops/scripts/guardian/*.py`, incident templates `ops/guardian/incidents/*.jsonl`. **|**
**References:** §5 Failure Modes, Ops governance policy, alert catalog.

- `RB-GUARD-001`: Restore availability during SLO breaches—validate `/readyz` and `/synthetic/status`, capture queue metrics, decide whether to pause submissions or scale evaluators (`ops/scripts/guardian/scale_guardian.py`), maintain manual review ledgers in `ops/guardian/manual_review/<date>.jsonl`, and replay artifacts once latency returns to target.
- `RB-GUARD-QUAR`: Investigate quarantine spikes—compare bundle digests, sample artifacts, coordinate waivers with Security/Architecture, and log evidence (manifests, policy hashes, detector logs) before resuming automation.
- `RB-GUARD-QUEUE`: Clear submission backlog—throttle enqueue rates, scale evaluator pods, reconcile queue offsets via `ops/scripts/guardian/queue_reconcile.py`, and keep artifacts in `PENDING_JUDGMENT` until metrics recover.
- `RB-GUARD-MANUAL`: Manage manual review mode—capture reviewer decisions, enforce masking policies, and replay manual judgments once automated processing stabilises.

### Guardian Service — 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills rehearse SLO breach recovery, quarantine investigation, backlog management, and manual reconciliation; evidence stored in `ops/guardian/drills/<date>/` with retrospective notes.
- Docs lint (`scripts/docs/build_runbook_catalog.py --check`) and PagerDuty analytics verify execution; missed drills block release sign-off until remediated.
- Compliance reviews reference drill evidence, incident logs, and manual review ledgers to confirm coverage of Guardian runbooks.

## Identity & Access — 8.3 Runbooks & Drills (binding)

**Purpose:** Keep operational playbooks aligned with alerts and exercised on schedule. **|**
**Contract:** Runbooks must exist, link to alerts, and produce evidence per cadence. **|**
**State:** Runbook files, automation outputs `ops/identity/<date>/`. **|**
**Failures & handling:** Missing or stale runbooks block releases until refreshed. **|**
**Observability:** Runbook execution tracker, drill logs. **|**
**Breadcrumbs:** Ops catalog, automation scripts. **|**
**References:** Ops runbook catalog, drill tracker.

### Identity & Access — 8.3.1 Runbook Index (informative)

| Signal / Scenario | Runbook | Notes |
| --- | --- | --- |
| IdP outage / federation drift | `RB-IDP-FAILOVER` | Switch to Keycloak-native auth, rollback steps |
| RLS context failures | `RB-RLS-CONTEXT` | Middleware/PgBouncer remediation |
| Device fingerprint surge | `RB-DEVICE-FP` | Rotate tokens, update trusted proxies |
| Masking violation | `RB-MASK` | Detokenization audit and remediation |
| Break-glass governance gap | `RB-BREAK-GLASS` | Close events, capture retrospectives |

### Identity & Access — 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarize the critical runbooks responders execute during incidents. **|**
**Contract:** Each runbook must remain current and linked from alert definitions. **|**
**State:** Runbook Markdown files, automation scripts, evidence directories. **|**
**Failures & handling:** Gaps discovered during drills trigger immediate updates and retrospective notes. **|**
**Observability:** Runbook execution tracker, drill reports. **|**
**Breadcrumbs:** Ops runbook catalog (`docs/src/ops/runbooks/identity/*.md`). **|**
**References:** Ops runbook catalog, incident retrospectives.

- `RB-IDP-FAILOVER` — federation failover/rollback with evidence capture.  
- `RB-RLS-CONTEXT` — diagnose missing GUCs or pooling drift.  
- `RB-DEVICE-FP` — investigate compromised sessions, rotate credentials.  
- `RB-MASK` — remediate PII leakage, update scrubber coverage.  
- `RB-BREAK-GLASS` — dual approval workflow, retrospective documentation.

### Identity & Access — 8.3.3 Drill Cadence & Evidence (informative)

- Quarterly drills cover IdP failover, RLS failure, and masking breach; evidence stored under `ops/identity/drills/<date>/`.  
- Automation validates runbook execution dates each release; failures raise `identity_runbook_outdated_total`.

## LangGraph Agent Orchestration — 8.3 Runbooks & Drills (binding)

**Purpose:** Ensure operators have actionable playbooks for agent degradations, activation failures, and QA regressions. **|**
**Contract:** Runbooks listed here must remain current, link to Ops catalog entries, and surface evidence expectations for compliance. **|**
**State:** Runbook markdown lives under `docs/src/ops/runbooks/agents/`; drill evidence and after-action reviews are archived in `ops/runbooks/evidence/agents/`. **|**
**Failures & handling:** Missing or stale runbooks block launch; drills uncover coverage gaps and feed remediation tickets. **|**
**Observability:** Ops catalog build (`scripts/docs/build_runbook_catalog.py`), drill checklist dashboards, and on-call retros track preparedness. **|**
**Breadcrumbs:** Runbook catalog `docs/src/ops/runbooks/index.md`, evidence store `ops/runbooks/evidence/agents/`, drill tracker `ops/runbooks/agents/drill_log.csv`. **|**
**References:** Ops runbooks index, TDD Appendix B, Worker Cluster spec §3.5, QA governance §6.

- Runbooks must cover activation rollback, shadow divergence, Guardian quarantine escalation, and QA defect surge.
- On-call rotation uses `RB-AGENT-TIMEOUT`, `RB-AGENT-RETRY`, `RB-AGENT-ACTIVATION`, `RB-AGENT-SHADOW`, and `RB-AGENT-QA`.
- Drill cadence and evidence capture feed quarterly readiness reviews and SOC2/SOCPA audits.

### LangGraph Agent Orchestration — 8.3.1 Runbook Index (informative)

The catalog enumerates each runbook with owner, verification cadence, and Ops catalog ID. Maintained via `scripts/docs/build_runbook_catalog.py`; stale ownership or verification dates fail the docs lint and block merges.

- `RB-AGENT-ACTIVATION` — Applied AI Engineering (primary), Platform Operations (secondary), verified quarterly.
- `RB-AGENT-SHADOW` — Platform Operations (primary), Applied AI Engineering (secondary), verified quarterly.
- `RB-AGENT-TIMEOUT` — Worker Cluster owners, verified monthly.

### LangGraph Agent Orchestration — 8.3.2 Primary Runbooks (binding)

**Purpose:** Highlight the runbooks that must exist before activating or modifying agent pipelines. **|**
**Contract:** Each primary runbook documents trigger conditions, escalation path, mitigation steps, and evidence capture. **|**
**State:** Markdown sources under `docs/src/ops/runbooks/agents/`; evidence appended to drill log. **|**
**Failures & handling:** Missing steps or outdated escalations prompt remediation tickets before launch readiness sign-off. **|**
**Observability:** Ops QA reviews, incident postmortems, and audit sampling confirm runbook quality. **|**
**Breadcrumbs:** `docs/src/ops/runbooks/agents/agent_activation.md`, `docs/src/ops/runbooks/agents/agent_shadow.md`, `docs/src/ops/runbooks/agents/agent_retry.md`. **|**
**References:** Ops QA policy, TDD §12 (observability/DR), Worker Cluster spec §3.5.

- Activation rollback: capture commands to revert settings activation, disable pipelines, and restore prior manifests.
- Shadow divergence: enumerate alert thresholds, disable steps, data capture for analysis, and communications checklist.
- QA defect surge: describe Guardian quarantine coordination, manual QA staffing, and follow-up tasks.

### LangGraph Agent Orchestration — 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover SLO breach recovery, quarantine spikes, backlog management, and manual reconciliation; evidence stored in `ops/runbooks/evidence/agents/<YYYY>/<MM>/` with retrospective notes.
- `scripts/docs/build_runbook_catalog.py --check` plus PagerDuty analytics verify execution; missed drills require catch-up within 30 days and block activation rollouts.
- Compliance reviews reference drill evidence, incident logs, and manual review ledgers to demonstrate readiness for auditors.

## LLM Registry & Runtime Governance — 8.3 Runbooks & Drills (binding)

**Purpose:** Keep LLM runbooks actionable and drills on cadence. **|**
**Contract:** Alerts map to `RB-LLM-*` runbooks; quarterly drills cover provider failover, moderation outage, FinOps budget breach, and replay divergence scenarios. **|**
**State:** Runbooks `ops/runbooks/llm/*.md`, drill evidence `ops/llm/drills/<date>/summary.md`, waiver logs in App.O. **|**
**Failures & handling:** Missing evidence or outdated steps block release sign-off until updated. **|**
**Observability:** Docs lint, drill calendar `ops/change/llm_rotations.ics`, Ops governance dashboards. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler, automation scripts. **|**
**References:** `RB-LLM-003`, `RB-LLM-JB`, `RB-LLM-FINOPS`, `RB-LLM-REPLAY`. *

### LLM Registry & Runtime Governance — 8.3.1 Runbook Index (informative)

| Runbook code | Scenario | Notes |
| --- | --- | --- |
| `RB-LLM-003` | Provider degradation / residency drift | Executes failover validation and waiver workflow |
| `RB-LLM-JB` | Moderation or jailbreak regression | Locks registry in safe mode, reruns golden set, coordinates with Guardian |
| `RB-LLM-FINOPS` | Budget hold or cost breach | Pauses jobs, coordinates overrides with FinOps and App.O |
| `RB-LLM-REPLAY` | Replay divergence | Replays envelopes, compares hashes, and documents drift |

### LLM Registry & Runtime Governance — 8.3.2 Primary Runbooks (binding)

**Purpose:** Document operational playbooks for the registry so responders act consistently during incidents. **|**
**Contract:** Each runbook maps to specific alerts, evidence requirements, and owning teams; responders update them after every drill or incident. **|**
**State:** Runbook markdown lives in `ops/runbooks/llm/`, automation scripts under `ops/scripts/llm/`, and evidence within incident records `ops/llm/incidents/`. **|**
**Failures & handling:** Missing steps or stale guidance block deployment sign-off until refreshed. **|**
**Observability:** Docs lint, PagerDuty analytics, and Ops governance dashboards track runbook freshness and drill completion. **|**
**Breadcrumbs:** `ops/runbooks/llm/*.md`, `ops/scripts/llm/*.py`, incident templates `ops/llm/incidents/*.md`. **|**
**References:** Alert catalog, FinOps policy, Guardian integration docs.

- `RB-LLM-003` — Validates provider failover chains, residency attestations, and waiver approvals before resuming traffic.
- `RB-LLM-JB` — Investigates moderation regressions, reruns golden set, and coordinates Guardian enforcement.
- `RB-LLM-FINOPS` — Evaluates budget guardrails, pauses costly workloads, and secures FinOps/App.O overrides.
- `RB-LLM-REPLAY` — Replays envelopes, compares hashes, and files follow-up tasks for divergence remediation.

### LLM Registry & Runtime Governance — 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover provider failover, moderation outage, FinOps budget breach, and replay divergence with evidence in `ops/llm/drills/<date>/summary.md`.
- Drill calendar `ops/change/llm_rotations.ics` tracks cadence and ownership; missed drills block release sign-off until evidence captured.
- Docs lint and Ops governance dashboards verify runbook freshness and evidence uploads prior to production changes.

## Localization & Policy Engine — 8.3 Runbooks & Drills (binding)

**Purpose:** Maintain authoritative recovery guides and drill expectations. **|**
**Contract:** Alerts in §8.2 map to RB-LPE identifiers; responders update the runbook index after each incident or quarterly tabletop. **|**
**State:** Runbooks live in `ops/runbooks/lpe/` with automation scripts under `ops/scripts/lpe/`; incident evidence attaches to App.O decision logs. **|**
**Failures & handling:** Missing or stale steps block deploy sign-off until the runbook is refreshed. **|**
**Observability:** Docs lint validates references; quarterly drill calendar tracks execution. **|**
**Breadcrumbs:** Runbooks `ops/runbooks/lpe/*.md`, automation `ops/scripts/lpe/*.py`, tests `tests/ops/test_runbook_integrity.py`. **|**
**References:** §5 Failure modes, §8.1 Operational posture, §6 Observability. *

### Localization & Policy Engine — 8.3.1 Runbook Index (informative)

- `RB-LPE-COMPILER` — Compiler regression / adoption freeze
- `RB-LPE-OPA-ROLLBACK` — OPA bundle rollback
- `RB-LPE-WAIVER` — Waiver expiry response
- `RB-LPE-LOCALE-GAP` — Localization coverage gap

### Localization & Policy Engine — 8.3.2 Primary Runbooks (binding)

**Purpose:** Document localization & policy engine runbooks executed during incidents or drills. **|**
**Contract:** Alerts map to specific RB-LPE identifiers with evidence requirements; responders update runbooks after each incident or drill. **|**
**State:** Runbook markdown and automation scripts live under `ops/runbooks/lpe/` and `ops/scripts/lpe/`; incident evidence persists in `ops/lpe/incidents/`. **|**
**Failures & handling:** Missing or stale instructions block deployment approvals until refreshed. **|**
**Observability:** Docs lint, PagerDuty analytics, and Ops governance dashboards provide freshness metrics. **|**
**Breadcrumbs:** `ops/runbooks/lpe/*.md`, `ops/scripts/lpe/*.py`, incident templates `ops/lpe/incidents/*.md`. **|**
**References:** Alert catalog, Settings governance policy, FinOps handbook.

- `RB-LPE-COMPILER`: Freeze compiler, roll back to last-known-good bundle, run regression suite, and capture adoption evidence before resuming publishes.
- `RB-LPE-OPA-ROLLBACK`: Deploy prior OPA bundle, flush discovery caches, validate `/status` endpoints, and document digests and validation output.
- `RB-LPE-WAIVER`: Renew or retire residency waivers, update Settings allowlists, run waiver verification scripts, and log approvals in App.O.
- `RB-LPE-LOCALE-GAP`: Restore localization coverage by delivering translations/QA artefacts, executing locale audits, and rebuilding compiler outputs.

### Localization & Policy Engine — 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover compiler regression, OPA rollback, waiver expiry, and localization gap scenarios; evidence stored in `ops/lpe/drills/<date>/` with retrospective notes.
- Docs lint (`scripts/docs/build_runbook_catalog.py --check`) and PagerDuty analytics confirm drill execution; missed drills trigger remediation before releases proceed.
- Compliance reviews reference drill artefacts, waiver ledgers, and compiler adoption metrics to demonstrate readiness.

## Notifications Service — 8.3 Runbooks & Drills (binding)

**Purpose:** Keep playbooks executable and drills current for core notification scenarios. **|**
**Contract:** Alerts map to `RB-NOTIFY-*` runbooks; quarterly drills rehearse provider failover, webhook compromise, STOP/HELP compliance surges, and download-token abuse investigations. **|**
**State:** Runbooks `ops/runbooks/notifications/*.md`, drill evidence `ops/notifications/drills/<date>/summary.md`. **|**
**Failures & handling:** Missing drill evidence or outdated steps block change approval until updated. **|**
**Observability:** Docs lint, Ops governance dashboards, drill scheduler reports. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler, Slack `#ops-notifications`. **|**
**References:** `RB-NOTIFY-OUTAGE`, `RB-NOTIFY-WEBHOOK`, `RB-NOTIFY-SMS`, `RB-NOTIFY-TOKEN`. *

### Notifications Service — 8.3.1 Runbook Index (informative)

| Runbook code | Scenario | Notes |
| --- | --- | --- |
| `RB-NOTIFY-OUTAGE` | Provider outage / degraded delivery | Provider escalation paths, failover to backup channel |
| `RB-NOTIFY-WEBHOOK` | Webhook signature drift / compromise | Key rotation, backlog replay, SIEM coordination |
| `RB-NOTIFY-SMS` | STOP/HELP surge & regulatory response | Compliance scripts, opt-in reinstatement |
| `RB-NOTIFY-TOKEN` | Download token abuse or leak | Token rotation, artifact quarantine |

### Notifications Service — 8.3.2 Primary Runbooks (binding)

**Purpose:** Document operational playbooks responders execute during incidents or exercises. **|**
**Contract:** Link production alerts to runbook identifiers, outline execution cadence, and name the maintaining team. **|**
**State:** Summarize where runbooks live (repo paths, automation scripts) and what evidence they produce. **|**
**Failures & handling:** Explain how missing, stale, or skipped runbooks are surfaced and remediated. **|**
**Observability:** Note tooling that tracks drill frequency, runbook completion, and incident follow-up. **|**
**Breadcrumbs:** Runbook files, automation scripts, incident templates. **|**
**References:** Alert catalogs, governance docs referencing the runbooks.

- `RB-NOTIFY-OUTAGE` — Executes provider failover, backlog drainage, and SLA communications.
- `RB-NOTIFY-WEBHOOK` — Rotates webhook secrets, replays payloads, and coordinates SIEM review.
- `RB-NOTIFY-SMS` — Handles STOP/HELP surges, regulator notifications, and opt-in reconciliation.
- `RB-NOTIFY-TOKEN` — Investigates token abuse, rotates secrets, and quarantines compromised artifacts.

### Notifications Service — 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover provider failover, webhook compromise, STOP/HELP surge, and token abuse scenarios with evidence stored in `ops/notifications/drills/<date>/`.
- Drill scheduler `ops/scripts/notifications/schedule_drills.py` tracks cadence; missed drills block change approvals until evidence uploaded.
- Docs lint and Ops governance dashboards verify runbook freshness and drill completion ahead of production changes.

## Platform Runtime — 8.3 Runbooks & Drills (binding)

**Purpose:** Keep operational playbooks aligned with alerts and exercised on schedule. **|**
**Contract:** Runbooks must exist, include automation evidence, and be rehearsed per cadence. **|**
**State:** Runbook files and automation outputs under `ops/platform-runtime/<date>/`. **|**
**Failures & handling:** Missing or stale runbooks block releases until updated. **|**
**Observability:** Runbook execution tracker, drill summaries. **|**
**Breadcrumbs:** Ops catalog, automation scripts. **|**
**References:** Ops runbook catalog, drill scheduler documentation.

### Platform Runtime — 8.3.1 Runbook Index (informative)

| Signal / Scenario | Runbook | Notes |
| --- | --- | --- |
| TLS expiry | `RB-TLS-LEGACY` | Temporary TLS 1.2 fallback, validation, rollback |
| Residency drift | `RB-RES-BLOCK` | Mesh policy hardening and waiver review |
| Pod security violation | `RB-K8S-FENCE` | Admission webhook remediation |
| Region outage | `RB-REGION-CUTOVER` | DR failover/failback workflow |
| Flux/Helm rollout stuck | `RB-FLUX-ROLLBACK` | Flux sync investigation and rollback |

### Platform Runtime — 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarize the critical runbooks responders execute during incidents. **|**
**Contract:** Each runbook must remain up to date and linked from alert definitions. **|**
**State:** Runbook Markdown files, automation scripts, evidence directories. **|**
**Failures & handling:** Missing steps discovered during drills trigger immediate updates and retro documentation. **|**
**Observability:** Runbook execution tracker, drill reports. **|**
**Breadcrumbs:** Runbook catalog entries (`docs/src/ops/runbooks/*.md`). **|**
**References:** Ops runbook catalog, incident retrospectives.

- `RB-TLS-LEGACY` — enable/disable TLS 1.2 fallback, confirm scanners, capture evidence.  
- `RB-RES-BLOCK` — tighten mesh allowlists, coordinate Reference Manager/LPE updates, review waivers.  
- `RB-K8S-FENCE` — remediate PodSecurity violations or admission webhook outages.  
- `RB-REGION-CUTOVER` — execute disaster-recovery cutover and failback within approved region pairs.  
- `RB-FLUX-ROLLBACK` — handle Flux/Helm deployment failures, ensure service availability.

### Platform Runtime — 8.3.3 Drill Cadence & Evidence (informative)

- Quarterly drills rehearse TLS fallback, residency drift remediation, and region cutover; evidence stored in `ops/platform-runtime/drills/<date>/summary.md`.  
- Buildkite “platform-runtime-guardrails” step verifies runbook execution dates and evidence directories; failures page ownership teams.

## Reference Manager — 8.3 Runbooks & Drills (binding)

**Purpose:** Maintain authoritative RM recovery guides and drills executed during incidents. **|**
**Contract:** Alerts in §8.2 map to RB-RM identifiers documented here; responders update these runbooks after every incident or quarterly tabletop. **|**
**State:** Procedures live in `ops/reference/runbooks/`, with evidence logged under `ops/reference/incidents/<date>/`. **|**
**Failures & handling:** Missing or stale steps block deploy sign-off until the runbook is refreshed. **|**
**Observability:** Post-incident retros, docs lint, and runbook catalog builds verify coverage. **|**
**Breadcrumbs:** Runbooks `ops/reference/runbooks/*.md`, automation `ops/reference/*.py`, tests `tests/reference/test_runbook_integrity.py`. **|**
**References:** §5 Failure modes, §8.1 Operational posture, Appendix B metrics. *

### Reference Manager — 8.3.1 Runbook Index (informative)

- `RB-RM-ROLLBACK` — Reference bundle rollback
- `RB-RM-HARVEST` — Source harvest incident triage
- `RB-RM-WAIVER` — Residency waiver enforcement
- `RB-RM-FEED` — External feed outage response

### Reference Manager — 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarise Reference Manager runbooks so responders execute consistent mitigation steps. **|**
**Contract:** Each runbook ties to specific alerts and evidence expectations; responders update the runbooks after incidents or drills. **|**
**State:** Runbooks live under `ops/runbooks/ref_manager/`, automation scripts under `ops/scripts/ref_manager/`, and incident evidence in `ops/ref_manager/incidents/`. **|**
**Failures & handling:** Missing steps or stale content block deployment sign-off until refreshed. **|**
**Observability:** Docs lint, PagerDuty analytics, and Ops governance dashboards track runbook freshness and drill completion. **|**
**Breadcrumbs:** `ops/runbooks/ref_manager/*.md`, `ops/scripts/ref_manager/*.py`, incident templates `ops/ref_manager/incidents/*.md`. **|**
**References:** Alert catalog, Guardian integration docs, residency policy.

- `RB-RM-ROLLBACK`: Roll back reference bundles, flush caches, validate discovery parity, and capture digest evidence before reopening adoption.
- `RB-RM-HARVEST`: Triages source ingestion failures, replays harvest jobs, coordinates with upstream connectors, and documents missing evidence.
- `RB-RM-WAIVER`: Renews or retires residency waivers, updates allowlists, runs verification scripts, and records approvals in App.O.
- `RB-RM-FEED`: Handles external feed outages by pausing downstream adoption, notifying stakeholders, and reconciling data once service resumes.

### Reference Manager — 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover bundle rollback, harvest failure, waiver expiry, and feed outage; evidence lives in `ops/ref_manager/drills/<date>/` with retrospective notes.
- Docs lint (`scripts/docs/build_runbook_catalog.py --check`) and PagerDuty analytics confirm drill execution; missed drills block release approvals until remedied.
- Compliance reviews reference drill evidence, waiver logs, and adoption metrics to demonstrate readiness.

## Settings Registry — 8.3 Runbooks & Drills (binding)

**Purpose:** Maintain authoritative SR recovery guides, drills, and manual procedures executed during incidents. **|**
**Contract:** Alerts enumerated in §8.2 and Appendix B map to RB-\* identifiers documented here; responders update these runbooks after every incident or drill. **|**
**State:** Procedures live alongside automation scripts in `ops/runbooks/settings/`, with evidence logged under `ops/settings/<date>/` for each activation or remediation. **|**
**Failures & handling:** Missing or stale steps block deployment sign-off; responders raise follow-up tasks to refresh runbooks before closing incidents. **|**
**Observability:** Post-incident retros, quarterly tabletop exercises, and docs lint verify runbook coverage. **|**
**Breadcrumbs:** Runbooks `ops/runbooks/settings/*.md`, automation scripts under `ops/scripts/settings/`, tests `tests/platform/settings/test_runbook_integrity.py`. **|**
**References:** §5 Failure modes, §8.1 Operational posture, Appendix B metrics, ADR-0004. *

### Settings Registry — 8.3.1 Runbook Index (informative)

- `RB-GOV-008` — Settings governance toggle / rollback
- `RB-RES-ENDPOINT` — Residency endpoint drift remediation
- `RB-SETTINGS-ACTIVATION` — Activation failure response
- `RB-SETTINGS-WAIVER` — Waiver renewal and auditing

### Settings Registry — 8.3.2 Primary Runbooks (binding)

**Purpose:** Capture Settings service playbooks so responders execute consistent mitigation and evidence capture. **|**
**Contract:** Each runbook links to alert identifiers, change tickets, and required evidence; responders update the runbooks after incidents or drills. **|**
**State:** Runbooks under `ops/runbooks/settings/`, automation scripts under `ops/scripts/settings/`, evidence stored in `ops/settings/incidents/`. **|**
**Failures & handling:** Missing or outdated instructions block deployment approvals. **|**
**Observability:** Docs lint, PagerDuty analytics, and governance dashboards track freshness and drill coverage. **|**
**Breadcrumbs:** `ops/runbooks/settings/*.md`, `ops/scripts/settings/*.py`, incident templates `ops/settings/incidents/*.md`. **|**
**References:** Alert catalog, residency policy, FinOps governance.

- `RB-GOV-008`: Roll back governance toggles, restore prior snapshots, and document change approvals before reactivating.
- `RB-RES-ENDPOINT`: Remediate residency drift by updating endpoint allowlists, flushing caches, and verifying Guardian exposure.
- `RB-SETTINGS-ACTIVATION`: Handle activation failures by validating schema diffs, rerunning validation harnesses, and coordinating rollback/promotion sequencing.
- `RB-SETTINGS-WAIVER`: Renew or retire waivers, update allowlists, run verification scripts, and log approvals in App.O.

### Settings Registry — 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover activation rollback, residency drift, governance toggle rollback, and waiver renewal; evidence stored in `ops/settings/drills/<date>/` with retrospectives.
- Docs lint (`scripts/docs/build_runbook_catalog.py --check`) and PagerDuty analytics confirm drill execution; missed drills block releases until mitigated.
- Compliance reviews reference drill artefacts, waiver logs, and activation evidence to demonstrate readiness.

## Worker Cluster — 8.3 Runbooks & Drills (binding)

**Purpose:** Keep worker playbooks current and drills executed on schedule. **|**
**Contract:** Alerts map to RB-\*; quarterly exercises cover watchdog stalls, provider failover simulations, queue backlog remediation, and DLQ replay drills. **|**
**State:** Runbooks `ops/runbooks/worker/*.md`, drill evidence `ops/workers/drills/<date>/`. **|**
**Failures & handling:** Missing drill evidence or outdated steps block automation restart after incidents. **|**
**Observability:** Docs lint, drill scheduler reports, Ops governance dashboards. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler, Ops governance records. **|**
**References:** `RB-JOB-WATCHDOG`, `RB-LOCK-006`, `RB-NOTIFY-*`, `RB-UPLOAD-SCAN`, `RB-CASE-IMPORT`. *

### Worker Cluster — 8.3.1 Runbook Index (informative)

- `RB-JOB-WATCHDOG` — Worker/job watchdog
- `RB-JOB-DRAIN` — Graceful worker drain and redeploy
- `RB-JOB-RESIDENCY` — Residency drift remediation
- `RB-JOB-QUEUE` — Queue backlog triage

### Worker Cluster — 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarise worker cluster runbooks so responders execute consistent mitigations for job orchestration incidents. **|**
**Contract:** Each runbook ties to specific alerts and evidence expectations; responders update these guides after incidents or drills. **|**
**State:** Runbooks live in `ops/runbooks/worker/`, automation scripts in `ops/scripts/worker/`, and incident evidence under `ops/worker/incidents/`. **|**
**Failures & handling:** Missing steps or stale guidance blocks deployment approvals. **|**
**Observability:** Docs lint, PagerDuty analytics, and Ops dashboards track runbook freshness and drill coverage. **|**
**Breadcrumbs:** `ops/runbooks/worker/*.md`, `ops/scripts/worker/*.py`, incident templates `ops/worker/incidents/*.md`. **|**
**References:** Alert catalog, Guardian/Settings integration docs.

- `RB-JOB-WATCHDOG`: Recover from stalled or failed jobs by replaying Celery tasks, verifying locks, and notifying portal/UI.
- `RB-JOB-DRAIN`: Drain workers safely before deploys or failures, ensuring in-flight jobs persist and resume.
- `RB-JOB-RESIDENCY`: Handle residency drift by enforcing queue segregation, updating allowlists, and coordinating with Settings.
- `RB-JOB-QUEUE`: Manage backlog spikes, scale workers, and reconcile queue offsets with audit evidence.

### Worker Cluster — 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills cover watchdog recovery, drain rehearsal, residency enforcement, and backlog triage; evidence stored in `ops/worker/drills/<date>/` with retrospective notes.
- Docs lint (`scripts/docs/build_runbook_catalog.py --check`) and PagerDuty analytics confirm drill execution; missed drills block release approvals.
- Compliance reviews reference drill evidence, queue audits, and residency logs to demonstrate readiness.

## Web Application & Portal — 8.3 Runbooks & Drills (binding)

**Purpose:** Keep UI runbooks executable and drills on cadence. **|**
**Contract:** Alerts map to RB-\* playbooks; quarterly exercises cover SSE resiliency, portal abuse investigation, accessibility audits, and assistant abuse response. **|**
**State:** Runbooks `ops/runbooks/webapp/*.md`, evidence `ops/webapp/drills/<date>/`. **|**
**Failures & handling:** Missing drill evidence or outdated steps block release approval until updated. **|**
**Observability:** Docs lint, drill scheduler reports, governance dashboards. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler, governance policy App.N. **|**
**References:** `RB-JOB-WATCHDOG`, `RB-PORTAL-INVALIDATION`, `RB-LPE-LOCALE-GAP`, `RB-NOTIFY-*`, `RB-CHAT-ABUSE`. *

### Web Application & Portal — 8.3.1 Runbook Index (informative)

| Runbook code | Scenario | Notes |
| --- | --- | --- |
| `RB-JOB-WATCHDOG` | SSE/worker watchdog remediation | Coordinates with worker cluster for stalled jobs |
| `RB-PORTAL-INVALIDATION` | Token revocation / portal link cleanup | Revokes signed URLs, notifies clients, captures evidence |
| `RB-LPE-LOCALE-GAP` | Localization/accessibility gap | Partners with LP Engine for missing locales or accessibility gaps |
| `RB-NOTIFY-*` | Delivery incidents | Aligns portal alerts with outbound notifications |
| `RB-CHAT-ABUSE` | Assistant abuse or moderation escalation | Disables assistants, gathers evidence for Security |

### Web Application & Portal — 8.3.2 Primary Runbooks (binding)

**Purpose:** Summarise web-app runbooks so responders execute consistent mitigations across SSE, portal, and assistant incidents. **|**
**Contract:** Alerts map to RB-Web runbooks with evidence requirements; responders refresh the playbooks after drills or incidents. **|**
**State:** Runbooks live under `ops/runbooks/webapp/`, automation scripts under `ops/scripts/webapp/`, and incident evidence in `ops/webapp/incidents/`. **|**
**Failures & handling:** Missing steps or stale content block deployment approvals. **|**
**Observability:** Docs lint, PagerDuty analytics, and Ops dashboards track runbook freshness and drill coverage. **|**
**Breadcrumbs:** `ops/runbooks/webapp/*.md`, `ops/scripts/webapp/*.py`, incident templates `ops/webapp/incidents/*.md`. **|**
**References:** Alert catalog, LP Engine, Notifications integration guides.

- `RB-JOB-WATCHDOG` — Restores SSE sessions, resumes watchdog automation, and coordinates backlog remediation.
- `RB-PORTAL-INVALIDATION` — Revokes signed URLs, reissues secure links, and documents evidence for auditors.
- `RB-LPE-LOCALE-GAP` — Triages localization/accessibility deficits with LP Engine and revalidates fallback artefacts.
- `RB-NOTIFY-*` — Synchronizes portal state with outbound notifications when delivery issues surface.
- `RB-CHAT-ABUSE` — Freezes assistants, escalates to Guardian, and captures moderation evidence.

### Web Application & Portal — 8.3.3 Drill Cadence & Evidence (binding)

- Quarterly drills exercise SSE resiliency, portal abuse response, accessibility audits, and assistant abuse scenarios with evidence in `ops/webapp/drills/<date>/`.
- Drill scheduler `ops/scripts/webapp/schedule_drills.py` tracks cadence and ownership; missed drills block release approvals until evidence uploaded.
- Docs lint, governance dashboards, and App.N reviews verify runbook freshness before production changes.
