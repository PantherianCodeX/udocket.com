# pyright: strict

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any, cast

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from packages.common.django.typing import TypedManager, get_typed_manager

if TYPE_CHECKING:
    from apps.platform.accounts.models import Organization, User


class CaseQuerySet(models.QuerySet["Case"]):
    def for_user(self, user: Any) -> CaseQuerySet:
        from apps.platform import tenancy

        return tenancy.scope_cases(self, user)


class CaseManager(models.Manager["Case"]):
    def get_queryset(self) -> CaseQuerySet:
        return CaseQuerySet(self.model, using=self._db)

    def for_user(self, user: Any) -> CaseQuerySet:
        return self.get_queryset().for_user(user)


class Case(models.Model):
    objects = CaseManager()

    @classmethod
    def typed_objects(cls) -> CaseManager:
        manager = cls.objects
        if not isinstance(manager, CaseManager):  # pragma: no cover - defensive
            raise TypeError("Case.objects is not a CaseManager")
        return manager

    class ClientPosition(models.TextChoices):
        PLAINTIFF = "PLAINTIFF", "Plaintiff"
        DEFENDANT = "DEFENDANT", "Defendant"
        APPLICANT = "APPLICANT", "Applicant"
        RESPONDENT = "RESPONDENT", "Respondent"
        PROSECUTION = "PROSECUTION", "Prosecution"
        DEFENCE = "DEFENCE", "Defence"
        OTHER = "OTHER", "Other"

    class CourtLevel(models.TextChoices):
        PROVINCIAL = "PROVINCIAL", "Provincial"
        KINGS_BENCH = "KINGS_BENCH", "King's Bench"
        APPEAL = "APPEAL", "Court of Appeal"
        SUPREME = "SUPREME", "Supreme Court"
        FEDERAL = "FEDERAL", "Federal Court"
        OTHER = "OTHER", "Other"

    class CourtDivision(models.TextChoices):
        CIVIL = "CIVIL", "Civil"
        FAMILY = "FAMILY", "Family"
        CRIMINAL = "CRIMINAL", "Criminal"
        TRAFFIC = "TRAFFIC", "Traffic"
        IMMIGRATION = "IMMIGRATION", "Immigration"
        ADMINISTRATIVE = "ADMIN", "Administrative"
        OTHER = "OTHER", "Other"

    class Representation(models.TextChoices):
        SELF = "SELF", "Self-represented"
        LAWYER = "LAWYER", "Lawyer"
        PARALEGAL = "PARALEGAL", "Paralegal"
        ADVOCATE = "ADVOCATE", "Advocate / Representative"
        OTHER = "OTHER", "Other"

    id: models.CharField[str, str] = models.CharField(primary_key=True, max_length=36)
    title: models.CharField[str, str] = models.CharField(max_length=200)
    organization: models.ForeignKey[Organization, Organization] = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.PROTECT,
        related_name="cases",
    )
    client_name: models.CharField[str, str] = models.CharField(max_length=200, blank=True)
    opposing_party: models.CharField[str, str] = models.CharField(max_length=200, blank=True)
    client_position: models.CharField[str, str] = models.CharField(
        max_length=20,
        choices=ClientPosition.choices,
        blank=True,
    )
    court_location: models.CharField[str, str] = models.CharField(max_length=200, blank=True)
    court_level: models.CharField[str, str] = models.CharField(
        max_length=20,
        choices=CourtLevel.choices,
        blank=True,
    )
    court_division: models.CharField[str, str] = models.CharField(
        max_length=20,
        choices=CourtDivision.choices,
        blank=True,
    )
    court_case_number: models.CharField[str, str] = models.CharField(max_length=100, blank=True)
    representation: models.CharField[str, str] = models.CharField(
        max_length=20,
        choices=Representation.choices,
        blank=True,
    )
    legal_aid: models.BooleanField[bool, bool] = models.BooleanField(default=False)
    pro_bono: models.BooleanField[bool, bool] = models.BooleanField(default=False)
    court_date: models.DateTimeField[datetime | None, datetime | None] = models.DateTimeField(
        null=True,
        blank=True,
    )
    filing_deadline: models.DateField[date | None, date | None] = models.DateField(
        null=True,
        blank=True,
    )
    notes: models.TextField[str, str] = models.TextField(blank=True)
    reviewer: models.ForeignKey[User, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cases_reviewing",
    )
    client_user: models.ForeignKey[User, User | None] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cases_as_client",
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now=True)
    history: HistoricalRecords[Case] = HistoricalRecords()

    objects = CaseManager()

    @classmethod
    def scoped(cls) -> CaseManager:
        return cls.typed_objects()

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.id} — {self.title}"


class CaseMembership(models.Model):
    @classmethod
    def typed_objects(cls) -> TypedManager[CaseMembership]:
        return get_typed_manager(cls)

    @classmethod
    def scoped(cls) -> TypedManager[CaseMembership]:
        return cls.typed_objects()

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        CONTRIBUTOR = "CONTRIBUTOR", "Contributor"
        REVIEWER = "REVIEWER", "Reviewer"
        ADMIN = "ADMIN", "Admin"
        SUPERUSER = "SUPERUSER", "Superuser"
        AUDITOR = "AUDITOR", "Auditor"
        EXTERNAL = "EXTERNAL", "External"
        CLIENT = "CLIENT", "Client"

    case: models.ForeignKey[Case, Case] = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user: models.ForeignKey[User, User] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="case_memberships",
    )
    role: models.CharField[str, str] = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.CONTRIBUTOR,
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("case", "user")
        verbose_name = "Case membership"
        verbose_name_plural = "Case memberships"

    def __str__(self) -> str:  # pragma: no cover - trivial
        case_id = cast(str | None, getattr(self, "case_id", None))
        user_id = cast(int | None, getattr(self, "user_id", None))
        role = cast(str | None, getattr(self, "role", None))
        return f"{case_id}:{user_id}:{role}"
