from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.forms import UserCreationForm

from apps.platform.accounts.models import Organization, OrganizationMembership, User
from apps.platform.accounts.utils import sync_user_access_flags


class UserCreationWizardForm(UserCreationForm):
    organization = forms.ModelChoiceField(queryset=Organization.objects.all(), required=True)
    membership_role = forms.ChoiceField(choices=OrganizationMembership.Role.choices, required=True)
    display_name = forms.CharField(max_length=200, required=False)
    email = forms.EmailField(required=False)
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = Organization.objects.order_by("name")
        self.fields["username"].widget.attrs.setdefault("autocomplete", "new-username")
        if "password1" in self.fields:
            self.fields["password1"].widget.attrs.setdefault("autocomplete", "new-password")
        if "password2" in self.fields:
            self.fields["password2"].widget.attrs.setdefault("autocomplete", "new-password")

    def save(self, commit: bool = True):  # type: ignore[override]
        user = super().save(commit=False)
        organization = self.cleaned_data.get("organization")
        membership_role = self.cleaned_data.get("membership_role")
        display_name = self.cleaned_data.get("display_name") or None
        email = self.cleaned_data.get("email") or None
        user.display_name = display_name
        if email:
            user.email = email
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            self.save_m2m()
        if commit and organization and membership_role:
            OrganizationMembership.objects.get_or_create(
                organization=organization,
                user=user,
                defaults={"role": membership_role},
            )
            sync_user_access_flags(user)
        return user
