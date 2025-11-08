from __future__ import annotations

# pyright: strict
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false
from django.http import HttpRequest

from apps.platform.jobs.models import Job
from apps.platform.jobs.serializers import JobTelemetrySerializer

from ..common import JobTelemetryPayload, as_dict


def job_telemetry_payload(
    job: Job,
    request: HttpRequest | None,
    *,
    ui_mode: bool = True,
) -> JobTelemetryPayload:
    serializer = JobTelemetrySerializer(job, context={"request": request, "ui_mode": ui_mode})
    return as_dict(serializer.data)


def job_telemetry_map(
    jobs: list[Job],
    request: HttpRequest | None,
    *,
    ui_mode: bool = True,
) -> dict[str, JobTelemetryPayload]:
    serializer = JobTelemetrySerializer(
        jobs, many=True, context={"request": request, "ui_mode": ui_mode}
    )
    payloads: list[JobTelemetryPayload] = []
    for item in serializer.data:
        payloads.append(as_dict(item))
    telemetry_map: dict[str, JobTelemetryPayload] = {}
    for payload in payloads:
        identifier = payload.get("id")
        if isinstance(identifier, (str, int)):
            telemetry_map[str(identifier)] = payload
    return telemetry_map
