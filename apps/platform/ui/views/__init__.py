from __future__ import annotations

from apps.platform.operations.tasks import transcribe_job

from .auth import ensure_authenticated, logout_view, select_organization
from .cases import (
    case_analysis_module,
    case_assign_client,
    case_assign_reviewer,
    case_detail,
    case_details_update,
    case_llm_providers,
    case_llm_provider_delete,
    case_llm_settings,
    case_tool_panel,
    case_update_title,
)
from .cases.guardian import case_guardian_report
from .contexts import (
    compute_case_tool_state,
    format_metadata,
    get_case_and_org,
    job_detail_context,
    user_can_review_case,
)
from .dashboard import index
from .jobs import (
    case_job_detail_panel,
    job_detail_panel,
    jobs,
)
from .jobs_actions import (
    case_job_create_artifact,
    case_job_row,
    case_job_title_form,
    case_job_update_title,
    create_job,
    summary_upload_transcript_text,
)
from .jobs_modals import (
    case_job_logs_modal,
    case_job_metadata_modal,
    case_job_transcript,
)
from .misc import favicon, ui_log
from .settings import organization_settings
from .permissions import permissions_overview
from .presenters.cases import table_config

__all__ = [
    "compute_case_tool_state",
    "ensure_authenticated",
    "format_metadata",
    "get_case_and_org",
    "job_detail_context",
    "table_config",
    "user_can_review_case",
    "case_analysis_module",
    "case_assign_client",
    "case_assign_reviewer",
    "case_detail",
    "case_details_update",
    "case_llm_settings",
    "case_llm_providers",
    "case_llm_provider_delete",
    "case_job_create_artifact",
    "case_job_detail_panel",
    "case_job_logs_modal",
    "case_job_metadata_modal",
    "case_job_row",
    "case_job_title_form",
    "case_job_transcript",
    "case_job_update_title",
    "case_tool_panel",
    "case_update_title",
    "case_guardian_report",
    "create_job",
    "summary_upload_transcript_text",
    "favicon",
    "index",
    "job_detail_panel",
    "jobs",
    "transcribe_job",
    "logout_view",
    "organization_settings",
    "permissions_overview",
    "select_organization",
    "ui_log",
]
