from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

if __package__ in {None, ""}:
    import sys

    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[2]))
    from scripts.typing.common import (  # type: ignore[import-not-found]
        PROJECT_ROOT,
        load_manifest,
        save_manifest,
        upsert_helper_record,
    )
else:
    from .common import PROJECT_ROOT, load_manifest, save_manifest, upsert_helper_record

import importlib.metadata as metadata
import sysconfig


TYPINGS_ROOT = PROJECT_ROOT / "typings"
STUB_VENDOR_DIR = TYPINGS_ROOT / "vendor"
METADATA_FILE = STUB_VENDOR_DIR / "VENDORED_STUBS.json"

# Distributions that publish typing stubs we rely on.
DIST_NAMES: tuple[str, ...] = (
    "django-stubs",
    "djangorestframework-stubs",
    "channels-stubs",
    "types-psycopg2",
    "types-requests",
    "types-requests-oauthlib",
    "types-redis",
    "types-PyYAML",
    "types-python-jose",
    "types-pyOpenSSL",
    "types-cffi",
    "types-setuptools",
    "types-oauthlib",
    "types-python-dateutil",
    "types-pyasn1",
)


@dataclass(frozen=True)
class VendoredStub:
    dist_name: str
    version: str
    stub_dirs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "dist": self.dist_name,
            "version": self.version,
            "stubDirs": list(self.stub_dirs),
        }


def _site_packages() -> Path:
    path_str = sysconfig.get_paths()["purelib"]
    path = Path(path_str)
    if not path.exists():  # pragma: no cover - defensive
        raise RuntimeError(f"Site-packages path {path} does not exist")
    return path


def _stub_directories(dist_name: str) -> tuple[str, ...]:
    try:
        dist = metadata.distribution(dist_name)
    except metadata.PackageNotFoundError as exc:  # pragma: no cover - should not happen
        raise RuntimeError(f"Distribution {dist_name} is not installed") from exc

    directories = {
        file.parts[0]
        for file in (dist.files or [])
        if file.parts and file.parts[0].endswith("-stubs")
    }
    if dist_name == "django-stubs" and not directories:
        directories.add("django-stubs")
    return tuple(sorted(directories))


def _copy_stub_dir(source_root: Path, subdir: str, destination_root: Path) -> Path:
    source = source_root / subdir
    if not source.exists():
        raise RuntimeError(f"Stub directory {subdir} not found under {source_root}")
    destination = destination_root / subdir
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    return destination


def _apply_pyright_directives(path: Path) -> None:
    directives = (
        "reportMissingParameterType=false",
        "reportUnknownParameterType=false",
        "reportUnknownVariableType=false",
        "reportUnknownMemberType=false",
        "reportAttributeAccessIssue=false",
        "reportPrivateUsage=false",
        "reportIncompatibleVariableOverride=false",
        "reportUntypedClassDecorator=false",
        "reportMissingTypeArgument=false",
        "reportOverlappingOverload=false",
        "reportInvalidTypeVarUse=false",
        "reportIncompatibleMethodOverride=false",
        "reportUntypedBaseClass=false",
        "reportGeneralTypeIssues=false",
    )
    directive_block = "# pyright: " + ", ".join(directives) + "\n\n"
    for stub_file in path.rglob("*.pyi"):
        text = stub_file.read_text(encoding="utf-8")
        if text.startswith("# pyright: reportMissingParameterType=false"):
            continue
        stub_file.write_text(directive_block + text, encoding="utf-8")


def vendor_stubs(dist_names: Iterable[str]) -> list[VendoredStub]:
    site_packages = _site_packages()
    vendored: list[VendoredStub] = []

    STUB_VENDOR_DIR.mkdir(parents=True, exist_ok=True)

    for dist_name in dist_names:
        stub_dirs = _stub_directories(dist_name)
        if not stub_dirs:
            # Some helper dists (e.g. django-stubs-ext) only contain runtime helpers.
            continue
        version = metadata.version(dist_name)
        for directory in stub_dirs:
            dest_dir = _copy_stub_dir(site_packages, directory, STUB_VENDOR_DIR)
            _apply_pyright_directives(dest_dir)
        vendored.append(VendoredStub(dist_name=dist_name, version=version, stub_dirs=stub_dirs))
    return vendored


def write_metadata(entries: list[VendoredStub]) -> None:
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "entries": [entry.to_dict() for entry in entries],
    }
    METADATA_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Vendor installed typing stubs into the repository")
    parser.add_argument(
        "--dist",
        action="append",
        help="Additional distribution names to vendor",
    )
    args = parser.parse_args()

    dist_names = list(dict.fromkeys(DIST_NAMES + tuple(args.dist or ())))
    vendored = vendor_stubs(dist_names)
    write_metadata(vendored)

    manifest = load_manifest()
    upsert_helper_record(
        manifest,
        name="vendor_stubs",
        version="0.1.0",
        status="ok",
        last_run=datetime.now(timezone.utc),
    )
    save_manifest(manifest)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
