"""Feature-scoped readiness CLI.

Usage example:
    uv run python -m packages.devops.readiness.cli refresh --feature-dir specs/001-ai-refactor-plan --lane modernization
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .service import (
    ReadinessService,
    ReadinessServiceConfig,
    ReadinessValidationError,
)

DEFAULT_FEATURE_DIR = Path("specs/001-ai-refactor-plan")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Readiness dataset utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    refresh = subparsers.add_parser("refresh", help="Regenerate readiness artifacts")
    refresh.add_argument(
        "--feature-dir",
        type=Path,
        default=DEFAULT_FEATURE_DIR,
        help="Path to the feature workspace (default: specs/001-ai-refactor-plan)",
    )
    refresh.add_argument(
        "--lane",
        type=str,
        default="modernization",
        help="Lane identifier used for ops/audit logging",
    )
    refresh.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate datasets without writing ops JSONL entries",
    )
    return parser


def _handle_refresh(args: argparse.Namespace) -> int:
    config = ReadinessServiceConfig(feature_dir=args.feature_dir, lane=args.lane)
    service = ReadinessService(config)
    try:
        result = service.refresh(dry_run=args.dry_run)
    except ReadinessValidationError as exc:
        print(f"Readiness validation failed: {exc}", file=sys.stderr)
        return 2
    print(
        " :: ".join(
            [
                f"lane={result.lane}",
                f"inventory={result.inventory_count}",
                f"gaps={result.gap_count}",
                f"hash={result.dataset_hash}",
            ]
        )
    )
    print(f"ops_log={result.ops_record_path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "refresh":
        return _handle_refresh(args)
    parser.error("Unknown command")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
