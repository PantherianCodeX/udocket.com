from __future__ import annotations

from pathlib import Path

import pytest

from packages.udocket_core.agents import build_summarize_graph
from packages.udocket_core.agents.summarize_lib import (
    SummarizeAgent,
    SummarizeConfig,
    TranscriptSegment,
    parse_transcript,
)


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
    result = agent.summarize(case_id="CASE-1", case_dir=case_dir, job_id="JOB-1")

    assert result.status == "ok"
    assert result.summary_file.exists()
    assert result.meta_json.exists()
    assert result.audit_jsonl.exists()
    meta_text = result.meta_json.read_text(encoding="utf-8")
    assert "summary_file" in meta_text


def test_build_summarize_graph_requires_langgraph():
    class Dummy:
        def input_discovery(self, state):
            return state

        parse_transcript = context_builder = extract_outline = build_timeline_seeds = build_entity_hints = draft_markdown = qa_and_finalize = write_ops_and_artifacts = input_discovery

    dummy = Dummy()
    with pytest.raises(RuntimeError):
        build_summarize_graph(dummy)
