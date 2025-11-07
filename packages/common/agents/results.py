from __future__ import annotations

# pyright: strict

"""Shared dataclasses describing agent outputs."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

RegionLiteral = Literal["canadacentral", "canadaeast"]


def _default_sha_map() -> dict[str, str]:
    return {}


@dataclass(slots=True)
class TranscriptionResult:
    """Normalized payload returned by the transcription agent.

    Attributes:
        transcript_file: Path to the generated transcript text file.
        meta_json: Structured metadata written by the agent (per-run JSON).
        meta_log: Human-readable log accompanying ``meta_json``.
        audit_jsonl: Append-only audit log for the case/job pair.
        region: Azure region used for the transcription (Canada-only).
        language: BCP-47 language code requested for the transcription.
        attempts: Number of attempts made before success.
        duration_s: Duration of the processed audio in seconds, when known.
        sha_map: Mapping of artifact names to SHA-256 digests.
        status: Fixed success marker; errors raise exceptions upstream.
        artifact_hashes: Optional convenience alias for ``sha_map`` consumers.
        udocket_core_version: Version string of ``packages.core`` that produced the result.
    """

    transcript_file: Path
    meta_json: Path
    meta_log: Path
    audit_jsonl: Path
    region: RegionLiteral
    language: str
    attempts: int
    duration_s: float | None
    sha_map: dict[str, str] = field(default_factory=_default_sha_map)
    status: Literal["ok"] = "ok"
    artifact_hashes: dict[str, str] | None = None
    udocket_core_version: str | None = None

    def with_core_version(self, version: str) -> TranscriptionResult:
        """Return a copy that includes the provided core version."""

        return TranscriptionResult(
            transcript_file=self.transcript_file,
            meta_json=self.meta_json,
            meta_log=self.meta_log,
            audit_jsonl=self.audit_jsonl,
            region=self.region,
            language=self.language,
            attempts=self.attempts,
            duration_s=self.duration_s,
            sha_map=dict(self.sha_map),
            status=self.status,
            artifact_hashes=(dict(self.artifact_hashes) if self.artifact_hashes else None),
            udocket_core_version=version,
        )


__all__ = ["TranscriptionResult", "RegionLiteral"]
