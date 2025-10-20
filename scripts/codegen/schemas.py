#!/usr/bin/env python3
"""
Lightweight schema round-trip helper.

Goals (no wiring into build yet):
- Validate JSON Schemas under spec/schemas/* using jsonschema.
- Emit a consolidated index of $id values to catch duplicates.
- Placeholder hooks for codegen (Pydantic/TS) without executing external tools.

Usage:
  python scripts/codegen/schemas.py validate

Exit non-zero on validation failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterator

try:
    import jsonschema
except Exception as exc:  # pragma: no cover
    print("jsonschema is required for local validation (pip install jsonschema)", file=sys.stderr)
    raise


SCHEMAS_ROOT = Path(__file__).resolve().parents[2] / "spec" / "schemas"


def iter_schema_files() -> Iterator[Path]:
    for p in SCHEMAS_ROOT.rglob("*.schema.json"):
        yield p


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_all() -> int:
    ids: set[str] = set()
    failed = 0
    for path in sorted(iter_schema_files()):
        try:
            data = load_json(path)
            # Basic mechanical checks
            if "$schema" not in data:
                raise ValueError("$schema missing")
            if "$id" not in data:
                raise ValueError("$id missing")
            _id = str(data["$id"]).strip()
            if _id in ids:
                raise ValueError(f"duplicate $id: {_id}")
            ids.add(_id)
            # Validate against draft 2020-12 metaschema
            jsonschema.validate(
                instance=data,
                schema=jsonschema.validators.DRAFT202012_META_SCHEMA,  # type: ignore[attr-defined]
            )
            print(f"OK  {path.relative_to(SCHEMAS_ROOT)}")
        except Exception as e:  # pragma: no cover
            failed += 1
            print(f"FAIL {path}: {e}", file=sys.stderr)
    if failed:
        print(f"\n{failed} schema(s) failed validation", file=sys.stderr)
        return 2
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] == "help":
        print("usage: schemas.py validate", file=sys.stderr)
        return 1
    if argv[1] == "validate":
        return validate_all()
    print(f"unknown command: {argv[1]}", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))

