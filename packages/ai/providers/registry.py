# pyright: strict

"""Factory helpers for provider adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.ai.providers.azure_openai import AzureOpenAIAdapter
from packages.ai.providers.null import NullProvider
from packages.ai.providers.settings import AzureOpenAIConfig
from packages.ai.types import AllowedRegion
from packages.ai.types.identifiers import ProviderName

if TYPE_CHECKING:
    from packages.ai.config import AISettings, ProviderAccount
    from packages.ai.providers.interfaces import ProviderAdapter
    from packages.ai.safety.egress import EgressPolicy
    from packages.ai.safety.residency import ResidencyPolicy
    from packages.ai.secret import SecretSource


def default_adapters() -> dict[ProviderName, ProviderAdapter]:
    """Return a registry containing the null provider for tests."""
    provider = NullProvider()
    return {provider.name: provider}


def adapters_from_settings(
    settings: AISettings,
    *,
    secret_source: SecretSource,
    residency_policy: ResidencyPolicy,
    egress_policy: EgressPolicy,
) -> dict[ProviderName, ProviderAdapter]:
    """Build provider adapters from AI settings."""
    adapters: dict[ProviderName, ProviderAdapter] = {}
    for account in settings.providers:
        adapter = _build_adapter_for_account(
            account,
            secret_source=secret_source,
            residency_policy=residency_policy,
            egress_policy=egress_policy,
        )
        if adapter is not None:
            adapters[adapter.name] = adapter
    if not adapters:
        return default_adapters()
    return adapters


def _build_adapter_for_account(
    account: ProviderAccount,
    *,
    secret_source: SecretSource,
    residency_policy: ResidencyPolicy,
    egress_policy: EgressPolicy,
) -> ProviderAdapter | None:
    provider_name = ProviderName(account.name)
    allowed_regions = account.allowed_regions or (AllowedRegion(region=account.region),)
    if account.provider_type in {"azure-openai", "azure"}:
        config = AzureOpenAIConfig(
            name=provider_name,
            region=account.region,
            allowed_regions=allowed_regions,
            endpoint=account.endpoint or "",
            deployment=account.default_model or "",
            api_key_env=account.api_key_env or "",
        )
        return AzureOpenAIAdapter(
            config=config,
            secret_source=secret_source,
            residency_policy=residency_policy,
            egress_policy=egress_policy,
        )
    return None


__all__ = ["adapters_from_settings", "default_adapters"]
