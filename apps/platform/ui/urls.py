from django.urls import path
from apps.platform.ui import views


urlpatterns = [
    path("", views.index, name="ui-index"),
    path("cases/<str:case_id>/", views.case_detail, name="ui-case-detail"),
    path("cases/<str:case_id>/jobs/new", views.create_job, name="ui-job-create"),
    path("jobs/", views.jobs, name="ui-jobs"),
    path("jobs/<uuid:job_id>/detail-panel/", views.job_detail_panel, name="ui-job-detail-panel"),
    path("permissions/", views.permissions_overview, name="ui-permissions"),
    path("logout/", views.logout_view, name="ui-logout"),
]
