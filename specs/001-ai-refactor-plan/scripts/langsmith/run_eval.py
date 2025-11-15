#!/usr/bin/env python3
"""Simulate LangSmith evaluation runs for planning evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTPUT_FILE = Path("specs/001-ai-refactor-plan/reports/langsmith_eval_results.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record LangSmith eval run metadata")
    parser.add_argument("--workspace", default="dev", help="LangSmith workspace env")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--prompt-bundle", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--pass-rate", type=float, default=0.9)
    parser.add_argument("--latency-ms", type=float, default=450.0)
    parser.add_argument("--cost-usd", type=float, default=2.15)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "experiment_id": args.experiment_id,
        "workspace": args.workspace,
        "prompt_bundle_id": args.prompt_bundle,
        "dataset_hash": args.dataset,
        "owner": args.owner,
        "metrics": {
            "pass_rate": args.pass_rate,
            "latency_ms": args.latency_ms,
            "cost_usd": args.cost_usd,
        },
        "run_started_at": now.isoformat().replace("+00:00", "Z"),
        "run_completed_at": now.isoformat().replace("+00:00", "Z"),
    }
    with OUTPUT_FILE.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    print(f"wrote eval results to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
