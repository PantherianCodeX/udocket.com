from __future__ import annotations

# pyright: strict

from pathlib import Path

from packages.udocket_common.agents import TranscriptionResult


def test_transcription_result_defaults() -> None:
    result = TranscriptionResult(
        transcript_file=Path("/tmp/transcript.txt"),
        meta_json=Path("/tmp/meta.json"),
        meta_log=Path("/tmp/meta.log"),
        audit_jsonl=Path("/tmp/audit.jsonl"),
        region="canadacentral",
        language="en-CA",
        attempts=2,
        duration_s=42.5,
        sha_map={"transcript": "abcd"},
    )

    assert result.status == "ok"
    assert result.artifact_hashes is None
    assert result.sha_map == {"transcript": "abcd"}


def test_transcription_result_with_core_version() -> None:
    base = TranscriptionResult(
        transcript_file=Path("/tmp/t.txt"),
        meta_json=Path("/tmp/m.json"),
        meta_log=Path("/tmp/m.log"),
        audit_jsonl=Path("/tmp/a.jsonl"),
        region="canadaeast",
        language="en-CA",
        attempts=1,
        duration_s=None,
        sha_map={"transcript": "ffff"},
        artifact_hashes={"transcript": "ffff"},
    )

    copy = base.with_core_version("1.2.3")

    assert copy is not base
    assert copy.udocket_core_version == "1.2.3"
    assert copy.sha_map == {"transcript": "ffff"}
    assert copy.artifact_hashes == {"transcript": "ffff"}
