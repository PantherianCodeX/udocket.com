#!/usr/bin/env python3
"""Apply documentation path remapping to align with the refreshed navigation."""

from __future__ import annotations

import sys
from pathlib import Path

from doc_tools import paths

DOCS_SRC = paths.DOCS_ROOT

# Canonical mapping from legacy service paths to the new taxonomy.
# Keys omit the leading docs/ prefix to keep the mapping concise.
PATH_MAPPING = {
    "services/platform-runtime": "platform/runtime",
    "services/settings": "platform/settings",
    "services/identity": "platform/identity",
    "services/guardian": "platform/guardian",
    "services/observability": "platform/observability",
    "services/langgraph-agents": "automation/langgraph-agents",
    "services/worker-cluster": "automation/worker-cluster",
    "services/llm-registry": "automation/llm-registry",
    "services/lp-engine": "automation/lp-engine",
    "services/artifact-store": "data/artifact-store",
    "services/digital-signer": "data/digital-signer",
    "services/ref-manager": "data/ref-manager",
    "services/search-index": "data/search-index",
    "services/audit": "data/audit",
    "services/accounts-tenants": "customer/accounts-tenants",
    "services/billing-subscriptions": "customer/billing-subscriptions",
    "services/communications": "customer/communications",
    "apps/web-app": "experience/web-app",
}


def move_sources() -> None:
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
            old_dir.rename(new_dir)

        if old_md.exists():
            new_md.parent.mkdir(parents=True, exist_ok=True)
            if new_md.exists():
                raise RuntimeError(f"Refusing to overwrite existing file: {new_md}")
            old_md.rename(new_md)


def update_references() -> None:
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
        and "build/mermaid" not in str(path)
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
            path.write_text(text, encoding="utf-8")


def main() -> int:
    move_sources()
    update_references()
    return 0


if __name__ == "__main__":
    sys.exit(main())
