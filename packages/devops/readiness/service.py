"""Ingest helpers for feature-scoped readiness datasets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Final, Iterable, Sequence

__all__ = [
    "ReadinessService",
    "ReadinessServiceConfig",
    "ReadinessServiceResult",
    "ReadinessValidationError",
]

ALLOWED_STATUSES: Final[frozenset[str]] = frozenset(
    {"complete", "in_flight", "blocked", "not_started"}
)


class ReadinessValidationError(RuntimeError):
    """Raised when the readiness payload violates the spec."""


@dataclass(frozen=True, slots=True)
class ReadinessServiceConfig:
    feature_dir: Path
    lane: str
    reports_subdir: str = "reports"

    def data_dir(self) -> Path:
        return self.feature_dir / "data" / "readiness"

    def reports_dir(self) -> Path:
        return self.feature_dir / self.reports_subdir


@dataclass(frozen=True, slots=True)
class ReadinessServiceResult:
    lane: str
    dataset_hash: str
    inventory_count: int
    gap_count: int
    ops_record_path: Path


class ReadinessService:
    """Surface readiness refresh helpers for CLI + scripts."""

    def __init__(self, config: ReadinessServiceConfig) -> None:
        self._config = config

    def refresh(self, *, dry_run: bool = False) -> ReadinessServiceResult:
        inventory_path = self._config.data_dir() / "inventory.json"
        gaps_path = self._config.data_dir() / "gaps.json"
        inventory = self._load_json(inventory_path)
        gaps = self._load_json(gaps_path)
        self._validate_inventory(inventory)
        self._validate_gaps(gaps)
        dataset_hash = self._hash_files([inventory_path, gaps_path])
        ops_record_path = self._config.reports_dir() / "readiness_ops.jsonl"
        if not dry_run:
            self._config.reports_dir().mkdir(parents=True, exist_ok=True)
            record = self._build_ops_record(dataset_hash, inventory, gaps)
            with ops_record_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, separators=(",", ":")) + "\n")
        return ReadinessServiceResult(
            lane=self._config.lane,
            dataset_hash=dataset_hash,
            inventory_count=len(inventory),
            gap_count=len(gaps),
            ops_record_path=ops_record_path,
        )

    def _build_ops_record(
        self,
        dataset_hash: str,
        inventory: Sequence[dict[str, object]],
        gaps: Sequence[dict[str, object]],
    ) -> dict[str, object]:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return {
            "timestamp": timestamp,
            "lane": self._config.lane,
            "dataset_hash": dataset_hash,
            "inventory_count": len(inventory),
            "gap_count": len(gaps),
            "evidence": {
                "inventory_path": str(self._config.data_dir() / "inventory.json"),
                "gaps_path": str(self._config.data_dir() / "gaps.json"),
            },
        }

    def _load_json(self, path: Path) -> list[dict[str, object]]:
        if not path.exists():
            raise ReadinessValidationError(f"Missing dataset: {path}")
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ReadinessValidationError(f"Expected list in {path}")
        return [self._ensure_mapping(item, path) for item in data]

    def _ensure_mapping(self, item: object, path: Path) -> dict[str, object]:
        if not isinstance(item, dict):
            raise ReadinessValidationError(f"Entries in {path} must be objects")
        return item

    def _validate_inventory(self, inventory: Sequence[dict[str, object]]) -> None:
        for entry in inventory:
            stage_key = entry.get("stage_key")
            status = entry.get("status")
            cutoff = entry.get("cutoff_date")
            if not isinstance(stage_key, str):
                raise ReadinessValidationError("stage_key must be a string")
            if status not in ALLOWED_STATUSES:
                raise ReadinessValidationError(
                    f"status must be in {sorted(ALLOWED_STATUSES)}"
                )
            if not isinstance(cutoff, str):
                raise ReadinessValidationError("cutoff_date must be ISO date string")

    def _validate_gaps(self, gaps: Sequence[dict[str, object]]) -> None:
        for gap in gaps:
            if "gap_id" not in gap:
                raise ReadinessValidationError("gap entries require gap_id")
            if "component_id" not in gap:
                raise ReadinessValidationError("gap entries require component_id")

    def _hash_files(self, paths: Iterable[Path]) -> str:
        digest = hashlib.sha256()
        for path in sorted(paths):
            digest.update(path.read_bytes())
        return digest.hexdigest()
