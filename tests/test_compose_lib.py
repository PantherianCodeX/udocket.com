from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from packages.udocket_core.agents.compose_lib import ComposeAgent, ComposeConfig, ComposeResult
from packages.udocket_core.json_utils import JSONObject
from tests._typing import MonkeyPatch


ClientResponse = Tuple[str, Dict[str, int], str]


def _write_inputs(base_dir: Path) -> tuple[Path, Path, Path]:
    summary_json = base_dir / "summary.json"
    summary_json.write_text(
        json.dumps(
            {
                "parties": [
                    {"name": "Alex", "role": "Applicant"},
                    {"name": "Morgan", "role": "Respondent"},
                ],
                "facts": [
                    {"text": "Hearing held on January 5, 2024."},
                    {"text": "Interim custody order currently in effect."},
                ],
            }
        ),
        encoding="utf-8",
    )

    summary_md = base_dir / "summary.md"
    summary_md.write_text(
        """# Summary

Alex and Morgan appeared before the court on January 5, 2024.
The court issued an interim order.
""",
        encoding="utf-8",
    )

    timeline_json = base_dir / "timeline.json"
    timeline_json.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "id": "event-1",
                        "summary": "Hearing commenced",
                        "ts_start": 1.0,
                        "ts_end": 2.0,
                        "speakers": ["Alex"],
                        "references": ["[00:01]"]
                    },
                    {
                        "id": "event-2",
                        "summary": "Order granted",
                        "ts_start": 120.0,
                        "ts_end": 121.0,
                        "speakers": ["Judge"],
                        "references": ["[02:00]"]
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    return summary_json, summary_md, timeline_json


def test_compose_agent_parallel_lanes(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    case_dir = tmp_path / "case"
    docs_dir = case_dir / "docs"
    ops_dir = case_dir / "ops"
    docs_dir.mkdir(parents=True)
    ops_dir.mkdir(parents=True)

    summary_json, summary_md, timeline_json = _write_inputs(docs_dir)

    config = ComposeConfig(
        provider_chain=["stub"],
        temperature=0.2,
        lawyer_temperature=0.2,
        max_output_tokens=2048,
        max_client_attempts=2,
        max_lawyer_attempts=2,
        min_timestamp_references=1,
        qa_required=True,
        enable_parallel_lanes=True,
        debug=True,
    )
    agent = ComposeAgent(config)

    client_doc = """## Case Overview
The judge reviewed the interim custody order at [00:01] and confirmed it remained active. The hearing record at [02:00] notes the court expects continued compliance while scheduling the next appearance.

## Key People and Roles
Alex, the Applicant, described day-to-day parenting responsibilities documented at [00:01]. Morgan, the Respondent, acknowledged disclosure duties at [02:00] and agreed to provide additional materials before the next date.

## Timeline of Events
At [00:01] the hearing opened with the judge summarising prior orders and confirming attendance. By [02:00] the court restated the interim order and set expectations for preparing the next conference.

## Main Issues
Interim custody arrangements discussed at [00:01] remain the central topic for the parties. Compliance with prior disclosure obligations at [02:00] continues to affect scheduling and preparation work.

## Next Steps / Preparation Notes
Gather additional financial disclosures before the next conference at [02:00], including updated income details and childcare schedules. Follow the existing order until further direction from the court and keep notes of cooperation at [00:01].
"""

    lawyer_doc = """## Case Summary
This matter involves interim custody arrangements reviewed on January 5, 2024 at [00:01]. The transcript at [02:00] confirms the interim order remains active while the parties organise updated disclosure.

## Parties and Roles
Alex (Applicant) presented evidence about parenting schedules at [00:01] and discussed timelines for exchanges. Morgan (Respondent) addressed compliance topics at [02:00] and confirmed availability for upcoming conferences.

## Factual Background
At [00:01] the hearing opened with a review of prior orders. The court confirmed at [02:00] that the interim order remains in effect and that disclosure obligations continue.

## Issues Presented
Whether the interim order should remain in effect based on remarks at [02:00] remains under consideration. Scheduling of disclosure deadlines discussed at [00:01] also needs coordination with counsel and the parties.

## Evidence / Supporting Facts
Transcript segments at [00:01] and [02:00] summarise the oral reasons and confirm the judge’s expectations. Counsel also referenced disclosure undertakings at [02:00] to support the status quo.

## Procedural Status / Next Known Steps
The case conference is scheduled, and the parties must exchange updated financial materials before the next appearance at [02:00]. The court also requested written updates that track commitments made at [00:01] and [02:00].
"""

    def fake_invoke(
        self: ComposeAgent,
        *,
        stage: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        provider_credentials: JSONObject,
    ) -> ClientResponse:
        if stage == "compose.client.draft":
            return client_doc, {"prompt_tokens": 100, "completion_tokens": 200}, "stub"
        if stage == "compose.lawyer.draft":
            return lawyer_doc, {"prompt_tokens": 120, "completion_tokens": 210}, "stub"
        if stage == "compose.qa_reviewer":
            response = json.dumps(
                {
                    "status": "ok",
                    "alerts": [],
                    "recommendations": [],
                    "staff_report": "# Staff Report\n\nAll checks passed.",
                }
            )
            return response, {"prompt_tokens": 80, "completion_tokens": 40}, "stub"
        raise AssertionError(f"Unexpected stage: {stage}")

    monkeypatch.setattr(ComposeAgent, "_invoke_llm", fake_invoke)  # type: ignore[arg-type]

    result: ComposeResult = agent.compose(
        case_id="CASE-001",
        case_dir=case_dir,
        job_id="JOB-001",
        summary_json_path=summary_json,
        summary_markdown_path=summary_md,
        transcript_path=None,
        timeline_seed_path=timeline_json,
        entity_hint_path=None,
    )

    assert result.status == "ok"
    artifacts = result.artifacts
    assert artifacts.bundle_path and artifacts.bundle_path.exists()
    bundle_text = artifacts.bundle_path.read_text(encoding="utf-8")
    assert "Part 1 – Client Summary" in bundle_text
    assert "Part 2 – Lawyer Brief" in bundle_text
    assert artifacts.client_markdown and artifacts.client_markdown.exists()
    assert artifacts.lawyer_markdown and artifacts.lawyer_markdown.exists()
    assert artifacts.staff_report and artifacts.staff_report.exists()
    assert artifacts.qa_report and artifacts.qa_report.exists()
    qa_text = artifacts.qa_report.read_text(encoding="utf-8")
    assert "## Client Lane" in qa_text
    assert result.meta_json.exists()
    meta = json.loads(result.meta_json.read_text(encoding="utf-8"))
    assert meta["client_attempts"] == 1
    assert meta["lawyer_attempts"] == 1
    assert meta["stage_usage"]
    assert meta["staff_report"] and Path(meta["staff_report"]).exists()


def test_compose_agent_revision_cycle(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    case_dir = tmp_path / "case"
    docs_dir = case_dir / "docs"
    ops_dir = case_dir / "ops"
    docs_dir.mkdir(parents=True)
    ops_dir.mkdir(parents=True)

    summary_json, summary_md, timeline_json = _write_inputs(docs_dir)

    config = ComposeConfig(
        provider_chain=["stub"],
        temperature=0.2,
        lawyer_temperature=0.2,
        max_output_tokens=2048,
        max_client_attempts=2,
        max_lawyer_attempts=1,
        min_timestamp_references=1,
        qa_required=True,
        enable_parallel_lanes=False,
        debug=True,
    )
    agent = ComposeAgent(config)

    call_counts: dict[str, int] = {"compose.client.draft": 0, "compose.client.revise": 0}

    bad_client_doc = """## Case Overview
This section omits required references and headings.

## Key People and Roles
- Alex: Applicant

## Main Issues
- Missing sections cause failure.
"""

    good_client_doc = """## Case Overview
The interim order remains active as described at [00:01], and the court reiterated those terms at [02:00] while planning the next steps.

## Key People and Roles
Alex, the Applicant, outlined weekly parenting responsibilities at [00:01] with support plans. Morgan, the Respondent, agreed at [02:00] to deliver additional disclosure and continue cooperation before the next court date.

## Timeline of Events
The hearing noted at [00:01] contextualised prior orders, while [02:00] documented the judge’s expectation that parties maintain the interim regime.

## Main Issues
Interim custody arrangements discussed at [00:01] remain unresolved and require updates. Disclosure compliance tracked at [02:00] directly affects scheduling for the next appearance.

## Next Steps / Preparation Notes
Prepare updated disclosure documents referencing commitments at [02:00] and summarise cooperation highlights from [00:01] so counsel can brief the court efficiently.
"""

    lawyer_doc = """## Case Summary
This matter involves interim custody arrangements reviewed on January 5, 2024 at [00:01]. The transcript at [02:00] confirms the interim order remains active while the parties organise updated disclosure.

## Parties and Roles
Alex (Applicant) presented evidence about parenting schedules at [00:01] and discussed timelines for exchanges. Morgan (Respondent) addressed compliance topics at [02:00] and confirmed availability for upcoming conferences.

## Factual Background
At [00:01] the hearing opened with a review of prior orders. The court confirmed at [02:00] that the interim order remains in effect and that disclosure obligations continue.

## Issues Presented
Whether the interim order should remain in effect based on remarks at [02:00] remains under consideration. Scheduling of disclosure deadlines discussed at [00:01] also needs coordination with counsel and the parties.

## Evidence / Supporting Facts
Transcript segments at [00:01] and [02:00] summarise the oral reasons and confirm the judge’s expectations. Counsel also referenced disclosure undertakings at [02:00] to support the status quo.

## Procedural Status / Next Known Steps
The case conference is scheduled, and the parties must exchange updated financial materials before the next appearance at [02:00]. The court also requested written updates that track commitments made at [00:01] and [02:00].
"""

    def fake_invoke(
        self: ComposeAgent,
        *,
        stage: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        provider_credentials: JSONObject,
    ) -> ClientResponse:
        if stage == "compose.client.draft":
            call_counts[stage] += 1
            return bad_client_doc, {"prompt_tokens": 50, "completion_tokens": 50}, "stub"
        if stage == "compose.client.revise":
            call_counts[stage] += 1
            return good_client_doc, {"prompt_tokens": 60, "completion_tokens": 70}, "stub"
        if stage == "compose.lawyer.draft":
            return lawyer_doc, {"prompt_tokens": 40, "completion_tokens": 60}, "stub"
        if stage == "compose.qa_reviewer":
            response = json.dumps(
                {
                    "status": "ok",
                    "alerts": [],
                    "recommendations": [],
                    "staff_report": "# Staff Report\n\nClient lane fixed.",
                }
            )
            return response, {"prompt_tokens": 30, "completion_tokens": 30}, "stub"
        raise AssertionError(f"Unexpected stage: {stage}")

    monkeypatch.setattr(ComposeAgent, "_invoke_llm", fake_invoke)  # type: ignore[arg-type]

    result = agent.compose(
        case_id="CASE-REV",
        case_dir=case_dir,
        job_id="JOB-REV",
        summary_json_path=summary_json,
        summary_markdown_path=summary_md,
        transcript_path=None,
        timeline_seed_path=timeline_json,
        entity_hint_path=None,
    )

    meta = json.loads(result.meta_json.read_text(encoding="utf-8"))
    assert meta["client_attempts"] == 2
    assert meta["lawyer_attempts"] == 1
    assert call_counts["compose.client.draft"] == 1
    assert call_counts["compose.client.revise"] == 1
    bundle_text = result.artifacts.bundle_path.read_text(encoding="utf-8")
    assert "Next Steps / Preparation Notes" in bundle_text
