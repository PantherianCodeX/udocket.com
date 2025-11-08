from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

from packages.core.agents.compose import graph_visuals as gv
from packages.core.agents.compose.graph_visuals import build_graph_visual_artifacts


def test_measure_text_with_default_font() -> None:
    """_measure_text should fall back to load_default without errors."""

    font = ImageFont.load_default()
    width, height = gv._measure_text(font, "Sample text")  # noqa: SLF001 - exercising internal helper
    assert width > 0
    assert height > 0


def test_build_graph_visual_artifacts_generates_png_and_html(tmp_path: Path) -> None:
    """Graph visual generation should produce well-formed HTML and PNG bytes."""

    payload = {
        "entities": [
            {"id": "alpha", "name": "Alpha Witness", "type": "PERSON"},
            {"id": "beta", "name": "Beta Report", "type": "EVIDENCE"},
        ],
        "relationships": [
            {"source": "alpha", "target": "beta", "label": "references"},
        ],
    }
    artifacts = build_graph_visual_artifacts(
        graph_payload=payload,
        alt_text="",
        size_hint=None,
        notes="Sample relationship",
    )

    assert artifacts.notes == "Sample relationship"
    assert "Relationship graph with 2 entities" in artifacts.html
    assert artifacts.html.strip().startswith("<!DOCTYPE html>")
    assert artifacts.png_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    # Ensure PNG is actually loadable for sanity.
    png_path = tmp_path / "graph.png"
    png_path.write_bytes(artifacts.png_bytes)
    with png_path.open("rb") as handle:
        header = handle.read(8)
    assert header == b"\x89PNG\r\n\x1a\n"


def test_build_graph_visual_artifacts_empty_graph() -> None:
    """Empty inputs should yield a placeholder artefact without errors."""

    payload: dict[str, object] = {"entities": [], "relationships": []}
    artifacts = build_graph_visual_artifacts(
        graph_payload=payload,
        alt_text="",
        size_hint=None,
        notes=None,
    )

    assert "No relationship graph data" in artifacts.html
    assert artifacts.png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
