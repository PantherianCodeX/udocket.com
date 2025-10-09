from __future__ import annotations

# pyright: strict

import json
import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Optional

from packages.udocket_core.json_utils import (
    JSONObject,
    JSONValue,
    coerce_json_object,
    coerce_json_value,
    coerce_str,
    parse_json_object,
)
from packages.udocket_core.llm import LLMSettings, load_llm_settings
from packages.udocket_core.llm.config import LLMProvider
from packages.udocket_core.llm.runtime import (
    ChatClient,
    ChatClientError,
    build_chat_client,
    build_provider_runtime_config,
)
from .common.llm_health import ensure_llm_client_health
from packages.udocket_core.logging.context import LogContext

logger = logging.getLogger("udocket.guardian")


def _normalize_providers(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for raw in values:
        name = (raw or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        output.append(name)
    return output


def _select_model_name(provider: LLMProvider, preferred: Optional[str]) -> Optional[str]:
    if preferred:
        normalized = preferred.strip()
        if normalized and normalized in provider.models:
            return normalized

    # Prefer default-enabled models
    for model in provider.models.values():
        if model.default_enabled:
            return model.name

    # Fall back to the first declared model if available
    for model in provider.models.values():
        return model.name

    return None


@dataclass(frozen=True)
class GuardianConfig:
    provider_chain: list[str] = field(default_factory=lambda: ["azure"])
    model: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 2048
    retry_attempts: int = 1


@dataclass(frozen=True)
class GuardianVerdict:
    approved: bool
    provider: Optional[str]
    model: Optional[str]
    notes: Optional[str]
    violations: list[JSONObject]
    usage: dict[str, int]
    raw: JSONObject
    remediation: Optional[str]


class GuardianRejection(RuntimeError):
    def __init__(self, verdict: GuardianVerdict, message: Optional[str] = None) -> None:
        detail = message or "Guardian rejected generated output"
        super().__init__(detail)
        self.verdict = verdict


def _usage_dict(payload: Mapping[str, object]) -> dict[str, int]:
    collector: dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = payload.get(key)
        if isinstance(value, int):
            collector[key] = value
    return collector


class GuardianAgent:
    """Policy guard agent that validates generated artifacts before release."""

    def __init__(
        self,
        config: Optional[GuardianConfig] = None,
        *,
        settings: Optional[LLMSettings] = None,
    ) -> None:
        self.config = config or GuardianConfig()
        self.settings = settings or load_llm_settings()
        self.logger = logger
        self._log_context = LogContext.from_defaults(component="guardian.agent")

    def review(
        self,
        *,
        case_id: str,
        job_id: str,
        artifact_kind: str,
        payload: Mapping[str, JSONValue],
        providers: Optional[Iterable[str]] = None,
        model: Optional[str] = None,
        options: Optional[Mapping[str, JSONValue]] = None,
        provider_credentials: Optional[Mapping[str, Mapping[str, JSONValue]]]
        = None,
        context: Optional[Mapping[str, JSONValue]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> GuardianVerdict:
        provider_credentials = provider_credentials or {}
        provider_order = _normalize_providers(
            providers
            if providers is not None
            else self.config.provider_chain
        )
        if not provider_order:
            provider_order = list(self.config.provider_chain or ["azure"])

        merged_options: dict[str, JSONValue] = {}
        if options:
            for key, value in options.items():
                merged_options[key] = coerce_json_value(value)
        selected_model = model or self.config.model
        configured_max_tokens = max_tokens or self.config.max_tokens
        configured_temperature = (
            self.config.temperature if temperature is None else temperature
        )

        stage_assignment = self.settings.stage("guardian.review")
        if stage_assignment:
            if not provider_order:
                provider_order = _normalize_providers(stage_assignment.providers)
            if not selected_model:
                selected_model = stage_assignment.model or selected_model
            for key, value in stage_assignment.options.items():
                merged_options[key] = value

        last_verdict: Optional[GuardianVerdict] = None
        attempts = max(1, int(self.config.retry_attempts))

        call_context = self._log_context.bind(
            case_id=case_id or None,
            job_id=job_id or None,
            artifact_kind=artifact_kind,
        )
        self.logger.info(
            "Guardian agent review started",
            extra=call_context.extra(
                event="guardian.agent.review.start",
                provider_chain=list(provider_order),
                requested_model=selected_model,
                max_tokens=configured_max_tokens,
                temperature=configured_temperature,
                retry_attempts=attempts,
            ),
        )

        for provider in provider_order:
            provider_meta = self.settings.provider(provider)
            if provider_meta is None:
                self.logger.warning(
                    "Guardian provider reference is missing from settings",
                    extra=call_context.extra(
                        event="guardian.agent.provider.missing",
                        provider=provider,
                    ),
                )
                continue

            provider_context = call_context.bind(provider=provider_meta.name)
            provider_model_name = _select_model_name(
                provider_meta,
                selected_model or (stage_assignment.model if stage_assignment else None),
            )
            if not provider_model_name:
                self.logger.warning(
                    "Guardian provider has no model configured",
                    extra=provider_context.extra(
                        event="guardian.agent.provider.no_model",
                    ),
                )
                continue
            provider_context = provider_context.bind(model=provider_model_name)
            self.logger.debug(
                "Evaluating Guardian provider",
                extra=provider_context.extra(event="guardian.agent.provider.start"),
            )

            credential_payload = provider_credentials.get(provider)
            runtime = None
            client: Optional[ChatClient] = None
            try:
                runtime_options = dict(merged_options) if merged_options else None
                credential_dict = (
                    dict(credential_payload) if credential_payload is not None else None
                )
                runtime = build_provider_runtime_config(
                    provider=provider_meta,
                    model_name=provider_model_name,
                    credential_payload=credential_dict,
                    options=runtime_options,
                )
                client = build_chat_client(provider_runtime=runtime)
            except ChatClientError as exc:
                self.logger.exception(
                    "Guardian provider initialization failed",
                    extra=provider_context.extra(
                        event="guardian.agent.provider.init_failed",
                        error=str(exc),
                    ),
                )
                continue

            try:
                self.logger.debug(
                    "Running Guardian provider health check",
                    extra=provider_context.extra(
                        event="guardian.agent.provider.health_check",
                    ),
                )
                ensure_llm_client_health(
                    client,
                    stage="guardian.review",
                    provider=provider_meta.name,
                    model=provider_model_name,
                    logger=self.logger,
                    raise_error=lambda message: ChatClientError(message),
                )
            except ChatClientError as exc:
                self.logger.error(
                    "Guardian provider health check failed",
                    extra=provider_context.extra(
                        event="guardian.agent.provider.health_failed",
                        error=str(exc),
                    ),
                )
                continue

            for attempt in range(attempts):
                system_prompt = (
                    "You are the uDocket Guardian, a compliance reviewer for AI outputs."
                    " Evaluate the provided artifact for unauthorized legal advice, interpretations,"
                    " form-selection guidance, or other policy violations."
                    " Respond with strict JSON containing the fields:"
                    " approved (bool), notes (string), remediation (string), and"
                    " violations (array of objects with category, message, severity, citation, recommendation)."
                    " Citations must reference transcript timestamps, artifact sections, or other verifiable anchors."
                    " Provide remediation summarizing next safe steps when violations exist."
                    " Approve only when no violations are present."
                )

                effective_context: dict[str, JSONValue] = {}
                if context:
                    effective_context.update(context)
                if attempt > 0 and last_verdict is not None:
                    effective_context.setdefault("guardian_feedback", last_verdict.raw)

                review_payload: JSONObject = {
                    "case_id": case_id,
                    "job_id": job_id,
                    "artifact_kind": artifact_kind,
                    "artifact": coerce_json_object(payload),
                    "context": effective_context,
                    "guardrails": {
                        "disallow_legal_advice": True,
                        "disallow_interpretation": True,
                        "disallow_form_selection": True,
                        "require_privacy": True,
                    },
                }

                try:
                    self.logger.debug(
                        "Submitting Guardian review request to provider",
                        extra=provider_context.extra(
                            event="guardian.agent.request",
                            attempt=attempt + 1,
                            temperature=configured_temperature,
                            max_tokens=max(256, configured_max_tokens),
                        ),
                    )
                    content, usage = client.chat(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": json.dumps(review_payload, ensure_ascii=False)},
                        ],
                        temperature=configured_temperature,
                        max_tokens=max(256, configured_max_tokens),
                    )
                except ChatClientError as exc:
                    self.logger.exception(
                        "Guardian provider request failed",
                        extra=provider_context.extra(
                            event="guardian.agent.request_failed",
                            error=str(exc),
                            attempt=attempt + 1,
                        ),
                    )
                    continue

                verdict = self._parse_verdict(
                    raw_response=content,
                    provider=provider_meta.name,
                    model=runtime.model.name if runtime and runtime.model else provider_model_name,
                    usage=_usage_dict(usage),
                )
                self.logger.info(
                    "Guardian provider returned verdict",
                    extra=provider_context.extra(
                        event="guardian.agent.verdict",
                        attempt=attempt + 1,
                        approved=verdict.approved,
                        violation_count=len(verdict.violations),
                    ),
                )
                if verdict.approved or attempt == attempts - 1:
                    return verdict
                self.logger.debug(
                    "Guardian provider verdict rejected; retrying if attempts remain",
                    extra=provider_context.extra(
                        event="guardian.agent.retry",
                        attempt=attempt + 1,
                    ),
                )
                last_verdict = verdict

        self.logger.error(
            "Guardian agent could not complete review with any provider",
            extra=call_context.extra(
                event="guardian.agent.review.exhausted",
                provider_chain=list(provider_order),
            ),
        )
        raise RuntimeError("Guardian validation could not contact any provider")

    def _parse_verdict(
        self,
        *,
        raw_response: Optional[str],
        provider: Optional[str],
        model: Optional[str],
        usage: dict[str, int],
    ) -> GuardianVerdict:
        if not raw_response:
            raise RuntimeError("Guardian returned no response")
        start = raw_response.find("{")
        end = raw_response.rfind("}")
        if start == -1 or end == -1:
            raise RuntimeError("Guardian response was not JSON")
        try:
            payload = parse_json_object(
                raw_response[start : end + 1],
                context="guardian agent response",
            )
        except ValueError as exc:
            raise RuntimeError(f"Guardian response parse error: {exc}") from exc

        approved = bool(payload.get("approved"))
        notes = coerce_str(payload.get("notes"))
        remediation: Optional[str] = None
        raw_remediation = payload.get("remediation") or payload.get("remediation_instructions")
        if raw_remediation:
            remediation = str(raw_remediation)
        violations_raw = payload.get("violations")
        violations: list[JSONObject] = []
        if isinstance(violations_raw, list):
            for entry in violations_raw:
                if isinstance(entry, dict):
                    entry_obj = coerce_json_object(entry)
                    category = coerce_str(entry_obj.get("category")) or "uncategorized"
                    severity = coerce_str(entry_obj.get("severity")) or "medium"
                    message = coerce_str(entry_obj.get("message")) or ""
                    citation = entry_obj.get("citation")
                    recommendation = entry_obj.get("recommendation")
                    violation_entry: JSONObject = {
                        "category": category,
                        "severity": severity,
                        "message": message,
                    }
                    if citation is not None:
                        violation_entry["citation"] = citation
                    if recommendation is not None:
                        violation_entry["recommendation"] = recommendation
                    violations.append(violation_entry)
                elif isinstance(entry, str):
                    violations.append(
                        {
                            "category": "unspecified",
                            "severity": "medium",
                            "message": entry,
                        }
                    )

        return GuardianVerdict(
            approved=approved,
            provider=provider,
            model=model,
            notes=notes,
            violations=violations,
            usage=usage,
            raw=payload,
            remediation=str(remediation) if remediation else None,
        )


__all__ = [
    "GuardianAgent",
    "GuardianConfig",
    "GuardianVerdict",
    "GuardianRejection",
]
