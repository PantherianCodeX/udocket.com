from __future__ import annotations

# pyright: strict

import json
import logging
import os
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence, cast, runtime_checkable

from ..agents.common.azure_client import (
    AzureChatClient,
    AzureClientConfig,
)
from ..agents.common.http_client import HTTPRetryConfig
from ..utils.json import (
    JSONObject,
    JSONValue,
    coerce_bool,
    coerce_float,
    coerce_int,
    coerce_json_object,
    coerce_json_value,
    coerce_str,
    coerce_str_dict,
    merge_json_objects,
)
from ..llm.config import LLMProvider, LLMProviderModel

logger = logging.getLogger("udocket.llm.runtime")


ChatMessage = Mapping[str, JSONValue]
TokenUsage = dict[str, int | None]
ResponseFormat = JSONObject


class _ResponseProtocol(Protocol):
    status_code: int
    text: str
    headers: Mapping[str, str]

    def json(self) -> JSONValue: ...

    def raise_for_status(self) -> None: ...


class _RequestsProtocol(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json: JSONValue | None = None,
        params: Mapping[str, JSONValue] | None = None,
        timeout: int | None = None,
    ) -> _ResponseProtocol: ...


_requests_module: _RequestsProtocol | None
try:  # pragma: no cover - optional dependency guard
    import requests as _imported_requests
except Exception:  # pragma: no cover
    _requests_module = None
else:
    _requests_module = cast(_RequestsProtocol, _imported_requests)

requests: _RequestsProtocol | None = _requests_module


class ChatClient(Protocol):
    """Protocol for chat-capable LLM clients."""

    def chat(
        self,
        *,
        messages: Sequence[ChatMessage],
        temperature: float = 1.0,
        max_tokens: int | None = None,
        response_format: ResponseFormat | None = None,
    ) -> tuple[str, TokenUsage]: ...


@runtime_checkable
class SupportsHealthCheck(Protocol):
    def health_check(self, *, force: bool = False) -> None: ...


class ChatClientError(RuntimeError):
    """Raised when an LLM invocation cannot be completed."""


def _require_requests() -> _RequestsProtocol:
    if requests is None:  # pragma: no cover - dependency missing
        raise RuntimeError("requests library is required for HTTP LLM providers")
    return requests


def _coerce_base_url(value: str | None) -> str:
    if not value:
        return ""
    url = value.strip()
    if not url:
        return ""
    return url.rstrip("/")


class OpenAIChatClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout: int = 120,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        _require_requests()
        self.base_url = _coerce_base_url(base_url) or "https://api.openai.com/v1"
        if not self.base_url.endswith("/v1"):
            if "/v1" not in self.base_url.split("?", 1)[0]:
                self.base_url = f"{self.base_url}/v1"
        self.api_key = api_key or ""
        self.model = model
        self.timeout = timeout
        self.extra_headers = dict(extra_headers or {})

    def chat(
        self,
        *,
        messages: Sequence[ChatMessage],
        temperature: float = 1.0,
        max_tokens: int | None = None,
        response_format: ResponseFormat | None = None,
    ) -> tuple[str, TokenUsage]:
        if not messages:
            raise ChatClientError("OpenAI chat requires at least one message")
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)
        payload: JSONObject = {
            "model": self.model,
            "messages": [coerce_json_object(message) for message in messages],
            "temperature": float(temperature),
        }
        if max_tokens is not None and max_tokens > 0:
            payload["max_tokens"] = int(max_tokens)
        if response_format:
            payload["response_format"] = coerce_json_object(response_format)
        requests_impl = _require_requests()
        try:
            response = requests_impl.post(url, headers=headers, json=payload, timeout=self.timeout)
        except Exception as exc:  # pragma: no cover - network failure
            raise ChatClientError(f"OpenAI request failed: {exc}") from exc
        if response.status_code >= 400:
            text = response.text
            raise ChatClientError(
                f"OpenAI request failed with status {response.status_code}: {text[:512]}"
            )
        data_raw = response.json()
        if not isinstance(data_raw, Mapping):
            raise ChatClientError("OpenAI response payload is not a JSON object")
        data_obj = coerce_json_object(data_raw)
        choices_raw = data_obj.get("choices")
        if not isinstance(choices_raw, list):
            raise ChatClientError("OpenAI response missing choices")
        choices_list = [
            coerce_json_object(choice)
            for choice in choices_raw
            if isinstance(choice, Mapping)
        ]
        if not choices_list:
            raise ChatClientError("OpenAI response missing structured choices")
        first = choices_list[0]
        message_value = first.get("message")
        if not isinstance(message_value, Mapping):
            raise ChatClientError("OpenAI response missing message content")
        message_dict = coerce_json_object(message_value)
        content_raw = message_dict.get("content")
        if isinstance(content_raw, str):
            content = content_raw
        elif content_raw is None:
            content = ""
        elif isinstance(content_raw, Sequence) and not isinstance(content_raw, (str, bytes, bytearray)):
            parts = [
                coerce_str(part.get("text"))
                for part in (
                    coerce_json_object(item)
                    for item in content_raw
                    if isinstance(item, Mapping)
                )
            ]
            content = "".join(part or "" for part in parts).strip()
        else:
            content = json.dumps(coerce_json_value(content_raw), ensure_ascii=False)
        usage_raw = data_obj.get("usage")
        usage: TokenUsage = {}
        if isinstance(usage_raw, Mapping):
            usage_obj = coerce_json_object(usage_raw)
            prompt_tokens = usage_obj.get("prompt_tokens") or usage_obj.get("input_tokens")
            completion_tokens = (
                usage_obj.get("completion_tokens") or usage_obj.get("output_tokens")
            )
            total_tokens = usage_obj.get("total_tokens")
            usage = {
                "prompt_tokens": int(prompt_tokens) if isinstance(prompt_tokens, int) else None,
                "completion_tokens": int(completion_tokens)
                if isinstance(completion_tokens, int)
                else None,
                "total_tokens": int(total_tokens) if isinstance(total_tokens, int) else None,
            }
        return content, usage


class AnthropicChatClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 120,
        api_version: str = "2023-06-01",
    ) -> None:
        _require_requests()
        if not api_key:
            raise ChatClientError("Anthropic API key is required")
        self.base_url = _coerce_base_url(base_url) or "https://api.anthropic.com/v1"
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.api_version = api_version

    def chat(
        self,
        *,
        messages: Sequence[ChatMessage],
        temperature: float = 1.0,
        max_tokens: int | None = None,
        response_format: ResponseFormat | None = None,
    ) -> tuple[str, TokenUsage]:
        if not messages:
            raise ChatClientError("Anthropic requires at least one message")
        max_tokens = max(1, int(max_tokens or 1024))
        converted: list[JSONObject] = []
        for message in messages:
            message_obj = coerce_json_object(message)
            role_value = coerce_str(message_obj.get("role")) or "user"
            content_value = message_obj.get("content")
            parts: list[JSONValue] = []
            if isinstance(content_value, str):
                parts.append({"type": "text", "text": content_value})
            elif isinstance(content_value, Sequence) and not isinstance(
                content_value, (str, bytes, bytearray)
            ):
                for entry in content_value:
                    if isinstance(entry, Mapping):
                        parts.append(coerce_json_object(entry))
            elif content_value is not None:
                parts.append(
                    {
                        "type": "text",
                        "text": json.dumps(coerce_json_value(content_value), ensure_ascii=False),
                    }
                )
            if not parts:
                parts.append({"type": "text", "text": ""})
            converted.append({"role": role_value, "content": parts})
        url = f"{self.base_url}/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
        }
        payload: JSONObject = {
            "model": self.model,
            "messages": cast(list[JSONValue], converted),
            "temperature": float(temperature),
            "max_tokens": max_tokens,
        }
        if response_format and response_format.get("type") == "json_object":
            payload["response_format"] = {"type": "json_object"}
        requests_impl = _require_requests()
        try:
            response = requests_impl.post(url, headers=headers, json=payload, timeout=self.timeout)
        except Exception as exc:  # pragma: no cover - network failure
            raise ChatClientError(f"Anthropic request failed: {exc}") from exc
        if response.status_code >= 400:
            text = response.text
            raise ChatClientError(
                f"Anthropic request failed with status {response.status_code}: {text[:512]}"
            )
        data_raw = response.json()
        if not isinstance(data_raw, Mapping):
            raise ChatClientError("Anthropic response payload is not a JSON object")
        data_obj = coerce_json_object(data_raw)
        content_blocks = data_obj.get("content")
        text_fragments: list[str] = []
        if isinstance(content_blocks, Sequence) and not isinstance(content_blocks, (str, bytes, bytearray)):
            for block in content_blocks:
                if isinstance(block, Mapping):
                    block_obj = coerce_json_object(block)
                    text_value = block_obj.get("text")
                    if isinstance(text_value, str):
                        text_fragments.append(text_value)
        content = "".join(text_fragments).strip()
        usage_raw = data_obj.get("usage")
        usage: TokenUsage = {}
        if isinstance(usage_raw, Mapping):
            usage_obj = coerce_json_object(usage_raw)
            prompt_tokens = usage_obj.get("input_tokens")
            completion_tokens = usage_obj.get("output_tokens")
            total_tokens = usage_obj.get("total_tokens")
            usage = {
                "prompt_tokens": int(prompt_tokens) if isinstance(prompt_tokens, int) else None,
                "completion_tokens": int(completion_tokens)
                if isinstance(completion_tokens, int)
                else None,
                "total_tokens": int(total_tokens) if isinstance(total_tokens, int) else None,
            }
        return content, usage


@dataclass(frozen=True)
class ProviderRuntimeConfig:
    provider: LLMProvider
    model: LLMProviderModel | None
    endpoint: str
    api_key: str
    options: JSONObject
    metadata: JSONObject


def _string_option(options: Mapping[str, JSONValue], key: str) -> str | None:
    value = options.get(key)
    text = coerce_str(value)
    return text.strip() if text else None


def _resolve_endpoint(
    provider: LLMProvider,
    credential_payload: JSONObject | None,
    options: JSONObject,
) -> str:
    option_endpoint = _string_option(options, "endpoint")
    if option_endpoint:
        return option_endpoint
    if credential_payload:
        cred_endpoint = _string_option(credential_payload, "endpoint")
        if cred_endpoint:
            return cred_endpoint
    if provider.default_endpoint:
        return provider.default_endpoint
    return ""


def _resolve_api_key(
    provider: LLMProvider,
    credential_payload: JSONObject | None,
    options: JSONObject,
) -> str:
    option_key = _string_option(options, "api_key")
    if option_key:
        return option_key
    if credential_payload:
        cred_key = _string_option(credential_payload, "api_key")
        if cred_key:
            return cred_key
    return ""


def _resolve_metadata(credential_payload: JSONObject | None) -> JSONObject:
    if not credential_payload:
        return {}
    metadata_value = credential_payload.get("metadata")
    return coerce_json_object(metadata_value)


def _first_matching_model(models_payload: object, model_name: str) -> JSONObject | None:
    if not models_payload or not model_name:
        return None
    target = model_name.strip().lower()
    if not target:
        return None
    candidates: list[JSONObject] = []
    if isinstance(models_payload, Mapping):
        mapping_payload = cast(Mapping[object, object], models_payload)
        candidates.append(coerce_json_object(mapping_payload))
    elif isinstance(models_payload, Sequence) and not isinstance(models_payload, (str, bytes, bytearray)):
        entries_iter = cast(Sequence[object], models_payload)
        for entry in entries_iter:
            if isinstance(entry, Mapping):
                mapping_entry = cast(Mapping[object, object], entry)
                candidates.append(coerce_json_object(mapping_entry))
    for entry in candidates:
        entry_name = coerce_str(entry.get("name") or entry.get("id"))
        if entry_name and entry_name.strip().lower() == target:
            return entry
    return None


def _apply_default_options(target: JSONObject, defaults: Mapping[str, JSONValue]) -> None:
    for key, value in defaults.items():
        if key in target:
            continue
        json_value = coerce_json_value(value)
        if json_value is None:
            continue
        target[key] = json_value


class _AzureChatAdapter:
    """Adapter that normalises AzureChatClient to the ChatClient protocol."""

    def __init__(self, client: AzureChatClient) -> None:
        self._client = client

    def chat(
        self,
        *,
        messages: Sequence[ChatMessage],
        temperature: float = 1.0,
        max_tokens: int | None = None,
        response_format: ResponseFormat | None = None,
    ) -> tuple[str, TokenUsage]:
        converted_messages: list[dict[str, str]] = []
        for message in messages:
            message_obj = coerce_json_object(message)
            role = coerce_str(message_obj.get("role")) or "user"
            content_value = message_obj.get("content")
            if isinstance(content_value, str):
                content_text = content_value
            elif content_value is None:
                content_text = ""
            else:
                content_text = json.dumps(coerce_json_value(content_value), ensure_ascii=False)
            converted_messages.append({"role": role, "content": content_text})
        content, usage_payload = self._client.chat(
            messages=converted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        logger.debug(
            "azure.adapter.raw_prefix prefix=%r len=%d", content[:200], len(content)
        )

        usage: TokenUsage = {
            "prompt_tokens": coerce_int(usage_payload.get("prompt_tokens")),
            "completion_tokens": coerce_int(usage_payload.get("completion_tokens")),
            "total_tokens": coerce_int(usage_payload.get("total_tokens")),
        }
        return content, usage

    def health_check(self, *, force: bool = False) -> None:
        self._client.health_check(force=force)


def build_chat_client(
    *,
    provider_runtime: ProviderRuntimeConfig,
) -> ChatClient:
    provider = provider_runtime.provider
    model = provider_runtime.model
    endpoint = _coerce_base_url(provider_runtime.endpoint)
    options = provider_runtime.options
    metadata = provider_runtime.metadata
    api_key = provider_runtime.api_key

    if provider.api_kind == "azure_openai":
        deployment = _string_option(options, "azure_deployment")
        if not deployment and metadata:
            for key in ("azure_deployment", "default_deployment", "deployment"):
                value = _string_option(metadata, key)
                if value:
                    deployment = value
                    break
        if not deployment and model and model.deployment_env:
            env_value = os.getenv(model.deployment_env)
            if env_value and env_value.strip():
                deployment = env_value.strip()
        if not deployment:
            raise ChatClientError(
                "Azure provider requires an `azure_deployment` option or stored metadata",
            )
        allow_non_ca = coerce_bool(options.get("allow_non_ca_region"))
        if allow_non_ca is None and metadata:
            allow_non_ca = coerce_bool(metadata.get("allow_non_ca_region"))
        if allow_non_ca is None:
            allow_non_ca_env = coerce_bool(os.getenv("AZURE_OPENAI_ALLOW_NON_CA_REGION"))
            if allow_non_ca_env is not None:
                allow_non_ca = allow_non_ca_env
                if allow_non_ca_env:
                    logger.warning(
                        "AZURE_OPENAI_ALLOW_NON_CA_REGION enabled; non-Canadian Azure endpoints are allowed."
                    )
        api_version_value = (
            _string_option(options, "api_version")
            or os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
            or "2024-10-21"
        )
        # Timeouts: allow granular overrides for long-running outputs
        timeout_opt = coerce_int(options.get("timeout"))
        connect_timeout_opt = coerce_int(options.get("connect_timeout"))
        read_timeout_opt = coerce_int(options.get("read_timeout"))
        if timeout_opt is None:
            timeout_env = coerce_int(os.getenv("AZURE_OPENAI_TIMEOUT"))
            if timeout_env is not None:
                timeout_opt = timeout_env
        if connect_timeout_opt is None:
            connect_env = coerce_int(os.getenv("AZURE_OPENAI_CONNECT_TIMEOUT"))
            if connect_env is not None:
                connect_timeout_opt = connect_env
        if read_timeout_opt is None:
            read_env = coerce_int(os.getenv("AZURE_OPENAI_READ_TIMEOUT"))
            if read_env is not None:
                read_timeout_opt = read_env

        # Session and retry tuning
        pool_opt = coerce_int(options.get("session_pool_size"))
        if pool_opt is None:
            pool_env = coerce_int(os.getenv("AZURE_OPENAI_SESSION_POOL_SIZE"))
            if pool_env is not None:
                pool_opt = pool_env
        retry_total_opt = coerce_int(options.get("retry_total"))
        if retry_total_opt is None:
            retry_total_env = coerce_int(os.getenv("AZURE_OPENAI_RETRY_TOTAL"))
            if retry_total_env is not None:
                retry_total_opt = retry_total_env
        retry_backoff_opt = coerce_float(options.get("retry_backoff_factor"))
        if retry_backoff_opt is None:
            retry_backoff_env = coerce_float(os.getenv("AZURE_OPENAI_RETRY_BACKOFF_FACTOR"))
            if retry_backoff_env is not None:
                retry_backoff_opt = retry_backoff_env

        retry_cfg = HTTPRetryConfig(
            total=retry_total_opt if retry_total_opt is not None else 3,
            backoff_factor=retry_backoff_opt if retry_backoff_opt is not None else 0.6,
            status_forcelist=(
                408,
                409,
                425,
                429,
                500,
                502,
                503,
                504,
                521,
                522,
                524,
            ),
        )
        cfg = AzureClientConfig(
            endpoint=endpoint,
            key=api_key,
            deployment=deployment,
            api_version=api_version_value,
            allow_non_ca_region=bool(allow_non_ca),
            timeout=timeout_opt if timeout_opt is not None else 120,
            connect_timeout=connect_timeout_opt if connect_timeout_opt is not None else 10,
            read_timeout=read_timeout_opt if read_timeout_opt is not None else 600,
            session_pool_size=pool_opt if pool_opt is not None else 10,
            retry_config=retry_cfg,
        )
        return _AzureChatAdapter(AzureChatClient(cfg))

    if provider.api_kind == "anthropic":
        timeout = coerce_int(options.get("timeout")) or 120
        api_version = _string_option(options, "api_version") or "2023-06-01"
        model_name = model.name if model else _string_option(options, "model") or "claude-3-haiku-20240307"
        return AnthropicChatClient(
            base_url=endpoint or "https://api.anthropic.com/v1",
            api_key=api_key,
            model=model_name,
            timeout=timeout,
            api_version=api_version,
        )

    if provider.api_kind in {
        "openai",
        "ollama",
        "cohere",
        "mistral",
        "deepseek",
        "fireworks",
        "groq",
        "openrouter",
        "perplexity",
        "together",
    }:
        extra_headers = coerce_str_dict(metadata.get("headers"))
        option_headers = coerce_str_dict(options.get("headers"))
        extra_headers.update(option_headers)
        timeout = coerce_int(options.get("timeout")) or 120
        model_name = model.name if model else _string_option(options, "model") or "gpt-4o-mini"
        return OpenAIChatClient(
            base_url=endpoint or provider.default_endpoint or "https://api.openai.com/v1",
            api_key=api_key,
            model=model_name,
            timeout=timeout,
            extra_headers=extra_headers,
        )

    if provider.api_kind == "bedrock":
        raise ChatClientError("AWS Bedrock chat support not yet implemented")

    if provider.api_kind == "google_genai":
        raise ChatClientError("Google Gemini chat support not yet implemented")

    raise ChatClientError(f"Unsupported provider api_kind: {provider.api_kind}")


def build_provider_runtime_config(
    *,
    provider: LLMProvider,
    model_name: str,
    credential_payload: Mapping[str, JSONValue] | None,
    options: Mapping[str, JSONValue] | None = None,
) -> ProviderRuntimeConfig:
    model = provider.models.get(model_name) if model_name in provider.models else None
    user_options = coerce_json_object(options) if options else {}
    if model and model.options:
        _apply_default_options(user_options, model.options)

    credential_payload_obj = coerce_json_object(credential_payload) if credential_payload else None
    credential_model: JSONObject | None = None
    if credential_payload_obj:
        credential_model = _first_matching_model(credential_payload_obj.get("models"), model_name)
        if credential_model:
            credential_options = credential_model.get("options")
            if isinstance(credential_options, Mapping):
                credential_options_mapping = cast(Mapping[object, object], credential_options)
                credential_options_obj = coerce_json_object(credential_options_mapping)
                _apply_default_options(user_options, credential_options_obj)
            deployment_env_value = coerce_str(credential_model.get("deployment_env"))
            if (
                deployment_env_value
                and "azure_deployment" not in user_options
            ):
                user_options["azure_deployment"] = deployment_env_value

    if (
        provider.api_kind == "azure_openai"
        and "azure_deployment" not in user_options
        and model
        and model.deployment_env
    ):
        deployment_env_value = model.deployment_env.strip() if model.deployment_env else ""
        env_value = os.getenv(deployment_env_value) if deployment_env_value else None
        if env_value and env_value.strip():
            user_options["azure_deployment"] = env_value.strip()
        elif deployment_env_value:
            user_options["azure_deployment"] = deployment_env_value

    endpoint = _resolve_endpoint(provider, credential_payload_obj, user_options)
    api_key = _resolve_api_key(provider, credential_payload_obj, user_options)
    metadata = _resolve_metadata(credential_payload_obj)
    if provider.requires_api_key and not api_key:
        raise ChatClientError(f"Provider '{provider.name}' requires an API key")
    merged_options = merge_json_objects(user_options)
    return ProviderRuntimeConfig(
        provider=provider,
        model=model,
        endpoint=endpoint,
        api_key=api_key,
        options=merged_options,
        metadata=metadata,
    )


__all__ = [
    "ChatClient",
    "ChatClientError",
    "SupportsHealthCheck",
    "OpenAIChatClient",
    "AnthropicChatClient",
    "ProviderRuntimeConfig",
    "build_chat_client",
    "build_provider_runtime_config",
]
