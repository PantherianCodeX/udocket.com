from __future__ import annotations

import argparse
import sys

from doc_tools.sync import adr_nav
from doc_tools.sync.nav import appendices


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synchronise MkDocs navigation sections.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show planned changes without editing files"
    )
    return parser.parse_args(argv or sys.argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    changed = False

    adr_files = adr_nav.discover_adrs(adr_nav.ADR_DIR)
    changed |= adr_nav.sync_nav(adr_nav.MKDOCS_CONFIG, adr_files, dry_run=args.dry_run)

    appendix_files = appendices.discover_appendices(appendices.APPENDICES_DIR)
    changed |= appendices.sync_nav(appendices.MKDOCS_CONFIG, appendix_files, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
