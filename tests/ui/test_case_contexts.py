from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import RequestFactory

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from django.core.cache import cache

from apps.platform.ui.views.contexts import compute_case_tool_state, get_case_tool_state
from tests._typing import SettingsFixture


@pytest.mark.django_db()
def test_compute_case_tool_state_transcribe_skips_analysis(settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = True

    org = Organization.objects.create(name="Ctx Org")
    case = Case.objects.create(id="CASE-CTX", title="Ctx Case", organization=org)
    job = Job.objects.create(case=case, audio_input="/tmp/audio.wav", status=Job.Status.SUCCEEDED)

    request = RequestFactory().get(f"/cases/{case.id}/tools/transcribe/")

    with patch("apps.platform.ui.views.contexts.analysis_modules_context") as mock_modules:
        compute_case_tool_state(request, case, active_tool="transcribe")
        mock_modules.assert_not_called()


@pytest.mark.django_db()
def test_compute_case_tool_state_compose_requests_analyze_and_compose(settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = True

    org = Organization.objects.create(name="Ctx Org 2")
    case = Case.objects.create(id="CASE-CTX-2", title="Ctx Case 2", organization=org)
    Job.objects.create(case=case, audio_input="/tmp/audio.wav", status=Job.Status.SUCCEEDED)

    request = RequestFactory().get(f"/cases/{case.id}/tools/compose/")

    with patch("apps.platform.ui.views.contexts.analysis_modules_context") as mock_modules:
        mock_modules.return_value = []
        compute_case_tool_state(request, case, active_tool="compose")
        mock_modules.assert_called_once()
        kwargs = mock_modules.call_args.kwargs
        assert kwargs.get("target_keys") == {"compose", "analyze"}


@pytest.mark.django_db()
def test_get_case_tool_state_uses_cache(settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = True
    settings.CASE_TOOL_CACHE_SECONDS = 60
    cache.clear()

    org = Organization.objects.create(name="Ctx Org Cache")
    case = Case.objects.create(id="CASE-CTX-CACHE", title="Ctx Cache", organization=org)
    Job.objects.create(case=case, audio_input="/tmp/audio.wav", status=Job.Status.SUCCEEDED)

    request = RequestFactory().get(f"/cases/{case.id}/tools/transcribe/")

    with patch("apps.platform.ui.views.contexts.compute_case_tool_state") as mock_compute:
        mock_compute.return_value = {
            "tool_panels": {},
            "case_header": {},
            "developer_cards": [],
            "job_summary": {},
            "latest_activity_ts": None,
            "job_summary_last_dt": None,
            "user_can_review": False,
            "job_table_state": None,
            "job_row_total": 0,
        }

        first = get_case_tool_state(request, case, active_tool="transcribe")
        second = get_case_tool_state(request, case, active_tool="transcribe")

        assert first == second
        assert mock_compute.call_count == 1


@pytest.mark.django_db()
def test_get_case_tool_state_default_cache(settings: SettingsFixture):
    settings.PLATFORM_DEV_OPEN = True
    sentinel = object()
    original_value = getattr(settings, "CASE_TOOL_CACHE_SECONDS", sentinel)
    if hasattr(settings, "CASE_TOOL_CACHE_SECONDS"):
        delattr(settings, "CASE_TOOL_CACHE_SECONDS")
    cache.clear()

    org = Organization.objects.create(name="Ctx Org Default")
    case = Case.objects.create(id="CASE-CTX-DEFAULT", title="Ctx Default", organization=org)
    Job.objects.create(case=case, audio_input="/tmp/audio.wav", status=Job.Status.SUCCEEDED)

    request = RequestFactory().get(f"/cases/{case.id}/tools/intake/")

    with patch("apps.platform.ui.views.contexts.compute_case_tool_state") as mock_compute:
        mock_compute.return_value = {
            "tool_panels": {},
            "case_header": {},
            "developer_cards": [],
            "job_summary": {},
            "latest_activity_ts": None,
            "job_summary_last_dt": None,
            "user_can_review": False,
            "job_table_state": None,
            "job_row_total": 0,
        }
        get_case_tool_state(request, case, active_tool="intake")
        get_case_tool_state(request, case, active_tool="intake")
        assert mock_compute.call_count == 1

    if original_value is not sentinel:
        setattr(settings, "CASE_TOOL_CACHE_SECONDS", original_value)
