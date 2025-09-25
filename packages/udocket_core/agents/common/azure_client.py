from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import json

try:  # pragma: no cover - optional dependency guard
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore[assignment]


CANADIAN_REGIONS = {"canadacentral", "canadaeast"}


def _endpoint_is_canadian(endpoint: str) -> bool:
    endpoint_lower = endpoint.lower()
    return any(region in endpoint_lower for region in CANADIAN_REGIONS)


@dataclass
class AzureClientConfig:
    endpoint: str
    key: str
    deployment: str
    api_version: str = "2024-08-01-preview"
    timeout: int = 60

    def validate(self) -> None:
        if not self.endpoint:
            raise ValueError("Missing Azure OpenAI endpoint")
        if not _endpoint_is_canadian(self.endpoint):
            raise ValueError("Azure OpenAI endpoint must target canadacentral or canadaeast")
        if not self.key:
            raise ValueError("Missing Azure OpenAI API key")
        if not self.deployment:
            raise ValueError("Missing Azure OpenAI deployment name")
        if requests is None:  # pragma: no cover - dependency missing
            raise RuntimeError("requests library is required for Azure OpenAI calls")


class AzureChatClient:
    """Lightweight wrapper around Azure OpenAI chat completions."""

    def __init__(self, config: AzureClientConfig) -> None:
        self.config = config
        self.config.validate()

    def chat(
        self,
        *,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        url = (
            self.config.endpoint.rstrip("/")
            + f"/openai/deployments/{self.config.deployment}/chat/completions"
        )
        params = {"api-version": self.config.api_version}
        payload: Dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format:
            payload["response_format"] = response_format

        headers = {
            "api-key": self.config.key,
            "Content-Type": "application/json",
        }

        response = requests.post(  # type: ignore[attr-defined]
            url,
            params=params,
            headers=headers,
            json=payload,
            timeout=self.config.timeout,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Azure OpenAI response missing choices")
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        usage = data.get("usage") or {}
        return content, usage


__all__ = ["AzureClientConfig", "AzureChatClient", "_endpoint_is_canadian"]
