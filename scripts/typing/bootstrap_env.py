from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

if __package__ in {None, ""}:
    import sys

    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[2]))
    from scripts.typing.common import (  # type: ignore[import-not-found]
        CACHE_ROOT,
        PROJECT_ROOT,
        ensure_cache_dir,
        load_manifest,
        record_pyright_stats,
        resolve_python,
        run_command,
        save_manifest,
        upsert_helper_record,
    )
else:
    from .common import (
        CACHE_ROOT,
        PROJECT_ROOT,
        ensure_cache_dir,
        load_manifest,
        record_pyright_stats,
        resolve_python,
        run_command,
        save_manifest,
        upsert_helper_record,
    )

BOOTSTRAP_CACHE = ensure_cache_dir() / "bootstrap.json"
DEFAULT_STUBS_FILE = Path("docs/typing/bootstrap_stubs.txt")
DEFAULT_STUB_PACKAGES = [
    "django-stubs",
    "djangorestframework-stubs",
    "pytest-stubs",
    "types-requests",
    "types-python-dateutil",
]
HELPER_NAME = "bootstrap_env"
HELPER_VERSION = "0.1.0"


def _load_package_list(extra_file: Path | None) -> List[str]:
    packages: list[str] = []
    seen: set[str] = set()
    for item in DEFAULT_STUB_PACKAGES:
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            packages.append(normalized)

    for path in (extra_file, DEFAULT_STUBS_FILE):
        if not path:
            continue
        candidate = PROJECT_ROOT / path
        if not candidate.exists():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped not in seen:
                seen.add(stripped)
                packages.append(stripped)
    return packages


def _load_cache() -> dict[str, object]:
    if BOOTSTRAP_CACHE.exists():
        return json.loads(BOOTSTRAP_CACHE.read_text(encoding="utf-8"))
    return {"packages": [], "hash": ""}


def _write_cache(packages: Iterable[str]) -> None:
    package_list = list(packages)
    payload = {
        "packages": package_list,
        "hash": hashlib.sha256("\0".join(package_list).encode("utf-8")).hexdigest(),
        "recordedAt": datetime.now(timezone.utc).isoformat(),
    }
    BOOTSTRAP_CACHE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _needs_install(packages: Iterable[str]) -> bool:
    cache = _load_cache()
    existing_hash = cache.get("hash")
    new_hash = hashlib.sha256("\0".join(packages).encode("utf-8")).hexdigest()
    return existing_hash != new_hash


def _install_packages(python_exe: Path, packages: Iterable[str]) -> None:
    for package in packages:
        run_command([str(python_exe), "-m", "pip", "install", package], check=True)


def _run_pyright_stats() -> str:
    try:
        result = run_command(["pyright", "--stats"], check=False)
        return result.stdout or result.stderr
    except FileNotFoundError:
        return "pyright executable not found"


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap typing environment stubs.")
    parser.add_argument("--venv", default=".venv", help="Path to virtual environment containing Python executable.")
    parser.add_argument("--packages-file", type=Path, help="Optional newline-delimited list of additional packages.")
    parser.add_argument("--check-only", action="store_true", help="Do not install packages; exit with 0 if up to date, 1 otherwise.")
    parser.add_argument("--no-stats", action="store_true", help="Skip running pyright --stats after installation.")
    args = parser.parse_args()

    venv_path = (PROJECT_ROOT / args.venv).resolve()
    package_list = _load_package_list(args.packages_file if args.packages_file else None)

    if not package_list:
        print("No stub packages configured; nothing to do.")
        return 0

    needs_install = _needs_install(package_list)
    if args.check_only:
        return 0 if not needs_install else 1

    python_exe = resolve_python(venv_path)
    if needs_install:
        print(f"Installing {len(package_list)} stub packages into {venv_path}...")
        _install_packages(python_exe, package_list)
        _write_cache(package_list)
    else:
        print("Stub packages already up to date; skipping installation.")

    manifest = load_manifest()
    upsert_helper_record(
        manifest,
        name=HELPER_NAME,
        version=HELPER_VERSION,
        status="ok",
        last_run=datetime.now(timezone.utc),
    )

    if not args.no_stats:
        stats_output = _run_pyright_stats()
        record_pyright_stats(manifest, command="pyright --stats", stdout=stats_output)

    manifest["recordedAt"] = datetime.now(timezone.utc).isoformat()
    save_manifest(manifest)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
