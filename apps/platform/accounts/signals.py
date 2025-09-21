from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.platform.accounts.models import OrganizationMembership
from apps.platform.accounts.utils import sync_user_access_flags


@receiver(post_save, sender=OrganizationMembership)
def organization_membership_saved(sender, instance: OrganizationMembership, **kwargs) -> None:
    if instance.user_id:
        sync_user_access_flags(instance.user)


@receiver(post_delete, sender=OrganizationMembership)
def organization_membership_deleted(sender, instance: OrganizationMembership, **kwargs) -> None:
    if instance.user_id:
        sync_user_access_flags(instance.user)
