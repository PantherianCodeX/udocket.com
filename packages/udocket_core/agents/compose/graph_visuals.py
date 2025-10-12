# pyright: strict

"""Deterministic rendering helpers for compose graph visuals."""

from __future__ import annotations

import math
from dataclasses import dataclass
from html import escape
from io import BytesIO
from typing import Mapping, Sequence

from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]

from ...utils.json import (
    JSONObject,
    JSONValue,
    coerce_json_object,
    coerce_object_list,
    coerce_str,
)


@dataclass(frozen=True)
class GraphNode:
    key: str
    label: str
    kind: str


@dataclass(frozen=True)
class GraphEdge:
    source: GraphNode
    target: GraphNode
    label: str


@dataclass(frozen=True)
class GraphVisualArtifacts:
    html: str
    png_bytes: bytes
    notes: str | None


DEFAULT_WIDTH = 960
DEFAULT_HEIGHT = 640
NODE_RADIUS = 28
SVG_PADDING = 48

NODE_COLORS: Mapping[str, str] = {
    "PERSON": "#2563eb",
    "ORGANIZATION": "#0ea5e9",
    "COMPANY": "#0ea5e9",
    "AGENCY": "#0ea5e9",
    "LOCATION": "#16a34a",
    "PLACE": "#16a34a",
    "EVIDENCE": "#f97316",
    "ISSUE": "#f59e0b",
}

PNG_COLORS: Mapping[str, tuple[int, int, int]] = {
    "PERSON": (37, 99, 235),
    "ORGANIZATION": (14, 165, 233),
    "COMPANY": (14, 165, 233),
    "AGENCY": (14, 165, 233),
    "LOCATION": (22, 163, 74),
    "PLACE": (22, 163, 74),
    "EVIDENCE": (249, 115, 22),
    "ISSUE": (245, 158, 11),
}


def build_graph_visual_artifacts(
    *,
    graph_payload: JSONObject,
    alt_text: str,
    size_hint: Mapping[str, JSONValue] | None = None,
    notes: str | None = None,
) -> GraphVisualArtifacts:
    """Generate polished HTML + PNG artifacts for a relationship graph."""

    nodes = _parse_nodes(graph_payload.get("entities"))
    edges = _parse_edges(graph_payload.get("relationships"), nodes)
    clean_alt = alt_text.strip() or _auto_alt_text(nodes, edges)
    width, height = _resolve_dimensions(size_hint)
    if not nodes:
        html = _empty_graph_html(clean_alt)
        png = _empty_png(width, height)
        return GraphVisualArtifacts(html=html, png_bytes=png, notes=notes)

    layout = _layout_nodes(nodes, width - 2 * SVG_PADDING, height - 2 * SVG_PADDING)
    svg_markup = _render_svg(nodes, edges, layout, width, height, clean_alt, notes)
    png_bytes = _render_png(nodes, edges, layout, width, height, clean_alt)
    html_markup = _wrap_html(svg_markup, clean_alt, notes)
    return GraphVisualArtifacts(html=html_markup, png_bytes=png_bytes, notes=notes)


def _parse_nodes(value: JSONValue) -> list[GraphNode]:
    items = coerce_object_list(value)
    parsed: list[GraphNode] = []
    seen: set[str] = set()
    for entry in items:
        identifier = coerce_str(entry.get("id")) or coerce_str(entry.get("uuid"))
        if not identifier:
            continue
        if identifier in seen:
            continue
        label = coerce_str(entry.get("name")) or coerce_str(entry.get("label")) or identifier
        kind = coerce_str(entry.get("type")).upper() if coerce_str(entry.get("type")) else ""
        parsed.append(GraphNode(key=identifier, label=label, kind=kind))
        seen.add(identifier)
    return parsed


def _parse_edges(value: JSONValue, nodes: Sequence[GraphNode]) -> list[GraphEdge]:
    items = coerce_object_list(value)
    node_map: dict[str, GraphNode] = {node.key: node for node in nodes}
    edges: list[GraphEdge] = []
    for entry in items:
        source_key = coerce_str(entry.get("source")) or coerce_str(entry.get("from")) or coerce_str(entry.get("src"))
        target_key = (
            coerce_str(entry.get("target")) or coerce_str(entry.get("to")) or coerce_str(entry.get("dst"))
        )
        if not source_key or not target_key:
            continue
        source_node = node_map.get(source_key)
        target_node = node_map.get(target_key)
        if source_node is None or target_node is None:
            continue
        label = coerce_str(entry.get("summary")) or coerce_str(entry.get("label")) or ""
        edges.append(GraphEdge(source=source_node, target=target_node, label=label))
    return edges


def _auto_alt_text(nodes: Sequence[GraphNode], edges: Sequence[GraphEdge]) -> str:
    entity_count = len(nodes)
    relation_count = len(edges)
    if not nodes:
        return "Empty relationship graph"
    if relation_count == 0:
        return f"Relationship graph with {entity_count} entities and no connections"
    return f"Relationship graph with {entity_count} entities and {relation_count} connections"


def _resolve_dimensions(size_hint: Mapping[str, JSONValue] | None) -> tuple[int, int]:
    width = DEFAULT_WIDTH
    height = DEFAULT_HEIGHT
    if size_hint:
        width = _parse_dimension(size_hint.get("width")) or width
        height = _parse_dimension(size_hint.get("height")) or height
    return max(width, 480), max(height, 360)


def _parse_dimension(value: JSONValue | None) -> int | None:
    raw = coerce_str(value)
    if not raw:
        return None
    cleaned = raw.strip().lower().replace("px", "")
    try:
        parsed = int(float(cleaned))
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def _layout_nodes(nodes: Sequence[GraphNode], width: int, height: int) -> dict[str, tuple[float, float]]:
    count = len(nodes)
    if count == 1:
        return {nodes[0].key: (SVG_PADDING + width / 2.0, SVG_PADDING + height / 2.0)}
    radius = min(width, height) * 0.42
    center_x = SVG_PADDING + width / 2.0
    center_y = SVG_PADDING + height / 2.0
    layout: dict[str, tuple[float, float]] = {}
    for index, node in enumerate(nodes):
        angle = (index / count) * math.tau
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        layout[node.key] = (x, y)
    return layout


def _render_svg(
    nodes: Sequence[GraphNode],
    edges: Sequence[GraphEdge],
    layout: Mapping[str, tuple[float, float]],
    width: int,
    height: int,
    alt_text: str,
    notes: str | None,
) -> str:
    arrow_head = (
        '<defs><marker id="arrowhead" markerWidth="12" markerHeight="8" refX="10" refY="4" orient="auto" '
        'markerUnits="strokeWidth"><path d="M0,0 L0,8 L12,4 z" fill="#4b5563"/></marker></defs>'
    )
    edge_lines: list[str] = []
    for edge in edges:
        source_pos = layout.get(edge.source.key)
        target_pos = layout.get(edge.target.key)
        if source_pos is None or target_pos is None:
            continue
        x1, y1 = source_pos
        x2, y2 = target_pos
        edge_lines.append(
            (
                '<line class="edge-line" x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                'stroke="#4b5563" stroke-width="2" marker-end="url(#arrowhead)" />'
            ).format(x1=x1, y1=y1, x2=x2, y2=y2)
        )
    node_groups: list[str] = []
    for node in nodes:
        position = layout.get(node.key)
        if position is None:
            continue
        x, y = position
        color = NODE_COLORS.get(node.kind, "#6366f1")
        safe_label = escape(node.label)
        node_groups.append(
            (
                '<g class="node" transform="translate({x:.2f},{y:.2f})">'
                '<circle r="{r}" fill="{color}" opacity="0.92" />'
                '<text text-anchor="middle" dominant-baseline="middle" fill="#ffffff">{label}</text>'
                "</g>"
            ).format(x=x, y=y, r=NODE_RADIUS, color=color, label=safe_label)
        )
    notes_markup = ""
    if notes:
        notes_markup = f'<div class="graph-notes">{escape(notes)}</div>'
    svg_content = "\n    ".join([arrow_head, *edge_lines, *node_groups])
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(alt_text)}">'
        f"\n    {svg_content}\n</svg>{notes_markup}"
    )


def _wrap_html(svg_markup: str, alt_text: str, notes: str | None) -> str:
    figcaption = escape(alt_text)
    notes_section = f"<p>{escape(notes)}</p>" if notes else ""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8" />\n'
        "  <title>Relationship graph</title>\n"
        "  <style>\n"
        "    body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 24px; background: #f9fafb; color: #111827; }\n"
        "    .graph-figure { max-width: 1024px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 10px 25px rgba(30, 41, 59, 0.08); padding: 24px; }\n"
        "    svg { width: 100%; height: auto; display: block; }\n"
        "    .graph-notes { margin-top: 16px; font-size: 0.95rem; color: #334155; }\n"
        "    figcaption { margin-top: 16px; font-weight: 600; }\n"
        "    .node text { font-size: 14px; font-weight: 600; pointer-events: none; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <figure class=\"graph-figure\">\n"
        f"    {svg_markup}\n"
        f"    <figcaption>{figcaption}</figcaption>\n"
        f"    {notes_section}\n"
        "  </figure>\n"
        "</body>\n"
        "</html>\n"
    )


def _render_png(
    nodes: Sequence[GraphNode],
    edges: Sequence[GraphEdge],
    layout: Mapping[str, tuple[float, float]],
    width: int,
    height: int,
    alt_text: str,
) -> bytes:
    image = Image.new("RGB", (width, height), color=(249, 250, 251))
    draw = ImageDraw.Draw(image)
    _draw_edges(draw, edges, layout)
    _draw_nodes(draw, nodes, layout)
    _draw_caption(draw, alt_text, width, height)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _draw_edges(
    draw: ImageDraw.ImageDraw,
    edges: Sequence[GraphEdge],
    layout: Mapping[str, tuple[float, float]],
) -> None:
    for edge in edges:
        source_pos = layout.get(edge.source.key)
        target_pos = layout.get(edge.target.key)
        if source_pos is None or target_pos is None:
            continue
        x1, y1 = source_pos
        x2, y2 = target_pos
        draw.line((x1, y1, x2, y2), fill=(75, 85, 99), width=3)
        _draw_arrowhead(draw, x1, y1, x2, y2)


def _draw_arrowhead(draw: ImageDraw.ImageDraw, x1: float, y1: float, x2: float, y2: float) -> None:
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length <= 1.0:
        return
    ux = dx / length
    uy = dy / length
    arrow_length = 14.0
    arrow_width = 6.5
    base_x = x2 - ux * NODE_RADIUS * 0.65
    base_y = y2 - uy * NODE_RADIUS * 0.65
    left_x = base_x - ux * arrow_length + uy * arrow_width
    left_y = base_y - uy * arrow_length - ux * arrow_width
    right_x = base_x - ux * arrow_length - uy * arrow_width
    right_y = base_y - uy * arrow_length + ux * arrow_width
    draw.polygon([(x2, y2), (left_x, left_y), (right_x, right_y)], fill=(75, 85, 99))


def _draw_nodes(
    draw: ImageDraw.ImageDraw,
    nodes: Sequence[GraphNode],
    layout: Mapping[str, tuple[float, float]],
) -> None:
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    for node in nodes:
        position = layout.get(node.key)
        if position is None:
            continue
        x, y = position
        color = PNG_COLORS.get(node.kind, (99, 102, 241))
        bbox = [x - NODE_RADIUS, y - NODE_RADIUS, x + NODE_RADIUS, y + NODE_RADIUS]
        draw.ellipse(bbox, fill=color)
        text = node.label
        text_width, text_height = _measure_text(font, text)
        draw.text(
            (x - text_width / 2, y - text_height / 2 - 1),
            text,
            font=font,
            fill=(255, 255, 255),
        )


def _draw_caption(draw: ImageDraw.ImageDraw, caption: str, width: int, height: int) -> None:
    if not caption:
        return
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    text_width, text_height = _measure_text(font, caption)
    draw.rectangle([(0, height - 48), (width, height)], fill=(255, 255, 255, 230))
    text_y = height - 24 - text_height / 2
    draw.text(
        ((width - text_width) / 2, text_y),
        caption,
        font=font,
        fill=(71, 85, 105),
    )


def _empty_graph_html(alt_text: str) -> str:
    safe_alt = escape(alt_text or "No graph data")
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8" />\n'
        "  <title>Relationship graph</title>\n"
        "  <style>body{font-family:Arial,sans-serif;padding:48px;color:#111827;background:#f8fafc}"
        "  .placeholder{max-width:640px;margin:0 auto;text-align:center;background:#fff;border-radius:12px;"
        "box-shadow:0 10px 25px rgba(30,41,59,0.08);padding:32px;}h1{font-size:1.5rem;margin-bottom:12px;}"
        "p{font-size:1rem;color:#475569;}</style>\n"
        "</head>\n"
        "<body>\n"
        '  <div class="placeholder">\n'
        "    <h1>No relationship graph data</h1>\n"
        f"    <p>{safe_alt}</p>\n"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    )


def _empty_png(width: int, height: int) -> bytes:
    image = Image.new("RGB", (width, height), color=(248, 250, 252))
    draw = ImageDraw.Draw(image)
    message = "No relationship data available"
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    text_width, text_height = _measure_text(font, message)
    draw.text(((width - text_width) / 2, (height - text_height) / 2), message, font=font, fill=(100, 116, 139))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


__all__ = ["GraphVisualArtifacts", "build_graph_visual_artifacts"]
def _measure_text(font: "ImageFont.ImageFont", text: str) -> tuple[float, float]:
    try:
        bbox = font.getbbox(text)
        return float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1])
    except AttributeError:
        width, height = font.getsize(text)  # type: ignore[attr-defined]
        return float(width), float(height)
