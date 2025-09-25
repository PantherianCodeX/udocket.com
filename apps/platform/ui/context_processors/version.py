from __future__ import annotations

import os
import subprocess
from typing import Dict


def app_version(_: object) -> Dict[str, str]:
    """Expose a short build/version string for footer display.

    Priority:
    1) APP_BUILD env (e.g., CI build number or docker image tag)
    2) GIT_SHA env (short commit)
    3) git rev-parse --short HEAD (if available)
    4) "dev"
    """
    build = os.getenv("APP_BUILD")
    if build:
        return {"APP_BUILD": build}
    sha = os.getenv("GIT_SHA")
    if sha:
        return {"APP_BUILD": sha[:12]}
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)
        return {"APP_BUILD": out.decode("utf-8").strip()}
    except Exception:
        return {"APP_BUILD": "dev"}

