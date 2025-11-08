from __future__ import annotations

from collections.abc import Iterable

# pyright: strict
from dataclasses import dataclass

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.db.models.functions import Coalesce
from django.http import HttpRequest

from apps.platform.jobs.models import Job


@dataclass
class JobTableState:
    rows: list[Job]
    filters: list[dict[str, object]]
    pagination: dict[str, object]
    limit_choices: tuple[int, ...]
    page_size: int
    param_prefix: str
    param_names: list[str]
    active_filters: int
    has_advanced_filters: bool

    @property
    def filters_active(self) -> int:
        return self.active_filters


def _unique_select_options(pairs: Iterable[tuple[object, object]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    results: list[dict[str, str]] = []
    for raw_value, raw_label in pairs:
        value = str(raw_value)
        if value in seen:
            continue
        seen.add(value)
        label = str(raw_label) if raw_label is not None else value
        results.append({"value": value, "label": label})
    return results


def _limit_choices() -> tuple[int, ...]:
    values = getattr(settings, "PLATFORM_UI_JOB_LIMIT_CHOICES", (25, 50, 100, 200))
    cleaned = sorted({int(v) for v in values if int(v) > 0})
    return tuple(cleaned or (25, 50, 100, 200))


def _default_page_size(choices: tuple[int, ...]) -> int:
    default_value = getattr(settings, "PLATFORM_UI_JOB_DEFAULT_LIMIT", choices[0])
    if default_value in choices:
        return default_value
    for value in choices:
        if default_value <= value:
            return value
    return choices[-1]


def _clean_multi(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for raw in values:
        if not raw:
            continue
        value = str(raw).strip()
        if value:
            result.append(value)
    return result


def _parse_date(value: str | None):
    if not value:
        return None
    from datetime import datetime

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _status_options() -> list[dict[str, str]]:
    return _unique_select_options(Job.Status.choices)


def _review_options() -> list[dict[str, str]]:
    return _unique_select_options(Job.ReviewStatus.choices)


def _distinct_strings(qs: QuerySet[Job], field: str, limit: int = 75) -> list[str]:
    values = (
        qs.exclude(**{f"{field}__isnull": True})
        .exclude(**{field: ""})
        .values_list(field, flat=True)
        .distinct()[:limit]
    )
    seen: set[str] = set()
    unique: list[str] = []
    for raw in values:
        value = str(raw)
        if not value.strip():
            continue
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def build_job_table_state(
    request: HttpRequest,
    queryset: QuerySet[Job],
    *,
    prefix: str,
    include_case_filters: bool = False,
) -> JobTableState:
    limit_options = _limit_choices()
    default_page_size = _default_page_size(limit_options)
    page_size_param = f"{prefix}_page_size"
    try:
        page_size = int(request.GET.get(page_size_param, default_page_size))
    except (TypeError, ValueError):
        page_size = default_page_size
    if page_size not in limit_options:
        for option in limit_options:
            if page_size <= option:
                page_size = option
                break
        else:
            page_size = limit_options[-1]

    page_param = f"{prefix}_page"
    try:
        page_number = int(request.GET.get(page_param, "1"))
    except (TypeError, ValueError):
        page_number = 1
    page_number = max(page_number, 1)

    search_param = f"{prefix}_search"
    search_value = (request.GET.get(search_param) or "").strip()

    status_param = f"{prefix}_status"
    status_values = {value.upper() for value in _clean_multi(request.GET.getlist(status_param))}

    review_param = f"{prefix}_review"
    review_values = {value.upper() for value in _clean_multi(request.GET.getlist(review_param))}

    agent_param = f"{prefix}_agent"
    agent_values = {_normalize(value) for value in _clean_multi(request.GET.getlist(agent_param))}

    kind_param = f"{prefix}_kind"
    kind_values = {_normalize(value) for value in _clean_multi(request.GET.getlist(kind_param))}

    case_param = f"{prefix}_case"
    case_values = (
        set(_clean_multi(request.GET.getlist(case_param))) if include_case_filters else set()
    )

    created_after_param = f"{prefix}_created_after"
    created_before_param = f"{prefix}_created_before"
    modified_after_param = f"{prefix}_modified_after"
    modified_before_param = f"{prefix}_modified_before"

    created_after = _parse_date(request.GET.get(created_after_param))
    created_before = _parse_date(request.GET.get(created_before_param))
    modified_after = _parse_date(request.GET.get(modified_after_param))
    modified_before = _parse_date(request.GET.get(modified_before_param))

    qs = queryset.annotate(last_activity=Coalesce("finished_at", "started_at", "created_at"))

    if status_values:
        qs = qs.filter(status__in=status_values)
    if review_values:
        qs = qs.filter(review_status__in=review_values)
    if agent_values:
        qs = qs.filter(agent_type__in=[value for value in agent_values if value])
    if kind_values:
        qs = qs.filter(job_kind__in=[value for value in kind_values if value])
    if include_case_filters and case_values:
        qs = qs.filter(case_id__in=case_values)
    if created_after:
        qs = qs.filter(created_at__date__gte=created_after)
    if created_before:
        qs = qs.filter(created_at__date__lte=created_before)
    if modified_after:
        qs = qs.filter(last_activity__date__gte=modified_after)
    if modified_before:
        qs = qs.filter(last_activity__date__lte=modified_before)

    if search_value:
        search_filter = Q(display_title__icontains=search_value) | Q(
            agent_label__icontains=search_value
        )
        search_filter |= Q(agent_type__icontains=search_value) | Q(job_kind__icontains=search_value)
        search_filter |= Q(id__icontains=search_value)
        if include_case_filters:
            search_filter |= Q(case__title__icontains=search_value)
        qs = qs.filter(search_filter)

    qs = qs.order_by("-created_at")

    paginator = Paginator(qs, page_size)
    page = paginator.get_page(page_number)
    rows = list(page.object_list)

    pagination = {
        "page": page.number,
        "pages": paginator.num_pages or 1,
        "page_size": page_size,
        "total": paginator.count,
        "start": page.start_index() if paginator.count else 0,
        "end": page.end_index() if paginator.count else 0,
        "has_previous": page.has_previous(),
        "has_next": page.has_next(),
        "previous_page": page.previous_page_number() if page.has_previous() else 1,
        "next_page": page.next_page_number() if page.has_next() else paginator.num_pages or 1,
        "display_count": len(rows),
        "first_page": 1,
        "last_page": paginator.num_pages or 1,
    }

    def _selected_labels(options: list[dict[str, str]], selections: Iterable[str]) -> list[str]:
        label_map = {option["value"]: option["label"] for option in options}
        labels: list[str] = []
        for value in selections:
            label = label_map.get(value)
            if label:
                labels.append(label)
        return labels

    filters: list[dict[str, object]] = [
        {
            "id": "search",
            "type": "search",
            "param": search_param,
            "placeholder": "Search jobs",
            "value": search_value,
        }
    ]

    status_options = _status_options()
    status_selected = sorted(status_values)
    filters.append(
        {
            "id": "status",
            "type": "select",
            "label": "Status",
            "param": status_param,
            "options": status_options,
            "multiple": True,
            "value": status_selected,
            "selected": _selected_labels(status_options, status_selected),
        }
    )

    review_options = _review_options()
    review_selected = sorted(review_values)
    filters.append(
        {
            "id": "review",
            "type": "select",
            "label": "Review",
            "param": review_param,
            "options": review_options,
            "multiple": True,
            "value": review_selected,
            "selected": _selected_labels(review_options, review_selected),
        }
    )

    agent_strings = sorted(_distinct_strings(queryset, "agent_type"))
    if agent_strings:
        agent_options = [
            {"value": value, "label": value.replace("_", " ").title()} for value in agent_strings
        ]
        agent_options.sort(key=lambda item: item["label"].lower())
        agent_selected = sorted(agent_values)
        filters.append(
            {
                "id": "agent",
                "type": "select",
                "label": "Agent",
                "param": agent_param,
                "options": agent_options,
                "multiple": True,
                "value": agent_selected,
                "selected": _selected_labels(agent_options, agent_selected),
            }
        )

    kind_strings = sorted(_distinct_strings(queryset, "job_kind"))
    if kind_strings:
        kind_options = [
            {"value": value, "label": value.replace("_", " ").title()} for value in kind_strings
        ]
        kind_options.sort(key=lambda item: item["label"].lower())
        kind_selected = sorted(kind_values)
        filters.append(
            {
                "id": "kind",
                "type": "select",
                "label": "Job Kind",
                "param": kind_param,
                "options": kind_options,
                "multiple": True,
                "value": kind_selected,
                "selected": _selected_labels(kind_options, kind_selected),
            }
        )

    if include_case_filters:
        case_pairs = (
            queryset.select_related("case").values_list("case_id", "case__title").distinct()
        )
        case_options = _unique_select_options(
            (str(case_id), case_title or str(case_id)) for case_id, case_title in case_pairs
        )
        case_options.sort(key=lambda item: item["label"].lower())
        if case_options:
            case_selected = sorted(case_values)
            filters.append(
                {
                    "id": "case",
                    "type": "select",
                    "label": "Case",
                    "param": case_param,
                    "options": case_options,
                    "multiple": True,
                    "value": case_selected,
                    "selected": _selected_labels(case_options, case_selected),
                }
            )

    filters.append(
        {
            "id": "created",
            "type": "daterange",
            "label": "Created",
            "start_param": created_after_param,
            "end_param": created_before_param,
            "start_value": request.GET.get(created_after_param, ""),
            "end_value": request.GET.get(created_before_param, ""),
            "selected": [],
        }
    )

    filters.append(
        {
            "id": "modified",
            "type": "daterange",
            "label": "Last Activity",
            "start_param": modified_after_param,
            "end_param": modified_before_param,
            "start_value": request.GET.get(modified_after_param, ""),
            "end_value": request.GET.get(modified_before_param, ""),
            "selected": [],
        }
    )

    param_names = [
        search_param,
        status_param,
        review_param,
        agent_param,
        kind_param,
        created_after_param,
        created_before_param,
        modified_after_param,
        modified_before_param,
        page_param,
        page_size_param,
    ]
    if include_case_filters:
        param_names.append(case_param)

    active_filters = 0
    advanced_filters = False
    for filter_payload in filters:
        values = filter_payload.get("value")
        if isinstance(values, (list, tuple, set)):
            active_filters += len([value for value in values if value])
        elif values:
            active_filters += 1
        if filter_payload.get("type") != "search":
            advanced_filters = True

    return JobTableState(
        rows=rows,
        filters=filters,
        pagination=pagination,
        limit_choices=limit_options,
        page_size=page_size,
        param_prefix=prefix,
        param_names=param_names,
        active_filters=active_filters,
        has_advanced_filters=advanced_filters,
    )


def _normalize(value: str | None) -> str:
    return value.strip().lower() if isinstance(value, str) else ""
