from __future__ import annotations

import io

from unittest.mock import patch

import pytest
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.platform.accounts.models import Organization, User
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job


def _wav_bytes() -> bytes:
    # Tiny PCM WAV header with silence (44-byte header + 4 bytes payload)
    return (
        b"RIFF" + (36 + 4).to_bytes(4, "little") + b"WAVEfmt "
        + (16).to_bytes(4, "little")  # fmt chunk size
        + (1).to_bytes(2, "little")  # PCM
        + (1).to_bytes(2, "little")  # mono
        + (16000).to_bytes(4, "little")  # sample rate
        + (16000 * 2).to_bytes(4, "little")  # byte rate
        + (2).to_bytes(2, "little")  # block align
        + (16).to_bytes(2, "little")  # bits per sample
        + b"data"
        + (4).to_bytes(4, "little")
        + b"\x00\x00\x00\x00"
    )


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_ui_job_creation_forces_batch_when_diarization(settings):
    settings.PLATFORM_DEV_OPEN = True
    org = Organization.objects.create(id="org-ui", name="UI Org")
    case = Case.objects.create(id="case-ui", title="UI Case", organization=org)
    user = User.objects.create_user(username="ui-user", password="pw")
    CaseMembership.objects.create(case=case, user=user, role=CaseMembership.Role.OWNER)

    client = Client()
    client.force_login(user)

    upload = SimpleUploadedFile("sample.wav", _wav_bytes(), content_type="audio/wav")
    with patch("apps.platform.ui.views.transcribe_job.delay") as mocked_delay:
        resp = client.post(
            f"/cases/{case.id}/jobs/new",
            {
                "mode": Job.Mode.ON_DEMAND,
                "diarization": "1",
                "language": "en-CA",
                "audio": upload,
            },
        )
        mocked_delay.assert_called_once()
    assert resp.status_code == 200

    job = Job.objects.filter(case=case).latest("created_at")
    assert job.diarization is True
    assert job.mode == Job.Mode.BATCH
