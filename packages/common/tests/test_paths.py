from __future__ import annotations

# pyright: strict
from pathlib import Path

from packages.common.paths import CasePaths, build_case_paths


def test_build_case_paths_sets_expected_subdirs(tmp_path: Path) -> None:
    paths = build_case_paths(tmp_path / "cases" / "abc")
    assert isinstance(paths, CasePaths)
    assert paths.root.name == "abc"
    assert paths.audio == paths.root / "audio"
    assert paths.transcript == paths.root / "transcript"
    assert paths.analysis == paths.root / "analysis"
    assert paths.ops == paths.root / "ops"
    assert paths.docs == paths.root / "docs"


def test_case_paths_ensure_creates_directories(tmp_path: Path) -> None:
    base = tmp_path / "tenant" / "cases" / "abc"
    paths = build_case_paths(base)
    paths.ensure()

    assert paths.audio.is_dir()
    assert paths.transcript.is_dir()
    assert paths.analysis.is_dir()
    assert paths.ops.is_dir()
    assert paths.docs.is_dir()
