#!/usr/bin/env python3
"""Generate PDFs from MkDocs HTML using shared WeasyPrint styling."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable, Sequence

from weasyprint import CSS, HTML

from doc_tools.config import paths

DOCS_DIR = paths.DOCS_ROOT
SITE_DIR = paths.SITE_DEV_DIR
BUILD_DIR = paths.PDF_DEV_DIR
MKDOCS_CONFIG = paths.DOCS_PACKAGE_ROOT / "mkdocs.yml"
SHARED_CSS = DOCS_DIR / "assets" / "stylesheets" / "weasy.css"


@dataclass(frozen=True)
class PdfTarget:
    name: str
    source: Path
    output: Path
    title: str

    def html_path(self) -> Path:
        relative = self.source.relative_to(DOCS_DIR)
        return SITE_DIR / relative.with_suffix(".html")


PDF_TARGETS: tuple[PdfTarget, ...] = (
    PdfTarget(
        name="tdd",
        source=DOCS_DIR / "overview" / "tdd.md",
        output=BUILD_DIR / "tdd.pdf",
        title="uDocket Technical Design Document",
    ),
    PdfTarget(
        name="prd",
        source=DOCS_DIR / "overview" / "prd.md",
        output=BUILD_DIR / "prd.pdf",
        title="uDocket Product Requirements Document",
    ),
)


def run_mkdocs_build() -> None:
    BUILD_DIR.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "mkdocs",
            "build",
            "--config-file",
            str(MKDOCS_CONFIG),
            "--site-dir",
            str(SITE_DIR),
        ],
        check=True,
    )


def render_target(target: PdfTarget) -> None:
    if not target.source.exists():
        raise FileNotFoundError(f"Markdown source missing for target '{target.name}': {target.source}")

    html_path = target.html_path()
    if not html_path.exists():
        raise FileNotFoundError(
            f"Expected HTML for '{target.name}' at {html_path}. Run mkdocs build first or check nav paths.",
        )

    target.output.parent.mkdir(parents=True, exist_ok=True)

    stylesheets: list[CSS] = [CSS(filename=str(SHARED_CSS))] if SHARED_CSS.exists() else []

    HTML(filename=str(html_path), base_url=str(SITE_DIR)).write_pdf(
        str(target.output),
        stylesheets=stylesheets,
        presentational_hints=True,
    )

    print(f"✓ Wrote {target.output.relative_to(paths.REPO_ROOT)}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        "-t",
        action="append",
        choices=[t.name for t in PDF_TARGETS],
        help="Restrict rendering to specific targets (default: all)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Assume mkdocs build already ran and skip rebuilding the site",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(list(argv) if argv is not None else None)

    targets = PDF_TARGETS
    if args.target:
        selected = {name for name in args.target}
        targets = tuple(target for target in PDF_TARGETS if target.name in selected)

    if not args.skip_build:
        run_mkdocs_build()

    for target in targets:
        render_target(target)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
