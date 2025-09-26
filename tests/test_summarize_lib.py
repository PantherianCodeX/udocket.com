from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.udocket_core.agents import build_summarize_graph
from packages.udocket_core.agents.summarize_lib import (
    SummarizeAgent,
    SummarizeConfig,
    TranscriptSegment,
    parse_transcript,
)
from packages.udocket_core.agents.summarize.exceptions import (
    AzureStageFailure,
    AzureUnavailableError,
)
from packages.udocket_core.agents.summarize.stages import OutlineStageResult


def _write_transcript(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_transcript_detects_header_and_segments(tmp_path):
    transcript = tmp_path / "sample.txt"
    _write_transcript(
        transcript,
        """Case: TEST\n-------------------------------\n[00:01] SPK_1: Hello there\n[00:05] SPK_2: General Kenobi\nSome trailing note\n""",
    )

    parsed = parse_transcript(transcript)

    assert parsed.header_lines == ["Case: TEST"]
    assert parsed.diarized is True
    assert parsed.segments[0] == TranscriptSegment(ts=1, speaker="SPK_1", text="Hello there")
    assert parsed.segments[-1] == TranscriptSegment(ts=None, speaker=None, text="Some trailing note")


def test_parse_transcript_handles_missing_divider(tmp_path):
    transcript = tmp_path / "plain.txt"
    _write_transcript(transcript, "[00:10] Hello world\nSecond line")

    parsed = parse_transcript(transcript)

    assert parsed.header_lines == []
    assert len(parsed.segments) == 2
    assert parsed.segments[0].ts == 10


def test_summarize_agent_offline_writes_artifacts(tmp_path):
    case_dir = tmp_path / "cases" / "CASE-1"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-1__transcript.txt"
    _write_transcript(
        transcript_path,
        """Header line\n---------------------------\n[00:01] SPK_1: Hello there\n[00:02] SPK_2: Welcome to court\n""",
    )

    agent = SummarizeAgent(SummarizeConfig())
    result = agent.summarize(
        case_id="CASE-1",
        case_dir=case_dir,
        job_id="JOB-1",
        allow_offline_fallback=True,
    )

    assert result.status == "ok"
    assert result.summary_file.exists()
    assert result.outline_file and result.outline_file.exists()
    assert result.timeline_seeds_file and result.timeline_seeds_file.exists()
    assert result.entity_hints_file and result.entity_hints_file.exists()
    assert result.case_brief_file and result.case_brief_file.exists()
    assert result.meta_json.exists()
    assert result.audit_jsonl.exists()
    meta = json.loads(result.meta_json.read_text(encoding="utf-8"))
    assert "summary_file" in meta
    assert "outline_file" in meta
    assert "case_brief_file" in meta
    assert meta.get("provider_chain")
    assert result.provider_chain
    assert result.offline_fallback_used is True
    summary_text = result.summary_file.read_text(encoding="utf-8")
    assert summary_text.startswith("# Header line")
    required_headings = [
        "## Case metadata summary",
        "## Executive summary",
        "## Detailed narrative",
        "## Claims and remedies sought",
        "## Procedural posture, orders, and deadlines",
        "## Risks, gaps, and questions",
        "## Next-step checklist",
    ]
    for heading in required_headings:
        assert heading in summary_text


def test_summarize_agent_versioned_outputs(tmp_path):
    case_dir = tmp_path / "cases" / "CASE-2"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-2__transcript.txt"
    _write_transcript(
        transcript_path,
        """Heading\n---------------------------\n[00:01] SPK_1: Statement A\n[00:02] SPK_2: Statement B\n""",
    )

    agent = SummarizeAgent(SummarizeConfig())
    first = agent.summarize(
        case_id="CASE-2",
        case_dir=case_dir,
        job_id="JOB-2",
        allow_offline_fallback=True,
    )
    second = agent.summarize(
        case_id="CASE-2",
        case_dir=case_dir,
        job_id="JOB-2",
        allow_offline_fallback=True,
    )

    assert first.summary_file.exists()
    assert second.summary_file.exists()
    assert first.summary_file != second.summary_file
    assert second.summary_file.name.endswith("_v2.md")
    assert first.case_brief_file and first.case_brief_file.exists()
    assert second.case_brief_file and second.case_brief_file.exists()
    assert first.case_brief_file != second.case_brief_file
    assert second.case_brief_file.name.endswith("_v2.json")
    assert first.provider_chain


def test_summarize_agent_warns_when_azure_missing(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://example-canadacentral.openai.azure.com",
    )
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini-test")
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    caplog.set_level("WARNING", "udocket.summarize.agent")

    case_dir = tmp_path / "cases" / "CASE-WARN"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-WARN__transcript.txt"
    _write_transcript(
        transcript_path,
        """Heading\n---------------------------\n[00:01] SPK_1: Missing key test\n""",
    )

    config = SummarizeConfig.from_env()
    agent = SummarizeAgent(config)
    result = agent.summarize(
        case_id="CASE-WARN",
        case_dir=case_dir,
        job_id="JOB-WARN",
        allow_offline_fallback=True,
    )

    assert result.offline_fallback_used is True
    warning_messages = [record.message for record in caplog.records]
    assert any("Azure provider disabled" in message for message in warning_messages)


def test_summarize_agent_adds_default_header(tmp_path):
    case_dir = tmp_path / "cases" / "CASE-3"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-3__transcript.txt"
    _write_transcript(
        transcript_path,
        """[00:01] Speaker: Hello\n[00:05] Another line\n""",
    )

    agent = SummarizeAgent(SummarizeConfig())
    result = agent.summarize(
        case_id="CASE-3",
        case_dir=case_dir,
        job_id="JOB-3",
        allow_offline_fallback=True,
    )

    summary_text = result.summary_file.read_text(encoding="utf-8")
    assert summary_text.startswith("# Summary for case CASE-3 (job JOB-3)")


def test_azure_failure_requires_consent(monkeypatch, tmp_path):
    fallback_outline = {
        "parties": {
            "client": {"name": None, "role": None},
            "opposing": {"name": None, "role": None},
            "counsel": [],
        },
        "issues": [],
        "claims_and_remedies": [],
        "facts": [],
        "deadlines": [],
        "orders_and_directions": [],
        "exhibits": [],
        "legal_refs": [],
    }
    fallback_result = OutlineStageResult(fallback_outline, {})

    def boom(**kwargs):
        raise AzureStageFailure("outline", RuntimeError("boom"), fallback_result)

    monkeypatch.setattr(
        "packages.udocket_core.agents.summarize.utils.generate_outline",
        boom,
    )
    monkeypatch.setattr(
        "packages.udocket_core.agents.common.azure_client.AzureChatClient.chat",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("network down")),
    )

    case_dir = tmp_path / "cases" / "CASE-4"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-4__transcript.txt"
    _write_transcript(
        transcript_path,
        """Header\n---------------------------\n[00:01] SPK_1: Test line\n""",
    )

    config = SummarizeConfig(
        azure_openai_endpoint="https://unit-canadacentral.openai.azure.com",
        azure_openai_key="test-key",
        azure_openai_deployment="test-deploy",
    )
    agent = SummarizeAgent(config)

    with pytest.raises(AzureUnavailableError):
        agent.summarize(case_id="CASE-4", case_dir=case_dir, job_id="JOB-4")

    result = agent.summarize(
        case_id="CASE-4",
        case_dir=case_dir,
        job_id="JOB-4",
        allow_offline_fallback=True,
    )
    meta = json.loads(result.meta_json.read_text(encoding="utf-8"))
    assert meta.get("offline_fallback_used") is True
    assert meta.get("provider_chain")
    assert result.summary_file.exists()
    assert result.case_brief_file and result.case_brief_file.exists()


def test_summarize_agent_provider_override(tmp_path):
    case_dir = tmp_path / "cases" / "CASE-5"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-5__transcript.txt"
    _write_transcript(
        transcript_path,
        """Header\n---------------------------\n[00:01] SPK_1: Custom provider test\n""",
    )

    agent = SummarizeAgent(SummarizeConfig())
    overrides = {
        "summarize.context_builder": {"provider": "local", "fallbacks": [], "model": "offline_v1"},
        "summarize.extract_outline": {"provider": "local", "fallbacks": [], "model": "offline_v1"},
        "summarize.build_timeline_seeds": {"provider": "local", "fallbacks": [], "model": "offline_v1"},
        "summarize.build_entity_hints": {"provider": "local", "fallbacks": [], "model": "offline_v1"},
        "summarize.draft_markdown": {"provider": "local", "fallbacks": [], "model": "offline_v1"},
        "summarize.qa_and_finalize": {"provider": "local", "fallbacks": [], "model": "offline_v1"},
    }
    result = agent.summarize(
        case_id="CASE-5",
        case_dir=case_dir,
        job_id="JOB-5",
        allow_offline_fallback=True,
        provider_chain=["local"],
        stage_overrides=overrides,
    )

    assert result.provider_chain == ["local"]
    meta = json.loads(result.meta_json.read_text(encoding="utf-8"))
    assert meta.get("provider_chain") == ["local"]


def test_build_summarize_graph_requires_langgraph():
    class Dummy:
        def input_discovery(self, state):
            return state

        parse_transcript = context_builder = extract_outline = build_timeline_seeds = build_entity_hints = draft_markdown = qa_and_finalize = write_ops_and_artifacts = input_discovery

    dummy = Dummy()
    with pytest.raises(RuntimeError):
        build_summarize_graph(dummy)


def test_config_provider_chain_from_env(monkeypatch):
    monkeypatch.setenv("SUMMARY_PRIMARY_PROVIDER", "local")
    monkeypatch.setenv("SUMMARY_FALLBACK_PROVIDERS", "azure,local")
    cfg = SummarizeConfig.from_env()
    assert cfg.provider_chain[0] == "local"
    # duplicates should be removed while keeping order
    assert cfg.provider_chain == ["local", "azure"]
    monkeypatch.delenv("SUMMARY_PRIMARY_PROVIDER", raising=False)
    monkeypatch.delenv("SUMMARY_FALLBACK_PROVIDERS", raising=False)
