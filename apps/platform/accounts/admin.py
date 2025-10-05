# pyright: strict

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Iterable, cast
from types import MethodType

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import QuerySet
from django.forms.models import BaseInlineFormSet, ModelChoiceField
from django.http import HttpRequest
from django.http.response import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import URLPattern, URLResolver, path, reverse
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

if TYPE_CHECKING:
    from django.contrib.admin import ModelAdmin as _ModelAdmin
    from django.contrib.admin import TabularInline as _TabularInline
    from django.contrib.auth.admin import UserAdmin as _UserAdmin

    OrganizationMembershipInlineBase = _TabularInline
    OrganizationMembershipUserInlineBase = _TabularInline
    CaseMembershipInlineBase = _TabularInline
    UserAdminBase = _UserAdmin
    OrganizationAdminBase = _ModelAdmin
    OrganizationMembershipAdminBase = _ModelAdmin
else:
    OrganizationMembershipInlineBase = admin.TabularInline
    OrganizationMembershipUserInlineBase = admin.TabularInline
    CaseMembershipInlineBase = admin.TabularInline
    UserAdminBase = DjangoUserAdmin
    OrganizationAdminBase = admin.ModelAdmin
    OrganizationMembershipAdminBase = admin.ModelAdmin


def _is_user_superuser(user: User) -> bool:
    return bool(getattr(user, "is_superuser", False))


class OrganizationMembershipInline(OrganizationMembershipInlineBase):
    model = OrganizationMembership
    extra = 1
    autocomplete_fields = ["organization"]


class OrganizationMembershipUserInline(OrganizationMembershipUserInlineBase):
    model = OrganizationMembership
    extra = 1
    autocomplete_fields = ["user"]


class CaseMembershipInline(CaseMembershipInlineBase):
    model = CaseMembership
    extra = 1
    autocomplete_fields = ["case"]


@admin.register(User)
class UserAdmin(UserAdminBase):
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
        memberships = list(
            OrganizationMembership.objects.select_related("organization").filter(user=obj)
        )
        if not memberships:
            return "—"
        labels: list[str] = []
        for membership in memberships[:3]:
            org_id = cast(str | None, getattr(membership, "organization_id", None))
            role_label = str(OrganizationMembership.Role(membership.role).label)
            label = f"{org_id}:{role_label}" if org_id else role_label
            labels.append(label)
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

            def _init(
                self: forms.ModelForm[User],
                *args: Any,
                **inner_kwargs: Any,
            ) -> None:
                base_form.__init__(self, *args, **inner_kwargs)
                raw_user = request.user
                user_instance = raw_user if isinstance(raw_user, User) else None
                if user_instance is not None:
                    org_qs = user_accessible_organizations(user_instance)
                    if not _is_user_superuser(user_instance):
                        field = self.fields.get("organization")
                        if isinstance(field, ModelChoiceField):
                            field.queryset = org_qs
                active_org_id = get_active_admin_org_id(request)
                if active_org_id and "organization" in self.fields:
                    self.fields["organization"].initial = active_org_id

            request_scoped_form = cast(
                type[forms.ModelForm[User]],
                type(
                    "RequestScopedUserCreationForm",
                    (base_form,),
                    {"__init__": _init},
                ),
            )

            kwargs["form"] = request_scoped_form
        else:
            kwargs["form"] = kwargs.get("form", self.form)
        return super().get_form(request, obj, change=change, **kwargs)

    def save_model(
        self,
        request: HttpRequest,
        obj: User,
        form: forms.ModelForm[User],
        change: bool,
    ) -> None:
        super().save_model(request, obj, form, change)
        sync_user_access_flags(obj)

    def save_formset(
        self,
        request: HttpRequest,
        form: forms.ModelForm[User] | None,
        formset: BaseInlineFormSet[Any, Any, forms.ModelForm[Any]],
        change: bool,
    ) -> None:
        instances = cast(Iterable[object], formset.save())
        for instance in instances:
            if isinstance(instance, OrganizationMembership):
                sync_user_access_flags(instance.user)
        for obj in getattr(formset, "deleted_objects", []):
            if isinstance(obj, OrganizationMembership):
                user = getattr(obj, "user", None)
                if user:
                    sync_user_access_flags(user)


@admin.register(Organization)
class OrganizationAdmin(OrganizationAdminBase):
    list_display = ("id", "name", "city", "province", "contact_email", "created_at")
    search_fields = ("id", "name", "display_name", "contact_email")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("id", "name", "display_name")}),
        (_("Contact"), {"fields": ("contact_name", "contact_email", "contact_phone")}),
        (_("Address"), {"fields": ("address_line1", "address_line2", "city", "province", "postal_code", "country")}),
        (_("Notes"), {"fields": ("notes",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )
    inlines = (OrganizationMembershipUserInline,)

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: Organization | None = None,
    ) -> list[str]:
        ro = list(super().get_readonly_fields(request, obj))
        if obj and "id" not in ro:
            ro.append("id")
        return ro


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(OrganizationMembershipAdminBase):
    list_display = ("organization", "user", "role", "created_at")
    list_filter = ("role", "organization")
    search_fields = ("organization__id", "organization__name", "user__username", "user__email")
    autocomplete_fields = ("organization", "user")

    def get_queryset(self, request: HttpRequest) -> QuerySet[OrganizationMembership]:
        qs = super().get_queryset(request)
        active_org_id = get_active_admin_org_id(request)
        if active_org_id:
            return qs.filter(organization_id=active_org_id)
        raw_user = request.user
        if isinstance(raw_user, User):
            user_instance = raw_user
        else:
            user_instance = None
        if user_instance is not None and _is_user_superuser(user_instance):
            return qs
        if user_instance is None:
            return qs.none()
        accessible_ids = user_accessible_organizations(user_instance).values_list("id", flat=True)
        return qs.filter(organization_id__in=accessible_ids)

    def get_form(
        self,
        request: HttpRequest,
        obj: OrganizationMembership | None = None,
        change: bool = False,
        **kwargs: Any,
    ) -> type[forms.ModelForm[OrganizationMembership]]:
        base_form = super().get_form(request, obj, change=change, **kwargs)
        raw_user = request.user
        if not isinstance(raw_user, User) or _is_user_superuser(raw_user):
            return base_form

        def _init(
            self: forms.ModelForm[OrganizationMembership],
            *args: Any,
            **inner_kwargs: Any,
        ) -> None:
            base_form.__init__(self, *args, **inner_kwargs)
            field = self.fields.get("organization")
            if isinstance(field, ModelChoiceField):
                field.queryset = user_accessible_organizations(raw_user)

        request_scoped_form = cast(
            type[forms.ModelForm[OrganizationMembership]],
            type(
                "RequestScopedMembershipForm",
                (base_form,),
                {"__init__": _init},
            ),
        )

        return request_scoped_form

UrlList = list[URLResolver | URLPattern]
_UrlGetter = Callable[[], Iterable[URLResolver | URLPattern]]
_EachContextCallable = Callable[[HttpRequest], dict[str, Any]]


@require_POST
def select_admin_organization(request: HttpRequest) -> HttpResponseRedirect:
    raw_user = request.user
    if isinstance(raw_user, User):
        user_instance = raw_user
    else:
        user_instance = None
    if user_instance is None or not user_instance.is_authenticated:
        return redirect("admin:login")
    next_url = (
        request.POST.get("next")
        or request.META.get("HTTP_REFERER")
        or reverse("admin:index")
    )
    choice = request.POST.get("organization")
    if choice == "__all__" and _is_user_superuser(user_instance):
        set_active_admin_org_id(request, None)
    else:
        org_qs = user_accessible_organizations(user_instance)
        if choice and org_qs.filter(id=choice).exists():
            set_active_admin_org_id(request, choice)
    return redirect(next_url)


_original_get_urls: _UrlGetter = admin.site.get_urls


def tenant_admin_urls(self: admin.AdminSite) -> UrlList:
    urls = list(_original_get_urls())
    custom: UrlList = [
        path(
            "select-organization/",
            self.admin_view(select_admin_organization),
            name="select_organization",
        ),
    ]
    return custom + urls


setattr(admin.site, "get_urls", MethodType(tenant_admin_urls, admin.site))


_original_each_context: _EachContextCallable = admin.site.each_context


def tenant_each_context(self: admin.AdminSite, request: HttpRequest) -> dict[str, Any]:
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


setattr(admin.site, "each_context", MethodType(tenant_each_context, admin.site))
