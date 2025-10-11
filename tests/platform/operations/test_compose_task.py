from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.platform.accounts.models import Organization
from apps.platform.artifacts.models import CaseArtifact
from apps.platform.cases.models import Case
from apps.platform.jobs.models import Job
from apps.platform.operations import runtime as operations_runtime
from apps.platform.operations import tasks
from apps.platform.operations.services import compose as compose_service
from apps.platform.operations.storage import ensure_case_dirs
from apps.platform.operations.utils import read_job_meta, update_job_meta
from packages.udocket_core.agents.compose_lib import ComposeResult
from tests._typing import MonkeyPatch, SettingsFixture


def _stub_task_notifications(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(tasks, "_emit_job_update", lambda *_, **__: None)
    monkeypatch.setattr(tasks, "send_case_update", lambda *_, **__: None)
    monkeypatch.setattr(tasks, "send_job_update", lambda *_, **__: None)
    monkeypatch.setattr(tasks, "audit_emit", lambda *_, **__: None)
    monkeypatch.setattr(operations_runtime, "send_job_update", lambda *_, **__: None)


@pytest.mark.django_db
def test_compose_job_uses_summary_outputs(monkeypatch: MonkeyPatch, settings: SettingsFixture, tmp_path: Path) -> None:
    _stub_task_notifications(monkeypatch)

    media_root = tmp_path / "media"
    media_root.mkdir()
    settings.MEDIA_ROOT = str(media_root)

    organization = Organization.objects.create(name="Org One")
    case = Case.objects.create(id="CASE-42", title="Compose Case", organization=organization)
    summary_job = Job.objects.create(case=case, organization=organization, audio_input="analysis.wav")
    compose_job_obj = Job.objects.create(case=case, organization=organization, audio_input="compose.wav")

    case_dir = ensure_case_dirs(case.id, organization.id)
    analysis_dir = case_dir / "analysis"
    transcript_dir = case_dir / "transcript"
    ops_dir = case_dir / "ops"

    summary_json = analysis_dir / f"{summary_job.id}__summary_v1.json"
    summary_json.write_text(json.dumps({"sections": [{"title": "Overview"}]}), encoding="utf-8")
    summary_markdown = analysis_dir / f"{summary_job.id}__summary_v1.md"
    summary_markdown.write_text("# Summary\n\nContent.\n", encoding="utf-8")
    timeline_seeds = analysis_dir / f"{summary_job.id}__timeline_seeds_v1.json"
    timeline_seeds.write_text("[]", encoding="utf-8")
    entity_hints = analysis_dir / f"{summary_job.id}__entity_hints_v1.json"
    entity_hints.write_text("{}", encoding="utf-8")
    transcript_path = transcript_dir / f"{summary_job.id}__transcript.txt"
    transcript_path.write_text("Transcript body", encoding="utf-8")

    update_job_meta(
        case.id,
        organization.id,
        str(summary_job.id),
        {
            "summary_file": str(summary_json),
            "summary_markdown_file": str(summary_markdown),
            "summary_timeline_file": str(timeline_seeds),
            "summary_entity_file": str(entity_hints),
            "source_transcript_path": str(transcript_path),
            "intake": {"client_position": "Applicant"},
        },
    )

    compose_calls: list[dict[str, object]] = []

    class DummyComposeAgent:
        def __init__(self, config: object) -> None:
            self.config = config

        def compose(
            self,
            *,
            case_id: str,
            case_dir: Path,
            job_id: str,
            summary_json_path: Path | None,
            summary_markdown_path: Path | None,
            timeline_seed_path: Path | None,
            entity_hint_path: Path | None,
            provider_chain: list[str] | None = None,
            stage_map: dict[str, object] | None = None,
            progress_callback=None,
            **_kwargs: object,
        ) -> ComposeResult:
            compose_calls.append(
                {
                    "case_id": case_id,
                    "case_dir": case_dir,
                    "job_id": job_id,
                    "summary_json_path": summary_json_path,
                    "summary_markdown_path": summary_markdown_path,
                    "timeline_seed_path": timeline_seed_path,
                    "entity_hint_path": entity_hint_path,
                    "provider_chain": provider_chain,
                    "stage_map": stage_map,
                    "resume": _kwargs.get("resume"),
                }
            )
            docs_dir = case_dir / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            client_markdown = docs_dir / f"{job_id}__compose_client_v1.md"
            client_markdown.write_text("Client deliverable", encoding="utf-8")
            meta_json = ops_dir / f"{job_id}__compose_log.json"
            meta_json.write_text(json.dumps({"status": "ok"}), encoding="utf-8")
            audit_jsonl = ops_dir / "ops_compose.jsonl"
            audit_jsonl.write_text("{}", encoding="utf-8")
            if progress_callback is not None:
                progress_callback(
                    "compose.client.draft",
                    "start",
                    {"lane": "client"},
                )
            artifacts = SimpleNamespace(
                client_markdown=client_markdown,
                lawyer_markdown=None,
                client_docx=None,
                lawyer_docx=None,
                bundle_path=None,
                qa_report=None,
                staff_report=None,
                timeline_file=None,
                graph_file=None,
                entities_file=None,
                timeline_summary=None,
                entity_brief=None,
                graph_visual_json=None,
                graph_html=None,
                graph_image=None,
            )
            return ComposeResult(
                status="ok",
                artifacts=artifacts,
                meta_json=meta_json,
                audit_jsonl=audit_jsonl,
                provider_chain=["dummy"],
                stage_usage={"compose.client.draft": {"prompt_tokens": 12}},
                stage_durations={"compose.client.draft": 1.2},
            )

    monkeypatch.setattr(compose_service, "ComposeAgent", DummyComposeAgent)
    monkeypatch.setattr(
        compose_service.ComposeConfig,
        "from_env",
        classmethod(lambda cls: cls(provider_chain=["dummy"])),
    )
    monkeypatch.setattr(
        compose_service,
        "load_llm_settings",
        lambda: SimpleNamespace(stage=lambda *_args, **_kwargs: None),
    )
    monkeypatch.setattr(compose_service, "get_llm_configuration", lambda **_kwargs: None)
    monkeypatch.setattr(
        compose_service,
        "ensure_default_llm_configuration",
        lambda **_kwargs: {"provider_chain": ["dummy"], "stage_map": {}},
    )
    monkeypatch.setattr(compose_service, "get_provider_secret_with_metadata", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(compose_service, "collect_requested_providers", lambda *_args, **_kwargs: ["dummy"])

    result = tasks.compose_job.run(
        case_id=str(case.id),
        job_id=str(compose_job_obj.id),
        summary_job_id=str(summary_job.id),
        llm_config_id=None,
    )

    assert result["status"] == "ok"
    assert len(compose_calls) == 1
    call = compose_calls[0]
    assert call["summary_json_path"] == summary_json
    assert call["summary_markdown_path"] == summary_markdown
    assert call["timeline_seed_path"] == timeline_seeds
    assert call["entity_hint_path"] == entity_hints

    artifacts = list(CaseArtifact.objects.filter(case_id=case.id, type="COMPOSE"))
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert Path(artifact.path).read_text(encoding="utf-8") == "Client deliverable"
    assert artifact.metadata["format"] == "markdown"

    meta = read_job_meta(case.id, organization.id, str(compose_job_obj.id))
    assert meta.get("compose_status") == "completed"
    assert meta.get("compose_client_markdown") == artifact.path
    assert meta.get("summary_job_id") == str(summary_job.id)
    assert result["client_markdown"] == artifact.path


@pytest.mark.django_db
def test_compose_job_rejects_cross_case_summary(monkeypatch: MonkeyPatch, settings: SettingsFixture, tmp_path: Path) -> None:
    _stub_task_notifications(monkeypatch)

    media_root = tmp_path / "media"
    media_root.mkdir()
    settings.MEDIA_ROOT = str(media_root)

    organization = Organization.objects.create(name="Org Two")
    case_one = Case.objects.create(id="CASE-A", title="Case A", organization=organization)
    case_two = Case.objects.create(id="CASE-B", title="Case B", organization=organization)

    summary_job = Job.objects.create(case=case_two, organization=organization, audio_input="analysis.wav")
    compose_job_obj = Job.objects.create(case=case_one, organization=organization, audio_input="compose.wav")

    with pytest.raises(RuntimeError, match="Summary job belongs to a different case"):
        tasks.compose_job.run(
            case_id=str(case_one.id),
            job_id=str(compose_job_obj.id),
            summary_job_id=str(summary_job.id),
            llm_config_id=None,
        )
