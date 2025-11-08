"""Shared template/doc-control requirements."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import FrozenSet

from doc_tools.config.header_includes import HEADER_INCLUDES_CONFIG, HeaderIncludesConfig
from doc_tools.common.doc_utils import normalize_key

BASE_FRONT_MATTER_KEYS: FrozenSet[str] = frozenset(
    {
        "title",
        "subtitle",
        "authors",
        "version",
        "status",
        "classification",
        "last_updated",
        "updated_by",
        "owners",
        "reviewers",
        "approvers",
        "approved_by",
        "approved_date",
    }
)
OPTIONAL_KEYS: FrozenSet[str] = frozenset({"approved_by", "approved_date"})
EXCLUDED_CONTROL_KEYS: FrozenSet[str] = frozenset({"title", "subtitle", "header-includes"})


@dataclass(frozen=True)
class TemplateRequirements:
    """Reusable requirements snapshot fed into template/doc checks."""

    header_config: HeaderIncludesConfig = HEADER_INCLUDES_CONFIG

    @cached_property
    def required_front_matter_keys(self) -> FrozenSet[str]:
        header_keys = self.header_config.required_front_matter_keys
        return frozenset(BASE_FRONT_MATTER_KEYS | header_keys)

    @cached_property
    def required_document_control_keys(self) -> FrozenSet[str]:
        return frozenset(
            key
            for key in self.required_front_matter_keys
            if key not in EXCLUDED_CONTROL_KEYS
        )

    @cached_property
    def required_document_control_labels(self) -> FrozenSet[str]:
        return frozenset(normalize_key(key) for key in self.required_document_control_keys)


TEMPLATE_REQUIREMENTS = TemplateRequirements()

__all__ = [
    "BASE_FRONT_MATTER_KEYS",
    "EXCLUDED_CONTROL_KEYS",
    "OPTIONAL_KEYS",
    "TEMPLATE_REQUIREMENTS",
    "TemplateRequirements",
]
