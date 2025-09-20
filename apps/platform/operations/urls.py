from rest_framework.routers import DefaultRouter
from django.urls import include, path

from apps.platform.operations.views import DiagnosticsViewSet


router = DefaultRouter()
router.register(r"diagnostics", DiagnosticsViewSet, basename="diagnostics")

urlpatterns = [
    path("", include(router.urls)),
]

