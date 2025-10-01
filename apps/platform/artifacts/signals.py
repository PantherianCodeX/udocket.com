from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.platform.artifacts.models import CaseArtifact
from apps.platform.operations.guardian import enqueue_guardian_review


@receiver(post_save, sender=CaseArtifact)
def _queue_guardian_review(sender, instance: CaseArtifact, created: bool, **_: object) -> None:
    if not created:
        return
    if not instance.path:
        return
    try:
        enqueue_guardian_review(int(instance.pk))
    except Exception:
        # Signal handlers must not raise; logging handled downstream
        pass
