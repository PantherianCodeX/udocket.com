from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from config.paths import ensure_storage_root
from packages.udocket_core.config.paths import (
    resolve_analyze_defaults_path,
    resolve_llm_assignments_path,
    resolve_llm_providers_path,
)
from packages.udocket_core.llm.config import LLMConfigError, load_llm_settings


class RuntimeConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


log = logging.getLogger("apps.platform.runtime_checks")
_SKIP_COMMANDS: tuple[str, ...] = ("collectstatic", "makemigrations", "migrate")


def _current_management_command() -> str | None:
    if not sys.argv:
        return None
    executable = os.path.basename(sys.argv[0])
    if sys.argv[0].endswith("manage.py") and len(sys.argv) >= 2:
        return sys.argv[1]
    if executable in {"django-admin", "django-admin.py"} and len(sys.argv) >= 2:
        return sys.argv[1]
    return None


def should_skip_runtime_validation() -> bool:
    if os.environ.get("UDOCKET_SKIP_RUNTIME_CHECKS") == "1":
        log.warning("Runtime configuration validation skipped via UDOCKET_SKIP_RUNTIME_CHECKS")
        return True
    command = _current_management_command()
    if command and command in _SKIP_COMMANDS:
        log.info("Skipping runtime configuration validation for management command '%s'", command)
        return True
    return False


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise RuntimeConfigurationError(f"{label} not found: {path}")
    if not path.is_file():
        raise RuntimeConfigurationError(f"{label} must be a file: {path}")


def _verify_storage_root() -> Path:
    root = ensure_storage_root()
    if not root.exists():
        raise RuntimeConfigurationError(f"Storage root missing: {root}")
    if not root.is_dir():
        raise RuntimeConfigurationError(f"Storage root is not a directory: {root}")
    probe = root / ".udocket_write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as exc:
        raise RuntimeConfigurationError(f"Storage root is not writable: {root}") from exc
    return root


def validate_runtime_configuration() -> None:
    """Fail fast when core configuration or required artifacts are missing."""

    if should_skip_runtime_validation():
        return

    storage_root = _verify_storage_root()

    providers_path = resolve_llm_providers_path()
    assignments_path = resolve_llm_assignments_path()
    analyze_defaults_path = resolve_analyze_defaults_path()

    _require_file(providers_path, "LLM providers configuration")
    _require_file(assignments_path, "LLM assignments configuration")
    _require_file(analyze_defaults_path, "Analyze defaults configuration")

    try:
        load_llm_settings(providers_path=providers_path, assignments_path=assignments_path)
    except LLMConfigError as exc:
        raise RuntimeConfigurationError("LLM configuration is invalid") from exc

    log.info(
        "Runtime configuration validated",
        extra={
            "event": "runtime.success",
            "component": "runtime",
            "status": "ok",
            "storage_root": str(storage_root),
            "llm_providers_path": str(providers_path),
            "llm_assignments_path": str(assignments_path),
            "analyze_defaults_path": str(analyze_defaults_path),
        },
    )
