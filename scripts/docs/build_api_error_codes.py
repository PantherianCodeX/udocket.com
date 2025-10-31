#!/usr/bin/env python3
"""Synchronise API error code tables and appendix from YAML sources."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable
from typing import Any, Sequence, cast

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
CROSS_LINK_PREFIX = "> _Full listing:_ [API error codes index]"
NOTE_PREFIX = "> Tables generated from `"
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts.docs.doc_utils import (  # noqa: E402
    begin_auto_generated_marker,
    derive_doc_label,
    end_auto_generated_marker,
    parse_front_matter,
    read_markdown_lines,
    replace_auto_generated_section,
    slugify,
    write_or_check,
    yaml,
)

SRC_DIR = ROOT / "docs" / "src"
SERVICES_DIR = SRC_DIR / "services"
APPS_DIR = SRC_DIR / "apps"
APPENDIX_FILE = SRC_DIR / "overview" / "tdd" / "appendices" / "api_error_codes.md"
APPENDIX_DIR = APPENDIX_FILE.parent
APPENDIX_LABEL = "api-error-index"
APPENDIX_BEGIN = begin_auto_generated_marker(APPENDIX_LABEL)
APPENDIX_END = end_auto_generated_marker(APPENDIX_LABEL)

SUMMARY_LABEL = "api-error-codes:summary (error_codes.yaml)"
CATALOG_LABEL = "api-error-codes:catalog (error_codes.yaml)"
SUMMARY_BEGIN = begin_auto_generated_marker(SUMMARY_LABEL)
SUMMARY_END = end_auto_generated_marker(SUMMARY_LABEL)
CATALOG_BEGIN = begin_auto_generated_marker(CATALOG_LABEL)
CATALOG_END = end_auto_generated_marker(CATALOG_LABEL)


@dataclass
class ErrorCodeEntry:
    code: str
    scenario: str
    client_action: str
    http_status: str
    audit_required: bool
    metrics: list[str]
    description: str


@dataclass
class Component:
    doc_path: Path
    yaml_path: Path
    display_name: str
    section_anchor: str
    index_anchor: str
    entries: list[ErrorCodeEntry]


def _fail(message: str) -> None:
    raise RuntimeError(message)


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:  # pragma: no cover - pyYAML bundled with docs tooling
        _fail("PyYAML is required to parse API error definitions")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Failed to parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        _fail(f"{path}: expected mapping with 'error_codes' list")
    return data


def _ensure_text(path: Path, code: str, value: Any, field: str) -> str:
    if value is None:
        _fail(f"{path}: error code '{code}' missing required field '{field}'")
    text = str(value).strip()
    if not text:
        _fail(f"{path}: error code '{code}' field '{field}' must not be empty")
    if text.startswith("<") and text.endswith(">"):
        _fail(f"{path}: error code '{code}' field '{field}' still uses template placeholder '{text}'")
    return text


def _coerce_http_status(path: Path, code: str, value: Any) -> str:
    text = _ensure_text(path, code, value, "http_status")
    try:
        number = int(text)
    except ValueError as exc:
        raise RuntimeError(f"{path}: error code '{code}' field 'http_status' must be an integer") from exc
    if not (100 <= number <= 599):
        _fail(f"{path}: error code '{code}' field 'http_status' must be between 100 and 599")
    return str(number)


def _coerce_bool(path: Path, code: str, value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"true", "yes", "y", "1"}:
            return True
        if token in {"false", "no", "n", "0"}:
            return False
    _fail(f"{path}: error code '{code}' field '{field}' must be boolean")
    return False  # pragma: no cover


def _normalize_metrics(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, Iterable):
        items: list[str] = []
        for element in value:
            text = str(element).strip()
            if text.lower() == "[optional]" or not text:
                continue
            items.append(text)
        return items
    _fail(f"related_metrics must be string or list, received {type(value)!r}")
    return []  # pragma: no cover


def _load_entries(yaml_path: Path) -> list[ErrorCodeEntry]:
    data = _load_yaml(yaml_path)
    codes_obj = data.get("error_codes")
    if not isinstance(codes_obj, list):
        _fail(f"{yaml_path}: 'error_codes' must be a non-empty list")
    if not codes_obj:
        _fail(f"{yaml_path}: 'error_codes' must be a non-empty list")
    codes_list = cast(list[Any], codes_obj)
    codes: list[Any] = list(codes_list)
    entries: list[ErrorCodeEntry] = []
    seen: set[str] = set()
    for item in codes:
        if not isinstance(item, dict):
            _fail(f"{yaml_path}: each entry must be a mapping")
        raw_code = _ensure_text(yaml_path, "<unknown>", item.get("code"), "code")
        code = raw_code
        if code in seen:
            _fail(f"{yaml_path}: duplicate error code '{code}'")
        http_status = _coerce_http_status(yaml_path, code, item.get("http_status"))
        audit_required = _coerce_bool(yaml_path, code, item.get("audit_required"), "audit_required")
        description = _ensure_text(yaml_path, code, item.get("description"), "description")
        client_action = _ensure_text(yaml_path, code, item.get("client_action"), "client_action")
        scenario = str(item.get("scenario") or description).strip()
        metrics = _normalize_metrics(item.get("related_metrics"))
        entries.append(
            ErrorCodeEntry(
                code=code,
                scenario=scenario,
                client_action=client_action,
                http_status=http_status,
                audit_required=audit_required,
                metrics=metrics,
                description=description,
            )
        )
        seen.add(code)
    return sorted(entries, key=lambda entry: entry.code)


def _rel_yaml_path(doc_path: Path) -> str:
    return f"./{doc_path.stem}/error_codes.yaml"


def _summary_markers(_: str) -> tuple[str, str]:
    return SUMMARY_BEGIN, SUMMARY_END


def _catalog_markers(_: str) -> tuple[str, str]:
    return CATALOG_BEGIN, CATALOG_END


def _find_section_anchor(doc_path: Path) -> str:
    pattern = re.compile(r"^###\s+3\.3\s+.*", re.IGNORECASE)
    for line in doc_path.read_text(encoding="utf-8").splitlines():
        if pattern.match(line.strip()):
            if "{#" in line:
                anchor = line.split("{#", 1)[1].split("}", 1)[0].strip()
                return anchor
            title = re.sub(r"{#.*}" , "", line).strip()
            base = re.sub(r"^#+\s+", "", title)
            return slugify(base)
    _fail(f"{doc_path}: missing '### 3.3' heading")
    return ""  # pragma: no cover


def _derive_display_name(doc_path: Path) -> str:
    lines = read_markdown_lines(doc_path)
    front = parse_front_matter(lines)
    title = front.get("title")
    label = derive_doc_label(str(title or ""), fallback=doc_path.stem.replace("-", " ").title())
    return label


def _replace_block(content: str, begin: str, end: str, body_lines: list[str]) -> str:
    if begin not in content or end not in content:
        raise RuntimeError(f"Missing marker '{begin}' or '{end}'")
    before, remainder = content.split(begin, 1)
    _, after = remainder.split(end, 1)
    body = "\n".join(body_lines)
    if body:
        body = body.rstrip() + "\n"
    return f"{before}{begin}\n{body}{end}{after}"


def _format_table_cell(text: str) -> str:
    value = str(text).strip()
    return value.replace("|", r"\|").replace("\n", " ")


def _render_summary_table(entries: list[ErrorCodeEntry]) -> list[str]:
    if not entries:
        return ["_No API error codes documented._"]
    lines = [
        "| Code | Scenario | Client guidance |",
        "| --- | --- | --- |",
    ]
    for entry in entries:
        scenario = _format_table_cell(entry.scenario)
        if entry.description and entry.description.strip() and entry.description.strip() != entry.scenario.strip():
            description = _format_table_cell(entry.description)
            scenario = f"{scenario}<br>_{description}_"
        guidance = _format_table_cell(entry.client_action)
        lines.append(f"| `{entry.code}` | {scenario or '—'} | {guidance or '—'} |")
    return lines


def _render_catalog_table(entries: list[ErrorCodeEntry]) -> list[str]:
    if not entries:
        return ["_No API error codes documented._"]
    lines = [
        "| Code | HTTP Status | Audit Required | Metrics |",
        "| --- | --- | --- | --- |",
    ]
    for entry in entries:
        metrics = "<br>".join(metric.replace("|", r"\|") for metric in entry.metrics) if entry.metrics else "—"
        lines.append(
            "| `{code}` | {status} | {audit} | {metrics} |".format(
                code=entry.code,
                status=entry.http_status,
                audit="Yes" if entry.audit_required else "No",
                metrics=metrics or "—",
            )
        )
    return lines


def _ensure_cross_link(lines: list[str], component: Component) -> None:
    appendix_rel = Path(os.path.relpath(APPENDIX_FILE, component.doc_path.parent)).as_posix()
    link_line = f"{CROSS_LINK_PREFIX}({appendix_rel}#{component.index_anchor})"
    summary_idx = None
    for idx, line in enumerate(lines):
        if line.strip() == SUMMARY_BEGIN:
            summary_idx = idx
            break
    if summary_idx is None:
        return
    # Find existing cross-link (line before summary marker).
    insert_idx = summary_idx
    look_idx = summary_idx - 1
    while look_idx >= 0 and not lines[look_idx].strip():
        look_idx -= 1
    if look_idx >= 0 and lines[look_idx].strip().startswith(CROSS_LINK_PREFIX):
        lines[look_idx] = link_line
        if look_idx + 1 >= len(lines) or lines[look_idx + 1].strip():
            lines.insert(look_idx + 1, "")
        return
    # Insert new link with a trailing blank line before the summary marker.
    if insert_idx > 0 and lines[insert_idx - 1].strip():
        lines.insert(insert_idx, "")
        insert_idx += 1
    lines.insert(insert_idx, link_line)
    lines.insert(insert_idx + 1, "")


def _ensure_heading_anchor(lines: list[str], component: Component) -> None:
    target_anchor = component.section_anchor
    if not target_anchor:
        return
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.lower().startswith("### 3.3"):
            continue
        if "{#" in stripped:
            return
        prefix = line.rstrip()
        suffix = f" {{#{target_anchor}}}"
        lines[idx] = prefix + suffix
        return


def _update_document(component: Component, *, check: bool) -> bool:
    original = component.doc_path.read_text(encoding="utf-8")
    summary_body = _render_summary_table(component.entries)
    catalog_body = _render_catalog_table(component.entries)
    summary_begin, summary_end = _summary_markers(_rel_yaml_path(component.doc_path))
    catalog_begin, catalog_end = _catalog_markers(_rel_yaml_path(component.doc_path))
    updated = _replace_block(original, summary_begin, summary_end, summary_body)
    updated = _replace_block(updated, catalog_begin, catalog_end, catalog_body)
    updated_lines = updated.splitlines()
    _remove_legacy_notes(updated_lines)
    _ensure_heading_anchor(updated_lines, component)
    _ensure_cross_link(updated_lines, component)
    final = "\n".join(updated_lines).rstrip() + "\n"
    if check:
        return write_or_check(component.doc_path, final, check=True)
    write_or_check(component.doc_path, final, check=False)
    return True


def _rel_from_appendix(target: Path) -> str:
    return Path(os.path.relpath(target, APPENDIX_DIR)).as_posix()


def _render_appendix(components: list[Component]) -> str:
    lines: list[str] = [
        "<!-- AUTO-GENERATED: Run `python scripts/docs/build_api_error_codes.py` to refresh. -->",
        "",
    ]
    for component in components:
        doc_rel = _rel_from_appendix(component.doc_path)
        target = f"{doc_rel}#{component.section_anchor}" if component.section_anchor else doc_rel
        heading = f"### [{component.display_name}]({target}) {{#{component.index_anchor}}}"
        lines.append(heading)
        lines.append("")
        lines.extend(_render_summary_table(component.entries))
        lines.append("")
        lines.extend(_render_catalog_table(component.entries))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _remove_legacy_notes(lines: list[str]) -> None:
    index = 0
    while index < len(lines):
        if lines[index].strip().startswith(NOTE_PREFIX):
            del lines[index]
            if index < len(lines) and not lines[index].strip():
                del lines[index]
            continue
        index += 1


def _collect_components() -> list[Component]:
    docs = sorted(SERVICES_DIR.glob("*.md")) + sorted(APPS_DIR.glob("*.md"))
    components: list[Component] = []
    for doc in docs:
        if doc.name.startswith("_template"):
            continue
        yaml_path = (doc.parent / doc.stem / "error_codes.yaml")
        doc_text = doc.read_text(encoding="utf-8")
        if not yaml_path.exists():
            if "### 3.3" in doc_text:
                _fail(f"{doc}: expected {yaml_path.name} alongside the document")
            continue
        entries = _load_entries(yaml_path)
        display_name = _derive_display_name(doc)
        section_anchor = _find_section_anchor(doc)
        index_anchor = slugify(display_name)
        components.append(
            Component(
                doc_path=doc,
                yaml_path=yaml_path,
                display_name=display_name,
                section_anchor=section_anchor,
                index_anchor=index_anchor,
                entries=entries,
            )
        )
    components.sort(key=lambda item: item.display_name.lower())
    return components


def build_content(*, check: bool) -> bool:
    components = _collect_components()
    stale = False
    for component in components:
        if not _update_document(component, check=check):
            stale = True
    appendix_body = _render_appendix(components)
    appendix_text = APPENDIX_FILE.read_text(encoding="utf-8")
    new_appendix = replace_auto_generated_section(appendix_text, APPENDIX_LABEL, appendix_body)
    if not write_or_check(
        APPENDIX_FILE,
        new_appendix,
        check=check,
        stale_message="API error codes tables are stale; run `python scripts/docs/build_api_error_codes.py`.",
    ):
        stale = True
    return not stale


def _run(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify the API error codes tables are up to date")
    args = parser.parse_args(argv)

    ok = build_content(check=args.check)
    if args.check and not ok:
        print("API error codes tables are stale; run `python scripts/docs/build_api_error_codes.py`.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_run())
