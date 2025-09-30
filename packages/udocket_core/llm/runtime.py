"""Runtime helpers for constructing LLM chat clients."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple

try:  # pragma: no cover - optional dependency guard
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore[assignment]

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
        messages: List[Dict[str, str]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]: ...


class ChatClientError(RuntimeError):
    """Raised when an LLM invocation cannot be completed."""


def _require_requests() -> None:
    if requests is None:  # pragma: no cover - dependency missing
        raise RuntimeError("requests library is required for HTTP LLM providers")


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
        messages: List[Dict[str, str]],
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
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        except Exception as exc:  # pragma: no cover - network failure
            raise ChatClientError(f"OpenAI request failed: {exc}") from exc
        if response.status_code >= 400:
            text = response.text
            raise ChatClientError(
                f"OpenAI request failed with status {response.status_code}: {text[:512]}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise ChatClientError("OpenAI response was not valid JSON") from exc
        choices = data.get("choices")
        if not choices:
            raise ChatClientError("OpenAI response missing choices")
        first = choices[0] or {}
        message = first.get("message") or {}
        content = message.get("content") or ""
        if not isinstance(content, str):
            content = str(content)
        usage = data.get("usage") or {}
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
        messages: List[Dict[str, str]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        if not messages:
            raise ChatClientError("Anthropic requires at least one message")
        max_tokens = max(1, int(max_tokens or 1024))
        converted: List[Dict[str, Any]] = []
        for message in messages:
            role = message.get("role") or "user"
            content = message.get("content")
            if isinstance(content, str):
                parts = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                parts = content
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
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        except Exception as exc:  # pragma: no cover - network failure
            raise ChatClientError(f"Anthropic request failed: {exc}") from exc
        if response.status_code >= 400:
            text = response.text
            raise ChatClientError(
                f"Anthropic request failed with status {response.status_code}: {text[:512]}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise ChatClientError("Anthropic response was not valid JSON") from exc
        content_blocks = data.get("content") or []
        text_fragments: List[str] = []
        for block in content_blocks:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    text_fragments.append(text)
        content = "".join(text_fragments).strip()
        usage_raw = data.get("usage") or {}
        usage = {
            "prompt_tokens": usage_raw.get("input_tokens"),
            "completion_tokens": usage_raw.get("output_tokens"),
            "total_tokens": usage_raw.get("total_tokens"),
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
        extra_headers = {}
        if metadata:
            headers = metadata.get("headers")
            if isinstance(headers, dict):
                extra_headers = {str(k): str(v) for k, v in headers.items() if k and v}
        if options.get("headers") and isinstance(options.get("headers"), dict):
            extra_headers.update({str(k): str(v) for k, v in options["headers"].items() if k and v})
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
