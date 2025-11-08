from __future__ import annotations

# pyright: strict
import logging
import random
import time
from collections.abc import Mapping
from typing import Any, cast

from packages.common.json_utils import JSONObject

from ...llm import LLMSettings
from ...llm.runtime import ChatClientError, build_chat_client, build_provider_runtime_config
from .errors import ComposeStageError
from .llm_profiles import STAGE_MODEL_DEFAULTS
from .settings import DEFAULT_PROVIDER_CHAIN, ComposeConfig, normalize_provider_chain

logger = logging.getLogger("udocket.compose.llm_runtime")

_NON_RETRYABLE_TOKENS: tuple[str, ...] = (
    "status 400",
    "status code: 400",
    '"status_code":400',
    "status 401",
    "status code: 401",
    '"status_code":401',
    "status 403",
    "status code: 403",
    '"status_code":403',
    "status 404",
    "status code: 404",
    '"status_code":404',
    "invalid api key",
    "unknown provider",
    "no model configured",
    "unsupported provider",
    "requires an api key",
    "temperature only the default",
)


def invoke_llm(
    *,
    stage: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    provider_credentials: Mapping[str, JSONObject],
    config: ComposeConfig,
    settings: LLMSettings,
) -> tuple[str, dict[str, int], str, str]:
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
        raise ComposeStageError(
            stage, f"Unknown provider '{provider_name}'", provider=provider_name
        )

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
        raise ComposeStageError(
            stage, f"No model configured for provider '{provider_name}'", provider=provider_name
        )

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
        attempts = max(1, 1 + max(0, config.llm_retry_attempts))
        delay_seconds = max(0.5, config.llm_retry_initial_delay_seconds)
    except AttributeError:
        # Backwards compatibility if config lacks retry fields
        attempts = 1
        delay_seconds = 1.0

    payload_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            content, usage = client.chat(
                messages=payload_messages,
                temperature=temperature,
                max_tokens=config.max_output_tokens,
                response_format=None,
            )
            logger.debug(
                "compose.llm.raw_prefix stage=%s provider=%s model=%s prefix=%r len=%d",
                stage,
                provider_name,
                model_name,
                content[:200],
                len(content),
            )

            usage_map = {key: value for key, value in usage.items() if isinstance(value, int)}
            if attempt > 1:
                logger.info(
                    "compose.llm.retry_recovered",
                    extra={
                        "compose": {
                            "stage": stage,
                            "attempt": attempt,
                            "provider": provider_name,
                            "model": model_name,
                        }
                    },
                )
            return content, usage_map, provider_name, model_name
        except ChatClientError as exc:
            last_error = exc
            if not _should_retry(exc) or attempt >= attempts:
                raise ComposeStageError(
                    stage, str(exc), provider=provider_name, model=model_name
                ) from exc
        except RuntimeError as exc:
            last_error = exc
            if not _should_retry(exc) or attempt >= attempts:
                raise ComposeStageError(
                    stage, str(exc), provider=provider_name, model=model_name
                ) from exc

        jitter = random.uniform(0.0, min(0.5, delay_seconds * 0.25))
        sleep_time = delay_seconds + jitter
        logger.warning(
            "compose.llm.retry_scheduled",
            extra={
                "compose": {
                    "stage": stage,
                    "attempt": attempt,
                    "max_attempts": attempts,
                    "provider": provider_name,
                    "model": model_name,
                    "delay_seconds": round(sleep_time, 2),
                    "error": str(last_error),
                }
            },
        )
        time.sleep(sleep_time)
        delay_seconds = min(delay_seconds * 2.0, 60.0)

    assert last_error is not None
    raise ComposeStageError(
        stage,
        f"LLM invocation failed after {attempts} attempts: {last_error}",
        provider=provider_name,
        model=model_name,
    ) from last_error


def _should_retry(exc: Exception) -> bool:
    message = str(exc).lower()
    for token in _NON_RETRYABLE_TOKENS:
        if token in message:
            return False
    return True


__all__ = ["invoke_llm"]
