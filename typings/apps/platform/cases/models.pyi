from __future__ import annotations

from typing import Any, Optional
from django.db.models import QuerySet as _DJQuerySet


class CaseQuerySet(_DJQuerySet[Any]):
    def select_related(self, *args: Any, **kwargs: Any) -> CaseQuerySet: ...
    def filter(self, *args: Any, **kwargs: Any) -> CaseQuerySet: ...
    def all(self) -> CaseQuerySet: ...
    def values_list(self, *args: Any, **kwargs: Any) -> CaseQuerySet: ...
    def first(self) -> Optional["Case"]: ...
    def get(self, *args: Any, **kwargs: Any) -> "Case": ...
    def exists(self) -> bool: ...
    def update(self, *args: Any, **kwargs: Any) -> int: ...
    def distinct(self, *args: Any, **kwargs: Any) -> CaseQuerySet: ...
    def none(self) -> CaseQuerySet: ...


class CaseManager(CaseQuerySet):
    ...


class Case:
    id: str
    organization_id: str
    reviewer_id: Optional[int]

    # Managers
    objects: CaseManager
    @classmethod
    def typed_objects(cls) -> CaseManager: ...

    # Enums (TextChoices in implementation) — names only used in UI
    class ClientPosition:
        PLAINTIFF: Any
        DEFENDANT: Any
        APPLICANT: Any
        RESPONDENT: Any
        PROSECUTION: Any
        DEFENCE: Any
        OTHER: Any

    class CourtLevel:
        PROVINCIAL: Any
        KINGS_BENCH: Any
        APPEAL: Any
        SUPREME: Any
        FEDERAL: Any
        OTHER: Any

    class CourtDivision:
        CIVIL: Any
        FAMILY: Any
        CRIMINAL: Any
        TRAFFIC: Any
        IMMIGRATION: Any
        ADMINISTRATIVE: Any
        OTHER: Any

    class Representation:
        SELF: Any
        LAWYER: Any
        PARALEGAL: Any
        ADVOCATE: Any
        OTHER: Any

    # Relations
    memberships: Any  # reverse FK manager


class CaseMembershipQuerySet(_DJQuerySet[Any]):
    def filter(self, *args: Any, **kwargs: Any) -> CaseMembershipQuerySet: ...
    def exists(self) -> bool: ...
    def values_list(self, *args: Any, **kwargs: Any) -> CaseMembershipQuerySet: ...
    def distinct(self, *args: Any, **kwargs: Any) -> CaseMembershipQuerySet: ...
    def none(self) -> CaseMembershipQuerySet: ...
    

class CaseMembershipManager(CaseMembershipQuerySet):
    ...


class CaseMembership:
    case_id: str
    user_id: int

    # Managers
    objects: CaseMembershipManager
    @classmethod
    def typed_objects(cls) -> CaseMembershipManager: ...

__all__ = ["Case", "CaseMembership"]
