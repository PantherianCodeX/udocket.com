# Dashboard Widgets Overview

The platform dashboard (`apps/platform/ui/views/dashboard.py`) now renders a sequence of widgets that can be
rearranged or extended per organization. This document captures the layout contract so future template overrides
and customization tooling can build on the current implementation.

## Layout anatomy

- **Full width widgets** render across the page before the two-column grid. The default build only includes the
  metrics summary widget.
- **Primary column widgets** live in the left column (`3fr` in the grid) and focus on case lists and recent
  activity.
- **Secondary column widgets** live in the right column (`2fr`) and focus on snapshots, actions, and reminders.

The layout is driven entirely by the `DashboardWidget` dataclass. Each widget defines a `template_name`,
`placement`, and `context`. The view groups widgets into three lists (`widgets_full`, `widgets_primary`,
`widgets_secondary`) that the template iterates over.

## Default widgets

| Key | Placement | Template path | Purpose |
| --- | --- | --- | --- |
| `metrics` | `full` | `platform_ui/pages/dashboard/widgets/metrics.html` | High-level counts for cases, jobs, and deadlines. |
| `cases` | `primary` | `platform_ui/pages/dashboard/widgets/case_table.html` | Tabular list of recently created cases with quick links. |
| `recent_jobs` | `primary` | `platform_ui/pages/dashboard/widgets/recent_jobs.html` | Highlights the latest automation runs with status pills. |
| `job_status` | `secondary`| `platform_ui/pages/dashboard/widgets/job_status.html` | Aggregated job counts across statuses. |
| `deadlines` | `secondary`| `platform_ui/pages/dashboard/widgets/deadlines.html` | Upcoming court dates and filing deadlines. |
| `create_case` | `secondary`| `platform_ui/pages/dashboard/widgets/create_case.html` | Lightweight case intake form; only rendered when the user has an active organization. |

Each template receives a `widget` variable with the dataclass instance, so custom widgets can re-use the same
pattern.

## Customization hooks

- **Per-organization overrides**: drop-in templates can replace the default widget templates by pointing a new
  `DashboardWidget` at an alternate `template_name`. Future work will load overrides from organization settings.
- **Additional widgets**: create a new `DashboardWidget` in `index()` and append it to one of the placement lists.
  The root template automatically renders whatever is supplied.
- **Data sources**: use typed helper functions in `dashboard.py` (`_collect_deadlines`, `_recent_job_entries`, etc.)
  as examples for structuring widget context. Keep helper output strongly typed for Pyright/mypy.

## Organization selection

The dashboard assumes an active organization. The login flow now redirects users to `/org/choose/` when they have
multiple memberships. Single-organization users are auto-selected. The selection view writes the organization
identifier to the session via `set_active_admin_org_id`, which the dashboard then reads via
`resolve_request_organization`.

## Adding new widgets safely

1. Add a helper that collects the data you need. Avoid per-row queries; annotate querysets with counts when possible.
2. Create a template under `platform_ui/pages/dashboard/widgets/` and keep styling consistent with the existing
   Tailwind utility patterns.
3. Instantiate a new `DashboardWidget` in `index()` with the helper output.
4. Decide which placement list to append to (`full`, `primary`, or `secondary`).
5. Update documentation and consider whether the widget should be feature-flagged per organization.

By keeping widgets declarative and typed, the dashboard can grow into a fully customizable workspace with minimal
risk to existing flows.
