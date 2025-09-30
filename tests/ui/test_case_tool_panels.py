from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case
from apps.platform.ui.views.presenters import cases as presenters


@pytest.mark.django_db()
def test_build_tool_panels_appends_return_url(monkeypatch):
    org = Organization.objects.create(id="ORG-PANELS", name="Panels Org")
    case = Case.objects.create(id="CASE-PANELS", title="Panels Case", organization=org)

    dummy_cfg = SimpleNamespace(provider_chain=["azure"])
    monkeypatch.setattr(presenters.SummarizeConfig, "from_env", classmethod(lambda cls: dummy_cfg))
    class DummyAssignment:
        def __init__(self, stage_key: str, target: str):
            self.stage_key = stage_key
            self.target = target
            self.label = stage_key.replace("_", " ").title()
            self.description = ""
            self.providers = ["azure"]
            self.model = "gpt"
            self.options = {}
            self.max_tokens = 4096

    class DummySettings:
        def __init__(self):
            self.assignments = {
                "summary_main": DummyAssignment("summary_main", "summary"),
                "timeline_main": DummyAssignment("timeline_main", "timeline"),
            }

        def stage(self, stage_key: str) -> DummyAssignment:
            return self.assignments.get(stage_key, DummyAssignment(stage_key, "summary"))

    monkeypatch.setattr(presenters, "load_llm_settings", lambda: DummySettings())
    monkeypatch.setattr(presenters, "load_provider_catalog", lambda: {})
    monkeypatch.setattr(presenters, "get_org_provider_credentials", lambda org_id: {})
    monkeypatch.setattr(
        presenters,
        "build_provider_registry",
        lambda **kwargs: {
            "azure": {
                "label": "Azure",
                "available": True,
                "configured": True,
            }
        },
    )

    def _org_configs(_org_id: str, target: str):
        return [{"id": f"{target}-config", "name": f"{target.title()} Config", "is_default": True}]

    def _active_config(*_args, target: str, **_kwargs):
        return {"id": f"{target}-config", "stage_map": {}, "provider_chain": ["azure"]}

    monkeypatch.setattr(presenters, "get_org_llm_configurations", _org_configs)
    monkeypatch.setattr(presenters, "get_llm_configuration", _active_config)
    monkeypatch.setattr(presenters, "ensure_default_llm_configuration", lambda **kwargs: None)

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
