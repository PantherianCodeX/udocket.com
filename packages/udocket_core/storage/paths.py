from __future__ import annotations

# pyright: strict

from pathlib import Path

from config.paths import resolve_storage_root


def case_dir(case_id: str) -> Path:
    base = resolve_storage_root() / "media" / "cases" / case_id
    for sub in ("audio", "ops", "transcript"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def audio_path(case_id: str, job_id: str, original_name: str) -> Path:
    return case_dir(case_id) / "audio" / f"{job_id}__{original_name}"


def transcript_path(case_id: str, job_id: str) -> Path:
    return case_dir(case_id) / "transcript" / f"{job_id}__transcript.txt"


def ops_log_path(case_id: str, job_id: str) -> Path:
    return case_dir(case_id) / "ops" / f"{job_id}.log"
