# uDocket Runbook Catalog

<!-- AUTO-GENERATED: Run `python scripts/docs/build_runbook_catalog.py` to refresh. -->

## Guardian Service — Appendix R — Runbooks & drills (binding)

**Breadcrumbs:** Implementation `ops/runbooks/guardian/`, Tests `tests/ops/test_runbook_integrity.py::test_guardian_runbooks`, Observability PagerDuty service “Guardian SLO” with Grafana dashboard “Guardian SLO”.\\ *Purpose: Maintain actionable Guardian recovery guides and manual review playbooks.*\\ *Contract: Alerts enumerated in §7 map to RB-GUARD identifiers here; responders update these procedures after every incident or drill.*\\ *State: Procedures live beside automation scripts in `ops/runbooks/guardian/`; this appendix summarizes triggers, decision trees, and evidence requirements.*\\ *Failure modes & retries: Missing or stale procedures trigger corrective actions and block deploy sign-off.*\\ *Observability: Incident retros attach the executed RB-GUARD identifier and confirm Appendix R coverage during quarterly reviews.*

### Guardian Service — R.1 Response index (informative)

- RB-GUARD-001 — Guardian SLO breach stabilization.
- RB-GUARD-QUAR — Quarantine spike investigation.
- RB-GUARD-QUEUE — Submission backlog watchdog.
- RB-GUARD-MANUAL — Manual review reconciliation.

<a id="rb-guard-001"></a>

### Guardian Service — R.2 RB-GUARD-001 — Guardian SLO breach (binding)

**Breadcrumbs:** Implementation `ops/runbooks/guardian/slo_breach.md`, Automation `ops/scripts/guardian/scale_guardian.py`, Tests `tests/ops/test_runbook_integrity.py::test_guardian_slo_runbook`, Observability Grafana dashboard “Guardian SLO” (alerts `guardian_judgment_latency_seconds`, `guardian_submission_timeout_total`).\\ *Purpose: Restore Guardian availability and route artifacts through manual review when automated judgments breach SLO.*\\ *Contract: Any breach of the availability or latency SLO uses this sequence before re-enabling automated progression.*\\ *State: Manual review ledger entries persist under `ops/guardian/manual_review/<date>.jsonl`.*\\ *Failure modes & retries: Skipping manual review tracking risks losing audit history and invalidating waivers.*\\ *Observability: Alert clears after two healthy scrapes and manual review backlog drains.*

- **Signals:** `guardian_judgment_latency_seconds` P95 > SLO, `guardian_submission_timeout_total` increasing, synthetic job failure (`guardian_slo.yaml`).
- **Triage (≤5 minutes):**
  1. Check `/readyz` and `/synthetic/status`; capture latency panels in Grafana (“Guardian SLO”).
  1. Confirm queue depth (`guardian_pending_total`, `guardian_pending_oldest_seconds`) and worker health (Celery heartbeat, pod restarts).
  1. Inspect recent deploys/settings (`guardian.rules.version`, Helm releases) for regressions.
- **Decision tree:**
  - *Service unhealthy*: place Guardian in manual review mode (pause submissions, notify ops). Operators record `MANUAL_GUARDIAN_JUDGMENT` artifacts while following this checklist.
  - *Compute exhaustion*: scale deployment (`kubectl -n platform scale deploy/guardian --replicas=<n>`), update HPA floor post-incident.
  - *Upstream dependency slowdown*: coordinate with LPE/Settings owners; consider throttling new submissions until latency stabilizes.
- **Post-remediation:**
  - Ensure `guardian_judgment_latency_seconds` P95 ≤ SLO for 2 consecutive scrapes and `guardian_submission_timeout_total` plateaued.
  - Clear manual review backlog by replaying queued artifacts once service healthy; annotate incident log with root cause and follow-ups.

<a id="rb-guard-quar"></a>

### Guardian Service — R.3 RB-GUARD-QUAR — Quarantine spike investigation (binding)

**Breadcrumbs:** Implementation `ops/runbooks/guardian/quarantine_spike.md`, Automation `ops/scripts/guardian/replay_quarantine.py`, Tests `tests/ops/test_runbook_integrity.py::test_guardian_quarantine_runbook`, Observability Grafana dashboard “Guardian Enforcement” (alert `alert_guardian_quarantine_spike`).\\ *Purpose: Diagnose QUARANTINED spikes without bypassing policy controls.*\\ *Contract: Any surge in quarantine outcomes requires this investigation before promoting new releases or waivers.*\\ *State: Findings logged under `ops/guardian/quarantine/<incident_id>.md` with root-cause summary and evidence attachments.*\\ *Failure modes & retries: Missing waiver documentation or misaligned settings snapshots risk repeat incidents.*\\ *Observability: Alert resolves when `guardian_cleared_ratio` recovers and reason-code distribution returns to baseline.*

- **Signals:** Increased `guardian_policy_block_total{reason=...}` (e.g., `POLICY_FORBIDDEN_PATTERN`, `INTEGRITY_HASH_MISMATCH`, `SOURCE_NOT_APPROVED`); drop in `OPERATOR_PREP`/`QUEUED_FOR_REVIEW` backlog throughput.
- **Triage:**
  1. Filter Guardian dashboard by `reason_codes[]` and `org_id` to locate affected cohorts.
  1. Sample judgments from `guardian_judgment_history_secure`; confirm `guardian.rules.version` and `settings_snapshot_sha256` alignment.
  1. For `INTEGRITY_HASH_MISMATCH`, verify upload finalize and recompute hashes; for `SOURCE_NOT_APPROVED`, ensure upstream artifacts cleared.
- **Decision:**
  - `POLICY_FORBIDDEN_PATTERN`: engage Product/QA; adjust templates or policies; consider waiver only with dual approval.
  - `SOURCE_NOT_APPROVED`: instruct operators to remediate upstream artifacts or rebind inputs; Guardian enforces parent gating.
  - Region/debug issues: enforce settings fix, resubmit, and confirm waiver stamping (`RESIDENCY_WAIVER_USED`) where applicable.
- **Post-remediation:** Track `guardian_cleared_ratio` recovery, log incident with counts per reason, and file rule-tuning tasks if false positives exceed thresholds.

<a id="rb-guard-queue"></a>

### Guardian Service — R.4 RB-GUARD-QUEUE — Submission backlog watchdog (binding)

**Breadcrumbs:** Implementation `ops/runbooks/guardian/submission_backlog.md`, Automation `ops/scripts/guardian/queue_drain.py`, Tests `tests/ops/test_runbook_integrity.py::test_guardian_queue_runbook`, Observability Grafana dashboard “Guardian Queue Health” (alert `alert_guardian_queue_stale`).\\ *Purpose: Restore submission throughput before `PENDING_JUDGMENT` artifacts stall.*\\ *Contract: Any backlog alert follows this playbook before artifacts are promoted or waived.*\\ *State: Queue samples exported to `ops/guardian/queue_samples/<timestamp>.csv` for audit.*\\ *Failure modes & retries: Failing to drain backlog before resuming automation risks out-of-order judgments.*\\ *Observability: Alert resolves when backlog age drops below threshold and throughput returns to baseline.*

- **Signals:** `guardian_pending_total` trending upward for 3 scrapes, `guardian_pending_oldest_seconds` > `guardian.queue.backlog_alert_minutes * 60`, `guardian_submission_timeout_total` incrementing, `review_queue_oldest_seconds` approaching `reviews.backlog.alert_minutes`.
- **Triage (≤5 minutes):**
  1. Verify Guardian health endpoints and latency dashboards.

  1. Inspect queue detail:

     ```sql
     SELECT artifact_id,
            org_id,
            submitted_at,
            now() - submitted_at AS age,
            last_heartbeat_at,
            judgment_attempts
       FROM guardian_submission_queue
     ```
  ORDER BY submitted_at LIMIT 50;
  ```

  3. Sample worker logs for `FAILED_GUARDIAN_TIMEOUT`; confirm Celery pods healthy.
  4. Review recent `guardian.rules.version` activations and Guardian deploys for regressions.
  ```
- **Decision:**
  - *Compute exhaustion*: raise HPA floor, ensure DB connections within pool limits, restart pods after scaling.
  - *Policy/rules regression*: roll back offending ruleset or apply waiver/manual review following RB-GUARD-001.
  - *External dependency degradation*: coordinate with LPE/Settings teams, throttle submissions if upstream latency high.
- **Post-remediation:**
  - Confirm `guardian_pending_total` below alert threshold and `guardian_pending_oldest_seconds` \< 120s for two scrapes.
  - Ensure `guardian_submission_timeout_total` stopped increasing and queued artifacts receive fresh judgments.
  - Document incident with root cause, remediation, SQL excerpt, and follow-up tasks; update HPA/alert thresholds if burst patterns changed.

<a id="rb-guard-manual"></a>

### Guardian Service — R.5 RB-GUARD-MANUAL — Manual review reconciliation (informative)

**Breadcrumbs:** Implementation `ops/runbooks/guardian/manual_review.md`, Automation `ops/scripts/guardian/reconcile_manual.py`, Tests `tests/ops/test_runbook_integrity.py::test_guardian_manual_runbook`, Observability Grafana dashboard “Guardian Manual Review” (panels `guardian_manual_pending_total`, `guardian_manual_age_seconds`).\\ *Purpose: Ensure manual decisions stay auditable and rejoin automated flow once Guardian recovers.*\\ *Contract: Manual review ledger updates must precede replay jobs so judgment history remains complete.*\\ *State: Ledger updates stored alongside incident tickets within `ops/guardian/manual_review/<date>.jsonl`.*\\ *Failure modes & retries: Omitting ledger updates or skipping reconciliation replays invalidates artifact provenance.*\\ *Observability: Manual review metrics return to baseline before incident closure.*

- Operators record manual decisions with manifest annotations while Guardian automation is paused.
- Reconciliation job replays queued artifacts once health recovers; incident owners capture waiver IDs, policy bundle hashes, and remediation tasks in the postmortem per RB-GUARD-001 follow-up checklist.

______________________________________________________________________

## Localization & Policy Engine — Appendix R — Runbooks & drills (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/`, Tests `tests/ops/test_runbook_integrity.py::test_lpe_runbook_links`, Observability PagerDuty service “Localization & Policy Engine” with Grafana dashboards “LPE – Enforcement & Residency” and “LPE Compiler”.\\ *Purpose: Maintain actionable recovery guides for LPE incidents and drills.*\\ *Contract: Every alert enumerated in §5.2 maps to an RB-LPE identifier here; responders keep procedures evergreen through quarterly tabletop reviews.*\\ *State: Runbooks live beside automation scripts in `ops/runbooks/lpe/`; this appendix summarizes triggers, decision trees, and evidence requirements.*\\ *Failure modes & retries: Missing or stale runbooks trigger corrective action items and block deploy sign-off.*\\ *Observability: Docs lint checks confirm Appendix R coverage; PagerDuty postmortems must reference the executed RB-LPE ID.*

### Localization & Policy Engine — R.1 Runbook index (informative)

- RB-LPE-COMPILER — Compiler diff escalation and rollback workflow.
- RB-OPA-ROLLBACK — OPA bundle rollback and policy cache validation.
- RB-LPE-WAIVER — Waiver expiry, renewal, and containment response.
- RB-LPE-LOCALE-GAP — Missing localization coverage remediation.

<a id="rb-lpe-compiler"></a>

### Localization & Policy Engine — R.2 RB-LPE-COMPILER — Compiler diff triage (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/compiler_diff_triage.md`, Automation `ops/scripts/lpe/run_compiler_diff.py`, Tests `tests/ops/test_runbook_integrity.py::test_compiler_diff_runbook`, Observability Grafana “LPE Compiler” (alerts `lpe_compiler_duration_overrun`, `lpe_bundle_signature_error`).\\ *Purpose: Contain defective compiler outputs and restore last-known-good bundles without service disruption.*\\ *Contract: Any compiler diff flagged unsafe or breaking must follow this procedure prior to promotion.*\\ *State: Diff artifacts reside in `ops/lpe/compiler_diffs/<date>/`; rollback bundles stored in `ops/lpe/rollback/<bundle_id>.json`.*\\ *Failure modes & retries: Skipping regression replays risks reintroducing invalid localization contexts; failing to rollback promptly blocks Settings activations.*\\ *Observability: Alert clears once safe bundle promoted and diff backlog returns to zero.*

Triggers: `lpe_compiler_duration_overrun`, `lpe_bundle_signature_error`, change tickets tagged `LPE-COMPILER`, manual escalations from QA.

Execution checklist:

1. Freeze compiler pipeline (`lpe.compiler.enabled=false`) and announce in `#ops-announcements`.
1. Inspect diff artifacts; confirm affected locales/regions and whether unsafe flags were raised.
1. Promote previous good bundle via `ops/scripts/lpe/promote_bundle.py --bundle <id>` and capture hash evidence.
1. Re-run regression suite (`make lpe-compiler-regressions`) and snapshot Grafana panels for incident ticket.
1. Coordinate Settings activation replay once bundle validated; update change ticket with evidence.

Post-remediation:

- Resume compiler pipeline and monitor `lpe_compiler_duration_seconds` for two cycles.
- File corrective tasks (root cause, automation gaps) and attach diff artefacts to App.O decision log.

<a id="rb-opa-rollback"></a>

### Localization & Policy Engine — R.3 RB-OPA-ROLLBACK — OPA bundle rollback (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/opa_bundle_rollback.md`, Automation `ops/scripts/lpe/deploy_opa_bundle.py`, Tests `tests/ops/test_runbook_integrity.py::test_opa_rollback_runbook`, Observability Grafana “OPA Discovery” (alerts `opa_discovery_stale_total`, `reference_bundle_stale_total`).\\ *Purpose: Restore healthy Open Policy Agent bundles when discovery or validation failures occur.*\\ *Contract: Any production rollback must document bundle hashes, discovery health, and post-rollback validation.*\\ *State: Bundle manifests stored in `ops/lpe/opa_bundles/`; discovery checks recorded in `ops/lpe/discovery_audit.jsonl`.*\\ *Failure modes & retries: Deploying stale bundles without discovery verification risks policy drift; skipping cache flush leaves workers on outdated decisions.*\\ *Observability: Alert resolves when discovery latency normalizes and signature validation succeeds twice consecutively.*

Response steps:

1. Capture failing discovery IDs and affected services from alert payload.
1. Roll back via `ops/scripts/lpe/deploy_opa_bundle.py --bundle <last_good>` and flush worker caches (`scripts/opa/flush_cache.py`).
1. Validate OPA `/status` and `/health` endpoints plus policy unit tests (`pytest tests/opa/test_policy_context.py`).
1. Notify dependent teams (Settings, Guardian, Reference Manager) and confirm cached digests refresh.
1. Attach bundle hashes, validation output, and Grafana snapshots to incident ticket.

Follow-up:

- Run `ops/scripts/lpe/discovery_audit.py` to confirm discovery parity within 30 minutes.
- File preventive tasks for root cause (compiler bug, Settings drift, CDN failure).

<a id="rb-lpe-waiver"></a>

### Localization & Policy Engine — R.4 RB-LPE-WAIVER — Waiver expiry response (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/waiver_expiry.md`, Automation `ops/scripts/lpe/check_waivers.py`, Tests `tests/ops/test_runbook_integrity.py::test_waiver_runbook`, Observability Grafana “Residency & Enforcement” (alerts `lpe_policy_block_spike`, `lpe_privacy_framework_enabled_total`).\\ *Purpose: Maintain compliant waiver coverage and prevent unauthorized cross-jurisdiction traffic.*\\ *Contract: Expiring waivers must either be renewed with dual approval or decommissioned before expiry.*\\ *State: Waiver ledger maintained in `ops/lpe/waivers.yaml`; renewal evidence archived under `ops/lpe/waiver_reviews/<date>/`.*\\ *Failure modes & retries: Letting waivers lapse without containment can block activations or violate residency commitments.*\\ *Observability: Alert clears once waiver renewal recorded and `lpe_policy_block_total` returns to baseline.*

Checklist:

1. Review waiver ledger for entries expiring within alert window; confirm impacted locales and providers.
1. Engage Security + Architecture for renewal decision; capture approvals in decision log.
1. If waiver retired, update Settings allowlists and trigger Appendix R RB-LPE-LOCALE-GAP if localization fallback required.
1. Run `ops/scripts/lpe/check_waivers.py --verify` to ensure updated posture and attach output to incident ticket.
1. Communicate outcome to affected product owners and document customer impact, if any.

Audit trail:

- Store approvals, renewal artefacts, and communication templates alongside incident log.
- Schedule follow-up review to validate long-term remediation (automation fix, localization updates).

<a id="rb-lpe-locale-gap"></a>

### Localization & Policy Engine — R.5 RB-LPE-LOCALE-GAP — Localization coverage gap (binding)

**Breadcrumbs:** Implementation `ops/runbooks/lpe/locale_gap.md`, Automation `ops/scripts/lpe/audit_locales.py`, Tests `tests/ops/test_runbook_integrity.py::test_locale_gap_runbook`, Observability Grafana “Localization QA” (alerts `lpe_locale_gap_total`, `lpe_lookup_latency_p95_breach`).\\ *Purpose: Restore locale coverage when translations, policy text, or metadata go missing.*\\ *Contract: New locales must publish translations, disclaimer copy, and QA artefacts before re-enabling bundles.*\\ *State: Locale inventories in `ops/lpe/locales.csv`; QA recordings referenced in Appendix A.*\\ *Failure modes & retries: Re-enabling locales without QA sign-off risks incorrect or missing compliance copy.*\\ *Observability: Alert resolves once locale gap metric returns to zero and QA artefacts uploaded.*

Resolution steps:

1. Identify affected locales and impacted surfaces (portal, Guardian, notifications) from alert payload.
1. Coordinate with Localization program to deliver missing translations and QA recordings; update Appendix A checklist items.
1. Validate `ops/scripts/lpe/audit_locales.py` passes for affected locales and attach proof to ticket.
1. Run synthetic checks (`tests/e2e/test_portal_policy_context.py::test_disclaimer_l10n`) to confirm correct copy rendering.
1. Update Settings bundles and trigger LPE compiler rebuild; monitor `lpe_lookup_latency_p95_breach` for regression.

Post-checks:

- Log decision record in App.O with locale IDs, remediation timeline, and QA sign-offs.
- Schedule follow-up audit within one release cycle to verify coverage remains intact.

______________________________________________________________________

## Reference Manager — Appendix R — Runbooks & drills

**Breadcrumbs:** Implementation guides under `ops/reference/runbooks/`, Tests `tests/reference/test_runbooks.py::test_catalog_alignment`, Observability PagerDuty service “Reference Manager On-Call”.\\ *Purpose: Centralize operational procedures for Reference Manager incidents and drills.*\\ *Contract: Alerts enumerated in §5 point to these runbooks; responders keep the procedures current through quarterly tabletop reviews.*\\ *State: Source of truth lives in the ops repository and is mirrored here for quick reference.*\\ *Failure modes & retries: Missing or stale entries trigger post-incident corrective actions and block publish approvals.*\\ *Observability: Docs lint (`docs_runbook_missing_total`) and incident reviews track coverage and freshness.*

### Reference Manager — R.1 Runbook index (informative)

**Breadcrumbs:** Implementation `ops/reference/runbooks/index.md`, Tests `tests/reference/test_runbooks.py::test_index_complete`, Observability Docs lint metric `docs_runbook_missing_total`.\\ *Purpose: Provide a fast lookup table from alerts and incidents to runbook identifiers.*\\ *Contract: Each Reference Manager alert references an ID listed here before shipping.*\\ *State: Maintained alongside monitoring configuration and mirrored in this appendix.*\\ *Failure modes & retries: Lint failures require index updates before merge.*\\ *Observability: Weekly docs lint verifies parity with PagerDuty and alertmanager routing.*

- RB-RM-ROLLBACK — Reference bundle rollback & adoption freeze
- RB-RM-HARVEST — Source harvest incident triage
- RB-RM-PUBLISH — Publish guard failure response
- RB-RM-LICENSE — License violation remediation
- RB-RM-RESIDENCY — Residency endpoint alignment

<a id="rb-rm-rollback"></a>

### Reference Manager — R.2 RB-RM-ROLLBACK — Reference bundle rollback & adoption freeze (binding)

**Breadcrumbs:** Implementation `ops/reference/rollback_bundle.py`, Tests `tests/reference/test_rollback.py::test_restores_previous_version`, Observability PagerDuty service “Reference Manager On-Call” (alert `reference_manager_adoption_lag_sla`).\\ *Purpose: Restore a stable bundle when adoption freezes or downstream services reject a release.*\\ *Contract: Rollbacks execute within 15 minutes, capture evidence, and keep downstream caches synchronized.*\\ *State: `BUNDLE_ROLLBACK_REPORT` artifacts store execution logs, adoption status, and validation evidence.*\\ *Failure modes & retries: Partial rollbacks or missing adoption validation trigger escalation to Architecture and freeze further publishes.*\\ *Observability: Alert resolves when adoption lag returns to budget and downstream acknowledgements report the restored bundle hash.*

Trigger conditions:

- `reference_manager_adoption_lag_sla` alert firing for >10 minutes.
- Downstream compile failures (LPE, Settings, Guardian) referencing the latest bundle hash.
- Manual escalation tagged `RM-ROLLBACK` in incident management.

Execution checklist:

1. Declare incident in `#ref-manager-oncall`, assign commander/scribe, and capture affected bundle IDs.
1. Halt new publishes (`reference publish --freeze`) and notify integrators.
1. Execute `reference rollback --bundle <previous_id>`; record CLI output and resulting bundle hash.
1. Re-run staging adoption suite (`reference adoption verify --bundle <previous_id>`) and confirm downstream acknowledgements.
1. Document outcome in the incident ticket with links to metrics, adoption diffs, and customer impact summary.

Post-rollback validation:

- Confirm `reference_manager_bundle_adoption_seconds` returns below SLA.
- Ensure Settings activation replay completes (`settings.activation.last_success` timestamp updated).
- Schedule root-cause review within 48 hours; capture corrective actions before unfreezing publishes.

<a id="rb-rm-harvest"></a>

### Reference Manager — R.3 RB-RM-HARVEST — Source harvest incident triage (binding)

**Breadcrumbs:** Implementation `ops/reference/runbooks/harvest_incident.md`, Tests `tests/reference/test_harvest_incident.py::test_selector_decision_tree`, Observability Grafana “Reference Manager – Ingestion & Quality” (alert `reference_manager_harvest_total`).\\ *Purpose: Restore healthy harvesting when connectors fail or data drift threatens bundle freshness.*\\ *Contract: Incidents remain active until the affected connectors produce clean ingests and evidence is archived.*\\ *State: Harvest incident ledger `reference_harvest_incident` stores status, root cause, and remediation steps.*\\ *Failure modes & retries: Re-enabling connectors without sanitizing payloads or validating licensing risks corrupt bundles; escalate if two retry cycles fail.*\\ *Observability: Alert clears after successful ingest and selector health checks remain green for two intervals.*

Decision tree:

1. Identify failing sources (`reference harvest status --failing`) and confirm alert payload scope.
1. For selector regressions, pull last-good HTML snapshot, update parser fixtures, and replay ingest in staging.
1. For licensing or robots.txt changes, coordinate with Legal Ops and update provenance manifests before re-enabling.
1. For infrastructure outages, engage provider contacts, increase backoff, and stage manual uploads if SLAs demand.
1. Re-enable connector only after validation passes and ledger entry updated with evidence links.

Communication & evidence:

- Update incident ledger with timestamps, owner, and validation artifacts (`ops/reference/harvest/<date>/`).
- Notify downstream services if freshness gap exceeds 24 hours or impacts regulatory filings.
- Document preventive tasks (selector monitoring, provider engagement) before closing incident.

<a id="rb-rm-publish"></a>

### Reference Manager — R.4 RB-RM-PUBLISH — Publish guard failure response (binding)

**Breadcrumbs:** Implementation `ops/reference/runbooks/publish_guard.md`, Tests `tests/reference/test_publish_guard.py::test_block_on_breaking_change`, Observability CI job “reference-manager-validate” and alert `reference_manager_publish_guard_failure`.\\ *Purpose: Triage schema or validation failures that block publish pipelines.*\\ *Contract: Guard failures remain blocking until validation diffs resolved, schema updates approved, and integration tests rerun.*\\ *State: Validation artifacts persist alongside bundle drafts in `reference_bundle_registry` with diff snapshots.*\\ *Failure modes & retries: Ignoring guard signals risks pushing inconsistent bundles; escalate to Architecture if fix exceeds 12 hours.*\\ *Observability: Alert clears when validation suite passes and guard pipeline returns green.*

Response steps:

1. Collect failing validation artifacts (`reference validate --bundle <id> --export artifacts/guard/<id>`).
1. Categorize failure: schema incompatibility, missing assets, license metadata, or diff threshold breach.
1. Assign owners per category (Schema Council, Content Ops, Localization) and capture remediation plan in incident doc.
1. Apply fixes in staging, rerun validation, and ensure unit/integration suites covering affected domains stay green.
1. Communicate readiness in `#ref-manager-oncall`, secure approvals, and resume publish pipeline.

Post-resolution:

- Attach diff snapshots, approvals, and validation logs to incident ticket.
- Update risk register if failure exposed undocumented dependency or schema gap.
- Trigger follow-up tabletop if guard was bypassed or detection lagged.

<a id="rb-rm-license"></a>

### Reference Manager — R.5 RB-RM-LICENSE — License violation remediation (binding)

**Breadcrumbs:** Implementation `ops/reference/runbooks/license_violation.md`, Tests `tests/reference/test_license_ledger.py::test_violation_alert`, Observability Grafana “Reference Manager – Compliance” (alert `reference_manager_license_violation_total`).\\ *Purpose: Resolve licensing or attribution violations before they propagate to customers.*\\ *Contract: Violations remain open until offending content removed or relicensed, and attribution updates verified downstream.*\\ *State: License ledger entries store violation metadata, remediation steps, and waiver approvals.*\\ *Failure modes & retries: Publishing without resolving violations risks contractual breaches; escalate to Legal Ops immediately.*\\ *Observability: Alert clears when ledger marks violation mitigated and attribution scanners pass.*

Remediation workflow:

1. Review violation payload (source, license, impacted assets) and freeze related publishes.
1. Remove or quarantine offending content from staging/curated schemas; note bundle versions impacted.
1. Coordinate with Legal Ops for relicensing or replacement assets; track approvals in waiver ledger.
1. Update attribution metadata, regenerate affected bundles, and validate Guardian/UI surfaces show correct badges.
1. Close ledger entry with evidence links (tickets, approvals, artifact hashes) and notify stakeholders.

Follow-up:

- Audit other domains for similar exposure; document preventive tasks.
- Update intake checklists to capture new licensing conditions if applicable.
- Record customer communications in incident ticket and App.O decision log.

<a id="rb-rm-residency"></a>

### Reference Manager — R.6 RB-RM-RESIDENCY — Residency endpoint alignment (binding)

**Breadcrumbs:** Implementation `ops/reference/runbooks/residency_alignment.md`, Tests `tests/reference/test_provider_endpoints.py::test_alignment_runbook`, Observability Grafana “Residency & Endpoint Posture” (alert `reference_manager_provider_endpoint_violation_total`).\\ *Purpose: Restore residency compliance when provider endpoint catalogues drift from approved footprints.*\\ *Contract: Findings stay open until catalogues updated, Settings activations rerun, and residency scanners confirm remediation.*\\ *State: Findings tracked in `reference_provider_endpoint_finding` with attestation references and waiver metadata.*\\ *Failure modes & retries: Allowing stale endpoints risks policy violations; escalate to Security Engineering if remediation exceeds SLA.*\\ *Observability: Alert resolves after two clean scans and Settings activation diff reports match updated catalogue.*

Remediation checklist:

1. Inspect finding details and gather attestation or SAN mismatch evidence.
1. Engage provider to confirm intended footprint; request updated attestation or schedule decommission.
1. Update RM catalogue entries (`provider_endpoints[]`), including CIDRs, SAN expectations, and residency notes.
1. Publish refreshed bundle, rerun Settings activation replay, and verify Guardian acknowledges new digest.
1. Archive evidence in incident folder and update waiver ledger if temporary exceptions granted.

Post-remediation validation:

- Confirm `reference_manager_provider_endpoint_violation_total` returns to zero.
- Ensure residency synthetic monitors (EU-REFERENCE, CA-REFERENCE) pass twice consecutively.
- Document lessons learned and automation improvements (scanner coverage, provider notifications).

## Settings Registry — Appendix R — Runbooks & drills

**Breadcrumbs:** Implementation runbooks under `ops/runbooks/settings/`, Tests `tests/platform/settings/test_rollback.py::test_replay_last_good` and peers listed per runbook, Observability Grafana OnCall incidents tagged `settings`.\
*Purpose: Centralize operational playbooks tied to Settings Registry alerts.*\
*Contract: Alerts enumerated in Appendix B must link to these runbooks; responders keep procedures current with quarterly tabletop reviews.*\
*State: Runbooks live alongside automation scripts in the ops repository; this appendix summarizes trigger conditions and critical steps.*\
*Failure modes & retries: Missing or stale runbooks trigger post-incident corrective actions and block deploy sign-off.*\
*Observability: OnCall analytics track time-to-ack/resolve for Settings incidents; drills recorded in App.O decision log.*

### Settings Registry — R.1 Runbook index (informative)

**Breadcrumbs:** Implementation `ops/runbooks/settings/index.md`, Tests `tests/platform/settings/test_runbook_index.py::test_entries_present`, Observability Docs lint metric `docs_runbook_missing_total`.\
*Purpose: Provide a quick map from alert codes to runbook IDs.*\
*Contract: Every Settings alert references one of these IDs; new alerts require index updates.*\
*State: Index maintained in version control and mirrored here.*\
*Failure modes & retries: Lint script fails when index missing an alert; add entry before merging.*\
*Observability: Weekly docs lint verifies the index matches OnCall configuration.*

- RB-GOV-008 — Settings governance toggle / rollback
- RB-RES-ENDPOINT — Residency endpoint drift remediation
- RB-RES-BLOCK — Residency waiver / block handling
- RB-LOCK-006 — Activation lock stale detection & remediation
- RB-LLM-003 — Provider degradation / circuit breaker
- RB-JOB-WATCHDOG — Job stall watchdog
- RB-UPLOAD-SCAN — Upload scanning outage response

<a id="rb-gov-008"></a>

### Settings Registry — R.2 RB-GOV-008 — Settings governance toggle / rollback (binding)

**Breadcrumbs:** Implementation `ops/runbooks/settings/governance_toggle.md`, Tests `tests/platform/settings/test_rollback.py::test_replay_last_good`, Observability Grafana “Settings Governance” dashboard (alert `settings_governance_override_total`).\
*Purpose: Safely activate or revert high-sensitivity governance toggles (waivers, residency overrides, cross-org pilots).*\
*Contract: Any activation flagged `unsafe` or touching governance scopes must follow this sequence before promotion.*\
*State: Runbook automation uses `ops/runbooks/settings_rollback.py`; evidence stored under `ops/settings/<date>/`.*\
*Failure modes & retries: Missing approvals or failed smoke tests require immediate rollback via `settings rollback --bundle <previous_id>`.*\
*Observability: Alert clears once activation completes with both approvals and validation metrics green.*

Triggers: `settings_governance_override_total`, change tickets tagged `GOV-TOGGLE`, or manual escalation from Security/Architecture.

Execution checklist:

1. Announce maintenance window with activation/rollback times in `#ops-announcements`.
1. Validate staging dry-run (matching bundle hash) and attach diff evidence to change ticket.
1. Execute activation via CLI/UI, capturing activation ID and `unsafe_reasons[]` result (expected empty).
1. Run targeted smoke tests (API read/write, portal toggle, worker snapshot) tied to the toggle.
1. Update change ticket and decision log with activation ID, evidence, and rollback window.

Rollback steps:

- Reapply prior bundle via `settings rollback --bundle <previous_id>` if smoke tests or monitors fail.
- Confirm `settings.changed` event emission and run smoke tests to verify reversion.
- Communicate rollback rationale to stakeholders and attach evidence to App.O.

Evidence requirements:

- Store activation/rollback JSON artifacts under `ops/settings/<date>/`.
- Append decision log entry referencing ADR/change ticket, activation ID, and outcome.
- Attach customer/support comms templates used (see `docs/runbooks/settings/templates/governance_toggle_announce.md`).

<a id="rb-res-endpoint"></a>

### Settings Registry — R.3 RB-RES-ENDPOINT — Residency endpoint drift remediation (binding)

**Breadcrumbs:** Implementation `ops/runbooks/settings/residency_endpoint_drift.md`, Tests `tests/platform/settings/test_residency_triage.py::test_endpoint_drift_runbook`, Observability Grafana “Residency & Endpoint Posture” dashboard (alert `alert_residency_endpoint_drift`).\
*Purpose: Restore compliant residency posture when outbound endpoints drift or new hosts appear.*\
*Contract: Findings remain `open` until catalogue updates or waivers recorded per this runbook.*\
*State: Findings persist in `residency_endpoint_findings`; evidence stored in `ops/residency/endpoint_scan.jsonl`.*\
*Failure modes & retries: Waivers lacking dual approval or catalogue gaps keep the finding open and block affected activations.*\
*Observability: Alert auto-resolves after two clean scans and updated catalogue hashes.*

Triage checklist:

1. Query `residency_endpoint_findings` for `state='open'`; review evidence attachments.
1. Inspect Istio AuthorizationPolicy revisions to ensure offending hosts remain blocked.
1. Identify impacted providers/orgs via activation diff linked in alert payload.

Decision tree:

- **Provider expansion** — Engage Reference Manager to ingest metadata, rerun `residency_endpoint_scan --host <fqdn>`, and promote Settings activation once SAN + GeoIP verified.
- **DNS drift/misconfig** — Flush DNS caches (`scripts/residency/flush_dns_cache.py`), roll egress gateway if stale endpoints persist.
- **Waiver path** — Seek dual approval (Security + Architecture), set temporary waiver in Settings, ensure Guardian manifests log `RESIDENCY_WAIVER_USED`.
- **False positive** — Annotate finding, keep block in place, downgrade alert severity after evidence review.

Post-remediation:

- Verify finding transitions to `mitigated` within two scans.
- Close incident with root cause, evidence links, and preventive actions (provider engagement, automation gap).
- Record outcome in decision log and App.O waiver ledger if applicable.

<a id="rb-res-block"></a>

### Settings Registry — R.4 RB-RES-BLOCK — Residency waiver / block handling (binding)

**Breadcrumbs:** Implementation `ops/runbooks/settings/residency_block.md`, Tests `tests/platform/settings/test_residency_validators.py::test_block_requires_waiver`, Observability Grafana “Residency Compliance” dashboard (alert `alert_residency_policy_block`).\
*Purpose: Resolve residency policy blocks triggered during activations or runtime checks.*\
*Contract: Blocks clear only after org allowlists align with RM catalogue or waivers recorded with expiry.*\
*State: Policy blocks logged as `RESIDENCY_POLICY_BLOCK`; waiver metadata stored in `settings_waiver`.*\
*Failure modes & retries: Waivers without expiry or missing approvals invalidate activation attempts.*\
*Observability: Alert returns to green once block count drops to zero.*

Steps:

1. Confirm org allowlists (`regions.allowlist.compute/storage/vector`).
1. Validate provider endpoints and DNS; compare to RM catalogue snapshots.
1. If cross-region access required, capture dual approval, set `cross_region_waiver=true`, and document expiry.
1. Re-run activation or job; confirm Guardian manifests reference waiver ID.
1. Audit waiver usage daily until expiry or remediation.

<a id="rb-lock-006"></a>

### Settings Registry — R.5 RB-LOCK-006 — Activation lock stale detection & remediation (binding)

**Breadcrumbs:** Implementation `ops/runbooks/settings/activation_lock.md`, Tests `tests/platform/settings/test_locks.py::test_lock_scope`, Observability Grafana “Settings Lock” panel (alert `settings_activation_lock_wait_seconds`).\
*Purpose: Detect and remediate stuck activation locks without risking concurrent edits.*\
*Contract: Lock holders must release within configured `udlock.max_session_hold_seconds`; stale locks trigger this runbook.*\
*State: Lock registry tracked in `settings_activation_lock`; helper scripts expose current holders.*\
*Failure modes & retries: Forcing unlock without verifying holder state risks split-brain activations; follow decision tree below.*\
*Observability: Alert clears when lock age returns under threshold and registry shows no stale entries.*

Checklist:

1. Inspect lock registry via `scripts/settings/show_activation_locks.py` filtered by environment.
1. Verify holder liveness (`SELECT ... FROM pg_stat_activity`) to differentiate idle vs active transactions.
1. If holder dead or idle-in-transaction, coordinate worker/web restart or issue `SELECT pg_terminate_backend(...)` per policy.
1. After release, rerun activation pipeline smoke tests; capture evidence in incident log.
1. File follow-up if lock reappears within 24h (root cause investigation, automation fix).

<a id="rb-llm-003"></a>

### Settings Registry — R.6 RB-LLM-003 — Provider degradation / circuit breaker (binding)

**Breadcrumbs:** Implementation `ops/runbooks/settings/provider_circuit_breaker.md`, Tests `tests/platform/settings/test_llm_circuit.py::test_half_open_probe`, Observability Grafana “FinOps – LLM Cost & Circuit” dashboard (alert `alert_llm_circuit_open`).\
*Purpose: Handle degraded LLM providers to protect cost and SLA budgets.*\
*Contract: OPEN circuits remain until provider health verifies; half-open probes follow cadence defined here.*\
*State: Circuit state stored in `settings_llm_circuit`; fallback chains defined in Settings bundles.*\
*Failure modes & retries: Prematurely closing circuits or leaving fallback unmonitored risks runaway spend and job failures.*\
*Observability: Alert resolves when circuit state returns to CLOSED for affected models and cost deltas stabilize.*

Response steps:

1. Confirm affected models via dashboard filters (`llm_circuit_state{model}`) and review recent error/latency metrics.
1. Validate fallback outcomes in logs (`PRIMARY_DEGRADED`, `FALLBACK_USED`) and ensure FinOps guardrails intact.
1. Keep circuits OPEN until three consecutive successful half-open probes; adjust fallback priorities if secondary models degrade.
1. Notify vendor/support with incident details when degradation persists >15 minutes; record ticket IDs in incident log.
1. After recovery, document budget impact and corrective actions; update preventive tasks (synthetic prompts, timeout tuning).

<a id="rb-job-watchdog"></a>

### Settings Registry — R.7 RB-JOB-WATCHDOG — Job stall watchdog (binding)

**Breadcrumbs:** Implementation `ops/runbooks/platform/job_watchdog.md`, Tests `tests/platform/watchdog/test_job_timeout.py::test_timeout_escalation`, Observability Grafana “Watchdog Runner” dashboard (alerts `job_watchdog_warning_total`, `job_watchdog_timeout_total`).\
*Purpose: Restore stuck jobs and protect downstream SLAs when heartbeats lapse.*\
*Contract: Watchdog alerts trigger within `jobs.watchdog.no_progress_minutes` / `jobs.watchdog.timeout_minutes`; responders must either resume progress or terminate safely.*\
*State: Heartbeats stored in `job_progress_heartbeat`; remediation evidence captured in incident ticket (`ops/watchdog/<date>/`).*\
*Failure modes & retries: Premature termination can lose customer work; skipping checkpoint verification risks replaying corrupted artifacts.*\
*Observability: Alert clears after watchdog completes remediation and fresh heartbeats resume for affected jobs.*

Triage & remediation:

1. Identify affected job IDs from alert payload; confirm `job_progress_heartbeat` age and last known task lane.
1. Inspect worker logs for stalled tasks, resource exhaustion, or upstream dependency failures; capture excerpts in incident notes.
1. If work-in-progress artifacts exist, trigger checkpoint validation (`ops/jobs/verify_checkpoint.py`) before retrying.
1. Attempt safe resume via `jobs resume --job <id>` when the worker is healthy; otherwise cancel and requeue after addressing root cause.
1. Close alert once heartbeats refresh (\< 2 × `jobs.watchdog.heartbeat_interval`) and audit trail updated with remediation steps.

Post-incident follow-up:

- File preventive tasks when repeated stalls originate from the same provider lane or dependency.
- Review Settings defaults (`jobs.watchdog.*`) to confirm thresholds remain appropriate for the workload mix.

<a id="rb-upload-scan"></a>

### Settings Registry — R.8 RB-UPLOAD-SCAN — Upload scanning outage response (binding)

**Breadcrumbs:** Implementation `ops/runbooks/security/upload_scan.md`, Tests `tests/security/test_upload_scan_guard.py::test_quarantine_on_failure`, Observability Grafana “Security — Upload Scanning” dashboard (alerts `upload_scan_error_total`, `upload_scan_queue_depth`).\
*Purpose: Maintain quarantine-first posture when malware scanning or format validation degrades.*\
*Contract: New uploads remain blocked (`uploads.enabled=false`) until scanners return to green and evidence recorded per this runbook.*\
*State: Scan attempts logged in `upload_scan_audit`; quarantined objects isolated under `storage/quarantine/<job_id>/`.*\
*Failure modes & retries: Re-enabling uploads without updated signatures risks releasing infected files; overriding quarantine without approvals violates security policy.*\
*Observability: Alert clears after two consecutive clean scan batches and queue depth normalizes below baseline.*

Response sequence:

1. Confirm scope of degradation (engine errors vs. queue backlog) using dashboard drill-downs and `upload_scan_audit` sampling.
1. Freeze new intake by toggling `uploads.enabled=false` in Settings; announce customer impact and expected review window.
1. Validate scanner health: check ClamAV/YARA signature freshness, sandbox resource utilization, and recent deployment changes.
1. For malware detections, coordinate with Security to analyze samples; maintain quarantine until signatures updated and retest passes.
1. Once scanners stable, re-enable uploads, replay quarantined items through the pipeline, and attach evidence (dashboards, signature reports) to the incident record.

Follow-up:

- File change tasks for signature automation gaps or scaling adjustments discovered during the incident.
- Update customer/regulator communications templates with incident summary and remediation timeline.
