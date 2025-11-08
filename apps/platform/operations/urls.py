# pyright: strict

from rest_framework.routers import DefaultRouter

from apps.platform.operations.views import DiagnosticsViewSet

router = DefaultRouter()
router.register(r"diagnostics", DiagnosticsViewSet, basename="diagnostics")

urlpatterns = router.urls
