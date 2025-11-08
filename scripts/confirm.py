#!/usr/bin/env python3

from __future__ import annotations

import os
import sys


def main() -> int:
    if os.environ.get("CONFIRM_BYPASS") == "1":
        return 0

    target = os.environ.get("CONFIRM_TARGET") or (sys.argv[1] if len(sys.argv) > 1 else "this command")

    if os.environ.get("CI", "").lower() in {"1", "true", "yes"}:
        print(f"[confirm] Refusing to run '{target}' in CI without explicit approval.", file=sys.stderr)
        return 1

    if not sys.stdin.isatty():
        print(f"[confirm] Cannot prompt for '{target}' in a non-interactive shell.", file=sys.stderr)
        return 1

    try:
        response = input(f"[confirm] Proceed with '{target}'? [y/N]: ").strip().lower()
    except EOFError:
        response = ""

    if response in {"y", "yes"}:
        return 0

    print("[confirm] Aborted.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
