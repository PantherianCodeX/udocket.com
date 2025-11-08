from dataclasses import dataclass
from pathlib import Path

JSONValue = object

class LLMConfigError(RuntimeError): ...

@dataclass(frozen=True)
class LLMProviderModel:
    name: str
    label: str
    cost_tier: str
    max_output_tokens: int | None = None
    context_window_tokens: int | None = None
    max_input_tokens: int | None = None
    max_chunk_chars: int | None = None
    chunk_overlap_tokens: int | None = None
    max_prompt_chars: int | None = None
    max_prompt_segments: int | None = None
    default_temperature: float | None = None
    deployment_env: str | None = None
    origin: str | None = None
    default_enabled: bool = True
    options: dict[str, JSONValue] = ...

@dataclass(frozen=True)
class LLMProvider:
    name: str
    display_name: str
    models: dict[str, LLMProviderModel]
    env_requirements: list[str] = ...
    api_kind: str = "openai"
    default_endpoint: str = ""
    requires_api_key: bool = True
    description: str = ""
    category: str = "creator"
    hosted_creators: list[str] = ...

    def is_available(self) -> bool: ...

@dataclass(frozen=True)
class LLMStageAssignment:
    stage_key: str
    providers: list[str]
    model: str
    options: dict[str, str] = ...
    target: str = ""
    label: str = ""
    description: str = ""

@dataclass(frozen=True)
class LLMSettings:
    providers: dict[str, LLMProvider]
    assignments: dict[str, LLMStageAssignment]

    def provider(self, name: str) -> LLMProvider | None: ...

    def stage(self, stage_key: str) -> LLMStageAssignment | None: ...

    def all_stage_keys(self) -> list[str]: ...

    def stage_targets(self) -> dict[str, list[str]]: ...

    def stage_keys_for_target(self, target: str) -> list[str]: ...

def load_llm_settings(
    providers_path: Path | None = None,
    assignments_path: Path | None = None,
) -> LLMSettings: ...

def validate_llm_settings(settings: LLMSettings) -> None: ...
