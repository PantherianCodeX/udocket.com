# pyright: strict

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from django.utils import timezone

from apps.platform.jobs.models import Job
from apps.platform.operations.channels import send_job_update
from apps.platform.operations.utils import append_job_log, update_job_meta


def _safe_job_meta(
    case_id: str,
    organization_id: str | None,
    job_id: str,
    updates: Mapping[str, object] | None,
) -> None:
    if not updates:
        return
    try:
        update_job_meta(case_id, organization_id, job_id, updates)
    except Exception:
        pass


def _safe_job_log(
    case_id: str,
    organization_id: str | None,
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
    status: str | None = None,
    payload: Mapping[str, object] | None = None,
) -> None:
    try:
        message = dict(payload or {})
        message.pop("case_id", None)
        message.pop("event", None)
        if status is not None:
            message["status"] = status
        message["case_id"] = case_id
        message["event"] = event
        send_job_update(job_id, **message)
    except Exception:
        pass


def safe_job_meta(
    case_id: str,
    organization_id: str | None,
    job_id: str,
    updates: Mapping[str, object] | None,
) -> None:
    """Public wrapper around ``_safe_job_meta`` for external modules."""

    _safe_job_meta(case_id, organization_id, job_id, updates)


def safe_job_log(
    case_id: str,
    organization_id: str | None,
    job_id: str,
    message: str,
    *,
    level: str = "INFO",
) -> None:
    """Public wrapper around ``_safe_job_log`` for external modules."""

    _safe_job_log(case_id, organization_id, job_id, message, level=level)


def emit_job_update(
    job_id: str,
    *,
    case_id: str,
    event: str,
    status: str | None = None,
    payload: Mapping[str, object] | None = None,
) -> None:
    """Public wrapper around ``_emit_job_update`` for external modules."""

    _emit_job_update(job_id, case_id=case_id, event=event, status=status, payload=payload)


def _resolve_status(payload: dict[str, object], fallback: str | None) -> str | None:
    raw_status = payload.pop("status", None)
    if isinstance(raw_status, str):
        return raw_status
    return fallback


def _empty_task_meta() -> dict[str, object]:
    return {}


@dataclass
class JobRuntimeContext:
    """Mutable context for running background jobs with consistent lifecycle hooks."""

    job: Job
    case_id: str
    org_id: str | None
    task_name: str | None = None
    task_id: str | None = None
    task_meta: dict[str, object] = field(default_factory=_empty_task_meta)
    _task_state: dict[str, object] = field(init=False, repr=False, default_factory=_empty_task_meta)

    def __post_init__(self) -> None:
        self._task_state = dict(self.task_meta)

    @property
    def job_id(self) -> str:
        return str(self.job.id)

    @property
    def task_state(self) -> dict[str, object]:
        """Read-only view of the runtime task state."""

        return dict(self._task_state)

    def _update_task_state(self, updates: Mapping[str, object] | None) -> None:
        if not updates:
            return
        self._task_state.update(dict(updates))

    def start(
        self,
        *,
        status: str,
        log_message: str | None = None,
        event: str | None = None,
        meta_updates: Mapping[str, object] | None = None,
        job_updates: Mapping[str, object] | None = None,
        started_at: datetime | None = None,
        job_event_payload: Mapping[str, object] | None = None,
    ) -> datetime:
        started = started_at or timezone.now()
        update_fields: list[str] = ["status", "started_at", "finished_at", "error_message"]
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
            payload = dict(job_event_payload or {})
            event_status = _resolve_status(payload, status)
            _emit_job_update(
                self.job_id,
                case_id=self.case_id,
                event=event,
                status=event_status,
                payload=payload,
            )
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
        log_message: str | None = None,
        meta_updates: Mapping[str, object] | None = None,
        events: Sequence[tuple[str, Mapping[str, object]]] | None = None,
        job_updates: Mapping[str, object] | None = None,
        task_meta_updates: Mapping[str, object] | None = None,
        job_event_payload: Mapping[str, object] | None = None,
    ) -> datetime:
        finished = timezone.now()
        update_fields: list[str] = ["status", "finished_at", "error_message"]
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

        payload = dict(job_event_payload or {})
        event_status = _resolve_status(payload, status)
        payload.pop("case_id", None)
        payload.pop("event", None)
        _emit_job_update(
            self.job_id,
            case_id=self.case_id,
            event="job.succeeded",
            status=event_status,
            payload=payload,
        )
        for event_name, event_payload in events or ():
            payload_with_status = dict(event_payload)
            event_status_override = _resolve_status(payload_with_status, status)
            payload_with_status.pop("case_id", None)
            payload_with_status.pop("event", None)
            _emit_job_update(
                self.job_id,
                case_id=self.case_id,
                event=event_name,
                status=event_status_override,
                payload=payload_with_status,
            )
        meta_payload: dict[str, object] = {
            "status": status,
            "finished_at": finished.isoformat(),
        }
        if task_meta_updates:
            for key, value in task_meta_updates.items():
                meta_payload[key] = value
        self._update_task_state(meta_payload)

        return finished

    def fail(
        self,
        *,
        error: str,
        status: str = Job.Status.FAILED,
        log_message: str | None = None,
        meta_updates: Mapping[str, object] | None = None,
        events: Sequence[tuple[str, Mapping[str, object]]] | None = None,
        job_updates: Mapping[str, object] | None = None,
        task_meta_updates: Mapping[str, object] | None = None,
        job_event_payload: Mapping[str, object] | None = None,
    ) -> datetime:
        finished = timezone.now()
        update_fields: list[str] = ["status", "finished_at", "error_message"]
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

        payload = dict(job_event_payload or {})
        payload.pop("case_id", None)
        payload.pop("event", None)
        payload.setdefault("error", error)
        event_status = _resolve_status(payload, status)
        _emit_job_update(
            self.job_id,
            case_id=self.case_id,
            event="job.failed",
            status=event_status,
            payload=payload,
        )
        for event_name, event_payload in events or ():
            payload_with_error = dict(event_payload)
            payload_with_error.pop("case_id", None)
            payload_with_error.pop("event", None)
            payload_with_error.setdefault("error", error)
            event_status_override = _resolve_status(payload_with_error, status)
            _emit_job_update(
                self.job_id,
                case_id=self.case_id,
                event=event_name,
                status=event_status_override,
                payload=payload_with_error,
            )

        additional_meta: dict[str, object] = {
            "status": status,
            "finished_at": finished.isoformat(),
            "error": error,
        }
        if task_meta_updates:
            for key, value in task_meta_updates.items():
                additional_meta[key] = value
        self._update_task_state(additional_meta)

        return finished

    def cancel(
        self,
        *,
        reason: str | None = None,
        log_message: str | None = None,
        meta_updates: Mapping[str, object] | None = None,
        events: Sequence[tuple[str, Mapping[str, object]]] | None = None,
        job_updates: Mapping[str, object] | None = None,
        job_event_payload: Mapping[str, object] | None = None,
    ) -> datetime:
        finished = timezone.now()
        update_fields: list[str] = ["status", "finished_at", "error_message"]
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

        payload = dict(job_event_payload or {})
        payload.setdefault("error", reason or "Cancelled")
        _emit_job_update(
            self.job_id,
            case_id=self.case_id,
            event="job.cancelled",
            status=Job.Status.CANCELLED,
            payload=payload,
        )
        for event_name, event_payload in events or ():
            _emit_job_update(
                self.job_id,
                case_id=self.case_id,
                event=event_name,
                status=Job.Status.CANCELLED,
                payload=event_payload,
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
        status: str | None = None,
        log_message: str | None = None,
        meta_updates: Mapping[str, object] | None = None,
        job_updates: Mapping[str, object] | None = None,
        event: str | None = None,
        job_event_payload: Mapping[str, object] | None = None,
        task_meta_updates: Mapping[str, object] | None = None,
    ) -> None:
        update_fields: list[str] = []
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
            event_status = _resolve_status(payload, status)
            _emit_job_update(
                self.job_id,
                case_id=self.case_id,
                event=event,
                status=event_status,
                payload=payload,
            )

        self._update_task_state(task_meta_updates)

    def emit(self, event: str, *, status: str | None = None, **payload: object) -> None:
        sanitized = dict(payload)
        sanitized.pop("case_id", None)
        sanitized.pop("event", None)
        _emit_job_update(
            self.job_id,
            case_id=self.case_id,
            event=event,
            status=status,
            payload=sanitized,
        )


__all__ = [
    "JobRuntimeContext",
    "safe_job_meta",
    "safe_job_log",
    "emit_job_update",
]
