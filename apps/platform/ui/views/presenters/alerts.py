from __future__ import annotations

# pyright: strict
from datetime import datetime
from typing import Any, Dict, List, Sequence

from django.utils import timezone

from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job

ALERT_SEVERITY_CLASSES: Dict[str, str] = {
    "critical": "border-rose-500/60 bg-rose-500/10 text-rose-100",
    "warning": "border-amber-400/60 bg-amber-400/10 text-amber-100",
    "info": "border-sky-400/60 bg-sky-400/10 text-sky-100",
}

ALERT_SEVERITY_ORDER: Dict[str, int] = {"critical": 0, "warning": 1, "info": 2}


def _distance_label(days: int) -> str:
    if days > 1:
        return f"due in {days} days"
    if days == 1:
        return "due tomorrow"
    if days == 0:
        return "due today"
    if days == -1:
        return "overdue by 1 day"
    if days < -1:
        return f"overdue by {abs(days)} days"
    return "due soon"


def _deadline_severity(days: int) -> str:
    if days < 0:
        return "critical"
    if days <= 3:
        return "critical"
    if days <= 7:
        return "warning"
    return "info"


def _event_severity(hours: float) -> str:
    if hours < 0:
        return "warning"
    if hours <= 48:
        return "critical"
    if hours <= 168:
        return "warning"
    return "info"


def _format_datetime(dt: datetime) -> str:
    localized = timezone.localtime(dt)
    return localized.strftime("%b %d, %Y %I:%M %p")


def build_case_team_alerts(case: Case, jobs: Sequence[Job]) -> List[Dict[str, Any]]:
    now = timezone.now()
    today = timezone.localdate()
    alerts: List[Dict[str, Any]] = []

    if case.filing_deadline:
        days_until = (case.filing_deadline - today).days
        severity = _deadline_severity(days_until)
        alerts.append(
            {
                "id": "filing-deadline",
                "title": "Filing deadline",
                "summary": case.filing_deadline.strftime("%b %d, %Y"),
                "detail": _distance_label(days_until),
                "severity": severity,
                "severity_class": ALERT_SEVERITY_CLASSES.get(severity, ALERT_SEVERITY_CLASSES["info"]),
                "tooltip": f"Filing deadline on {case.filing_deadline:%B %d, %Y} ({_distance_label(days_until)})",
                "due": case.filing_deadline.isoformat(),
                "due_kind": "date",
                "sort_ts": case.filing_deadline.toordinal(),
            }
        )

    if case.court_date:
        court_ts = timezone.localtime(case.court_date)
        hours_until = (court_ts - now).total_seconds() / 3600
        days_until = int((court_ts.date() - today).days)
        severity = _event_severity(hours_until)
        tooltip_distance = _distance_label(days_until)
        alerts.append(
            {
                "id": "court-date",
                "title": "Court appearance",
                "summary": _format_datetime(court_ts),
                "detail": tooltip_distance,
                "severity": severity,
                "severity_class": ALERT_SEVERITY_CLASSES.get(severity, ALERT_SEVERITY_CLASSES["info"]),
                "tooltip": f"Court appearance on {_format_datetime(court_ts)} ({tooltip_distance})",
                "due": court_ts.isoformat(),
                "due_kind": "datetime",
                "sort_ts": court_ts.timestamp(),
            }
        )

    failed_jobs = [job for job in jobs if job.status in {Job.Status.FAILED, Job.Status.CANCELLED, Job.Status.CORRUPTED}]
    if failed_jobs:
        count = len(failed_jobs)
        alerts.append(
            {
                "id": "failed-jobs",
                "title": "Jobs failed",
                "summary": f"{count} job{'s' if count != 1 else ''} need attention",
                "detail": "Review error details and retry as needed.",
                "severity": "critical",
                "severity_class": ALERT_SEVERITY_CLASSES["critical"],
                "tooltip": "One or more jobs failed. Review error logs to resolve.",
                "sort_ts": now.timestamp() - 1,
            }
        )

    pending_reviews = [
        job
        for job in jobs
        if job.status == Job.Status.SUCCEEDED and job.review_status == Job.ReviewStatus.PENDING
    ]
    if pending_reviews:
        count = len(pending_reviews)
        alerts.append(
            {
                "id": "pending-reviews",
                "title": "Reviews pending",
                "summary": f"{count} transcript{'s' if count != 1 else ''} awaiting approval",
                "detail": "Approve or request changes to unblock automations.",
                "severity": "warning",
                "severity_class": ALERT_SEVERITY_CLASSES["warning"],
                "tooltip": "Transcription reviews are pending approval.",
                "sort_ts": now.timestamp(),
            }
        )

    active_jobs = [
        job
        for job in jobs
        if job.status
        in {
            Job.Status.RUNNING,
            Job.Status.CONVERTING,
            Job.Status.UPLOADING,
            Job.Status.CANCELLING,
        }
    ]
    if active_jobs:
        count = len(active_jobs)
        alerts.append(
            {
                "id": "active-jobs",
                "title": "Jobs in progress",
                "summary": f"{count} job{'s' if count != 1 else ''} running",
                "detail": "You will see updates here as they complete.",
                "severity": "info",
                "severity_class": ALERT_SEVERITY_CLASSES["info"],
                "tooltip": "Jobs are actively running for this case.",
                "sort_ts": now.timestamp() + 1,
            }
        )

    alerts.sort(
        key=lambda item: (
            ALERT_SEVERITY_ORDER.get(item.get("severity"), 99),
            item.get("sort_ts", float("inf")),
        )
    )

    return alerts
