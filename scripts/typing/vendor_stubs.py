from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

if __package__ in {None, ""}:
    import sys

    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[2]))
    from scripts.typing.common import (
        PROJECT_ROOT,
        load_manifest,
        save_manifest,
        upsert_helper_record,
    )
else:
    from .common import PROJECT_ROOT, load_manifest, save_manifest, upsert_helper_record

import importlib.metadata as metadata
import sys
import sysconfig
import tempfile


TYPINGS_ROOT = PROJECT_ROOT / "typings"
STUB_VENDOR_DIR = TYPINGS_ROOT / "vendor"
METADATA_FILE = STUB_VENDOR_DIR / "VENDORED_STUBS.json"

# Distributions that publish typing stubs we rely on.
DIST_NAMES: tuple[str, ...] = (
    "django-stubs",
    "djangorestframework-stubs",
    "channels-stubs",
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
    "mozilla-django-oidc",
)

STUBGEN_MODULES: dict[str, tuple[str, ...]] = {
    "mozilla-django-oidc": ("mozilla_django_oidc",),
}


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


def _discover_installed_stub_dists() -> set[str]:
    discovered: set[str] = set()
    for dist in metadata.distributions():
        if any(
            path.parts and path.parts[0].endswith("-stubs")
            for path in (dist.files or [])
        ):
            discovered.add(dist.metadata["Name"])
    return discovered


def _top_level_modules(dist: metadata.Distribution) -> tuple[str, ...]:
    top_level_raw = dist.read_text("top_level.txt")
    if top_level_raw:
        modules = [
            line.strip()
            for line in top_level_raw.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        if modules:
            return tuple(modules)

    candidates: set[str] = set()
    for file in dist.files or []:
        if not file.parts:
            continue
        head = file.parts[0]
        if head.endswith(".dist-info") or head.endswith(".data"):
            continue
        if head in {"__pycache__", "tests", "docs"}:
            continue
        candidates.add(head.replace("/", "."))
    ordered = sorted(candidates)
    return tuple(ordered)


def _run_stubgen(modules: tuple[str, ...], destination_root: Path, search_path: Path) -> tuple[str, ...]:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        stubgen_exe = Path(sys.executable).with_name("stubgen")
        search_paths = os.pathsep.join([str(search_path), str(PROJECT_ROOT)])
        args = [
            str(stubgen_exe),
            "--search-path",
            search_paths,
            "--ignore-errors",
            "--include-docstrings",
        ]
        for module in modules:
            args.extend(["-p", module])
        args.extend(["-o", str(tmp_path)])
        subprocess.run(args, check=True)

        generated_dirs: list[str] = []
        for module in modules:
            module_path = Path(module.replace(".", "/"))
            source_dir = tmp_path / module_path
            target_stub_dir = destination_root / f"{module.replace('.', '_')}-stubs"
            if target_stub_dir.exists():
                shutil.rmtree(target_stub_dir)
            if source_dir.is_dir():
                target_module_dir = target_stub_dir / module_path
                target_module_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source_dir, target_module_dir)
            else:
                stub_file = source_dir.with_suffix(".pyi")
                if not stub_file.exists():
                    continue
                target_file = target_stub_dir / module_path.with_suffix(".pyi")
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(stub_file, target_file)
            generated_dirs.append(target_stub_dir.name)
        return tuple(generated_dirs)


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
    files: Iterable[Path]
    if path.is_file():
        files = (path,)
    else:
        files = path.rglob("*.pyi")
    for stub_file in files:
        if stub_file.suffix != ".pyi":
            continue
        text = stub_file.read_text(encoding="utf-8")
        if text.startswith("# pyright: reportMissingParameterType=false"):
            continue
        stub_file.write_text(directive_block + text, encoding="utf-8")


def vendor_stubs(
    dist_names: Iterable[str],
    *,
    stubgen_missing: bool = True,
) -> list[VendoredStub]:
    site_packages = _site_packages()
    vendored: list[VendoredStub] = []

    STUB_VENDOR_DIR.mkdir(parents=True, exist_ok=True)

    for dist_name in dist_names:
        try:
            dist = metadata.distribution(dist_name)
        except metadata.PackageNotFoundError:
            print(f"warning: distribution '{dist_name}' is not installed; skipping.")
            continue

        stub_dirs = _stub_directories(dist_name)
        generated_dirs: tuple[str, ...] = tuple()

        if stub_dirs:
            print(f"{dist_name}: found packaged stubs -> {', '.join(stub_dirs)}")
            for directory in stub_dirs:
                dest_dir = _copy_stub_dir(site_packages, directory, STUB_VENDOR_DIR)
                _apply_pyright_directives(dest_dir)
        elif stubgen_missing:
            module_targets: tuple[str, ...]
            if dist_name in STUBGEN_MODULES:
                module_targets = STUBGEN_MODULES[dist_name]
            else:
                module_targets = _top_level_modules(dist)
            if not module_targets:
                print(f"{dist_name}: no stub package and unable to infer modules; skipping stubgen")
                continue
            print(
                f"{dist_name}: no packaged stubs; generating via stubgen for modules: "
                + ", ".join(module_targets)
            )
            generated_dirs = _run_stubgen(module_targets, STUB_VENDOR_DIR, site_packages)
            stub_dirs = generated_dirs
            for directory in generated_dirs:
                dest_path = STUB_VENDOR_DIR / directory
                if dest_path.exists():
                    _apply_pyright_directives(dest_path)
        else:
            print(f"{dist_name}: missing stubs and stubgen disabled; reporting only")
            stub_dirs = ()

        if not stub_dirs:
            continue

        version = dist.version
        vendored.append(
            VendoredStub(dist_name=dist_name, version=version, stub_dirs=stub_dirs)
        )
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
    parser.add_argument(
        "--scan-installed",
        action="store_true",
        help="Include any installed distributions that already ship -stubs packages",
    )
    parser.add_argument(
        "--no-stubgen",
        action="store_true",
        help="Skip stubgen fallback for distributions without packaged stubs",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate vendored stubs even if the destination directory is already populated",
    )
    args = parser.parse_args()

    requested: list[str] = list(DIST_NAMES)
    if args.dist:
        requested.extend(args.dist)
    if args.scan_installed:
        requested.extend(sorted(_discover_installed_stub_dists()))

    dist_names = list(dict.fromkeys(requested))

    if STUB_VENDOR_DIR.exists() and any(STUB_VENDOR_DIR.iterdir()) and not args.force:
        print(
            "Vendored stubs directory already populated; skipping generation. Use --force to regenerate."
        )
        vendored: list[VendoredStub] = []
    else:
        vendored = vendor_stubs(dist_names, stubgen_missing=not args.no_stubgen)
        if vendored:
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
