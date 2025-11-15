"""Telemetry/residency helper utilities for the automation AI refactor."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
from uuid import UUID

from packages.common.types import FeatureID, ResidencyLedgerEntry, ResidencyTag

_LEDGER_PATH = Path("storage/audit/ai-refactor/ledger.jsonl")
LEDGER_PATH = _LEDGER_PATH


def _ensure_ledger_dir() -> None:
    _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class LangSmithEvidence:
    workspace_id: UUID
    eval_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class LangFuseEvidence:
    session_id: UUID
    disconnect_event: bool


def append_residency_entry(entry: ResidencyLedgerEntry) -> Path:
    """Append a residency ledger entry to the audited log."""

    _ensure_ledger_dir()
    row = {
        "ledger_id": str(entry.ledger_id),
        "feature_id": entry.feature_id.value,
        "run_id": str(entry.run_id),
        "stage_key": entry.stage_key.value,
        "residency_tag": entry.residency_tag.value,
        "telemetry_bundle_path": str(entry.telemetry_bundle_path),
        "langsmith_eval_ids": [str(ref) for ref in entry.langsmith_eval_ids],
        "langfuse_session_id": str(entry.langfuse_session_id) if entry.langfuse_session_id else None,
        "disconnect_event": entry.disconnect_event,
        "timestamp": entry.timestamp.isoformat(),
    }
    with _LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")))
        handle.write("\n")
    return _LEDGER_PATH


def ledger_entries() -> list[dict[str, object]]:
    if not _LEDGER_PATH.exists():
        return []
    entries: list[dict[str, object]] = []
    with _LEDGER_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def record_langsmith_evidence(workspace_id: UUID, eval_ids: Sequence[UUID]) -> LangSmithEvidence:
    return LangSmithEvidence(workspace_id=workspace_id, eval_ids=tuple(eval_ids))


def record_langfuse_session(session_id: UUID, disconnect_event: bool) -> LangFuseEvidence:
    return LangFuseEvidence(session_id=session_id, disconnect_event=disconnect_event)
