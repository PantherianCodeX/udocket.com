from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from collections.abc import Iterable, Sequence
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

HELPER_NAME = "annotate_fixtures"
HELPER_VERSION = "0.1.0"

PARAM_TYPES = {
    "monkeypatch": "MonkeyPatch",
    "settings": "SettingsFixture",
    "db": "DatabaseFixture",
    "client": "ClientFixture",
}
IMPORT_MODULE = "tests._typing"


def iter_python_files(targets: Iterable[Path]) -> Iterable[Path]:
    for target in targets:
        if target.is_file() and target.suffix == ".py":
            yield target
        elif target.is_dir():
            yield from sorted(target.rglob("test_*.py"))


@dataclass
class ParamEdit:
    line: int
    column: int
    name: str
    annotation: str


def collect_edits(tree: ast.Module) -> dict[str, list[ParamEdit]]:
    edits: dict[str, list[ParamEdit]] = defaultdict(list)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            parameters = list(node.args.args) + list(node.args.kwonlyargs)
            if node.args.vararg:
                parameters.append(node.args.vararg)
            if node.args.kwarg:
                parameters.append(node.args.kwarg)
            for arg in parameters:
                if arg.annotation is not None:
                    continue
                annotation = PARAM_TYPES.get(arg.arg)
                if not annotation or arg.lineno is None or arg.col_offset is None:
                    continue
                edits[node.name].append(
                    ParamEdit(
                        line=arg.lineno - 1,
                        column=arg.col_offset + len(arg.arg),
                        name=arg.arg,
                        annotation=annotation,
                    )
                )
    return edits


def apply_edits(text: str, edits: Sequence[ParamEdit]) -> str:
    if not edits:
        return text
    lines = text.splitlines()
    per_line: dict[int, list[ParamEdit]] = defaultdict(list)
    for edit in edits:
        per_line[edit.line].append(edit)
    for line_index, line_edits in per_line.items():
        line = lines[line_index]
        for edit in sorted(line_edits, key=lambda item: item.column, reverse=True):
            insert_pos = edit.column
            insert_pos = min(insert_pos, len(line))
            line = line[:insert_pos] + f": {edit.annotation}" + line[insert_pos:]
        lines[line_index] = line
    return "\n".join(lines) + ("" if text.endswith("\n") else "\n")


def ensure_import(text: str, needed: Sequence[str]) -> str:
    if not needed:
        return text
    needed_set = set(needed)
    module = ast.parse(text)
    lines = text.splitlines()

    for node in module.body:
        if isinstance(node, ast.ImportFrom) and node.module == IMPORT_MODULE:
            existing = {alias.name for alias in node.names if alias.name}
            if needed_set.issubset(existing):
                return text
            merged = sorted(existing | needed_set)
            start = node.lineno - 1
            end = (node.end_lineno or node.lineno) - 1
            indent = lines[start][: len(lines[start]) - len(lines[start].lstrip())]
            lines[start : end + 1] = [f"{indent}from {IMPORT_MODULE} import {', '.join(merged)}"]
            new_text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
            return new_text

    docstring_end = 0
    if (
        module.body
        and isinstance(module.body[0], ast.Expr)
        and isinstance(module.body[0].value, ast.Constant)
        and isinstance(module.body[0].value.value, str)
    ):
        docstring_end = module.body[0].end_lineno or module.body[0].lineno

    last_import_end = docstring_end
    for node in module.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last_import_end = max(last_import_end, node.end_lineno or node.lineno)

    insertion_index = last_import_end
    lines.insert(insertion_index, f"from {IMPORT_MODULE} import {', '.join(sorted(needed_set))}")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def process_file(path: Path, *, apply: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    edits_by_function = collect_edits(tree)
    edits = [edit for edits in edits_by_function.values() for edit in edits]
    if not edits:
        return False
    if not apply:
        print(
            f"{path}: parameters needing annotations -> {', '.join(sorted({edit.name for edit in edits}))}"
        )
        return True
    updated = apply_edits(text, edits)
    needed_types = sorted({edit.annotation for edit in edits})
    updated = ensure_import(updated, needed_types)
    path.write_text(updated, encoding="utf-8")
    print(f"Annotated fixtures in {path}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Annotate common pytest fixtures with helper types."
    )
    parser.add_argument(
        "targets", nargs="+", type=Path, help="Test files or directories to process."
    )
    parser.add_argument(
        "--apply", action="store_true", help="Apply changes instead of reporting only."
    )
    args = parser.parse_args()

    targets = [target if target.is_absolute() else PROJECT_ROOT / target for target in args.targets]
    files = list(iter_python_files(targets))
    if not files:
        print("No test files found.")
        return 0

    touched = False
    for file_path in files:
        touched = process_file(file_path, apply=args.apply) or touched

    if args.apply:
        manifest = load_manifest()
        upsert_helper_record(
            manifest,
            name=HELPER_NAME,
            version=HELPER_VERSION,
            status="ok" if touched else "noop",
            last_run=datetime.now(UTC),
        )
        save_manifest(manifest)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
