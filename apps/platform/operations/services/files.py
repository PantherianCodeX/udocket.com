from __future__ import annotations

from pathlib import Path
from typing import Optional
import hashlib


def sha256_file(path: Path) -> Optional[str]:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:  # pragma: no cover - filesystem errors
        return None


__all__ = ["sha256_file"]
