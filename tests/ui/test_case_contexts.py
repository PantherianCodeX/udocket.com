from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import RequestFactory

from apps.platform.accounts.models import Organization
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.ui.views.contexts import compute_case_tool_state
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
