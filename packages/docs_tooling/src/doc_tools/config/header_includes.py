from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping
import re

import yaml

CONFIG_PATH = Path(__file__).with_suffix(".yaml")
PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


@dataclass(frozen=True)
class HeaderIncludesConfig:
    blocks: tuple[str, ...]
    subtitle_lead: str = " <br> "

    def render(self, context: Mapping[str, str]) -> list[str]:
        return [PLACEHOLDER_RE.sub(lambda match: context.get(match.group(1), match.group(0)), block) for block in self.blocks]


def load_header_includes_config(path: Path = CONFIG_PATH) -> HeaderIncludesConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("header includes config must be a mapping")

    blocks_obj = raw.get("blocks")
    if not isinstance(blocks_obj, Iterable):
        raise ValueError("header includes config 'blocks' must be a list of strings")
    blocks_list: list[str] = []
    for item in blocks_obj:
        if not isinstance(item, str):
            raise ValueError("header includes config blocks must be strings")
        blocks_list.append(item.rstrip())

    subtitle_lead = raw.get("subtitle_lead", " <br> ")
    if not isinstance(subtitle_lead, str):
        raise ValueError("header includes config 'subtitle_lead' must be a string")

    return HeaderIncludesConfig(blocks=tuple(blocks_list), subtitle_lead=subtitle_lead)


HEADER_INCLUDES_CONFIG = load_header_includes_config()

__all__ = ["HeaderIncludesConfig", "HEADER_INCLUDES_CONFIG", "load_header_includes_config"]
