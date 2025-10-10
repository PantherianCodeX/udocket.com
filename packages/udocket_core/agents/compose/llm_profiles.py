from __future__ import annotations

# pyright: strict

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple


DEFAULT_TEMPERATURE = 0.6
DEFAULT_LAWYER_TEMPERATURE = 0.4
DEFAULT_MAX_OUTPUT_TOKENS = 12000

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


CLIENT_MIN_SECTION_WORDS = 20
LAWYER_MIN_SECTION_WORDS = 25
CLIENT_MAX_AVG_SENTENCE_WORDS = 18.0
CLIENT_MIN_TIMESTAMP_REFERENCES = 0
LAWYER_MIN_TIMESTAMP_REFERENCES = 3


CLIENT_COMPOSER_SYSTEM_PROMPT = (
    "You are Client Composer. Task: write the Client Summary only.\n"
    "Constraints:\n"
    "- Plain English, grade 6-8, neutral and empathetic.\n"
    "- No legal advice, no opinions, no predictions, no instructions.\n"
    "- No new facts; use only provided ComposeContext.\n"
    "- If data is missing, write 'Information not provided.'\n"
    "Format (exact H2 headings, plain text):\n"
    "## Case Overview\n"
    "## Key People and Roles\n"
    "## Timeline of Events\n"
    "## Main Issues\n"
    "## Next Steps / Preparation Notes\n"
)


CLIENT_REVISION_SYSTEM_PROMPT = (
    "You are Client Composer (Revision Mode).\n"
    "Rewrite the Client Summary to satisfy the revision brief exactly.\n"
    "Preserve required headings, tone, and constraints. Output full document, plain text."
)


LAWYER_COMPOSER_SYSTEM_PROMPT = (
    "You are Lawyer Composer. Task: write the Lawyer Brief only.\n"
    "Constraints:\n"
    "- Neutral, concise, professional; no advocacy, no advice, no predictions.\n"
    "- No new facts; only provided ComposeContext.\n"
    "- If data is missing, write 'Information not provided.'\n"
    "Format (exact H2 headings, plain text):\n"
    "## Case Summary\n"
    "## Parties and Roles\n"
    "## Factual Background\n"
    "## Issues Presented\n"
    "## Evidence / Supporting Facts\n"
    "## Procedural Status / Next Known Steps\n"
)


LAWYER_REVISION_SYSTEM_PROMPT = (
    "You are Lawyer Composer (Revision Mode).\n"
    "Rewrite the Lawyer Brief to satisfy the revision brief exactly.\n"
    "Preserve required headings and constraints. Output full document, plain text."
)


QA_REVIEWER_SYSTEM_PROMPT = (
    "You are Compose QA Reviewer.\n"
    "Role: senior staff reviewer assessing client and lawyer deliverables for compliance, factual accuracy, and clarity.\n"
    "Tasks:\n"
    "1. Summarize critical findings, risks, and follow-ups in staff-report format.\n"
    "2. Produce JSON status for automated gating.\n"
    "Rules:\n"
    "- Use provided context only.\n"
    "- Flag legal advice or speculation.\n"
    "- Ensure timelines and facts align with claimable atoms.\n"
    "Output: respond with JSON containing keys `status`, `alerts`, `recommendations`, `staff_report`."
)


STAGE_MODEL_DEFAULTS: Mapping[str, str] = {
    "compose.client.draft": "gpt-4o",
    "compose.client.revise": "gpt-4o-mini",
    "compose.lawyer.draft": "gpt-4o",
    "compose.lawyer.revise": "gpt-4o-mini",
    "compose.qa_reviewer": "gpt-4o-mini",
}


CLIENT_DRAFT_USER_INSTRUCTION = (
    "Draft the full client summary using the provided ComposeContext.\n"
    "- Keep language plain, empathetic, and grade 6-8.\n"
    "- Preserve every required heading in order.\n"
    "- Use only facts from the context; cite transcript timestamps with [mm:ss] when available.\n"
    "- If information is missing, write 'Information not provided.'\n"
    "- Do not offer advice, predictions, or instructions."
)

LAWYER_DRAFT_USER_INSTRUCTION = (
    "Draft the full lawyer brief using the provided ComposeContext.\n"
    "- Maintain a professional, neutral tone focused on litigation readiness.\n"
    "- Preserve every required heading in order.\n"
    "- Use [mm:ss] timestamp cites for transcript evidence and reference relevant entities.\n"
    "- Include only verifiable facts; do not speculate or recommend strategy.\n"
    "- Mark gaps explicitly with 'Information not provided.' when data is absent."
)

CLIENT_REVISION_USER_INSTRUCTION = (
    "Revise the client summary to satisfy every item in the revision brief.\n"
    "- Maintain the required headings, tone, grade level, and compliance rules.\n"
    "- Apply precise fixes without introducing new facts or removing required references.\n"
    "- Return the full updated document only."
)

LAWYER_REVISION_USER_INSTRUCTION = (
    "Revise the lawyer brief to satisfy every item in the revision brief.\n"
    "- Maintain the required headings, neutral professional tone, and compliance rules.\n"
    "- Address each requested change directly without inventing facts or legal advice.\n"
    "- Return the full updated document only."
)

REVISION_HEADER_TEMPLATE = "Revise the {lane} document to address the following:"


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


def lane_system_prompt(lane: str, *, revision: bool) -> str:
    if lane == "client":
        return CLIENT_REVISION_SYSTEM_PROMPT if revision else CLIENT_COMPOSER_SYSTEM_PROMPT
    if lane == "lawyer":
        return LAWYER_REVISION_SYSTEM_PROMPT if revision else LAWYER_COMPOSER_SYSTEM_PROMPT
    raise ValueError(f"Unknown lane '{lane}'")
