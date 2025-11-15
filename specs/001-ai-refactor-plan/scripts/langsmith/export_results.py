#!/usr/bin/env python3
"""Validate LangSmith eval results against local schema and emit normalized export."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path("specs/001-ai-refactor-plan/schemas/tooling/evaluation_evidence.schema.json")
INPUT_PATH = Path("specs/001-ai-refactor-plan/reports/langsmith_eval_results.json")
OUTPUT_PATH = Path("specs/001-ai-refactor-plan/reports/langsmith_eval_export.json")
DATASET_RE = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(slots=True)
class ValidationError(Exception):
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate LangSmith eval results and emit normalized JSON")
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    return parser.parse_args()


def validate(payload: dict[str, Any]) -> None:
    required = [
        "experiment_id",
        "dataset_hash",
        "prompt_bundle_id",
        "metrics",
        "run_started_at",
        "run_completed_at",
        "owner",
    ]
    for key in required:
        if key not in payload:
            raise ValidationError(f"missing field {key}")
    if not DATASET_RE.match(payload["dataset_hash"]):
        raise ValidationError("dataset_hash must be 64 hex chars")
    start = datetime.fromisoformat(payload["run_started_at"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(payload["run_completed_at"].replace("Z", "+00:00"))
    if end < start:
        raise ValidationError("run_completed_at must be >= run_started_at")
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        raise ValidationError("metrics must be object")


def main() -> None:
    args = parse_args()
    with args.input.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    validate(payload)
    normalized = {
        "experiment_id": payload["experiment_id"],
        "dataset_hash": payload["dataset_hash"],
        "prompt_bundle_id": payload["prompt_bundle_id"],
        "metrics": payload["metrics"],
        "owner": payload["owner"],
        "run_started_at": payload["run_started_at"],
        "run_completed_at": payload["run_completed_at"],
        "attachments": payload.get("attachments", []),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(normalized, handle, indent=2)
        handle.write("\n")
    print(f"validated export -> {args.output}")


if __name__ == "__main__":
    main()
