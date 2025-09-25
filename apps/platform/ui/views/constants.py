from __future__ import annotations

from typing import Any, Dict, Tuple

STATUS_CLASS_MAP: Dict[str, str] = {
    "Approved": "border-emerald-400/40 bg-emerald-500/10 text-emerald-200",
    "Created": "border-white/20 bg-white/5 text-slate-200",
    "Converting": "border-primary-400/40 bg-primary-500/10 text-primary-200",
    "Running": "border-primary-400/40 bg-primary-500/10 text-primary-200",
    "Uploading": "border-primary-400/40 bg-primary-500/10 text-primary-200",
    "Rejected": "border-rose-400/40 bg-rose-500/10 text-rose-200",
    "Cancelling": "border-slate-400/40 bg-slate-500/20 text-slate-200",
    "Ready": "border-emerald-400/40 bg-emerald-500/10 text-emerald-200",
    "Not Started": "border-white/20 bg-white/5 text-slate-200",
    "No Transcript": "border-amber-400/40 bg-amber-500/10 text-amber-100",
    "Corrupted": "border-rose-400/40 bg-rose-500/15 text-rose-200",
}

STATUS_PILL_STYLES: Dict[str, str] = {
    "SUCCEEDED": "border-emerald-400/40 bg-emerald-500/10 text-emerald-200",
    "READY": "border-emerald-400/40 bg-emerald-500/10 text-emerald-200",
    "FAILED": "border-rose-400/40 bg-rose-500/10 text-rose-200",
    "CORRUPTED": "border-rose-400/40 bg-rose-500/10 text-rose-200",
    "ERROR": "border-rose-400/40 bg-rose-500/10 text-rose-200",
    "CANCELLED": "border-slate-400/40 bg-slate-500/20 text-slate-200",
    "CANCELLING": "border-slate-400/40 bg-slate-500/20 text-slate-200",
    "PENDING": "border-primary-400/40 bg-primary-500/10 text-primary-100",
    "RUNNING": "border-primary-400/40 bg-primary-500/10 text-primary-100",
    "CONVERTING": "border-primary-400/40 bg-primary-500/10 text-primary-100",
    "UPLOADING": "border-primary-400/40 bg-primary-500/10 text-primary-100",
    "QUEUED": "border-amber-400/40 bg-amber-500/10 text-amber-100",
}

CANCELABLE_STATUSES = {"RUNNING", "PENDING", "QUEUED", "UPLOADING", "CANCELLING", "CONVERTING"}

RESTARTABLE_STATUSES = {"SUCCEEDED", "FAILED", "CANCELLED", "CORRUPTED"}

STATUS_SORT_ORDER: Dict[str, int] = {
    "UPLOADING": 10,
    "QUEUED": 20,
    "PENDING": 30,
    "CONVERTING": 40,
    "RUNNING": 50,
    "CANCELLING": 60,
    "SUCCEEDED": 80,
    "READY": 85,
    "FAILED": 90,
    "CANCELLED": 95,
    "CORRUPTED": 100,
    "ERROR": 110,
}

DEFAULT_TABLE_FILTERS = (
    {
        "type": "search",
        "id": "query",
        "placeholder": "Filter jobs",
    },
)

CASE_JOB_TABLE_COLUMNS: Tuple[Dict[str, Any], ...] = (
    {"id": "title", "label": "Title", "sortable": True, "sort_key": "title"},
    {"id": "status", "label": "Status", "sortable": True, "sort_key": "status"},
    {"id": "review", "label": "Approval", "sortable": True, "sort_key": "review"},
    {"id": "agent", "label": "Agent", "sortable": True, "sort_key": "agent"},
    {
        "id": "created",
        "label": "Created",
        "sortable": True,
        "sort_key": "created",
        "align": "right",
        "default_direction": "desc",
    },
    {"id": "notes", "label": "Notes", "sortable": False, "align": "center", "hide_on_mobile": True},
    {"id": "actions", "label": "Actions", "sortable": False, "align": "right"},
    {"id": "expander", "label": "", "sortable": False, "align": "right"},
)

GLOBAL_JOB_TABLE_COLUMNS: Tuple[Dict[str, Any], ...] = (
    {"id": "title", "label": "Job", "sortable": True, "sort_key": "title"},
    {"id": "status", "label": "Status", "sortable": True, "sort_key": "status"},
    {"id": "type", "label": "Type", "sortable": True, "sort_key": "type"},
    {"id": "agent", "label": "Agent", "sortable": True, "sort_key": "agent"},
    {
        "id": "created",
        "label": "Created",
        "sortable": True,
        "sort_key": "created",
        "align": "right",
        "default_direction": "desc",
    },
    {"id": "notes", "label": "Notes", "sortable": False, "align": "center", "hide_on_mobile": True},
    {"id": "actions", "label": "Actions", "sortable": False, "align": "right"},
    {"id": "expander", "label": "", "sortable": False, "align": "right"},
)
