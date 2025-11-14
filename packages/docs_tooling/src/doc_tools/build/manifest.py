from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, UTC
from pathlib import Path
from collections.abc import Iterable

from doc_tools.config import paths


def sha256_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_manifest(files: Iterable[Path]) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    for file in files:
        if not file.exists():
            continue
        entries.append({"name": file.name, "sha256": sha256_digest(file)})
    return {
        "generated_at": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifacts": entries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hash PDF outputs and write a manifest.json")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=paths.PDF_DEV_DIR,
        help="Directory containing generated PDFs (default: out/doc-builds/pdf/dev)",
    )
    args = parser.parse_args(argv)

    output_dir: Path = args.output_dir
    pdfs = [output_dir / "prd.pdf", output_dir / "tdd.pdf"]
    manifest = build_manifest(pdfs)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
