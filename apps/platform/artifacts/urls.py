from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.platform.artifacts.views import ArtifactViewSet

router = DefaultRouter()
router.register(r"artifacts", ArtifactViewSet, basename="artifact")

urlpatterns = [
    path("", include(router.urls)),
]
