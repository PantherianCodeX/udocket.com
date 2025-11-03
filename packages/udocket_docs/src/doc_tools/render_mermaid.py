from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from collections.abc import Iterable
from typing import Sequence

from doc_tools import paths
from doc_tools.postprocess_svg import process as postprocess_svg

DEFAULT_SRC = paths.DOCS_ROOT
DEFAULT_OUT = paths.BUILD_ROOT / "diagrams"
DEFAULT_PUPPETEER_CONFIG = paths.CONFIG_ROOT / "puppeteer.config.json"
DEFAULT_CONFIG = paths.CONFIG_ROOT / "mermaid.config.json"
DEFAULT_DIFF_BASE = "origin/main"


def detect_cli(cli_override: Sequence[str] | None = None) -> list[str]:
    if cli_override:
        return list(cli_override)
    mmdc = shutil.which("mmdc")
    if mmdc:
        return [mmdc]
    return ["npx", "--yes", "@mermaid-js/mermaid-cli"]


def git_changed(diff_base: str, repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--name-only", "--diff-filter=ACMRTUXB", diff_base, "--", "*.mmd"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return [repo_root / line for line in files]


def render_file(
    source: Path,
    destination: Path,
    cli: list[str],
    puppeteer_config: Path | None,
    cli_config: Path | None,
    fmt: str,
    verbose: bool,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    cmd = [*cli, "-i", str(source), "-o", str(destination)]
    if puppeteer_config and puppeteer_config.exists():
        cmd.extend(["-p", str(puppeteer_config)])
    if cli_config and cli_config.exists():
        cmd.extend(["-c", str(cli_config)])
    if verbose:
        print("Rendering", source.relative_to(paths.REPO_ROOT), "->", destination.relative_to(paths.REPO_ROOT))
    subprocess.run(cmd, check=True)
    if fmt == "svg" and destination.exists():
        postprocess_svg(destination)


def _is_diagram(path: Path) -> bool:
    return "diagrams" in path.parts and path.suffix.lower() == ".mmd"


def _dedupe_sorted(paths_iter: Iterable[Path]) -> list[Path]:
    unique: dict[Path, None] = {}
    for candidate in paths_iter:
        unique[candidate] = None
    return sorted(unique)


def _gather_from_paths(paths_args: list[Path]) -> list[Path]:
    resolved: list[Path] = []
    for candidate in paths_args:
        target = candidate.resolve()
        if target.is_dir():
            resolved.extend(path for path in target.rglob("*.mmd") if _is_diagram(path))
        elif target.suffix.lower() == ".mmd":
            resolved.append(target)
    return _dedupe_sorted(resolved)


def collect_sources(mode: str, repo_root: Path, src_root: Path, diff_base: str, paths_args: list[Path]) -> list[Path]:
    if mode == "paths":
        return _gather_from_paths(paths_args)
    if mode == "all":
        return _dedupe_sorted(path for path in src_root.rglob("*.mmd") if _is_diagram(path))
    if mode == "changed":
        changed = [
            path
            for path in git_changed(diff_base, repo_root)
            if path.exists() and _is_diagram(path)
        ]
        return _dedupe_sorted(changed)
    raise ValueError(f"Unknown mode {mode}")


def build_output_relative(source: Path, src_root: Path) -> Path:
    try:
        rel = source.relative_to(src_root)
    except ValueError:
        rel = source.name
        return Path(rel)
    parts = list(rel.parts)
    if "diagrams" in parts:
        idx = parts.index("diagrams")
        trimmed = parts[:idx] + parts[idx + 1 :]
        if trimmed:
            return Path(*trimmed)
        return Path(source.name)
    return rel


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Mermaid diagrams with consistent defaults.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--all",
        action="store_true",
        help="Render every Mermaid source found under the docs tree (diagrams directories only)",
    )
    group.add_argument("--changed", action="store_true", help="Render only files changed relative to --diff-base")
    group.add_argument("--paths", nargs="*", default=None, help="Explicit Mermaid source file paths")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help="Destination directory for rendered diagrams")
    parser.add_argument("--format", choices=["svg", "png"], default="svg", help="Rendered output format")
    parser.add_argument("--diff-base", default=DEFAULT_DIFF_BASE, help="Git commit/ref to diff against in --changed mode")
    parser.add_argument(
        "--cli",
        help="Override Mermaid CLI command (e.g. 'mmdc' or 'docker run ...').",
    )
    parser.add_argument("--verbose", action="store_true", help="Print rendered files")
    parser.add_argument(
        "--src-root",
        type=Path,
        default=DEFAULT_SRC,
        help="Root directory to scan for Mermaid sources (defaults to the docs root)",
    )
    parser.add_argument("sources", nargs="*", help="Alias for --paths")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    mode: str
    paths_args: list[Path] = []
    if args.paths is not None or args.sources:
        mode = "paths"
        path_values: list[str] = list(args.paths or [])
        source_values: list[str] = list(args.sources)
        combined = [*path_values, *source_values]
        paths_args = [Path(p) for p in combined]
    elif args.all:
        mode = "all"
    else:
        mode = "changed"

    cli_override = shlex.split(args.cli) if args.cli else None
    cli = detect_cli(cli_override)
    sources = collect_sources(mode, paths.REPO_ROOT, args.src_root, args.diff_base, paths_args)
    if not sources:
        if args.verbose:
            print("No Mermaid sources to render", file=sys.stderr)
        return 0

    for source in sources:
        if not source.exists():
            continue
        rel = build_output_relative(source, args.src_root)
        destination = args.out_dir / rel.with_suffix(f".{args.format}")
        render_file(
            source,
            destination,
            cli,
            DEFAULT_PUPPETEER_CONFIG if DEFAULT_PUPPETEER_CONFIG.exists() else None,
            DEFAULT_CONFIG if DEFAULT_CONFIG.exists() else None,
            args.format,
            args.verbose,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
