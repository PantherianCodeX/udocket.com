#!/usr/bin/env python3
"""Record activation dry-run evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path("specs/001-ai-refactor-plan/reports/activation_dry_run.jsonl")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append dry-run evidence entry")
    parser.add_argument("step", choices=["readiness", "langsmith", "langfuse"], help="Step name")
    parser.add_argument("result", choices=["pass", "fail"])
    parser.add_argument("notes")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "step": args.step,
        "result": args.result,
        "notes": args.notes,
    }
    with OUTPUT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    print(f"logged dry-run step {args.step}")


if __name__ == "__main__":
    main()
