from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from packages.ai.telemetry.config import LEDGER_PATH, append_residency_entry, ledger_entries
from packages.common.agents.stage_map import StageKey
from packages.common.types import FeatureID, ResidencyLedgerEntry, ResidencyTag


def _build_entry() -> ResidencyLedgerEntry:
    return ResidencyLedgerEntry(
        ledger_id=uuid4(),
        feature_id=FeatureID.REFRACTOR_002,
        run_id=uuid4(),
        stage_key=StageKey.AN_SUMMARY_DRAFT,
        residency_tag=ResidencyTag.US_EAST,
        telemetry_bundle_path=Path("storage/ops/ai-refactor/graphs/test.bundle"),
        langsmith_eval_ids=(uuid4(),),
        langfuse_session_id=None,
        disconnect_event=False,
        timestamp=datetime.now(timezone.utc),
    )


def test_append_residency_entry_preserves_existing(tmp_path: Path) -> None:
    backup: Path | None = None
    if LEDGER_PATH.exists():
        backup = tmp_path / "ledger.backup"
        backup.write_bytes(LEDGER_PATH.read_bytes())
    try:
        entry = _build_entry()
        append_residency_entry(entry)
        entries = ledger_entries()
        assert any(row.get("ledger_id") == str(entry.ledger_id) for row in entries)
    finally:
        if backup:
            LEDGER_PATH.write_bytes(backup.read_bytes())
        elif LEDGER_PATH.exists():
            LEDGER_PATH.unlink()
