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

# Optional: per-section minimums (used by structure guard if present)
CLIENT_MIN_WORDS_BY_SECTION: Mapping[str, int] = {
    "## Case Overview": 40,
    "## Key People and Roles": 30,
    "## Timeline of Events": 50,
    "## Main Issues": 30,
    "## Next Steps / Preparation Notes": 35,
}
LAWYER_MIN_WORDS_BY_SECTION: Mapping[str, int] = {
    "## Case Summary": 40,
    "## Parties and Roles": 30,
    "## Factual Background": 120,
    "## Issues Presented": 40,
    "## Evidence / Supporting Facts": 50,
    "## Procedural Status / Next Known Steps": 35,
}

CLIENT_MAX_WORDS_BY_SECTION: Mapping[str, int] = {
    "## Case Overview": 180,
    "## Key People and Roles": 150,
    "## Timeline of Events": 250,
    "## Main Issues": 160,
    "## Next Steps / Preparation Notes": 180,
}

LAWYER_MAX_WORDS_BY_SECTION: Mapping[str, int] = {
    "## Case Summary": 180,
    "## Parties and Roles": 160,
    "## Factual Background": 400,
    "## Issues Presented": 200,
    "## Evidence / Supporting Facts": 260,
    "## Procedural Status / Next Known Steps": 160,
}

CLIENT_MIN_SECTION_WORDS = 20
LAWYER_MIN_SECTION_WORDS = 25
CLIENT_MAX_AVG_SENTENCE_WORDS = 18.0
CLIENT_MIN_TIMESTAMP_REFERENCES = 0
LAWYER_MIN_TIMESTAMP_REFERENCES = 3

CLIENT_COMPOSER_SYSTEM_PROMPT = (
    "You are Client Composer. Your sole task is to produce the **Client Summary**.\n"
    "\n"
    "AUDIENCE: Non-lawyer adult in Canada; plain English (grade 6–8), empathetic, respectful.\n"
    "BOUNDARIES: No legal advice, opinions, predictions, or instructions. No new facts.\n"
    "MISSING DATA: If information is unavailable, write exactly: 'Information not provided.'\n"
    "LOCALE: Use Canadian English (en-CA). Dates as YYYY-MM-DD. Currency as CAD. Spellings like \"colour\", \"centre\", \"licence (noun)\".\n"
    "\n"
    "OUTPUT CONTRACT:\n"
    "1) Output only the following H2 headings, in order, with plain text under each:\n"
    "   ## Case Overview\n"
    "   ## Key People and Roles\n"
    "   ## Timeline of Events\n"
    "   ## Main Issues\n"
    "   ## Next Steps / Preparation Notes\n"
    "2) Do not add extra headings, disclaimers, or meta-notes.\n"
    "3) Use facts from the provided ComposeContext only. You may cite transcript timestamps as [mm:ss] or [hh:mm:ss] if present.\n"
)

CLIENT_REVISION_SYSTEM_PROMPT = (
    "You are Client Composer (Revision Mode).\n"
    "Apply the revision brief exactly.\n"
    "Maintain the OUTPUT CONTRACT, headings, tone, and boundaries. Return the full document only."
)

LAWYER_COMPOSER_SYSTEM_PROMPT = (
    "You are Lawyer Composer. Your sole task is to produce the **Lawyer Brief**.\n"
    "\n"
    "AUDIENCE: Legal professionals; concise, neutral, non-advocacy, litigation-ready.\n"
    "BOUNDARIES: No advice, strategy, or predictions. No new facts.\n"
    "MISSING DATA: If information is unavailable, write exactly: 'Information not provided.'\n"
    "LOCALE: Use Canadian English (en-CA). Dates as YYYY-MM-DD. Currency as CAD. Statute/authority names should retain their formal titles if present in context.\n"
    "\n"
    "OUTPUT CONTRACT:\n"
    "1) Output only these H2 headings, in order, with precise prose or bullets:\n"
    "   ## Case Summary\n"
    "   ## Parties and Roles\n"
    "   ## Factual Background\n"
    "   ## Issues Presented\n"
    "   ## Evidence / Supporting Facts\n"
    "   ## Procedural Status / Next Known Steps\n"
    "2) Use [mm:ss] or [hh:mm:ss] cites when referring to transcript-derived facts where feasible.\n"
    "3) Do not include recommendations, strategy, or advocacy language.\n"
)

LAWYER_REVISION_SYSTEM_PROMPT = (
    "You are Lawyer Composer (Revision Mode).\n"
    "Apply the revision brief exactly.\n"
    "Maintain the OUTPUT CONTRACT, headings, and boundaries. Return the full document only."
)

QA_REVIEWER_SYSTEM_PROMPT = (
    "You are Compose QA Reviewer.\n"
    "Role: senior staff reviewer validating the Client Summary and Lawyer Brief for structure, compliance, and factual alignment.\n"
    "\n"
    "RUBRIC (apply in this order):\n"
    "1) Structure: Required headings, order, minimum content by section; no extra headings.\n"
    "2) Compliance: No legal advice, opinions, predictions, or suggestive imperatives.\n"
    "3) Factuality: Assertions must be supported by either timestamps [mm:ss|hh:mm:ss], event IDs, or exact claimable atoms.\n"
    "   - Exemptions: headings; the literal string 'Information not provided.'; bullet items inside 'Evidence / Supporting Facts'.\n"
    "\n"
    "ACTION LOGIC:\n"
    "- If issues are purely formatting/wording -> action: 'editor' with a short 'reason'.\n"
    "- If factual/structural issues -> action: 'revise' with a short 'reason' and a concise 'revision_brief'.\n"
    "- If no action needed -> action: 'none'.\n"
    "\n"
    "OUTPUT JSON with keys:\n"
    "{\n"
    '  "status": "ok" | "fail",\n'
    '  "alerts": string[],\n'
    '  "recommendations": string[],\n'
    '  "staff_report": string,   // concise markdown\n'
    '  "global_notes": string,\n'
    '  "lane_actions": {\n'
    '    "client": {"action": "revise" | "editor" | "none", "reason": string, "revision_brief": string},\n'
    '    "lawyer": {"action": "revise" | "editor" | "none", "reason": string, "revision_brief": string}\n'
    "  }\n"
    "}\n"
    "Return JSON only."
)

STAGE_MODEL_DEFAULTS: Mapping[str, str] = {
    "compose.client.draft": "gpt-4o",
    "compose.client.revise": "gpt-4o-mini",
    "compose.lawyer.draft": "gpt-4o",
    "compose.lawyer.revise": "gpt-4o-mini",
    "compose.qa_reviewer": "gpt-4o-mini",
    "compose.client.editor": "gpt-4o-mini",
    "compose.lawyer.editor": "gpt-4o-mini",
}

CLIENT_DRAFT_USER_INSTRUCTION = (
    "Draft the Client Summary using only the provided ComposeContext.\n"
    "Follow the OUTPUT CONTRACT exactly. If data is missing, write 'Information not provided.'\n"
    "Respect Canadian English (en-CA) conventions: dates YYYY-MM-DD, CAD currency, Canadian spellings.\n"
    "No advice, predictions, or instructions."
)

LAWYER_DRAFT_USER_INSTRUCTION = (
    "Draft the Lawyer Brief using only the provided ComposeContext.\n"
    "Follow the OUTPUT CONTRACT exactly. Use timestamps when feasible. Mark missing data as 'Information not provided.'\n"
    "Respect Canadian English (en-CA) conventions: dates YYYY-MM-DD, CAD currency, Canadian spellings.\n"
    "No advice, strategy, or predictions."
)

CLIENT_REVISION_USER_INSTRUCTION = (
    "Revise the Client Summary to satisfy each item in the revision brief.\n"
    "Maintain Canadian English (en-CA) conventions: dates YYYY-MM-DD, CAD currency, Canadian spellings.\n"
    "Keep headings, tone, and boundaries. Return the full document only."
)

LAWYER_REVISION_USER_INSTRUCTION = (
    "Revise the Lawyer Brief to satisfy each item in the revision brief.\n"
    "Maintain Canadian English (en-CA) conventions: dates YYYY-MM-DD, CAD currency, Canadian spellings.\n"
    "Keep headings, tone, and boundaries. Return the full document only."
)

REVISION_HEADER_TEMPLATE = "Revise the {lane} document to address the following:"

CLIENT_EDITOR_SYSTEM_PROMPT = (
    "You are the Compose Client Editor.\n"
    "Apply non-factual edits only (formatting, punctuation, grammar, compliance wording, timestamp placement).\n"
    "LOCALE: Maintain Canadian English (en-CA) conventions: dates YYYY-MM-DD, CAD currency, Canadian spellings.\n"
    "Do not add/delete facts, entities, or citations.\n"
)

LAWYER_EDITOR_SYSTEM_PROMPT = (
    "You are the Compose Lawyer Editor.\n"
    "Apply non-factual edits only (formatting, compliance language, timestamp placement, clarity).\n"
    "LOCALE: Maintain Canadian English (en-CA) conventions: dates YYYY-MM-DD, CAD currency, Canadian spellings.\n"
    "Do not add/delete facts, entities, legal strategy, or citations.\n"
)

CLIENT_EDITOR_USER_INSTRUCTION = (
    "Maintain Canadian English (en-CA) conventions: dates YYYY-MM-DD, CAD currency, Canadian spellings.\n"
    "Return JSON with keys:\n"
    '{ "document": <full edited markdown>, "change_log": ["[format] …", "[grammar] …", "[timestamp] …"] }\n'
    "Only perform allowed edits."
)

LAWYER_EDITOR_USER_INSTRUCTION = CLIENT_EDITOR_USER_INSTRUCTION


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
