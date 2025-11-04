"""Helper to print filtered Makefile help groups."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
try:
    sys.path.remove(str(THIS_DIR))
except ValueError:
    pass
else:
    sys.path.append(str(THIS_DIR))

REPO_ROOT = THIS_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from packages.udocket_common.text import slugify


def decode_from_make(lines: Sequence[str], name: str) -> str:
    pattern = re.compile(rf"^{re.escape(name)}\s*:=\s*\"(.*)\"$")
    for line in lines:
        match = pattern.match(line)
        if match:
            return bytes(match.group(1), "utf-8").decode("unicode_escape")
    raise SystemExit(f"Missing definition for {name}")


def collect_sections(
    lines: Sequence[str],
) -> tuple[list[tuple[str, str]], dict[str, list[tuple[str, str]]]]:
    sections: list[tuple[str, str]] = []
    commands: dict[str, list[tuple[str, str]]] = {}
    current: str | None = None

    command_pattern = re.compile(r"^([A-Za-z0-9_.-]+):.*##(.*)$")

    for raw in lines:
        if raw.startswith("##@ "):
            label = raw[4:].strip()
            current = slugify(label, separator=".")
            sections.append((current, label))
            commands.setdefault(current, [])
            continue

        if current is None:
            continue

        match = command_pattern.match(raw)
        if not match:
            continue

        name = match.group(1)
        desc = match.group(2).strip()
        commands[current].append((name, desc))

    return sections, commands


def select_sections(sections: Sequence[tuple[str, str]], slug: str) -> list[tuple[str, str]]:
    exact = [entry for entry in sections if entry[0] == slug]
    if exact:
        return exact

    prefix = [
        entry
        for entry in sections
        if entry[0].startswith(f"{slug}.")
        or entry[0].startswith(f"{slug}-")
        or (entry[0].startswith(slug) and entry[0] != slug)
    ]
    if prefix:
        return prefix

    ancestor = [entry for entry in sections if slug.startswith(f"{entry[0]}.")]
    if ancestor:
        return ancestor

    return []


def select_commands(
    sections: Sequence[tuple[str, str]],
    commands: dict[str, list[tuple[str, str]]],
    slug: str,
) -> list[tuple[str, str, list[tuple[str, str]]]]:
    matched: list[tuple[str, str, list[tuple[str, str]]]] = []
    for section_slug, label in sections:
        entries = [
            (name, desc)
            for name, desc in commands.get(section_slug, [])
            if name == slug or name.startswith(f"{slug}.")
        ]
        if entries:
            matched.append((section_slug, label, entries))
    return matched


def render_help(slug: str, makefile_path: Path) -> int:
    lines = makefile_path.read_text().splitlines()
    group_fmt = decode_from_make(lines, "HELP_GROUP_FORMAT")
    cmd_fmt = decode_from_make(lines, "HELP_CMD_FORMAT")

    sections, commands = collect_sections(lines)
    targets = select_sections(sections, slug)

    printed = False
    for section_slug, label in targets:
        entries = commands.get(section_slug, [])
        if not entries:
            continue

        sys.stdout.write(group_fmt % label)
        for name, desc in entries:
            sys.stdout.write(cmd_fmt % (name, desc))
        printed = True

    if not printed:
        matches = select_commands(sections, commands, slug)
        if matches:
            for _, label, entries in matches:
                sys.stdout.write(group_fmt % label)
                for name, desc in entries:
                    sys.stdout.write(cmd_fmt % (name, desc))
            return 0

    if not printed and targets:
        label = targets[0][1]
        sys.stdout.write(group_fmt % label)
        sys.stdout.write("  (no commands with help descriptions)\n")
        return 0

    if printed:
        return 0

    print(f"Unknown help group: {slug}")
    return 1


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render scoped Makefile help output.")
    parser.add_argument("slug", help="Help group to render (e.g., docker, docker.images, dev)")
    parser.add_argument(
        "makefile",
        nargs="?",
        default="Makefile",
        help="Path to the Makefile (defaults to ./Makefile)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    makefile_path = Path(args.makefile).resolve()
    if not makefile_path.exists():
        raise SystemExit(f"Makefile not found: {makefile_path}")

    return render_help(slug=args.slug, makefile_path=makefile_path)


if __name__ == "__main__":
    sys.exit(main())
