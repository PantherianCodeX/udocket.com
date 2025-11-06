from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from doc_tools import postprocess_svg as psvg


def test_parse_svg_returns_none_for_missing(tmp_path: Path) -> None:
    assert psvg.parse_svg(tmp_path / "missing.svg") is None


def test_bounding_box_detects_invalid_path() -> None:
    with pytest.raises(ValueError):
        psvg.bounding_box_from_path("M0 0 L0 0")


def test_process_applies_transformations(tmp_path: Path) -> None:
    svg_file = tmp_path / "diagram.svg"
    svg_content = """
    <svg xmlns="http://www.w3.org/2000/svg">
      <g class="edgeLabel">
        <rect class="background" x="0" y="0" width="10" height="10" />
        <text><tspan>Edge Label</tspan></text>
      </g>
      <g>
        <rect class="actor" x="0" y="0" width="60" height="20" />
        <text><tspan>ExtremelyLongActorName</tspan></text>
      </g>
      <g class="node node-default">
        <path fill="#fff" d="M0 0 L40 0 L40 20 L0 20 Z" />
      </g>
      <rect x="0" y="0" width="5" height="5" />
    </svg>
    """
    svg_file.write_text(svg_content, encoding="utf-8")

    psvg.process(svg_file)

    tree = etree.parse(str(svg_file))
    root = tree.getroot()

    # edge label centered
    label_text = root.xpath(".//svg:g[contains(@class,'edgeLabel')]//svg:text", namespaces=psvg.NS_MAP)[0]
    assert label_text.get("text-anchor") == "middle"

    # actor label wrapped
    actor_text = root.xpath(".//svg:g[svg:rect[contains(@class,'actor')]]/svg:text", namespaces=psvg.NS_MAP)[0]
    tspans = actor_text.findall(f"{psvg.SVG}tspan")
    assert len(tspans) > 1

    # rounded rect inserted for path-based node
    rounded = root.xpath(".//svg:g[contains(@class,'node')]//svg:rect", namespaces=psvg.NS_MAP)
    assert any(rect.get("rx") == "12.0" for rect in rounded)

    # all rectangles have radius applied
    for rect in root.findall(f".{psvg.SVG}rect"):
        assert rect.get("rx") == "12.0"
        assert rect.get("ry") == "12.0"


def test_main_requires_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    rc = psvg.main(["postprocess_svg.py"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "Usage" in captured.err


def test_center_edge_labels_handles_missing_elements() -> None:
    svg = etree.fromstring(
        """
        <svg xmlns="http://www.w3.org/2000/svg">
          <g class="edgeLabel">
            <text>Only text</text>
          </g>
          <g class="edgeLabel">
            <rect class="background" x="NaN" width="10" />
            <text/>
          </g>
        </svg>
        """
    )

    changed = psvg.center_edge_labels(svg)

    assert changed is False


def test_center_edge_labels_cleans_nested_tspans() -> None:
    svg = etree.fromstring(
        """
        <svg xmlns="http://www.w3.org/2000/svg">
          <g class="edgeLabel">
            <rect class="background" x="0" y="0" width="10" height="10" />
            <text>
              <tspan dx="1">
                Inner
                <tspan x="5" />
              </tspan>
            </text>
          </g>
        </svg>
        """
    )

    changed = psvg.center_edge_labels(svg)

    inner = svg.findall(".//{http://www.w3.org/2000/svg}tspan/{http://www.w3.org/2000/svg}tspan")
    assert changed is True
    assert all("x" not in node.attrib for node in inner)


def test_wrap_sequence_actor_labels_skips_single_word() -> None:
    svg = etree.fromstring(
        """
        <svg xmlns="http://www.w3.org/2000/svg">
          <g>
            <rect class="actor" x="0" y="0" width="40" height="20" />
            <text><tspan>Actor</tspan></text>
          </g>
        </svg>
        """
    )

    changed = psvg.wrap_sequence_actor_labels(svg)

    assert changed is False


def test_ensure_rect_radius_skips_divider_class() -> None:
    svg = etree.fromstring(
        """
        <svg xmlns="http://www.w3.org/2000/svg">
          <rect class="divider" rx="5" ry="5" />
        </svg>
        """
    )

    changed = psvg.ensure_rect_radius(svg)

    rect = svg.find(".//{http://www.w3.org/2000/svg}rect")
    assert changed is False
    assert rect.get("rx") == "5"


def test_make_rounded_backplates_ignores_invalid_path() -> None:
    svg = etree.fromstring(
        """
        <svg xmlns="http://www.w3.org/2000/svg">
          <g class="node">
            <path d="M0 0 L10" fill="#fff" />
          </g>
        </svg>
        """
    )

    changed = psvg.make_rounded_backplates(svg)

    assert changed is False


def test_make_rounded_backplates_skips_ineligible_container() -> None:
    svg = etree.fromstring(
        """
        <svg xmlns="http://www.w3.org/2000/svg">
          <g class="node divider">
            <path d="M0 0 L0 10 L10 10 L10 0 Z" fill="#fff" />
          </g>
        </svg>
        """
    )

    changed = psvg.make_rounded_backplates(svg)

    assert changed is False


def test_make_rounded_backplates_transfers_styles() -> None:
    svg = etree.fromstring(
        """
        <svg xmlns="http://www.w3.org/2000/svg">
          <g class="node">
            <g class="row-rect-step">
              <path d="M0 0 L0 20 L30 20 L30 0 Z" fill="#eee" style="opacity:0.5" stroke="none" />
              <path d="M0 0 L0 20 L30 20 L30 0 Z" fill="none" stroke="#222" stroke-width="2" />
            </g>
          </g>
        </svg>
        """
    )

    changed = psvg.make_rounded_backplates(svg)

    rect = svg.find(".//{http://www.w3.org/2000/svg}rect")
    assert changed is False
    assert rect is None


def test_make_rounded_backplates_replaces_path_with_rect() -> None:
    svg = etree.fromstring(
        """
        <svg xmlns="http://www.w3.org/2000/svg">
          <g class="node node-default">
            <path d="M0 0 L0 10 L20 10 L20 0 Z" fill="#ddd" stroke="#444" stroke-width="2" />
          </g>
        </svg>
        """
    )

    changed = psvg.make_rounded_backplates(svg)

    rect = svg.find(".//{http://www.w3.org/2000/svg}rect")
    assert changed is True
    assert rect is not None and rect.get("stroke") == "#444"
