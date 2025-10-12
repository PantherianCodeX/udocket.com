from __future__ import annotations

"""Shared formatting helpers for compose agent logging."""

# pyright: strict

from dataclasses import dataclass
from typing import Mapping, Sequence


def _safe_int(value: object) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return None
    return None


def _safe_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _sequence_size(value: object) -> int:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len(value)
    return 0


@dataclass(slots=True)
class ComposeLogContext:
    """Lightweight context that decorates compose logs with human identifiers."""

    case_id: str
    job_id: str
    case_title: str | None = None
    job_display_title: str | None = None
    organization_name: str | None = None

    @property
    def case_label(self) -> str:
        if self.case_title:
            return self.case_title
        if self.job_display_title:
            return self.job_display_title
        return self.case_id

    @property
    def prefix(self) -> str:
        return f"Case [{self.case_label}]"

    def with_fallback(self, *, case_title: str | None = None) -> "ComposeLogContext":
        if self.case_title:
            return self
        if case_title:
            return ComposeLogContext(
                case_id=self.case_id,
                job_id=self.job_id,
                case_title=case_title,
                job_display_title=self.job_display_title,
                organization_name=self.organization_name,
            )
        return self


_STAGE_LABELS: dict[str, str] = {
    "compose.context": "context assembly",
    "compose.release_gate": "release gate",
}


def _lane_stage_label(stage: str) -> str:
    parts = stage.split(".")
    if len(parts) < 3:
        return stage.replace("_", " ")
    lane, action = parts[1], parts[2]
    action_label = {
        "draft": "draft",
        "structure": "structure checks",
        "compliance": "compliance checks",
        "factuality": "factuality review",
        "revision": "revision brief",
        "revise": "revision drafting",
        "qa_reviewer": "QA review",
        "qa_revision": "QA-directed revision",
        "qa_editor": "QA editor pass",
        "editor": "editor pass",
    }.get(action, action.replace("_", " "))
    return f"{lane} {action_label}".strip()


def friendly_stage_label(stage: str) -> str:
    return _STAGE_LABELS.get(stage, _lane_stage_label(stage))


def format_stage_message(
    context: ComposeLogContext,
    stage: str,
    event: str,
    details: Mapping[str, object],
) -> str:
    label = friendly_stage_label(stage)
    attempt = _safe_int(details.get("attempt"))
    lane = _safe_str(details.get("lane"))
    source = _safe_str(details.get("source"))
    provider = _safe_str(details.get("provider"))
    model = _safe_str(details.get("model"))
    error_count = _safe_int(details.get("error_count"))
    warning_count = _safe_int(details.get("warning_count"))
    if error_count is None and "errors" in details:
        error_count = _sequence_size(details.get("errors"))
    if warning_count is None and "warnings" in details:
        warning_count = _sequence_size(details.get("warnings"))

    suffix_parts: list[str] = []
    if lane:
        suffix_parts.append(f"lane {lane}")
    if attempt is not None:
        suffix_parts.append(f"attempt {attempt}")
    if source:
        suffix_parts.append(f"source {source}")

    if event == "start":
        suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
        return f"{context.prefix}: Compose agent starting {label}{suffix}."
    if event == "complete":
        provider_clause = f" via {provider}:{model}" if provider and model else ""
        suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
        summary_bits: list[str] = []
        if error_count:
            summary_bits.append(f"errors={error_count}")
        if warning_count:
            summary_bits.append(f"warnings={warning_count}")
        summary = f" [{', '.join(summary_bits)}]" if summary_bits else ""
        return (
            f"{context.prefix}: Compose agent finished {label}{suffix}{provider_clause}.{summary}"
        )
    if event == "max_attempts_exhausted":
        suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
        return f"{context.prefix}: Compose agent exhausted attempts for {label}{suffix}."
    if event == "error":
        suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
        error_text = _safe_str(details.get("error"))
        if error_text:
            return f"{context.prefix}: Compose agent error in {label}{suffix}: {error_text}."
        return f"{context.prefix}: Compose agent error in {label}{suffix}."
    suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
    return f"{context.prefix}: Compose agent event '{event}' for {label}{suffix}."


def format_run_message(
    context: ComposeLogContext,
    event: str,
    payload: Mapping[str, object],
) -> str:
    sequence = _safe_int(payload.get("sequence"))
    stage = _safe_str(payload.get("stage"))
    stage_label = friendly_stage_label(stage) if stage else "compose stage"
    snapshot_path = _safe_str(payload.get("path"))

    if event.endswith("reset_begin"):
        location = _safe_str(payload.get("snapshot_dir"))
        suffix = f" ({location})" if location else ""
        return f"{context.prefix}: Preparing compose snapshots{suffix}."
    if event.endswith("reset_complete"):
        return f"{context.prefix}: Compose snapshots cleared."
    if event.endswith("snapshot_recorded"):
        suffix = f" #{sequence}" if sequence is not None else ""
        path_clause = f" ({snapshot_path})" if snapshot_path else ""
        return f"{context.prefix}: Saved compose snapshot{suffix} for {stage_label}{path_clause}."
    if event.endswith("snapshot_restored"):
        suffix = f" #{sequence}" if sequence is not None else ""
        path_clause = f" ({snapshot_path})" if snapshot_path else ""
        return f"{context.prefix}: Restored compose snapshot{suffix} for {stage_label}{path_clause}."
    if event.endswith("manifest_written"):
        suffix = f" #{sequence}" if sequence is not None else ""
        return f"{context.prefix}: Updated compose manifest{suffix} for {stage_label}."
    if event.endswith("manifest_read_failed"):
        path_clause = f" ({snapshot_path})" if snapshot_path else ""
        return f"{context.prefix}: Failed reading compose manifest{path_clause}."
    if event.endswith("snapshot_failed"):
        path_clause = f" ({snapshot_path})" if snapshot_path else ""
        return f"{context.prefix}: Failed writing compose snapshot{path_clause}."
    return f"{context.prefix}: Compose run event '{event}'."


__all__ = [
    "ComposeLogContext",
    "format_stage_message",
    "format_run_message",
    "friendly_stage_label",
]
