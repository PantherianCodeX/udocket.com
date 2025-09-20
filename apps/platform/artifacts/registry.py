from __future__ import annotations

"""Central catalog of artifact fields used for permission presets.

The registry lists every artifact type/field that can appear in
CaseArtifact payloads so new fields automatically flow through
permission tooling.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, Tuple


@dataclass(frozen=True)
class ArtifactField:
    """Declarative metadata describing an artifact field."""

    name: str
    default_actions: Tuple[str, ...] = tuple()
    description: str | None = None


ARTIFACT_FIELD_REGISTRY: Dict[str, Dict[str, ArtifactField]] = {
    "TRANSCRIPT": {
        "path": ArtifactField(
            name="path",
            default_actions=(),
            description="Filesystem path to transcript artifact",
        ),
        "checksum": ArtifactField(
            name="checksum",
            default_actions=(),
            description="SHA-256 checksum of transcript contents",
        ),
    },
    "SUMMARY": {
        "path": ArtifactField(
            name="path",
            default_actions=(),
            description="Filesystem path to summary artifact",
        ),
    },
    "TIMELINE": {
        "path": ArtifactField(
            name="path",
            default_actions=(),
            description="Filesystem path to timeline artifact",
        ),
    },
    "ENTITIES": {
        "path": ArtifactField(
            name="path",
            default_actions=(),
            description="Filesystem path to entities artifact",
        ),
    },
    "GRAPH": {
        "path": ArtifactField(
            name="path",
            default_actions=(),
            description="Filesystem path to graph artifact",
        ),
    },
}


def iter_artifact_fields() -> Iterator[Tuple[str, ArtifactField]]:
    """Iterate over every artifact type/field pair."""

    for artifact_type, fields in ARTIFACT_FIELD_REGISTRY.items():
        for field in fields.values():
            yield artifact_type, field


def artifact_field(artifact_type: str, field_name: str) -> ArtifactField | None:
    """Return metadata for an artifact field if registered."""

    fields = ARTIFACT_FIELD_REGISTRY.get(artifact_type, {})
    return fields.get(field_name)


def artifact_field_keys() -> set[tuple[str, str]]:
    """Convenience set of (type, field) keys."""

    return {(atype, field.name) for atype, field in iter_artifact_fields()}


def artifact_types() -> Iterable[str]:
    """Return all known artifact types."""

    return ARTIFACT_FIELD_REGISTRY.keys()


