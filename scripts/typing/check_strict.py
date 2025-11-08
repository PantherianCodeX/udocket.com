#!/usr/bin/env python3
"""Targeted pyright/mypy runs for entries in the typing automation manifest."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:  # pragma: no cover - script entrypoint
    import sys as _sys
    from pathlib import Path as _Path

    _sys.path.append(str(_Path(__file__).resolve().parents[2]))
    from scripts.typing.common import (  # type: ignore[import-not-found]
        PROJECT_ROOT,
        run_command,
    )
else:  # pragma: no cover - imported usage
    from .common import PROJECT_ROOT, run_command


DEFAULT_MANIFEST = PROJECT_ROOT / "docs/typing/automation_manifest.json"


@dataclass
class ToolResult:
    exit_code: int
    diagnostics: int


def _load_strict_paths(manifest_path: Path) -> list[str]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = data.get("strictModules", [])
    paths: list[str] = []
    for entry in entries:
        path = entry.get("path")
        verified_at = entry.get("verifiedAt")
        if not path or not verified_at:
            continue
        paths.append(path)
    # Preserve manifest order while removing duplicates
    unique = list(dict.fromkeys(paths))
    return unique


def _print_module_list(paths: Sequence[str]) -> None:
    width = len(str(len(paths))) or 1
    for idx, path in enumerate(paths, 1):
        print(f"{idx:>{width}}. {path}")


def _resolve_modules(paths: Sequence[str], selections: Sequence[str] | None) -> list[str]:
    if not selections:
        return list(paths)

    resolved: list[str] = []
    for sel in selections:
        sel = sel.strip()
        if not sel:
            continue
        if sel.isdigit():
            index = int(sel) - 1
            if index < 0 or index >= len(paths):
                raise ValueError(f"Module index out of range: {sel}")
            resolved.append(paths[index])
            continue

        matches = [path for path in paths if sel in path]
        if not matches:
            raise ValueError(f"No manifest entry matches '{sel}'")
        resolved.extend(matches)

    # Maintain original manifest ordering but remove duplicates
    manifest_index = {path: idx for idx, path in enumerate(paths)}
    unique = sorted(dict.fromkeys(resolved), key=lambda p: manifest_index.get(p, 10**9))
    return unique


def _format_pyright_diagnostic(diag: dict[str, object]) -> str:
    path = diag.get("filePath", "<unknown>")
    range_obj = diag.get("range", {})
    start = range_obj.get("start", {}) if isinstance(range_obj, dict) else {}
    line = start.get("line", 0)
    character = start.get("character", 0)
    severity = diag.get("severity", "error")
    message = diag.get("message", "")
    rule = diag.get("rule", "")
    suffix = f" ({rule})" if rule else ""
    return f"{severity.upper()} {path}:{line + 1}:{character + 1}: {message}{suffix}"


def _pyright_relative_filter(diag_path: str, target: Path) -> bool:
    diag_path_resolved = Path(diag_path).resolve()
    if target.is_dir():
        try:
            diag_path_resolved.relative_to(target)
            return True
        except ValueError:
            return False
    return diag_path_resolved == target


def _run_pyright(path: str, extra_args: Sequence[str], focus: bool) -> ToolResult:
    target = (PROJECT_ROOT / path).resolve()
    cmd = ["pyright", path]

    capture_output = focus and "--outputjson" not in extra_args
    if capture_output:
        cmd.append("--outputjson")
    cmd.extend(extra_args)

    result = run_command(cmd, check=False)

    if not focus:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return ToolResult(result.returncode, -1)

    # Focused mode: filter diagnostics to the target path only
    payload_str = result.stdout or result.stderr
    try:
        payload = json.loads(payload_str)
        diagnostics = payload.get("generalDiagnostics", [])
    except json.JSONDecodeError:
        print(payload_str, end="")
        return ToolResult(max(result.returncode, 1), 0)

    filtered = [
        d for d in diagnostics if _pyright_relative_filter(str(d.get("filePath", "")), target)
    ]

    if not filtered:
        print(f"pyright: no diagnostics for {path}")
        return ToolResult(0, 0)

    print(f"pyright diagnostics for {path}:")
    for diag in filtered:
        print("  " + _format_pyright_diagnostic(diag))
    return ToolResult(1, len(filtered))


def _run_mypy(path: str, extra_args: Sequence[str], focus: bool) -> ToolResult:
    cmd = [sys.executable, "-m", "mypy", path]

    focus_args = [
        "--follow-imports=skip",
        "--show-error-codes",
        "--hide-error-context",
        "--no-error-summary",
    ]
    if focus:
        for arg in focus_args:
            if arg not in extra_args:
                cmd.append(arg)
    cmd.extend(extra_args)

    result = run_command(cmd, check=False)
    output = result.stdout.strip()
    stderr = result.stderr.strip()

    if not focus:
        if output:
            print(output)
        if stderr:
            print(stderr, file=sys.stderr)
        return ToolResult(result.returncode, -1)

    rel_path = path
    abs_path = str((PROJECT_ROOT / path).resolve())
    filtered_lines = [
        line
        for line in output.splitlines()
        if line.startswith(rel_path + ":") or line.startswith(abs_path + ":")
    ]

    if not filtered_lines:
        print(f"mypy: no diagnostics for {path}")
        return ToolResult(0, 0)

    print(f"mypy diagnostics for {path}:")
    for line in filtered_lines:
        print("  " + line)
    return ToolResult(1, len(filtered_lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to automation manifest (default: %(default)s)",
    )
    parser.add_argument(
        "--module",
        action="append",
        help=(
            "Focus on specific manifest entries by index or substring. "
            "Use multiple times to queue several modules."
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the manifest entries and exit",
    )
    parser.add_argument(
        "--tool",
        choices=["pyright", "mypy", "both"],
        default="both",
        help="Select which tooling to run (default: both)",
    )
    parser.add_argument(
        "--pyright-arg",
        dest="pyright_args",
        action="append",
        default=[],
        help="Extra argument passed to pyright (repeatable)",
    )
    parser.add_argument(
        "--mypy-arg",
        dest="mypy_args",
        action="append",
        default=[],
        help="Extra argument passed to mypy (repeatable)",
    )
    parser.add_argument(
        "--stop-on-first",
        action="store_true",
        help="Stop after the first module that reports diagnostics",
    )

    args = parser.parse_args()

    if not args.manifest.exists():
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        return 1

    manifest_paths = _load_strict_paths(args.manifest)
    if args.list:
        _print_module_list(manifest_paths)
        return 0

    try:
        selected_paths = _resolve_modules(manifest_paths, args.module)
    except ValueError as exc:  # pragma: no cover - argument validation
        print(str(exc), file=sys.stderr)
        return 2

    if not selected_paths:
        print("No modules selected.")
        return 0

    focus_mode = bool(args.module)
    pyright_failures = 0
    mypy_failures = 0

    for module_path in selected_paths:
        print(f"\n=== {module_path} ===")

        if args.tool in {"pyright", "both"}:
            result = _run_pyright(module_path, args.pyright_args, focus_mode)
            if result.diagnostics > 0:
                pyright_failures += result.diagnostics
            if args.stop_on_first and result.diagnostics > 0:
                break

        if args.tool in {"mypy", "both"}:
            result = _run_mypy(module_path, args.mypy_args, focus_mode)
            if result.diagnostics > 0:
                mypy_failures += result.diagnostics
            if args.stop_on_first and result.diagnostics > 0:
                break

    if focus_mode:
        print("\nSummary (focused run):")
        if args.tool in {"pyright", "both"}:
            print(f"  pyright diagnostics: {pyright_failures}")
        if args.tool in {"mypy", "both"}:
            print(f"  mypy diagnostics: {mypy_failures}")

    return 0 if (pyright_failures + mypy_failures) == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
