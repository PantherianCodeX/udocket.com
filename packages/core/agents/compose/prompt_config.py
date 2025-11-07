from __future__ import annotations

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, cast

# pyright: strict
import yaml
from pydantic import BaseModel, Field, ValidationError

from packages.common.prompts import DEFAULT_LOCALE, render_prompt


class LanePrompts(BaseModel):
    system_prompt: str = Field(..., description="System prompt for initial draft generation")
    revision_system_prompt: str = Field(..., description="System prompt when applying revisions")
    draft_instruction: str = Field(..., description="User instruction for draft generation")
    revision_instruction: str = Field(..., description="User instruction when revising drafts")
    editor_system_prompt: str = Field(..., description="System prompt for editor passes")
    editor_instruction: str = Field(..., description="Instruction payload for editor passes")


class QALanePrompts(BaseModel):
    system_prompt: str = Field(..., description="System prompt for the lane QA reviewer model")


class QAReviewPrompts(BaseModel):
    client: QALanePrompts
    lawyer: QALanePrompts
    final_system_prompt: str | None = Field(
        default=None,
        description="Optional system prompt for a final joiner summary",
    )


class ComposePromptConfig(BaseModel):
    revision_header_template: str = Field(..., description="Template applied to revision briefs")
    client: LanePrompts
    lawyer: LanePrompts
    qa: QAReviewPrompts


def load_prompt_config(
    path: Path | None,
    *,
    locale: str = DEFAULT_LOCALE,
) -> ComposePromptConfig:
    if path is None:
        return load_prompt_config_from_resources(locale=locale)
    if not path.exists():
        raise FileNotFoundError(f"Compose prompt config not found at {path}")
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Failed to read prompt config from {path}: {exc}") from exc
    if not isinstance(loaded, MutableMapping):
        raise RuntimeError(f"Invalid prompt configuration at {path}: expected mapping root")
    raw_data = cast(MutableMapping[str, Any], loaded)
    data: dict[str, Any] = {str(key): value for key, value in raw_data.items()}
    qa_section = data.get("qa")
    if isinstance(qa_section, MutableMapping):
        qa_mapping = cast(MutableMapping[str, Any], qa_section)
        qa_map: dict[str, Any] = {str(key): value for key, value in qa_mapping.items()}
        if "client" not in qa_map and "lawyer" not in qa_map:
            system_prompt = qa_map.get("system_prompt")
            if isinstance(system_prompt, str) and system_prompt.strip():
                qa_map = {
                    "client": {"system_prompt": system_prompt},
                    "lawyer": {"system_prompt": system_prompt},
                }
        data["qa"] = qa_map
    elif isinstance(qa_section, str):
        data["qa"] = {
            "client": {"system_prompt": qa_section},
            "lawyer": {"system_prompt": qa_section},
        }
    try:
        return ComposePromptConfig.model_validate(data)
    except ValidationError as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Invalid prompt configuration at {path}: {exc}") from exc


def load_prompt_config_from_resources(locale: str = DEFAULT_LOCALE) -> ComposePromptConfig:
    def _render(key: str) -> str:
        return render_prompt("compose", key, locale=locale)

    client = LanePrompts(
        system_prompt=_render("client_system"),
        revision_system_prompt=_render("client_revision_system"),
        draft_instruction=_render("client_draft_instruction"),
        revision_instruction=_render("client_revision_instruction"),
        editor_system_prompt=_render("client_editor_system"),
        editor_instruction=_render("client_editor_instruction"),
    )
    lawyer = LanePrompts(
        system_prompt=_render("lawyer_system"),
        revision_system_prompt=_render("lawyer_revision_system"),
        draft_instruction=_render("lawyer_draft_instruction"),
        revision_instruction=_render("lawyer_revision_instruction"),
        editor_system_prompt=_render("lawyer_editor_system"),
        editor_instruction=_render("lawyer_editor_instruction"),
    )
    qa = QAReviewPrompts(
        client=QALanePrompts(system_prompt=_render("qa_client_system")),
        lawyer=QALanePrompts(system_prompt=_render("qa_lawyer_system")),
    )
    return ComposePromptConfig(
        revision_header_template=_render("revision_header"),
        client=client,
        lawyer=lawyer,
        qa=qa,
    )


__all__ = [
    "ComposePromptConfig",
    "LanePrompts",
    "QAReviewPrompts",
    "QALanePrompts",
    "load_prompt_config",
    "load_prompt_config_from_resources",
]
