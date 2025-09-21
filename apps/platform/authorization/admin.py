from django import forms
from django.contrib import admin
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.urls import path

from apps.platform.accounts.models import Organization, OrganizationMembership
from apps.platform.accounts.utils import (
    get_active_admin_org_id,
    user_accessible_organizations,
)
from apps.platform.authorization.capabilities import CAPABILITY_CHOICES
from apps.platform.authorization.models import (
    FIELD_RESOURCE_CHOICES,
    PermissionPreset,
    PresetCapability,
    PresetFieldPolicy,
    Role,
    RoleCapability,
)
from apps.platform.artifacts.registry import artifact_field, artifact_types


class RoleAdminForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ["name", "description", "organization", "system", "presets"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        org = None
        if self.instance and self.instance.pk:
            org = self.instance.organization
        elif "organization" in self.initial:
            org = self.initial.get("organization")
        elif self.data.get("organization"):
            try:
                org = Organization.objects.get(pk=self.data.get("organization"))
            except Organization.DoesNotExist:
                org = None
        qs = PermissionPreset.objects.all().order_by("name")
        if org:
            qs = qs.filter(Q(organization=org) | Q(organization__isnull=True))
        self.fields["presets"].queryset = qs


class PermissionPresetAdminForm(forms.ModelForm):
    class Meta:
        model = PermissionPreset
        fields = ["name", "description", "organization", "system"]


class RoleCapabilityForm(forms.ModelForm):
    capability = forms.ChoiceField(choices=CAPABILITY_CHOICES)

    class Meta:
        model = RoleCapability
        fields = ["capability"]


class RoleCapabilityInline(admin.TabularInline):
    model = RoleCapability
    extra = 1
    form = RoleCapabilityForm


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    form = RoleAdminForm
    list_display = ("name", "organization", "system", "created_at")
    list_filter = ("system", "created_at", "organization")
    date_hierarchy = "created_at"
    ordering = ("name",)
    search_fields = ("name", "organization__name")
    filter_horizontal = ("presets",)
    inlines = [RoleCapabilityInline]

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path("capabilities/", self.admin_site.admin_view(self.capabilities_summary), name="authorization_capabilities_summary"),
        ]
        return extra + urls

    def capabilities_summary(self, request: HttpRequest) -> HttpResponse:
        from apps.platform.authorization.capabilities import role_capabilities, DEFAULT_CAPS
        roles = Role.objects.select_related("organization").all().order_by("name")
        role_rows = []
        for name, caps in DEFAULT_CAPS.items():
            role_rows.append({"name": name.title(), "system": True, "caps": sorted(caps)})
        for r in roles:
            caps = role_capabilities(r.name, organization_id=r.organization_id)
            role_rows.append({
                "uuid": r.uuid,
                "name": r.name,
                "system": r.system,
                "organization": r.organization.name if r.organization else None,
                "caps": sorted(caps),
            })
        ctx = {**self.admin_site.each_context(request), "title": "Effective Capabilities", "role_rows": role_rows}
        return TemplateResponse(request, "admin/authorization/capabilities_summary.html", ctx)

    def get_queryset(self, request):  # type: ignore[override]
        qs = super().get_queryset(request)
        active_org_id = get_active_admin_org_id(request)
        if active_org_id:
            return qs.filter(Q(organization__isnull=True) | Q(organization_id=active_org_id))
        if request.user.is_superuser:
            return qs
        org_ids = user_accessible_organizations(request.user).values_list("id", flat=True)
        return qs.filter(Q(organization__isnull=True) | Q(organization_id__in=org_ids))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):  # type: ignore[override]
        if db_field.name == "organization" and not request.user.is_superuser:
            kwargs["queryset"] = user_accessible_organizations(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):  # type: ignore[override]
        form_class = super().get_form(request, obj, **kwargs)
        active_org_id = get_active_admin_org_id(request)
        accessible_qs = user_accessible_organizations(request.user)

        class WrappedForm(form_class):
            def __init__(self_inner, *args, **inner_kwargs):
                initial = dict(inner_kwargs.get("initial", {}))
                if active_org_id and obj is None:
                    initial.setdefault("organization", active_org_id)
                inner_kwargs["initial"] = initial
                super().__init__(*args, **inner_kwargs)
                if not request.user.is_superuser and "organization" in self_inner.fields:
                    self_inner.fields["organization"].queryset = accessible_qs
                presets_qs = self_inner.fields["presets"].queryset
                if active_org_id:
                    presets_qs = presets_qs.filter(
                        Q(organization__isnull=True) | Q(organization_id=active_org_id)
                    )
                elif not request.user.is_superuser:
                    accessible_ids = list(accessible_qs.values_list("id", flat=True))
                    presets_qs = presets_qs.filter(
                        Q(organization__isnull=True) | Q(organization_id__in=accessible_ids)
                    )
                self_inner.fields["presets"].queryset = presets_qs.order_by("name")

        return WrappedForm


class PresetCapabilityInline(admin.TabularInline):
    model = PresetCapability
    extra = 1
class PresetFieldPolicyForm(forms.ModelForm):
    resource = forms.ChoiceField(choices=FIELD_RESOURCE_CHOICES, required=True)
    type = forms.ChoiceField(choices=(), required=True)

    class Meta:
        model = PresetFieldPolicy
        fields = ["resource", "type", "field_name", "actions"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].choices = [(t, t) for t in sorted(artifact_types())]
        self.fields["field_name"].help_text = "Must match a registered artifact field name."
        self.fields["actions"].help_text = "JSON list of allowed actions (view, download, update, create, delete)."

    def clean(self):
        cleaned = super().clean()
        atype = cleaned.get("type")
        fname = cleaned.get("field_name")
        if atype and fname and artifact_field(atype, fname) is None:
            raise forms.ValidationError(f"Unknown artifact field: {atype}.{fname}")
        return cleaned


class PresetFieldPolicyInline(admin.TabularInline):
    model = PresetFieldPolicy
    extra = 1
    form = PresetFieldPolicyForm


@admin.register(PermissionPreset)
class PermissionPresetAdmin(admin.ModelAdmin):
    form = PermissionPresetAdminForm
    list_display = ("name", "organization", "system", "created_at")
    search_fields = ("name", "organization__name")
    list_filter = ("system", "created_at", "organization")
    date_hierarchy = "created_at"
    inlines = [PresetCapabilityInline, PresetFieldPolicyInline]

    def get_queryset(self, request):  # type: ignore[override]
        qs = super().get_queryset(request)
        active_org_id = get_active_admin_org_id(request)
        if active_org_id:
            return qs.filter(Q(organization__isnull=True) | Q(organization_id=active_org_id))
        if request.user.is_superuser:
            return qs
        org_ids = user_accessible_organizations(request.user).values_list("id", flat=True)
        return qs.filter(Q(organization__isnull=True) | Q(organization_id__in=org_ids))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):  # type: ignore[override]
        if db_field.name == "organization" and not request.user.is_superuser:
            kwargs["queryset"] = user_accessible_organizations(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):  # type: ignore[override]
        form_class = super().get_form(request, obj, **kwargs)
        active_org_id = get_active_admin_org_id(request)
        accessible_qs = user_accessible_organizations(request.user)

        class WrappedForm(form_class):
            def __init__(self_inner, *args, **inner_kwargs):
                initial = dict(inner_kwargs.get("initial", {}))
                if active_org_id and obj is None:
                    initial.setdefault("organization", active_org_id)
                inner_kwargs["initial"] = initial
                super().__init__(*args, **inner_kwargs)
                if not request.user.is_superuser and "organization" in self_inner.fields:
                    self_inner.fields["organization"].queryset = accessible_qs

        return WrappedForm
