from __future__ import annotations

# pyright: strict
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .llm_profiles import (
    DEFAULT_LAWYER_TEMPERATURE,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_TEMPERATURE,
)

logger = logging.getLogger("udocket.compose.config")

DOC_TEMPLATE_ENV = "COMPOSE_DOCX_TEMPLATE"
DEFAULT_PROVIDER_CHAIN: list[str] = ["azure"]
DEFAULT_PROMPT_CONFIG_ENV = "COMPOSE_PROMPT_CONFIG"


def _truthy(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _safe_float(value: str | None, fallback: float) -> float:
    try:
        return float(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


def _safe_int(value: str | None, fallback: int) -> int:
    try:
        return int(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


def normalize_provider_chain(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in values:
        name = (raw or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _resolve_prompt_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Compose prompt config missing at {resolved}")
    return resolved


def _default_prompt_config_path() -> Path:
    env_path = os.getenv(DEFAULT_PROMPT_CONFIG_ENV)
    if env_path:
        return _resolve_prompt_path(Path(env_path))
    package_path = Path(__file__).resolve().parent.parent.parent / "config" / "compose_prompts.yaml"
    return _resolve_prompt_path(package_path)


@dataclass(slots=True)
class ComposeConfig:
    provider_chain: list[str] = field(default_factory=lambda: list(DEFAULT_PROVIDER_CHAIN))
    temperature: float = DEFAULT_TEMPERATURE
    lawyer_temperature: float = DEFAULT_LAWYER_TEMPERATURE
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    max_client_attempts: int = 2
    max_lawyer_attempts: int = 2
    min_timestamp_references: int = 3
    qa_enforced: bool = True
    debug: bool = False
    doc_template_path: Path | None = None
    enable_editor: bool = True
    client_editor_model: str | None = None
    lawyer_editor_model: str | None = None
    qa_iteration_limit: int = 3
    locale: str = "en-CA"
    prompt_config_path: Path = field(default_factory=_default_prompt_config_path)
    llm_retry_attempts: int = 2
    llm_retry_initial_delay_seconds: float = 2.0
    enable_async: bool = False

    @classmethod
    def from_env(cls) -> ComposeConfig:
        providers_env = os.getenv("COMPOSE_PROVIDER_CHAIN", "")
        providers = (
            normalize_provider_chain(providers_env.split(","))
            if providers_env
            else list(DEFAULT_PROVIDER_CHAIN)
        )
        temperature = _safe_float(os.getenv("COMPOSE_TEMPERATURE"), DEFAULT_TEMPERATURE)
        lawyer_temperature = _safe_float(
            os.getenv("COMPOSE_LAWYER_TEMPERATURE"), DEFAULT_LAWYER_TEMPERATURE
        )
        max_tokens = _safe_int(os.getenv("COMPOSE_MAX_OUTPUT_TOKENS"), DEFAULT_MAX_OUTPUT_TOKENS)
        max_client_attempts = _safe_int(os.getenv("COMPOSE_MAX_CLIENT_ATTEMPTS"), 2)
        max_lawyer_attempts = _safe_int(os.getenv("COMPOSE_MAX_LAWYER_ATTEMPTS"), 2)
        min_timestamp_references = _safe_int(os.getenv("COMPOSE_MIN_TIMESTAMP_REFERENCES"), 3)
        qa_enforced = _truthy(os.getenv("COMPOSE_QA_ENFORCED"), True)
        debug = _truthy(os.getenv("DEBUG"), False)
        enable_editor = _truthy(os.getenv("COMPOSE_ENABLE_EDITOR"), True)
        client_editor_model = os.getenv("COMPOSE_CLIENT_EDITOR_MODEL") or None
        lawyer_editor_model = os.getenv("COMPOSE_LAWYER_EDITOR_MODEL") or None
        qa_iteration_limit = _safe_int(os.getenv("COMPOSE_QA_MAX_ITERATIONS"), 3)
        locale = os.getenv("COMPOSE_LOCALE", "en-CA")
        template_env = os.getenv(DOC_TEMPLATE_ENV)
        template_path = Path(template_env).resolve() if template_env else None
        if template_path and not template_path.exists():
            logger.warning("compose.doc_template.missing", extra={"path": str(template_path)})
            template_path = None
        if not providers:
            providers = list(DEFAULT_PROVIDER_CHAIN)
        prompt_config_path = _default_prompt_config_path()
        llm_retry_attempts = max(0, _safe_int(os.getenv("COMPOSE_LLM_RETRY_ATTEMPTS"), 2))
        llm_retry_initial_delay_seconds = max(
            0.5,
            _safe_float(os.getenv("COMPOSE_LLM_RETRY_DELAY_SECONDS"), 2.0),
        )
        enable_async = _truthy(os.getenv("COMPOSE_ENABLE_ASYNC"), False)
        return cls(
            provider_chain=providers,
            temperature=temperature,
            lawyer_temperature=lawyer_temperature,
            max_output_tokens=max_tokens,
            max_client_attempts=max_client_attempts,
            max_lawyer_attempts=max_lawyer_attempts,
            min_timestamp_references=min_timestamp_references,
            qa_enforced=qa_enforced,
            debug=debug,
            doc_template_path=template_path,
            enable_editor=enable_editor,
            client_editor_model=client_editor_model,
            lawyer_editor_model=lawyer_editor_model,
            qa_iteration_limit=qa_iteration_limit,
            locale=locale,
            prompt_config_path=prompt_config_path,
            llm_retry_attempts=llm_retry_attempts,
            llm_retry_initial_delay_seconds=llm_retry_initial_delay_seconds,
            enable_async=enable_async,
        )


__all__ = [
    "ComposeConfig",
    "DEFAULT_PROVIDER_CHAIN",
    "DOC_TEMPLATE_ENV",
    "normalize_provider_chain",
]
