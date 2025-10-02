from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:  # pragma: no cover - optional dependency guard
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore[assignment]


CANADIAN_REGIONS = {"canadacentral", "canadaeast"}


logger = logging.getLogger("udocket.azure.client")


def _endpoint_is_canadian(endpoint: str) -> bool:
    endpoint_lower = endpoint.lower()
    return any(region in endpoint_lower for region in CANADIAN_REGIONS)


def _extract_json_candidate(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped
    fence = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        inner = fence.group(1).strip()
        if inner:
            return inner
    match = re.search(r"([\[{].*[\]}])", stripped, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped


def _content_from_tool_calls(tool_calls: Any) -> str:
    items = tool_calls or []
    for call in items:
        if not isinstance(call, dict):
            continue
        fn = call.get("function") or {}
        args = fn.get("arguments")
        if isinstance(args, (dict, list)):
            return json.dumps(args)
        if isinstance(args, str) and args.strip():
            return args
    return ""


def _content_from_annotations(annotations: Any) -> str:
    if not annotations:
        return ""

    items: List[Dict[str, Any]]
    if isinstance(annotations, list):
        items = [item for item in annotations if isinstance(item, dict)]
    elif isinstance(annotations, dict):
        items = [annotations]
    else:
        return ""

    json_fragments: List[str] = []
    text_fragments: List[str] = []

    for annotation in items:
        for key in ("output_json", "json", "data"):
            value = annotation.get(key)
            if isinstance(value, (dict, list)):
                json_fragments.append(json.dumps(value))
                break
            if isinstance(value, str) and value.strip():
                json_fragments.append(value.strip())
                break
        else:
            for text_key in ("text", "output_text", "content"):
                text_value = annotation.get(text_key)
                if isinstance(text_value, str) and text_value.strip():
                    text_fragments.append(text_value.strip())
                    break

    if json_fragments:
        combined_json = "".join(json_fragments).strip()
        if combined_json:
            return combined_json

    if text_fragments:
        combined_text = "".join(text_fragments).strip()
        if combined_text:
            return combined_text

    return ""


def _content_from_parts(parts: Any) -> str:
    if not parts:
        return ""

    text_fragments: List[str] = []
    json_fragments: List[str] = []

    for part in parts:
        if not isinstance(part, dict):
            continue

        part_type = part.get("type") or ""

        if part_type and str(part_type).startswith("output_json"):
            raw = part.get("json") or part.get("text") or part.get("data")
            if isinstance(raw, (dict, list)):
                json_fragments.append(json.dumps(raw))
                continue
            if isinstance(raw, str) and raw.strip():
                json_fragments.append(raw)
                continue

        text_value = part.get("text") or part.get("content")
        if isinstance(text_value, str) and text_value.strip():
            text_fragments.append(text_value)

    if json_fragments:
        combined_json = "".join(json_fragments).strip()
        if combined_json:
            return combined_json

    if text_fragments:
        combined_text = "".join(text_fragments).strip()
        if combined_text:
            return combined_text

    return ""


def _content_from_delta(delta_payload: Any) -> str:
    if not isinstance(delta_payload, dict):
        return ""
    delta_content = delta_payload.get("content")
    if isinstance(delta_content, str) and delta_content.strip():
        return delta_content
    if isinstance(delta_content, list):
        text = _content_from_parts(delta_content)
        if text:
            return text
    annotations = delta_payload.get("annotations")
    if annotations:
        text = _content_from_annotations(annotations)
        if text:
            return text
    tool_calls = delta_payload.get("tool_calls")
    if tool_calls:
        text = _content_from_tool_calls(tool_calls)
        if text:
            return text
    return ""


@dataclass
class AzureClientConfig:
    endpoint: str
    key: str
    deployment: str
    api_version: str = "2024-10-21"
    timeout: int = 120
    allow_non_ca_region: bool = False

    def validate(self) -> None:
        if not self.endpoint:
            raise ValueError("Missing Azure OpenAI endpoint")
        if not self.allow_non_ca_region and not _endpoint_is_canadian(self.endpoint):
            logger.warning(
                "Azure endpoint %s is outside approved Canadian regions; allowing temporarily.",
                self.endpoint,
            )
            # TODO: move regional restrictions into configurable settings enforcement.
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
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        return self._chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            include_max_output_tokens=True,
        )

    def _chat(
        self,
        *,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        response_format: Optional[Dict[str, Any]],
        include_max_output_tokens: bool,
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
            payload["max_completion_tokens"] = max_tokens
            if include_max_output_tokens:
                payload["max_output_tokens"] = max_tokens
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
            if (
                include_max_output_tokens
                and exc.response is not None
                and exc.response.status_code == 400
                and detail
                and "max_output_tokens" in detail
            ):
                logger.info(
                    "retrying without max_output_tokens parameter",
                    extra={
                        "endpoint": url,
                        "deployment": self.config.deployment,
                        "status_code": exc.response.status_code,
                    },
                )
                return self._chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    include_max_output_tokens=False,
                )
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

        response_text = response.text
        headers_obj = getattr(response, "headers", None)
        if headers_obj is None:
            response_headers: Dict[str, Any] = {}
        elif hasattr(headers_obj, "get"):
            response_headers = headers_obj  # type: ignore[assignment]
        else:
            try:
                response_headers = dict(headers_obj)
            except Exception:
                response_headers = {}

        request_id = None
        if hasattr(response_headers, "get"):
            request_id = response_headers.get("x-ms-request-id") or response_headers.get("x-request-id")

        if logger.isEnabledFor(logging.DEBUG):
            preview = (response_text or "")[:2000]
            logger.debug(
                "azure response body preview=%s",
                preview if preview else "<empty>",
                extra={
                    "deployment": self.config.deployment,
                    "request_id": request_id,
                },
            )

        try:
            data = response.json()
        except ValueError as exc:
            preview = (response_text or "")[:500]
            preview_single_line = preview.replace("\n", "\\n").replace("\r", "\\r")
            logger.error(
                "azure response json decode failed (status=%s, deployment=%s, request_id=%s): %s",
                response.status_code,
                self.config.deployment,
                request_id,
                preview_single_line if preview_single_line else "<empty>",
            )
            raise RuntimeError(
                "Azure OpenAI returned an invalid JSON payload (status="
                f"{response.status_code}, deployment='{self.config.deployment}', request_id='{request_id}'). "
                f"Body preview: {preview_single_line if preview_single_line else '<empty>'}"
            ) from exc

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

        choice0 = choices[0]
        message = choice0.get("message") or {}

        content = ""
        content_obj = message.get("content")
        if isinstance(content_obj, str) and content_obj.strip():
            content = content_obj
        elif isinstance(content_obj, list):
            content = _content_from_parts(content_obj)

        if not content:
            content = _content_from_tool_calls(message.get("tool_calls"))

        if not content:
            content = _content_from_annotations(message.get("annotations"))

        if not content:
            refusal = message.get("refusal")
            if isinstance(refusal, str) and refusal.strip():
                content = refusal
            elif isinstance(refusal, (dict, list)) and refusal:
                try:
                    content = json.dumps(refusal)
                except Exception:
                    content = str(refusal)

        if not content:
            content = _content_from_delta(choice0.get("delta"))

        if content:
            content = _extract_json_candidate(content)

        if not content:
            finish_reason = choice0.get("finish_reason")
            preview = (response_text or "")[:500]
            preview_single_line = preview.replace("\n", "\\n").replace("\r", "\\r")
            logger.error(
                "azure empty completion (status=%s, deployment=%s, request_id=%s, finish_reason=%s): %s",
                response.status_code,
                self.config.deployment,
                request_id,
                finish_reason,
                preview_single_line if preview_single_line else "<empty>",
            )
            raise RuntimeError(
                "Azure OpenAI returned an empty completion (deployment='"
                f"{self.config.deployment}', request_id='{request_id}', finish_reason='{finish_reason}'). "
                f"Body preview: {preview_single_line if preview_single_line else '<empty>'}"
            )

        if not isinstance(content, str):
            try:
                content = json.dumps(content)
            except Exception:
                content = ""

        if not content:
            finish_reason = choice0.get("finish_reason")
            preview = (response_text or "")[:500]
            preview_single_line = preview.replace("\n", "\\n").replace("\r", "\\r")
            logger.error(
                "azure empty completion after coercion (status=%s, deployment=%s, request_id=%s, finish_reason=%s): %s",
                response.status_code,
                self.config.deployment,
                request_id,
                finish_reason,
                preview_single_line if preview_single_line else "<empty>",
            )
            raise RuntimeError(
                "Azure OpenAI returned an empty completion after coercion (deployment='"
                f"{self.config.deployment}', request_id='{request_id}', finish_reason='{finish_reason}'). "
                f"Body preview: {preview_single_line if preview_single_line else '<empty>'}"
            )

        usage = data.get("usage") or {}
        return content, usage


__all__ = ["AzureClientConfig", "AzureChatClient", "_endpoint_is_canadian"]
