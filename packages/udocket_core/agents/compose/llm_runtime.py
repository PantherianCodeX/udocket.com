from __future__ import annotations

# pyright: strict

from typing import Any, Mapping, Tuple, cast

from packages.udocket_core.json_utils import JSONObject
from packages.udocket_core.llm import LLMSettings
from packages.udocket_core.llm.runtime import ChatClientError, build_chat_client, build_provider_runtime_config
from .errors import ComposeStageError
from .settings import ComposeConfig, DEFAULT_PROVIDER_CHAIN, normalize_provider_chain
from .llm_profiles import STAGE_MODEL_DEFAULTS


def invoke_llm(
    *,
    stage: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    provider_credentials: Mapping[str, JSONObject],
    config: ComposeConfig,
    settings: LLMSettings,
) -> Tuple[str, dict[str, int], str, str]:
    providers = normalize_provider_chain(config.provider_chain)
    assignment = settings.stage(stage)
    provider_name = ""
    if assignment and assignment.providers:
        provider_name = assignment.providers[0]
    if not provider_name and providers:
        provider_name = providers[0]
    if not provider_name:
        provider_name = DEFAULT_PROVIDER_CHAIN[0]

    provider_meta = settings.provider(provider_name)
    if provider_meta is None:
        raise ComposeStageError(stage, f"Unknown provider '{provider_name}'", provider=provider_name)

    provider_info = cast(Any, provider_meta)
    default_model = cast(str, getattr(provider_info, "default_model", ""))
    model_override = STAGE_MODEL_DEFAULTS.get(stage, "")
    if stage == "compose.client.editor" and config.client_editor_model:
        model_override = config.client_editor_model
    elif stage == "compose.lawyer.editor" and config.lawyer_editor_model:
        model_override = config.lawyer_editor_model
    elif assignment and assignment.model and not model_override:
        model_override = assignment.model
    model_name = model_override or default_model
    if not model_name:
        raise ComposeStageError(stage, f"No model configured for provider '{provider_name}'", provider=provider_name)

    credentials = provider_credentials.get(provider_name)
    try:
        runtime = build_provider_runtime_config(
            provider=provider_meta,
            model_name=model_name,
            credential_payload=credentials,
            options=None,
        )
    except ChatClientError as exc:
        raise ComposeStageError(stage, str(exc), provider=provider_name, model=model_name) from exc

    try:
        client = build_chat_client(provider_runtime=runtime)
    except ChatClientError as exc:
        raise ComposeStageError(stage, str(exc), provider=provider_name, model=model_name) from exc

    try:
        content, usage = client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=config.max_output_tokens,
            response_format=None,
        )
    except ChatClientError as exc:
        raise ComposeStageError(stage, str(exc), provider=provider_name, model=model_name) from exc

    usage_map = {key: value for key, value in usage.items() if isinstance(value, int)}
    return content, usage_map, provider_name, model_name


__all__ = ["invoke_llm"]
