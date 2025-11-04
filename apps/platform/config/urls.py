from django.contrib import admin
from django.urls import include, path

from apps.platform.authorization import api as authz_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("", include("apps.platform.ui.urls")),
    path("api/v1/", include("apps.platform.cases.urls")),
    path("api/v1/", include("apps.platform.jobs.urls")),
    path("api/v1/", include("apps.platform.artifacts.urls")),
    path("api/v1/", include("apps.platform.operations.urls")),
    # Authz catalog endpoints (read-only)
    path("api/v1/authz/registry/", authz_api.registry_fields),
    path("api/v1/authz/presets/", authz_api.list_presets),
    path("api/v1/authz/roles/", authz_api.list_roles),
]
