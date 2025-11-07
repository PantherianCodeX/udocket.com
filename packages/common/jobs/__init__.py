from __future__ import annotations

"""Typed helpers for job metadata storage and propagation."""

from .meta import JobRecordPatch, merge_job_meta

__all__ = [
    "JobRecordPatch",
    "merge_job_meta",
]
