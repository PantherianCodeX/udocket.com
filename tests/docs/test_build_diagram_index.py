from __future__ import annotations

from pathlib import Path

import pytest

from scripts.docs import build_diagram_index as bdi


def _setup_diagram_env(tmp_path: Path) -> None:
    src_dir = tmp_path / "docs" / "src"
    appendix = src_dir / "overview" / "tdd" / "appendices" / "diagrams.md"
    appendix.parent.mkdir(parents=True, exist_ok=True)
    appendix.write_text(
        """---
title: diagrams
---

## Overview

<!-- BEGIN AUTO-GENERATED DIAGRAM INDEX -->
_placeholder_
<!-- END AUTO-GENERATED DIAGRAM INDEX -->
""",
        encoding="utf-8",
    )

    service_dir = src_dir / "services" / "alpha"
    diagram_dir = service_dir / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    (service_dir.with_suffix(".md")).write_text("# Alpha\n", encoding="utf-8")

    (diagram_dir / "alpha-flow-v1.mmd").write_text(
        "%% id: alpha-flow\n%% version: v1\nflowchart LR; A-->B;\n", encoding="utf-8"
    )
    (diagram_dir / "alpha-other-v2.mmd").write_text("flowchart LR; B-->C;\n", encoding="utf-8")
    build_dir = src_dir / "build" / "mermaid" / "services" / "alpha" / "diagrams"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "alpha-flow-v1.svg").write_text("<svg/>", encoding="utf-8")
    (build_dir / "alpha-other-v2.svg").write_text("<svg/>", encoding="utf-8")


def test_build_content_renders_tables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_diagram_env(tmp_path)
    src_dir = tmp_path / "docs" / "src"
    appendix = src_dir / "overview" / "tdd" / "appendices" / "diagrams.md"

    monkeypatch.setattr(bdi, "SRC_DIR", src_dir)
    monkeypatch.setattr(bdi, "APPENDIX_FILE", appendix)
    monkeypatch.setattr(bdi, "APPENDIX_DIR", appendix.parent)

    result = bdi.build_content()

    assert "alpha-flow" in result
    assert "| `alpha-flow` | v1 |" in result
    assert "| `alpha-other-v2` | v2 |" in result
    assert 'class="glightbox"' in result


def test_main_updates_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_diagram_env(tmp_path)
    src_dir = tmp_path / "docs" / "src"
    appendix = src_dir / "overview" / "tdd" / "appendices" / "diagrams.md"

    monkeypatch.setattr(bdi, "SRC_DIR", src_dir)
    monkeypatch.setattr(bdi, "APPENDIX_FILE", appendix)
    monkeypatch.setattr(bdi, "APPENDIX_DIR", appendix.parent)

    rc = bdi.main([])
    assert rc == 0

    refreshed = appendix.read_text(encoding="utf-8")
    assert "alpha-flow" in refreshed

    rc_check = bdi.main(["--check"])
    assert rc_check == 0

