from __future__ import annotations

from pathlib import Path

from doc_tools import check_repository_trees as crt


def write_appendix(root: Path, tree_body: str) -> Path:
    appendix = root / "docs" / "overview" / "tdd" / "appendices" / "repository_trees.md"
    appendix.parent.mkdir(parents=True, exist_ok=True)
    appendix.write_text(
        "### Example Section\n\n```tree\n" + tree_body + "\n```\n",
        encoding="utf-8",
    )
    return appendix


def test_success_when_paths_exist(tmp_path):
    (tmp_path / "apps" / "web").mkdir(parents=True)
    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "api.md").write_text("{}", encoding="utf-8")
    appendix = write_appendix(
        tmp_path,
        "apps/\n  web/\nservices/\n  api.md\n",
    )

    exit_code = crt.main(["--appendix", str(appendix), "--repo-root", str(tmp_path)])
    assert exit_code == 0


def test_missing_path_reports_error(tmp_path, capsys):
    (tmp_path / "apps").mkdir()
    appendix = write_appendix(tmp_path, "apps/\n  portal/\n")

    exit_code = crt.main(["--appendix", str(appendix), "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing path 'apps/portal'" in captured.err


def test_type_mismatch_detected(tmp_path, capsys):
    file_path = tmp_path / "configs"
    file_path.write_text("{}", encoding="utf-8")
    appendix = write_appendix(tmp_path, "configs/\n")

    exit_code = crt.main(["--appendix", str(appendix), "--repo-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "expected directory for 'configs'" in captured.err

