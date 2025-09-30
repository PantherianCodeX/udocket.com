from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone

from apps.platform.jobs.models import Job
from apps.platform.operations.channels import send_job_update
from apps.platform.operations.utils import append_job_log, update_job_meta


def _safe_job_meta(
    case_id: str,
    organization_id: Optional[str],
    job_id: str,
    updates: Optional[Dict[str, Any]],
) -> None:
    if not updates:
        return
    try:
        update_job_meta(case_id, organization_id, job_id, updates)
    except Exception:
        pass


def _safe_job_log(
    case_id: str,
    organization_id: Optional[str],
    job_id: str,
    message: str,
    *,
    level: str = "INFO",
) -> None:
    if not message:
        return
    try:
        append_job_log(case_id, organization_id, job_id, message, level=level)
    except Exception:
        pass


def _emit_job_update(
    job_id: str,
    *,
    case_id: str,
    event: str,
    status: Optional[str] = None,
    **payload: Any,
) -> None:
    try:
        send_job_update(job_id, event=event, case_id=case_id, status=status, **payload)
    except Exception:
        pass


@dataclass
class JobRuntimeContext:
    """Mutable context for running background jobs with consistent lifecycle hooks."""

    job: Job
    case_id: str
    org_id: Optional[str]
    task_name: Optional[str] = None
    task_id: Optional[str] = None
    task_meta: Dict[str, Any] = field(default_factory=dict)
    _task_state: Dict[str, Any] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._task_state = dict(self.task_meta)

    @property
    def job_id(self) -> str:
        return str(self.job.id)

    @property
    def task_state(self) -> Dict[str, Any]:
        """Read-only view of the runtime task state."""

        return dict(self._task_state)

    def _update_task_state(self, updates: Optional[Dict[str, Any]]) -> None:
        if not updates:
            return
        self._task_state.update(updates)

    def start(
        self,
        *,
        status: str,
        log_message: Optional[str] = None,
        event: Optional[str] = None,
        meta_updates: Optional[Dict[str, Any]] = None,
        job_updates: Optional[Dict[str, Any]] = None,
        started_at: Optional[datetime] = None,
        job_event_payload: Optional[Dict[str, Any]] = None,
    ) -> datetime:
        started = started_at or timezone.now()
        update_fields: List[str] = ["status", "started_at", "finished_at", "error_message"]
        self.job.status = status
        self.job.started_at = started
        self.job.finished_at = None
        self.job.error_message = None
        if job_updates:
            for field, value in job_updates.items():
                setattr(self.job, field, value)
                if field not in update_fields:
                    update_fields.append(field)
        try:
            self.job.save(update_fields=update_fields)
        except Exception:
            pass

        _safe_job_log(self.case_id, self.org_id, self.job_id, log_message or "")
        _safe_job_meta(self.case_id, self.org_id, self.job_id, meta_updates)
        if event:
            payload = job_event_payload or {}
            _emit_job_update(self.job_id, case_id=self.case_id, event=event, status=status, **payload)
        self._update_task_state(
            {
                "status": status,
                "started_at": started.isoformat(),
                "task_id": self.task_id or "",
            }
        )
        return started

    def succeed(
        self,
        *,
        status: str = Job.Status.SUCCEEDED,
        log_message: Optional[str] = None,
        meta_updates: Optional[Dict[str, Any]] = None,
        events: Optional[List[Tuple[str, Dict[str, Any]]]] = None,
        job_updates: Optional[Dict[str, Any]] = None,
        task_meta_updates: Optional[Dict[str, Any]] = None,
        job_event_payload: Optional[Dict[str, Any]] = None,
    ) -> datetime:
        finished = timezone.now()
        update_fields: List[str] = ["status", "finished_at", "error_message"]
        self.job.status = status
        self.job.finished_at = finished
        self.job.error_message = None
        if job_updates:
            for field, value in job_updates.items():
                setattr(self.job, field, value)
                if field not in update_fields:
                    update_fields.append(field)
        try:
            self.job.save(update_fields=update_fields)
        except Exception:
            pass

        _safe_job_log(self.case_id, self.org_id, self.job_id, log_message or "")
        _safe_job_meta(self.case_id, self.org_id, self.job_id, meta_updates)

        payload = job_event_payload or {}
        _emit_job_update(self.job_id, case_id=self.case_id, event="job.succeeded", status=status, **payload)
        for event_name, payload in events or []:
            _emit_job_update(self.job_id, case_id=self.case_id, event=event_name, status=status, **payload)
        meta_payload = {"status": status, "finished_at": finished.isoformat()}
        if task_meta_updates:
            meta_payload.update(task_meta_updates)
        self._update_task_state(meta_payload)

        return finished

    def fail(
        self,
        *,
        error: str,
        status: str = Job.Status.FAILED,
        log_message: Optional[str] = None,
        meta_updates: Optional[Dict[str, Any]] = None,
        events: Optional[List[Tuple[str, Dict[str, Any]]]] = None,
        job_updates: Optional[Dict[str, Any]] = None,
        task_meta_updates: Optional[Dict[str, Any]] = None,
        job_event_payload: Optional[Dict[str, Any]] = None,
    ) -> datetime:
        finished = timezone.now()
        update_fields: List[str] = ["status", "finished_at", "error_message"]
        self.job.status = status
        self.job.finished_at = finished
        self.job.error_message = error
        if job_updates:
            for field, value in job_updates.items():
                setattr(self.job, field, value)
                if field not in update_fields:
                    update_fields.append(field)
        try:
            self.job.save(update_fields=update_fields)
        except Exception:
            pass

        log_line = log_message or f"Job failed: {error}"
        _safe_job_log(self.case_id, self.org_id, self.job_id, log_line, level="ERROR")
        _safe_job_meta(self.case_id, self.org_id, self.job_id, meta_updates)

        payload = job_event_payload or {}
        payload.setdefault("error", error)
        _emit_job_update(self.job_id, case_id=self.case_id, event="job.failed", status=status, **payload)
        for event_name, payload in events or []:
            payload_with_error = dict(payload)
            payload_with_error.setdefault("error", error)
            _emit_job_update(self.job_id, case_id=self.case_id, event=event_name, status=status, **payload_with_error)

        additional_meta = {"status": status, "finished_at": finished.isoformat(), "error": error}
        if task_meta_updates:
            additional_meta.update(task_meta_updates)
        self._update_task_state(additional_meta)

        return finished

    def cancel(
        self,
        *,
        reason: Optional[str] = None,
        log_message: Optional[str] = None,
        meta_updates: Optional[Dict[str, Any]] = None,
        events: Optional[List[Tuple[str, Dict[str, Any]]]] = None,
        job_updates: Optional[Dict[str, Any]] = None,
        job_event_payload: Optional[Dict[str, Any]] = None,
    ) -> datetime:
        finished = timezone.now()
        update_fields: List[str] = ["status", "finished_at", "error_message"]
        self.job.status = Job.Status.CANCELLED
        self.job.finished_at = finished
        self.job.error_message = reason or "Cancelled"
        if job_updates:
            for field, value in job_updates.items():
                setattr(self.job, field, value)
                if field not in update_fields:
                    update_fields.append(field)
        try:
            self.job.save(update_fields=update_fields)
        except Exception:
            pass

        _safe_job_log(
            self.case_id,
            self.org_id,
            self.job_id,
            log_message or "Job cancelled",
            level="WARNING",
        )
        _safe_job_meta(self.case_id, self.org_id, self.job_id, meta_updates)

        payload = job_event_payload or {}
        payload.setdefault("error", reason or "Cancelled")
        _emit_job_update(
            self.job_id,
            case_id=self.case_id,
            event="job.cancelled",
            status=Job.Status.CANCELLED,
            **payload,
        )
        for event_name, payload in events or []:
            _emit_job_update(
                self.job_id,
                case_id=self.case_id,
                event=event_name,
                status=Job.Status.CANCELLED,
                **payload,
            )

        self._update_task_state(
            {
                "status": Job.Status.CANCELLED,
                "finished_at": finished.isoformat(),
                "reason": reason or "cancelled",
            }
        )
        return finished

    def transition(
        self,
        *,
        status: Optional[str] = None,
        log_message: Optional[str] = None,
        meta_updates: Optional[Dict[str, Any]] = None,
        job_updates: Optional[Dict[str, Any]] = None,
        event: Optional[str] = None,
        job_event_payload: Optional[Dict[str, Any]] = None,
        task_meta_updates: Optional[Dict[str, Any]] = None,
    ) -> None:
        update_fields: List[str] = []
        if status:
            self.job.status = status
            update_fields.append("status")
        if job_updates:
            for field, value in job_updates.items():
                setattr(self.job, field, value)
                if field not in update_fields:
                    update_fields.append(field)
        if update_fields:
            try:
                self.job.save(update_fields=update_fields)
            except Exception:
                pass

        if log_message:
            _safe_job_log(self.case_id, self.org_id, self.job_id, log_message)
        _safe_job_meta(self.case_id, self.org_id, self.job_id, meta_updates)

        if event:
            payload = dict(job_event_payload or {})
            event_status = payload.pop("status", status)
            _emit_job_update(self.job_id, case_id=self.case_id, event=event, status=event_status, **payload)

        self._update_task_state(task_meta_updates)

    def emit(self, event: str, *, status: Optional[str] = None, **payload: Any) -> None:
        _emit_job_update(self.job_id, case_id=self.case_id, event=event, status=status, **payload)


__all__ = [
    "JobRuntimeContext",
    "_safe_job_meta",
    "_safe_job_log",
    "_emit_job_update",
]
