#!/usr/bin/env python3
"""Prototype backlog generator for the AI Module Migration plan."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence

STAGE_DEPENDENCIES: Final[dict[str, list[str]]] = {
    "analyze.atoms_extract": ["analyze.input_discovery"],
    "analyze.context_builder": ["analyze.atoms_extract"],
    "analyze.gaps_extract": ["analyze.context_builder"],
    "analyze.flags_extract": ["analyze.gaps_extract"],
    "compose.release_gate": ["analyze.flags_extract"],
}

STAGE_QA_GATES: Final[dict[str, list[str]]] = {
    "analyze.input_discovery": ["ops_ingest_evidence"],
    "analyze.atoms_extract": ["token_histogram", "owner_ack"],
    "analyze.context_builder": ["residency_tags_validated"],
    "analyze.gaps_extract": ["gap_diff_hash"],
    "analyze.flags_extract": ["risk_log_sync"],
    "compose.release_gate": ["residency_attestation", "readiness_hash_check"],
}

STAGE_COSTS: Final[dict[str, float]] = {
    "analyze.input_discovery": 0.05,
    "analyze.atoms_extract": 0.2,
    "analyze.context_builder": 0.25,
    "analyze.gaps_extract": 0.3,
    "analyze.flags_extract": 0.15,
    "compose.release_gate": 0.0,
}


@dataclass(slots=True)
class MigrationTask:
    task_id: str
    title: str
    stage_key: str
    status: str
    dependencies: list[str]
    effort_low: int
    effort_high: int
    critical_path: bool
    qa_gates: list[str]
    cost_ceiling: float

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "stage_key": self.stage_key,
            "status": self.status,
            "dependencies": self.dependencies,
            "effort_low": self.effort_low,
            "effort_high": self.effort_high,
            "critical_path": self.critical_path,
            "qa_gates": self.qa_gates,
            "cost_ceiling": self.cost_ceiling,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate migration backlog from readiness data")
    parser.add_argument(
        "--feature-dir",
        type=Path,
        default=Path("specs/001-ai-refactor-plan"),
        help="Path to feature directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional override for backlog json path",
    )
    return parser.parse_args()


def load_inventory(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):  # pragma: no cover (planning script)
        raise SystemExit("inventory.json must be a list")
    return data


def determine_tasks(inventory: Sequence[dict[str, object]]) -> list[MigrationTask]:
    tasks: list[MigrationTask] = []
    counter = 1
    for entry in inventory:
        stage_key = entry["stage_key"]
        status = str(entry["status"])
        if status == "complete":
            continue
        task_id = f"MIG-{counter:03d}"
        counter += 1
        dependencies = STAGE_DEPENDENCIES.get(stage_key, [])
        critical = stage_key in {"analyze.gaps_extract", "compose.release_gate"}
        effort_low, effort_high = _effort_estimate(status)
        tasks.append(
            MigrationTask(
                task_id=task_id,
                title=f"Modernize {stage_key}",
                stage_key=stage_key,
                status=status,
                dependencies=dependencies,
                effort_low=effort_low,
                effort_high=effort_high,
                critical_path=critical,
                qa_gates=STAGE_QA_GATES.get(stage_key, []),
                cost_ceiling=STAGE_COSTS.get(stage_key, 0.0),
            )
        )
    return tasks


def _effort_estimate(status: str) -> tuple[int, int]:
    if status == "blocked":
        return (5, 8)
    if status == "in_flight":
        return (3, 5)
    return (2, 3)


def main() -> None:
    args = parse_args()
    inventory = load_inventory(args.feature_dir / "data" / "readiness" / "inventory.json")
    tasks = determine_tasks(inventory)
    output_path = (
        args.output
        if args.output is not None
        else args.feature_dir / "data" / "backlog" / "migration_backlog.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = [task.to_dict() for task in tasks]
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(serialized, handle, indent=2)
        handle.write("\n")
    print(f"wrote {len(serialized)} tasks to {output_path}")


if __name__ == "__main__":
    main()
