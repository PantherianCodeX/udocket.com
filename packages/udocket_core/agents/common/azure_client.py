# pyright: strict

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
import threading
import time
from typing import Any, Optional, Protocol, cast
from urllib.parse import urlsplit


class _ResponseProtocol(Protocol):
    status_code: int
    text: str
    headers: Mapping[str, Any] | None

    def json(self) -> object: ...

    def raise_for_status(self) -> None: ...


class _RequestsExceptionsProtocol(Protocol):
    HTTPError: type[Exception]
    RequestException: type[Exception]


class _RequestsProtocol(Protocol):
    exceptions: _RequestsExceptionsProtocol

    class Session(Protocol):
        def post(
            self,
            url: str,
            *,
            params: Mapping[str, object] | None = None,
            headers: Mapping[str, str] | None = None,
            json: object | None = None,
            stream: bool | None = None,
            timeout: int | float | tuple[float, float] | None = None,
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
from .http_client import HTTPRetryConfig, HTTPSessionConfig, RequestsSessionManager
CANADIAN_REGIONS = {"canadacentral", "canadaeast"}


logger = logging.getLogger("udocket.azure.client")


@dataclass
class _FallbackState:
    require_default_temperature: bool = False
    disable_max_output_tokens: bool = False


_FALLBACK_STATE: dict[tuple[str, str], _FallbackState] = {}
_FALLBACK_LOCK = threading.Lock()


def _fallback_state_key(config: AzureClientConfig) -> tuple[str, str]:
    endpoint = config.endpoint.strip().lower()
    deployment = config.deployment.strip().lower()
    return (endpoint, deployment)


def _get_fallback_state(key: tuple[str, str]) -> _FallbackState:
    with _FALLBACK_LOCK:
        state = _FALLBACK_STATE.get(key)
        if state is None:
            return _FallbackState()
        return _FallbackState(
            require_default_temperature=state.require_default_temperature,
            disable_max_output_tokens=state.disable_max_output_tokens,
        )


def _update_fallback_state(
    key: tuple[str, str],
    *,
    require_default_temperature: bool = False,
    disable_max_output_tokens: bool = False,
) -> None:
    if not require_default_temperature and not disable_max_output_tokens:
        return
    with _FALLBACK_LOCK:
        state = _FALLBACK_STATE.get(key)
        if state is None:
            state = _FallbackState()
            _FALLBACK_STATE[key] = state
        if require_default_temperature:
            state.require_default_temperature = True
        if disable_max_output_tokens:
            state.disable_max_output_tokens = True


def _reset_fallback_state() -> None:  # pragma: no cover - test helper
    with _FALLBACK_LOCK:
        _FALLBACK_STATE.clear()


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


def _summarize_exception_chain(exc: BaseException, *, max_depth: int = 4) -> str:
    parts: list[str] = []
    current: BaseException | None = exc
    visited: set[int] = set()
    depth = 0
    while current is not None and depth < max_depth:
        identifier = id(current)
        if identifier in visited:
            break
        visited.add(identifier)
        text = str(current).strip()
        if not text:
            text = current.__class__.__name__
        parts.append(text)
        next_exc: BaseException | None = None
        if current.__cause__ is not None:
            next_exc = current.__cause__
        elif current.__context__ is not None and not current.__suppress_context__:
            next_exc = current.__context__
        current = next_exc
        depth += 1
    return " -> ".join(parts)


@dataclass
class AzureClientConfig:
    endpoint: str
    key: str
    deployment: str
    api_version: str = "2024-10-21"
    timeout: int = 120
    connect_timeout: int = 10
    read_timeout: int = 600
    allow_non_ca_region: bool = False
    session_pool_size: int = 10
    retry_config: HTTPRetryConfig = field(
        default_factory=lambda: HTTPRetryConfig(total=3, backoff_factor=0.6)
    )
    health_check_cache_ttl: int = 300
    health_check_max_tokens: int = 16

    def validate(self) -> None:
        if not self.endpoint:
            raise ValueError("Missing Azure OpenAI endpoint")
        if not self.allow_non_ca_region and not _endpoint_is_canadian(self.endpoint):
            raise ValueError(
                f"Azure OpenAI endpoint '{self.endpoint}' is outside allowed Canadian regions"
            )
        if self.allow_non_ca_region and not _endpoint_is_canadian(self.endpoint):
            logger.warning(
                "Azure endpoint %s bypasses Canadian-region guard (testing override enabled).",
                self.endpoint,
            )
        if not self.key:
            raise ValueError("Missing Azure OpenAI API key")
        if not self.deployment:
            raise ValueError("Missing Azure OpenAI deployment name")
        _require_requests()


_SESSION_MANAGER_CACHE: dict[HTTPSessionConfig, RequestsSessionManager] = {}
_SESSION_MANAGER_LOCK = threading.Lock()


def _resolve_session_manager(
    config: AzureClientConfig,
    override: RequestsSessionManager | None,
) -> RequestsSessionManager:
    if override is not None:
        return override
    http_config = HTTPSessionConfig(
        pool_maxsize=config.session_pool_size,
        retry=config.retry_config,
    )
    with _SESSION_MANAGER_LOCK:
        cached = _SESSION_MANAGER_CACHE.get(http_config)
        if cached is not None:
            return cached
        manager = RequestsSessionManager(config=http_config)
        _SESSION_MANAGER_CACHE[http_config] = manager
        return manager


class AzureChatClient:
    """Lightweight wrapper around Azure OpenAI chat completions."""

    def __init__(
        self,
        config: AzureClientConfig,
        *,
        session_manager: RequestsSessionManager | None = None,
    ) -> None:
        self.config = config
        self.config.validate()
        self._session_manager = _resolve_session_manager(self.config, session_manager)
        self._health_lock = threading.Lock()
        self._last_health_check: float | None = None
        self._state_key = _fallback_state_key(self.config)
        fallback_state = _get_fallback_state(self._state_key)
        self._require_default_temperature: bool = fallback_state.require_default_temperature
        self._disable_max_output_tokens: bool = fallback_state.disable_max_output_tokens

    def chat(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Mapping[str, JSONValue]] = None,
    ) -> tuple[str, JSONObject]:
        requests_client = _require_requests()
        session = self._session_manager.session_for(self.config.endpoint)

        url = (
            self.config.endpoint.rstrip("/")
            + f"/openai/deployments/{self.config.deployment}/chat/completions"
        )
        params = {"api-version": self.config.api_version}
        message_payloads = [coerce_json_value(message) for message in messages]
        headers = {
            "api-key": self.config.key,
            "Content-Type": "application/json",
        }

        while True:
            temp_to_use = 1.0 if self._require_default_temperature else temperature
            payload: JSONObject = {
                "messages": message_payloads,
                "temperature": temp_to_use,
                "stream": True,
            }
            if max_tokens is not None:
                payload["max_completion_tokens"] = max_tokens
                if not self._disable_max_output_tokens:
                    payload["max_output_tokens"] = max_tokens
            if response_format:
                payload["response_format"] = dict(response_format)

            try:
                _resp = session.post(
                    url,
                    params=params,
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=(
                        float(max(1, self.config.connect_timeout)),
                        float(max(30, self.config.read_timeout)),
                    )
                    if (self.config.connect_timeout or self.config.read_timeout)
                    else self.config.timeout,
                )
                response = cast(_ResponseProtocol, _resp)
                logger.debug(
                    "azure request",
                    extra={
                        "endpoint": url,
                        "deployment": self.config.deployment,
                        "status_code": response.status_code,
                    },
                )
                response.raise_for_status()
                break
            except requests_client.exceptions.HTTPError as exc:
                response_obj = getattr(exc, "response", None)
                detail = cast(str, getattr(response_obj, "text", "") or "")
                status_code = getattr(response_obj, "status_code", None)
                detail_lower = detail.lower() if isinstance(detail, str) else ""
                if (
                    status_code == 400
                    and detail_lower
                    and "temperature" in detail_lower
                    and "only the default (1) value is supported" in detail_lower
                    and not self._require_default_temperature
                ):
                    logger.warning(
                        "azure temperature fallback",
                        extra={
                            "endpoint": url,
                            "deployment": self.config.deployment,
                            "requested_temperature": temperature,
                            "status_code": status_code,
                        },
                    )
                    self._require_default_temperature = True
                    _update_fallback_state(
                        self._state_key,
                        require_default_temperature=True,
                    )
                    continue
                if (
                    status_code == 400
                    and detail_lower
                    and "max_output_tokens" in detail_lower
                    and not self._disable_max_output_tokens
                    and max_tokens is not None
                ):
                    logger.info(
                        "retrying without max_output_tokens parameter",
                        extra={
                            "endpoint": url,
                            "deployment": self.config.deployment,
                            "status_code": status_code,
                        },
                    )
                    self._disable_max_output_tokens = True
                    _update_fallback_state(
                        self._state_key,
                        disable_max_output_tokens=True,
                    )
                    continue
                error_message = f"Azure OpenAI request failed: {exc}"
                if detail:
                    error_message += f"\n{detail}"
                logger.error(
                    "azure request failed",
                    extra={
                        "endpoint": url,
                        "deployment": self.config.deployment,
                        "status_code": status_code,
                        "body": detail,
                    },
                )
                raise RuntimeError(error_message) from exc
            except requests_client.exceptions.RequestException as exc:
                self._session_manager.reset_session(self.config.endpoint)
                connection_error_type = getattr(requests_client.exceptions, "ConnectionError", None)
                timeout_error_type = getattr(requests_client.exceptions, "Timeout", None)
                is_connection_error = (
                    isinstance(exc, connection_error_type) if connection_error_type is not None else False
                )
                is_timeout_error = (
                    isinstance(exc, timeout_error_type) if timeout_error_type is not None else False
                )
                error_summary = _summarize_exception_chain(exc)
                retry_cfg = self.config.retry_config
                max_retries = retry_cfg.total if retry_cfg.total >= 0 else 0
                retry_fragment = f" (max retries={max_retries})" if max_retries else ""
                guidance_parts: list[str] = []
                if error_summary:
                    summary_text = f"Last error: {error_summary}"
                    if not summary_text.endswith((".", "!", "?")):
                        summary_text += "."
                    guidance_parts.append(summary_text)
                if is_connection_error and "closed connection without response" in error_summary.lower():
                    guidance_parts.append("Azure closed the connection without sending a response.")
                elif is_connection_error:
                    guidance_parts.append("Azure reported a connection failure.")
                if is_timeout_error:
                    guidance_parts.append("The request timed out waiting for a response from Azure.")
                message = f"Azure OpenAI transport error: request failed after retries{retry_fragment}."
                if guidance_parts:
                    message = message.rstrip(".") + ". " + " ".join(guidance_parts)

                logger.error(
                    "azure transport failure",
                    exc_info=exc,
                    extra={
                        "endpoint": url,
                        "deployment": self.config.deployment,
                        "max_retries": max_retries,
                        "error": error_summary,
                    },
                )
                raise RuntimeError(message) from exc

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

        content_parts: list[str] = []
        usage: JSONObject = {}

        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            segment = raw_line.strip()
            if not segment:
                continue
            if segment.startswith("data:"):
                payload_text = segment[5:].strip()
            else:
                payload_text = segment
            if not payload_text:
                continue
            if payload_text == "[DONE]":
                break
            try:
                chunk = _require_json_object(json.loads(payload_text), context="stream chunk")
            except ValueError:
                logger.debug(
                    "azure stream chunk decode failed",
                    extra={
                        "deployment": self.config.deployment,
                        "request_id": request_id,
                        "chunk": payload_text[:200],
                    },
                )
                continue

            choices_value = chunk.get("choices")
            if isinstance(choices_value, list) and choices_value:
                choice0 = choices_value[0]
                if isinstance(choice0, Mapping):
                    choice_obj = _require_json_object(choice0, context="stream choice")
                    delta_value = choice_obj.get("delta")
                    if isinstance(delta_value, Mapping):
                        delta = _require_json_object(delta_value, context="stream delta")
                        content_piece = delta.get("content")
                        if isinstance(content_piece, str):
                            content_parts.append(content_piece)
                        elif isinstance(content_piece, Sequence) and not isinstance(
                            content_piece, (str, bytes, bytearray)
                        ):
                            content_parts.append(_content_from_parts(content_piece))
                        else:
                            tool_calls_piece = delta.get("tool_calls")
                            if tool_calls_piece is not None:
                                content_parts.append(_content_from_tool_calls(tool_calls_piece))
                            annotations_piece = delta.get("annotations")
                            if annotations_piece is not None:
                                content_parts.append(_content_from_annotations(annotations_piece))
                    message_value = choice_obj.get("message")
                    if isinstance(message_value, Mapping):
                        message_obj = _require_json_object(message_value, context="stream message")
                        content_value = message_obj.get("content")
                        tool_text = _content_from_tool_calls(message_obj.get("tool_calls"))
                        annotation_text = _content_from_annotations(message_obj.get("annotations"))
                        appended_annotations = False
                        appended_tools = False
                        if isinstance(content_value, str):
                            content_parts.append(content_value)
                        elif isinstance(content_value, Sequence) and not isinstance(
                            content_value, (str, bytes, bytearray)
                        ):
                            content_parts.append(_content_from_parts(content_value))
                        else:
                            if annotation_text:
                                content_parts.append(annotation_text)
                                appended_annotations = True
                            if tool_text:
                                content_parts.append(tool_text)
                                appended_tools = True
                        if annotation_text and not appended_annotations:
                            content_parts.append(annotation_text)
                        if tool_text and not appended_tools:
                            content_parts.append(tool_text)

            usage_value = chunk.get("usage")
            if isinstance(usage_value, Mapping):
                usage = _require_json_object(usage_value, context="usage metadata")

        content = "".join(part for part in content_parts if part).strip()
        if content:
            content = _extract_json_candidate(content)

        if not content:
            logger.error(
                "azure streaming completion empty",
                extra={
                    "deployment": self.config.deployment,
                    "request_id": request_id,
                },
            )
            raise RuntimeError(
                "Azure OpenAI returned an empty streaming completion "
                f"(deployment='{self.config.deployment}', request_id='{request_id}')."
            )

        logger.debug(
            "azure response usage",
            extra={
                "deployment": self.config.deployment,
                "usage": usage,
            },
        )

        return content, usage

    def health_check(self, *, force: bool = False) -> None:
        now = time.monotonic()
        with self._health_lock:
            if (
                not force
                and self._last_health_check is not None
                and (now - self._last_health_check) < max(1, self.config.health_check_cache_ttl)
            ):
                return
        parsed = urlsplit(self.config.endpoint)
        hostname = (parsed.hostname or "").lower()
        if not hostname or hostname.startswith("example") or hostname in {"localhost", "127.0.0.1"}:
            with self._health_lock:
                self._last_health_check = now
            return
        try:
            self.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "You respond to health probes with a short acknowledgement.",
                    },
                    {
                        "role": "user",
                        "content": "Reply with the word OK.",
                    },
                ],
                temperature=1.0,
                max_tokens=max(256, self.config.health_check_max_tokens),
                response_format=None,
            )
        except RuntimeError as exc:
            raise RuntimeError(f"Azure OpenAI health check failed: {exc}") from exc
        with self._health_lock:
            self._last_health_check = now


__all__ = [
    "AzureClientConfig",
    "AzureChatClient",
    "_endpoint_is_canadian",
]
