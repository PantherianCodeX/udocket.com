from __future__ import annotations

"""Central catalog of artifact fields used for permission presets.

The registry lists every artifact type/field that can appear in
CaseArtifact payloads so new fields automatically flow through
permission tooling.
"""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactField:
    """Declarative metadata describing an artifact field."""

    name: str
    default_actions: tuple[str, ...] = tuple()
    description: str | None = None


ARTIFACT_FIELD_REGISTRY: dict[str, dict[str, ArtifactField]] = {
    "CASE": {
        "id": ArtifactField(
            name="id",
            default_actions=("view",),
            description="Case identifier",
        ),
        "title": ArtifactField(
            name="title",
            default_actions=("view",),
            description="Case title",
        ),
        "organization": ArtifactField(
            name="organization",
            default_actions=("view",),
            description="Owning organization identifier",
        ),
        "created_at": ArtifactField(
            name="created_at",
            default_actions=("view",),
            description="Case creation timestamp",
        ),
        "updated_at": ArtifactField(
            name="updated_at",
            default_actions=("view",),
            description="Case last update timestamp",
        ),
    },
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


def iter_artifact_fields() -> Iterator[tuple[str, ArtifactField]]:
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

    return {(atype, field.name) for atype, field in iter_artifact_fields() if atype != "CASE"}


def artifact_types() -> Iterable[str]:
    """Return all known artifact types."""

    return ARTIFACT_FIELD_REGISTRY.keys()
