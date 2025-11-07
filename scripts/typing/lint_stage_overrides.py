from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path

from packages.core.agents.analyze_lib import (
    LLM_STAGE_KEYS,
    StageOverride,
    _normalize_stage_map,
)

if __package__ in {None, ""}:
    import sys
    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parents[2]))
    from scripts.typing.common import PROJECT_ROOT
else:
    from .common import PROJECT_ROOT

VALID_STAGES = set(LLM_STAGE_KEYS.values())


def load_stage_map(path: Path) -> Mapping[str, Mapping[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Stage map must be a JSON object")
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def lint_stage_map(stage_map: Mapping[str, Mapping[str, object]]) -> list[str]:
    normalized = _normalize_stage_map(stage_map)
    problems: list[str] = []
    for key, options in normalized.items():
        canonical = key if key in VALID_STAGES else LLM_STAGE_KEYS.get(key)
        if canonical is None:
            problems.append(f"Unknown stage key '{key}'")
            continue
        override = StageOverride.from_mapping(options)
        if override is None:
            continue
        if not override.providers and override.model is None and override.max_tokens is None:
            problems.append(f"Stage {key} override has no effect; consider removing.")
    return problems


def write_normalized(path: Path, stage_map: Mapping[str, Mapping[str, object]]) -> None:
    normalized = _normalize_stage_map(stage_map)
    # only keep canonical keys
    canonical = {key: normalized[key] for key in sorted(normalized.keys()) if key in VALID_STAGES}
    path.write_text(json.dumps(canonical, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint analyze stage override maps.")
    parser.add_argument("stage_map", type=Path, help="Path to stage map JSON file.")
    parser.add_argument(
        "--fix", action="store_true", help="Rewrite file with normalized stage map."
    )
    args = parser.parse_args()

    path = args.stage_map if args.stage_map.is_absolute() else PROJECT_ROOT / args.stage_map
    if not path.exists():
        raise FileNotFoundError(path)

    stage_map = load_stage_map(path)
    problems = lint_stage_map(stage_map)
    if problems:
        for problem in problems:
            print(problem)
    else:
        print("Stage map is clean.")

    if args.fix:
        write_normalized(path, stage_map)
        print(f"Normalized stage map written to {path}")

    return 0 if not problems else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
