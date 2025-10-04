# pyright: strict

from rest_framework.routers import DefaultRouter
from django.urls import include, path

from apps.platform.cases.views import CaseViewSet


router = DefaultRouter()
router.register(r"cases", CaseViewSet, basename="case")

urlpatterns = [
    path("", include(router.urls)),
]

