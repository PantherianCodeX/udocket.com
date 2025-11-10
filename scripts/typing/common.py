from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from config.paths import REPO_ROOT
from typing import Any

PROJECT_ROOT = REPO_ROOT
DOCS_ROOT = PROJECT_ROOT / "docs"
TYPING_DOCS_ROOT = DOCS_ROOT / "typing"
MANIFEST_PATH = TYPING_DOCS_ROOT / "automation_manifest.json"
STRICT_MANIFEST_PATH = TYPING_DOCS_ROOT / "strict_manifest.json"
CACHE_ROOT = PROJECT_ROOT / ".cache" / "typing"


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def run_command(args: Iterable[str], cwd: Path | None = None, check: bool = True) -> CommandResult:
    """Run a subprocess command and capture output."""
    completed = subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"Command {' '.join(args)} failed with code {completed.returncode}: {completed.stderr.strip()}"
        )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def ensure_cache_dir() -> Path:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    return CACHE_ROOT


def load_manifest() -> MutableMapping[str, Any]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {
        "recordedAt": None,
        "pyrightStats": None,
        "helpers": [],
        "strictModules": [],
        "notes": [],
    }


def save_manifest(manifest: Mapping[str, Any]) -> None:
    TYPING_DOCS_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def upsert_helper_record(
    manifest: MutableMapping[str, Any],
    *,
    name: str,
    version: str,
    status: str,
    last_run: datetime | None = None,
) -> None:
    helpers: list[dict[str, Any]] = list(manifest.get("helpers", []))
    updated = False
    for helper in helpers:
        if helper.get("name") == name:
            helper.update(
                {
                    "version": version,
                    "status": status,
                    "lastRun": (
                        last_run.astimezone(UTC).isoformat()
                        if last_run
                        else helper.get("lastRun")
                    ),
                }
            )
            updated = True
            break
    if not updated:
        helpers.append(
            {
                "name": name,
                "version": version,
                "status": status,
                "lastRun": (last_run.astimezone(UTC).isoformat() if last_run else None),
            }
        )
    manifest["helpers"] = sorted(helpers, key=lambda item: item.get("name", ""))


def record_pyright_stats(
    manifest: MutableMapping[str, Any],
    *,
    command: str,
    stdout: str,
) -> None:
    manifest["pyrightStats"] = {
        "command": command,
        "output": stdout,
        "recordedAt": datetime.now(UTC).isoformat(),
    }


def append_strict_manifest(path: Path) -> None:
    STRICT_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if STRICT_MANIFEST_PATH.exists():
        existing = json.loads(STRICT_MANIFEST_PATH.read_text(encoding="utf-8"))
    entry = {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "verifiedAt": datetime.now(UTC).isoformat(),
    }
    filtered = [item for item in existing if item.get("path") != entry["path"]]
    filtered.append(entry)
    filtered.sort(key=lambda item: item["path"])
    STRICT_MANIFEST_PATH.write_text(
        json.dumps(filtered, indent=2) + "\n",
        encoding="utf-8",
    )


def resolve_python(venv_path: Path) -> Path:
    candidates = [venv_path / "bin" / "python", venv_path / "Scripts" / "python.exe"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Unable to locate python executable in {venv_path}")
