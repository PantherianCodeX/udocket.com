from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from packages.udocket_common.json_utils import (
    JSONObject,
    JSONValue,
    coerce_json_object,
    coerce_str_list,
    normalize_json_object,
)


def optional_json_object(value: object) -> JSONObject | None:
    """Return a JSON object when the input is mapping-like, otherwise None."""

    if isinstance(value, Mapping):
        mapping = coerce_json_object(value)
        return dict(mapping)
    return None


@dataclass(frozen=True)
class ComposeStageMap:
    """Immutable mapping of compose stages to normalized JSON configuration."""

    entries: dict[str, JSONObject] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object] | None) -> ComposeStageMap:
        if not payload:
            return cls()
        entries: dict[str, JSONObject] = {}
        for key, value in payload.items():
            if isinstance(value, Mapping):
                entries[key] = coerce_json_object(value)
        return cls(entries=dict(entries))

    def providers(self) -> list[str]:
        """Return a de-duplicated list of providers referenced by the stage map."""

        discovered: list[str] = []
        for config in self.entries.values():
            for candidate in _provider_candidates(config):
                lowered = candidate.lower()
                if lowered not in discovered:
                    discovered.append(lowered)
        return discovered

    def to_dict(self) -> dict[str, JSONObject]:
        """Return a shallow copy suitable for JSON serialization."""

        return {key: dict(value) for key, value in self.entries.items()}


@dataclass(frozen=True)
class ComposeProviderCredentials:
    """Provider credentials keyed by provider name."""

    items: dict[str, JSONObject] = field(default_factory=dict)

    def with_secret(
        self, provider: str, payload: Mapping[str, object] | None
    ) -> ComposeProviderCredentials:
        if payload is None:
            return self
        normalized = dict(self.items)
        normalized[provider] = coerce_json_object(payload)
        return ComposeProviderCredentials(items=normalized)

    def extend(
        self, pairs: Iterable[tuple[str, Mapping[str, object] | None]]
    ) -> ComposeProviderCredentials:
        credentials = self
        for provider, payload in pairs:
            credentials = credentials.with_secret(provider, payload)
        return credentials

    def to_dict(self) -> dict[str, JSONObject]:
        return {key: dict(value) for key, value in self.items.items()}


@dataclass(frozen=True)
class ComposeCaseMetadata:
    """Case metadata passed into compose agents."""

    case_id: str
    compose_job_id: str
    summary_job_id: str
    job_display_title: str | None = None
    case_title: str | None = None
    organization_id: str | None = None
    organization_name: str | None = None
    summary_markdown_file: str | None = None
    summary_json_file: str | None = None

    def to_json(self) -> JSONObject:
        payload: dict[str, JSONValue] = {
            "case_id": self.case_id,
            "compose_job_id": self.compose_job_id,
            "summary_job_id": self.summary_job_id,
        }
        if self.job_display_title:
            payload["job_display_title"] = self.job_display_title
        if self.case_title:
            payload["case_title"] = self.case_title
        if self.organization_id:
            payload["organization_id"] = self.organization_id
        if self.organization_name:
            payload["organization_name"] = self.organization_name
        if self.summary_markdown_file:
            payload["summary_markdown_file"] = self.summary_markdown_file
        if self.summary_json_file:
            payload["summary_json_file"] = self.summary_json_file
        return normalize_json_object(payload, drop_nullish_values=True, drop_empty_keys=True)


def _provider_candidates(config: Mapping[str, JSONValue]) -> Sequence[str]:
    providers_value = config.get("providers")
    single_provider = config.get("provider")
    providers = list(coerce_str_list(providers_value, unique=False, drop_empty=True, lower=True))
    for candidate in coerce_str_list(single_provider, unique=False, drop_empty=True, lower=True):
        providers.append(candidate)
    return providers
