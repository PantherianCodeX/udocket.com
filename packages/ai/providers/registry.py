from __future__ import annotations

# pyright: strict

"""Factory helpers for provider adapters."""

from collections.abc import Mapping

from collections.abc import Mapping

from .azure_openai import AzureOpenAIAdapter
from .interfaces import ProviderAdapter
from .null import NullProvider
from ..config import AISettings, ProviderAccount
from ..providers.settings import AzureOpenAIConfig
from ..safety.egress import EgressPolicy
from ..safety.residency import ResidencyPolicy
from ..secret import SecretSource
from ..types import AllowedRegion
from ..types.identifiers import ProviderName


def default_adapters() -> Mapping[ProviderName, ProviderAdapter]:
    """Return a registry containing the null provider for tests."""

    provider = NullProvider()
    return {provider.name: provider}


def adapters_from_settings(
    settings: AISettings,
    *,
    secret_source: SecretSource,
    residency_policy: ResidencyPolicy,
    egress_policy: EgressPolicy,
) -> Mapping[ProviderName, ProviderAdapter]:
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
            allowed_regions=allowed_regions or (AllowedRegion(region=account.region),),
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


__all__ = ["default_adapters", "adapters_from_settings"]
