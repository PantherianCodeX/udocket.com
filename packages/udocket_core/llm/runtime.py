"""Runtime helpers for constructing LLM chat clients."""
# pyright: reportMissingModuleSource=false

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Tuple, cast


class _ResponseProtocol(Protocol):
    status_code: int
    text: str
    headers: Mapping[str, str]

    def json(self) -> Any: ...

    def raise_for_status(self) -> None: ...


class _RequestsProtocol(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        json: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> _ResponseProtocol: ...


try:  # pragma: no cover - optional dependency guard
    import requests as _requests  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    _requests = None

requests: Optional[_RequestsProtocol]
if _requests is not None:
    requests = cast(_RequestsProtocol, _requests)
else:
    requests = None

from packages.udocket_core.agents.common.azure_client import (
    AzureChatClient,
    AzureClientConfig,
)
from packages.udocket_core.llm.config import LLMProvider, LLMProviderModel


logger = logging.getLogger("udocket.llm.runtime")


class ChatClient(Protocol):
    """Protocol for chat-capable LLM clients."""

    def chat(
        self,
        *,
        messages: List[Dict[str, Any]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]: ...


class ChatClientError(RuntimeError):
    """Raised when an LLM invocation cannot be completed."""


def _require_requests() -> _RequestsProtocol:
    if requests is None:  # pragma: no cover - dependency missing
        raise RuntimeError("requests library is required for HTTP LLM providers")
    return requests


def _coerce_base_url(value: Optional[str]) -> str:
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
        api_key: Optional[str],
        model: str,
        timeout: int = 120,
        extra_headers: Optional[Dict[str, str]] = None,
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
        messages: List[Dict[str, Any]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": float(temperature),
        }
        if max_tokens is not None and max_tokens > 0:
            payload["max_tokens"] = int(max_tokens)
        if response_format:
            payload["response_format"] = response_format
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
        try:
            data_raw = response.json()
        except ValueError as exc:
            raise ChatClientError("OpenAI response was not valid JSON") from exc
        if not isinstance(data_raw, dict):
            raise ChatClientError("OpenAI response payload is not a JSON object")
        data_obj = cast(Dict[str, Any], data_raw)
        choices_raw = data_obj.get("choices")
        if not isinstance(choices_raw, list):
            raise ChatClientError("OpenAI response missing choices")
        choices_iter = cast(List[Any], choices_raw)
        choices_list: List[Dict[str, Any]] = []
        for entry in choices_iter:
            if isinstance(entry, dict):
                choices_list.append(cast(Dict[str, Any], entry))
        if not choices_list:
            raise ChatClientError("OpenAI response missing structured choices")
        first: Dict[str, Any] = choices_list[0]
        message_value = first.get("message")
        if not isinstance(message_value, dict):
            raise ChatClientError("OpenAI response missing message content")
        message_dict: Dict[str, Any] = message_value
        content_raw: object = message_dict.get("content")
        if isinstance(content_raw, str):
            content = content_raw
        else:
            content = str(content_raw or "")
        usage_raw: object = data_obj.get("usage")
        usage: Dict[str, Any] = {}
        if isinstance(usage_raw, dict):
            usage_dict: Dict[str, Any] = usage_raw
            usage = {
                "prompt_tokens": usage_dict.get("prompt_tokens")
                or usage_dict.get("input_tokens"),
                "completion_tokens": usage_dict.get("completion_tokens")
                or usage_dict.get("output_tokens"),
                "total_tokens": usage_dict.get("total_tokens"),
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
        messages: List[Dict[str, Any]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        if not messages:
            raise ChatClientError("Anthropic requires at least one message")
        max_tokens = max(1, int(max_tokens or 1024))
        converted: List[Dict[str, Any]] = []
        for message in messages:
            role_value = message.get("role") or "user"
            role = str(role_value)
            content = message.get("content")
            parts: List[Dict[str, Any]]
            if isinstance(content, str):
                parts = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                parts = []
                content_items = cast(List[Any], content)
                for entry in content_items:
                    if isinstance(entry, dict):
                        parts.append(cast(Dict[str, Any], entry))
            else:
                parts = [{"type": "text", "text": json.dumps(content)}]
            converted.append({"role": role, "content": parts})
        url = f"{self.base_url}/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": converted,
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
        try:
            data_raw = response.json()
        except ValueError as exc:
            raise ChatClientError("Anthropic response was not valid JSON") from exc
        if not isinstance(data_raw, dict):
            raise ChatClientError("Anthropic response payload is not a JSON object")
        data_obj = cast(Dict[str, Any], data_raw)
        content_blocks = data_obj.get("content")
        text_fragments: List[str] = []
        if isinstance(content_blocks, list):
            content_block_items = cast(List[Any], content_blocks)
            for block in content_block_items:
                if isinstance(block, dict):
                    block_dict = cast(Dict[str, Any], block)
                    text_value: object = block_dict.get("text")
                    if isinstance(text_value, str):
                        text_fragments.append(text_value)
        content = "".join(text_fragments).strip()
        usage_raw = data_obj.get("usage")
        usage: Dict[str, Any] = {}
        if isinstance(usage_raw, dict):
            usage_dict = cast(Dict[str, Any], usage_raw)
            usage = {
                "prompt_tokens": usage_dict.get("input_tokens"),
                "completion_tokens": usage_dict.get("output_tokens"),
                "total_tokens": usage_dict.get("total_tokens"),
            }
        return content, usage


@dataclass
class ProviderRuntimeConfig:
    provider: LLMProvider
    model: LLMProviderModel | None
    endpoint: str
    api_key: str
    options: Dict[str, Any]
    metadata: Dict[str, Any]


def _resolve_endpoint(
    provider: LLMProvider,
    credential_payload: Optional[Dict[str, Any]],
    options: Dict[str, Any],
) -> str:
    endpoint_option = options.get("endpoint")
    if isinstance(endpoint_option, str) and endpoint_option.strip():
        return endpoint_option.strip()
    if credential_payload:
        endpoint = credential_payload.get("endpoint")
        if isinstance(endpoint, str) and endpoint.strip():
            return endpoint.strip()
    if provider.default_endpoint:
        return provider.default_endpoint
    return ""


def _resolve_api_key(
    provider: LLMProvider,
    credential_payload: Optional[Dict[str, Any]],
    options: Dict[str, Any],
) -> str:
    option_key = options.get("api_key")
    if isinstance(option_key, str) and option_key.strip():
        return option_key.strip()
    if credential_payload:
        key = credential_payload.get("api_key")
        if isinstance(key, str) and key.strip():
            return key.strip()
    return ""


def _resolve_metadata(credential_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    metadata = credential_payload.get("metadata") if credential_payload else None
    return dict(metadata or {})


def _first_matching_model(
    models_payload: Optional[Iterable[Any]],
    model_name: str,
) -> Optional[Dict[str, Any]]:
    if not models_payload or not model_name:
        return None
    target_name = model_name.strip().lower()
    if not target_name:
        return None
    for entry in models_payload:
        if not isinstance(entry, Mapping):
            continue
        entry_name_raw = entry.get("name") or entry.get("id")
        if not isinstance(entry_name_raw, str):
            continue
        entry_name = entry_name_raw.strip().lower()
        if not entry_name:
            continue
        if entry_name == target_name:
            return {str(key): value for key, value in entry.items()}
    return None


def _merge_default_options(base: Dict[str, Any], defaults: Optional[Mapping[str, Any]]) -> None:
    if not defaults:
        return
    for key, value in defaults.items():
        if key in base:
            continue
        if value is None:
            continue
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                continue
            base[key] = candidate
        else:
            base[key] = value


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
        deployment = options.get("azure_deployment")
        if not deployment and metadata:
            for key in ("azure_deployment", "default_deployment", "deployment"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    deployment = value.strip()
                    break
        if not deployment and model and model.deployment_env:
            deployment = os.getenv(model.deployment_env)
        if not deployment:
            raise ChatClientError(
                "Azure provider requires an `azure_deployment` option or stored metadata",
            )
        allow_non_ca = bool(
            options.get("allow_non_ca_region")
            or metadata.get("allow_non_ca_region")
        )
        cfg = AzureClientConfig(
            endpoint=endpoint,
            key=api_key,
            deployment=deployment,
            api_version=str(options.get("api_version") or os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")),
            allow_non_ca_region=allow_non_ca,
        )
        return AzureChatClient(cfg)

    if provider.api_kind == "anthropic":
        return AnthropicChatClient(
            base_url=endpoint or "https://api.anthropic.com/v1",
            api_key=api_key,
            model=model.name if model else provider_runtime.options.get("model") or "claude-3-haiku-20240307",
            timeout=int(options.get("timeout") or 120),
            api_version=str(options.get("api_version") or "2023-06-01"),
        )

    if provider.api_kind in {"openai", "ollama", "cohere", "mistral", "deepseek", "fireworks", "groq", "openrouter", "perplexity", "together"}:
        extra_headers: Dict[str, str] = {}
        if metadata:
            headers_meta = metadata.get("headers")
            if isinstance(headers_meta, Mapping):
                headers_mapping = cast(Mapping[str, Any], headers_meta)
                for key, value in headers_mapping.items():
                    if key:
                        extra_headers[key] = str(value)
        option_headers = options.get("headers")
        if isinstance(option_headers, Mapping):
            option_mapping = cast(Mapping[str, Any], option_headers)
            for key, value in option_mapping.items():
                if key:
                    extra_headers[key] = str(value)
        timeout = int(options.get("timeout") or 120)
        return OpenAIChatClient(
            base_url=endpoint or provider.default_endpoint or "https://api.openai.com/v1",
            api_key=api_key,
            model=model.name if model else provider_runtime.options.get("model") or "gpt-4o-mini",
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
    credential_payload: Optional[Dict[str, Any]],
    options: Optional[Dict[str, Any]] = None,
) -> ProviderRuntimeConfig:
    model = provider.models.get(model_name) if model_name in provider.models else None
    options = dict(options or {})
    if model and model.options:
        _merge_default_options(options, model.options)

    models_payload = credential_payload.get("models") if credential_payload else None
    credential_model = _first_matching_model(models_payload, model_name)
    if credential_model:
        credential_options = credential_model.get("options")
        if isinstance(credential_options, Mapping):
            _merge_default_options(options, credential_options)
        deployment_env = credential_model.get("deployment_env")
        if (
            "azure_deployment" not in options
            and isinstance(deployment_env, str)
            and deployment_env.strip()
        ):
            options["azure_deployment"] = deployment_env.strip()

    if (
        provider.api_kind == "azure_openai"
        and "azure_deployment" not in options
        and model
        and isinstance(model.deployment_env, str)
        and model.deployment_env.strip()
    ):
        env_value = os.getenv(model.deployment_env.strip())
        if env_value and env_value.strip():
            options["azure_deployment"] = env_value.strip()
        else:
            options["azure_deployment"] = model.deployment_env.strip()

    endpoint = _resolve_endpoint(provider, credential_payload, options)
    api_key = _resolve_api_key(provider, credential_payload, options)
    metadata = _resolve_metadata(credential_payload)
    if provider.requires_api_key and not api_key:
        raise ChatClientError(f"Provider '{provider.name}' requires an API key")
    return ProviderRuntimeConfig(
        provider=provider,
        model=model,
        endpoint=endpoint,
        api_key=api_key,
        options=options,
        metadata=metadata,
    )


__all__ = [
    "ChatClient",
    "ChatClientError",
    "OpenAIChatClient",
    "AnthropicChatClient",
    "ProviderRuntimeConfig",
    "build_chat_client",
    "build_provider_runtime_config",
]
