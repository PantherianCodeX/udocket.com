from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import json
import logging
import os

try:  # pragma: no cover - optional dependency guard
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore[assignment]


CANADIAN_REGIONS = {"canadacentral", "canadaeast"}


logger = logging.getLogger("udocket.azure.client")


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
    allow_non_ca_region: bool = False

    def validate(self) -> None:
        if not self.endpoint:
            raise ValueError("Missing Azure OpenAI endpoint")
        if not self.allow_non_ca_region and not _endpoint_is_canadian(
            self.endpoint
        ):
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

        try:
            response = requests.post(  # type: ignore[attr-defined]
                url,
                params=params,
                headers=headers,
                json=payload,
                timeout=self.config.timeout,
            )
            logger.debug(
                "azure request",
                extra={
                    "endpoint": url,
                    "deployment": self.config.deployment,
                    "status_code": response.status_code,
                },
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:  # type: ignore[attr-defined]
            detail = exc.response.text if exc.response is not None else ""
            message = (
                f"Azure OpenAI request failed: {exc}" + (f"\n{detail}" if detail else "")
            )
            logger.error(
                "azure request failed",
                extra={
                    "endpoint": url,
                    "deployment": self.config.deployment,
                    "status_code": getattr(exc.response, "status_code", None),
                    "body": detail,
                },
            )
            raise RuntimeError(message) from exc
        data = response.json()
        logger.debug(
            "azure response usage",
            extra={
                "deployment": self.config.deployment,
                "usage": data.get("usage"),
            },
        )
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Azure OpenAI response missing choices")
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        usage = data.get("usage") or {}
        return content, usage


__all__ = ["AzureClientConfig", "AzureChatClient", "_endpoint_is_canadian"]
