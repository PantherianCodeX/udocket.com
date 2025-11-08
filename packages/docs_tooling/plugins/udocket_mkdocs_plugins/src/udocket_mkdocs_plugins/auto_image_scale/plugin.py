from __future__ import annotations

import math
import os
import re
from typing import Dict, Optional, Tuple
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup  # Requires: beautifulsoup4
from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from ._image_wrappers import open_image


def _parse_svg_dimensions(svg_path: str) -> Optional[Tuple[float, float]]:
    """
    Return (width_px, height_px) for an SVG if determinable.
    Tries width/height attributes with units or falls back to viewBox.
    """

    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        width = root.get("width")
        height = root.get("height")

        def _to_px(value: Optional[str]) -> Optional[float]:
            if not value:
                return None
            value = value.strip()
            match = re.match(r"^([0-9]*\.?[0-9]+)\s*(px|pt|in|cm|mm|pc)?$", value)
            if not match:
                return None
            magnitude = float(match.group(1))
            unit = (match.group(2) or "px").lower()
            if unit == "px":
                return magnitude
            if unit == "pt":
                # 1pt = 1/72in and we assume 96 DPI => multiplier of 96/72.
                return magnitude * (96.0 / 72.0)
            if unit == "in":
                return magnitude * 96.0
            if unit == "cm":
                return magnitude * (96.0 / 2.54)
            if unit == "mm":
                return magnitude * (96.0 / 25.4)
            if unit == "pc":
                # pica (12pt) => 16px at 96 DPI.
                return magnitude * 16.0
            return None

        width_px = _to_px(width)
        height_px = _to_px(height)
        if width_px and height_px:
            return width_px, height_px

        view_box = root.get("viewBox")
        if view_box:
            parts = [part for part in re.split(r"[ ,]+", view_box.strip()) if part]
            if len(parts) == 4:
                _, _, vb_width, vb_height = parts
                try:
                    return float(vb_width), float(vb_height)
                except ValueError:
                    return None
    except Exception:
        return None
    return None


def _image_intrinsic_size(abs_path: str) -> Optional[Tuple[int, int]]:
    _, ext = os.path.splitext(abs_path)
    ext = ext.lower()
    if ext == ".svg":
        dims = _parse_svg_dimensions(abs_path)
        if dims:
            return int(round(dims[0])), int(round(dims[1]))
        return None
    try:
        with open_image(abs_path) as image:
            image.load()
            return image.width, image.height
    except Exception:
        return None


class AutoImageScalePlugin(BasePlugin):
    """
    MkDocs plugin: for each <img> with a known scale marker (class or data attribute),
    read the actual image dimensions and set width/height attributes to the scaled size.
    """

    config_scheme = (
        ("scale_attr", config_options.Type(str, default="data-scale")),
        ("class_map", config_options.Type(dict, default={"img--half": 0.5})),
        ("default_scale", config_options.Type(float, default=None)),
        ("strict_missing", config_options.Type(bool, default=False)),
    )

    def on_page_content(  # noqa: N802
        self,
        html: str,
        page,
        config,
        files,
    ) -> str:
        docs_dir = config.get("docs_dir")
        page_dir = os.path.dirname(page.file.abs_src_path)

        soup = BeautifulSoup(html, "html.parser")

        def resolve_src(src: str) -> Optional[str]:
            if not src or "://" in src or src.startswith("data:"):
                return None
            abs_candidate = os.path.normpath(os.path.join(docs_dir, src))
            if os.path.isfile(abs_candidate):
                return abs_candidate
            rel_candidate = os.path.normpath(os.path.join(page_dir, src))
            if os.path.isfile(rel_candidate):
                return rel_candidate
            return None

        scale_attr: str = self.config.get("scale_attr") or "data-scale"
        class_map: Dict[str, float] = self.config.get("class_map") or {}
        default_scale: Optional[float] = self.config.get("default_scale")

        changed = False

        warned_missing: set[str] = set()
        warned_size: set[str] = set()

        for image in soup.find_all("img"):
            try:
                scale: Optional[float] = None
                if image.has_attr(scale_attr):
                    try:
                        scale = float(image.get(scale_attr))
                    except Exception:
                        scale = None

                if scale is None and image.has_attr("class"):
                    for cls in image["class"]:
                        if cls in class_map:
                            scale = float(class_map[cls])
                            break

                if scale is None and default_scale:
                    scale = float(default_scale)

                if scale is None:
                    continue

                src = image.get("src")
                abs_path = resolve_src(src)
                if not abs_path:
                    if self.config.get("strict_missing"):
                        raise FileNotFoundError(f"Cannot resolve image path for: {src}")
                    if src and src not in warned_missing:
                        self.logger.warning(
                            "auto-image-scale: could not resolve image path for %s; skipping resize.",
                            src,
                        )
                        warned_missing.add(src)
                    continue

                dims = _image_intrinsic_size(abs_path)
                if not dims:
                    if self.config.get("strict_missing"):
                        raise RuntimeError(f"Cannot determine size for: {src}")
                    key = abs_path if abs_path else src or "<unknown>"
                    if key not in warned_size:
                        self.logger.warning(
                            "auto-image-scale: could not determine intrinsic size for %s (%s); skipping resize.",
                            src or "<unknown>",
                            abs_path,
                        )
                        warned_size.add(key)
                    continue

                width, height = dims
                if width <= 0:
                    continue

                scaled_width = max(1, int(math.floor(width * scale)))
                scaled_height = max(1, int(math.floor(height * scale))) if height and height > 0 else None

                image["width"] = str(scaled_width)
                if scaled_height:
                    image["height"] = str(scaled_height)

                changed = True
            except RuntimeError as exc:
                # Open-image errors (e.g. Pillow missing) must surface loudly.
                self.logger.error(
                    "auto-image-scale: fatal error while processing %s: %s",
                    image.get("src") or "<unknown>",
                    exc,
                )
                raise
            except Exception as exc:  # pragma: no cover - defensive
                if self.config.get("strict_missing"):
                    raise
                self.logger.exception(
                    "auto-image-scale: unexpected error processing %s; skipping.",
                    image.get("src") or "<unknown>",
                )
                continue

        return str(soup) if changed else html
