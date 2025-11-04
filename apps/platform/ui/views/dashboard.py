from __future__ import annotations

# pyright: strict
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal, TypedDict
from urllib.parse import urlencode

from django.conf import settings
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.platform.accounts.utils import (
    resolve_request_organization,
    set_active_admin_org_id,
    user_accessible_organizations,
)
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.jobs.models import Job

Placement = Literal["full", "primary", "secondary"]

DEV_OPEN_DASHBOARD_PARAM = "demo"


@dataclass(frozen=True, slots=True)
class DashboardWidget:
    key: str
    title: str
    description: str
    template_name: str
    placement: Placement
    context: Mapping[str, object]


class ActiveOrganizationContext(TypedDict):
    id: str
    name: str


class CaseTableRow(TypedDict):
    id: str
    title: str
    client_name: str
    created_at: datetime
    job_total: int
    court_date: datetime | None
    filing_deadline: date | None


class DeadlineEntry(TypedDict):
    case_id: str
    case_title: str
    due_at: datetime
    kind: str


class JobStatusSummary(TypedDict):
    total: int
    running: int
    pending: int
    failed: int
    succeeded: int


class RecentJobEntry(TypedDict):
    id: str
    case_id: str
    case_title: str
    status: str
    agent_label: str
    created_at: datetime


class MetricEntry(TypedDict):
    label: str
    value: int
    hint: str


class LandingFeature(TypedDict):
    title: str
    description: str


class LandingPageContext(TypedDict):
    hero_title: str
    hero_subtitle: str
    features: tuple[LandingFeature, ...]
    login_url: str
    show_dashboard_link: bool
    dashboard_url: str


class CaseFormData(TypedDict):
    title: str
    client_name: str
    opposing_party: str
    client_position: str
    court_location: str
    court_level: str
    court_division: str
    court_case_number: str
    representation: str
    court_date: str
    filing_deadline: str
    notes: str
    legal_aid: bool
    pro_bono: bool


class DashboardPageContext(TypedDict):
    active_org: ActiveOrganizationContext | None
    widgets_full: tuple[DashboardWidget, ...]
    widgets_primary: tuple[DashboardWidget, ...]
    widgets_secondary: tuple[DashboardWidget, ...]
    case_form_data: CaseFormData
    case_form_error: str | None
    allow_case_creation: bool
    organization_count: int


def _initial_case_form_data() -> CaseFormData:
    return {
        "title": "",
        "client_name": "",
        "opposing_party": "",
        "client_position": "",
        "court_location": "",
        "court_level": "",
        "court_division": "",
        "court_case_number": "",
        "representation": "",
        "court_date": "",
        "filing_deadline": "",
        "notes": "",
        "legal_aid": False,
        "pro_bono": False,
    }


def _parse_local_datetime(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        naive = datetime.strptime(raw, "%Y-%m-%dT%H:%M")
    except ValueError:
        return None
    if timezone.is_aware(naive):
        return naive
    return timezone.make_aware(naive, timezone.get_current_timezone())


def _parse_local_date(raw: str) -> date | None:
    if not raw:
        return None
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None
    return parsed


def _collect_deadlines(cases: Sequence[Case]) -> list[DeadlineEntry]:
    entries: list[DeadlineEntry] = []
    now = timezone.now()
    window_end = now + timedelta(days=30)
    current_tz = timezone.get_current_timezone()
    for case in cases:
        if case.court_date and case.court_date >= now and case.court_date <= window_end:
            entries.append(
                {
                    "case_id": case.id,
                    "case_title": case.title or case.id,
                    "due_at": case.court_date,
                    "kind": "Court date",
                }
            )
        if case.filing_deadline:
            filing_dt = datetime.combine(case.filing_deadline, time.min)
            if not timezone.is_aware(filing_dt):
                filing_dt = timezone.make_aware(filing_dt, current_tz)
            if filing_dt >= now and filing_dt <= window_end:
                entries.append(
                    {
                        "case_id": case.id,
                        "case_title": case.title or case.id,
                        "due_at": filing_dt,
                        "kind": "Filing deadline",
                    }
                )
    entries.sort(key=lambda entry: entry["due_at"])
    return entries[:6]


def _build_case_rows(cases: Sequence[Case]) -> list[CaseTableRow]:
    rows: list[CaseTableRow] = []
    for case in cases:
        job_total_raw = getattr(case, "job_total", 0)
        job_total = (
            int(job_total_raw) if isinstance(job_total_raw, int) else int(job_total_raw or 0)
        )
        rows.append(
            {
                "id": case.id,
                "title": case.title or case.id,
                "client_name": case.client_name,
                "created_at": case.created_at,
                "job_total": job_total,
                "court_date": case.court_date,
                "filing_deadline": case.filing_deadline,
            }
        )
    return rows


def _job_status_summary_from_counts(counts: Mapping[str, int]) -> JobStatusSummary:
    running = sum(
        counts.get(status, 0)
        for status in (
            Job.Status.RUNNING,
            Job.Status.CONVERTING,
            Job.Status.UPLOADING,
        )
    )
    pending = counts.get(Job.Status.PENDING, 0)
    failed = sum(
        counts.get(status, 0)
        for status in (
            Job.Status.FAILED,
            Job.Status.CORRUPTED,
            Job.Status.CANCELLED,
        )
    )
    succeeded = counts.get(Job.Status.SUCCEEDED, 0)
    total = running + pending + failed + succeeded
    return {
        "total": total,
        "running": running,
        "pending": pending,
        "failed": failed,
        "succeeded": succeeded,
    }


def _recent_job_entries(jobs: Sequence[Job]) -> list[RecentJobEntry]:
    entries: list[RecentJobEntry] = []
    for job in jobs:
        case = getattr(job, "case", None)
        case_title = case.title if case else str(job.case_id)
        label = job.agent_label or job.job_kind or job.agent_type or "Job"
        entries.append(
            {
                "id": str(job.id),
                "case_id": str(job.case_id),
                "case_title": case_title,
                "status": job.status,
                "agent_label": label,
                "created_at": job.created_at,
            }
        )
    return entries


def _redirect_to_org_gate(request: HttpRequest) -> HttpResponseRedirect:
    destination = reverse("ui-organization-gate")
    next_param = request.get_full_path()
    if next_param:
        return HttpResponseRedirect(f"{destination}?{urlencode({'next': next_param})}")
    return HttpResponseRedirect(destination)


@require_http_methods(["GET", "POST"])
def index(request: HttpRequest) -> HttpResponse:
    user = getattr(request, "user", None)
    is_authenticated = bool(user and getattr(user, "is_authenticated", False))
    dev_open_enabled = bool(getattr(settings, "PLATFORM_DEV_OPEN", False))
    dev_open_requested = dev_open_enabled and request.GET.get(DEV_OPEN_DASHBOARD_PARAM) == "1"

    if not is_authenticated and not dev_open_requested:
        if request.method == "POST":
            return redirect("ui-login")

        features: tuple[LandingFeature, ...] = (
            {
                "title": "Build reliable transcripts",
                "description": "Secure, Canada-only speech services generate structured transcripts and audit trails for every job.",
            },
            {
                "title": "Stack layered analyses",
                "description": "Summaries, outlines, and timelines stay linked to source evidence so reviewers can trace conclusions quickly.",
            },
            {
                "title": "Deliver polished reports",
                "description": "Compose client-ready and lawyer-ready deliverables with provenance and version control baked in.",
            },
        )

        context: LandingPageContext = {
            "hero_title": "Case intelligence, orchestrated by uDocket agents",
            "hero_subtitle": "Transcribe hearings, analyze evidence, and publish deliverables with transparent workflows and reviewer controls.",
            "features": features,
            "login_url": reverse("ui-login"),
            "show_dashboard_link": dev_open_enabled,
            "dashboard_url": f"{reverse('ui-index')}?{DEV_OPEN_DASHBOARD_PARAM}=1",
        }
        return render(request, "platform_ui/pages/landing.html", context)

    accessible_orgs = list(user_accessible_organizations(user))
    organization = resolve_request_organization(request, required=False)

    if organization is None and len(accessible_orgs) == 1:
        single = accessible_orgs[0]
        set_active_admin_org_id(request, str(single.id))
        organization = single

    if organization is None and accessible_orgs:
        return _redirect_to_org_gate(request)

    cases_qs = Case.typed_objects().select_related("organization")
    cases_for_user = cases_qs.for_user(user).order_by("-created_at")
    if organization is not None:
        cases_for_user = cases_for_user.filter(organization=organization)
    else:
        cases_for_user = cases_for_user.none()

    jobs_qs = Job.typed_objects().for_user(user).order_by("-created_at")
    if organization is not None:
        jobs_qs = jobs_qs.filter(organization=organization)
    else:
        jobs_qs = jobs_qs.none()

    case_form_data = _initial_case_form_data()
    case_form_error: str | None = None

    if request.method == "POST":
        if organization is None:
            case_form_error = "Select an organization before creating cases."
        else:
            case_form_data.update(
                {
                    "title": (request.POST.get("title") or "").strip(),
                    "client_name": (request.POST.get("client_name") or "").strip(),
                    "opposing_party": (request.POST.get("opposing_party") or "").strip(),
                    "client_position": (request.POST.get("client_position") or "").strip(),
                    "court_location": (request.POST.get("court_location") or "").strip(),
                    "court_level": (request.POST.get("court_level") or "").strip(),
                    "court_division": (request.POST.get("court_division") or "").strip(),
                    "court_case_number": (request.POST.get("court_case_number") or "").strip(),
                    "representation": (request.POST.get("representation") or "").strip(),
                    "court_date": (request.POST.get("court_date") or "").strip(),
                    "filing_deadline": (request.POST.get("filing_deadline") or "").strip(),
                    "notes": (request.POST.get("notes") or "").strip(),
                    "legal_aid": bool(request.POST.get("legal_aid")),
                    "pro_bono": bool(request.POST.get("pro_bono")),
                }
            )

            court_date_value = _parse_local_datetime(case_form_data["court_date"])
            filing_deadline_value = _parse_local_date(case_form_data["filing_deadline"])

            new_case = Case.typed_objects().create(
                id=str(uuid.uuid4()),
                title=case_form_data["title"] or "Untitled case",
                organization=organization,
                client_name=case_form_data["client_name"],
                opposing_party=case_form_data["opposing_party"],
                client_position=case_form_data["client_position"],
                court_location=case_form_data["court_location"],
                court_level=case_form_data["court_level"],
                court_division=case_form_data["court_division"],
                court_case_number=case_form_data["court_case_number"],
                representation=case_form_data["representation"],
                legal_aid=case_form_data["legal_aid"],
                pro_bono=case_form_data["pro_bono"],
                court_date=court_date_value,
                filing_deadline=filing_deadline_value,
                notes=case_form_data["notes"],
            )

            if user and getattr(user, "is_authenticated", False):
                CaseMembership.objects.get_or_create(
                    case=new_case,
                    user=user,
                    defaults={"role": CaseMembership.Role.OWNER},
                )
            return redirect("ui-case-detail", case_id=new_case.id)

    annotated_cases = list(cases_for_user.annotate(job_total=Count("jobs")))
    case_rows = _build_case_rows(annotated_cases)
    deadlines = _collect_deadlines(annotated_cases)

    status_rows = jobs_qs.values("status").annotate(total=Count("id"))
    status_counts: dict[str, int] = {}
    for row in status_rows:
        status_value = row.get("status")
        total_value = row.get("total")
        if status_value is None:
            continue
        status_counts[str(status_value)] = int(total_value or 0)

    job_summary = _job_status_summary_from_counts(status_counts)

    recent_jobs_list = list(jobs_qs.select_related("case")[:6])
    recent_jobs = _recent_job_entries(recent_jobs_list[:4])

    metrics: list[MetricEntry] = [
        {
            "label": "Total cases",
            "value": len(case_rows),
            "hint": "Scoped to this organization",
        },
        {
            "label": "Active jobs",
            "value": job_summary["running"] + job_summary["pending"],
            "hint": "Running or awaiting execution",
        },
        {
            "label": "Upcoming deadlines",
            "value": len(deadlines),
            "hint": "Next 30 days",
        },
    ]

    active_org_context: ActiveOrganizationContext | None = None
    if organization is not None:
        active_org_context = {"id": str(organization.id), "name": organization.name}

    widgets: list[DashboardWidget] = [
        DashboardWidget(
            key="metrics",
            title="Organization overview",
            description="Key indicators for your automation workload",
            template_name="platform_ui/pages/dashboard/widgets/metrics.html",
            placement="full",
            context={"metrics": metrics, "active_org": active_org_context},
        ),
        DashboardWidget(
            key="cases",
            title="Case portfolio",
            description="Recently created cases and job totals",
            template_name="platform_ui/pages/dashboard/widgets/case_table.html",
            placement="primary",
            context={"rows": case_rows},
        ),
        DashboardWidget(
            key="recent_jobs",
            title="Latest automation runs",
            description="Most recent jobs across this organization",
            template_name="platform_ui/pages/dashboard/widgets/recent_jobs.html",
            placement="primary",
            context={"jobs": recent_jobs},
        ),
        DashboardWidget(
            key="job_status",
            title="Job status summary",
            description="Snapshot of active and completed jobs",
            template_name="platform_ui/pages/dashboard/widgets/job_status.html",
            placement="secondary",
            context={"summary": job_summary},
        ),
        DashboardWidget(
            key="deadlines",
            title="Upcoming deadlines",
            description="Court appearances and filing reminders",
            template_name="platform_ui/pages/dashboard/widgets/deadlines.html",
            placement="secondary",
            context={"deadlines": deadlines},
        ),
    ]

    allow_case_creation = organization is not None
    if allow_case_creation:
        widgets.append(
            DashboardWidget(
                key="create_case",
                title="Create a case",
                description="Capture intake details and start a new workspace",
                template_name="platform_ui/pages/dashboard/widgets/create_case.html",
                placement="secondary",
                context={
                    "data": case_form_data,
                    "error": case_form_error,
                    "client_position_choices": Case.ClientPosition.choices,
                    "court_level_choices": Case.CourtLevel.choices,
                    "court_division_choices": Case.CourtDivision.choices,
                    "representation_choices": Case.Representation.choices,
                },
            )
        )

    full_width = tuple(widget for widget in widgets if widget.placement == "full")
    primary = tuple(widget for widget in widgets if widget.placement == "primary")
    secondary = tuple(widget for widget in widgets if widget.placement == "secondary")

    context: DashboardPageContext = {
        "active_org": active_org_context,
        "widgets_full": full_width,
        "widgets_primary": primary,
        "widgets_secondary": secondary,
        "case_form_data": case_form_data,
        "case_form_error": case_form_error,
        "allow_case_creation": allow_case_creation,
        "organization_count": len(accessible_orgs),
    }
    return render(request, "platform_ui/dashboard/index.html", context)
