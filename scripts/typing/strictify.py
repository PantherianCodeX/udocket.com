from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    import sys
    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[2]))
    from scripts.typing.common import (  # type: ignore[import-not-found]
        append_strict_manifest,
        load_manifest,
        save_manifest,
        upsert_helper_record,
    )
else:
    from .common import append_strict_manifest, load_manifest, save_manifest, upsert_helper_record

HELPER_NAME = "strictify"
HELPER_VERSION = "0.1.0"
STRICT_PRAGMA = "# pyright: strict"


def iter_python_files(targets: Iterable[Path]) -> Iterable[Path]:
    for target in targets:
        if target.is_file() and target.suffix == ".py":
            yield target
        elif target.is_dir():
            for path in sorted(target.rglob("*.py")):
                yield path


def has_strict(text: str) -> bool:
    return STRICT_PRAGMA in text.splitlines()[:5]


def add_strict(text: str) -> str:
    lines = text.splitlines()
    insertion_index = 0

    if lines and lines[0].startswith("#!/"):
        insertion_index = 1

    # skip encoding comments
    while (
        insertion_index < len(lines)
        and lines[insertion_index].startswith("#")
        and "coding" in lines[insertion_index]
    ):
        insertion_index += 1

    # avoid duplicate blank lines
    needs_blank = False
    if insertion_index < len(lines) and lines[insertion_index].strip():
        needs_blank = True

    new_lines = list(lines)
    new_lines.insert(insertion_index, STRICT_PRAGMA)
    if needs_blank:
        new_lines.insert(insertion_index + 1, "")
    return "\n".join(new_lines) + ("" if text.endswith("\n") else "\n")


def strictify_file(path: Path, *, dry_run: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    if has_strict(original):
        return False
    updated = add_strict(original)
    if dry_run:
        sys.stdout.write(f"[strictify] would update {path}\n")
        return True
    path.write_text(updated, encoding="utf-8")
    append_strict_manifest(path)
    sys.stdout.write(f"[strictify] updated {path}\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Add # pyright: strict to Python modules.")
    parser.add_argument("targets", nargs="+", type=Path, help="Files or directories to process.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show files that need updates without editing them."
    )
    parser.add_argument(
        "--check", action="store_true", help="Exit with 1 if any file is missing the strict pragma."
    )
    args = parser.parse_args()

    files = list(iter_python_files(args.targets))
    if not files:
        print("No Python files found for provided targets.")
        return 0

    missing = []
    changed_any = False
    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        if has_strict(text):
            continue
        missing.append(file_path)
        if not args.check:
            modified = strictify_file(file_path, dry_run=args.dry_run)
            changed_any = changed_any or modified

    if args.check:
        if missing:
            for file_path in missing:
                sys.stdout.write(f"{file_path}: missing {STRICT_PRAGMA}\n")
            return 1
        return 0

    if changed_any and not args.dry_run:
        manifest = load_manifest()
        upsert_helper_record(
            manifest,
            name=HELPER_NAME,
            version=HELPER_VERSION,
            status="ok",
            last_run=datetime.now(UTC),
        )
        save_manifest(manifest)

    if not changed_any:
        print("All files already marked strict.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
