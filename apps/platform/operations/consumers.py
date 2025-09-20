from __future__ import annotations

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from apps.platform.jobs.models import Job


class JobConsumer(AsyncJsonWebsocketConsumer):
    group_name: str

    async def connect(self):
        job_id = self.scope["url_route"]["kwargs"].get("job_id")
        self.group_name = f"jobs_{job_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # Send initial snapshot so the UI reflects current status immediately
        payload = await self._current_job_payload(job_id)
        await self.send_json(payload)

    async def disconnect(self, close_code):  # noqa: D401
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def job_update(self, event):
        await self.send_json(event)

    @database_sync_to_async
    def _current_job_payload(self, job_id: str) -> dict:
        try:
            j = Job.objects.get(pk=job_id)
            return {
                "type": "job.update",
                "event": "snapshot",
                "job_id": str(j.id),
                "status": j.status,
                "transcript_path": j.transcript_path,
                "transcript_file": j.transcript_path,
            }
        except Job.DoesNotExist:
            return {"type": "job.update", "event": "snapshot", "job_id": job_id, "status": "UNKNOWN"}


class CaseConsumer(AsyncJsonWebsocketConsumer):
    group_name: str

    async def connect(self):
        case_id = self.scope["url_route"]["kwargs"].get("case_id")
        self.group_name = f"cases_{case_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):  # noqa: D401
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def case_update(self, event):
        await self.send_json(event)
