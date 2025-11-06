from __future__ import annotations

from pathlib import Path


def test_docs_clean_no_render() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8").splitlines()
    try:
        start = next(idx for idx, line in enumerate(makefile) if line.startswith("docs.clean:"))
    except StopIteration:
        raise AssertionError("docs.clean target missing from Makefile")
    commands: list[str] = []
    idx = start + 1
    while idx < len(makefile) and makefile[idx].startswith("\t"):
        commands.append(makefile[idx].strip())
        idx += 1
    assert commands == ["rm -rf docs/build", "rm -rf packages/udocket_docs/build"]
