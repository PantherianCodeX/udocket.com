from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from packages.common.json_utils import JSONObject, JSONValue


def _normalize_payload(data: Mapping[str, JSONValue] | None) -> JSONObject:
    return dict(data or {})


@dataclass(frozen=True)
class ChannelPayload:
    """Base payload wrapper for websocket messages."""

    data: JSONObject

    def message(self) -> JSONObject:
        return dict(self.data)

    @property
    def group(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class JobUpdatePayload(ChannelPayload):
    job_id: str

    @classmethod
    def create(cls, job_id: str, extra: Mapping[str, JSONValue] | None = None) -> JobUpdatePayload:
        payload = _normalize_payload(extra)
        payload["type"] = "job.update"
        payload["job_id"] = job_id
        return cls(job_id=job_id, data=payload)

    @property
    def group(self) -> str:
        return f"jobs_{self.job_id}"


@dataclass(frozen=True)
class CaseUpdatePayload(ChannelPayload):
    case_id: str

    @classmethod
    def create(
        cls, case_id: str, extra: Mapping[str, JSONValue] | None = None
    ) -> CaseUpdatePayload:
        payload = _normalize_payload(extra)
        payload["type"] = "case.update"
        payload["case_id"] = case_id
        return cls(case_id=case_id, data=payload)

    @property
    def group(self) -> str:
        return f"cases_{self.case_id}"


__all__ = ["JobUpdatePayload", "CaseUpdatePayload"]
