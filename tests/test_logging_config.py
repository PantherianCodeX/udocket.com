from typing import Any, MutableMapping, cast

from pytest import MonkeyPatch

from apps.platform.config.settings.base import LOGGING as RAW_LOGGING  # pyright: ignore[reportUnknownVariableType]
from packages.udocket_core.agents import langgraph_orchestrator

LOGGING_CONFIG = cast(MutableMapping[str, Any], RAW_LOGGING)
LOGGERS_CONFIG_RAW = LOGGING_CONFIG.get("loggers")
assert isinstance(LOGGERS_CONFIG_RAW, MutableMapping)
LOGGERS_CONFIG = cast(MutableMapping[str, MutableMapping[str, Any]], LOGGERS_CONFIG_RAW)


def _get_logger_config(name: str) -> MutableMapping[str, Any]:
    logger_cfg = LOGGERS_CONFIG.get(name)
    assert isinstance(logger_cfg, MutableMapping)
    return logger_cfg


def test_auth_logger_inherits_console_handler() -> None:
    logger_cfg = _get_logger_config("apps.platform.accounts.auth")
    assert logger_cfg.get("propagate") is True
    assert "handlers" not in logger_cfg


def test_django_auth_logger_propagates() -> None:
    logger_cfg = _get_logger_config("django.contrib.auth")
    assert logger_cfg.get("propagate") is True


def test_langchain_logger_uses_inheritance() -> None:
    logger_cfg = _get_logger_config("langchain")
    assert logger_cfg.get("propagate") is True
    assert "handlers" not in logger_cfg


def test_enable_langgraph_debug_logging_sets_debug(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(langgraph_orchestrator, "_LANGGRAPH_DEBUG_INITIALIZED", False)
    import logging as std_logging

    root_logger = std_logging.getLogger()
    original_root_level = root_logger.level
    langgraph_logger = std_logging.getLogger("langgraph")
    original_langgraph_level = langgraph_logger.level
    try:
        root_logger.setLevel(std_logging.INFO)
        langgraph_logger.setLevel(std_logging.INFO)
        langgraph_orchestrator.enable_langgraph_debug_logging(force=True)
        assert root_logger.level <= std_logging.DEBUG
        assert langgraph_logger.level <= std_logging.DEBUG
    finally:
        root_logger.setLevel(original_root_level)
        langgraph_logger.setLevel(original_langgraph_level)
        monkeypatch.setattr(langgraph_orchestrator, "_LANGGRAPH_DEBUG_INITIALIZED", False)
