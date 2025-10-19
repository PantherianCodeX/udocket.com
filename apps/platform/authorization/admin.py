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
from apps.platform.authorization.capabilities import capability_choices
from apps.platform.authorization.models import (
    PermissionPreset,
    PresetCapability,
    Role,
    RoleCapability,
)


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
    capabilities = forms.MultipleChoiceField(
        choices=(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Capabilities",
    )
    extra_capabilities = forms.CharField(
        required=False,
        help_text="Add custom capability keys (comma separated).",
        label="Additional capabilities",
    )

    class Meta:
        model = PermissionPreset
        fields = [
            "name",
            "description",
            "organization",
            "system",
            "capabilities",
            "extra_capabilities",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["capabilities"].choices = capability_choices()
        if self.instance and self.instance.pk:
            existing = self.instance.capabilities.values_list("capability", flat=True)
            self.fields["capabilities"].initial = list(existing)

    def save(self, commit=True):  # type: ignore[override]
        preset = super().save(commit=commit)
        extras_raw = self.cleaned_data.get("extra_capabilities", "") or ""
        extra_caps = {
            cap.strip() for cap in extras_raw.split(",") if cap.strip()
        }
        self._selected_capabilities = set(self.cleaned_data.get("capabilities", [])) | extra_caps
        if commit:
            self.sync_capabilities(preset)
        return preset

    def sync_capabilities(self, preset: PermissionPreset) -> None:
        selected = getattr(self, "_selected_capabilities", set())
        current = set(preset.capabilities.values_list("capability", flat=True))
        for cap in current - selected:
            preset.capabilities.filter(capability=cap).delete()
        for cap in selected - current:
            PresetCapability.objects.create(preset=preset, capability=cap)
        # Refresh cached choices for dependent forms
        try:
            from apps.platform.authorization import capabilities as capabilities_module

            capabilities_module.capability_choices(force_refresh=True)
        except Exception:
            pass

    def save_m2m(self) -> None:  # type: ignore[override]
        self.sync_capabilities(self.instance)


class RoleCapabilityForm(forms.ModelForm):
    capability = forms.ChoiceField(choices=(), label="Capability")

    class Meta:
        model = RoleCapability
        fields = ["capability"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["capability"].choices = capability_choices()


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


@admin.register(PermissionPreset)
class PermissionPresetAdmin(admin.ModelAdmin):
    form = PermissionPresetAdminForm
    list_display = ("name", "organization", "system", "created_at")
    search_fields = ("name", "organization__name")
    list_filter = ("system", "created_at", "organization")
    date_hierarchy = "created_at"

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

    def save_model(self, request, obj, form, change):  # type: ignore[override]
        super().save_model(request, obj, form, change)
        if isinstance(form, PermissionPresetAdminForm):
            form.sync_capabilities(obj)

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
