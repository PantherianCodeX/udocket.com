#!/usr/bin/env python3
"""Validate that every settings key documented in Appendix E exists somewhere in the codebase.

Reads `docs/overview/tdd.md`, extracts settings keys from Appendix E, then uses ripgrep to
search for each key outside the document. Prints any keys that are missing so CI can
fail fast when docs reference non-existent keys.

Usage: python -m doc_tools.check.settings_keys
Environment variables:
  SKIP_KEYS  Comma separated list of keys to ignore (e.g. experimental placeholders).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

from doc_tools import paths

DOC_PATH = paths.DOCS_ROOT / "overview" / "tdd.md"
SKIP_FILE = paths.CONFIG_ROOT / "settings_key_skip.txt"


def extract_keys(text: str) -> list[str]:
    pattern = re.compile(r"^- ([a-zA-Z0-9_.]+) — ")
    keys: list[str] = []
    for line in text.splitlines():
        m = pattern.match(line.strip())
        if m:
            keys.append(m.group(1))
    return keys


def find_missing(keys: list[str], skip: set[str]) -> list[str]:
    missing: list[str] = []
    for key in keys:
        if key in skip:
            continue
        # Ripgrep exits 0 on match, 1 on no match, >1 on error.
        result = subprocess.run(
            [
                "rg",
                "--glob",
                "!docs/overview/tdd.md",
                "--glob",
                "!packages/docs_tooling/src/doc_tools/check_settings_keys.py",
                key,
                str(paths.REPO_ROOT),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 1:
            missing.append(key)
        elif result.returncode > 1:
            print(result.stderr, file=sys.stderr)
            raise RuntimeError(f"ripgrep failed for key {key}")
    return missing


def main() -> int:
    if not DOC_PATH.exists():
        print(f"Unable to find {DOC_PATH}", file=sys.stderr)
        return 2

    text = DOC_PATH.read_text(encoding="utf-8")
    keys = extract_keys(text)
    skip_env = os.getenv("SKIP_KEYS", "")
    skip = {k.strip() for k in skip_env.split(",") if k.strip()}
    if SKIP_FILE.exists():
        skip_from_file = {
            line.strip()
            for line in SKIP_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        skip.update(skip_from_file)

    missing = find_missing(keys, skip)
    if missing:
        print("Settings keys documented but not found in code:")
        for key in missing:
            print(f" - {key}")
        return 1

    print("All documented settings keys were found in the codebase.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
