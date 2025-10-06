from __future__ import annotations

from typing import Any, Optional
from django.db.models import QuerySet as _DJQuerySet


class _Choice(str):
    value: str


class JobQuerySet(_DJQuerySet[Any]):
    def select_related(self, *args: Any, **kwargs: Any) -> JobQuerySet: ...
    def filter(self, *args: Any, **kwargs: Any) -> JobQuerySet: ...
    def all(self) -> JobQuerySet: ...
    def values_list(self, *args: Any, **kwargs: Any) -> JobQuerySet: ...
    def first(self) -> Optional["Job"]: ...
    def get(self, *args: Any, **kwargs: Any) -> "Job": ...
    def create(self, *args: Any, **kwargs: Any) -> "Job": ...
    def exists(self) -> bool: ...
    def update(self, *args: Any, **kwargs: Any) -> int: ...
    def distinct(self, *args: Any, **kwargs: Any) -> JobQuerySet: ...
    def none(self) -> JobQuerySet: ...


class JobManager(JobQuerySet):
    ...


class Job:
    # Core identifiers
    id: Any
    case_id: str
    organization_id: str

    # Django managers (treated as dynamic in stubs)
    objects: JobManager
    @classmethod
    def typed_objects(cls) -> JobManager: ...

    # Enum-like choices (TextChoices in implementation)
    class Status:
        def __new__(cls, *args: Any, **kwargs: Any) -> _Choice: ...
        def __init__(self, *args: Any, **kwargs: Any) -> None: ...
        PENDING: _Choice
        RUNNING: _Choice
        CONVERTING: _Choice
        UPLOADING: _Choice
        CANCELLING: _Choice
        SUCCEEDED: _Choice
        FAILED: _Choice
        CANCELLED: _Choice
        CORRUPTED: _Choice

    class Mode:
        BATCH: _Choice
        ON_DEMAND: _Choice

    class ReviewStatus:
        PENDING: _Choice
        APPROVED: _Choice
        REJECTED: _Choice

    # Commonly accessed fields
    status: str
    audio_input: str
    transcript_path: Optional[str]
    duration_s: Optional[float]
    display_title: str
    agent_type: str
    agent_label: str
    job_kind: str
    upload_progress: Optional[float]
    error_message: Optional[str]
    started_at: Optional[Any]
    finished_at: Optional[Any]

    # Relations
    case: Any
    organization: Any
    source_job: Optional["Job"]

    # Selected methods
    def save(self, *args: Any, **kwargs: Any) -> None: ...
    def refresh_from_db(self, *args: Any, **kwargs: Any) -> None: ...

    # Exceptions
    DoesNotExist: type[Exception]

__all__ = ["Job"]
