from django.db import models


class Case(models.Model):
    """Initial placeholder; full schema to follow in Step 4."""

    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.id} — {self.title}"

