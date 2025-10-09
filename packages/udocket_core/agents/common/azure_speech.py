from __future__ import annotations

# pyright: strict

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from packages.udocket_core.json_utils import (
    JSONObject,
    JSONValue,
    coerce_json_object,
    coerce_json_value,
)

from .http_client import (
    HTTPRetryConfig,
    HTTPSessionConfig,
    RequestsSessionManager,
    RequestsSessionProtocol,
)


class AzureSpeechError(RuntimeError):
    """Raised when Azure Speech operations fail."""


def _default_raise(message: str) -> Exception:
    return AzureSpeechError(message)


_CACHE_LOCK = threading.Lock()
_CACHE: dict[tuple[str, str], float] = {}


@dataclass(frozen=True)
class AzureSpeechHealthConfig:
    cache_ttl_s: int = 300
    timeout_s: float = 10.0
    session_manager: RequestsSessionManager = field(
        default_factory=lambda: RequestsSessionManager(
            config=HTTPSessionConfig(
                pool_maxsize=4,
                retry=HTTPRetryConfig(total=3, backoff_factor=0.6),
            )
        )
    )


def ensure_azure_speech_health(
    *,
    key: str,
    region: str,
    logger: logging.Logger,
    raise_error: Callable[[str], Exception] = _default_raise,
    config: AzureSpeechHealthConfig | None = None,
    force: bool = False,
) -> None:
    if not key:
        raise raise_error("Azure Speech key is required")
    if not region:
        raise raise_error("Azure Speech region is required")

    normalized_region = region.strip().lower()
    cfg = config or AzureSpeechHealthConfig()
    cache_key = (key, normalized_region)
    now = time.monotonic()
    if not force:
        with _CACHE_LOCK:
            last = _CACHE.get(cache_key)
            if last is not None and (now - last) < max(1, cfg.cache_ttl_s):
                return

    token_url = f"https://{normalized_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    session = cfg.session_manager.session_for(token_url)
    try:
        response = session.post(
            token_url,
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Content-Length": "0",
            },
            timeout=cfg.timeout_s,
        )
    except Exception as exc:  # pragma: no cover - network failure
        logger.error(
            "azure.speech.health.transport",
            extra={
                "region": normalized_region,
                "error": str(exc),
            },
        )
        raise raise_error(
            "Azure Speech transport error: could not reach the configured endpoint."
        ) from exc

    if response.status_code >= 400:
        preview = (response.text or "")[:500]
        logger.error(
            "azure.speech.health.failed",
            extra={
                "region": normalized_region,
                "status_code": response.status_code,
                "body": preview,
            },
        )
        raise raise_error(
            f"Azure Speech credential test failed (status={response.status_code})."
        )

    with _CACHE_LOCK:
        _CACHE[cache_key] = now


@dataclass(frozen=True)
class AzureSpeechClientConfig:
    key: str
    region: str
    api_version: str = "v3.2"
    request_timeout_s: float = 30.0
    poll_interval_s: float = 5.0
    poll_timeout_s: float = 5400.0
    health_cache_ttl_s: int = 300
    session_manager: RequestsSessionManager = field(
        default_factory=lambda: RequestsSessionManager(
            config=HTTPSessionConfig(
                pool_maxsize=6,
                retry=HTTPRetryConfig(total=4, backoff_factor=0.6),
            )
        )
    )

    @property
    def normalized_region(self) -> str:
        return self.region.strip().lower()

    @property
    def base_url(self) -> str:
        return f"https://{self.normalized_region}.api.cognitive.microsoft.com/speechtotext/{self.api_version}"

    @property
    def transcription_url(self) -> str:
        return f"{self.base_url}/transcriptions"

    @property
    def token_url(self) -> str:
        return f"https://{self.normalized_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"


@dataclass(frozen=True)
class AzureSpeechBatchResult:
    text: str
    duration_s: float | None
    metadata: JSONObject


_ISO_DURATION_PATTERN = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$",
    re.IGNORECASE,
)


def _json_payload(**items: object) -> JSONObject:
    return {key: coerce_json_value(value) for key, value in items.items()}


def _iso8601_to_seconds(value: str) -> float:
    trimmed = value.strip()
    if ":" in trimmed:
        parts = trimmed.split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid duration: {value}")
        hours, minutes = int(parts[0]), int(parts[1])
        seconds_part = parts[2]
        if "." in seconds_part:
            seconds, fractional = seconds_part.split(".", 1)
            return hours * 3600 + minutes * 60 + int(seconds) + float(f"0.{fractional}")
        return hours * 3600 + minutes * 60 + int(seconds_part)
    if trimmed.upper().startswith("P"):
        match = _ISO_DURATION_PATTERN.fullmatch(trimmed)
        if match is None:
            raise ValueError(f"Invalid duration: {value}")
        days = float(match.group("days") or 0)
        hours = float(match.group("hours") or 0)
        minutes = float(match.group("minutes") or 0)
        seconds = float(match.group("seconds") or 0)
        return days * 86400 + hours * 3600 + minutes * 60 + seconds
    raise ValueError(f"Invalid duration: {value}")


def _to_seconds(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value) / 10_000_000 if abs(float(value)) > 1_000_000 else float(value)
    if isinstance(value, str):
        return _iso8601_to_seconds(value)
    raise ValueError(f"Cannot convert value to seconds: {value!r}")


def _analyze_batch_error(payload: object) -> str:
    if isinstance(payload, Mapping):
        mapping = payload  # retain original for json dump fallback
        mp: Mapping[str, object] = payload  # typing-friendly view
        message_parts: list[str] = []
        code_val = mp.get("code")
        if isinstance(code_val, (str, int, float)):
            code_str = str(code_val).strip()
            if code_str:
                message_parts.append(f"code={code_str}")
        message_val = mp.get("message") or mp.get("description")
        if isinstance(message_val, (str, int, float)):
            message_text = str(message_val).strip()
            if message_text:
                message_parts.append(message_text)
        if message_parts:
            return " | ".join(message_parts)
        details_val = mp.get("details")
        if isinstance(details_val, Sequence) and not isinstance(details_val, (str, bytes, bytearray)):
            details_seq: Sequence[object] = details_val
            detail_messages = [_analyze_batch_error(item) for item in details_seq]
            filtered = [msg for msg in detail_messages if msg]
            if filtered:
                return "; ".join(filtered)
        props_val = mp.get("properties")
        if isinstance(props_val, Mapping):
            props_mp: Mapping[str, object] = props_val
            error_prop = props_mp.get("error")
            if error_prop is not None:
                return _analyze_batch_error(error_prop)
        return json.dumps(dict(mapping), ensure_ascii=False)[:500]
    return str(payload)


class AzureSpeechClient:
    def __init__(self, config: AzureSpeechClientConfig, *, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self._health_config = AzureSpeechHealthConfig(
            cache_ttl_s=config.health_cache_ttl_s,
            timeout_s=10.0,
            session_manager=config.session_manager,
        )

    def ensure_health(self, *, force: bool = False) -> None:
        ensure_azure_speech_health(
            key=self.config.key,
            region=self.config.region,
            logger=self.logger,
            raise_error=_default_raise,
            config=self._health_config,
            force=force,
        )

    def run_batch_transcription(
        self,
        *,
        audio_url: str,
        locale: str,
        diarization: bool,
        display_name: str,
        on_location: Callable[[str], None] | None = None,
    ) -> AzureSpeechBatchResult:
        location = self._create_transcription(audio_url, locale, diarization, display_name)
        if on_location is not None:
            try:
                on_location(location)
            except Exception as exc:  # pragma: no cover - logging only
                self.logger.debug("azure.speech.location_callback_failed", exc_info=exc)

        self._await_transcription(location)
        content_url = self._resolve_content_url(location)
        payload = self._download_json(content_url)
        return self._extract_transcription(payload, diarization, location)

    # Internal helpers -----------------------------------------------------

    def _session(self, url: str) -> RequestsSessionProtocol:
        return self.config.session_manager.session_for(url)

    def _create_transcription(
        self,
        audio_url: str,
        locale: str,
        diarization: bool,
        display_name: str,
    ) -> str:
        properties: dict[str, JSONValue] = {
            "wordLevelTimestampsEnabled": True,
            "punctuationMode": "DictatedAndAutomatic",
            "profanityFilterMode": "Masked",
        }
        if diarization:
            properties["diarizationEnabled"] = True
        payload: dict[str, JSONValue] = {
            "displayName": display_name,
            "locale": locale,
            "contentUrls": [audio_url],
            "properties": properties,
        }
        session = self._session(self.config.transcription_url)
        try:
            response = session.post(
                self.config.transcription_url,
                headers={
                    "Ocp-Apim-Subscription-Key": self.config.key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.config.request_timeout_s,
            )
        except Exception as exc:
            raise AzureSpeechError(f"Failed to create transcription job: {exc}") from exc
        if response.status_code >= 400:
            raise AzureSpeechError(
                f"Azure Speech create failed (status={response.status_code}): {(response.text or '')[:500]}"
            )
        # Prefer header Location; fall back to JSON "self"
        location: object | None = None
        headers_obj = getattr(response, "headers", None)
        if isinstance(headers_obj, Mapping):
            header_map: Mapping[str, object] = headers_obj
            loc_header = header_map.get("Location") or header_map.get("location")
            if isinstance(loc_header, str) and loc_header:
                location = loc_header
        if not isinstance(location, str):
            resp_payload = coerce_json_object(response.json())
            self_val = resp_payload.get("self")
            if isinstance(self_val, str) and self_val:
                location = self_val
        if not isinstance(location, str) or not location:
            raise AzureSpeechError("Azure Speech create response missing polling location")
        return location

    def _await_transcription(self, location: str) -> JSONObject:
        start = time.monotonic()
        while True:
            session = self._session(location)
            try:
                response = session.get(
                    location,
                    headers={"Ocp-Apim-Subscription-Key": self.config.key},
                    timeout=self.config.request_timeout_s,
                )
            except Exception as exc:
                raise AzureSpeechError(f"Polling transcription job failed: {exc}") from exc
            if response.status_code >= 400:
                raise AzureSpeechError(
                    f"Azure Speech poll failed (status={response.status_code}): {(response.text or '')[:500]}"
                )
            payload = coerce_json_object(response.json())
            status = payload.get("status")
            if isinstance(status, str) and status in {"Succeeded", "Failed"}:
                if status != "Succeeded":
                    error_message = _analyze_batch_error(payload)
                    raise AzureSpeechError(f"Transcription failed: {error_message}")
                return payload
            if time.monotonic() - start > self.config.poll_timeout_s:
                raise AzureSpeechError("Azure Speech polling timed out")
            time.sleep(self.config.poll_interval_s)

    def _resolve_content_url(self, location: str) -> str:
        files_url = f"{location}/files"
        session = self._session(files_url)
        try:
            response = session.get(
                files_url,
                headers={"Ocp-Apim-Subscription-Key": self.config.key},
                timeout=self.config.request_timeout_s,
            )
        except Exception as exc:
            raise AzureSpeechError(f"Failed to list transcription files: {exc}") from exc
        if response.status_code >= 400:
            raise AzureSpeechError(
                f"Azure Speech files request failed (status={response.status_code}): {(response.text or '')[:500]}"
            )
        payload = coerce_json_object(response.json())
        values = payload.get("values")
        files: Sequence[object] = values if isinstance(values, Sequence) else []
        for entry in files:
            if not isinstance(entry, Mapping):
                continue
            if entry.get("kind") != "Transcription":
                continue
            links_value = entry.get("links")
            links = links_value if isinstance(links_value, Mapping) else {}
            content_url = links.get("contentUrl") or links.get("content")
            if isinstance(content_url, str) and content_url:
                return content_url
        raise AzureSpeechError("Azure Speech files listing missing transcription content")

    def _download_json(self, url: str) -> JSONObject:
        session = self._session(url)
        try:
            response = session.get(url, timeout=self.config.request_timeout_s * 4)
        except Exception as exc:
            raise AzureSpeechError(f"Failed to download transcription JSON: {exc}") from exc
        if response.status_code >= 400:
            raise AzureSpeechError(
                f"Azure Speech transcription download failed (status={response.status_code}): {(response.text or '')[:500]}"
            )
        return coerce_json_object(response.json())

    def _extract_transcription(
        self,
        payload: Mapping[str, object],
        diarization: bool,
        location: str,
    ) -> AzureSpeechBatchResult:
        lines: list[str] = []
        meta = _json_payload(diarization=diarization, azure_transcription_url=location)
        recognized_value = payload.get("recognizedPhrases")
        recognized: Sequence[object] = (
            recognized_value if isinstance(recognized_value, Sequence) else []
        )
        max_end = 0.0
        seg_count = 0
        conf_sum = 0.0
        conf_count = 0
        speaker_ids: set[str] = set()

        for phrase in recognized:
            if not isinstance(phrase, Mapping):
                continue
            phrase_mp: Mapping[str, object] = phrase
            offset = _to_seconds(phrase_mp.get("offset") or phrase_mp.get("offsetInTicks"))
            duration = _to_seconds(phrase_mp.get("duration") or phrase_mp.get("durationInTicks"))
            max_end = max(max_end, offset + duration)
            seg_count += 1

            speaker = phrase_mp.get("speaker") or phrase_mp.get("channel")
            if speaker is not None:
                speaker_ids.add(str(speaker))

            nbest_value = phrase_mp.get("nBest")
            nbest: Sequence[object] = nbest_value if isinstance(nbest_value, Sequence) else []
            best_entry = nbest[0] if nbest else None
            text = ""
            if isinstance(best_entry, Mapping):
                best_mp: Mapping[str, object] = best_entry
                display = best_mp.get("display") or best_mp.get("lexical")
                if isinstance(display, str):
                    text = display.strip()
                confidence_value = best_mp.get("confidence")
                if isinstance(confidence_value, (int, float)):
                    conf_sum += float(confidence_value)
                    conf_count += 1
            elif isinstance(phrase_mp.get("display"), str):
                text = str(phrase_mp.get("display")).strip()

            if not text:
                continue
            minutes = int(offset // 60)
            seconds = int(offset % 60)
            if diarization and speaker is not None:
                lines.append(f"[{minutes:02d}:{seconds:02d}] SPK_{speaker}: {text}")
            else:
                lines.append(f"[{minutes:02d}:{seconds:02d}] {text}")

        if conf_count:
            meta["avg_confidence"] = conf_sum / conf_count
        if speaker_ids:
            meta["num_speakers"] = len(speaker_ids)
        meta["segments"] = seg_count

        if not lines:
            combined_value = payload.get("combinedRecognizedPhrases")
            combined: Sequence[object] = (
                combined_value if isinstance(combined_value, Sequence) else []
            )
            for item in combined:
                if not isinstance(item, Mapping):
                    continue
                item_mp: Mapping[str, object] = item
                display_text = item_mp.get("display") or item_mp.get("lexical")
                if isinstance(display_text, str):
                    candidate = display_text.strip()
                    if candidate:
                        lines.append(candidate)
            if not lines:
                simple_text = payload.get("text")
                if isinstance(simple_text, str) and simple_text.strip():
                    lines.append(simple_text.strip())

        text_output = "\n".join(lines) if lines else ""
        duration_value: float | None = max_end if max_end > 0 else None
        return AzureSpeechBatchResult(
            text=text_output,
            duration_s=duration_value,
            metadata=meta,
        )


__all__ = [
    "AzureSpeechError",
    "AzureSpeechHealthConfig",
    "AzureSpeechClientConfig",
    "AzureSpeechClient",
    "AzureSpeechBatchResult",
    "ensure_azure_speech_health",
]
