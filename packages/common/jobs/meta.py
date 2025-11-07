from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from packages.common.json_utils import (
    JSONObject,
    coerce_json_object,
    coerce_str,
)

_TITLE_KEYS: Final[tuple[str, ...]] = ("job_title", "title", "display_title")
_SOURCE_KEYS: Final[tuple[str, ...]] = ("source_job_id", "converted_audio_job_id")


@dataclass(frozen=True)
class JobRecordPatch:
    """Normalized fields propagated from job metadata into the primary Job record."""

    agent_type: str | None = None
    agent_label: str | None = None
    job_kind: str | None = None
    display_title: str | None = None
    source_job_id: uuid.UUID | None = None

    @classmethod
    def from_meta(cls, meta: Mapping[str, object]) -> JobRecordPatch:
        """Build a sanitized patch from arbitrary job metadata."""

        normalized = coerce_json_object(meta)

        agent_type = _normalized_text(normalized.get("agent_type"), max_length=64)
        agent_label = _normalized_text(normalized.get("agent_label"), max_length=128)
        job_kind = _normalized_text(normalized.get("job_kind"), max_length=64)

        display_title: str | None = None
        for key in _TITLE_KEYS:
            display_title = _normalized_text(normalized.get(key), max_length=255)
            if display_title:
                break

        source_job_id = _extract_uuid(normalized)

        return cls(
            agent_type=agent_type,
            agent_label=agent_label,
            job_kind=job_kind,
            display_title=display_title,
            source_job_id=source_job_id,
        )

    def as_model_kwargs(self, *, include_source_job: bool = True) -> dict[str, object]:
        """Return a dict suitable for Job.objects.update with non-null fields."""

        payload: dict[str, object] = {}
        if self.agent_type:
            payload["agent_type"] = self.agent_type
        if self.agent_label:
            payload["agent_label"] = self.agent_label
        if self.job_kind:
            payload["job_kind"] = self.job_kind
        if self.display_title:
            payload["display_title"] = self.display_title
        if include_source_job and self.source_job_id is not None:
            payload["source_job_id"] = self.source_job_id
        return payload


def merge_job_meta(
    base: Mapping[str, object],
    updates: Mapping[str, object],
) -> tuple[JSONObject, bool]:
    """Merge JSON-friendly metadata, returning the new object and change flag."""

    merged: JSONObject = dict(coerce_json_object(base))
    normalized_updates = coerce_json_object(updates)
    changed = False
    for key, value in normalized_updates.items():
        if merged.get(key) != value:
            merged[key] = value
            changed = True
    return merged, changed


def _normalized_text(value: object, *, max_length: int) -> str | None:
    text = coerce_str(value)
    if not text:
        return None
    return text[:max_length]


def _extract_uuid(meta: Mapping[str, object]) -> uuid.UUID | None:
    for key in _SOURCE_KEYS:
        candidate = meta.get(key)
        if candidate is None:
            continue
        try:
            extracted = uuid.UUID(str(candidate))
        except (ValueError, TypeError, AttributeError):
            continue
        return extracted
    return None
