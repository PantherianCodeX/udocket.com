from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

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

HELPER_NAME = "check_stubs"
HELPER_VERSION = "0.1.0"


def read_pyright_stub_paths(config_path: Path) -> List[Path]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    stub_path = data.get("stubPath")
    paths: list[Path] = []
    if isinstance(stub_path, str):
        paths.append(PROJECT_ROOT / stub_path)
    elif isinstance(stub_path, list):
        for item in stub_path:
            if isinstance(item, str):
                paths.append(PROJECT_ROOT / item)
    return paths


def ensure_directories(paths: Iterable[Path], *, fix: bool) -> list[str]:
    problems: list[str] = []
    for path in paths:
        if path.exists():
            continue
        message = f"Stub directory missing: {path}"
        problems.append(message)
        if fix:
            path.mkdir(parents=True, exist_ok=True)
            print(f"Created stub directory {path}")
    return problems


def module_to_stub_path(stub_root: Path, module: str) -> Path:
    parts = module.split(".")
    name = parts[-1]
    if name == "__init__":
        parts = parts[:-1]
        target = stub_root.joinpath(*parts, "__init__.pyi")
    else:
        target = stub_root.joinpath(*parts[:-1], f"{name}.pyi")
    return target


def ensure_module_stubs(stub_root: Path, modules: Iterable[str], *, fix: bool) -> list[str]:
    missing: list[str] = []
    for module in modules:
        target = module_to_stub_path(stub_root, module)
        if target.exists():
            continue
        if not fix:
            missing.append(f"Missing stub for {module} -> {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        header = "# Auto-generated skeleton by scripts/typing/check_stubs.py\n"
        target.write_text(header + "...\n", encoding="utf-8")
        print(f"Created stub skeleton {target}")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Pyright stub overlays.")
    parser.add_argument("--config", default="pyrightconfig.json", type=Path, help="Path to pyright configuration file.")
    parser.add_argument("--module", dest="modules", action="append", help="Runtime module to ensure has a stub skeleton.")
    parser.add_argument("--fix", action="store_true", help="Create missing directories or stubs automatically.")
    args = parser.parse_args()

    config_path = PROJECT_ROOT / args.config
    if not config_path.exists():
        raise FileNotFoundError(config_path)

    stub_paths = read_pyright_stub_paths(config_path)
    if not stub_paths:
        print("No stubPath entries found in configuration.")
        return 0

    problems = ensure_directories(stub_paths, fix=args.fix)
    modules = args.modules or []
    for stub_root in stub_paths:
        problems.extend(ensure_module_stubs(stub_root, modules, fix=args.fix))

    if problems:
        for problem in problems:
            print(problem)
        if not args.fix:
            print("Run with --fix to create missing resources.")
            return 1

    if args.fix:
        from datetime import datetime, timezone

        manifest = load_manifest()
        upsert_helper_record(
            manifest,
            name=HELPER_NAME,
            version=HELPER_VERSION,
            status="ok" if not problems else "error",
            last_run=datetime.now(timezone.utc),
        )
        save_manifest(manifest)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
