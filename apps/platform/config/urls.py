from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("", include("apps.platform.ui.urls")),
    path("api/v1/", include("apps.platform.cases.urls")),
    path("api/v1/", include("apps.platform.jobs.urls")),
    path("api/v1/", include("apps.platform.artifacts.urls")),
]
