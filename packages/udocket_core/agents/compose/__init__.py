# pyright: strict

"""Compose agent support modules.

This package currently exposes stage profile metadata used by the UI when
rendering LLM configuration controls for the Compose tool. As the Compose agent
pipeline is implemented, additional helpers (configs, orchestrators, etc.) will
live here to keep the contract aligned with root AGENTS guidelines.
"""

from .profiles import COMPOSE_STAGE_PROFILES, ComposeStageProfile

__all__: list[str] = [
    "COMPOSE_STAGE_PROFILES",
    "ComposeStageProfile",
]
