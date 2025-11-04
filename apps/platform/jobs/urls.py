from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.platform.jobs.views import JobViewSet

router = DefaultRouter()
router.register(r"jobs", JobViewSet, basename="job")

urlpatterns = [
    path("", include(router.urls)),
]
