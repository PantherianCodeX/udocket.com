from django.urls import path
from apps.platform.ui import views


urlpatterns = [
    path("", views.index, name="ui-index"),
    path("cases/<str:case_id>/", views.case_detail, name="ui-case-detail"),
    path(
        "cases/<str:case_id>/analysis/<str:agent>/module/",
        views.case_analysis_module,
        name="ui-case-analysis-module",
    ),
    path("cases/<str:case_id>/title", views.case_update_title, name="ui-case-update-title"),
    path("cases/<str:case_id>/jobs/<uuid:job_id>/detail/", views.case_job_detail_panel, name="ui-case-job-detail"),
    path("cases/<str:case_id>/jobs/new", views.create_job, name="ui-job-create"),
    path("cases/<str:case_id>/assign-reviewer/", views.case_assign_reviewer, name="ui-case-assign-reviewer"),
    path("cases/<str:case_id>/assign-client/", views.case_assign_client, name="ui-case-assign-client"),
    path("jobs/", views.jobs, name="ui-jobs"),
    path("org/select/", views.select_organization, name="ui-select-organization"),
    path("jobs/<uuid:job_id>/detail-panel/", views.job_detail_panel, name="ui-job-detail-panel"),
    path("permissions/", views.permissions_overview, name="ui-permissions"),
    path("logout/", views.logout_view, name="ui-logout"),
]
