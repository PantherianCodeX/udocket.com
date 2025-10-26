#!/usr/bin/env python3
"""
Post-process Mermaid-rendered SVGs to smooth out styling quirks.

Currently handles:
  * Centering ER edge labels (including multi-line spans) within their pill.
  * Swapping the square path-based node backplates for rounded <rect> elements.
  * Applying a consistent border radius to any native <rect> nodes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable, Tuple

from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"
SVG = f"{{{SVG_NS}}}"
NS_MAP = {"svg": SVG_NS}


def parse_svg(path: Path) -> etree._ElementTree | None:
    if not path.exists():
        return None
    parser = etree.XMLParser(remove_comments=False)
    return etree.parse(str(path), parser)


def float_pairs_from_path(d: str) -> Tuple[Iterable[float], Iterable[float]]:
    values = [float(match) for match in re.findall(r"[-+]?(?:\d+\.\d+|\d+)", d)]
    if len(values) < 8 or len(values) % 2 != 0:
        raise ValueError("path does not look like a rectangle")
    xs = values[0::2]
    ys = values[1::2]
    return xs, ys


def bounding_box_from_path(d: str) -> Tuple[float, float, float, float]:
    xs, ys = float_pairs_from_path(d)
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    width, height = x_max - x_min, y_max - y_min
    if width <= 0 or height <= 0:
        raise ValueError("degenerate rectangle")
    return x_min, y_min, width, height


def center_edge_labels(root: etree._Element) -> bool:
    line_height_em = 1.1
    pad_x = 8.0
    pad_y = 4.0
    changed = False
    for label in root.xpath(".//svg:g[contains(@class,'edgeLabel')]", namespaces=NS_MAP):
        text = label.find(f".//{SVG}text")
        rect = label.find(f".//{SVG}rect[@class='background']")
        if text is None or rect is None:
            continue
        try:
            rect_x = float(rect.get("x", "0"))
            rect_width = float(rect.get("width", "0"))
            rect_y = float(rect.get("y", "0"))
            rect_height = float(rect.get("height", "0"))
        except ValueError:
            continue
        if rect.get("data-udocket-pill") != "1":
            rect_width += pad_x * 2.0
            rect_height += pad_y * 2.0
            rect_x -= pad_x
            rect_y -= pad_y
            rect.set("width", f"{rect_width}")
            rect.set("height", f"{rect_height}")
            rect.set("x", f"{rect_x}")
            rect.set("y", f"{rect_y}")
            rect.set("data-udocket-pill", "1")
        center_x = rect_x + rect_width / 2.0
        center_y = rect_y + rect_height / 2.0
        text.set("text-anchor", "middle")
        text.set("x", f"{center_x}")
        text.set("y", f"{center_y}")
        text.set("dominant-baseline", "middle")
        text.set("alignment-baseline", "middle")

        lines = list(text.findall(f"./{SVG}tspan"))
        if not lines:
            continue
        initial_offset = -line_height_em * (len(lines) - 1) / 2.0
        for idx, line in enumerate(lines):
            line.set("x", f"{center_x}")
            line.attrib.pop("dx", None)
            line.attrib.pop("y", None)
            line.attrib["dy"] = f"{initial_offset:.3f}em" if idx == 0 else f"{line_height_em:.3f}em"
            for inner in line.findall(f".//{SVG}tspan"):
                inner.attrib.pop("x", None)
                inner.attrib.pop("dx", None)
        changed = True
    return changed


def wrap_sequence_actor_labels(root: etree._Element) -> bool:
    changed = False
    line_height_em = 1.1
    avg_char_px = 8.0
    padding_px = 16.0

    for group in root.xpath(".//svg:g[svg:rect[contains(@class,'actor')]]", namespaces=NS_MAP):
        rect = group.find(f"./{SVG}rect")
        text = group.find(f"./{SVG}text")
        if rect is None or text is None:
            continue
        content = " ".join(" ".join(tspan.itertext()).strip() for tspan in text.findall(f"./{SVG}tspan")).strip()
        if not content or len(content.split()) <= 1:
            segments = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z]|$)", content)
            if len(segments) <= 1:
                continue
            content = " ".join(segments)
        try:
            width = float(rect.get("width", "0"))
            rect_x = float(rect.get("x", "0"))
            rect_y = float(rect.get("y", "0"))
            rect_height = float(rect.get("height", "0"))
        except ValueError:
            continue

        max_chars = max(1, int((width - padding_px) / avg_char_px))
        words = content.split()
        lines: list[str] = []
        current: list[str] = []
        for word in words:
            tentative = " ".join(current + [word]) if current else word
            if len(tentative) <= max_chars or not current:
                current.append(word)
            else:
                lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))
        if len(lines) <= 1:
            continue

        center_x = rect_x + width / 2.0
        text.set("x", f"{center_x}")
        text.set("text-anchor", "middle")
        text.set("dominant-baseline", "middle")
        text.set("alignment-baseline", "middle")
        text.set("y", f"{rect_y + rect_height / 2.0}")

        for node in list(text):
            text.remove(node)

        initial_offset = -line_height_em * (len(lines) - 1) / 2.0
        for idx, line in enumerate(lines):
            tspan = etree.Element(f"{SVG}tspan")
            if idx == 0:
                tspan.set("dy", f"{initial_offset:.3f}em")
            else:
                tspan.set("dy", f"{line_height_em:.3f}em")
            tspan.set("x", f"{center_x}")
            tspan.text = line
            text.append(tspan)
        changed = True
    return changed


def ensure_rect_radius(root: etree._Element, radius: float = 12.0) -> bool:
    changed = False
    for rect in root.findall(f".//{SVG}rect"):
        cls = rect.get("class", "")
        if "divider" in cls or "row-rect" in cls and "background" not in cls:
            continue
        if rect.get("rx") != f"{radius}":
            rect.set("rx", f"{radius}")
            changed = True
        if rect.get("ry") != f"{radius}":
            rect.set("ry", f"{radius}")
            changed = True
    return changed


def make_rounded_backplates(root: etree._Element, radius: float = 12.0) -> bool:
    changed = False

    def eligible_container(path: etree._Element) -> etree._Element | None:
        for ancestor in path.iterancestors(f"{SVG}g"):
            cls = ancestor.get("class") or ""
            tokens = cls.split()
            if any(token.startswith(prefix) for token in tokens for prefix in ("divider", "subGraph")):
                return None
            if any(token.startswith("row-rect") for token in tokens):
                return ancestor
            if any(
                token in ("node", "node-default", "node_default", "classGroup", "cluster")
                or token.startswith("node")
                for token in tokens
            ):
                return ancestor
        return None
    def process_path(path: etree._Element, container: etree._Element, radius_multiplier: float = 1.0) -> None:
        nonlocal changed
        try:
            x, y, width, height = bounding_box_from_path(path.get("d", ""))
        except ValueError:
            return
        parent = path.getparent()
        if parent is None:
            return
        sibling_paths = [
            sibling for sibling in parent
            if isinstance(sibling.tag, str)
            and sibling.tag == f"{SVG}path"
            and sibling is not path
            and sibling.get("stroke") not in (None, "none")
        ]
        stroke_path = sibling_paths[0] if sibling_paths else None

        rect_attrs = {
            "x": f"{x}",
            "y": f"{y}",
            "width": f"{width}",
            "height": f"{height}",
            "rx": f"{radius * radius_multiplier}",
            "ry": f"{radius * radius_multiplier}",
            "fill": path.get("fill", "#fff"),
        }
        container_class = container.get("class") or ""
        if container_class:
            rect_attrs["class"] = container_class
        for attr in ("fill-opacity", "style", "class"):
            val = path.get(attr)
            if val:
                rect_attrs[attr] = val
        stroke = None
        stroke_width = None
        stroke_dash = None
        if stroke_path is not None:
            stroke = stroke_path.get("stroke")
            stroke_width = stroke_path.get("stroke-width")
            stroke_dash = stroke_path.get("stroke-dasharray")
        else:
            stroke = path.get("stroke")
            stroke_width = path.get("stroke-width")
            stroke_dash = path.get("stroke-dasharray")
        if stroke and stroke != "none":
            rect_attrs["stroke"] = stroke
        if stroke_width:
            rect_attrs["stroke-width"] = stroke_width
        if stroke_dash:
            rect_attrs["stroke-dasharray"] = stroke_dash

        rounded_rect = etree.Element(f"{SVG}rect", rect_attrs)
        parent.insert(0, rounded_rect)
        parent.remove(path)
        if stroke_path is not None and stroke_path in parent:
            parent.remove(stroke_path)
        changed = True

    for path in root.xpath(".//svg:path[@fill]", namespaces=NS_MAP):
        fill = path.get("fill")
        if not fill or fill == "none":
            continue
        container = eligible_container(path)
        if container is None:
            continue
        cls = container.get("class", "")
        tokens = cls.split()
        if any(token.startswith("row-rect") for token in tokens):
            continue
        radius_multiplier = 1.0
        process_path(path, container, radius_multiplier)

    return changed


def process(svg_path: Path) -> None:
    tree = parse_svg(svg_path)
    if tree is None:
        return
    root = tree.getroot()

    changed = False
    changed |= center_edge_labels(root)
    changed |= ensure_rect_radius(root)
    changed |= make_rounded_backplates(root)
    changed |= wrap_sequence_actor_labels(root)

    if changed:
        svg_path.write_text(etree.tostring(root, encoding="unicode"))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: postprocess_svg.py <svg> [...]", file=sys.stderr)
        return 1
    for arg in argv[1:]:
        process(Path(arg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
