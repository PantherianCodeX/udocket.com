from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.platform.accounts.models import Organization
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.operations.storage import ensure_case_dirs
from apps.platform.operations import tasks


@pytest.mark.django_db
def test_guardian_review_artifact_initializes_case_id(monkeypatch, settings, tmp_path):
    media_root = tmp_path / "media"
    media_root.mkdir()
    settings.MEDIA_ROOT = str(media_root)

    organization = Organization.objects.create(name="Org One")
    case = Case.objects.create(id="CASE-1", title="Example Case", organization=organization)
    job = Job.objects.create(case=case, organization=organization, audio_input="input.wav")

    case_base = ensure_case_dirs(case.id, organization.id)
    artifact_path = case_base / "analysis" / "artifact.md"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("review me", encoding="utf-8")

    artifact = CaseArtifact.objects.create(
        case_id=case.id,
        case_fk=case,
        organization=organization,
        job_id=str(job.id),
        type="SUMMARY",
        title="Summary",
        path=str(artifact_path),
        checksum="",
        schema_version="v1",
        metadata={},
    )

    call_payload = {}

    class DummyAgent:
        def __init__(self) -> None:
            self.config = SimpleNamespace(retry_attempts=1)

        def review(self, **kwargs):
            nonlocal call_payload
            call_payload = kwargs
            return SimpleNamespace(
                approved=True,
                provider="dummy",
                model="dummy",
                notes="",
                violations=[],
                remediation=[],
                usage={"total_tokens": 1},
            )

    context = SimpleNamespace(
        agent=DummyAgent(),
        credentials={},
        provider_chain=["dummy"],
        model="dummy",
        max_tokens=256,
        temperature=0.0,
        instructions=[{"id": "1"}],
        configuration_id="cfg-1",
        configuration_name="default",
    )

    monkeypatch.setattr(tasks, "build_guardian_context", lambda _org_id: context)
    monkeypatch.setattr(tasks, "_emit_job_update", lambda *_, **__: None)

    result = tasks.guardian_review_artifact.run(artifact_id=artifact.id)

    assert result["status"] == "approved"
    assert call_payload["case_id"] == case.id
    assert call_payload["job_id"] == str(job.id)

    updated_artifact = CaseArtifact.objects.get(pk=artifact.pk)
    assert updated_artifact.metadata.get("guardian_status") == "approved"


@pytest.mark.django_db
def test_guardian_review_artifact_falls_back_to_job_case(monkeypatch, settings, tmp_path):
    media_root = tmp_path / "media"
    media_root.mkdir()
    settings.MEDIA_ROOT = str(media_root)

    organization = Organization.objects.create(name="Org Two")
    case = Case.objects.create(id="CASE-2", title="Second Case", organization=organization)
    job = Job.objects.create(case=case, organization=organization, audio_input="input.wav")

    case_base = ensure_case_dirs(case.id, organization.id)
    artifact_path = case_base / "analysis" / "artifact.md"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("review me", encoding="utf-8")

    artifact = CaseArtifact.objects.create(
        case_id="",
        case_fk=case,
        organization=organization,
        job_id=str(job.id),
        type="SUMMARY",
        title="Summary",
        path=str(artifact_path),
        checksum="",
        schema_version="v1",
        metadata={},
    )

    call_payload = {}

    class DummyAgent:
        def __init__(self) -> None:
            self.config = SimpleNamespace(retry_attempts=1)

        def review(self, **kwargs):
            nonlocal call_payload
            call_payload = kwargs
            return SimpleNamespace(
                approved=True,
                provider="dummy",
                model="dummy",
                notes="",
                violations=[],
                remediation=[],
                usage={"total_tokens": 1},
            )

    context = SimpleNamespace(
        agent=DummyAgent(),
        credentials={},
        provider_chain=["dummy"],
        model="dummy",
        max_tokens=256,
        temperature=0.0,
        instructions=[{"id": "1"}],
        configuration_id="cfg-2",
        configuration_name="default",
    )

    monkeypatch.setattr(tasks, "build_guardian_context", lambda _org_id: context)
    monkeypatch.setattr(tasks, "_emit_job_update", lambda *_, **__: None)

    tasks.guardian_review_artifact.run(artifact_id=artifact.id)

    assert call_payload["case_id"] == case.id
