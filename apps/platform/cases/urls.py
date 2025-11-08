# pyright: strict

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.platform.cases.views import CaseViewSet

router = DefaultRouter()
router.register(r"cases", CaseViewSet, basename="case")

urlpatterns = [
    path("", include(router.urls)),
]
