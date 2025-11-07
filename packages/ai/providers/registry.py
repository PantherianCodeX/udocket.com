from __future__ import annotations

# pyright: strict

"""Factory helpers for provider adapters."""

from collections.abc import Mapping

from .interfaces import ProviderAdapter
from .null import NullProvider
from ..types.identifiers import ProviderName


def default_adapters() -> Mapping[ProviderName, ProviderAdapter]:
    """Return a registry containing the null provider for tests."""

    provider = NullProvider()
    return {provider.name: provider}


__all__ = ["default_adapters"]
