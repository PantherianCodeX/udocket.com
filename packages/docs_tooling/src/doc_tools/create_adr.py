#!/usr/bin/env python3
"""Generate a new ADR skeleton using the next sequential identifier."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from typing import Sequence

from doc_tools import paths
from packages.common.text import slugify

ADR_DIR = paths.DOCS_ROOT / "adr"


def next_identifier() -> int:
    existing: list[int] = []
    for path in ADR_DIR.glob("ADR-*.md"):
        try:
            number = int(path.stem.split("-", 2)[1])
        except (IndexError, ValueError):
            continue
        existing.append(number)
    return (max(existing) if existing else 0) + 1


def build_content(
    ident: int,
    title: str,
    status: str,
    deciders: Sequence[str],
    tags: Sequence[str],
    date: str,
) -> str:
    header = f"# ADR-{ident:04d} — {title}\n"
    lines: list[str] = [
        header,
        f"- **Status:** {status}",
        f"- **Date:** {date}",
        f"- **Deciders:** {', '.join(deciders) if deciders else 'TBD'}",
        f"- **Tags:** {', '.join(tags) if tags else 'tbd'}",
        "",
        "## Context",
        "",
        "> What background or problem statement led to this decision?",
        "",
        "## Decision",
        "",
        "> Describe the chosen direction. Capture the technical changes and the rationale.",
        "",
        "## Consequences",
        "",
        "> List positive and negative outcomes. Include follow-up work.",
        "",
    ]
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a new ADR skeleton.")
    parser.add_argument("title", help="Human-readable ADR title, e.g. 'Background worker topology'.")
    parser.add_argument("--status", default="Proposed", help="Initial status (default: Proposed).")
    parser.add_argument(
        "--deciders",
        default="",
        help="Comma-separated deciders (defaults to TBD).",
    )
    parser.add_argument("--tags", default="", help="Comma-separated tag list.")
    parser.add_argument(
        "--date",
        default=dt.date.today().isoformat(),
        help="Decision date (defaults to today).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the target file without writing.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    ident = next_identifier()
    slug = slugify(args.title)
    filename = f"ADR-{ident:04d}-{slug}.md"
    path = ADR_DIR / filename
    if path.exists():
        print(f"ADR already exists at {path}", file=sys.stderr)
        return 1

    deciders: list[str] = [part.strip() for part in args.deciders.split(",") if part.strip()]
    tags: list[str] = [part.strip() for part in args.tags.split(",") if part.strip()]
    content = build_content(ident, args.title, args.status, deciders, tags, args.date)

    if args.dry_run:
        print(f"[create-adr] would write {path}")
        print(content)
        return 0

    ADR_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[create-adr] created {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
