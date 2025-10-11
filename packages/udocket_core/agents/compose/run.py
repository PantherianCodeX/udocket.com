from __future__ import annotations

# pyright: strict

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from packages.udocket_core.json_utils import JSONObject

from .state import ComposeState, serialize_compose_state


@dataclass(slots=True)
class ComposeRun:
    case_id: str
    job_id: str
    snapshot_dir: Path
    logger: logging.Logger
    enabled: bool = True
    _sequence: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def record(self, stage: str, state: ComposeState) -> None:
        if not self.enabled:
            return
        self._sequence += 1
        snapshot_payload = serialize_compose_state(state)
        envelope: JSONObject = {
            "case_id": self.case_id,
            "job_id": self.job_id,
            "stage": stage,
            "sequence": self._sequence,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "state": snapshot_payload,
        }
        filename = f"{self._sequence:04d}_{stage.replace('.', '-')}.json"
        target = self.snapshot_dir / filename
        try:
            target.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            self.logger.warning(
                "compose.run.snapshot_failed",
                extra={"stage": stage, "path": str(target)},
                exc_info=True,
            )


__all__ = ["ComposeRun"]
