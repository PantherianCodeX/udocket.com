from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    import sys

    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[2]))
    from scripts.typing.common import DOCS_ROOT, PROJECT_ROOT  # type: ignore[import-not-found]
else:
    from .common import DOCS_ROOT, PROJECT_ROOT

STATUS_FILE = DOCS_ROOT / "typing" / "automation_status.md"


def format_helper_table(helpers: Sequence[Mapping[str, Any]]) -> str:
    if not helpers:
        return "_No helper runs recorded._"
    headers = "| Helper | Version | Status | Last Run |\n| --- | --- | --- | --- |"
    rows = [
        f"| {item.get('name')} | {item.get('version', '-') } | {item.get('status', '-')} | {item.get('lastRun', '-') } |"
        for item in helpers
    ]
    return "\n".join([headers, *rows])


def format_strict_list(strict_modules: Sequence[Mapping[str, Any]]) -> str:
    if not strict_modules:
        return "_No modules recorded._"
    lines = [f"- `{item.get('path')}` (verified {item.get('verifiedAt')})" for item in strict_modules]
    return "\n".join(lines)


def sync_status(manifest: Mapping[str, Any]) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    pyright_stats = manifest.get("pyrightStats") or {}
    helpers = manifest.get("helpers") or []
    strict_modules = manifest.get("strictModules") or []

    content = [
        "# Typing Automation Status",
        "",
        f"Last updated: {manifest.get('recordedAt', 'unknown')}",
        "",
        "## Pyright Snapshot",
        "",
        f"Command: `{pyright_stats.get('command', 'pyright --stats')}`",
    ]
    if output := pyright_stats.get("output"):
        content.extend(["", "```", output.strip(), "```"])
    else:
        content.append("\n_No pyright output recorded._")

    content.extend(
        [
            "",
            "## Helpers",
            "",
            format_helper_table(helpers),
            "",
            "## Strict Modules",
            "",
            format_strict_list(strict_modules),
        ]
    )
    STATUS_FILE.write_text("\n".join(content) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate automation status documentation from manifest.")
    parser.add_argument("manifest", nargs="?", default="docs/typing/automation_manifest.json", type=Path)
    args = parser.parse_args()

    manifest_path = args.manifest if args.manifest.is_absolute() else PROJECT_ROOT / args.manifest
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sync_status(manifest)

    print(f"Updated {STATUS_FILE.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
