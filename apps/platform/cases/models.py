from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from simple_history.models import HistoricalRecords


class CaseQuerySet(models.QuerySet):
    def for_user(self, user):
        from apps.platform import tenancy

        return tenancy.scope_cases(self, user)


CaseManager = CaseQuerySet.as_manager()


class Case(models.Model):
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

    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=200)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.PROTECT, related_name="cases"
    )
    client_name = models.CharField(max_length=200, blank=True)
    opposing_party = models.CharField(max_length=200, blank=True)
    client_position = models.CharField(max_length=20, choices=ClientPosition.choices, blank=True)
    court_location = models.CharField(max_length=200, blank=True)
    court_level = models.CharField(max_length=20, choices=CourtLevel.choices, blank=True)
    court_division = models.CharField(max_length=20, choices=CourtDivision.choices, blank=True)
    court_case_number = models.CharField(max_length=100, blank=True)
    representation = models.CharField(max_length=20, choices=Representation.choices, blank=True)
    legal_aid = models.BooleanField(default=False)
    pro_bono = models.BooleanField(default=False)
    court_date = models.DateTimeField(null=True, blank=True)
    filing_deadline = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cases_reviewing",
    )
    client_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cases_as_client",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    objects = CaseManager

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.id} — {self.title}"


class CaseMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        CONTRIBUTOR = "CONTRIBUTOR", "Contributor"
        REVIEWER = "REVIEWER", "Reviewer"
        ADMIN = "ADMIN", "Admin"
        SUPERUSER = "SUPERUSER", "Superuser"
        AUDITOR = "AUDITOR", "Auditor"
        EXTERNAL = "EXTERNAL", "External"
        CLIENT = "CLIENT", "Client"

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="case_memberships")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.CONTRIBUTOR)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("case", "user")
        verbose_name = "Case membership"
        verbose_name_plural = "Case memberships"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.case_id}:{self.user_id}:{self.role}"
