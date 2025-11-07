# pyright: strict

"""Typed routing registry definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from packages.ai.types import AgentTask

if TYPE_CHECKING:
    from packages.ai.types.identifiers import ModelName, ProviderName, RouteName


@dataclass(slots=True, frozen=True)
class RouteBinding:
    """Resolved provider/model binding for a task."""

    task: AgentTask
    provider: ProviderName
    model: ModelName
    route_name: RouteName | None = None


RouteRegistry = dict[AgentTask, tuple[RouteBinding, ...]]

__all__ = ["RouteBinding", "RouteRegistry"]
