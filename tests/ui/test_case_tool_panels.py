from __future__ import annotations

from urllib.parse import quote

import pytest

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case
from apps.platform.ui.views.presenters import cases as presenters


@pytest.mark.django_db()
def test_build_tool_panels_appends_return_url(monkeypatch):
    org = Organization.objects.create(id="ORG-PANELS", name="Panels Org")
    case = Case.objects.create(id="CASE-PANELS", title="Panels Case", organization=org)

    def fake_llm_context(_case: Case, return_url: str):
        encoded_next = quote(return_url, safe="")
        def ctx(target: str) -> dict[str, object]:
            return {
                "target": target,
                "provider_chain": [],
                "provider_chain_json": "[]",
                "configurations": [],
                "configurations_json": "[]",
                "active_configuration": None,
                "active_configuration_json": "{}",
                "configured_stages": [],
                "stage_configs": [],
                "stage_configs_json": "[]",
                "stage_map_json": "{}",
                "urls": {
                    "base": "#",
                    "edit": f"#?next={encoded_next}",
                    "new": f"#?next={encoded_next}",
                    "tuning": "#",
                },
                "return_url": return_url,
            }

        return {"summary": ctx("summary"), "timeline": ctx("timeline")}

    monkeypatch.setattr(presenters, "build_analysis_llm_context", fake_llm_context)

    progress_items = [
        {"key": "case_setup", "status": "Ready", "status_class": "ok", "updated": None, "detail": None},
        {"key": "transcription", "status": "Idle", "status_class": "idle", "updated": None, "detail": None},
        {"key": "summary", "status": "Idle", "status_class": "idle", "updated": None, "detail": None},
        {"key": "timeline", "status": "Idle", "status_class": "idle", "updated": None, "detail": None},
    ]

    analysis_modules = [
        {"key": "summary", "latest": None, "history": [], "notes": {"job_id": None, "entries": [], "user_can_add": False}},
        {"key": "timeline", "latest": None, "history": [], "notes": {"job_id": None, "entries": [], "user_can_add": False}},
    ]

    panels = presenters.build_tool_panels(
        case,
        jobs=[],
        progress_items=progress_items,
        job_rows=[],
        telemetry_map={},
        transcript_artifacts={},
        analysis_modules=analysis_modules,
        artifacts=[],
        memberships=[],
        latest_job=None,
        latest_job_telemetry=None,
        job_summary={},
        user_can_review=False,
        return_url=f"/cases/{case.id}/",
    )

    summary_urls = panels["summary"]["body_context"]["summary_llm"]["urls"]
    timeline_urls = panels["timeline"]["body_context"]["timeline_llm"]["urls"]

    expected_suffix = f"next=%2Fcases%2F{case.id}%2F"
    assert expected_suffix in summary_urls["edit"]
    assert expected_suffix in summary_urls["new"]
    assert expected_suffix in timeline_urls["edit"]
    assert expected_suffix in timeline_urls["new"]
    assert panels["summary"]["body_context"]["summary_llm"]["return_url"] == f"/cases/{case.id}/"
    assert "guardian" not in panels
