from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from packages.udocket_core.agents import build_summarize_graph
from packages.udocket_core.agents.summarize_lib import (
    LLM_STAGE_KEYS,
    SUMMARIZE_STAGE_PROFILES,
    StageRuntime,
    SummarizeAgent,
    SummarizeConfig,
    SummarizePipeline,
    TranscriptParse,
    TranscriptSegment,
    parse_transcript,
    summarize_defaults,
)
from packages.udocket_core.agents.summarize.stages import (
    DraftStageResult,
    EntityStageResult,
    OutlineStageResult,
    TimelineStageResult,
)
from packages.udocket_core.agents.summarize.stages.outline_stage import generate_outline as outline_generate


def _write_transcript(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _install_stage_stubs(monkeypatch: pytest.MonkeyPatch, summary_text: str | None = None) -> None:
    if summary_text is None:
        summary_text = (
            "# Auto Summary\n\n"
            "## Executive summary\n- Key point\n\n"
            "## Detailed narrative\n- Narrative item\n\n"
            "## Claims and remedies sought\n- Claim A\n\n"
            "## Procedural posture, orders, and deadlines\n- Procedural note\n\n"
            "## Risks, gaps, and questions\n- Risk item\n\n"
            "## Next-step checklist\n- Next step\n"
        )

    def fake_outline(**_: Any) -> OutlineStageResult:
        outline = {
            "parties": {
                "client": {"name": "Client", "role": "Applicant"},
                "opposing": {"name": "Opposing", "role": "Respondent"},
                "counsel": [],
            },
            "issues": [
                {
                    "id": "ISSUE-1",
                    "title": "Preliminary issue",
                    "description": "Placeholder description",
                    "stance_client": None,
                    "stance_opposing": None,
                    "status": "RAISED",
                }
            ],
            "claims_and_remedies": [],
            "facts": [],
            "deadlines": [],
            "orders_and_directions": [],
            "exhibits": [],
            "legal_refs": [],
        }
        return OutlineStageResult(outline, {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})

    def fake_timeline(**_: Any) -> TimelineStageResult:
        events = [
            {"ts_start": 1.0, "ts_end": None, "speaker": "SPK_1", "text": "Event", "labels": ["summary"]}
        ]
        return TimelineStageResult(events, {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12})

    def fake_entities(**_: Any) -> EntityStageResult:
        hints = {
            "entities": [
                {"id": "E1", "name": "Test Person", "type": "PERSON", "aliases": [], "mentions": []},
            ],
            "relations": [],
        }
        return EntityStageResult(hints, {"prompt_tokens": 6, "completion_tokens": 3, "total_tokens": 9})

    def fake_summary(**_: Any) -> DraftStageResult:
        return DraftStageResult(summary_text, {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20})

    monkeypatch.setattr(
        "packages.udocket_core.agents.summarize.utils.generate_outline",
        fake_outline,
    )
    monkeypatch.setattr(
        "packages.udocket_core.agents.summarize.utils.generate_timeline",
        fake_timeline,
    )
    monkeypatch.setattr(
        "packages.udocket_core.agents.summarize.utils.generate_entities",
        fake_entities,
    )
    monkeypatch.setattr(
        "packages.udocket_core.agents.summarize.utils.generate_summary_markdown",
        fake_summary,
    )


def _make_config() -> SummarizeConfig:
    return SummarizeConfig(
        azure_openai_endpoint="https://example-canadacentral.openai.azure.com",
        azure_openai_key="test-key",
        azure_openai_deployment="test-deployment",
    )


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


def test_summarize_agent_writes_artifacts(monkeypatch, tmp_path):
    case_dir = tmp_path / "cases" / "CASE-1"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-1__transcript.txt"
    _write_transcript(
        transcript_path,
        """Header line\n---------------------------\n[00:01] SPK_1: Hello there\n[00:02] SPK_2: Welcome to court\n""",
    )

    _install_stage_stubs(monkeypatch)
    agent = SummarizeAgent(_make_config())
    result = agent.summarize(
        case_id="CASE-1",
        case_dir=case_dir,
        job_id="JOB-1",
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
    summary_text = result.summary_file.read_text(encoding="utf-8")
    assert summary_text.startswith("# Auto Summary")
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


def test_summarize_agent_versioned_outputs(monkeypatch, tmp_path):
    case_dir = tmp_path / "cases" / "CASE-2"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-2__transcript.txt"
    _write_transcript(
        transcript_path,
        """Heading\n---------------------------\n[00:01] SPK_1: Statement A\n[00:02] SPK_2: Statement B\n""",
    )

    _install_stage_stubs(monkeypatch)
    agent = SummarizeAgent(_make_config())
    first = agent.summarize(
        case_id="CASE-2",
        case_dir=case_dir,
        job_id="JOB-2",
    )
    second = agent.summarize(
        case_id="CASE-2",
        case_dir=case_dir,
        job_id="JOB-2",
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


def test_summarize_agent_requires_azure_configuration(tmp_path):
    case_dir = tmp_path / "cases" / "CASE-WARN"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-WARN__transcript.txt"
    _write_transcript(
        transcript_path,
        """Heading\n---------------------------\n[00:01] SPK_1: Missing key test\n""",
    )

    agent = SummarizeAgent(SummarizeConfig())

    with pytest.raises(RuntimeError):
        agent.summarize(
            case_id="CASE-WARN",
            case_dir=case_dir,
            job_id="JOB-WARN",
        )


def test_summarize_agent_adds_default_header(monkeypatch, tmp_path):
    case_dir = tmp_path / "cases" / "CASE-3"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-3__transcript.txt"
    _write_transcript(
        transcript_path,
        """[00:01] Speaker: Hello\n[00:05] Another line\n""",
    )

    _install_stage_stubs(monkeypatch, summary_text="Executive summary only")
    agent = SummarizeAgent(_make_config())
    result = agent.summarize(
        case_id="CASE-3",
        case_dir=case_dir,
        job_id="JOB-3",
    )

    summary_text = result.summary_file.read_text(encoding="utf-8")
    assert summary_text.startswith("# Summary for case CASE-3 (job JOB-3)")


def test_stage_catalog_lists_recommended_models():
    agent = SummarizeAgent(SummarizeConfig())

    catalog = agent.stage_catalog()
    outline_info = catalog["summarize.extract_outline"]

    assert outline_info["resource_notes"]
    assert outline_info["recommended_models"]
    for entry in outline_info["recommended_models"]:
        tokens = entry.get("context_window_tokens")
        if tokens is not None:
            assert tokens >= outline_info["recommended_context_tokens"]


def test_summarize_config_uses_defaults_file():
    defaults = summarize_defaults()
    cfg = SummarizeConfig.from_env()

    assert cfg.temperature == defaults["temperature"]
    assert cfg.max_output_tokens == defaults["max_output_tokens"]
    assert cfg.max_prompt_segments == defaults["max_prompt_segments"]
    assert cfg.max_prompt_chars == defaults["max_prompt_chars"]
    assert cfg.provider_chain == [value.lower() for value in defaults["default_provider_chain"]]



def test_stage_temperature_and_max_tokens_override(monkeypatch, tmp_path):
    case_dir = tmp_path / "cases" / "CASE-OVR"
    transcript = case_dir / "transcript" / "JOB-OVR__transcript.txt"
    _write_transcript(transcript, "[00:00] Speaker: Hello world")

    _install_stage_stubs(monkeypatch)

    recorded_temperatures: list[float] = []
    recorded_max_tokens: list[int] = []

    def capture_summary(**kwargs: Any) -> DraftStageResult:
        recorded_temperatures.append(kwargs.get("temperature"))
        recorded_max_tokens.append(kwargs.get("max_tokens"))
        return DraftStageResult("Summary", {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10})

    monkeypatch.setattr(
        "packages.udocket_core.agents.summarize.utils.generate_summary_markdown",
        capture_summary,
    )

    agent = SummarizeAgent(_make_config())
    agent.summarize(
        case_id="CASE-OVR",
        case_dir=case_dir,
        job_id="JOB-OVR",
        input=transcript,
        provider_chain=["azure"],
        stage_map={
            "summarize.draft_markdown": {
                "provider": "azure",
                "model": "gpt-4o",
                "max_tokens": 5000,
                "options": {"temperature": 0.3},
            }
        },
    )

    assert recorded_temperatures == [0.3]
    assert recorded_max_tokens == [5000]


def test_outline_chunk_splitting_on_empty_completion():
    large_segments = [
        TranscriptSegment(ts=float(i), speaker=f"SPK_{i%3}", text=f"Sentence {i} " + ("Lorem ipsum " * 10).strip())
        for i in range(60)
    ]
    parse = TranscriptParse(
        header_lines=[],
        segments=large_segments,
        body_text="",
        diarized=True,
    )

    class FailingAzureClient:
        def __init__(self) -> None:
            self.calls: List[int] = []

        def chat(self, *, messages, temperature, max_tokens, response_format):  # type: ignore[no-untyped-def]
            prompt = messages[-1]["content"]
            marker = "):\n"
            chunk_text = prompt.split(marker, 1)[1]
            line_count = len([line for line in chunk_text.splitlines() if line.strip()])
            self.calls.append(line_count)
            if line_count > 12:
                raise RuntimeError(
                    "Azure OpenAI returned an empty completion (deployment='stub', request_id='stub', finish_reason='length')."
                )
            payload = {
                "parties": {
                    "client": {"name": "Client", "role": "applicant"},
                    "opposing": {"name": "Other", "role": "respondent"},
                    "counsel": [],
                },
                "issues": [
                    {
                        "id": "ISSUE-1",
                        "title": "Title",
                        "description": "Desc",
                        "stance_client": None,
                        "stance_opposing": None,
                        "status": "RAISED",
                    }
                ],
                "claims_and_remedies": [],
                "facts": [],
                "deadlines": [],
                "orders_and_directions": [],
                "exhibits": [],
                "legal_refs": [],
            }
            return json.dumps(payload), {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

    azure_stub = FailingAzureClient()
    context_snippet = "\n".join(seg.text for seg in large_segments)
    result = outline_generate(
        parse=parse,
        intake={},
        context_snippet=context_snippet,
        case_brief={},
        azure_client=azure_stub,
        temperature=0.0,
        max_tokens=8000,
    )

    assert result.outline["issues"]
    assert any(count > 12 for count in azure_stub.calls)
    assert any(count <= 12 for count in azure_stub.calls)


def test_build_context_respects_config_limits(tmp_path):
    transcript = tmp_path / "demo.txt"
    _write_transcript(
        transcript,
        "Heading\n-----------------\n"
        + "\n".join(f"[00:{i:02d}] SPK_{i % 2}: line {i}" for i in range(1, 25))
    )
    parse = parse_transcript(transcript)
    cfg = SummarizeConfig(
        max_prompt_segments=5,
        prompt_segments_override=5,
        max_prompt_chars=80,
        prompt_chars_override=80,
    )

    stage_runtimes: Dict[str, StageRuntime] = {}
    for stage_key in LLM_STAGE_KEYS.values():
        profile = SUMMARIZE_STAGE_PROFILES[stage_key]
        stage_runtimes[stage_key] = StageRuntime(
            stage_key=stage_key,
            providers=["azure"],
            model="gpt-5-mini",
            azure_client=None,
            max_output_tokens=profile.min_context_tokens,
            context_window_tokens=200000,
            profile=profile,
            temperature=cfg.temperature,
        )

    def resolve_transcript(input_path, case_dir):
        return transcript

    pipeline = SummarizePipeline(
        case_id="CASE-CTX",
        job_id="JOB-CTX",
        case_dir=tmp_path,
        intake={},
        transcript_hint=None,
        config=cfg,
        resolve_transcript=resolve_transcript,
        build_context=lambda p, _: "",
        provider_chain=["azure"],
        stage_runtimes=stage_runtimes,
        default_temperature=cfg.temperature,
    )

    state: Dict[str, Any] = {"parse": parse}
    pipeline.context_builder(state)
    outline_chunks = state["context_chunks"]["summarize.extract_outline"]
    first_chunk = outline_chunks[0]
    lines = first_chunk.splitlines()

    assert len(lines) <= cfg.prompt_segments_override
    total_chars = sum(len(line) for line in lines)
    max_line = max((len(line) for line in lines), default=0)
    assert total_chars <= cfg.prompt_chars_override + max_line


def test_summarize_agent_raises_on_stage_failure(monkeypatch, tmp_path):
    _install_stage_stubs(monkeypatch)

    def boom(**_: Any) -> OutlineStageResult:
        raise RuntimeError("outline failure")

    monkeypatch.setattr(
        "packages.udocket_core.agents.summarize.utils.generate_outline",
        boom,
    )

    case_dir = tmp_path / "cases" / "CASE-4"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-4__transcript.txt"
    _write_transcript(
        transcript_path,
        """Header\n---------------------------\n[00:01] SPK_1: Test line\n""",
    )

    agent = SummarizeAgent(_make_config())

    with pytest.raises(RuntimeError):
        agent.summarize(case_id="CASE-4", case_dir=case_dir, job_id="JOB-4")



def test_build_summarize_graph_requires_langgraph():
    class Dummy:
        def input_discovery(self, state):
            return state

        parse_transcript = context_builder = extract_outline = build_timeline_seeds = build_entity_hints = draft_markdown = qa_and_finalize = write_ops_and_artifacts = input_discovery

    dummy = Dummy()
    with pytest.raises(RuntimeError):
        build_summarize_graph(dummy)
