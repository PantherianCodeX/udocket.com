# pyright: strict

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional, Protocol, cast


class _ResponseProtocol(Protocol):
    status_code: int
    text: str
    headers: Mapping[str, Any] | None

    def json(self) -> object: ...

    def raise_for_status(self) -> None: ...


class _RequestsExceptionsProtocol(Protocol):
    HTTPError: type[Exception]


class _RequestsProtocol(Protocol):
    exceptions: _RequestsExceptionsProtocol

    def post(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        json: object | None = None,
        timeout: int | float | None = None,
    ) -> _ResponseProtocol: ...


_requests_module: _RequestsProtocol | None
try:  # pragma: no cover - optional dependency guard
    import requests as _imported_requests
except Exception:  # pragma: no cover
    _requests_module = None
else:
    _requests_module = cast(_RequestsProtocol, _imported_requests)

requests: _RequestsProtocol | None = _requests_module

from packages.udocket_core.json_utils import (
    JSONObject,
    JSONValue,
    coerce_json_value,
    ensure_json_object,
)
CANADIAN_REGIONS = {"canadacentral", "canadaeast"}


logger = logging.getLogger("udocket.azure.client")


def _endpoint_is_canadian(endpoint: str) -> bool:
    endpoint_lower = endpoint.lower()
    return any(region in endpoint_lower for region in CANADIAN_REGIONS)


def _require_requests() -> _RequestsProtocol:
    if requests is None:  # pragma: no cover - dependency missing
        raise RuntimeError("requests library is required for Azure OpenAI calls")
    return requests


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

def _iter_mappings(payload: object) -> Iterable[Mapping[str, object]]:
    if isinstance(payload, Mapping):
        yield payload
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for item in cast(Sequence[object], payload):
            if isinstance(item, Mapping):
                yield item


def _is_json_structure(value: object) -> bool:
    return isinstance(value, Mapping) or (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
    )


def _require_json_object(value: object, *, context: str) -> JSONObject:
    try:
        return ensure_json_object(value, context=context)
    except ValueError as exc:  # pragma: no cover - network failure path
        raise RuntimeError(f"Azure OpenAI returned a non-object payload for {context}") from exc


def _content_from_tool_calls(tool_calls: object) -> str:
    for call in _iter_mappings(tool_calls):
        fn_value = call.get("function")
        if not isinstance(fn_value, Mapping):
            continue
        fn_mapping = cast(Mapping[str, object], fn_value)
        args_value: object | None = fn_mapping.get("arguments")
        if args_value is None:
            continue
        args: object = args_value
        if _is_json_structure(args):
            try:
                return json.dumps(args)
            except (TypeError, ValueError):
                return str(args)
        if isinstance(args, str) and args.strip():
            return args
    return ""


def _content_from_annotations(annotations: object) -> str:
    items = list(_iter_mappings(annotations))
    if not items:
        return ""

    normalized_items: list[dict[str, object]] = [dict(annotation.items()) for annotation in items]

    json_fragments: list[str] = []
    text_fragments: list[str] = []

    for annotation in normalized_items:
        for key in ("output_json", "json", "data"):
            value: object | None = annotation.get(key)
            if _is_json_structure(value):
                try:
                    json_fragments.append(json.dumps(value))
                except (TypeError, ValueError):
                    json_fragments.append(str(value))
                break
            if isinstance(value, str) and value.strip():
                json_fragments.append(value.strip())
                break
        else:
            for text_key in ("text", "output_text", "content"):
                text_value: object | None = annotation.get(text_key)
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


def _content_from_parts(parts: object) -> str:
    items = list(_iter_mappings(parts))
    if not items:
        return ""

    normalized_parts: list[dict[str, object]] = [dict(part.items()) for part in items]

    text_fragments: list[str] = []
    json_fragments: list[str] = []

    for part in normalized_parts:
        part_type: object | None = part.get("type")
        if isinstance(part_type, str) and part_type.startswith("output_json"):
            raw_candidate = part.get("json") or part.get("text") or part.get("data")
            raw: object | None = raw_candidate
            if _is_json_structure(raw):
                try:
                    json_fragments.append(json.dumps(raw))
                    continue
                except (TypeError, ValueError):
                    json_fragments.append(str(raw))
                    continue
            if isinstance(raw, str) and raw.strip():
                json_fragments.append(raw)
                continue

        text_value_candidate = part.get("text") or part.get("content")
        text_value: object | None = text_value_candidate
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


def _content_from_delta(delta_payload: object) -> str:
    if not isinstance(delta_payload, Mapping):
        return ""
    mapping_payload = cast(Mapping[str, object], delta_payload)
    delta_content = mapping_payload.get("content")
    if isinstance(delta_content, str) and delta_content.strip():
        return delta_content
    if _is_json_structure(delta_content):
        text = _content_from_parts(delta_content)
        if text:
            return text
    annotations = mapping_payload.get("annotations")
    if annotations:
        text = _content_from_annotations(annotations)
        if text:
            return text
    tool_calls = mapping_payload.get("tool_calls")
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
        _require_requests()


class AzureChatClient:
    """Lightweight wrapper around Azure OpenAI chat completions."""

    def __init__(self, config: AzureClientConfig) -> None:
        self.config = config
        self.config.validate()

    def chat(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Mapping[str, JSONValue]] = None,
    ) -> tuple[str, JSONObject]:
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
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        response_format: Optional[Mapping[str, JSONValue]],
        include_max_output_tokens: bool,
    ) -> tuple[str, JSONObject]:
        requests_client = _require_requests()

        url = (
            self.config.endpoint.rstrip("/")
            + f"/openai/deployments/{self.config.deployment}/chat/completions"
        )
        params = {"api-version": self.config.api_version}
        message_payloads = [coerce_json_value(message) for message in messages]
        payload: JSONObject = {
            "messages": message_payloads,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_completion_tokens"] = max_tokens
            if include_max_output_tokens:
                payload["max_output_tokens"] = max_tokens
        if response_format:
            payload["response_format"] = dict(response_format)

        headers = {
            "api-key": self.config.key,
            "Content-Type": "application/json",
        }

        try:
            response = requests_client.post(
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
        except requests_client.exceptions.HTTPError as exc:
            response_obj = getattr(exc, "response", None)
            detail = cast(str, getattr(response_obj, "text", "") or "")
            if (
                include_max_output_tokens
                and response_obj is not None
                and getattr(response_obj, "status_code", None) == 400
                and detail
                and "max_output_tokens" in detail
            ):
                logger.info(
                    "retrying without max_output_tokens parameter",
                    extra={
                        "endpoint": url,
                        "deployment": self.config.deployment,
                        "status_code": getattr(response_obj, "status_code", None),
                    },
                )
                return self._chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    include_max_output_tokens=False,
                )
            error_message = (
                f"Azure OpenAI request failed: {exc}" + (f"\n{detail}" if detail else "")
            )
            logger.error(
                "azure request failed",
                extra={
                        "endpoint": url,
                        "deployment": self.config.deployment,
                        "status_code": getattr(response_obj, "status_code", None),
                        "body": detail,
                    },
                )
            raise RuntimeError(error_message) from exc

        response_text = response.text
        headers_obj = getattr(response, "headers", None)
        response_headers: Mapping[str, str] | None
        if isinstance(headers_obj, Mapping):
            response_headers = cast(Mapping[str, str], headers_obj)
        elif headers_obj is None:
            response_headers = None
        else:
            try:
                response_headers = {str(key): str(value) for key, value in headers_obj}
            except Exception:
                response_headers = None

        request_id: str | None = None
        if response_headers is not None:
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
            data = _require_json_object(response.json(), context="chat response")
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

        choices_value = data.get("choices")
        if not isinstance(choices_value, list):
            raise RuntimeError("Azure OpenAI response missing choices")

        choices: list[JSONObject] = [item for item in choices_value if isinstance(item, dict)]
        if not choices:
            raise RuntimeError("Azure OpenAI response missing choices")

        choice0 = choices[0]
        message_value = choice0.get("message")
        if isinstance(message_value, Mapping):
            message = _require_json_object(message_value, context="chat message")
        else:
            message = {}

        content = ""
        content_obj = message.get("content")
        if isinstance(content_obj, str) and content_obj.strip():
            content = content_obj
        else:
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

        usage_value = data.get("usage")
        if isinstance(usage_value, Mapping):
            usage = _require_json_object(usage_value, context="usage metadata")
        else:
            usage = {}

        return content, usage


__all__ = ["AzureClientConfig", "AzureChatClient", "_endpoint_is_canadian"]
