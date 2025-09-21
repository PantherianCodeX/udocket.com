from __future__ import annotations

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from apps.platform.accounts.admin import UserAdmin
from apps.platform.accounts.forms import UserCreationWizardForm
from apps.platform.accounts.models import Organization, User


def test_user_creation_wizard_form_creates_membership(db):
    org = Organization.objects.create(id="ORG-WIZ", name="Wizard Org")
    data = {
        "username": "wizard",
        "password1": "Supersafe123!",
        "password2": "Supersafe123!",
        "display_name": "Wizard User",
        "email": "wizard@example.com",
        "organization": org.pk,
        "membership_role": "ADMIN",
        "is_staff": True,
        "is_superuser": False,
    }
    form = UserCreationWizardForm(data)
    assert form.is_valid(), form.errors
    user = form.save()
    assert User.objects.filter(pk=user.pk).exists()
    assert user.org_memberships.filter(organization=org, role="ADMIN").exists()
    assert user.is_staff is True
    assert user.is_superuser is False


def test_user_admin_add_form_uses_wizard(db):
    org = Organization.objects.create(id="ORG-WIZ2", name="Wizard Org 2")
    site = AdminSite()
    admin = UserAdmin(User, site)
    request = RequestFactory().get("/admin/auth/user/add/")
    admin_user = User.objects.create_superuser(username="admin", password="x", email="admin@example.com")
    request.user = admin_user
    form = admin.get_form(request)
    assert issubclass(form, UserCreationWizardForm)
    form_instance = form(
        {
            "username": "wizard2",
            "password1": "Supersafe123!",
            "password2": "Supersafe123!",
            "organization": org.pk,
            "membership_role": "ADMIN",
        }
    )
    assert form_instance.is_valid(), form_instance.errors
    user = form_instance.save()
    assert User.objects.filter(pk=user.pk).exists()
    assert user.org_memberships.filter(organization=org, role="ADMIN").exists()
