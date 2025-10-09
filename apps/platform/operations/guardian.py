# pyright: strict

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Final, Protocol, TypeAlias, cast

from django.utils import timezone

from apps.platform.artifacts.models import CaseArtifact
from apps.platform.operations.models import GuardianSettings
from apps.platform.operations.llm import (
    ensure_default_llm_configuration,
    get_llm_configuration,
    get_provider_secret_with_metadata,
)
from packages.udocket_core.agents.guardian_lib import GuardianAgent, GuardianConfig, GuardianVerdict
from packages.udocket_core.llm import LLMSettings, LLMStageAssignment, load_llm_settings
from packages.udocket_core.json_utils import (
    JSONObject,
    JSONValue,
    coerce_float,
    coerce_int,
    coerce_json_object,
    coerce_json_value,
    coerce_object_list,
    coerce_str,
    coerce_str_list,
    normalize_json_object,
    parse_json_value,
    read_json_object,
)
from packages.udocket_core.logging.context import LogContext, build_extra


MAX_CONTENT_CHARS: Final = 50000
MAX_HISTORY_ENTRIES: Final = 10
GUARDIAN_DEFAULTS_PATH: Final = Path(__file__).resolve().parents[3] / "config" / "guardian_defaults.json"


log = logging.getLogger("udocket.guardian")

JSONDict: TypeAlias = JSONObject
CredentialsMap: TypeAlias = dict[str, JSONDict]
InstructionList: TypeAlias = list[JSONDict]

_ENSURE_DEFAULT_LLM_CONFIGURATION = cast(
    Callable[..., dict[str, object] | None],
    ensure_default_llm_configuration,
)


class _GuardianReviewTask(Protocol):
    def delay(self, *, artifact_id: int) -> object:
        ...


@dataclass(frozen=True)
class GuardianContext:
    agent: GuardianAgent
    credentials: CredentialsMap
    configuration_id: str | None
    configuration_name: str | None
    provider_chain: list[str]
    model: str | None
    max_tokens: int
    temperature: float
    instructions: InstructionList

def _normalize_chain(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for raw in values:
        name = raw.strip().lower()
        if not name or name in result:
            continue
        result.append(name)
    return result


def _extract_guardian_stage(stage_map: Mapping[str, object]) -> JSONDict:
    for key in ("review", "policy", "guardian", "default"):
        value = stage_map.get(key)
        candidate = coerce_json_object(value)
        if candidate:
            return candidate
    # fall back to the first dict entry
    for value in stage_map.values():
        candidate = coerce_json_object(value)
        if candidate:
            return candidate
    return {}


@lru_cache(maxsize=1)
def _load_guardian_defaults() -> JSONDict:
    try:
        return read_json_object(GUARDIAN_DEFAULTS_PATH)
    except OSError:
        return {}


def _default_instructions() -> InstructionList:
    defaults = _load_guardian_defaults()
    return coerce_object_list(defaults.get("instructions"))


def _fetch_guardian_configuration(organization_id: str) -> JSONDict:
    return coerce_json_object(
        get_llm_configuration(
            organization_id=organization_id,
            config_id=None,
            target="guardian",
        )
    )


def _ensure_guardian_configuration(
    organization_id: str,
    *,
    llm_settings: LLMSettings,
) -> JSONDict:
    return coerce_json_object(
        _ENSURE_DEFAULT_LLM_CONFIGURATION(
            organization_id=organization_id,
            target="guardian",
            llm_settings=llm_settings,
        )
    )


def ensure_guardian_settings(organization_id: str | None) -> GuardianSettings | None:
    if not organization_id:
        return None
    settings_obj, _created = GuardianSettings.objects.get_or_create(
        organization_id=organization_id,
        defaults={"instructions": list(_default_instructions())},
    )
    return settings_obj


def get_guardian_instructions(organization_id: str | None) -> InstructionList:
    settings_obj = ensure_guardian_settings(organization_id)
    if not settings_obj:
        return _default_instructions()
    instructions_value: object = settings_obj.instructions or []
    normalized = coerce_object_list(instructions_value)
    return normalized or _default_instructions()


def save_guardian_instructions(organization_id: str | None, instructions: InstructionList) -> None:
    if not organization_id:
        return
    settings_obj = ensure_guardian_settings(organization_id)
    if settings_obj is None:
        return
    settings_obj.instructions = [dict(entry) for entry in instructions]
    settings_obj.save(update_fields=["instructions", "updated_at"])


def build_guardian_context(organization_id: str | None) -> GuardianContext | None:
    if not organization_id:
        log.info(
            "Guardian context skipped because no organization id was provided",
            extra=build_extra(
                event="guardian.context.missing_org",
                component="guardian.context",
            ),
        )
        return None

    context = LogContext.from_defaults(
        component="guardian.context",
        organization_id=organization_id,
    )
    log.debug(
        "Building Guardian context",
        extra=context.extra(event="guardian.context.build"),
    )
    llm_settings: LLMSettings = load_llm_settings()

    config_payload = _fetch_guardian_configuration(organization_id)
    if not config_payload:
        log.debug(
            "Guardian configuration missing; attempting to ensure defaults",
            extra=context.extra(event="guardian.context.ensure_default"),
        )
        config_payload = _ensure_guardian_configuration(
            organization_id,
            llm_settings=llm_settings,
        )
    if not config_payload:
        log.warning(
            "Guardian configuration is unavailable for organization",
            extra=context.extra(event="guardian.context.unconfigured"),
        )
        return None

    stage_map_raw = coerce_json_object(config_payload.get("stage_map"))
    review_cfg = _extract_guardian_stage(stage_map_raw)

    configured_chain = _normalize_chain(
        coerce_str_list(config_payload.get("provider_chain"), unique=False)
    )
    provider_chain = [name for name in configured_chain if llm_settings.provider(name)]
    if configured_chain and not provider_chain:
        log.warning(
            "Guardian provider override contains unknown providers",
            extra=context.extra(
                event="guardian.providers.unknown_configured",
                providers=configured_chain,
            ),
        )

    if not provider_chain:
        review_chain = _normalize_chain(
            coerce_str_list(review_cfg.get("provider"), unique=False)
        )
        review_filtered = [name for name in review_chain if llm_settings.provider(name)]
        if review_chain and not review_filtered:
            log.warning(
                "Guardian review stage references unknown providers",
                extra=context.extra(
                    event="guardian.providers.unknown_stage",
                    providers=review_chain,
                ),
            )
        provider_chain = review_filtered

    if not provider_chain:
        assignment: LLMStageAssignment | None = llm_settings.stage("guardian.review")
        assignment_chain = _normalize_chain(assignment.providers) if assignment else []
        assignment_filtered = [name for name in assignment_chain if llm_settings.provider(name)]
        if assignment_chain and not assignment_filtered:
            log.warning(
                "Guardian stage assignment references unknown providers",
                extra=context.extra(
                    event="guardian.providers.unknown_assignment",
                    providers=assignment_chain,
                ),
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
            "Guardian provider chain resolved to an empty list",
            extra=context.extra(event="guardian.providers.empty"),
        )

    options_raw = normalize_json_object(
        review_cfg.get("options"),
        drop_empty_keys=True,
        drop_nullish_values=True,
    )
    temperature = coerce_float(options_raw.get("temperature"), default=1.0) or 1.0

    max_tokens_value = coerce_int(review_cfg.get("max_tokens"), default=2048, minimum=1) or 2048

    guardian_config = GuardianConfig(
        provider_chain=list(provider_chain),
        model=coerce_str(review_cfg.get("model")),
        temperature=temperature,
        max_tokens=max_tokens_value,
    )

    agent = GuardianAgent(guardian_config, settings=llm_settings)

    credentials: CredentialsMap = {}
    for provider in guardian_config.provider_chain:
        secret = normalize_json_object(
            get_provider_secret_with_metadata(organization_id, provider)
        )
        if secret:
            credentials[provider] = secret
            log.debug(
                "Loaded Guardian provider credentials",
                extra=context.extra(
                    event="guardian.credentials.loaded",
                    provider=provider,
                ),
            )
        else:
            log.info(
                "Guardian provider credentials missing",
                extra=context.extra(
                    event="guardian.credentials.missing",
                    provider=provider,
                ),
            )

    instructions = get_guardian_instructions(organization_id)
    log.info(
        "Guardian context ready",
        extra=context.extra(
            event="guardian.context.ready",
            provider_chain=list(guardian_config.provider_chain),
            model=guardian_config.model,
            max_tokens=guardian_config.max_tokens,
            temperature=guardian_config.temperature,
            instruction_count=len(instructions),
        ),
    )

    return GuardianContext(
        agent=agent,
        credentials=credentials,
        configuration_id=coerce_str(config_payload.get("id")),
        configuration_name=coerce_str(config_payload.get("name")),
        provider_chain=list(guardian_config.provider_chain),
        model=guardian_config.model,
        max_tokens=guardian_config.max_tokens,
        temperature=guardian_config.temperature,
        instructions=instructions,
    )


def new_instruction_template() -> JSONDict:
    return {
        "id": uuid.uuid4().hex,
        "title": "",
        "text": "",
        "applies_to": [],
        "severity": "medium",
    }


def snapshot_artifact_for_guardian(artifact: CaseArtifact) -> JSONDict:
    metadata = normalize_json_object(artifact.metadata or {})
    case_id_value = getattr(artifact, "case_id", None)
    job_id_value = getattr(artifact, "job_id", None)
    org_value = getattr(artifact, "organization_id", None)
    artifact_context = LogContext.from_defaults(
        component="guardian.snapshot",
        case_id=str(case_id_value) if case_id_value else None,
        job_id=str(job_id_value) if job_id_value else None,
        artifact_id=int(artifact.id),
        organization_id=str(org_value) if org_value else None,
    )
    log.debug(
        "Preparing Guardian snapshot for artifact",
        extra=artifact_context.extra(
            event="guardian.artifact.snapshot",
            artifact_type=artifact.type,
        ),
    )
    payload: JSONDict = {
        "id": artifact.id,
        "case_id": artifact.case_id,
        "job_id": artifact.job_id,
        "type": artifact.type,
        "title": artifact.title,
        "path": artifact.path,
        "checksum": artifact.checksum,
        "metadata": metadata,
    }
    payload["source_kind"] = metadata.get("source_kind")
    payload["source_label"] = metadata.get("source_label")

    path_value = artifact.path
    if not path_value:
        payload["missing_path"] = True
        log.warning(
            "Guardian snapshot skipped because the artifact path is empty",
            extra=artifact_context.extra(event="guardian.artifact.missing_path"),
        )
        return payload

    path = Path(path_value)
    if not path.exists():
        payload["missing_file"] = True
        log.warning(
            "Guardian snapshot skipped because the artifact file is missing",
            extra=artifact_context.extra(
                event="guardian.artifact.missing_file",
                path=str(path),
            ),
        )
        return payload

    suffix = path.suffix.lower()
    try:
        if suffix in {".json", ".jsonl"}:
            text = path.read_text(encoding="utf-8")
            payload["content"] = text[:MAX_CONTENT_CHARS]
            parsed = parse_json_value(text)
            if parsed is not None:
                payload["parsed"] = parsed
            elif suffix == ".jsonl":
                line_items: list[JSONValue] = []
                for line in text.splitlines():
                    stripped = line.strip()
                    if not stripped:
                        continue
                    line_payload = parse_json_value(stripped)
                    if line_payload is not None:
                        line_items.append(line_payload)
                if line_items:
                    payload["parsed"] = line_items
        elif suffix in {".txt", ".md", ".markdown"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            payload["content"] = text[:MAX_CONTENT_CHARS]
        else:
            binary_snippet = path.read_bytes()[:4096]
            payload["content"] = binary_snippet.decode("utf-8", errors="ignore")
            payload["binary"] = True
    except Exception as exc:
        payload["read_error"] = str(exc)
        log.exception(
            "Guardian snapshot failed to read artifact",
            extra=artifact_context.extra(
                event="guardian.artifact.read_error",
                path=str(path),
            ),
        )
    else:
        log.debug(
            "Guardian snapshot prepared",
            extra=artifact_context.extra(
                event="guardian.artifact.snapshot_ready",
                has_content="content" in payload,
                has_parsed="parsed" in payload,
                binary=payload.get("binary", False),
            ),
        )
    return payload


def store_guardian_review(artifact: CaseArtifact, review: JSONDict) -> None:
    metadata = normalize_json_object(artifact.metadata or {})
    history = coerce_object_list(metadata.get("guardian_history"))
    history.append(dict(review))
    if len(history) > MAX_HISTORY_ENTRIES:
        history = history[-MAX_HISTORY_ENTRIES:]
    history_payload = [dict(entry) for entry in history]
    metadata["guardian_history"] = cast(list[JSONValue], history_payload)
    metadata["guardian_status"] = review.get("status")
    metadata["guardian_last_review"] = cast(JSONValue, dict(review))
    CaseArtifact.objects.filter(pk=artifact.pk).update(metadata=metadata)
    artifact.metadata = metadata
    case_id_value = getattr(artifact, "case_id", None)
    job_id_value = getattr(artifact, "job_id", None)
    org_value = getattr(artifact, "organization_id", None)
    review_context = LogContext.from_defaults(
        component="guardian.review.store",
        case_id=str(case_id_value) if case_id_value else None,
        job_id=str(job_id_value) if job_id_value else None,
        artifact_id=int(artifact.id),
        organization_id=str(org_value) if org_value else None,
    )
    log.info(
        "Stored Guardian review metadata",
        extra=review_context.extra(
            event="guardian.review.store",
            status=review.get("status"),
        ),
    )


def build_guardian_review_record(
    *,
    verdict: GuardianVerdict,
    status: str,
    artifact: CaseArtifact,
    context: GuardianContext,
    extra: JSONDict | None = None,
) -> JSONDict:
    record: JSONDict = {
        "status": status,
        "reviewed_at": timezone.now().isoformat(),
        "provider": verdict.provider,
        "model": verdict.model,
        "notes": verdict.notes,
        "violations": coerce_json_value(verdict.violations),
        "usage": coerce_json_object(verdict.usage),
        "configuration_id": context.configuration_id,
        "configuration_name": context.configuration_name,
        "artifact_id": artifact.id,
        "artifact_type": artifact.type,
        "remediation": coerce_json_value(verdict.remediation),
    }
    if extra:
        record.update(extra)
    return record


def enqueue_guardian_review(artifact_id: int) -> None:
    from apps.platform.operations.tasks import guardian_review_artifact

    task = cast(_GuardianReviewTask, guardian_review_artifact)
    task.delay(artifact_id=artifact_id)
    log.info(
        "Guardian review enqueued",
        extra=build_extra(
            event="guardian.review.enqueue",
            component="guardian.enqueue",
            artifact_id=artifact_id,
        ),
    )


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
