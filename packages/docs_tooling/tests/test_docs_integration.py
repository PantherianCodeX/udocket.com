from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urljoin

import pytest

from doc_tools.check import structure as cs
from doc_tools.common import doc_utils


from config.paths import REPO_ROOT
DOCS_SRC = REPO_ROOT / "docs"
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:", "javascript:", "data:")
LINK_RE = re.compile(r'href="([^"]+)"')


@pytest.fixture(scope="session")
def built_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    site_dir = tmp_path_factory.mktemp("site")
    env = os.environ.copy()
    cmd = [
        "uv",
        "run",
        "--project",
        "packages/docs_tooling",
        "--extra",
        "dev",
        "mkdocs",
        "build",
        "--strict",
        "-f",
        str(REPO_ROOT / "packages" / "docs_tooling" / "mkdocs.yml"),
        "-d",
        str(site_dir),
    ]
    subprocess.run(cmd, check=True, cwd=REPO_ROOT, env=env)
    return site_dir


def test_docs_lint_script_runs_on_repo() -> None:
    subprocess.run(["make", "docs.lint"], check=True, cwd=REPO_ROOT)


def test_mkdocs_build_produces_expected_pages(built_site: Path) -> None:
    expected_paths = [
        built_site / "index.html",
        built_site / "overview" / "tdd.html",
        built_site / "automation" / "lp-engine.html",
        built_site / "platform" / "settings.html",
    ]
    missing = [path for path in expected_paths if not path.exists()]
    assert not missing, f"Expected MkDocs outputs missing: {missing}"


def test_site_internal_anchor_integrity(built_site: Path) -> None:
    for html_file in built_site.rglob("*.html"):
        html = html_file.read_text(encoding="utf-8", errors="ignore")
        anchors = set(re.findall(r'id="([^"]+)"', html))
        for target in re.findall(r'href="#([^"]+)"', html):
            if not target or target.startswith(("!", "%")):
                continue
            assert target in anchors, f"Missing anchor '#{target}' in {html_file}"


def test_site_internal_links_resolve(built_site: Path) -> None:
    missing: list[tuple[Path, str]] = []

    for html_file in built_site.rglob("*.html"):
        html = html_file.read_text(encoding="utf-8", errors="ignore")
        for href in LINK_RE.findall(html):
            if not href or href.startswith("#"):
                continue
            if href.startswith(EXTERNAL_SCHEMES):
                continue
            path_part = href.split("#", 1)[0].split("?", 1)[0]
            if not path_part:
                continue
            base = html_file.relative_to(built_site).as_posix()
            resolved_href = urljoin(base, path_part)
            if resolved_href.startswith("/"):
                target = built_site / resolved_href.lstrip("/")
            else:
                target = built_site / resolved_href
            if not target.exists():
                missing.append((html_file, href))

    assert not missing, "Missing link targets:\n" + "\n".join(f"{source}: {href}" for source, href in missing)


def test_docs_scripts_typecheck() -> None:
    cmd = [
        "uv",
        "run",
        "--project",
        "packages/docs_tooling",
        "--extra",
        "dev",
        "pyright",
        "--project",
        str(REPO_ROOT / "pyrightconfig.docs-scripts.json"),
    ]
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)


def test_preamble_divider_convention_preserved() -> None:
    assert doc_utils.PREAMBLE_DIVIDER == "**|**"
    template = DOCS_SRC / "_template.md"
    specs = cs.build_template_spec(template)
    assert specs, "Template must define sections"
    first_section = specs[0]
    for label in first_section.preamble_order[:-1]:
        assert first_section.preamble_requires_marker[label] is True
