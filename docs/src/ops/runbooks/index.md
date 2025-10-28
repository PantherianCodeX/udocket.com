# uDocket Runbook Catalog

<!-- AUTO-GENERATED: Run `python scripts/docs/build_runbook_catalog.py` to refresh. -->

## _Template — 8.3 Runbooks & drills

**Purpose:** Document operational playbooks responders execute during incidents or exercises. **|**
**Contract:** Link production alerts to runbook identifiers, outline execution cadence, and name the maintaining team. **|**
**State:** Summarize where runbooks live (repo paths, automation scripts) and what evidence they produce. **|**
**Failure modes & handling:** Explain how missing, stale, or skipped runbooks are surfaced and remediated. **|**
**Observability:** Note tooling that tracks drill frequency, runbook completion, and incident follow-up. **|**
**Breadcrumbs:** Runbook files, automation scripts, incident templates. **|**
**References:** Alert catalogs, governance docs referencing the runbooks.

### _Template — 8.3.1 Runbook index

> Provide a quick map from alert codes/signals to runbook identifiers.

### _Template — 8.3.2 Primary runbooks

> Document the key runbooks (rollback, incident triage, hotfix, etc.) with summary tables or links.

### _Template — 8.3.3 Drill cadence & evidence

> Capture expectations for tabletop exercises, on-call readiness checks, and evidence storage.

## Guardian — 8.3 Runbooks & drills (binding)

**Purpose:** Maintain authoritative Guardian recovery guides, drills, and manual review procedures executed during incidents. **|**
**Contract:** Alerts enumerated in §§5–8 map to RB-GUARD identifiers documented here; responders update these runbooks after every incident or drill. **|**
**State:** Procedures live alongside automation scripts in `ops/runbooks/guardian/`, with this section summarizing triggers, decision trees, and evidence requirements. **|**
**Failure modes & handling:** Missing or stale steps block deployment sign-off; responders raise follow-up tasks to refresh runbooks before closing incidents. **|**
**Observability:** Post-incident retros attach the executed RB-GUARD identifier and confirm coverage during quarterly reviews; docs CI checks referenced runbook files exist. **|**
**References:** §5 Failure modes, §8.1 Operational posture, §8.3, ADR-0001. **|**
**Breadcrumbs:** Runbooks `ops/runbooks/guardian/*.md`, automation `ops/scripts/guardian/`, tests `tests/ops/test_runbook_integrity.py::test_guardian_runbooks`, PagerDuty service “Guardian SLO”, Grafana dashboard “Guardian SLO”.

### Guardian — 8.3.1 Runbook index (informative)

**Purpose:** Provide a quick lookup of Guardian runbooks and drill identifiers. **|**
**Contract:** Keep the list synchronized with §8.3 entries; add new RB-GUARD codes as they are introduced. **|**
**State:** Index mirrors runbook filenames under `ops/runbooks/guardian/`. **|**
**Failure modes & handling:** Missing entries confuse responders; update this index during runbook reviews. **|**
**Observability:** Docs lint validates referenced sections; quarterly runbook audits review this list. **|**
**References:** §8.3.2–§8.3.5, §8.2 Incident triggers. **|**
**Breadcrumbs:** Runbooks `ops/runbooks/guardian/*.md`, automation scripts `ops/scripts/guardian/`.

- RB-GUARD-001 — Guardian SLO breach stabilization.
- RB-GUARD-QUAR — Quarantine spike investigation.
- RB-GUARD-QUEUE — Submission backlog watchdog.
- RB-GUARD-MANUAL — Manual review reconciliation.

<a id="rb-guard-001"></a>

### Guardian — 8.3.2 RB-GUARD-001 — Guardian SLO breach (binding)

**Purpose:** Restore Guardian availability and route artifacts through manual review when automated judgments breach the SLO. **|**
**Contract:** Any availability or latency breach must execute this sequence before re-enabling automated progression; manual review requires ledger capture. **|**
**State:** Manual review ledger entries persist under `ops/guardian/manual_review/<date>.jsonl`, alongside incident records in `ops/guardian/incidents/`. **|**
**Failure modes & handling:** Skipping ledger updates or failing to scale evaluators risks lost audit history and ongoing SLO breaches. **|**
**Observability:** Alerts `guardian_judgment_latency_seconds`, `guardian_submission_timeout_total`, and synthetic job results confirm recovery once they return to baseline. **|**
**References:** §5.1 Submission backlog, §8.1 Operational posture, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/runbooks/guardian/slo_breach.md`, automation `ops/scripts/guardian/scale_guardian.py`, tests `tests/ops/test_runbook_integrity.py::test_guardian_slo_runbook`, Grafana dashboard “Guardian SLO”.

- **Signals:** `guardian_judgment_latency_seconds` P95 > SLO, `guardian_submission_timeout_total` increasing, synthetic job failure (`guardian_slo.yaml`).
- **Triage (≤ 5 minutes):**
  1. Check `/readyz` and `/synthetic/status`; capture latency panels in Grafana (“Guardian SLO”).
  2. Confirm queue depth (`guardian_pending_total`, `guardian_pending_oldest_seconds`) and worker health (Celery heartbeat, pod restarts).
  3. Inspect recent deploys/settings (`guardian.rules.version`, Helm releases) for regressions.
- **Decision tree:**
  - *Service unhealthy*: place Guardian in manual review mode (pause submissions, notify ops). Operators record `MANUAL_GUARDIAN_JUDGMENT` artifacts while following this checklist.
  - *Compute exhaustion*: scale deployment (`kubectl -n platform scale deploy/guardian --replicas=<n>`), update HPA floor post-incident.
  - *Upstream dependency slowdown*: coordinate with LPE/Settings owners; consider throttling new submissions until latency stabilizes.
- **Post-remediation:**
  - Ensure `guardian_judgment_latency_seconds` P95 ≤ SLO for two consecutive scrapes and `guardian_submission_timeout_total` plateaued.
  - Clear manual review backlog by replaying queued artifacts once service healthy; annotate incident log with root cause and follow-ups.

<a id="rb-guard-quar"></a>

### Guardian — 8.3.3 RB-GUARD-QUAR — Quarantine spike investigation (binding)

**Purpose:** Diagnose spikes in QUARANTINED outcomes while preserving policy integrity. **|**
**Contract:** Any surge in quarantine outcomes uses this investigation before promoting new releases or issuing waivers. **|**
**State:** Findings log under `ops/guardian/quarantine/<incident_id>.md` with root cause summaries and evidence attachments. **|**
**Failure modes & handling:** Missing waiver documentation or mismatched settings snapshots lead to repeated incidents; responders must reconcile digests before closing. **|**
**Observability:** Alerts `guardian_quarantine_false_positive_total`, `guardian_policy_block_total`, and synthetic classifier drift checks signal this runbook; dashboards “Guardian Detection Quality” and incident annotations track progress. **|**
**References:** §2.2 Responsibilities, §5.2 Detector regression, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/runbooks/guardian/quarantine_spike.md`, automation `ops/scripts/guardian/replay_quarantine.py`, tests `tests/ops/test_runbook_integrity.py::test_guardian_quarantine_runbook`.

- Verify detector bundle digests against Settings (`guardian.rules.version`) and LPE outputs; roll back bundles when digests diverge.
- Sample quarantined artifacts, classify false positives versus true violations, and coordinate waivers when policy exceptions are justified.
- Capture evidence (manifests, policy hashes, detector logs) in the incident log prior to reopening automation.

<a id="rb-guard-queue"></a>

### Guardian — 8.3.4 RB-GUARD-QUEUE — Submission backlog watchdog (binding)

**Purpose:** Clear submission backlogs while ensuring artifacts remain gated by Guardian. **|**
**Contract:** Backlog incidents hold artifacts in `PENDING_JUDGMENT` until the queue drains; any manual progression requires dual approval recorded in the ledger. **|**
**State:** Queue statistics emit via `guardian_pending_total`, `guardian_pending_oldest_seconds`, and audit tables `guardian_submission_audit`. **|**
**Failure modes & handling:** Skipped throttling or missing replay steps cause double-processing or lost submissions; this runbook enforces sequencing and reconciles offsets. **|**
**Observability:** Alerts `alert_guardian_queue_stale`, `guardian_submission_timeout_total`, and Celery heartbeat dashboards confirm backlog health. **|**
**References:** §3.2 Submission interfaces, §5.1 Submission backlog, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/runbooks/guardian/queue_backlog.md`, reconciliation script `ops/scripts/guardian/queue_reconcile.py`, tests `tests/platform/guardian/test_backlog_handling.py`.

- Pause new submissions if queue age exceeds policy; coordinate with upstream services to shed load.
- Scale evaluator pods (`kubectl scale deploy/guardian --replicas=<n>`) and confirm Kafka/Service Bus lag recedes.
- Replay stuck messages via `POST /guardian/judgments:enqueue` with retention-aware offsets; reconcile submission audit tables before closing the incident.

<a id="rb-guard-manual"></a>

### Guardian — 8.3.5 RB-GUARD-MANUAL — Manual review reconciliation (binding)

**Purpose:** Govern manual judgment operation when automation is intentionally paused. **|**
**Contract:** Manual review requires Security + Architecture approval, dual sign-offs per artifact, and full ledger capture prior to re-enabling automation. **|**
**State:** Ledgers persist in `ops/guardian/manual_review/<date>.jsonl`, with reconciliation jobs logging outputs to `ops/guardian/reconciliation/<incident_id>.jsonl`. **|**
**Failure modes & handling:** Missing ledger entries or skipped reconciliation jobs break provenance; responders must backfill records and hold automation until evidence is complete. **|**
**Observability:** Dashboard “Guardian Manual Review” tracks backlog age; incident retros verify ledger completeness and follow-up tasks. **|**
**References:** §4 State management, §5 Failure modes, §8.5.1 Manual review cadence. **|**
**Breadcrumbs:** Runbook `ops/runbooks/guardian/manual_review.md`, automation `ops/scripts/guardian/reconcile_manual.py`, tests `tests/ops/test_runbook_integrity.py::test_guardian_manual_runbook`.

- Record every manual decision with evidence hashes, reviewer IDs, and timestamps.
- Reconcile manual artifacts via replay once automation recovers; annotate incidents with residual risk assessments.
- Update waiver manifests and close-out tasks before declaring the incident resolved.

## Lp Engine — Appendix R — Runbooks & drills (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/`, Tests `tests/ops/test_runbook_integrity.py::test_lpe_runbook_links`, Observability PagerDuty service “Localization & Policy Engine” with Grafana dashboards “LPE – Enforcement & Residency” and “LPE Compiler”.\\ *Purpose: Maintain actionable recovery guides for LPE incidents and drills.*\\ *Contract: Every alert enumerated in §5.2 maps to an RB-LPE identifier here; responders keep procedures evergreen through quarterly tabletop reviews.*\\ *State: Runbooks live beside automation scripts in `ops/runbooks/lpe/`; this appendix summarizes triggers, decision trees, and evidence requirements.*\\ *Failure modes & retries: Missing or stale runbooks trigger corrective action items and block deploy sign-off.*\\ *Observability: Docs lint checks confirm Appendix R coverage; PagerDuty postmortems must reference the executed RB-LPE ID.*

### Lp Engine — R.1 Runbook index (informative)

- RB-LPE-COMPILER — Compiler diff escalation and rollback workflow.
- RB-OPA-ROLLBACK — OPA bundle rollback and policy cache validation.
- RB-LPE-WAIVER — Waiver expiry, renewal, and containment response.
- RB-LPE-LOCALE-GAP — Missing localization coverage remediation.

<a id="rb-lpe-compiler"></a>

### Lp Engine — R.2 RB-LPE-COMPILER — Compiler diff triage (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/compiler_diff_triage.md`, Automation `ops/scripts/lpe/run_compiler_diff.py`, Tests `tests/ops/test_runbook_integrity.py::test_compiler_diff_runbook`, Observability Grafana “LPE Compiler” (alerts `lpe_compiler_duration_overrun`, `lpe_bundle_signature_error`).\\ *Purpose: Contain defective compiler outputs and restore last-known-good bundles without service disruption.*\\ *Contract: Any compiler diff flagged unsafe or breaking must follow this procedure prior to promotion.*\\ *State: Diff artifacts reside in `ops/lpe/compiler_diffs/<date>/`; rollback bundles stored in `ops/lpe/rollback/<bundle_id>.json`.*\\ *Failure modes & retries: Skipping regression replays risks reintroducing invalid localization contexts; failing to rollback promptly blocks Settings activations.*\\ *Observability: Alert clears once safe bundle promoted and diff backlog returns to zero.*

Triggers: `lpe_compiler_duration_overrun`, `lpe_bundle_signature_error`, change tickets tagged `LPE-COMPILER`, manual escalations from QA.

Execution checklist:

1. Freeze compiler pipeline (`lpe.compiler.enabled=false`) and announce in `#ops-announcements`.
2. Inspect diff artifacts; confirm affected locales/regions and whether unsafe flags were raised.
3. Promote previous good bundle via `ops/scripts/lpe/promote_bundle.py --bundle <id>` and capture hash evidence.
4. Re-run regression suite (`make lpe-compiler-regressions`) and snapshot Grafana panels for incident ticket.
5. Coordinate Settings activation replay once bundle validated; update change ticket with evidence.

Post-remediation:

- Resume compiler pipeline and monitor `lpe_compiler_duration_seconds` for two cycles.
- File corrective tasks (root cause, automation gaps) and attach diff artefacts to App.O decision log.

<a id="rb-opa-rollback"></a>

### Lp Engine — R.3 RB-OPA-ROLLBACK — OPA bundle rollback (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/opa_bundle_rollback.md`, Automation `ops/scripts/lpe/deploy_opa_bundle.py`, Tests `tests/ops/test_runbook_integrity.py::test_opa_rollback_runbook`, Observability Grafana “OPA Discovery” (alerts `opa_discovery_stale_total`, `reference_bundle_stale_total`).\\ *Purpose: Restore healthy Open Policy Agent bundles when discovery or validation failures occur.*\\ *Contract: Any production rollback must document bundle hashes, discovery health, and post-rollback validation.*\\ *State: Bundle manifests stored in `ops/lpe/opa_bundles/`; discovery checks recorded in `ops/lpe/discovery_audit.jsonl`.*\\ *Failure modes & retries: Deploying stale bundles without discovery verification risks policy drift; skipping cache flush leaves workers on outdated decisions.*\\ *Observability: Alert resolves when discovery latency normalizes and signature validation succeeds twice consecutively.*

Response steps:

1. Capture failing discovery IDs and affected services from alert payload.
2. Roll back via `ops/scripts/lpe/deploy_opa_bundle.py --bundle <last_good>` and flush worker caches (`scripts/opa/flush_cache.py`).
3. Validate OPA `/status` and `/health` endpoints plus policy unit tests (`pytest tests/opa/test_policy_context.py`).
4. Notify dependent teams (Settings, Guardian, Reference Manager) and confirm cached digests refresh.
5. Attach bundle hashes, validation output, and Grafana snapshots to incident ticket.

Follow-up:

- Run `ops/scripts/lpe/discovery_audit.py` to confirm discovery parity within 30 minutes.
- File preventive tasks for root cause (compiler bug, Settings drift, CDN failure).

<a id="rb-lpe-waiver"></a>

### Lp Engine — R.4 RB-LPE-WAIVER — Waiver expiry response (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/waiver_expiry.md`, Automation `ops/scripts/lpe/check_waivers.py`, Tests `tests/ops/test_runbook_integrity.py::test_waiver_runbook`, Observability Grafana “Residency & Enforcement” (alerts `lpe_policy_block_spike`, `lpe_privacy_framework_enabled_total`).\\ *Purpose: Maintain compliant waiver coverage and prevent unauthorized cross-jurisdiction traffic.*\\ *Contract: Expiring waivers must either be renewed with dual approval or decommissioned before expiry.*\\ *State: Waiver ledger maintained in `ops/lpe/waivers.yaml`; renewal evidence archived under `ops/lpe/waiver_reviews/<date>/`.*\\ *Failure modes & retries: Letting waivers lapse without containment can block activations or violate residency commitments.*\\ *Observability: Alert clears once waiver renewal recorded and `lpe_policy_block_total` returns to baseline.*

Checklist:

1. Review waiver ledger for entries expiring within alert window; confirm impacted locales and providers.
2. Engage Security + Architecture for renewal decision; capture approvals in decision log.
3. If waiver retired, update Settings allowlists and trigger Appendix R RB-LPE-LOCALE-GAP if localization fallback required.
4. Run `ops/scripts/lpe/check_waivers.py --verify` to ensure updated posture and attach output to incident ticket.
5. Communicate outcome to affected product owners and document customer impact, if any.

Audit trail:

- Store approvals, renewal artefacts, and communication templates alongside incident log.
- Schedule follow-up review to validate long-term remediation (automation fix, localization updates).

<a id="rb-lpe-locale-gap"></a>

### Lp Engine — R.5 RB-LPE-LOCALE-GAP — Localization coverage gap (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/locale_gap.md`, Automation `ops/scripts/lpe/audit_locales.py`, Tests `tests/ops/test_runbook_integrity.py::test_locale_gap_runbook`, Observability Grafana “Localization QA” (alerts `lpe_locale_gap_total`, `lpe_lookup_latency_p95_breach`).\\ *Purpose: Restore locale coverage when translations, policy text, or metadata go missing.*\\ *Contract: New locales must publish translations, disclaimer copy, and QA artefacts before re-enabling bundles.*\\ *State: Locale inventories in `ops/lpe/locales.csv`; QA recordings referenced in Appendix A.*\\ *Failure modes & retries: Re-enabling locales without QA sign-off risks incorrect or missing compliance copy.*\\ *Observability: Alert resolves once locale gap metric returns to zero and QA artefacts uploaded.*

Resolution steps:

1. Identify affected locales and impacted surfaces (portal, Guardian, notifications) from alert payload.
2. Coordinate with Localization program to deliver missing translations and QA recordings; update Appendix A checklist items.
3. Validate `ops/scripts/lpe/audit_locales.py` passes for affected locales and attach proof to ticket.
4. Run synthetic checks (`tests/e2e/test_portal_policy_context.py::test_disclaimer_l10n`) to confirm correct copy rendering.
5. Update Settings bundles and trigger LPE compiler rebuild; monitor `lpe_lookup_latency_p95_breach` for regression.

Post-checks:

- Log decision record in App.O with locale IDs, remediation timeline, and QA sign-offs.
- Schedule follow-up audit within one release cycle to verify coverage remains intact.

______________________________________________________________________

## Ref Manager — 8.3 Runbooks & drills (binding)

**Purpose:** Maintain authoritative RM recovery guides and drills executed during incidents. **|**
**Contract:** Alerts in §8.2 map to RB-RM identifiers documented here; responders update these runbooks after every incident or quarterly tabletop. **|**
**State:** Procedures live in `ops/reference/runbooks/`, with evidence logged under `ops/reference/incidents/<date>/`. **|**
**Failure modes & handling:** Missing or stale steps block deploy sign-off until the runbook is refreshed. **|**
**Observability:** Post-incident retros, docs lint, and runbook catalog builds verify coverage. **|**
**References:** §5 Failure modes, §8.1 Operational posture, Appendix B metrics. **|**
**Breadcrumbs:** Runbooks `ops/reference/runbooks/*.md`, automation `ops/reference/*.py`, tests `tests/reference/test_runbook_integrity.py`.

### Ref Manager — 8.3.1 Runbook index (informative)

**Purpose:** Provide a quick map from RM alerts to runbook identifiers. **|**
**Contract:** Every RM alert references one of these IDs; new alerts require index updates before merge. **|**
**State:** Index maintained in `ops/reference/runbooks/index.md` and mirrored here. **|**
**Failure modes & handling:** Docs lint fails when the index misses an alert. **|**
**Observability:** Weekly lint ensures index matches Alertmanager routes. **|**
**References:** §8.2 Incident triggers, §8.3.2–§8.3.6. **|**
**Breadcrumbs:** Runbook index `ops/reference/runbooks/index.md`, tests `tests/reference/test_runbook_index.py`.

- RB-RM-ROLLBACK — Reference bundle rollback & adoption freeze
- RB-RM-HARVEST — Source harvest incident triage
- RB-RM-PUBLISH — Publish guard failure response
- RB-RM-LICENSE — License violation remediation
- RB-RM-RESIDENCY — Residency endpoint alignment

<a id="rb-rm-rollback"></a>

### Ref Manager — 8.3.2 RB-RM-ROLLBACK — Reference bundle rollback & adoption freeze (binding)

**Purpose:** Restore catalog stability when published bundles must be reverted. **|**
**Contract:** Rollbacks execute within 15 minutes of decision, capture evidence, and freeze dependent publishes until adoption latency returns to baseline. **|**
**State:** Automation uses `ops/reference/rollback_bundle.py`; evidence stored under `ops/reference/incidents/<date>/rollback`. **|**
**Failure modes & handling:** Missing rollback evidence or lingering adoption lag triggers escalation to Architecture. **|**
**Observability:** Alert `reference_bundle_adoption_total{status="stale"}` clears when all services acknowledge the rollback. **|**
**References:** §4.2 Bundle registry, §5.5 Adoption lag, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/reference/runbooks/rollback.md`, tests `tests/reference/test_rollback.py`.

Execution checklist:

1. Pause new publishes and announce freeze in `#ref-manager-oncall`.
2. Run `reference rollback --bundle <previous_id>` capturing activation ID and diff artifacts.
3. Trigger adoption verification for LPE, Settings, Guardian, Compose/Analyze, and Portal.
4. Update change ticket and App.O decision log with rollback details, evidence links, and remediation tasks.
5. Resume publishes only after adoption lag returns below SLA and follow-up actions assigned.

<a id="rb-rm-harvest"></a>

### Ref Manager — 8.3.3 RB-RM-HARVEST — Source harvest incident triage (binding)

**Purpose:** Mitigate source outages or connector failures before catalog staleness accumulates. **|**
**Contract:** Incidents remain open until harvest resumes, manual uploads address backlog, and validation confirms no data loss. **|**
**State:** Incident records track source metadata, outage start, workaround steps, and licensing considerations. **|**
**Failure modes & handling:** Ignoring prolonged harvest outages risks stale catalog data; escalate to Program Leads and Legal Ops when SLAs breach. **|**
**Observability:** Alert `reference_manager_harvest_error_total` and stale-source monitors signal recovery. **|**
**References:** §2.2 Source acquisition, §5.1 Harvest outage, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/reference/runbooks/harvest_incident.md`, connectors `packages/udocket_core/reference_manager/connectors.py`.

Response checklist:

1. Review failing connector logs, capture last successful snapshot, and assess licensing implications.
2. Engage source owner (court/government contact) and record ETA; initiate manual upload if available.
3. Queue interim communications to stakeholders when outage exceeds SLA.
4. Resume scheduled harvest, validate ETL outputs, and confirm review queue impact.
5. Close incident with root cause, remediation summary, and preventive actions.

<a id="rb-rm-publish"></a>

### Ref Manager — 8.3.4 RB-RM-PUBLISH — Publish guard failure response (binding)

**Purpose:** Triage schema or validation failures that block publish pipelines. **|**
**Contract:** Guard failures remain blocking until diffs resolve, schema updates approve, and integration tests rerun. **|**
**State:** Validation artifacts persist alongside bundle drafts in `reference_bundle_registry`; tickets track remediation. **|**
**Failure modes & handling:** Ignoring guard signals risks inconsistent bundles; escalate to Architecture if fixes exceed 12 hours. **|**
**Observability:** Alert `reference_manager_publish_guard_failure` clears when validation suite passes. **|**
**References:** §5.2 Publish guard failure, §2.9 Testing, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/reference/runbooks/publish_guard.md`, tests `tests/reference/test_publish_guard.py`.

Execution checklist:

1. Export failing validation artifacts (`reference validate --bundle <id> --export artifacts/guard/<id>`).
2. Categorize failure (schema, missing assets, licensing metadata, diff threshold) and assign owners.
3. Apply fixes in staging, rerun validation and unit/integration suites.
4. Secure approvals, document evidence, and resume publish pipeline.
5. Attach diff snapshots and validation logs to incident ticket and update risk register if needed.

<a id="rb-rm-license"></a>

### Ref Manager — 8.3.5 RB-RM-LICENSE — License violation remediation (binding)

**Purpose:** Resolve licensing or attribution violations before they propagate. **|**
**Contract:** Violations remain open until offending content removed or relicensed, attribution updates verified downstream, and Legal Ops approvals documented. **|**
**State:** License ledger entries store violation metadata, remediation steps, and waiver approvals. **|**
**Failure modes & handling:** Publishing without remediation risks contractual breaches; escalate to Legal Ops immediately. **|**
**Observability:** Alert `reference_manager_license_violation_total` clears when ledger marks violation mitigated and attribution scanners pass. **|**
**References:** §2.8 Security & licensing, §5.3 Licensing incidents, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/reference/runbooks/license_violation.md`, tests `tests/reference/test_license_ledger.py`.

Remediation checklist:

1. Review violation payload, freeze related publishes, and notify Legal Ops.
2. Remove or quarantine offending content from staging/curated schemas; note impacted bundle versions.
3. Coordinate relicensing or replacements; capture approvals in waiver ledger.
4. Regenerate bundles, validate Guardian/UI attribution, and resume adoption.
5. Close ledger entry with evidence links and communicate resolution to stakeholders.

<a id="rb-rm-residency"></a>

### Ref Manager — 8.3.6 RB-RM-RESIDENCY — Residency endpoint alignment (binding)

**Purpose:** Restore residency compliance when provider endpoint catalogues drift. **|**
**Contract:** Findings stay open until catalogues update, Settings activations replay, and residency scanners confirm remediation. **|**
**State:** Findings tracked in `reference_provider_endpoint_finding` with attestation evidence and waiver metadata. **|**
**Failure modes & handling:** Allowing stale endpoints risks policy violations; escalate to Security Engineering if remediation exceeds SLA. **|**
**Observability:** Alert `reference_manager_provider_endpoint_violation_total` resolves after two clean scans and Settings activations match updated catalogues. **|**
**References:** §4.4 Residency catalogue, §5.4 Residency incidents, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/reference/runbooks/residency_alignment.md`, tests `tests/reference/test_provider_endpoints.py`.

Remediation checklist:

1. Inspect finding details, gather attestation or SAN mismatch evidence, and engage provider contacts.
2. Update RM catalogue entries (`provider_endpoints[]`) with new CIDRs, SAN expectations, and residency notes.
3. Publish refreshed bundle, replay Settings activation, and verify Guardian acknowledges new digest.
4. Archive evidence in incident folder and update waiver ledger for temporary exceptions.
5. Confirm residency monitors pass twice consecutively before closing the incident.

## Settings — 8.3 Runbooks & drills (binding)

**Purpose:** Maintain authoritative SR recovery guides, drills, and manual procedures executed during incidents. **|**
**Contract:** Alerts enumerated in §8.2 and Appendix B map to RB-* identifiers documented here; responders update these runbooks after every incident or drill. **|**
**State:** Procedures live alongside automation scripts in `ops/runbooks/settings/`, with evidence logged under `ops/settings/<date>/` for each activation or remediation. **|**
**Failure modes & handling:** Missing or stale steps block deployment sign-off; responders raise follow-up tasks to refresh runbooks before closing incidents. **|**
**Observability:** Post-incident retros, quarterly tabletop exercises, and docs lint verify runbook coverage. **|**
**References:** §5 Failure modes, §8.1 Operational posture, Appendix B metrics, ADR-0004. **|**
**Breadcrumbs:** Runbooks `ops/runbooks/settings/*.md`, automation scripts under `ops/scripts/settings/`, tests `tests/platform/settings/test_runbook_integrity.py`.

### Settings — 8.3.1 Runbook index (informative)

**Purpose:** Provide a quick lookup of SR runbooks and drill identifiers. **|**
**Contract:** Every Settings alert references one of these IDs; new alerts require index updates. **|**
**State:** Index maintained in version control and mirrored here. **|**
**Failure modes & handling:** Lint script fails when the index misses an alert; update the entry before merging. **|**
**Observability:** Weekly docs lint verifies the index matches Alertmanager routes. **|**
**References:** §8.2 Incident triggers, §8.3.2–§8.3.8. **|**
**Breadcrumbs:** Runbook index `ops/runbooks/settings/index.md`, tests `tests/platform/settings/test_runbook_index.py`.

- RB-GOV-008 — Settings governance toggle / rollback
- RB-RES-ENDPOINT — Residency endpoint drift remediation
- RB-RES-BLOCK — Residency waiver / block handling
- RB-LOCK-006 — Activation lock stale detection & remediation
- RB-LLM-003 — Provider degradation / circuit breaker
- RB-JOB-WATCHDOG — Job stall watchdog
- RB-UPLOAD-SCAN — Upload scanning outage response

<a id="rb-gov-008"></a>

### Settings — 8.3.2 RB-GOV-008 — Settings governance toggle / rollback (binding)

**Purpose:** Safely activate or revert high-sensitivity governance toggles (waivers, residency overrides, cross-org pilots). **|**
**Contract:** Any activation flagged `unsafe` or touching governance scopes must follow this sequence before promotion. **|**
**State:** Runbook automation uses `ops/runbooks/settings_rollback.py`; evidence stores under `ops/settings/<date>/`. **|**
**Failure modes & handling:** Missing approvals or failed smoke tests require immediate rollback via `settings rollback --bundle <previous_id>`. **|**
**Observability:** Alert clears once activation completes with both approvals and validation metrics green. **|**
**References:** §4 State management, §5.1 Activation validator failure, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/runbooks/settings/governance_toggle.md`, tests `tests/platform/settings/test_rollback.py`, dashboard “Settings Governance”.

- Triggers: `settings_governance_override_total`, change tickets tagged `GOV-TOGGLE`, or manual escalation from Security/Architecture.
- Execution checklist:
  1. Announce maintenance window with activation/rollback times in `#ops-announcements`.
  2. Validate staging dry-run (matching bundle hash) and attach diff evidence to the change ticket.
  3. Execute activation via CLI/UI, capturing activation ID and `unsafe_reasons[]` result (expected empty).
  4. Run targeted smoke tests (API read/write, portal toggle, worker snapshot) tied to the toggle.
  5. Update change ticket and decision log with activation ID, evidence, and rollback window.
- Rollback steps: reapply prior bundle via `settings rollback --bundle <previous_id>`, verify `settings.changed` emission, rerun smoke tests, and communicate rollback rationale.
- Evidence requirements: store activation/rollback JSON artifacts under `ops/settings/<date>/`, append decision log entries with activation IDs, and attach customer/support comms templates.

<a id="rb-res-endpoint"></a>

### Settings — 8.3.3 RB-RES-ENDPOINT — Residency endpoint drift remediation (binding)

**Purpose:** Restore compliant residency posture when outbound endpoints drift or new hosts appear. **|**
**Contract:** Findings remain open until catalogue updates land or waivers capture dual approval and expiry. **|**
**State:** Findings persist in `residency_endpoint_findings`; evidence stored in `ops/residency/endpoint_scan.jsonl`. **|**
**Failure modes & handling:** Waivers lacking dual approval or missing catalogue updates keep the incident open and block affected activations. **|**
**Observability:** Alert `alert_residency_endpoint_drift` and dashboard “Residency & Endpoint Posture” track drift; auto-resolves after two clean scans and updated catalogue hashes. **|**
**References:** §5.3 Residency enforcement incident, §8.3.1 Runbook index, ADR-0004. **|**
**Breadcrumbs:** Runbook `ops/runbooks/settings/residency_endpoint_drift.md`, tests `tests/platform/settings/test_residency_triage.py::test_endpoint_drift_runbook`, Grafana dashboard “Residency & Endpoint Posture”.

Triage checklist:

1. Query `residency_endpoint_findings` for `state='open'`; review evidence attachments.
2. Inspect Istio AuthorizationPolicy revisions to ensure offending hosts remain blocked.
3. Identify impacted providers/orgs via activation diff linked in alert payload.

Decision tree:

- **Provider expansion** — Engage Reference Manager to ingest metadata, rerun `residency_endpoint_scan --host <fqdn>`, and promote Settings activation once SAN + GeoIP verified.
- **Configuration drift** — Update Settings bundle with corrected allowlist entries; require Security + Architecture approval before clearing the finding.
- **False positive** — Document justification, capture scan logs, and close after two consecutive clean scans.

Evidence: Attach updated catalogue hashes, scan output, and change ticket references to the incident log.

<a id="rb-res-block"></a>

### Settings — 8.3.4 RB-RES-BLOCK — Residency waiver / block handling (binding)

**Purpose:** Resolve residency policy blocks triggered during activations or runtime checks. **|**
**Contract:** Blocks clear only after org allowlists align with Reference Manager catalogues or waivers recorded with expiry and dual approval. **|**
**State:** Policy blocks logged as `RESIDENCY_POLICY_BLOCK`; waiver metadata stored in `settings_waiver`. **|**
**Failure modes & handling:** Waivers without expiry or missing approvals invalidate activation attempts; responders must remediate before promoting changes. **|**
**Observability:** Alert `alert_residency_policy_block` and dashboard “Residency Compliance” show resolution status. **|**
**References:** §5.3 Residency enforcement incident, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/runbooks/settings/residency_block.md`, tests `tests/platform/settings/test_residency_validators.py::test_block_requires_waiver`.

Steps:

1. Confirm org allowlists (`regions.allowlist.compute/storage/vector`).
2. Validate provider endpoints and DNS against RM catalogue snapshots.
3. If cross-region access required, capture dual approval, set `cross_region_waiver=true`, and document expiry.
4. Re-run activation or job; confirm Guardian manifests reference waiver ID.
5. Audit waiver usage daily until expiry or remediation.

<a id="rb-lock-006"></a>

### Settings — 8.3.5 RB-LOCK-006 — Activation lock stale detection & remediation (binding)

**Purpose:** Detect and remediate stuck activation locks without risking concurrent edits. **|**
**Contract:** Lock holders must release within `udlock.max_session_hold_seconds`; stale locks trigger this runbook. **|**
**State:** Lock registry tracked in `settings_activation_lock`; helper scripts expose current holders. **|**
**Failure modes & handling:** Forcing unlock without verifying holder state risks split-brain activations; follow the decision tree below. **|**
**Observability:** Alert `settings_activation_lock_wait_seconds` and dashboard “Settings Lock” confirm resolution. **|**
**References:** §4.3 Activation locks, §5.1 Activation validator failure, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/runbooks/settings/activation_lock.md`, tests `tests/platform/settings/test_locks.py::test_lock_scope`, script `scripts/settings/show_activation_locks.py`.

Checklist:

1. Inspect lock registry via `scripts/settings/show_activation_locks.py` filtered by environment.
2. Verify holder liveness (`SELECT ... FROM pg_stat_activity`) to differentiate idle vs active transactions.
3. If holder dead or idle-in-transaction, coordinate worker/web restart or issue `SELECT pg_terminate_backend(...)` per policy.
4. After release, rerun activation pipeline smoke tests; capture evidence in incident log.
5. File follow-up if lock reappears within 24h (root cause investigation, automation fix).

<a id="rb-llm-003"></a>

### Settings — 8.3.6 RB-LLM-003 — Provider degradation / circuit breaker (binding)

**Purpose:** Handle degraded LLM providers to protect cost and SLA budgets. **|**
**Contract:** OPEN circuits remain until provider health verifies; half-open probes follow the cadence defined here. **|**
**State:** Circuit state stored in `settings_llm_circuit`; fallback chains defined in Settings bundles. **|**
**Failure modes & handling:** Prematurely closing circuits or leaving fallback unmonitored risks runaway spend and job failures. **|**
**Observability:** Alert `alert_llm_circuit_open` and dashboard “FinOps – LLM Cost & Circuit” show circuit posture. **|**
**References:** §2.7 Provider governance, §5.2 Detector regression, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/runbooks/settings/provider_circuit_breaker.md`, tests `tests/platform/settings/test_llm_circuit.py::test_half_open_probe`, dashboard “FinOps – LLM Cost & Circuit”.

Response steps:

1. Confirm affected models via dashboard filters (`llm_circuit_state{model}`) and review recent error/latency metrics.
2. Validate fallback outcomes in logs (`PRIMARY_DEGRADED`, `FALLBACK_USED`) and ensure FinOps guardrails intact.
3. Keep circuits OPEN until three consecutive successful half-open probes; adjust fallback priorities if secondary models degrade.
4. Notify vendor/support with incident details when degradation persists > 15 minutes; record ticket IDs in incident log.
5. After recovery, document budget impact and corrective actions; update preventive tasks (synthetic prompts, timeout tuning).

<a id="rb-job-watchdog"></a>

### Settings — 8.3.7 RB-JOB-WATCHDOG — Job stall watchdog (binding)

**Purpose:** Restore stuck jobs and protect downstream SLAs when heartbeats lapse. **|**
**Contract:** Watchdog alerts trigger within `jobs.watchdog.no_progress_minutes` / `jobs.watchdog.timeout_minutes`; responders must either resume progress or terminate safely. **|**
**State:** Heartbeats stored in `job_progress_heartbeat`; remediation evidence captured in incident tickets (`ops/watchdog/<date>/`). **|**
**Failure modes & handling:** Premature termination can lose customer work; skipping checkpoint verification risks replaying corrupted artifacts. **|**
**Observability:** Alerts `job_watchdog_warning_total` and `job_watchdog_timeout_total` plus “Watchdog Runner” dashboards confirm recovery. **|**
**References:** §5.1 Activation validator failure, §8.3.1 Runbook index, Appendix B metrics. **|**
**Breadcrumbs:** Runbook `ops/runbooks/platform/job_watchdog.md`, tests `tests/platform/watchdog/test_job_timeout.py::test_timeout_escalation`.

Triage & remediation:

1. Identify affected job IDs from alert payload; confirm `job_progress_heartbeat` age and last known task lane.
2. Inspect worker logs for stalled tasks, resource exhaustion, or upstream dependency failures; capture excerpts in incident notes.
3. If work-in-progress artifacts exist, trigger checkpoint validation (`ops/jobs/verify_checkpoint.py`) before retrying.
4. Attempt safe resume via `jobs resume --job <id>` when the worker is healthy; otherwise cancel and requeue after addressing root cause.
5. Close alert once heartbeats refresh (< 2 × `jobs.watchdog.heartbeat_interval`) and audit trail updated.

Post-incident follow-up: file preventive tasks for repeated stalls and review `jobs.watchdog.*` thresholds for workload fit.

<a id="rb-upload-scan"></a>

### Settings — 8.3.8 RB-UPLOAD-SCAN — Upload scanning outage response (binding)

**Purpose:** Maintain quarantine-first posture when malware scanning or format validation degrades. **|**
**Contract:** New uploads remain blocked (`uploads.enabled=false`) until scanners return to green and evidence recorded per this runbook. **|**
**State:** Scan attempts logged in `upload_scan_audit`; quarantined objects isolated under `storage/quarantine/<job_id>/`. **|**
**Failure modes & handling:** Re-enabling uploads without updated signatures risks releasing infected files; overriding quarantine without approvals violates security policy. **|**
**Observability:** Alerts `upload_scan_error_total` and `upload_scan_queue_depth` alongside “Security — Upload Scanning” dashboard indicate recovery. **|**
**References:** §2.8 Security enforcement, §5.3 Residency enforcement incident, §8.3.1 Runbook index. **|**
**Breadcrumbs:** Runbook `ops/runbooks/security/upload_scan.md`, tests `tests/security/test_upload_scan_guard.py::test_quarantine_on_failure`, dashboard “Security — Upload Scanning”.

Response sequence:

1. Confirm scope of degradation (engine errors vs queue backlog) using dashboard drill-downs and `upload_scan_audit` sampling.
2. Freeze new intake by toggling `uploads.enabled=false` in Settings; announce customer impact and expected review window.
3. Validate scanner health: check signature freshness, sandbox resource utilization, and recent deployment changes.
4. For malware detections, coordinate with Security to analyze samples; maintain quarantine until signatures updated and retest passes.
5. Once scanners stable, re-enable uploads, replay quarantined items through the pipeline, and attach evidence to the incident record.
