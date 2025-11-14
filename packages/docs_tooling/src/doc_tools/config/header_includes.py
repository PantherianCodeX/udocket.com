from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

CONFIG_PATH = Path(__file__).with_suffix(".yaml")
FRONT_MATTER_PLACEHOLDER_RE = re.compile(r"\{<\s*([a-zA-Z0-9_.:-]+)\s*>\}")
BUILTIN_PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")
COMPUTED_FRONT_PLACEHOLDERS = frozenset({"subtitle_block"})
DEFAULT_BUILTIN_HTML = {
    "page_number": '<span class="page-number"></span>',
    "page_count": '<span class="page-count"></span>',
}


@dataclass(frozen=True)
class HeaderIncludesConfig:
    blocks: tuple[str, ...]
    subtitle_lead: str
    front_matter_placeholders: frozenset[str]
    builtin_placeholders: frozenset[str]

    def render(
        self,
        *,
        front_values: Mapping[str, str],
        builtin_values: Mapping[str, str],
    ) -> list[str]:
        def _replace_front(match: re.Match[str]) -> str:
            name = match.group(1)
            return front_values.get(name, match.group(0))

        def _replace_builtin(match: re.Match[str]) -> str:
            name = match.group(1)
            return builtin_values.get(name, match.group(0))

        rendered: list[str] = []
        for block in self.blocks:
            interim = FRONT_MATTER_PLACEHOLDER_RE.sub(_replace_front, block)
            rendered.append(BUILTIN_PLACEHOLDER_RE.sub(_replace_builtin, interim))
        return rendered

    @property
    def required_front_matter_keys(self) -> frozenset[str]:
        return frozenset(
            placeholder
            for placeholder in self.front_matter_placeholders
            if placeholder not in COMPUTED_FRONT_PLACEHOLDERS
        )

    @property
    def legacy_front_matter_tokens(self) -> frozenset[str]:
        return frozenset(
            token
            for token in self.builtin_placeholders
            if token in self.required_front_matter_keys
        )

    @property
    def style(self) -> str:
        return self.blocks[0] if self.blocks else ""


def load_header_includes_config(path: Path = CONFIG_PATH) -> HeaderIncludesConfig:
    raw_obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw_obj, dict):
        msg = "header includes config must be a mapping"
        raise TypeError(msg)
    raw_map = cast("dict[object, object]", raw_obj)
    raw: dict[str, object] = {str(key): value for key, value in raw_map.items()}

    blocks_obj = raw.get("blocks")
    if not isinstance(blocks_obj, list):
        msg = "header includes config 'blocks' must be a list of strings"
        raise TypeError(msg)
    blocks_list: list[str] = []
    for item in cast("list[object]", blocks_obj):
        if not isinstance(item, str):
            msg = "header includes config blocks must be strings"
            raise TypeError(msg)
        blocks_list.append(item.rstrip())

    subtitle_lead_obj = raw.get("subtitle_lead", " <br> ")
    if not isinstance(subtitle_lead_obj, str):
        msg = "header includes config 'subtitle_lead' must be a string"
        raise TypeError(msg)
    subtitle_lead = subtitle_lead_obj

    front_placeholders = frozenset(
        match.group(1)
        for block in blocks_list
        for match in FRONT_MATTER_PLACEHOLDER_RE.finditer(block)
    )
    builtin_placeholders = frozenset(
        match.group(1)
        for block in blocks_list
        for match in BUILTIN_PLACEHOLDER_RE.finditer(block)
    )

    return HeaderIncludesConfig(
        blocks=tuple(blocks_list),
        subtitle_lead=subtitle_lead,
        front_matter_placeholders=front_placeholders,
        builtin_placeholders=builtin_placeholders,
    )


HEADER_INCLUDES_CONFIG = load_header_includes_config()

__all__ = [
    "COMPUTED_FRONT_PLACEHOLDERS",
    "DEFAULT_BUILTIN_HTML",
    "HEADER_INCLUDES_CONFIG",
    "HeaderIncludesConfig",
    "load_header_includes_config",
]
