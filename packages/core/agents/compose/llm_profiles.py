from __future__ import annotations

from collections.abc import Mapping

# pyright: strict
from dataclasses import dataclass

DEFAULT_TEMPERATURE = 0.6
DEFAULT_LAWYER_TEMPERATURE = 0.4
DEFAULT_MAX_OUTPUT_TOKENS = 120000

CLIENT_HEADINGS: tuple[str, ...] = (
    "## Case Overview",
    "## Key People and Roles",
    "## Timeline of Events",
    "## Main Issues",
    "## Next Steps / Preparation Notes",
)

LAWYER_HEADINGS: tuple[str, ...] = (
    "## Case Summary",
    "## Parties and Roles",
    "## Factual Background",
    "## Issues Presented",
    "## Evidence / Supporting Facts",
    "## Procedural Status / Next Known Steps",
)

# Optional: per-section minimums (used by structure guard if present)
CLIENT_MIN_WORDS_BY_SECTION: Mapping[str, int] = {
    "## Case Overview": 4,
    "## Key People and Roles": 3,
    "## Timeline of Events": 5,
    "## Main Issues": 3,
    "## Next Steps / Preparation Notes": 4,  # 35
}
LAWYER_MIN_WORDS_BY_SECTION: Mapping[str, int] = {
    "## Case Summary": 4,
    "## Parties and Roles": 3,
    "## Factual Background": 12,
    "## Issues Presented": 4,
    "## Evidence / Supporting Facts": 5,
    "## Procedural Status / Next Known Steps": 4,  # 35
}

CLIENT_MAX_WORDS_BY_SECTION: Mapping[str, int] = {
    "## Case Overview": 18000,
    "## Key People and Roles": 15000,
    "## Timeline of Events": 25000,
    "## Main Issues": 16000,
    "## Next Steps / Preparation Notes": 18000,
}

LAWYER_MAX_WORDS_BY_SECTION: Mapping[str, int] = {
    "## Case Summary": 18000,
    "## Parties and Roles": 16000,
    "## Factual Background": 40000,
    "## Issues Presented": 20000,
    "## Evidence / Supporting Facts": 26000,
    "## Procedural Status / Next Known Steps": 16000,
}

CLIENT_MIN_SECTION_WORDS = 20
LAWYER_MIN_SECTION_WORDS = 25
CLIENT_MAX_AVG_SENTENCE_WORDS = 1800.0  # 18.0
CLIENT_MIN_TIMESTAMP_REFERENCES = 0
LAWYER_MIN_TIMESTAMP_REFERENCES = 0

STAGE_MODEL_DEFAULTS: Mapping[str, str] = {
    "compose.client.draft": "gpt-5-mini",
    "compose.client.revise": "gpt-5-mini",
    "compose.client.qa_reviewer": "gpt-5-mini",
    "compose.client.editor": "gpt-5-mini",
    "compose.lawyer.draft": "gpt-5-mini",
    "compose.lawyer.revise": "gpt-5-mini",
    "compose.lawyer.qa_reviewer": "gpt-5-mini",
    "compose.lawyer.editor": "gpt-5-mini",
}


@dataclass(frozen=True)
class LaneConfig:
    lane: str
    headings: tuple[str, ...]
    min_words: int
    readability_limit: float | None
    min_timestamp_references: int
    temperature: float
    revision_temperature: float


LANE_CONFIGS: Mapping[str, LaneConfig] = {
    "client": LaneConfig(
        lane="client",
        headings=CLIENT_HEADINGS,
        min_words=CLIENT_MIN_SECTION_WORDS,
        readability_limit=CLIENT_MAX_AVG_SENTENCE_WORDS,
        min_timestamp_references=CLIENT_MIN_TIMESTAMP_REFERENCES,
        temperature=DEFAULT_TEMPERATURE,
        revision_temperature=max(DEFAULT_TEMPERATURE - 0.15, 0.0),
    ),
    "lawyer": LaneConfig(
        lane="lawyer",
        headings=LAWYER_HEADINGS,
        min_words=LAWYER_MIN_SECTION_WORDS,
        readability_limit=None,
        min_timestamp_references=LAWYER_MIN_TIMESTAMP_REFERENCES,
        temperature=DEFAULT_LAWYER_TEMPERATURE,
        revision_temperature=max(DEFAULT_LAWYER_TEMPERATURE - 0.1, 0.0),
    ),
}
