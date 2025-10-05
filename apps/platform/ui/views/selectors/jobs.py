from __future__ import annotations

# pyright: strict
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false

from typing import Dict, List, Optional

from django.http import HttpRequest

from apps.platform.jobs.models import Job
from apps.platform.jobs.serializers import JobTelemetrySerializer

from ..common import JobTelemetryPayload, as_dict


def job_telemetry_payload(
    job: Job,
    request: Optional[HttpRequest],
    *,
    ui_mode: bool = True,
) -> JobTelemetryPayload:
    serializer = JobTelemetrySerializer(job, context={"request": request, "ui_mode": ui_mode})
    return as_dict(serializer.data)


def job_telemetry_map(
    jobs: List[Job],
    request: Optional[HttpRequest],
    *,
    ui_mode: bool = True,
) -> Dict[str, JobTelemetryPayload]:
    serializer = JobTelemetrySerializer(jobs, many=True, context={"request": request, "ui_mode": ui_mode})
    payloads: List[JobTelemetryPayload] = []
    for item in serializer.data:
        payloads.append(as_dict(item))
    telemetry_map: Dict[str, JobTelemetryPayload] = {}
    for payload in payloads:
        identifier = payload.get("id")
        if isinstance(identifier, (str, int)):
            telemetry_map[str(identifier)] = payload
    return telemetry_map
