#!/usr/bin/env python3
"""Utility to normalize section references in docs-new/tdd.md.

The current TDD draft still references legacy section numbers from the prior
outline.  This script replaces those dangling references with their updated
destinations so link lint stays green.  It also normalizes the lone HIPAA
citation that previously used a section symbol, which confused the cross-link
checker.

Usage:
    python scripts/docs/fix_tdd_refs.py

Optional flags:
    --path PATH     Target file (default: docs-new/tdd.md)
    --dry-run       Show the planned edits without writing changes
    --check-only    Exit non-zero if any mapping key is missing

The script preserves UTF-8 content, applies replacements in descending key
length order (to avoid partial overlaps), and prints a short replacement
summary to stdout.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

# Use a narrow no-break space (U+202F) per style guide.
_NBSP = "\u202f"


# Mapping of legacy references to their updated targets.
_MAPPING: dict[str, str] = {
    "HIPAA §164.312": f"HIPAA section{_NBSP}164.312",
    "§54.1-54.10": "§6.6-§6.10",
    "§54.6-54.10": "§6.7-§6.10",
    "§57.4": "§13.5",
    "§57.3": "§12.9",
    "§57": "§12.9",
    "§56": "§6.10",
    "§55": "§6.9",
    "§53": "§6.8",
    "§52": "§10.5",
    "§50": "§10.8",
    "§49": "§7.4",
    "§48": "§8.4",
    "§47": "§10.6",
    "§45": "§10.8",
    "§44": "§10.5",
    "§42": "§9.14",
    "§41.7": "§10.8",
    "§41": "§10.8",
    "§40": "§12.8",
    "§39": "§14.5",
    "§37.3": "§5.7",
    "§37": "§5.7",
    "§36.10": "§9.11",
    "§36.8": "§9.7",
    "§36": "§9",
    "§35": "§16",
    "§34": "§16",
    "§33": "§16",
    "§32": "§16",
    "§31": "§14.4",
    "§29.7": "§14.8",
    "§29.5": "§5.5",
    "§29.4": "§11.6",
    "§29": "§14",
    "§25.1": "§14.9",
    "§25": "§14.9",
    "§24": "§12",
    "§23": "§12",
    "§21.9": "§10.8",
    "§21.7": "§10.9",
    "§21.2": "§10.3",
    "§21": "§10",
    "§20.3": "§12.2",
    "§20.1": "§14.2",
    "§20": "§12",
    "§18": "§11.5",
    "§17": "§11.8",
    "§4.6": "§4.5",
}


def _apply_mapping(text: str) -> tuple[str, dict[str, int]]:
    """Return the updated text and replacement counts for each key."""
    normalized = unicodedata.normalize("NFC", text)
    counts: dict[str, int] = {}

    for legacy in sorted(_MAPPING, key=len, reverse=True):
        replacement = _MAPPING[legacy]
        count = normalized.count(legacy)
        counts[legacy] = count
        if count:
            normalized = normalized.replace(legacy, replacement)

    return normalized, counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("docs-new") / "tdd.md",
        help="Target markdown file (default: docs-new/tdd.md)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show replacement summary without writing the file",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Exit with status 1 if any mapping key was not found",
    )
    args = parser.parse_args()

    path = args.path
    if not path.exists():
        parser.error(f"Target file {path} does not exist")

    original = path.read_text(encoding="utf-8")
    updated, counts = _apply_mapping(original)

    missing = [key for key, count in counts.items() if count == 0]
    changed = updated != original

    for key in sorted(_MAPPING, key=len, reverse=True):
        count = counts[key]
        print(f"{key} -> {_MAPPING[key]} : {count}")

    if args.check_only and missing:
        print(
            "Missing expected references: " + ", ".join(missing),
            file=sys.stderr,
        )
        sys.exit(1)

    if args.dry_run:
        status = "would update" if changed else "no changes needed"
        print(f"[dry-run] {status}: {path}")
        return

    if changed:
        path.write_text(updated, encoding="utf-8")
        print(f"Updated {path}")
    else:
        print(f"No changes needed for {path}")


if __name__ == "__main__":
    main()
