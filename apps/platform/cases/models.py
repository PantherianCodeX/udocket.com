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
    """Initial placeholder; full schema to follow in Step 4."""

    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=200)
    # Optional organization scoping (null during migration phase)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.PROTECT, related_name="cases"
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
