from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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

HELPER_NAME = "manager_codemod"
HELPER_VERSION = "0.1.0"

TARGET_METHODS = {"typed_objects", "scoped"}


@dataclass
class ClassUpdate:
    path: Path
    class_name: str
    missing_methods: list[str]


def iter_python_files(targets: Iterable[Path]) -> Iterable[Path]:
    for target in targets:
        if target.is_file() and target.suffix == ".py":
            yield target
        elif target.is_dir():
            yield from sorted(target.rglob("*.py"))


def is_model_class(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in {"Model", "TypedModel"}:
            return True
        if isinstance(base, ast.Attribute) and base.attr == "Model":
            return True
    return False


def analyse_file(path: Path) -> list[ClassUpdate]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    updates: list[ClassUpdate] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not is_model_class(node):
            continue
        existing_methods = {n.name for n in node.body if isinstance(n, ast.FunctionDef)}
        missing = sorted(TARGET_METHODS - existing_methods)
        if missing:
            updates.append(ClassUpdate(path=path, class_name=node.name, missing_methods=missing))
    return updates


def ensure_cast_import(lines: list[str]) -> None:
    for index, line in enumerate(lines):
        if line.startswith("from typing import"):
            if "cast" in line:
                return
            lines[index] = line.rstrip() + ", cast" + ("" if line.endswith("\n") else "")
            return
    insertion_index = 0
    if lines and lines[0].startswith("#!/"):
        insertion_index = 1
    lines.insert(insertion_index, "from typing import cast\n")


def insert_methods(lines: list[str], class_update: ClassUpdate, node: ast.ClassDef) -> None:
    class_line = node.lineno - 1
    class_indent = len(lines[class_line]) - len(lines[class_line].lstrip())
    body_indent = class_indent + 4
    indent = " " * body_indent

    snippet_lines: list[str] = []
    for method in class_update.missing_methods:
        snippet_lines.append("")
        snippet_lines.extend(
            [
                f"{indent}@classmethod\n",
                f"{indent}def {method}(cls):\n",
                f"{indent}    from django.db import models\n",
                f'{indent}    return cast("models.Manager[{class_update.class_name}]", cls.objects)\n',
            ]
        )
    snippet = snippet_lines

    insert_index = node.end_lineno - 1 if node.end_lineno else len(lines) - 1
    while insert_index > class_line:
        line = lines[insert_index]
        if line.strip() == "":
            insert_index -= 1
            continue
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= class_indent:
            break
        insert_index -= 1
    insert_index += 1
    lines[insert_index:insert_index] = snippet


def apply_updates(path: Path, class_updates: list[ClassUpdate]) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    class_nodes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    for update in sorted(
        class_updates,
        key=lambda item: class_nodes[item.class_name].lineno,  # type: ignore[index]
        reverse=True,
    ):
        node = class_nodes.get(update.class_name)
        if node is None:
            continue
        insert_methods(lines, update, node)
    ensure_cast_import(lines)
    path.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Codemod for typed Django managers.")
    parser.add_argument("targets", nargs="+", type=Path, help="Files or directories to process.")
    parser.add_argument("--apply", action="store_true", help="Apply changes instead of reporting.")
    args = parser.parse_args()

    targets = [target if target.is_absolute() else PROJECT_ROOT / target for target in args.targets]
    files = list(iter_python_files(targets))
    pending: list[ClassUpdate] = []
    for file_path in files:
        pending.extend(analyse_file(file_path))

    if not pending:
        print("No models require typed manager helpers.")
        return 0

    for update in pending:
        missing = ", ".join(update.missing_methods)
        print(f"{update.path}: class {update.class_name} missing {missing}")

    if args.apply:
        grouped: dict[Path, list[ClassUpdate]] = {}
        for update in pending:
            grouped.setdefault(update.path, []).append(update)
        for path, updates in grouped.items():
            apply_updates(path, updates)
            print(f"Updated {path}")
        manifest = load_manifest()
        upsert_helper_record(
            manifest,
            name=HELPER_NAME,
            version=HELPER_VERSION,
            status="ok",
            last_run=datetime.now(UTC),
        )
        save_manifest(manifest)
    else:
        print("Run with --apply to modify files.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
