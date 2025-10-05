from __future__ import annotations

# pyright: strict
import uuid
from collections.abc import Mapping

from apps.platform.operations.task_modules.analyze import analyze_job
from apps.platform.operations.task_modules.compose import compose_job
from apps.platform.operations.guardian import build_guardian_context
from apps.platform.operations.audit import emit as audit_emit
from apps.platform.operations.channels import send_case_update, send_job_update
from apps.platform.operations.llm import (
    ensure_default_llm_configuration,
    get_llm_configuration,
    get_provider_secret_with_metadata,
)
from apps.platform.operations.services import collect_requested_providers
from apps.platform.operations.task_modules.guardian import guardian_review_artifact
from apps.platform.operations.task_modules.transcribe import transcribe_job
from apps.platform.operations.utils import update_job_meta
from apps.platform.operations.runtime import emit_job_update
from packages.udocket_core.agents import AnalyzeAgent
from packages.udocket_core.llm.config import load_llm_settings

__all__ = [
    "transcribe_job",
    "compose_job",
    "analyze_job",
    "guardian_review_artifact",
    "build_guardian_context",
    "_emit_job_update",
    "send_case_update",
    "send_job_update",
    "audit_emit",
    "load_llm_settings",
    "get_llm_configuration",
    "ensure_default_llm_configuration",
    "get_provider_secret_with_metadata",
    "collect_requested_providers",
    "AnalyzeAgent",
    "_update_job_meta",
]

_emit_job_update = emit_job_update


def _update_job_meta(
    case_id: str,
    organization_id: str | uuid.UUID | None,
    job_id: str,
    updates: Mapping[str, object],
) -> None:  # pragma: no cover - shim
    update_job_meta(case_id, organization_id, job_id, updates)
