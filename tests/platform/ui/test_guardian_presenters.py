from __future__ import annotations

from apps.platform.ui.views.presenters.guardian import (
    collect_guardian_reviews,
    guardian_stats_from_reviews,
    guardian_violation_entries,
)

def test_guardian_presenter_stats_and_violations():
    artifacts = [
        {
            "id": 101,
            "title": "Summary artifact",
            "type": "SUMMARY",
            "metadata": {
                "guardian_history": [
                    {
                        "status": "approved",
                        "reviewed_at": "2025-03-01T12:00:00Z",
                        "violations": [],
                        "notes": "Looks good",
                    },
                    {
                        "status": "rejected",
                        "reviewed_at": "2025-03-02T15:30:00Z",
                        "violations": [
                            {"severity": "HIGH", "message": "Sensitive medical data", "category": "PII"},
                            {"severity": "LOW", "message": "Minor formatting issue"},
                        ],
                        "notes": "Redact patient details",
                    },
                ]
            },
        }
    ]

    reviews = collect_guardian_reviews(artifacts)
    assert len(reviews) == 2
    assert reviews[0]["status"] == "rejected"  # most recent first
    assert reviews[0]["artifact_id"] == 101

    stats = guardian_stats_from_reviews(reviews)
    assert stats["total_reviews"] == 2
    assert stats["approved"] == 1
    assert stats["rejected"] == 1
    assert stats["violation_count"] == 2
    assert stats["status_label"] == "Flagged"

    violations = guardian_violation_entries(reviews)
    assert len(violations) == 2
    severities = [violation["severity"] for violation in violations]
    assert severities[0] == "HIGH"
    assert violations[0]["violation"]["message"] == "Sensitive medical data"
