from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

import packages.core.agents.analyze_lib as analyze_lib

from packages.core.agents import build_analyze_graph, langgraph_orchestrator
from packages.core.agents.analyze_lib import (
    LLM_STAGE_KEYS,
    ANALYZE_STAGE_PROFILES,
    StageRuntime,
    AnalyzeAgent,
    AnalyzeConfig,
    AnalyzePipeline,
    TranscriptParse,
    TranscriptSegment,
    analyze_defaults,
    parse_transcript,
    _normalize_stage_map,
)
from packages.core.agents.analyze.stages import (
    EntityStageResult,
    OutlineStageResult,
    SummaryStageResult,
    TimelineStageResult,
    generate_summary_payload,
)
from packages.core.agents.analyze.stages.outline_stage import generate_outline as outline_generate
from packages.core.llm.config import (
    LLMProvider,
    LLMProviderModel,
    LLMSettings,
    LLMStageAssignment,
)
from packages.core.llm.runtime import ChatClientError
from packages.common.agents import (
    StageKey,
    StageOverrideConfig,
    normalize_stage_override_mapping,
)
from tests._typing import MonkeyPatch


FAKE_AZURE_SECRET = {
    "endpoint": "https://example-canadacentral.openai.azure.com",
    "api_key": "test-key",
    "metadata": {"azure_deployment": "test-deployment"},
}


def _write_transcript(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _install_llm_settings_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    azure_models = {
        "gpt-5-mini": LLMProviderModel(
            name="gpt-5-mini",
            label="GPT-5 Mini",
            cost_tier="standard",
            default_enabled=True,
            max_output_tokens=16000,
            context_window_tokens=200000,
            default_temperature=1.0,
        ),
        "gpt-5": LLMProviderModel(
            name="gpt-5",
            label="GPT-5",
            cost_tier="premium",
            default_enabled=True,
            max_output_tokens=32000,
            context_window_tokens=220000,
            default_temperature=1.0,
        ),
        "gpt-4o": LLMProviderModel(
            name="gpt-4o",
            label="GPT-4o",
            cost_tier="standard",
            default_enabled=True,
            max_output_tokens=10000,
            context_window_tokens=128000,
            default_temperature=1.0,
        ),
    }
    azure_provider = LLMProvider(
        name="azure",
        display_name="Azure",
        models=azure_models,
    )
    assignments: Dict[str, LLMStageAssignment] = {}
    for stage_key in LLM_STAGE_KEYS.values():
        model_name = "gpt-5" if stage_key == "analyze.draft_markdown" else "gpt-5-mini"
        assignments[stage_key] = LLMStageAssignment(
            stage_key=stage_key,
            providers=["azure"],
            model=model_name,
        )
    settings = LLMSettings(
        providers={"azure": azure_provider},
        assignments=assignments,
    )
    monkeypatch.setattr(analyze_lib, "_llm_settings_cache", settings, raising=False)
    monkeypatch.setattr(analyze_lib, "_load_llm_settings", lambda: settings)


def _install_stage_stubs(monkeypatch: pytest.MonkeyPatch, summary_text: str | None = None) -> None:
    if summary_text is None:
        summary_text = (
            "# Summary\n\n"
            "## Executive summary\n- Key point\n\n"
            "## Detailed narrative\n- Narrative item\n\n"
            "## Claims and remedies sought\n- Claim A\n\n"
            "## Procedural posture, orders, and deadlines\n- Procedural note\n\n"
            "## Risks, gaps, and questions\n- Risk item\n\n"
            "## Next-step checklist\n- Next step\n"
        )

    summary_payload = {
        "case_metadata_summary": {
            "overview": "Case overview",
            "parties": ["Client", "Opposing"],
            "jurisdiction": "Ontario",
            "key_dates": ["2024-01-01"],
        },
        "executive_summary": {"bullets": ["Key point"]},
        "detailed_narrative": [
            {"heading": "Narrative item", "summary": "Narrative summary.", "citations": []}
        ],
        "claims_and_remedies": [
            {"claim": "Claim A", "remedy_requested": "Remedy"}
        ],
        "procedural_posture": {
            "status": "Active",
            "deadlines": ["2024-02-01"],
            "orders": ["Order 1"],
        },
        "risks_gaps_questions": [
            {"issue": "Risk item", "risk_level": "medium", "notes": "Watch this."}
        ],
        "next_step_checklist": [
            {"action": "Next step", "owner": "Team", "due": "ASAP"}
        ],
        "supporting_quotes": [
            {"timestamp": "00:01", "speaker": "SPK_1", "text": "Hello there"}
        ],
    }

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
        return OutlineStageResult(
            outline,
            {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            (),
        )

    def fake_timeline(**_: Any) -> TimelineStageResult:
        events = [
            {
                "id": "event-1",
                "uuid": "event-1",
                "ts_start": 1.0,
                "ts_end": None,
                "speaker": "SPK_1",
                "text": "Event",
                "labels": ["summary"],
            }
        ]
        return TimelineStageResult(
            events,
            {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
            (),
        )

    def fake_entities(**_: Any) -> EntityStageResult:
        hints = {
            "entities": [
                {
                    "id": "entity-1",
                    "uuid": "entity-1",
                    "name": "Test Person",
                    "type": "PERSON",
                    "aliases": [],
                    "mentions": [],
                    "description": "",
                },
            ],
            "relations": [
                {
                    "id": "relation-1",
                    "uuid": "relation-1",
                    "type": "RELATED_TO",
                    "source": "entity-1",
                    "target": "entity-1",
                    "evidence": [],
                    "summary": "",
                }
            ],
        }
        return EntityStageResult(
            hints,
            {"prompt_tokens": 6, "completion_tokens": 3, "total_tokens": 9},
            (),
        )

    def fake_summary(**_: Any) -> SummaryStageResult:
        return SummaryStageResult(
            data=summary_payload,
            markdown=summary_text,
            usage={"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
            prompts=(),
        )

    monkeypatch.setattr(
        "packages.core.agents.analyze.utils.generate_outline",
        fake_outline,
    )
    monkeypatch.setattr(
        "packages.core.agents.analyze.utils.generate_timeline",
        fake_timeline,
    )
    monkeypatch.setattr(
        "packages.core.agents.analyze.utils.generate_entities",
        fake_entities,
    )
    monkeypatch.setattr(
        "packages.core.agents.analyze.utils.generate_summary_payload",
        fake_summary,
    )


def _make_config() -> AnalyzeConfig:
    return AnalyzeConfig(provider_chain=["azure"])


def _make_llm_settings(
    provider_order: List[str],
    providers: Dict[str, LLMProvider],
) -> LLMSettings:
    assignments: Dict[str, LLMStageAssignment] = {}
    for stage_key in LLM_STAGE_KEYS.values():
        assignments[stage_key] = LLMStageAssignment(
            stage_key=stage_key,
            providers=list(provider_order),
            model="",
        )
    return LLMSettings(providers=providers, assignments=assignments)


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


def test_analyze_agent_writes_artifacts(monkeypatch: MonkeyPatch, tmp_path):
    case_dir = tmp_path / "cases" / "CASE-1"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-1__transcript.txt"
    _write_transcript(
        transcript_path,
        """Header line\n---------------------------\n[00:01] SPK_1: Hello there\n[00:02] SPK_2: Welcome to court\n""",
    )

    _install_llm_settings_stub(monkeypatch)
    _install_stage_stubs(monkeypatch)
    agent = AnalyzeAgent(_make_config())
    result = agent.analyze(
        case_id="CASE-1",
        case_dir=case_dir,
        job_id="JOB-1",
        provider_credentials={"azure": FAKE_AZURE_SECRET},
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
    summary_payload = json.loads(result.summary_file.read_text(encoding="utf-8"))
    assert summary_payload["executive_summary"]["bullets"][0] == "Key point"
    markdown_text = result.summary_markdown_file.read_text(encoding="utf-8")
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
        assert heading in markdown_text


def test_analyze_agent_versioned_outputs(monkeypatch: MonkeyPatch, tmp_path):
    case_dir = tmp_path / "cases" / "CASE-2"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-2__transcript.txt"
    _write_transcript(
        transcript_path,
        """Heading\n---------------------------\n[00:01] SPK_1: Statement A\n[00:02] SPK_2: Statement B\n""",
    )

    _install_llm_settings_stub(monkeypatch)
    _install_stage_stubs(monkeypatch)
    agent = AnalyzeAgent(_make_config())
    first = agent.analyze(
        case_id="CASE-2",
        case_dir=case_dir,
        job_id="JOB-2",
        provider_credentials={"azure": FAKE_AZURE_SECRET},
    )
    second = agent.analyze(
        case_id="CASE-2",
        case_dir=case_dir,
        job_id="JOB-2",
        provider_credentials={"azure": FAKE_AZURE_SECRET},
    )

    assert first.summary_file.exists()
    assert second.summary_file.exists()
    assert first.summary_file != second.summary_file
    assert second.summary_file.name.endswith("_v2.json")
    assert second.summary_markdown_file and second.summary_markdown_file.exists()
    assert second.summary_markdown_file.name.endswith("_v2.md")
    assert first.case_brief_file and first.case_brief_file.exists()
    assert second.case_brief_file and second.case_brief_file.exists()
    assert first.case_brief_file != second.case_brief_file
    assert second.case_brief_file.name.endswith("_v2.json")
    assert first.provider_chain


def test_analyze_agent_requires_azure_configuration(tmp_path):
    case_dir = tmp_path / "cases" / "CASE-WARN"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-WARN__transcript.txt"
    _write_transcript(
        transcript_path,
        """Heading\n---------------------------\n[00:01] SPK_1: Missing key test\n""",
    )

    agent = AnalyzeAgent(AnalyzeConfig())

    with pytest.raises(RuntimeError):
        agent.analyze(
            case_id="CASE-WARN",
            case_dir=case_dir,
            job_id="JOB-WARN",
        )


def test_analyze_agent_adds_default_header(monkeypatch: MonkeyPatch, tmp_path):
    case_dir = tmp_path / "cases" / "CASE-3"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-3__transcript.txt"
    _write_transcript(
        transcript_path,
        """[00:01] Speaker: Hello\n[00:05] Another line\n""",
    )

    _install_llm_settings_stub(monkeypatch)
    _install_stage_stubs(monkeypatch, summary_text="Executive summary only")
    agent = AnalyzeAgent(_make_config())
    result = agent.analyze(
        case_id="CASE-3",
        case_dir=case_dir,
        job_id="JOB-3",
        provider_credentials={"azure": FAKE_AZURE_SECRET},
    )

    summary_payload = json.loads(result.summary_file.read_text(encoding="utf-8"))
    summary_text = result.summary_markdown_file.read_text(encoding="utf-8")
    assert summary_text.startswith("# Summary for case CASE-3 (job JOB-3)")
    assert summary_payload["executive_summary"]["bullets"]


def test_stage_catalog_lists_recommended_models():
    agent = AnalyzeAgent(AnalyzeConfig())

    catalog = agent.stage_catalog()
    outline_info = catalog["analyze.extract_outline"]

    assert outline_info["resource_notes"]
    assert outline_info["recommended_models"]
    for entry in outline_info["recommended_models"]:
        tokens = entry.get("context_window_tokens")
        if tokens is not None:
            assert tokens >= outline_info["recommended_context_tokens"]


def test_analyze_config_uses_defaults_file():
    defaults = analyze_defaults()
    cfg = AnalyzeConfig.from_env()

    assert cfg.temperature == defaults["temperature"]
    assert cfg.max_output_tokens == defaults["max_output_tokens"]
    assert cfg.max_prompt_segments == defaults["max_prompt_segments"]
    assert cfg.max_prompt_chars == defaults["max_prompt_chars"]
    assert cfg.provider_chain == [value.lower() for value in defaults["default_provider_chain"]]



def test_stage_temperature_and_max_tokens_override(monkeypatch: MonkeyPatch, tmp_path):
    case_dir = tmp_path / "cases" / "CASE-OVR"
    transcript = case_dir / "transcript" / "JOB-OVR__transcript.txt"
    _write_transcript(transcript, "[00:00] Speaker: Hello world")

    _install_llm_settings_stub(monkeypatch)
    _install_stage_stubs(monkeypatch)

    recorded_temperatures: list[float] = []
    recorded_max_tokens: list[int] = []

    def capture_summary(**kwargs: Any) -> SummaryStageResult:
        recorded_temperatures.append(kwargs.get("temperature"))
        recorded_max_tokens.append(kwargs.get("max_tokens"))
        return SummaryStageResult(
            data={"executive_summary": {"bullets": ["Summary"]}},
            markdown="# Summary\n\n## Executive summary\n- Summary\n",
            usage={"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10},
            prompts=(),
        )

    monkeypatch.setattr(
        "packages.core.agents.analyze.utils.generate_summary_payload",
        capture_summary,
    )

    agent = AnalyzeAgent(_make_config())
    agent.analyze(
        case_id="CASE-OVR",
        case_dir=case_dir,
        job_id="JOB-OVR",
        input=transcript,
        provider_credentials={"azure": FAKE_AZURE_SECRET},
        provider_chain=["azure"],
        stage_map={
            "analyze.draft_markdown": {
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

    class FailingClient:
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

    llm_stub = FailingClient()
    context_snippet = "\n".join(seg.text for seg in large_segments)
    result = outline_generate(
        parse=parse,
        intake={},
        context_snippet=context_snippet,
        case_brief={},
        llm_client=llm_stub,
        temperature=0.0,
        max_tokens=8000,
    )

    assert result.outline["issues"]
    assert any(count > 12 for count in llm_stub.calls)
    assert any(count <= 12 for count in llm_stub.calls)


def test_outline_identity_is_deterministic() -> None:
    segments = [
        TranscriptSegment(ts=0.0, speaker="SPK_1", text="Applicant describes the dispute and desired remedy."),
        TranscriptSegment(ts=45.0, speaker="SPK_2", text="Respondent outlines deadlines and prior orders."),
    ]
    parse = TranscriptParse(
        header_lines=[],
        segments=segments,
        body_text="\n".join(seg.text for seg in segments),
        diarized=True,
    )
    intake = {"client_name": "Alex Applicant", "opposing_party": "Morgan Respondent", "client_position": "Applicant"}

    payload = {
        "parties": {
            "client": {"name": "Alex Applicant", "role": "Applicant"},
            "opposing": {"name": "Morgan Respondent", "role": "Respondent"},
            "counsel": [{"name": "Jordan Counsel", "for": "Alex Applicant"}],
        },
        "issues": [
            {
                "id": "ISSUE-PRIMARY",
                "title": "Primary dispute",
                "description": "Summary of the main dispute.",
                "stance_client": "Seeks relief",
                "stance_opposing": "Opposes relief",
                "status": "RAISED",
            }
        ],
        "claims_and_remedies": [
            {
                "claim": "Damages",
                "remedy_requested": "Monetary compensation",
                "amounts": ["5000"],
                "jurisdictional_notes": None,
            }
        ],
        "facts": [
            {
                "ts": 12.5,
                "speaker": "SPK_1",
                "text": "Key fact described in transcript.",
                "tags": ["transcript"],
            }
        ],
        "deadlines": [{"label": "Filing deadline", "date": "2025-05-01", "ts": None, "basis": "Court order"}],
        "orders_and_directions": [{"date": "2024-11-15", "ts": None, "text": "Disclosure order"}],
        "exhibits": [{"id": "EX-1", "description": "Contract", "cited_ts": [12.5]}],
        "legal_refs": [{"citation": "Civil Code s.10", "context": "Damages provision"}],
    }

    class StaticClient:
        def chat(self, *, messages, temperature, max_tokens, response_format):  # type: ignore[no-untyped-def]
            return json.dumps(payload), {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75}

    def _generate() -> OutlineStageResult:
        return outline_generate(
            parse=parse,
            intake=intake,
            context_snippet="\n".join(seg.text for seg in segments),
            case_brief={},
            llm_client=StaticClient(),
            temperature=0.0,
            max_tokens=2000,
        )

    first = _generate()
    second = _generate()

    first_issue = first.outline["issues"][0]
    second_issue = second.outline["issues"][0]
    assert first_issue["uuid"] == second_issue["uuid"]
    assert first_issue["uuid"]

    first_fact = first.outline["facts"][0]
    second_fact = second.outline["facts"][0]
    assert first_fact["uuid"] == second_fact["uuid"]

    parties1 = first.outline["parties"]
    parties2 = second.outline["parties"]
    assert parties1["client"]["uuid"] == parties2["client"]["uuid"]
    assert parties1["counsel"][0]["uuid"] == parties2["counsel"][0]["uuid"]

    for section in ("claims_and_remedies", "deadlines", "orders_and_directions", "exhibits", "legal_refs"):
        assert first.outline[section][0]["uuid"]
        assert first.outline[section][0]["uuid"] == second.outline[section][0]["uuid"]


def test_build_context_respects_config_limits(tmp_path):
    transcript = tmp_path / "demo.txt"
    _write_transcript(
        transcript,
        "Heading\n-----------------\n"
        + "\n".join(f"[00:{i:02d}] SPK_{i % 2}: line {i}" for i in range(1, 25))
    )
    parse = parse_transcript(transcript)
    cfg = AnalyzeConfig(
        max_prompt_segments=5,
        prompt_segments_override=5,
        max_prompt_chars=80,
        prompt_chars_override=80,
    )

    stage_runtimes: Dict[str, StageRuntime] = {}
    for stage_key in LLM_STAGE_KEYS.values():
        profile = ANALYZE_STAGE_PROFILES[stage_key]
        stage_runtimes[stage_key] = StageRuntime(
            stage_key=stage_key,
            providers=["azure"],
            provider="azure",
            model="gpt-5-mini",
            client=None,
            max_output_tokens=profile.min_context_tokens,
            context_window_tokens=200000,
            profile=profile,
            temperature=cfg.temperature,
        )

    def resolve_transcript(input_path, case_dir):
        return transcript

    pipeline = AnalyzePipeline(
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
    outline_chunks = state["context_chunks"]["analyze.extract_outline"]
    first_chunk = outline_chunks[0]
    lines = first_chunk.splitlines()

    assert len(lines) <= cfg.prompt_segments_override
    total_chars = sum(len(line) for line in lines)
    max_line = max((len(line) for line in lines), default=0)
    assert total_chars <= cfg.prompt_chars_override + max_line


def test_analyze_agent_raises_on_stage_failure(monkeypatch: MonkeyPatch, tmp_path):
    _install_llm_settings_stub(monkeypatch)
    _install_stage_stubs(monkeypatch)

    def boom(**_: Any) -> OutlineStageResult:
        raise RuntimeError("outline failure")

    monkeypatch.setattr(
        "packages.core.agents.analyze.utils.generate_outline",
        boom,
    )

    case_dir = tmp_path / "cases" / "CASE-4"
    transcript_dir = case_dir / "transcript"
    transcript_path = transcript_dir / "JOB-4__transcript.txt"
    _write_transcript(
        transcript_path,
        """Header\n---------------------------\n[00:01] SPK_1: Test line\n""",
    )

    agent = AnalyzeAgent(_make_config())

    with pytest.raises(RuntimeError):
        agent.analyze(
            case_id="CASE-4",
            case_dir=case_dir,
            job_id="JOB-4",
            provider_credentials={"azure": FAKE_AZURE_SECRET},
        )



def test_stage_requires_explicit_model_configuration(monkeypatch: MonkeyPatch, tmp_path):
    azure_provider = LLMProvider(
        name="azure",
        display_name="Azure",
        models={
            "gpt-4o": LLMProviderModel(
                name="gpt-4o",
                label="GPT-4o",
                cost_tier="standard",
                default_enabled=True,
                max_output_tokens=4000,
                context_window_tokens=16000,
                default_temperature=0.2,
            )
        },
    )
    settings = _make_llm_settings(["azure"], {"azure": azure_provider})
    monkeypatch.setattr(analyze_lib, "_llm_settings_cache", settings, raising=False)
    monkeypatch.setattr(analyze_lib, "_load_llm_settings", lambda: settings)

    _install_stage_stubs(monkeypatch)

    case_dir = tmp_path / "cases" / "CASE-FALLBACK"
    transcript = case_dir / "transcript" / "JOB-FB__transcript.txt"
    _write_transcript(transcript, "[00:00] Speaker: Hello\n[00:01] Speaker: Again")

    agent = AnalyzeAgent(_make_config())
    with pytest.raises(RuntimeError) as excinfo:
        agent.analyze(
            case_id="CASE-FALLBACK",
            case_dir=case_dir,
            job_id="JOB-FB",
            provider_credentials={"azure": FAKE_AZURE_SECRET},
        )

    assert "No model configured" in str(excinfo.value)


def test_stage_provider_initialization_error(monkeypatch: MonkeyPatch, tmp_path):
    azure_provider = LLMProvider(
        name="azure",
        display_name="Azure",
        models={
            "gpt-4o": LLMProviderModel(
                name="gpt-4o",
                label="GPT-4o",
                cost_tier="standard",
                default_enabled=True,
                max_output_tokens=4000,
                context_window_tokens=16000,
            )
        },
    )
    settings = _make_llm_settings(["azure"], {"azure": azure_provider})
    monkeypatch.setattr(analyze_lib, "_llm_settings_cache", settings, raising=False)
    monkeypatch.setattr(analyze_lib, "_load_llm_settings", lambda: settings)

    def fake_build_provider_runtime_config(
        *,
        provider: LLMProvider,
        model_name: str,
        credential_payload: Dict[str, Any] | None,
        options: Dict[str, Any] | None,
    ) -> ProviderRuntimeConfig:
        raise ChatClientError("Invalid credentials")

    monkeypatch.setattr(
        analyze_lib,
        "build_provider_runtime_config",
        fake_build_provider_runtime_config,
    )

    _install_stage_stubs(monkeypatch)

    case_dir = tmp_path / "cases" / "CASE-FAILOVER"
    transcript = case_dir / "transcript" / "JOB-FO__transcript.txt"
    _write_transcript(transcript, "[00:00] Speaker: Hello\n[00:01] Speaker: Again")

    agent = AnalyzeAgent(AnalyzeConfig(provider_chain=["azure"]))
    with pytest.raises(RuntimeError) as excinfo:
        agent.analyze(
            case_id="CASE-FAILOVER",
            case_dir=case_dir,
            job_id="JOB-FO",
            provider_credentials={"azure": FAKE_AZURE_SECRET},
            stage_map={
                "analyze.extract_outline": {
                    "provider": "azure",
                    "model": "gpt-4o",
                }
            },
        )

    assert "Unable to configure provider" in str(excinfo.value)


def test_prompt_limits_respect_config_defaults(tmp_path):
    stage_profile = ANALYZE_STAGE_PROFILES["analyze.draft_markdown"]
    runtime = StageRuntime(
        stage_key="analyze.draft_markdown",
        providers=["azure"],
        provider="azure",
        model="gpt-4o",
        client=None,
        max_output_tokens=2048,
        context_window_tokens=16000,
        profile=stage_profile,
        temperature=0.1,
        options={},
    )

    segments = [
        TranscriptSegment(ts=float(idx), speaker=f"SPK_{idx}", text=f"Short line {idx}")
        for idx in range(5)
    ]
    parse = TranscriptParse(header_lines=[], segments=segments, body_text="", diarized=True)

    # Segment limit scenario
    config_segments = AnalyzeConfig(
        provider_chain=["azure"],
        max_prompt_segments=2,
        max_prompt_chars=500,
    )
    pipeline_segments = AnalyzePipeline(
        case_id="CASE-LIMIT",
        job_id="JOB-LIMIT",
        case_dir=tmp_path,
        intake={},
        transcript_hint=None,
        config=config_segments,
        resolve_transcript=lambda input_path, case_dir: Path(input_path) if input_path else Path(),
        build_context=lambda parse, intake: "",
        provider_chain=["azure"],
        stage_runtimes={"analyze.draft_markdown": runtime},
        default_temperature=0.0,
        logger=None,
    )
    state_segments: Dict[str, Any] = {"parse": parse}
    state_segments = pipeline_segments.context_builder(state_segments)
    chunk_lines = state_segments["context_chunks"]["analyze.draft_markdown"]
    total_lines = sum(len(chunk.splitlines()) for chunk in chunk_lines)
    assert total_lines == config_segments.max_prompt_segments

    # Character limit scenario
    config_chars = AnalyzeConfig(
        provider_chain=["azure"],
        max_prompt_segments=0,
        max_prompt_chars=20,
    )
    pipeline_chars = AnalyzePipeline(
        case_id="CASE-LIMIT",
        job_id="JOB-LIMIT",
        case_dir=tmp_path,
        intake={},
        transcript_hint=None,
        config=config_chars,
        resolve_transcript=lambda input_path, case_dir: Path(input_path) if input_path else Path(),
        build_context=lambda parse, intake: "",
        provider_chain=["azure"],
        stage_runtimes={"analyze.draft_markdown": runtime},
        default_temperature=0.0,
        logger=None,
    )
    state_chars: Dict[str, Any] = {"parse": parse}
    state_chars = pipeline_chars.context_builder(state_chars)
    char_chunks = state_chars["context_chunks"]["analyze.draft_markdown"]
    assert len(char_chunks) > 1
    char_limit = pipeline_chars._char_limit_for_stage("analyze.draft_markdown")
    assert char_limit == config_chars.max_prompt_chars
    assert len(char_chunks) == len(segments)
    assert all(len(chunk.splitlines()) == 1 for chunk in char_chunks)


def test_stage_map_wildcard_defaults():
    stage_map = {
        "*": {"provider": "azure", "model": "gpt-4o"},
        "draft_markdown": {"provider": "azure", "model": "gpt-4o-mini"},
        "analyze.qa_and_finalize": {"provider": "azure", "model": "gpt-4o"},
    }
    normalized = _normalize_stage_map(stage_map)
    assert normalized["analyze.extract_outline"]["provider"] == "azure"
    assert normalized["extract_outline"]["provider"] == "azure"
    assert normalized["analyze.draft_markdown"]["model"] == "gpt-4o-mini"
    assert normalized["qa_and_finalize"]["provider"] == "azure"

    prefixed = {
        "analyze.*": {"provider": "azure", "model": "gpt-4o"},
        "compose.context": {"provider": "azure", "model": "gpt-4o-c"},
    }
    normalized_prefixed = _normalize_stage_map(prefixed)
    assert normalized_prefixed["analyze.build_timeline_seeds"]["model"] == "gpt-4o"
    assert normalized_prefixed["compose.context"]["model"] == "gpt-4o-c"


def test_stage_override_mapping_accepts_stage_keys():
    override = StageOverrideConfig(providers=("azure",), model="gpt-override")
    mapping = normalize_stage_override_mapping({StageKey.AN_SUMMARY_DRAFT: override})
    assert mapping["analyze.draft_markdown"] is override


def test_summary_stage_uses_json_mode():
    class DummyJSONClient:
        def __init__(self) -> None:
            self.response_format = None

        def chat(self, *, messages, temperature, max_tokens, response_format=None):
            self.response_format = response_format
            sample = {
                "case_metadata_summary": {
                    "overview": "Case overview",
                    "parties": ["Client", "Opposing"],
                    "jurisdiction": "Ontario",
                    "key_dates": ["2024-01-01"],
                },
                "executive_summary": {"bullets": ["Point"]},
                "detailed_narrative": [],
                "claims_and_remedies": [],
                "procedural_posture": {"status": "Active", "deadlines": [], "orders": []},
                "risks_gaps_questions": [],
                "next_step_checklist": [],
                "supporting_quotes": [],
            }
            return json.dumps(sample), {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

    client = DummyJSONClient()
    parse = TranscriptParse(header_lines=[], segments=[], body_text="", diarized=False)
    result = generate_summary_payload(
        parse=parse,
        outline={},
        timeline=[],
        entities={},
        intake={},
        context_snippet="",
        case_brief={},
        llm_client=client,
        temperature=0.1,
        max_tokens=512,
    )

    assert client.response_format == {"type": "json_object"}
    assert result.data["case_metadata_summary"]["overview"] == "Case overview"
    assert result.usage["total_tokens"] == 2


def test_build_analyze_graph_requires_langgraph(monkeypatch: pytest.MonkeyPatch):
    class Dummy:
        def input_discovery(self, state):
            return state

        parse_transcript = (
            context_builder
        ) = (
            extract_outline
        ) = (
            build_timeline_seeds
        ) = (
            build_entity_hints
        ) = (
            draft_markdown
        ) = (
            qa_and_finalize
        ) = qa_join = write_ops_and_artifacts = input_discovery

    dummy = Dummy()
    monkeypatch.setattr(langgraph_orchestrator, "STATE_GRAPH_FACTORY", None)
    monkeypatch.setattr(langgraph_orchestrator, "LANGGRAPH_END", None)
    with pytest.raises(RuntimeError):
        build_analyze_graph(dummy)
