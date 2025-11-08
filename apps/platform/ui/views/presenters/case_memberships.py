"""Helpers for presenting case membership assignments."""

from __future__ import annotations

from apps.platform.cases.models import Case, CaseMembership

from ..presenters.utils import user_label


def case_owner_memberships(memberships: list[CaseMembership]) -> list[CaseMembership]:
    """Return owner memberships with users attached."""

    return [
        membership
        for membership in memberships
        if membership.role == CaseMembership.Role.OWNER and membership.user
    ]


def case_owner_labels(memberships: list[CaseMembership]) -> list[str]:
    return [
        user_label(membership.user)
        for membership in case_owner_memberships(memberships)
        if membership.user
    ]


def case_owner_details(memberships: list[CaseMembership]) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    for membership in case_owner_memberships(memberships):
        user = membership.user
        if not user:
            continue
        details.append(
            {
                "label": user_label(user),
                "username": getattr(user, "username", ""),
            }
        )
    return details


def case_assignment_lists(
    case: Case, memberships: list[CaseMembership] | None = None
) -> dict[str, list[dict[str, str]]]:
    memberships = memberships or list(case.memberships.select_related("user"))
    reviewers: list[dict[str, str]] = []
    clients: list[dict[str, str]] = []
    owners: list[dict[str, str]] = []
    for membership in memberships:
        user = membership.user
        if not user:
            continue
        entry = {"id": str(user.id), "label": user_label(user)}
        if membership.role == CaseMembership.Role.REVIEWER:
            reviewers.append(entry)
        elif membership.role == CaseMembership.Role.CLIENT:
            clients.append(entry)
        elif membership.role == CaseMembership.Role.OWNER:
            owners.append(entry)
    return {
        "reviewer_candidates": reviewers,
        "client_candidates": clients,
        "owner_candidates": owners,
    }


__all__ = [
    "case_owner_memberships",
    "case_owner_labels",
    "case_owner_details",
    "case_assignment_lists",
]
