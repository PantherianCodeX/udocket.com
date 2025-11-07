from __future__ import annotations

"""Import-forwarding shims for Celery task modules.

The long-term goal is to relocate the task implementations into the automation
tree. Until then we lazily re-export the existing platform task modules so that
new import paths are already available to callers and tests.
"""

# pyright: strict
from importlib import import_module
from typing import TYPE_CHECKING, Any, Final

__all__ = [
    "analyze_job",
    "compose_job",
    "guardian_review_artifact",
    "recover_stale_jobs",
    "transcribe_job",
]

_TARGET_MODULE: Final[str] = "apps.platform.operations.task_modules"
_EXPORTED_NAMES: Final[set[str]] = set(__all__)


if TYPE_CHECKING:
    from apps.platform.operations.task_modules import (
        analyze_job,
        compose_job,
        guardian_review_artifact,
        recover_stale_jobs,
        transcribe_job,
    )


def __getattr__(name: str) -> Any:
    if name not in _EXPORTED_NAMES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(_TARGET_MODULE)
    value = getattr(module, name)
    globals()[name] = value
    return value
