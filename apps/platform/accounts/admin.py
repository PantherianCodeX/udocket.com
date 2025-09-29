from __future__ import annotations

from typing import Any, Iterable, cast, no_type_check

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db import models
from django.db.models import QuerySet
from django.db.models.manager import Manager
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import URLPattern, URLResolver, path, reverse
from django.forms import ModelChoiceField
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.platform.cases.models import CaseMembership

from .forms import UserCreationWizardForm
from .models import Organization, OrganizationMembership, User
from .utils import (
    admin_org_choices,
    get_active_admin_org,
    get_active_admin_org_id,
    set_active_admin_org_id,
    sync_user_access_flags,
    user_accessible_organizations,
)


class OrganizationMembershipInline(admin.TabularInline[OrganizationMembership, User]):
    model = OrganizationMembership
    extra = 1
    autocomplete_fields = ["organization"]


class OrganizationMembershipUserInline(admin.TabularInline[OrganizationMembership, Organization]):
    model = OrganizationMembership
    extra = 1
    autocomplete_fields = ["user"]


class CaseMembershipInline(admin.TabularInline[CaseMembership, User]):
    model = CaseMembership
    extra = 1
    autocomplete_fields = ["case"]


@admin.register(User)
class UserAdmin(DjangoUserAdmin[User]):
    list_display = ("username", "email", "display_name", "primary_membership_roles", "last_login")
    search_fields = ("username", "email", "display_name", "kc_sub")
    ordering = ("username",)
    list_filter = ("is_active",)
    add_form = UserCreationWizardForm
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2", "display_name", "email", "organization", "membership_role"),
        }),
    )
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("display_name", "first_name", "last_name", "email")}),
        (_("Tenant Profile"), {"fields": ("kc_sub",)}),
        (_("Status"), {"fields": ("is_active",)}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    readonly_fields = ("last_login", "date_joined")
    inlines = (OrganizationMembershipInline, CaseMembershipInline)

    @admin.display(description="Roles")
    def primary_membership_roles(self, obj: User) -> str:
        memberships_manager = cast(
            Manager[OrganizationMembership],
            getattr(obj, "org_memberships"),
        )
        memberships_qs: QuerySet[OrganizationMembership] = memberships_manager.all()
        memberships = list(memberships_qs.select_related("organization"))
        if not memberships:
            return "—"
        labels: list[str] = []
        for membership in memberships[:3]:
            role_value = cast(str, getattr(membership, "role"))
            labels.append(
                f"{membership.organization_id}:{OrganizationMembership.Role(role_value).label}"
            )
        more = len(memberships) - len(labels)
        if more > 0:
            labels.append(f"(+{more})")
        return ", ".join(labels)

    def get_form(
        self,
        request: HttpRequest,
        obj: User | None = None,
        change: bool = False,
        **kwargs: Any,
    ) -> type[forms.ModelForm[User]]:
        if obj is None:
            base_form: type[forms.ModelForm[User]] = self.add_form

            class RequestScopedUserCreationForm(base_form):
                def __init__(self, *args: Any, **inner_kwargs: Any) -> None:
                    super().__init__(*args, **inner_kwargs)
                    user = cast(User, request.user)
                    org_qs = user_accessible_organizations(user)
                    if not user.is_superuser:
                        org_field = self.fields.get("organization")
                        if isinstance(org_field, ModelChoiceField):
                            org_field.queryset = org_qs
                    active_org_id = get_active_admin_org_id(request)
                    if active_org_id:
                        org_field = self.fields.get("organization")
                        if isinstance(org_field, ModelChoiceField):
                            org_field.initial = active_org_id

            kwargs["form"] = RequestScopedUserCreationForm
        else:
            kwargs.setdefault("form", self.form)
        return super().get_form(request, obj, change=change, **kwargs)

    def save_model(self, request, obj, form, change):  # type: ignore[override]
        super().save_model(request, obj, form, change)
        sync_user_access_flags(obj)

    def save_formset(self, request, form, formset, change):  # type: ignore[override]
        instances: Iterable[Any] = formset.save()
        for instance in instances:
            if isinstance(instance, OrganizationMembership):
                sync_user_access_flags(instance.user)
        for obj in getattr(formset, "deleted_objects", []):
            if isinstance(obj, OrganizationMembership):
                user = getattr(obj, "user", None)
                if user:
                    sync_user_access_flags(user)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin[Organization]):
    list_display = ("id", "name", "city", "province", "contact_email", "created_at")
    search_fields = ("id", "name", "display_name", "contact_email")
    ordering = ("name",)
    readonly_fields = ("uid", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("id", "uid", "name", "display_name")}),
        (_("Contact"), {"fields": ("contact_name", "contact_email", "contact_phone")}),
        (_("Address"), {"fields": ("address_line1", "address_line2", "city", "province", "postal_code", "country")}),
        (_("Notes"), {"fields": ("notes",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )
    inlines = (OrganizationMembershipUserInline,)

    def get_readonly_fields(
        self, request: HttpRequest, obj: Organization | None = None
    ) -> tuple[str, ...]:
        ro = list(super().get_readonly_fields(request, obj))
        if obj and "id" not in ro:
            ro.append("id")
        return tuple(ro)


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin[OrganizationMembership]):
    list_display = ("organization", "user", "role", "created_at")
    list_filter = ("role", "organization")
    search_fields = ("organization__id", "organization__name", "user__username", "user__email")
    autocomplete_fields = ("organization", "user")

    def get_queryset(self, request: HttpRequest) -> QuerySet[OrganizationMembership]:  # type: ignore[override]
        qs: QuerySet[OrganizationMembership] = super().get_queryset(request)
        active_org_id = get_active_admin_org_id(request)
        if active_org_id:
            return qs.filter(organization_id=active_org_id)
        user = cast(User, request.user)
        if user.is_superuser:
            return qs
        accessible_ids = user_accessible_organizations(user).values_list("id", flat=True)
        return qs.filter(organization_id__in=accessible_ids)

    @no_type_check
    def formfield_for_foreignkey(
        self,
        db_field: models.ForeignKey[Organization, OrganizationMembership],
        request: HttpRequest,
        **kwargs: Any,
    ) -> ModelChoiceField[Any] | None:
        user = cast(User, request.user)
        if db_field.name == "organization" and not user.is_superuser:
            kwargs["queryset"] = user_accessible_organizations(user)
        field = cast(
            ModelChoiceField[Any] | None,
            super().formfield_for_foreignkey(db_field, request, **kwargs),
        )
        return field


@require_POST
def select_admin_organization(request: HttpRequest) -> HttpResponseRedirect:
    user = cast(User, request.user)
    if not user.is_authenticated:
        return redirect("admin:login")
    next_url = (
        request.POST.get("next")
        or request.META.get("HTTP_REFERER")
        or reverse("admin:index")
    )
    choice = request.POST.get("organization")
    if choice == "__all__" and user.is_superuser:
        set_active_admin_org_id(request, None)
    else:
        org_qs = user_accessible_organizations(user)
        if choice and org_qs.filter(id=choice).exists():
            set_active_admin_org_id(request, choice)
    return redirect(next_url)


_original_get_urls = admin.site.get_urls


def tenant_admin_urls() -> list[URLResolver | URLPattern]:
    urls = _original_get_urls()
    custom: list[URLResolver | URLPattern] = [
        path("select-organization/", admin.site.admin_view(select_admin_organization), name="select_organization"),
    ]
    return custom + urls


admin.site.get_urls = tenant_admin_urls  # type: ignore[assignment]


_original_each_context = admin.site.each_context


def tenant_each_context(request: HttpRequest) -> dict[str, Any]:
    ctx = _original_each_context(request)
    org_choices = admin_org_choices(request)
    active_org = get_active_admin_org(request)
    ctx.update(
        {
            "admin_org_choices": org_choices,
            "admin_active_org": active_org,
            "admin_active_org_id": active_org.id if active_org else None,
            "request": request,
        }
    )
    return ctx


admin.site.each_context = tenant_each_context  # type: ignore[assignment]
