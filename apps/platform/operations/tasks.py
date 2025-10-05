# pyright: strict

from __future__ import annotations

import uuid
from collections.abc import Mapping

from apps.platform.operations.task_modules.analyze import analyze_job
from apps.platform.operations.task_modules.compose import compose_job
from apps.platform.operations.task_modules.guardian import guardian_review_artifact
from apps.platform.operations.task_modules.transcribe import transcribe_job
from apps.platform.operations.utils import update_job_meta

__all__ = [
    "transcribe_job",
    "compose_job",
    "analyze_job",
    "guardian_review_artifact",
    "_update_job_meta",
]


def _update_job_meta(
    case_id: str,
    organization_id: str | uuid.UUID | None,
    job_id: str,
    updates: Mapping[str, object],
) -> None:  # pragma: no cover - shim
    update_job_meta(case_id, organization_id, job_id, updates)
