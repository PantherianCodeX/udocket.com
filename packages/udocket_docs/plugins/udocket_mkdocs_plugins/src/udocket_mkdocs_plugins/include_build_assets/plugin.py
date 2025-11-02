"""MkDocs plugin to include pre-rendered build assets in the output site.

Copies everything under ``source_dir`` into ``site_prefix`` within the
MkDocs site directory. Designed for Mermaid renders and similar artifacts
produced outside MkDocs.
"""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Callable

from mkdocs.config import Config
from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin

class IncludeBuildAssetsPlugin(BasePlugin):
    config_scheme = (
        ("source_dir", config_options.Type(str, default="packages/udocket_docs/build")),
        ("site_prefix", config_options.Type(str, default="build")),
    )

    def __init__(self) -> None:
        super().__init__()
        self._source_dir: Path | None = None
        self._site_prefix: str = "build"
        self._config_dir: Path | None = None

    @property
    def source_dir(self) -> Path:
        if self._source_dir is None:
            raise RuntimeError("Plugin not initialised")
        return self._source_dir

    def on_config(self, config: Config) -> Config:
        config_dir = Path(config.config_file_path).resolve().parent
        self._config_dir = config_dir

        raw_source = Path(self.config.get("source_dir", "packages/udocket_docs/build"))
        if not raw_source.is_absolute():
            raw_source = (config_dir / raw_source).resolve()
        self._source_dir = raw_source

        site_prefix = str(self.config.get("site_prefix", "build")).strip("/")
        self._site_prefix = site_prefix
        return config

    def on_post_build(self, config: Config) -> None:  # pragma: no cover - exercised in integration
        if self.source_dir.exists():
            self._copy_assets(Path(config["site_dir"]))

    def on_serve(self, server, config: Config, builder: Callable[[], None]):  # pragma: no cover
        source_dir = self.source_dir
        if source_dir.exists():
            server.watch(str(source_dir), lambda: self._copy_assets(Path(config["site_dir"])))

        def _build_and_copy() -> None:
            builder()
            if source_dir.exists():
                self._copy_assets(Path(config["site_dir"]))

        return _build_and_copy

    def _copy_assets(self, site_dir: Path) -> None:
        source_dir = self.source_dir
        dest_root = site_dir
        if self._site_prefix:
            dest_root = dest_root / self._site_prefix
        if dest_root.exists():
            shutil.rmtree(dest_root)
        for file_path in sorted(source_dir.rglob("*")):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(source_dir)
            target = dest_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(file_path.read_bytes())
