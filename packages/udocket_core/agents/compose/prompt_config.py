from __future__ import annotations

# pyright: strict

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


class LanePrompts(BaseModel):
    system_prompt: str = Field(..., description="System prompt for initial draft generation")
    revision_system_prompt: str = Field(..., description="System prompt when applying revisions")
    draft_instruction: str = Field(..., description="User instruction for draft generation")
    revision_instruction: str = Field(..., description="User instruction when revising drafts")
    editor_system_prompt: str = Field(..., description="System prompt for editor passes")
    editor_instruction: str = Field(..., description="Instruction payload for editor passes")


class QAReviewPrompts(BaseModel):
    system_prompt: str = Field(..., description="System prompt for QA reviewer model")


class ComposePromptConfig(BaseModel):
    revision_header_template: str = Field(..., description="Template applied to revision briefs")
    client: LanePrompts
    lawyer: LanePrompts
    qa: QAReviewPrompts


def load_prompt_config(path: Path) -> ComposePromptConfig:
    if not path.exists():
        raise FileNotFoundError(f"Compose prompt config not found at {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Failed to read prompt config from {path}: {exc}") from exc
    try:
        return ComposePromptConfig.model_validate(data)
    except ValidationError as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Invalid prompt configuration at {path}: {exc}") from exc


__all__ = ["ComposePromptConfig", "LanePrompts", "QAReviewPrompts", "load_prompt_config"]
