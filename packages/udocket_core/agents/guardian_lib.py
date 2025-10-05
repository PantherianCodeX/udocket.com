from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from packages.udocket_core.json_utils import parse_json_object
from packages.udocket_core.llm import LLMSettings, load_llm_settings
from packages.udocket_core.llm.config import LLMProvider, LLMProviderModel
from packages.udocket_core.llm.runtime import (
    ChatClient,
    ChatClientError,
    build_chat_client,
    build_provider_runtime_config,
)

logger = logging.getLogger("udocket.guardian")


def _normalize_providers(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    output: List[str] = []
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
        if isinstance(model, LLMProviderModel) and model.default_enabled:
            return model.name

    # Fall back to the first declared model if available
    for model in provider.models.values():
        if isinstance(model, LLMProviderModel):
            return model.name

    return None


@dataclass
class GuardianConfig:
    provider_chain: List[str] = field(default_factory=lambda: ["azure"])
    model: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 2048
    retry_attempts: int = 1


@dataclass
class GuardianVerdict:
    approved: bool
    provider: Optional[str]
    model: Optional[str]
    notes: Optional[str]
    violations: List[Dict[str, Any]]
    usage: Dict[str, int]
    raw: Dict[str, Any]
    remediation: Optional[str]


class GuardianRejection(RuntimeError):
    def __init__(self, verdict: GuardianVerdict, message: Optional[str] = None) -> None:
        detail = message or "Guardian rejected generated output"
        super().__init__(detail)
        self.verdict = verdict


def _usage_dict(payload: Dict[str, Any]) -> Dict[str, int]:
    collector: Dict[str, int] = {}
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

    def review(
        self,
        *,
        case_id: str,
        job_id: str,
        artifact_kind: str,
        payload: Dict[str, Any],
        providers: Optional[Iterable[str]] = None,
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        provider_credentials: Optional[Dict[str, Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
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

        default_options = dict(options or {})
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
            default_options = {
                **(stage_assignment.options or {}),
                **default_options,
            }

        last_verdict: Optional[GuardianVerdict] = None
        attempts = max(1, int(self.config.retry_attempts))

        for provider in provider_order:
            provider_meta = self.settings.provider(provider)
            if provider_meta is None:
                continue

            provider_model_name = _select_model_name(
                provider_meta,
                selected_model or (stage_assignment.model if stage_assignment else None),
            )
            if not provider_model_name:
                self.logger.warning(
                    "guardian.provider.no_model",
                    extra={
                        "provider": provider_meta.name,
                        "job_id": job_id,
                        "case_id": case_id,
                    },
                )
                continue

            credential_payload = provider_credentials.get(provider)
            runtime = None
            client: Optional[ChatClient] = None
            try:
                runtime = build_provider_runtime_config(
                    provider=provider_meta,
                    model_name=provider_model_name,
                    credential_payload=credential_payload,
                    options=default_options or None,
                )
                client = build_chat_client(provider_runtime=runtime)
            except ChatClientError as exc:
                self.logger.exception(
                    "guardian.provider.init_failed",
                    extra={
                        "provider": provider_meta.name,
                        "model": provider_model_name,
                        "job_id": job_id,
                        "case_id": case_id,
                        "error": str(exc),
                    },
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

                effective_context = dict(context or {})
                if attempt > 0 and last_verdict is not None:
                    effective_context.setdefault("guardian_feedback", last_verdict.raw)

                review_payload = {
                    "case_id": case_id,
                    "job_id": job_id,
                    "artifact_kind": artifact_kind,
                    "artifact": payload,
                    "context": effective_context,
                    "guardrails": {
                        "disallow_legal_advice": True,
                        "disallow_interpretation": True,
                        "disallow_form_selection": True,
                        "require_privacy": True,
                    },
                }

                try:
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
                        "guardian.provider.request_failed",
                        extra={
                            "provider": provider_meta.name,
                            "model": provider_model_name,
                            "job_id": job_id,
                            "case_id": case_id,
                            "error": str(exc),
                            "attempt": attempt + 1,
                        },
                    )
                    continue

                verdict = self._parse_verdict(
                    raw_response=content,
                    provider=provider_meta.name,
                    model=runtime.model.name if runtime and runtime.model else provider_model_name,
                    usage=_usage_dict(usage),
                )
                if verdict.approved or attempt == attempts - 1:
                    return verdict
                last_verdict = verdict

        raise RuntimeError("Guardian validation could not contact any provider")

    def _parse_verdict(
        self,
        *,
        raw_response: Optional[str],
        provider: Optional[str],
        model: Optional[str],
        usage: Dict[str, int],
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
        notes = payload.get("notes") if isinstance(payload, Mapping) else None
        remediation: Optional[str] = None
        raw_remediation = payload.get("remediation") or payload.get("remediation_instructions")
        if raw_remediation:
            remediation = str(raw_remediation)
        violations_raw = payload.get("violations")
        violations: List[Dict[str, Any]] = []
        if isinstance(violations_raw, list):
            for entry in violations_raw:
                if isinstance(entry, dict):
                    category = str(entry.get("category") or "uncategorized")
                    severity = str(entry.get("severity") or "medium")
                    message = str(entry.get("message") or "")
                    citation = entry.get("citation")
                    recommendation = entry.get("recommendation")
                    violation_entry: Dict[str, Any] = {
                        "category": category,
                        "severity": severity,
                        "message": message,
                    }
                    if citation:
                        violation_entry["citation"] = citation
                    if recommendation:
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
            notes=str(notes) if notes else None,
            violations=violations,
            usage=usage,
            raw=payload if isinstance(payload, dict) else {"raw": raw_response},
            remediation=str(remediation) if remediation else None,
        )


__all__ = [
    "GuardianAgent",
    "GuardianConfig",
    "GuardianVerdict",
    "GuardianRejection",
]
