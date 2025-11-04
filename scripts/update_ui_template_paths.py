#!/usr/bin/env python3
"""Rename UI partial templates to components and update references."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

FILE_MAPPING: dict[str, str] = {
    "apps/platform/ui/templates/platform_ui/partials/analysis_module.html": "apps/platform/ui/templates/platform_ui/components/cases/analysis_module.html",
    "apps/platform/ui/templates/platform_ui/partials/case_progress.html": "apps/platform/ui/templates/platform_ui/components/cases/case_progress.html",
    "apps/platform/ui/templates/platform_ui/partials/case_title.html": "apps/platform/ui/templates/platform_ui/components/cases/case_title.html",
    "apps/platform/ui/templates/platform_ui/partials/job_detail.html": "apps/platform/ui/templates/platform_ui/components/jobs/job_detail.html",
    "apps/platform/ui/templates/platform_ui/partials/job_detail_audio_conversion.html": "apps/platform/ui/templates/platform_ui/components/jobs/job_detail_audio_conversion.html",
    "apps/platform/ui/templates/platform_ui/partials/job_detail_title_form.html": "apps/platform/ui/templates/platform_ui/components/jobs/job_detail_title_form.html",
    "apps/platform/ui/templates/platform_ui/partials/job_row.html": "apps/platform/ui/templates/platform_ui/components/jobs/job_row.html",
    "apps/platform/ui/templates/platform_ui/partials/job_metadata_modal.html": "apps/platform/ui/templates/platform_ui/components/modals/job_metadata_modal.html",
    "apps/platform/ui/templates/platform_ui/partials/log_modal.html": "apps/platform/ui/templates/platform_ui/components/modals/log_modal.html",
    "apps/platform/ui/templates/platform_ui/partials/metadata_modal.html": "apps/platform/ui/templates/platform_ui/components/modals/metadata_modal.html",
    "apps/platform/ui/templates/platform_ui/partials/modal_base.html": "apps/platform/ui/templates/platform_ui/components/modals/modal_base.html",
    "apps/platform/ui/templates/platform_ui/partials/text_modal.html": "apps/platform/ui/templates/platform_ui/components/modals/text_modal.html",
    "apps/platform/ui/templates/platform_ui/partials/transcript_modal.html": "apps/platform/ui/templates/platform_ui/components/modals/transcript_modal.html",
}

STRING_MAPPING: dict[str, str] = {
    "platform_ui/partials/analysis_module.html": "platform_ui/components/cases/analysis_module.html",
    "platform_ui/partials/case_progress.html": "platform_ui/components/cases/case_progress.html",
    "platform_ui/partials/case_title.html": "platform_ui/components/cases/case_title.html",
    "platform_ui/partials/job_detail.html": "platform_ui/components/jobs/job_detail.html",
    "platform_ui/partials/job_detail_audio_conversion.html": "platform_ui/components/jobs/job_detail_audio_conversion.html",
    "platform_ui/partials/job_detail_title_form.html": "platform_ui/components/jobs/job_detail_title_form.html",
    "platform_ui/partials/job_row.html": "platform_ui/components/jobs/job_row.html",
    "platform_ui/partials/job_metadata_modal.html": "platform_ui/components/modals/job_metadata_modal.html",
    "platform_ui/partials/log_modal.html": "platform_ui/components/modals/log_modal.html",
    "platform_ui/partials/metadata_modal.html": "platform_ui/components/modals/metadata_modal.html",
    "platform_ui/partials/modal_base.html": "platform_ui/components/modals/modal_base.html",
    "platform_ui/partials/text_modal.html": "platform_ui/components/modals/text_modal.html",
    "platform_ui/partials/transcript_modal.html": "platform_ui/components/modals/transcript_modal.html",
}

TEXT_SUFFIXES = {
    ".py",
    ".html",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".css",
    ".scss",
    ".md",
    ".json",
    ".yml",
    ".yaml",
    ".txt",
}


def rename_templates() -> None:
    for old_rel, new_rel in FILE_MAPPING.items():
        old_path = REPO_ROOT / old_rel
        new_path = REPO_ROOT / new_rel
        if not old_path.exists():
            continue
        new_path.parent.mkdir(parents=True, exist_ok=True)
        if new_path.exists():
            print(f"[skip] target exists: {new_rel}")
            continue
        print(f"[move] {old_rel} -> {new_rel}")
        old_path.rename(new_path)


def update_references() -> None:
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix and path.suffix not in TEXT_SUFFIXES:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        original = text
        for old, new in STRING_MAPPING.items():
            if old in text:
                text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding="utf-8")
            rel = path.relative_to(REPO_ROOT)
            print(f"[update] {rel}")


def main() -> None:
    rename_templates()
    update_references()


if __name__ == "__main__":
    main()
