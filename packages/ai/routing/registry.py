from __future__ import annotations

# pyright: strict

"""Typed routing registry definitions."""

from dataclasses import dataclass
from typing import Mapping

from ..types import AgentTask
from ..types.identifiers import ModelName, ProviderName, RouteName


@dataclass(slots=True, frozen=True)
class RouteBinding:
    """Resolved provider/model binding for a task."""

    task: AgentTask
    provider: ProviderName
    model: ModelName
    route_name: RouteName | None = None


RouteRegistry = Mapping[AgentTask, tuple[RouteBinding, ...]]

__all__ = ["RouteBinding", "RouteRegistry"]
