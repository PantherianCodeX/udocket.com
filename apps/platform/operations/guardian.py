from __future__ import annotations

import json
import uuid
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from django.utils import timezone

from apps.platform.artifacts.models import CaseArtifact
from apps.platform.operations.models import GuardianSettings
from apps.platform.operations.llm import (
    ensure_default_llm_configuration,
    get_llm_configuration,
    get_provider_secret_with_metadata,
)
from packages.udocket_core.agents.guardian_lib import GuardianAgent, GuardianConfig, GuardianVerdict
from packages.udocket_core.llm import load_llm_settings


MAX_CONTENT_CHARS = 50000
MAX_HISTORY_ENTRIES = 10
GUARDIAN_DEFAULTS_PATH = Path(__file__).resolve().parents[3] / "config" / "guardian_defaults.json"


log = logging.getLogger("udocket.guardian")


@dataclass(frozen=True)
class GuardianContext:
    agent: GuardianAgent
    credentials: Dict[str, Dict[str, Any]]
    configuration_id: Optional[str]
    configuration_name: Optional[str]
    provider_chain: List[str]
    model: Optional[str]
    max_tokens: int
    temperature: float
    instructions: List[Dict[str, Any]]


def _normalize_chain(values: Iterable[str] | None) -> List[str]:
    result: List[str] = []
    if not values:
        return result
    for raw in values:
        name = (raw or "").strip().lower()
        if not name or name in result:
            continue
        result.append(name)
    return result


def _extract_guardian_stage(stage_map: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("review", "policy", "guardian", "default"):
        value = stage_map.get(key)
        if isinstance(value, dict):
            return value
    # fall back to the first dict entry
    for value in stage_map.values():
        if isinstance(value, dict):
            return value
    return {}


@lru_cache(maxsize=1)
def _load_guardian_defaults() -> Dict[str, Any]:
    try:
        payload = json.loads(GUARDIAN_DEFAULTS_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _default_instructions() -> List[Dict[str, Any]]:
    defaults = _load_guardian_defaults()
    instructions = defaults.get("instructions")
    if isinstance(instructions, list):
        normalized: List[Dict[str, Any]] = []
        for entry in instructions:
            if isinstance(entry, dict):
                normalized.append(dict(entry))
        return normalized
    return []


def ensure_guardian_settings(organization_id: Optional[str]) -> GuardianSettings | None:
    if not organization_id:
        return None
    settings_obj, _created = GuardianSettings.objects.get_or_create(
        organization_id=organization_id,
        defaults={"instructions": _default_instructions()},
    )
    return settings_obj


def get_guardian_instructions(organization_id: Optional[str]) -> List[Dict[str, Any]]:
    settings_obj = ensure_guardian_settings(organization_id)
    if not settings_obj:
        return _default_instructions()
    payload = settings_obj.instructions or []
    if not isinstance(payload, list):
        return _default_instructions()
    normalized: List[Dict[str, Any]] = []
    for entry in payload:
        if isinstance(entry, dict):
            normalized.append(dict(entry))
    return normalized or _default_instructions()


def save_guardian_instructions(organization_id: Optional[str], instructions: List[Dict[str, Any]]) -> None:
    if not organization_id:
        return
    settings_obj = ensure_guardian_settings(organization_id)
    if settings_obj is None:
        return
    settings_obj.instructions = instructions
    settings_obj.save(update_fields=["instructions", "updated_at"])


def build_guardian_context(organization_id: Optional[str]) -> Optional[GuardianContext]:
    if not organization_id:
        return None

    llm_settings = load_llm_settings()
    config_payload = get_llm_configuration(
        organization_id=organization_id,
        config_id=None,
        target="guardian",
    )
    if not config_payload:
        config_payload = ensure_default_llm_configuration(
            organization_id=organization_id,
            target="guardian",
            llm_settings=llm_settings,
        )
    if not config_payload:
        return None

    stage_map_raw = config_payload.get("stage_map") or {}
    review_cfg = _extract_guardian_stage(stage_map_raw)

    configured_chain = _normalize_chain(config_payload.get("provider_chain"))
    provider_chain = [name for name in configured_chain if llm_settings.provider(name)]
    if configured_chain and not provider_chain:
        log.warning(
            "guardian.provider.unknown_configured",
            extra={
                "organization_id": organization_id,
                "providers": configured_chain,
            },
        )

    if not provider_chain and review_cfg.get("provider"):
        review_chain = _normalize_chain([review_cfg.get("provider")])
        review_filtered = [name for name in review_chain if llm_settings.provider(name)]
        if review_chain and not review_filtered:
            log.warning(
                "guardian.provider.unknown_stage",
                extra={
                    "organization_id": organization_id,
                    "providers": review_chain,
                },
            )
        provider_chain = review_filtered

    if not provider_chain:
        assignment = llm_settings.stage("guardian.review")
        assignment_chain = _normalize_chain(assignment.providers if assignment else [])
        assignment_filtered = [name for name in assignment_chain if llm_settings.provider(name)]
        if assignment_chain and not assignment_filtered:
            log.warning(
                "guardian.provider.unknown_assignment",
                extra={
                    "organization_id": organization_id,
                    "providers": assignment_chain,
                },
            )
        provider_chain = assignment_filtered

    if not provider_chain:
        fallback = llm_settings.provider("azure")
        if fallback:
            provider_chain = [fallback.name]
        elif llm_settings.providers:
            provider_chain = [next(iter(llm_settings.providers.keys()))]

    if not provider_chain:
        log.warning(
            "guardian.provider_chain.empty",
            extra={"organization_id": organization_id},
        )

    options_raw = review_cfg.get("options") if isinstance(review_cfg.get("options"), dict) else {}
    temperature = 0.0
    if "temperature" in options_raw:
        try:
            temperature = float(options_raw["temperature"])
        except (TypeError, ValueError):
            temperature = 0.0

    try:
        max_tokens_value = int(review_cfg.get("max_tokens"))
    except (TypeError, ValueError):
        max_tokens_value = 2048
    if max_tokens_value <= 0:
        max_tokens_value = 2048

    guardian_config = GuardianConfig(
        provider_chain=list(provider_chain),
        model=str(review_cfg.get("model") or "") or None,
        temperature=temperature,
        max_tokens=max_tokens_value,
    )

    agent = GuardianAgent(guardian_config, settings=llm_settings)

    credentials: Dict[str, Dict[str, Any]] = {}
    for provider in guardian_config.provider_chain:
        secret = get_provider_secret_with_metadata(organization_id, provider)
        if secret:
            credentials[provider] = secret

    instructions = get_guardian_instructions(organization_id)

    return GuardianContext(
        agent=agent,
        credentials=credentials,
        configuration_id=config_payload.get("id"),
        configuration_name=config_payload.get("name"),
        provider_chain=list(guardian_config.provider_chain),
        model=guardian_config.model,
        max_tokens=guardian_config.max_tokens,
        temperature=guardian_config.temperature,
        instructions=instructions,
    )


def new_instruction_template() -> Dict[str, Any]:
    return {
        "id": uuid.uuid4().hex,
        "title": "",
        "text": "",
        "applies_to": [],
        "severity": "medium",
    }


def snapshot_artifact_for_guardian(artifact: CaseArtifact) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "id": artifact.id,
        "case_id": artifact.case_id,
        "job_id": artifact.job_id,
        "type": artifact.type,
        "title": artifact.title,
        "path": artifact.path,
        "checksum": artifact.checksum,
        "metadata": artifact.metadata or {},
        "source_kind": (artifact.metadata or {}).get("source_kind"),
        "source_label": (artifact.metadata or {}).get("source_label"),
    }

    path_value = artifact.path
    if not path_value:
        payload["missing_path"] = True
        return payload

    path = Path(path_value)
    if not path.exists():
        payload["missing_file"] = True
        return payload

    suffix = path.suffix.lower()
    try:
        if suffix in {".json", ".jsonl"}:
            text = path.read_text(encoding="utf-8")
            payload["content"] = text[:MAX_CONTENT_CHARS]
            try:
                payload["parsed"] = json.loads(text)
            except json.JSONDecodeError:
                # fall back to structured lines for JSONL
                if suffix == ".jsonl":
                    payload["parsed"] = [json.loads(line) for line in text.splitlines() if line.strip()]
        elif suffix in {".txt", ".md", ".markdown"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            payload["content"] = text[:MAX_CONTENT_CHARS]
        else:
            binary_snippet = path.read_bytes()[:4096]
            payload["content"] = binary_snippet.decode("utf-8", errors="ignore")
            payload["binary"] = True
    except Exception as exc:
        payload["read_error"] = str(exc)
    return payload


def store_guardian_review(artifact: CaseArtifact, review: Dict[str, Any]) -> None:
    metadata = dict(artifact.metadata or {})
    history: List[Dict[str, Any]] = list(metadata.get("guardian_history") or [])
    history.append(review)
    if len(history) > MAX_HISTORY_ENTRIES:
        history = history[-MAX_HISTORY_ENTRIES:]
    metadata["guardian_history"] = history
    metadata["guardian_status"] = review.get("status")
    metadata["guardian_last_review"] = review
    CaseArtifact.objects.filter(pk=artifact.pk).update(metadata=metadata)
    artifact.metadata = metadata


def build_guardian_review_record(
    *,
    verdict: GuardianVerdict,
    status: str,
    artifact: CaseArtifact,
    context: GuardianContext,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "status": status,
        "reviewed_at": timezone.now().isoformat(),
        "provider": verdict.provider,
        "model": verdict.model,
        "notes": verdict.notes,
        "violations": verdict.violations,
        "usage": verdict.usage,
        "configuration_id": context.configuration_id,
        "configuration_name": context.configuration_name,
        "artifact_id": artifact.id,
        "artifact_type": artifact.type,
        "remediation": verdict.remediation,
    }
    if extra:
        record.update(extra)
    return record


def enqueue_guardian_review(artifact_id: int) -> None:
    from apps.platform.operations.tasks import guardian_review_artifact

    guardian_review_artifact.delay(artifact_id=artifact_id)


__all__ = [
    "GuardianContext",
    "build_guardian_context",
    "snapshot_artifact_for_guardian",
    "store_guardian_review",
    "build_guardian_review_record",
    "enqueue_guardian_review",
    "get_guardian_instructions",
    "save_guardian_instructions",
    "new_instruction_template",
]
