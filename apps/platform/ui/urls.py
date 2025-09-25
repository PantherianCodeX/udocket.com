from django.urls import path
from apps.platform.ui import views


urlpatterns = [
    path("favicon.ico", views.favicon, name="ui-favicon"),
    path("", views.index, name="ui-index"),
    path("cases/<str:case_id>/", views.case_detail, name="ui-case-detail"),
    path("ui/log", views.ui_log, name="ui-log"),
    path(
        "cases/<str:case_id>/tools/<str:tool_key>/",
        views.case_tool_panel,
        name="ui-case-tool-panel",
    ),
    path(
        "cases/<str:case_id>/jobs/<uuid:job_id>/transcript/",
        views.case_job_transcript,
        name="ui-case-job-transcript",
    ),
    path(
        "cases/<str:case_id>/jobs/<uuid:job_id>/logs/modal/",
        views.case_job_logs_modal,
        name="ui-case-job-logs-modal",
    ),
    path(
        "cases/<str:case_id>/jobs/<uuid:job_id>/metadata/modal/",
        views.case_job_metadata_modal,
        name="ui-case-job-metadata-modal",
    ),
    path(
        "cases/<str:case_id>/analysis/<str:agent>/module/",
        views.case_analysis_module,
        name="ui-case-analysis-module",
    ),
    path(
        "cases/<str:case_id>/tools/case-details/update/",
        views.case_details_update,
        name="ui-case-details-update",
    ),
    path(
        "cases/<str:case_id>/llm/settings/",
        views.case_llm_settings,
        name="ui-case-llm-settings",
    ),
    path(
        "cases/<str:case_id>/llm/providers/",
        views.case_llm_providers,
        name="ui-case-llm-providers",
    ),
    path(
        "cases/<str:case_id>/llm/providers/<str:provider>/delete/",
        views.case_llm_provider_delete,
        name="ui-case-llm-provider-delete",
    ),
    path("cases/<str:case_id>/title", views.case_update_title, name="ui-case-update-title"),
    path("cases/<str:case_id>/jobs/<uuid:job_id>/detail/", views.case_job_detail_panel, name="ui-case-job-detail"),
    path(
        "cases/<str:case_id>/jobs/<uuid:job_id>/title/form/",
        views.case_job_title_form,
        name="ui-case-job-title-form",
    ),
    path(
        "cases/<str:case_id>/jobs/<uuid:job_id>/title/",
        views.case_job_update_title,
        name="ui-case-job-update-title",
    ),
    path(
        "cases/<str:case_id>/jobs/<uuid:job_id>/artifact/create/",
        views.case_job_create_artifact,
        name="ui-case-job-create-artifact",
    ),
    path("cases/<str:case_id>/jobs/<uuid:job_id>/row/", views.case_job_row, name="ui-case-job-row"),
    path("cases/<str:case_id>/jobs/new", views.create_job, name="ui-job-create"),
    path("cases/<str:case_id>/assign-reviewer/", views.case_assign_reviewer, name="ui-case-assign-reviewer"),
    path("cases/<str:case_id>/assign-client/", views.case_assign_client, name="ui-case-assign-client"),
    path("jobs/", views.jobs, name="ui-jobs"),
    path("org/select/", views.select_organization, name="ui-select-organization"),
    path("jobs/<uuid:job_id>/detail-panel/", views.job_detail_panel, name="ui-job-detail-panel"),
    path("permissions/", views.permissions_overview, name="ui-permissions"),
    path("logout/", views.logout_view, name="ui-logout"),
]
