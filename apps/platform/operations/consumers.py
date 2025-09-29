from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from typing import Any, Mapping, TypeAlias, cast

from channels.generic.websocket import AsyncJsonWebsocketConsumer  # pyright: ignore[reportMissingModuleSource]
from channels.db import database_sync_to_async  # pyright: ignore[reportMissingModuleSource]
from django.conf import settings as django_settings  # pyright: ignore[reportMissingImports]

from apps.platform.jobs.models import Job
from apps.platform.cases.models import CaseMembership


django_settings: Any

ScopeMapping: TypeAlias = Mapping[str, Any]
settings = cast(Any, django_settings)


class JobConsumer(AsyncJsonWebsocketConsumer):
    group_name: str

    async def connect(self) -> None:
        scope = _scope_mapping(self.scope)
        kwargs = _scope_kwargs(scope)
        job_id_value = kwargs.get("job_id")
        if not isinstance(job_id_value, str):
            await self.close(code=4400)
            return
        job_id = job_id_value
        self.group_name = f"jobs_{job_id}"
        if not await self._allowed_for_job(job_id):
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        payload = await self._current_job_payload(job_id)
        await self.send_json(payload)

    async def disconnect(self, code: int) -> None:  # noqa: D401
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def job_update(self, event: Mapping[str, Any]) -> None:
        await self.send_json(dict(event))

    @database_sync_to_async
    def _current_job_payload(self, job_id: str) -> dict[str, Any]:
        try:
            j = Job.objects.get(pk=job_id)
            return {
                "type": "job.update",
                "event": "snapshot",
                "job_id": str(j.id),
                "status": j.status,
                "transcript_path": j.transcript_path,
                "transcript_file": j.transcript_path,
                "upload_progress": j.upload_progress,
                "progress_percent": j.upload_progress,
            }
        except Job.DoesNotExist:
            return {
                "type": "job.update",
                "event": "snapshot",
                "job_id": job_id,
                "status": "UNKNOWN",
            }

    @database_sync_to_async
    def _allowed_for_job(self, job_id: str) -> bool:
        # Dev-open bypass for local
        if getattr(settings, "PLATFORM_DEV_OPEN", True):
            return True
        scope = _scope_mapping(self.scope)
        user = scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            return False
        try:
            j = Job.objects.select_related("case").get(pk=job_id)
        except Job.DoesNotExist:
            return False
        return CaseMembership.objects.filter(case=j.case, user=user).exists()


class CaseConsumer(AsyncJsonWebsocketConsumer):
    group_name: str

    async def connect(self) -> None:
        scope = _scope_mapping(self.scope)
        kwargs = _scope_kwargs(scope)
        case_id_value = kwargs.get("case_id")
        if not isinstance(case_id_value, str):
            await self.close(code=4400)
            return
        case_id = case_id_value
        self.group_name = f"cases_{case_id}"
        if not await self._allowed_for_case(case_id):
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:  # noqa: D401
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def case_update(self, event: Mapping[str, Any]) -> None:
        await self.send_json(dict(event))

    @database_sync_to_async
    def _allowed_for_case(self, case_id: str) -> bool:
        if getattr(settings, "PLATFORM_DEV_OPEN", True):
            return True
        scope = _scope_mapping(self.scope)
        user = scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return CaseMembership.objects.filter(case_id=case_id, user=user).exists()


def _scope_mapping(scope: Any) -> ScopeMapping:
    return cast(ScopeMapping, scope)


def _scope_kwargs(scope: ScopeMapping) -> Mapping[str, Any]:
    url_route = scope.get("url_route")
    if isinstance(url_route, Mapping):
        kwargs = url_route.get("kwargs")
        if isinstance(kwargs, Mapping):
            return kwargs
    return {}
