# pyright: strict

from __future__ import annotations

from collections.abc import Mapping as MappingABC
from typing import Iterable, Mapping, Sequence, TYPE_CHECKING, cast

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

from apps.platform.cases.models import CaseMembership
from apps.platform.jobs.models import Job
from apps.platform.tenancy import scope_jobs

GroupName = str
JsonPayload = Mapping[str, object]
MutableJson = dict[str, object]

if TYPE_CHECKING:
    from channels.layers import ChannelLayerProtocol
else:  # pragma: no cover - runtime fallback for typing-only import
    ChannelLayerProtocol = object


def _scope_kwargs(scope: Mapping[str, object]) -> Mapping[str, object]:
    url_route = scope.get("url_route")
    if isinstance(url_route, MappingABC):
        url_route_mapping = cast(Mapping[str, object], url_route)
        kwargs = url_route_mapping.get("kwargs")
        if isinstance(kwargs, MappingABC):
            return cast(Mapping[str, object], kwargs)
    return cast(Mapping[str, object], {})


def _require_channel_layer(layer: "ChannelLayerProtocol | None") -> "ChannelLayerProtocol":
    if layer is None:
        msg = "Channel layer is not configured for websocket consumer"
        raise RuntimeError(msg)
    return layer


class JobStreamConsumer(AsyncJsonWebsocketConsumer):
    subscribed_jobs: set[str]
    subscribed_cases: set[str]

    async def connect(self) -> None:
        if not await self._can_access():
            await self.close(code=4403)
            return
        self.subscribed_jobs = set()
        self.subscribed_cases = set()
        await self.accept()
        await self.send_json({"type": "job.stream", "event": "connected"})

    async def disconnect(self, code: int) -> None:  # noqa: D401 - signature mandated by Channels
        layer = _require_channel_layer(self.channel_layer)
        for job_id in list(self.subscribed_jobs):
            await layer.group_discard(f"jobs_{job_id}", self.channel_name)
        for case_id in list(self.subscribed_cases):
            await layer.group_discard(f"cases_{case_id}", self.channel_name)
        self.subscribed_jobs.clear()
        self.subscribed_cases.clear()

    async def receive_json(self, content: Mapping[str, object], **_: object) -> None:
        action = str(content.get("action") or "").strip().lower()
        if action in {"subscribe", "add"}:
            await self._handle_subscribe(content)
        elif action in {"unsubscribe", "remove"}:
            await self._handle_unsubscribe(content)
        elif action in {"replace", "set"}:
            await self._handle_replace(content)
        elif action == "ping":
            await self.send_json({"type": "job.stream", "event": "pong"})
        else:
            await self.send_json(
                {"type": "job.stream", "event": "error", "error": "unknown_action"}
            )

    async def job_update(self, event: JsonPayload) -> None:
        await self.send_json(event)

    async def case_update(self, event: JsonPayload) -> None:
        await self.send_json(event)

    async def _handle_subscribe(self, payload: Mapping[str, object]) -> None:
        job_ids = self._normalize_ids(payload.get("jobs"))
        case_ids = self._normalize_ids(payload.get("cases"))

        granted_jobs: list[str] = await self._authorized_job_ids(job_ids)
        denied_jobs = sorted(set(job_ids) - set(granted_jobs))
        layer = _require_channel_layer(self.channel_layer)
        for job_id in granted_jobs:
            if job_id in self.subscribed_jobs:
                continue
            await layer.group_add(f"jobs_{job_id}", self.channel_name)
            self.subscribed_jobs.add(job_id)

        granted_cases: list[str] = await self._authorized_case_ids(case_ids)
        denied_cases = sorted(set(case_ids) - set(granted_cases))
        for case_id in granted_cases:
            if case_id in self.subscribed_cases:
                continue
            await layer.group_add(f"cases_{case_id}", self.channel_name)
            self.subscribed_cases.add(case_id)

        await self.send_json(
            {
                "type": "job.stream",
                "event": "subscribed",
                "jobs": granted_jobs,
                "cases": granted_cases,
                "denied_jobs": denied_jobs,
                "denied_cases": denied_cases,
            }
        )

    async def _handle_unsubscribe(self, payload: Mapping[str, object]) -> None:
        job_ids = self._normalize_ids(payload.get("jobs"))
        case_ids = self._normalize_ids(payload.get("cases"))

        removed_jobs: list[str] = []
        layer = _require_channel_layer(self.channel_layer)
        for job_id in job_ids:
            if job_id not in self.subscribed_jobs:
                continue
            await layer.group_discard(f"jobs_{job_id}", self.channel_name)
            self.subscribed_jobs.remove(job_id)
            removed_jobs.append(job_id)

        removed_cases: list[str] = []
        for case_id in case_ids:
            if case_id not in self.subscribed_cases:
                continue
            await layer.group_discard(f"cases_{case_id}", self.channel_name)
            self.subscribed_cases.remove(case_id)
            removed_cases.append(case_id)

        await self.send_json(
            {
                "type": "job.stream",
                "event": "unsubscribed",
                "jobs": removed_jobs,
                "cases": removed_cases,
            }
        )

    async def _handle_replace(self, payload: Mapping[str, object]) -> None:
        job_ids = set(self._normalize_ids(payload.get("jobs")))
        case_ids = set(self._normalize_ids(payload.get("cases")))

        current_jobs = set(self.subscribed_jobs)
        current_cases = set(self.subscribed_cases)

        to_add_jobs = sorted(job_ids - current_jobs)
        to_remove_jobs = sorted(current_jobs - job_ids)
        to_add_cases = sorted(case_ids - current_cases)
        to_remove_cases = sorted(current_cases - case_ids)

        if to_remove_jobs or to_remove_cases:
            await self._handle_unsubscribe({"jobs": to_remove_jobs, "cases": to_remove_cases})
        if to_add_jobs or to_add_cases:
            await self._handle_subscribe({"jobs": to_add_jobs, "cases": to_add_cases})

    async def _can_access(self) -> bool:
        if getattr(settings, "PLATFORM_DEV_OPEN", True):
            return True
        user = self.scope.get("user")
        return bool(user and getattr(user, "is_authenticated", False))

    @staticmethod
    def _normalize_ids(raw_values: object) -> list[str]:
        if raw_values is None:
            return []
        if isinstance(raw_values, (str, int)):
            values: Iterable[object] = [raw_values]
        elif isinstance(raw_values, Iterable):
            values = cast(Iterable[object], raw_values)
        else:
            return []

        normalized: list[str] = []
        for value in values:
            try:
                normalized_value = str(value).strip()
            except Exception:  # noqa: BLE001 - best effort sanitisation
                continue
            if normalized_value:
                normalized.append(normalized_value)
        return normalized

    @database_sync_to_async
    def _authorized_job_ids(self, job_ids: Sequence[str]) -> list[str]:
        if not job_ids:
            return []
        qs = Job.objects.filter(pk__in=job_ids)
        if getattr(settings, "PLATFORM_DEV_OPEN", True):
            return [str(pk) for pk in qs.values_list("pk", flat=True)]
        user = self.scope.get("user")
        scoped = scope_jobs(qs, user)
        return [str(pk) for pk in scoped.values_list("pk", flat=True)]

    @database_sync_to_async
    def _authorized_case_ids(self, case_ids: Sequence[str]) -> list[str]:
        if not case_ids:
            return []
        if getattr(settings, "PLATFORM_DEV_OPEN", True):
            return [str(case_id) for case_id in case_ids]
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            return []
        return [
            str(case_id)
            for case_id in CaseMembership.objects.filter(
                case_id__in=case_ids, user=user
            ).values_list("case_id", flat=True)
        ]


class JobConsumer(AsyncJsonWebsocketConsumer):
    group_name: GroupName

    async def connect(self) -> None:
        scope_kwargs = _scope_kwargs(self.scope)
        job_value = scope_kwargs.get("job_id")
        job_id = str(job_value) if job_value is not None else ""
        self.group_name = f"jobs_{job_id}"
        if not await self._allowed_for_job(job_id):
            await self.close(code=4403)
            return
        layer = _require_channel_layer(self.channel_layer)
        await layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        payload: MutableJson = await self._current_job_payload(job_id)
        await self.send_json(payload)

    async def disconnect(self, code: int) -> None:  # noqa: D401
        layer = _require_channel_layer(self.channel_layer)
        await layer.group_discard(self.group_name, self.channel_name)

    async def job_update(self, event: JsonPayload) -> None:
        await self.send_json(event)

    @database_sync_to_async
    def _current_job_payload(self, job_id: str) -> MutableJson:
        try:
            job = Job.objects.get(pk=job_id)
        except Job.DoesNotExist:
            return {"type": "job.update", "event": "snapshot", "job_id": job_id, "status": "UNKNOWN"}
        return {
            "type": "job.update",
            "event": "snapshot",
            "job_id": str(job.id),
            "status": job.status,
            "transcript_path": job.transcript_path,
            "transcript_file": job.transcript_path,
            "upload_progress": job.upload_progress,
            "progress_percent": job.upload_progress,
        }

    @database_sync_to_async
    def _allowed_for_job(self, job_id: str) -> bool:
        if getattr(settings, "PLATFORM_DEV_OPEN", True):
            return True
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            return False
        try:
            job = Job.objects.select_related("case").get(pk=job_id)
        except Job.DoesNotExist:
            return False
        return CaseMembership.objects.filter(case=job.case, user=user).exists()


class CaseConsumer(AsyncJsonWebsocketConsumer):
    group_name: GroupName

    async def connect(self) -> None:
        scope_kwargs = _scope_kwargs(self.scope)
        case_value = scope_kwargs.get("case_id")
        case_id = str(case_value) if case_value is not None else ""
        self.group_name = f"cases_{case_id}"
        if not await self._allowed_for_case(case_id):
            await self.close(code=4403)
            return
        layer = _require_channel_layer(self.channel_layer)
        await layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:  # noqa: D401
        layer = _require_channel_layer(self.channel_layer)
        await layer.group_discard(self.group_name, self.channel_name)

    async def case_update(self, event: JsonPayload) -> None:
        await self.send_json(event)

    @database_sync_to_async
    def _allowed_for_case(self, case_id: str) -> bool:
        if getattr(settings, "PLATFORM_DEV_OPEN", True):
            return True
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return CaseMembership.objects.filter(case_id=case_id, user=user).exists()
