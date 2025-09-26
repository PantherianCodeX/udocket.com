import logging

from apps.platform.config.settings.base import LOGGING
from packages.udocket_core.agents import langgraph_orchestrator


def test_auth_logger_inherits_console_handler():
    logger_cfg = LOGGING["loggers"].get("apps.platform.accounts.auth")
    assert logger_cfg is not None
    assert logger_cfg.get("propagate") is True
    assert "handlers" not in logger_cfg


def test_django_auth_logger_propagates():
    logger_cfg = LOGGING["loggers"].get("django.contrib.auth")
    assert logger_cfg is not None
    assert logger_cfg.get("propagate") is True


def test_langchain_logger_uses_inheritance():
    logger_cfg = LOGGING["loggers"].get("langchain")
    assert logger_cfg is not None
    assert logger_cfg.get("propagate") is True
    assert "handlers" not in logger_cfg


def test_enable_langgraph_debug_logging_sets_debug(monkeypatch):
    monkeypatch.setattr(langgraph_orchestrator, "_LANGGRAPH_DEBUG_INITIALIZED", False)
    root_logger = logging.getLogger()
    original_root_level = root_logger.level
    langgraph_logger = logging.getLogger("langgraph")
    original_langgraph_level = langgraph_logger.level
    try:
        root_logger.setLevel(logging.INFO)
        langgraph_logger.setLevel(logging.INFO)
        langgraph_orchestrator.enable_langgraph_debug_logging(force=True)
        assert root_logger.level <= logging.DEBUG
        assert langgraph_logger.level <= logging.DEBUG
    finally:
        root_logger.setLevel(original_root_level)
        langgraph_logger.setLevel(original_langgraph_level)
        monkeypatch.setattr(langgraph_orchestrator, "_LANGGRAPH_DEBUG_INITIALIZED", False)
