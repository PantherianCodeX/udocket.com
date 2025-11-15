"""API helpers for the AI refactor manifest contracts."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence

from packages.ai.telemetry.config import ledger_entries

DEFAULT_OPS_TOKEN = "ai-refactor-default-token"
OPS_TOKEN_ENV = "AI_REFACTOR_OPS_TOKEN"
GRAPH_DIR = Path("storage/ops/ai-refactor/graphs")


def _expected_token() -> str:
    return os.environ.get(OPS_TOKEN_ENV, DEFAULT_OPS_TOKEN)


def _check_token(token: str) -> None:
    if token != _expected_token():
        raise PermissionError("Invalid OpsToken")


def manifest_endpoint(
    token: str,
    manifest_path: Path,
    *,
    status: str | None = None,
) -> list[dict[str, object]]:
    _check_token(token)
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)

    results: list[dict[str, object]] = []
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            entry = json.loads(line)
            record_status = entry.get("status")
            if status and record_status != status:
                continue
            if isinstance(record_status, str):
                entry["status"] = record_status
            results.append(entry)
    return results


def readiness_snapshots(
    token: str,
    *,
    graph_dir: Path = GRAPH_DIR,
    max_staleness_days: int | None = None,
) -> list[dict[str, object]]:
    _check_token(token)
    cutoff: datetime | None = (
        datetime.now(tz=datetime.utcnow().astimezone().tzinfo) - timedelta(days=max_staleness_days)
        if max_staleness_days
        else None
    )
    snapshots: list[dict[str, object]] = []
    for path in sorted(graph_dir.glob("graph_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        generated = payload.get("generated_at")
        if cutoff and generated:
            parsed = datetime.fromisoformat(generated)
            if parsed < cutoff:
                continue
        snapshots.append({"path": str(path), "payload": payload})
    return snapshots


def residency_ledger(
    token: str,
    *,
    stage_key: str | None = None,
    run_id: str | None = None,
) -> list[dict[str, object]]:
    _check_token(token)
    entries = ledger_entries()
    filtered: list[dict[str, object]] = []
    for entry in entries:
        if stage_key and entry.get("stage_key") != stage_key:
            continue
        if run_id and entry.get("run_id") != run_id:
            continue
        filtered.append(entry)
    return filtered
