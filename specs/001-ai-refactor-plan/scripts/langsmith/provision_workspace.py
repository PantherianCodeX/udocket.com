#!/usr/bin/env python3
"""Provision LangSmith workspace metadata for planning evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACES_FILE = Path("specs/001-ai-refactor-plan/data/tooling/workspaces.yaml")
LOG_FILE = Path("specs/001-ai-refactor-plan/reports/langsmith_workspace_records.jsonl")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record LangSmith workspace provisioning event")
    parser.add_argument("workspace", help="Workspace environment name (dev/staging)")
    parser.add_argument("api_key_suffix", help="Last 4 chars of API key for audit")
    parser.add_argument("owner", help="Person executing provisioning")
    return parser.parse_args()


def load_workspace_data() -> dict[str, Any]:
    import yaml  # locally available

    with WORKSPACES_FILE.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> None:
    args = parse_args()
    data = load_workspace_data()
    entry = next(
        (item for item in data.get("langsmith", []) if item["environment"] == args.workspace),
        None,
    )
    if entry is None:
        raise SystemExit(f"workspace {args.workspace} not found in {WORKSPACES_FILE}")
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workspace_env": args.workspace,
        "workspace_id": entry["workspace_id"],
        "owners": entry["owners"],
        "actor": args.owner,
        "api_key_suffix": args.api_key_suffix,
    }
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    print(f"recorded provisioning for {args.workspace} -> {LOG_FILE}")


if __name__ == "__main__":
    main()
