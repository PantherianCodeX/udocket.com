"""Typed helpers for job metadata storage and propagation."""

from __future__ import annotations

from .meta import JobRecordPatch, merge_job_meta

__all__ = [
    "JobRecordPatch",
    "merge_job_meta",
]
