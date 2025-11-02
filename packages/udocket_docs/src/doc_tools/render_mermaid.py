from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from doc_tools import paths
from doc_tools.postprocess_svg import process as postprocess_svg

DEFAULT_SRC = paths.DOCS_ROOT / "diagrams"
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


def collect_sources(mode: str, repo_root: Path, src_root: Path, diff_base: str, paths_args: list[Path]) -> list[Path]:
    if mode == "paths":
        return [p.resolve() for p in paths_args]
    if mode == "all":
        return sorted(src_root.rglob("*.mmd"))
    if mode == "changed":
        return [p for p in git_changed(diff_base, repo_root) if p.exists()]
    raise ValueError(f"Unknown mode {mode}")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Mermaid diagrams with consistent defaults.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Render every Mermaid source under docs/diagrams")
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
    parser.add_argument("--src-root", type=Path, default=DEFAULT_SRC, help="Source directory to scan for diagrams")
    parser.add_argument("sources", nargs="*", help="Alias for --paths")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    mode: str
    paths_args: list[Path] = []
    if args.paths is not None or args.sources:
        mode = "paths"
        paths_args = [Path(p) for p in (args.paths or [])]
        paths_args.extend(Path(p) for p in args.sources)
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
        rel = source.relative_to(args.src_root)
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
