from __future__ import annotations

# pyright: strict

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple


DEFAULT_TEMPERATURE = 0.6
DEFAULT_LAWYER_TEMPERATURE = 0.4
DEFAULT_MAX_OUTPUT_TOKENS = 120000

CLIENT_HEADINGS: Tuple[str, ...] = (
    "## Case Overview",
    "## Key People and Roles",
    "## Timeline of Events",
    "## Main Issues",
    "## Next Steps / Preparation Notes",
)

LAWYER_HEADINGS: Tuple[str, ...] = (
    "## Case Summary",
    "## Parties and Roles",
    "## Factual Background",
    "## Issues Presented",
    "## Evidence / Supporting Facts",
    "## Procedural Status / Next Known Steps",
)

# Optional: per-section minimums (used by structure guard if present)
CLIENT_MIN_WORDS_BY_SECTION: Mapping[str, int] = {
    "## Case Overview": 400,
    "## Key People and Roles": 300,
    "## Timeline of Events": 500,
    "## Main Issues": 300,
    "## Next Steps / Preparation Notes": 350,
}
LAWYER_MIN_WORDS_BY_SECTION: Mapping[str, int] = {
    "## Case Summary": 400,
    "## Parties and Roles": 300,
    "## Factual Background": 1200,
    "## Issues Presented": 400,
    "## Evidence / Supporting Facts": 500,
    "## Procedural Status / Next Known Steps": 350,
}

CLIENT_MAX_WORDS_BY_SECTION: Mapping[str, int] = {
    "## Case Overview": 1800,
    "## Key People and Roles": 1500,
    "## Timeline of Events": 2500,
    "## Main Issues": 1600,
    "## Next Steps / Preparation Notes": 1800,
}

LAWYER_MAX_WORDS_BY_SECTION: Mapping[str, int] = {
    "## Case Summary": 1800,
    "## Parties and Roles": 1600,
    "## Factual Background": 4000,
    "## Issues Presented": 2000,
    "## Evidence / Supporting Facts": 2600,
    "## Procedural Status / Next Known Steps": 1600,
}

CLIENT_MIN_SECTION_WORDS = 200
LAWYER_MIN_SECTION_WORDS = 250
CLIENT_MAX_AVG_SENTENCE_WORDS = 180.0 #18.0
CLIENT_MIN_TIMESTAMP_REFERENCES = 0
LAWYER_MIN_TIMESTAMP_REFERENCES = 2

STAGE_MODEL_DEFAULTS: Mapping[str, str] = {
    "compose.client.draft": "gpt-5-mini",
    "compose.client.revise": "gpt-5-mini",
    "compose.lawyer.draft": "gpt-5-mini",
    "compose.lawyer.revise": "gpt-5-mini",
    "compose.qa_reviewer": "gpt-5-mini",
    "compose.client.editor": "gpt-5-mini",
    "compose.lawyer.editor": "gpt-5-mini",
}

@dataclass(frozen=True)
class LaneConfig:
    lane: str
    headings: Tuple[str, ...]
    min_words: int
    readability_limit: Optional[float]
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
