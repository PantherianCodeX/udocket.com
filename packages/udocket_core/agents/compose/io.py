from __future__ import annotations

# pyright: strict

import logging
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, cast

from docxtpl import DocxTemplate  # type: ignore[import]

from ..common import next_versioned
from ..common.docx import write_basic_docx
from .settings import ComposeConfig
from .state import ComposeArtifacts, ComposeState, LaneOutcome


class ArtifactWriter:
    def __init__(self, *, config: ComposeConfig, logger: logging.Logger) -> None:
        self._config = config
        self._logger = logger

    def write(
        self,
        *,
        state: ComposeState,
        docs_dir: Path,
        job_id: str,
    ) -> ComposeArtifacts:
        artifacts = ComposeArtifacts()

        client_md_path = next_versioned(docs_dir / f"{job_id}__compose_client_v1.md")
        client_md_path.write_text(state.lanes["client"].document, encoding="utf-8")
        artifacts.client_markdown = client_md_path

        lawyer_md_path = next_versioned(docs_dir / f"{job_id}__compose_lawyer_v1.md")
        lawyer_md_path.write_text(state.lanes["lawyer"].document, encoding="utf-8")
        artifacts.lawyer_markdown = lawyer_md_path

        bundle_path = next_versioned(docs_dir / f"{job_id}__compose_bundle_v1.md")
        bundle = build_bundle(state)
        bundle_path.write_text(bundle, encoding="utf-8")
        artifacts.bundle_path = bundle_path

        qa_result = state.qa
        if qa_result is None:
            raise ValueError("QA results missing when writing artifacts")

        staff_report_path = next_versioned(docs_dir / f"{job_id}__compose_staff_report_v1.md")
        staff_report_path.write_text(qa_result.staff_report, encoding="utf-8")
        artifacts.staff_report = staff_report_path

        qa_report_path = next_versioned(docs_dir / f"{job_id}__compose_qa_report_v1.md")
        qa_report_text = render_qa_markdown(state)
        qa_report_path.write_text(qa_report_text, encoding="utf-8")
        artifacts.qa_report = qa_report_path

        shared_context = docx_placeholder_context(
            bundle=bundle,
            staff_report=qa_result.staff_report,
            qa_report=qa_report_text,
        )
        client_context = dict(shared_context)
        client_context["client_summary"] = state.lanes["client"].document
        lawyer_context = dict(shared_context)
        lawyer_context["lawyer_brief"] = state.lanes["lawyer"].document

        artifacts.client_docx = self._write_docx(
            markdown=state.lanes["client"].document,
            output_prefix=docs_dir / f"{job_id}__compose_client_v1",
            template_key="client_summary",
            docx_context=client_context,
        )
        artifacts.lawyer_docx = self._write_docx(
            markdown=state.lanes["lawyer"].document,
            output_prefix=docs_dir / f"{job_id}__compose_lawyer_v1",
            template_key="lawyer_brief",
            docx_context=lawyer_context,
        )

        return artifacts

    def _write_docx(
        self,
        *,
        markdown: str,
        output_prefix: Path,
        template_key: str,
        docx_context: Mapping[str, str],
    ) -> Optional[Path]:
        output_path = next_versioned(output_prefix.with_suffix(".docx"))
        template_path = self._config.doc_template_path
        if template_path and template_path.exists():
            context = dict(docx_context)
            context[template_key] = markdown
            if render_docx_from_template(template_path, context, output_path):
                return output_path
            self._logger.debug(
                "compose.doc_template.fallback",
                extra={"template": str(template_path), "output": str(output_path)},
            )
        paragraphs = markdown_paragraphs(markdown)
        write_basic_docx(paragraphs=paragraphs, output_path=output_path, title=output_prefix.name)
        return output_path


def build_bundle(state: ComposeState) -> str:
    sections = [
        "Part 1 – Client Summary",
        state.lanes["client"].document.strip(),
        "",
        "---",
        "",
        "Part 2 – Lawyer Brief",
        state.lanes["lawyer"].document.strip(),
    ]
    return "\n".join(sections).strip() + "\n"


def render_qa_markdown(state: ComposeState) -> str:
    qa = state.qa
    if qa is None:
        raise ValueError("QA results missing when rendering QA markdown")
    lines = ["# QA Review", ""]
    lines.append(f"**Status:** {qa.status}")
    if qa.provider:
        lines.append(f"**Provider:** {qa.provider}")
    if qa.global_notes:
        lines.append("")
        lines.append("## QA Notes")
        lines.append(qa.global_notes.strip())
    if qa.alerts:
        lines.append("## Alerts")
        lines.extend([f"- {alert}" for alert in qa.alerts])
    if qa.recommendations:
        lines.append("")
        lines.append("## Recommendations")
        lines.extend([f"- {rec}" for rec in qa.recommendations])
    if qa.lane_actions:
        lines.append("")
        lines.append("## Lane Actions")
        for lane, directive in qa.lane_actions.items():
            action_text = directive.original_action or "none"
            brief = directive.revision_brief or ""
            reason = directive.reason or ""
            lines.append(f"- {lane.title()}: {action_text}")
            if brief:
                lines.append(f"  - Brief: {brief}")
            if reason:
                lines.append(f"  - Reason: {reason}")

    def _lane_section(title: str, outcome: LaneOutcome) -> None:
        lines.append("")
        lines.append(f"## {title} Lane")
        lines.append(f"- Attempts: {outcome.attempts}")
        lines.append(f"- Structure: {'ok' if outcome.structure_report.ok else 'fail'}")
        if outcome.structure_report.errors:
            lines.extend([f"  - {error}" for error in outcome.structure_report.errors])
        lines.append(f"- Compliance: {'ok' if outcome.compliance_report.ok else 'fail'}")
        if outcome.compliance_report.errors:
            lines.extend([f"  - {error}" for error in outcome.compliance_report.errors])
        lines.append(f"- Factuality: {'ok' if outcome.factuality_report.ok else 'fail'}")
        if outcome.factuality_report.errors:
            lines.extend([f"  - {error}" for error in outcome.factuality_report.errors])

    _lane_section("Client", state.lanes["client"])
    _lane_section("Lawyer", state.lanes["lawyer"])

    lines.append("")
    lines.append("## Staff Report")
    lines.append(qa.staff_report.strip())
    return "\n".join(lines).strip() + "\n"


def docx_placeholder_context(**sections: str) -> dict[str, str]:
    base: dict[str, str] = {
        "client_summary": "",
        "lawyer_brief": "",
        "bundle": "",
        "staff_report": "",
        "qa_report": "",
    }
    for key, value in sections.items():
        base[key] = value
    return base


def render_docx_from_template(template_path: Path, context: Mapping[str, str], output_path: Path) -> bool:
    try:
        template = DocxTemplate(str(template_path))
    except Exception:
        return False
    try:
        context_map: dict[str, Any] = dict(context)
        template.render(context_map)
        save_method = cast(Callable[[str], None], getattr(template, "save"))
        save_method(str(output_path))
        return True
    except Exception:
        return False


def markdown_paragraphs(markdown_text: str) -> list[str]:
    lines = markdown_text.splitlines()
    buffer: list[str] = []
    paragraphs: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer.clear()
            continue
        if stripped.startswith("##"):
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer.clear()
            paragraphs.append(stripped)
        else:
            buffer.append(stripped)
    if buffer:
        paragraphs.append(" ".join(buffer).strip())
    return paragraphs


def markdown_to_subdoc(template: Any, markdown: str) -> Any:
    subdoc: Any = template.new_subdoc()
    lines = markdown.splitlines()
    if not lines:
        subdoc.add_paragraph("")
        return subdoc
    for raw_line in lines:
        line = raw_line.rstrip("\r")
        stripped = line.strip()
        if not stripped:
            subdoc.add_paragraph("")
            continue
        if stripped.startswith("### "):
            subdoc.add_paragraph(stripped[4:].strip(), style="Heading 3")
            continue
        if stripped.startswith("## "):
            subdoc.add_paragraph(stripped[3:].strip(), style="Heading 2")
            continue
        if stripped.startswith(("- ", "* ")):
            subdoc.add_paragraph(stripped[2:].strip(), style="List Bullet")
            continue
        subdoc.add_paragraph(stripped)
    return subdoc


__all__ = [
    "ArtifactWriter",
    "build_bundle",
    "docx_placeholder_context",
    "markdown_paragraphs",
    "markdown_to_subdoc",
    "render_docx_from_template",
    "render_qa_markdown",
]
