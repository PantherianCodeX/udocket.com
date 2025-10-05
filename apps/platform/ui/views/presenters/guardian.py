from __future__ import annotations

# pyright: strict
from collections import Counter
from datetime import datetime
from typing import Any, Dict, Iterable, List, Sequence

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .utils import status_class


SEVERITY_ORDER = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "INFO": 4,
}


def _parse_review_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = parse_datetime(str(value))
    if dt is None:
        return None
    if timezone.is_naive(dt):  # pragma: no cover - defensive
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def collect_guardian_reviews(artifacts: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    reviews: List[Dict[str, Any]] = []
    for artifact in artifacts:
        metadata = artifact.get("metadata") or {}
        history: Iterable[Dict[str, Any]] = metadata.get("guardian_history") or []
        artifact_id = artifact.get("id")
        artifact_title = artifact.get("title") or artifact.get("filename") or metadata.get("source")
        artifact_type = artifact.get("type")
        artifact_created_at = artifact.get("created_at")

        for entry in history:
            record = dict(entry or {})
            record.setdefault("artifact_id", artifact_id)
            record.setdefault("artifact_title", artifact_title)
            record.setdefault("artifact_type", artifact_type)
            record.setdefault("artifact_created_at", artifact_created_at)
            reviewed_at_dt = _parse_review_dt(record.get("reviewed_at"))
            record["_reviewed_at_dt"] = reviewed_at_dt
            reviews.append(record)

    reviews.sort(key=lambda item: item.get("_reviewed_at_dt") or datetime.min, reverse=True)
    return reviews


def guardian_stats_from_reviews(reviews: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(reviews)
    status_counts = Counter()
    violation_total = 0
    severity_counts: Counter[str] = Counter()
    latest_review = reviews[0] if reviews else None
    latest_status = None
    latest_reviewed_at_dt = None

    for review in reviews:
        status = str(review.get("status") or "").strip().lower() or "unknown"
        status_counts[status] += 1
        violations = review.get("violations") or []
        if isinstance(violations, (list, tuple)):
            violation_total += len(violations)
            for violation in violations:
                severity = str((violation or {}).get("severity") or "").upper() or "UNKNOWN"
                severity_counts[severity] += 1

    if latest_review:
        latest_status = latest_review.get("status")
        latest_reviewed_at_dt = latest_review.get("_reviewed_at_dt")

    stats: Dict[str, Any] = {
        "total_reviews": total,
        "approved": status_counts.get("approved", 0),
        "rejected": status_counts.get("rejected", 0),
        "skipped": status_counts.get("skipped", 0),
        "error": status_counts.get("error", 0),
        "other": total - sum(status_counts.get(key, 0) for key in ("approved", "rejected", "skipped", "error")),
        "violation_count": violation_total,
        "severity_counts": dict(severity_counts),
        "latest_review": latest_review,
        "latest_status": latest_status,
    }

    if latest_reviewed_at_dt:
        stats["latest_reviewed_at_dt"] = latest_reviewed_at_dt
        stats["latest_reviewed_at"] = latest_reviewed_at_dt.isoformat()
    else:
        stats["latest_reviewed_at_dt"] = None
        stats["latest_reviewed_at"] = None

    if total == 0:
        status_label = "Not Started"
        detail = "Guardian has not reviewed any artifacts yet."
    elif stats["rejected"] > 0:
        status_label = "Flagged"
        detail = f"{stats['rejected']} review(s) flagged violations."
    elif stats["approved"] > 0:
        status_label = "Monitoring"
        detail = "Latest guardian review approved the content."
    elif stats["error"] > 0:
        status_label = "Error"
        detail = "Guardian encountered errors while reviewing recent artifacts."
    elif stats["skipped"] == total:
        status_label = "Skipped"
        detail = "Guardian skipped every artifact reviewed so far."
    else:
        status_label = (latest_status or "Monitoring").title()
        detail = "Guardian reviews recorded."

    stats["status_label"] = status_label
    stats["status_class"] = status_class(status_label)
    stats["status_detail"] = detail

    return stats


def guardian_violation_entries(reviews: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for review in reviews:
        violations = review.get("violations") or []
        if not isinstance(violations, (list, tuple)):
            continue
        reviewed_at_dt = review.get("_reviewed_at_dt")
        for violation in violations:
            violation_data = violation or {}
            severity = str(violation_data.get("severity") or "").upper() or "UNKNOWN"
            category = violation_data.get("category") or violation_data.get("code") or "Violation"
            entries.append(
                {
                    "artifact_id": review.get("artifact_id"),
                    "artifact_title": review.get("artifact_title"),
                    "artifact_type": review.get("artifact_type"),
                    "reviewed_at": review.get("reviewed_at"),
                    "reviewed_at_dt": reviewed_at_dt,
                    "status": review.get("status"),
                    "notes": review.get("notes"),
                    "violation": violation_data,
                    "severity": severity,
                    "category": category,
                }
            )

    def sort_key(item: Dict[str, Any]):
        severity_rank = SEVERITY_ORDER.get(item.get("severity") or "", 99)
        reviewed_at_dt = item.get("reviewed_at_dt") or datetime.min
        return (severity_rank, reviewed_at_dt)

    entries.sort(key=sort_key)
    return entries


def guardian_report_payload(
    *,
    case: Any,
    stats: Dict[str, Any],
    reviews: Sequence[Dict[str, Any]],
    violations: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    generated_at = timezone.now()
    return {
        "case_id": str(getattr(case, "id", "")),
        "case_title": getattr(case, "title", ""),
        "generated_at": generated_at.isoformat(),
        "stats": stats,
        "reviews": list(reviews),
        "violations": list(violations),
    }


__all__ = [
    "collect_guardian_reviews",
    "guardian_stats_from_reviews",
    "guardian_violation_entries",
    "guardian_report_payload",
]
