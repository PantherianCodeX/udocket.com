#!/usr/bin/env python3
"""CI-friendly strict pragma enforcement.

Runs ``enforce_pyright_strict.py --dry-run`` and exits non-zero if any files
would be modified, preventing regressions where strict modules lack the pragma.
"""

from __future__ import annotations

import subprocess
import sys


def run() -> int:
    proc = subprocess.run(
        [sys.executable, "scripts/typing/enforce_pyright_strict.py", "--dry-run"],
        text=True,
        capture_output=True,
        check=False,
    )
    output = (proc.stdout or "").strip()
    if output:
        # Emit the list of files that are missing the pragma and fail.
        sys.stdout.write("Strict pragma missing in the following files:\n")
        sys.stdout.write(output + "\n")
        return 1
    print("All strict files include the pragma.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
