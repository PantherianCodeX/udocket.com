# uDocket Runbook Catalog

<!-- AUTO-GENERATED: Run `python scripts/docs/build_runbook_catalog.py` to refresh. -->

## Digital Signer — 8.3 Runbooks & drills (binding)

**Purpose:** Maintain executable runbooks and drill cadence for key signing scenarios. **|**
**Contract:** Alerts map to RB-SIGN-* playbooks; quarterly drills rehearse trust-root renewal, TSA failover, FIPS recovery, and client acknowledgement remediation. **|**
**State:** Runbooks `ops/runbooks/signer/`, drill evidence `ops/security/key_rotation/<timestamp>/`, tabletop notes `ops/change/signer_rotations.ics`. **|**
**Failure modes & handling:** Stale runbooks or missing drill evidence block release sign-off until refreshed. **|**
**Observability:** Docs lint, PagerDuty analytics, Ops governance dashboards. **|**
**References:** RB-SIGN-TSA, RB-SIGN-FIPS, RB-SIGN-ACK, RB-SIGN-TRUSTROTATE. **|**
**Breadcrumbs:** Runbook files, rotation scripts, drill tracker. **|**

- RB-SIGN-TSA — TSA/OCSP outage response.
- RB-SIGN-FIPS — FIPS attestation recovery.
- RB-SIGN-ACK — Client acknowledgement remediation.
- RB-SIGN-TRUSTROTATE — Trust-root / certificate rotation checklist.

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

## Llm Registry — 8.1 Runbooks & drills (binding)

**Purpose:** Ensure on-call teams can remediate provider, safety, and cost incidents quickly. **|**
**Contract:** Alerts map to RB-LLM-003 (provider degradation), RB-LLM-JB (jailbreak/malicious output), RB-LLM-FINOPS (budget hold), RB-LLM-REPLAY (divergence). Runbook catalog must remain in sync with alert routing. **|**
**State:** Runbooks live in `ops/runbooks/llm/`, drill calendar `ops/change/llm_rotations.ics` tracks quarterly exercises. **|**
**Observability:** Docs CI validates runbook references; PagerDuty analytics monitor response metrics. **|**
**Breadcrumbs:** `ops/runbooks/index.md`, automation scripts `ops/scripts/llm/*.py`.

- Quarterly drills cover provider failover, moderation outage, FinOps budget breach, and replay divergence scenarios.
- Change calendar entries document golden-set updates and safety harness tuning; approvals captured in App.O decision logs.
- On-call rotation shared by Platform Architecture and Applied AI Programs; runbooks specify escalation matrix.

## Lp Engine — 8.3 Runbooks & drills (binding)

**Purpose:** Maintain authoritative recovery guides and drill expectations. **|**
**Contract:** Alerts in §8.2 map to RB-LPE identifiers; responders update the runbook index after each incident or quarterly tabletop. **|**
**State:** Runbooks live in `ops/runbooks/lpe/` with automation scripts under `ops/scripts/lpe/`; incident evidence attaches to App.O decision logs. **|**
**Failure modes & handling:** Missing or stale steps block deploy sign-off until the runbook is refreshed. **|**
**Observability:** Docs lint validates references; quarterly drill calendar tracks execution. **|**
**References:** §5 Failure modes, §8.1 Operational posture, §6 Observability. **|**
**Breadcrumbs:** Runbooks `ops/runbooks/lpe/*.md`, automation `ops/scripts/lpe/*.py`, tests `tests/ops/test_runbook_integrity.py`.

### Lp Engine — 8.3.1 Runbook index (informative)

- RB-LPE-COMPILER — Compiler regression / adoption freeze.
- RB-LPE-OPA-ROLLBACK — OPA bundle rollback & discovery remediation.
- RB-LPE-WAIVER — Waiver expiry response.
- RB-LPE-LOCALE-GAP — Localization coverage gap.

<a id="rb-lpe-compiler"></a>

### Lp Engine — 8.3.2 RB-LPE-COMPILER — Compiler regression & adoption freeze (binding)

**Purpose:** Restore compiler health when diff guards or adoption lags fail. **|**
**Contract:** Pause new publishes, roll back to last-good bundle, capture diff artefacts, and verify adoption across Guardian/Settings/Portal before resuming. **|**
**State:** Evidence stored in `ops/lpe/incidents/<date>/compiler/` with bundle hashes and diff exports. **|**
**Failure modes & handling:** Diff classification bugs, expired waivers, adoption lag; follow checklist to freeze, roll back, validate, and document. **|**
**Observability:** Alerts `lpe_compiler_duration_overrun`, `reference_bundle_stale_total`, `lpe_policy_block_total`. **|**
**Breadcrumbs:** Runbook `ops/runbooks/lpe/compiler.md`, automation `ops/scripts/lpe/deploy_bundle.py`, tests `tests/specs/test_lpe_compiler.py`.

Triggers: alerts `lpe_compiler_duration_overrun`, `lpe_bundle_signature_error`, change tickets tagged `LPE-COMPILER`, manual escalations from QA.

Execution checklist:

1. Freeze compiler pipeline (`lpe.compiler.enabled=false`) and announce in `#ops-announcements`.
2. Inspect diff artefacts; confirm affected locales/regions and whether unsafe flags were raised.
3. Promote previous good bundle via `ops/scripts/lpe/promote_bundle.py --bundle <id>` and capture hash evidence.
4. Re-run regression suite (`make lpe-compiler-regressions`) and snapshot Grafana panels for the incident ticket.
5. Coordinate Settings activation replay once bundle validated; update change ticket with evidence and adoption metrics.

Post-remediation:

- Resume compiler pipeline and monitor `lpe_compiler_duration_seconds` for two cycles.
- File corrective tasks (root cause, automation gaps) and attach diff artefacts to the App.O decision log.

<a id="rb-lpe-opa-rollback"></a>

### Lp Engine — 8.3.3 RB-LPE-OPA-ROLLBACK — OPA bundle rollback (binding)

**Purpose:** Recover from discovery or signature failures without policy gaps. **|**
**Contract:** Roll back to last-good bundle, flush caches, validate OPA `/status`, and gather evidence before returning traffic. **|**
**State:** Bundle manifests under `ops/lpe/opa_bundles/`; discovery audits in `ops/lpe/discovery_audit.jsonl`. **|**
**Failure modes & handling:** Missing signatures, discovery latency, cache poisoning; follow automated scripts to redeploy and verify. **|**
**Observability:** Alerts `lpe_bundle_signature_error`, `opa_discovery_stale_total`. **|**
**Breadcrumbs:** Runbook `ops/runbooks/lpe/opa_bundle_rollback.md`, automation `ops/scripts/lpe/deploy_opa_bundle.py`, `scripts/opa/flush_cache.py`.

Response steps:

1. Capture failing discovery IDs and affected services from alert payload.
2. Roll back via `ops/scripts/lpe/deploy_opa_bundle.py --bundle <last_good>` and flush worker caches (`scripts/opa/flush_cache.py`).
3. Validate OPA `/status` and `/health` endpoints plus policy unit tests (`pytest tests/opa/test_policy_context.py`).
4. Notify dependent teams (Settings, Guardian, Reference Manager) and confirm cached digests refresh.
5. Attach bundle hashes, validation output, and Grafana snapshots to the incident ticket.

Follow-up:

- Run `ops/scripts/lpe/discovery_audit.py` to confirm discovery parity within 30 minutes.
- File preventive tasks for root cause (compiler bug, Settings drift, CDN failure).

<a id="rb-lpe-waiver"></a>

### Lp Engine — 8.3.4 RB-LPE-WAIVER — Waiver expiry response (binding)

**Purpose:** Maintain compliant residency posture when waivers expire. **|**
**Contract:** Renew with dual approvals or decommission before expiry; update Settings allowlists and run verification scripts. **|**
**State:** Waiver ledger `ops/lpe/waivers.yaml`, renewal artefacts `ops/lpe/waiver_reviews/<date>/`. **|**
**Failure modes & handling:** Expired waivers, missing approvals; escalate to Security + Architecture and document outcomes. **|**
**Observability:** Alerts `lpe_policy_block_spike`, `waiver_expiring_total`. **|**
**Breadcrumbs:** Runbook `ops/runbooks/lpe/waiver_expiry.md`, automation `ops/scripts/lpe/check_waivers.py`.

Checklist:

1. Review waiver ledger for entries expiring within the alert window; confirm impacted locales and providers.
2. Engage Security + Architecture for renewal decision; capture approvals in the decision log.
3. If waiver retired, update Settings allowlists and trigger §8.3.5 RB-LPE-LOCALE-GAP if localization fallback required.
4. Run `ops/scripts/lpe/check_waivers.py --verify` to ensure updated posture and attach output to the incident ticket.
5. Communicate outcome to affected product owners and document customer impact, if any.

Audit trail:

- Store approvals, renewal artefacts, and communication templates alongside the incident log.
- Schedule follow-up review to validate long-term remediation (automation fix, localization updates).

<a id="rb-lpe-locale-gap"></a>

### Lp Engine — 8.3.5 RB-LPE-LOCALE-GAP — Localization coverage gap (binding)

**Purpose:** Restore localization completeness when translations or QA artefacts regress. **|**
**Contract:** Deliver missing translations, QA recordings, and screenshots before re-enabling locales; Settings activation stays frozen until artefacts pass review. **|**
**State:** Locale inventories `ops/lpe/locales.csv`, QA artefacts in `ops/localization/*`. **|**
**Failure modes & handling:** Missing pseudolocale output, accessibility evidence, or localization tests; follow runbook to gather artefacts and rerun checks. **|**
**Observability:** Alerts `lpe_localization_gap_total`, pseudolocale CI, Playwright RTL snapshots. **|**
**Breadcrumbs:** Runbook `ops/runbooks/lpe/locale_gap.md`, automation `ops/scripts/lpe/audit_locales.py`, tests `tests/e2e/test_portal_policy_context.py`.

Resolution steps:

1. Identify affected locales and impacted surfaces (portal, Guardian, notifications) from alert payload.
2. Coordinate with Localization program to deliver missing translations and QA recordings; update Appendix A checklist items.
3. Validate `ops/scripts/lpe/audit_locales.py` passes for affected locales and attach proof to the incident ticket.
4. Run synthetic checks (`tests/e2e/test_portal_policy_context.py::test_disclaimer_l10n`) to confirm correct copy rendering.
5. Update Settings bundles and trigger an LPE compiler rebuild; monitor `lpe_lookup_latency_p95_breach` for regression.

Post-checks:

- Log decision record in App.O with locale IDs, remediation timeline, and QA sign-offs.
- Schedule follow-up audit within one release cycle to verify coverage remains intact.

## Notifications — 8) Operations & runbooks

**Purpose:** Maintain resilient notification delivery, provider readiness, and compliance evidence. **|**
**Contract:** On-call rotations, runbooks, drills, and release workflows must remain current; notification channels pause when health or compliance gates fail until remediation completes. **|**
**State:** Runbooks under `ops/runbooks/notifications/`, drill evidence `ops/notifications/drills/<date>/`, DMARC onboarding reports `ops/notifications/dmarc/`, STOP/HELP audit logs in App.O. **|**
**Failure modes & handling:** Stale playbooks, missed drills, or expired DMARC/SPF attestations trigger incidents and block change approvals. **|**
**Observability:** Docs lint (`build_runbook_catalog.py --check`), dashboards “Notifications Delivery” / “In-App Notifications”, alert `alert_notifications_delivery_health`. **|**
**Breadcrumbs:** Runbook catalog `docs/src/ops/runbooks/index.md`, drill scheduler `ops/scripts/notifications/schedule_drills.py`, provider automation `ops/scripts/notifications/*.py`. **|**
**References:** §5 Failure modes, §6 Observability, §7 Security & compliance, Ops governance policy App.N. **|**

### Notifications — 8.1 Operational posture (binding)

**Purpose:** Capture on-call coverage, freeze windows, and readiness expectations. **|**
**Contract:** Platform Engineering (queue health) and Operations Engineering (provider integrations) share PagerDuty “Notifications SLO”, staff a 24/7 rotation, and honor change freezes during major provider cutovers. **|**
**State:** Roster `ops/notifications/roster.yaml`, freeze calendar `ops/notifications/freeze_windows.ics`, provider credential inventory `ops/notifications/provider_credentials.md`. **|**
**Failure modes & handling:** Staffing gaps or ignored freezes trigger management review; deployments pause until coverage restored. **|**
**Observability:** PagerDuty analytics, delivery dashboards, alert `notifications_oncall_gap_total`. **|**
**References:** Notifications spec §7, RB-NOTIFY-*. **|**
**Breadcrumbs:** Roster docs, freeze calendars, App.O escalation notes. **|**

### Notifications — 8.2 Incident triggers (binding)

**Purpose:** Map alerts and dashboards to notification runbooks so responders act immediately. **|**
**Contract:** Alert rules (`infra/monitoring/notifications-prometheus-rules.yaml`) embed RB-NOTIFY-* identifiers; evidence logged before closing incidents. **|**
**State:** Incident records `ops/notifications/incidents/<date>.jsonl` capture provider, channel, and alert metadata. **|**
**Failure modes & handling:** Missing annotations or muted routes require corrective PRs and Ops governance follow-up. **|**
**Observability:** Dashboards “Notifications Delivery”, “SMS Compliance”, Alertmanager routes. **|**
**References:** §5 Failure modes, RB-NOTIFY-OUTAGE, RB-NOTIFY-WEBHOOK, RB-NOTIFY-SMS, RB-NOTIFY-TOKEN. **|**
**Breadcrumbs:** Alert rule files, PagerDuty services, SIEM integrations. **|**

- `alert_notifications_delivery_health` detects provider degradation and opens RB-NOTIFY-OUTAGE.
- `alert_notifications_sms_compliance` / `notifications_sms_stop_spike_total` drive RB-NOTIFY-SMS for STOP/HELP surges and regulatory response.
- `notifications_token_abuse_total` escalates access breaches via RB-NOTIFY-TOKEN.
- `notifications_webhook_signature_fail_total` triggers RB-NOTIFY-WEBHOOK for signature rotation and backlog replay.

### Notifications — 8.3 Runbooks & drills (binding)

**Purpose:** Keep playbooks executable and drills current for core notification scenarios. **|**
**Contract:** Alerts map to RB-NOTIFY-* runbooks; quarterly drills rehearse provider failover, webhook compromise, STOP/HELP compliance surges, and download-token abuse investigations. **|**
**State:** Runbooks `ops/runbooks/notifications/*.md`, drill evidence `ops/notifications/drills/<date>/summary.md`. **|**
**Failure modes & handling:** Missing drill evidence or outdated steps block change approval until updated. **|**
**Observability:** Docs lint, Ops governance dashboards, drill scheduler reports. **|**
**References:** RB-NOTIFY-OUTAGE, RB-NOTIFY-WEBHOOK, RB-NOTIFY-SMS, RB-NOTIFY-TOKEN. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler, Slack `#ops-notifications`. **|**

| Runbook code      | Scenario                                   | Notes |
| ----------------- | ------------------------------------------ | ----- |
| RB-NOTIFY-OUTAGE  | Provider outage / degraded delivery        | Provider escalation paths, failover to backup channel |
| RB-NOTIFY-WEBHOOK | Webhook signature drift / compromise       | Key rotation, backlog replay, SIEM coordination |
| RB-NOTIFY-SMS     | STOP/HELP surge & regulatory response      | Compliance scripts, opt-in reinstatement |
| RB-NOTIFY-TOKEN   | Download token abuse or leak               | Token rotation, artifact quarantine |

### Notifications — 8.4 Migrations & backfills (normative)

**Purpose:** Govern provider onboarding, template migrations, and DLQ replays. **|**
**Contract:** Provider credential rotations and template migrations require change tickets, dry-run evidence, and rollback plans; DLQ replays run in preview before promotion. **|**
**State:** Migration scripts `ops/scripts/notifications/onboard_provider.py`, template bundles `config/notifications/templates/*.json`, DLQ replay logs `ops/notifications/dlq_replay/<date>/`. **|**
**Failure modes & handling:** Failed migrations revert to previous provider/template and open RB-NOTIFY-OUTAGE; replay failures quarantine payloads until corrected. **|**
**Observability:** Metrics `notifications_migration_success_total`, `notifications_dlq_replay_total`, App.O change tickets. **|**
**References:** Settings spec §5, Notifications spec §4. **|**
**Breadcrumbs:** Migration scripts, template bundles, DLQ tooling. **|**

### Notifications — 8.5 Operational workflows (normative)

**Purpose:** Document recurring tasks that sustain notification compliance and quality. **|**
**Contract:** Teams review DMARC/SPF attestations quarterly, refresh STOP/HELP evidence, generate weekly residency digests, and audit digest accuracy before distribution. **|**
**State:** DMARC reports `ops/notifications/dmarc/<quarter>/`, residency digests `ops/residency/digest_<iso_week>.json`, STOP/HELP audit logs `ops/notifications/sms_opt_out.csv`. **|**
**Failure modes & handling:** Expired DMARC alignment or missing digests trigger RB-NOTIFY-SMS and governance follow-up; digest discrepancies open App.O remediation tasks. **|**
**Observability:** Metrics `notifications_digest_generated_total`, `notifications_dmca_alignment_total`, STOP/HELP dashboards in SIEM. **|**
**References:** §7 Security & compliance, §4 State management. **|**
**Breadcrumbs:** Digest generator `apps/platform/operations/task_modules/notifications.py::generate_digest`, compliance scripts `ops/scripts/notifications/audit_opt_out.py`. **|**

- Weekly residency digests aggregate waivers, remediation SLAs, and provider drift; evidence archived alongside digests.
- STOP/HELP audit jobs reconcile opt-out state with provider receipts to enforce compliance.
- DMARC/SPF attestations renewed before enabling custom sender domains; automation blocks production traffic when alignment lapses.

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
**Contract:** Alerts enumerated in §8.2 and Appendix B map to RB-\* identifiers documented here; responders update these runbooks after every incident or drill. **|**
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

## Web App — 8) Operations & runbooks

**Purpose:** Keep the staff workspace and client portal operationally ready while satisfying security and compliance controls. **|**
**Contract:** Runbooks, drills, and release workflows must stay current; UI surfaces pause when alert gates or evidence requirements fail. **|**
**State:** Runbooks in `ops/runbooks/webapp/` and `ops/runbooks/notifications/`, drill evidence `ops/webapp/drills/<date>/`, freeze calendars `ops/webapp/freeze_windows.ics`. **|**
**Failure modes & handling:** Stale playbooks, missed drills, or expired freezes block deployments until remediation and evidence capture. **|**
**Observability:** Docs lint (`build_runbook_catalog.py --check`), dashboards “Portal Integrity”/“Operator Workspace”, alert `portal_link_invalidated_total`. **|**
**Breadcrumbs:** Runbook index `docs/src/ops/runbooks/index.md`, drill scripts `ops/scripts/webapp/schedule_drills.py`, governance policies App.N. **|**
**References:** §5 Failure modes, §6 Observability, §7 Security & compliance. **|**

### Web App — 8.1 Operational posture (binding)

**Purpose:** Document on-call coverage, freeze windows, and readiness assumptions for the web application. **|**
**Contract:** Platform Engineering owns PagerDuty “WebApp SLO”, enforces release freezes during major UI migrations, and keeps portal/privacy SMEs on-call for high-severity incidents. **|**
**State:** Roster `ops/webapp/roster.yaml`, freeze calendar `ops/webapp/freeze_windows.ics`, contact matrix in App.N. **|**
**Failure modes & handling:** Unstaffed shifts or ignored freezes escalate to Product & Security; deployments halted until posture restored. **|**
**Observability:** PagerDuty metrics, freeze dashboards, alert `webapp_oncall_gap_total`. **|**
**References:** Notifications spec §7, Settings spec §7. **|**
**Breadcrumbs:** Roster files, freeze calendars, App.O decision logs. **|**

### Web App — 8.2 Incident triggers (binding)

**Purpose:** Tie UI alerts to playbooks so responders execute consistent recovery steps. **|**
**Contract:** Alert rules (`infra/monitoring/webapp-prometheus-rules.yaml`) annotate RB-\* identifiers; incidents log evidence before closure. **|**
**State:** Incident records `ops/webapp/incidents/<date>.jsonl` capture alert, context, and applied runbook. **|**
**Failure modes & handling:** Missing annotations or muted alerts require corrective PRs and governance follow-up. **|**
**Observability:** Dashboards “Operator Workspace”, “Portal Integrity”, Alertmanager routes. **|**
**References:** RB-JOB-WATCHDOG, RB-PORTAL-INVALIDATION, RB-CHAT-ABUSE. **|**
**Breadcrumbs:** Alert rule files, PagerDuty services, SIEM dashboards. **|**

- `portal_link_invalidated_total` spikes or `portal_download_precondition_total` errors invoke RB-PORTAL-INVALIDATION.
- `sse_connection_drop_total` sustained > threshold drives SSE recovery drills via RB-JOB-WATCHDOG.
- `chat_policy_block_total` / `chat_abuse_alert_total` escalate to RB-CHAT-ABUSE.
- Accessibility monitors (axe regression jobs) failing in CI pause releases and trigger RB-LPE-LOCALE-GAP before resuming deployments.

### Web App — 8.3 Runbooks & drills (binding)

**Purpose:** Keep UI runbooks executable and drills on cadence. **|**
**Contract:** Alerts map to RB-\* playbooks; quarterly exercises cover SSE resiliency, portal abuse investigation, accessibility audits, and assistant abuse response. **|**
**State:** Runbooks `ops/runbooks/webapp/*.md`, evidence `ops/webapp/drills/<date>/`. **|**
**Failure modes & handling:** Missing drill evidence or outdated steps block release approval until updated. **|**
**Observability:** Docs lint, drill scheduler reports, governance dashboards. **|**
**References:** RB-JOB-WATCHDOG, RB-PORTAL-INVALIDATION, RB-LPE-LOCALE-GAP, RB-NOTIFY-\*, RB-CHAT-ABUSE. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler, governance policy App.N. **|**

| Runbook code | Scenario | Notes |
| ------------ | -------- | ----- |
| RB-JOB-WATCHDOG | SSE/worker watchdog remediation | Coordinated with worker cluster for stalled jobs |
| RB-PORTAL-INVALIDATION | Token revocation / portal link cleanup | Revokes signed URLs, notifies clients, captures evidence |
| RB-LPE-LOCALE-GAP | Localization/accessibility gap | Coordinates with LP Engine for missing locales |
| RB-NOTIFY-\* | Delivery incidents | Aligns portal alerts with outbound notifications |
| RB-CHAT-ABUSE | Assistant abuse or moderation escalation | Disables assistants, gathers evidence for Security |

### Web App — 8.4 Migrations & backfills (normative)

**Purpose:** Govern CDN cache pushes, static asset migrations, and portal data backfills. **|**
**Contract:** UI asset migrations require change tickets, blue/green verification, and rollback plans; backfills of portal metadata run in read-only preview before publishing. **|**
**State:** Migration scripts `ops/scripts/webapp/deploy_assets.py`, cache manifests `ops/webapp/cdn_manifest.json`, backfill logs `ops/webapp/backfill/<date>/`. **|**
**Failure modes & handling:** Failed migrations revert to prior asset version; incomplete backfills trigger RB-PORTAL-INVALIDATION to prevent stale downloads. **|**
**Observability:** Metrics `webapp_asset_publish_total`, `webapp_backfill_success_total`. **|**
**References:** Settings spec §5, Notifications spec §4. **|**
**Breadcrumbs:** Asset deployment scripts, CDN manifests, backfill tooling. **|**

### Web App — 8.5 Operational workflows (normative)

**Purpose:** Document recurring tasks for portal/workspace hygiene. **|**
**Contract:** Teams review portal invalidations daily, reconcile signed download tokens, audit assistant manifests, and validate accessibility snapshots. **|**
**State:** Token reconciliation reports `ops/webapp/token_audit/<date>.csv`, accessibility evidence `ops/webapp/accessibility/<run_id>/`, assistant manifest reviews `ops/webapp/chat_manifest_checks.md`. **|**
**Failure modes & handling:** Missing audits trigger RB-PORTAL-INVALIDATION or RB-CHAT-ABUSE follow-up; unresolved accessibility gaps block release. **|**
**Observability:** Metrics `download_token_validation_total{outcome}`, `chat_sessions_total{audience}`, accessibility CI dashboards. **|**
**References:** §4 State management, §7 Security & compliance. **|**
**Breadcrumbs:** Token audit scripts `ops/scripts/webapp/audit_tokens.py`, accessibility CI configs, assistant manifest validators. **|**

- Daily token audits reconcile download tokens with Guardian artefact states and revoke stale entries.
- Weekly assistant manifest reviews ensure disclaimers and policy contexts match Settings snapshots.
- Accessibility jobs (axe/playwright) capture evidence for auditors; failures raise App.O tasks and hold releases.

______________________________________________________________________

## Worker Cluster — 8) Operations & runbooks

**Purpose:** Maintain the worker fleet’s readiness, watchdog coverage, and remediation playbooks. **|**
**Contract:** On-call rotations, runbooks, and drills must remain current; queues pause when automation gates fail until remediation completes. **|**
**State:** Runbooks in `ops/runbooks/worker/`, drill evidence `ops/workers/drills/<date>/`, freeze calendars `ops/workers/freeze_windows.ics`. **|**
**Failure modes & handling:** Stale playbooks, missed drills, or unstaffed rotations block change approvals and keep automation paused. **|**
**Observability:** Docs lint (`build_runbook_catalog.py --check`), dashboards “Worker Queues”/“Watchdog Runner”, alert `watchdog_runner_missed_total`. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler `ops/scripts/worker/schedule_drills.py`, governance policies App.N. **|**
**References:** §5 Failure modes, §6 Observability, §7 Security & compliance. **|**

### Worker Cluster — 8.1 Operational posture (binding)

**Purpose:** Capture staffing and readiness expectations for the worker cluster. **|**
**Contract:** Platform Engineering staffs PagerDuty “Worker Queue SLO”, maintains blue/green deployment freezes during major migrations, and ensures watchdog-runner automation continues within ±60s schedule. **|**
**State:** Roster `ops/workers/roster.yaml`, freeze calendar `ops/workers/freeze_windows.ics`, watchdog timer reports `ops/workers/watchdog_status.json`. **|**
**Failure modes & handling:** Staffing gaps or missed watchdog runs trigger RB-JOB-WATCHDOG before resuming automation. **|**
**Observability:** PagerDuty metrics, watchdog dashboards, alert `watchdog_runner_missed_total`. **|**
**References:** RB-JOB-WATCHDOG, §6 Observability. **|**
**Breadcrumbs:** Roster files, freeze calendars, watchdog status logs. **|**

### Worker Cluster — 8.2 Incident triggers (binding)

**Purpose:** Map queue and automation alerts to worker runbooks. **|**
**Contract:** Alert rules (`infra/monitoring/worker-prometheus-rules.yaml`) embed RB-\* identifiers; responders capture evidence before resolving. **|**
**State:** Incident records `ops/workers/incidents/<date>.jsonl` document alert context and applied remediation. **|**
**Failure modes & handling:** Missing annotations or silenced alerts require governance review and follow-up tasks. **|**
**Observability:** Dashboards “Worker Queues”, “Watchdog Runner”, Alertmanager routes. **|**
**References:** RB-JOB-WATCHDOG, RB-LOCK-006, RB-NOTIFY-\*. **|**
**Breadcrumbs:** Alert rule files, PagerDuty services, SIEM dashboards. **|**

- `celery_queue_depth_high` / `dlq_messages_total` breaches invoke RB-JOB-WATCHDOG and RB-NOTIFY-OUTAGE for queue remediation.
- `watchdog_runner_missed_total` or `watchdog_runner_lag_seconds` triggers RB-JOB-WATCHDOG to restore automation.
- `rls_context_missing_total` escalates to RB-LOCK-006 to re-establish GUC guards.
- `upload_scan_error_total` routes to RB-UPLOAD-SCAN; `case_import_failure_total` invokes RB-CASE-IMPORT.

### Worker Cluster — 8.3 Runbooks & drills (binding)

**Purpose:** Keep worker playbooks current and drills executed on schedule. **|**
**Contract:** Alerts map to RB-\*; quarterly exercises cover watchdog stalls, provider failover simulations, queue backlog remediation, and DLQ replay drills. **|**
**State:** Runbooks `ops/runbooks/worker/*.md`, drill evidence `ops/workers/drills/<date>/`. **|**
**Failure modes & handling:** Missing drill evidence or outdated steps block automation restart after incidents. **|**
**Observability:** Docs lint, drill scheduler reports, Ops governance dashboards. **|**
**References:** RB-JOB-WATCHDOG, RB-LOCK-006, RB-NOTIFY-\*, RB-UPLOAD-SCAN, RB-CASE-IMPORT. **|**
**Breadcrumbs:** Runbook catalog, drill scheduler, Ops governance records. **|**

| Runbook code | Scenario | Notes |
| ------------ | -------- | ----- |
| RB-JOB-WATCHDOG | Queue/backlog remediation & watchdog stall | Coordinates pause/resume, collects evidence |
| RB-LOCK-006 | Advisory lock / activation lock remediation | Clears stale locks before re-running jobs |
| RB-NOTIFY-\* | Delivery queue backlog | Shared with notifications service |
| RB-UPLOAD-SCAN | Upload scanning outage | Quarantines staging blobs, restarts scanners |
| RB-CASE-IMPORT | Legacy case import failure | Replays bundles, validates manifests |

### Worker Cluster — 8.4 Migrations & backfills (normative)

**Purpose:** Manage queue migrations, Celery upgrades, and DLQ replays. **|**
**Contract:** Queue renames and Celery upgrades require change tickets, KEDA dry runs, and rollback plans; DLQ replays run in preview before promotion. **|**
**State:** Migration scripts `ops/scripts/worker/migrate_queue.py`, upgrade playbooks `ops/runbooks/worker/celery_upgrade.md`, DLQ replay logs `ops/workers/dlq_replay/<date>/`. **|**
**Failure modes & handling:** Failed migrations revert to prior queue configuration; replay failures quarantine payloads for manual inspection. **|**
**Observability:** Metrics `worker_migration_success_total`, `dlq_replay_success_total`, change tickets in App.O. **|**
**References:** §4 State management, Notifications spec §4. **|**
**Breadcrumbs:** Migration scripts, upgrade playbooks, DLQ tooling. **|**

### Worker Cluster — 8.5 Operational workflows (normative)

**Purpose:** Document recurring worker tasks (queue audits, watchdog verification, capacity reviews). **|**
**Contract:** Teams review queue depth daily, reconcile watchdog heartbeat reports, audit Settings snapshot adoption, and refresh worker autoscaling parameters quarterly. **|**
**State:** Queue audit reports `ops/workers/queue_audit/<date>.csv`, watchdog summaries `ops/workers/watchdog_status.json`, capacity review decks `ops/workers/capacity/<quarter>.pptx`. **|**
**Failure modes & handling:** Missing audits trigger RB-JOB-WATCHDOG follow-up; outdated scaling parameters escalate via Ops governance. **|**
**Observability:** Metrics `celery_queue_depth`, `watchdog_runner_lag_seconds`, capacity dashboards. **|**
**References:** Settings spec §6, LLM registry spec §2.4. **|**
**Breadcrumbs:** Audit scripts `ops/scripts/worker/audit_queues.py`, watchdog tools, capacity planning docs. **|**

- Daily queue audits catch runaway jobs and coordinate with agent owners for mitigation.
- Weekly watchdog verifications ensure metrics, SSE, and logs reflect automation health.
- Quarterly capacity reviews adjust KEDA/HPA thresholds and record scaling decisions in Ops governance.

______________________________________________________________________
