#!/usr/bin/env python3
"""Apply documentation path remapping to align with the refreshed navigation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from doc_tools.config import paths

DOCS_SRC = paths.DOCS_ROOT
PROJECT_ROOT = paths.REPO_ROOT

# Canonical mapping from legacy service paths to the new taxonomy.
# Keys omit the leading docs/ prefix to keep the mapping concise.
PATH_MAPPING = {
    "platform/runtime": "platform/runtime",
    "platform/settings": "platform/settings",
    "platform/identity": "platform/identity",
    "platform/guardian": "platform/guardian",
    "platform/observability": "platform/observability",
    "automation/langgraph-agents": "automation/langgraph-agents",
    "automation/worker-cluster": "automation/worker-cluster",
    "automation/llm-registry": "automation/llm-registry",
    "automation/lp-engine": "automation/lp-engine",
    "data/artifact-store": "data/artifact-store",
    "data/digital-signer": "data/digital-signer",
    "data/ref-manager": "data/ref-manager",
    "data/search-index": "data/search-index",
    "data/audit": "data/audit",
    "customer/accounts-tenants": "customer/accounts-tenants",
    "customer/billing-subscriptions": "customer/billing-subscriptions",
    "customer/communications": "customer/communications",
    "experience/web-app": "experience/web-app",
}


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def move_sources(*, dry_run: bool = False) -> None:
    """Move markdown files and their asset directories to the new locations."""
    for old, new in PATH_MAPPING.items():
        old_md = DOCS_SRC / f"{old}.md"
        new_md = DOCS_SRC / f"{new}.md"
        old_dir = DOCS_SRC / old
        new_dir = DOCS_SRC / new

        # Move supporting asset directory first (if present) so relative links remain valid.
        if old_dir.exists():
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            if new_dir.exists():
                raise RuntimeError(f"Refusing to overwrite existing directory: {new_dir}")
            if dry_run:
                print(f"[nav-mapping] would move directory {_rel(old_dir)} -> {_rel(new_dir)}")
            else:
                old_dir.rename(new_dir)

        if old_md.exists():
            new_md.parent.mkdir(parents=True, exist_ok=True)
            if new_md.exists():
                raise RuntimeError(f"Refusing to overwrite existing file: {new_md}")
            if dry_run:
                print(f"[nav-mapping] would move file {_rel(old_md)} -> {_rel(new_md)}")
            else:
                old_md.rename(new_md)


def update_references(*, dry_run: bool = False) -> None:
    """Rewrite intra-doc references so links resolve after the move."""
    # Process a concise set of text-based extensions we expect to contain references.
    extensions = {".md", ".yml", ".yaml", ".py", ".sh", ".json", ".txt"}
    # Gather candidates once; skip generated output.
    candidates = [
        path
        for path in PROJECT_ROOT.rglob("*")
        if path.is_file()
        and path.suffix in extensions
        and "node_modules" not in path.parts
        and "build/diagrams" not in str(path)
    ]

    replacements = {f"{old}": f"{new}" for old, new in PATH_MAPPING.items()}

    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Skip binary or non-UTF8 files (e.g., vendored assets).
            continue
        original = text
        for old, new in replacements.items():
            text = text.replace(old, new)
        if text != original:
            if dry_run:
                print(f"[nav-mapping] would rewrite {_rel(path)}")
            else:
                path.write_text(text, encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply docs nav path remapping.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned moves/rewrites without modifying files.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    move_sources(dry_run=args.dry_run)
    update_references(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
