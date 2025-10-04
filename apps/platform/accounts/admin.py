from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.urls import path, reverse
from django.shortcuts import redirect
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


class OrganizationMembershipInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 1
    autocomplete_fields = ["organization"]


class OrganizationMembershipUserInline(admin.TabularInline):
    model = OrganizationMembership
    extra = 1
    autocomplete_fields = ["user"]


class CaseMembershipInline(admin.TabularInline):
    model = CaseMembership
    extra = 1
    autocomplete_fields = ["case"]


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
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
    inlines = [OrganizationMembershipInline, CaseMembershipInline]

    @admin.display(description="Roles")
    def primary_membership_roles(self, obj: User) -> str:
        memberships = list(obj.org_memberships.select_related("organization").all())
        if not memberships:
            return "—"
        labels = [f"{m.organization_id}:{m.get_role_display()}" for m in memberships[:3]]
        more = len(memberships) - len(labels)
        if more > 0:
            labels.append(f"(+{more})")
        return ", ".join(labels)

    def get_form(self, request, obj=None, **kwargs):  # type: ignore[override]
        if obj is None:
            base_form = self.add_form

            class RequestScopedUserCreationForm(base_form):
                def __init__(self_inner, *args, **inner_kwargs):
                    super().__init__(*args, **inner_kwargs)
                    org_qs = user_accessible_organizations(request.user)
                    if not request.user.is_superuser:
                        self_inner.fields["organization"].queryset = org_qs
                    active_org_id = get_active_admin_org_id(request)
                    if active_org_id and "organization" in self_inner.fields:
                        self_inner.fields["organization"].initial = active_org_id

            kwargs["form"] = RequestScopedUserCreationForm
        else:
            kwargs["form"] = kwargs.get("form", self.form)
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):  # type: ignore[override]
        super().save_model(request, obj, form, change)
        sync_user_access_flags(obj)

    def save_formset(self, request, form, formset, change):  # type: ignore[override]
        instances = formset.save()
        for instance in instances:
            if isinstance(instance, OrganizationMembership):
                sync_user_access_flags(instance.user)
        for obj in getattr(formset, "deleted_objects", []):
            if isinstance(obj, OrganizationMembership):
                user = getattr(obj, "user", None)
                if user:
                    sync_user_access_flags(user)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
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
    inlines = [OrganizationMembershipUserInline]

    def get_readonly_fields(self, request, obj=None):  # type: ignore[override]
        ro = list(super().get_readonly_fields(request, obj))
        if obj and "id" not in ro:
            ro.append("id")
        return ro


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "created_at")
    list_filter = ("role", "organization")
    search_fields = ("organization__id", "organization__name", "user__username", "user__email")
    autocomplete_fields = ("organization", "user")

    def get_queryset(self, request):  # type: ignore[override]
        qs = super().get_queryset(request)
        active_org_id = get_active_admin_org_id(request)
        if active_org_id:
            return qs.filter(organization_id=active_org_id)
        if request.user.is_superuser:
            return qs
        accessible_ids = user_accessible_organizations(request.user).values_list("id", flat=True)
        return qs.filter(organization_id__in=accessible_ids)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):  # type: ignore[override]
        if db_field.name == "organization" and not request.user.is_superuser:
            kwargs["queryset"] = user_accessible_organizations(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@require_POST
def select_admin_organization(request):
    if not request.user or not request.user.is_authenticated:
        return redirect("admin:login")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("admin:index")
    choice = request.POST.get("organization")
    if choice == "__all__" and request.user.is_superuser:
        set_active_admin_org_id(request, None)
    else:
        org_qs = user_accessible_organizations(request.user)
        if choice and org_qs.filter(id=choice).exists():
            set_active_admin_org_id(request, choice)
    return redirect(next_url)


_original_get_urls = admin.site.get_urls


def tenant_admin_urls():
    urls = _original_get_urls()
    custom = [
        path("select-organization/", admin.site.admin_view(select_admin_organization), name="select_organization"),
    ]
    return custom + urls


admin.site.get_urls = tenant_admin_urls  # type: ignore[assignment]


_original_each_context = admin.site.each_context


def tenant_each_context(request):
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
