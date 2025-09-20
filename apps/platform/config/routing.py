from django.urls import path
from apps.platform.operations import consumers


websocket_urlpatterns = [
    path("ws/jobs/<str:job_id>/", consumers.JobConsumer.as_asgi()),
    path("ws/cases/<str:case_id>/", consumers.CaseConsumer.as_asgi()),
]

