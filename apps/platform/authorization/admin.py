from __future__ import annotations

from typing import Any, MutableMapping, cast

from django import forms
from django.contrib import admin
from django.db.models import Q, QuerySet
from django.db.models.fields.related import ForeignKey
from django.forms import ModelChoiceField
from django.forms.models import ModelForm
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.urls import path

from apps.platform.accounts.models import Organization
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


def _user_is_superuser(user: Any) -> bool:
    return bool(getattr(user, "is_superuser", False))


class RoleAdminForm(forms.ModelForm[Role]):
    class Meta:  # type: ignore[override]
        model = Role
        fields = ["name", "description", "organization", "system", "presets"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        org: Organization | None = None
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
        presets_field = cast(forms.ModelMultipleChoiceField, self.fields["presets"])
        presets_field.queryset = qs


class PermissionPresetAdminForm(forms.ModelForm[PermissionPreset]):
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

    class Meta:  # type: ignore[override]
        model = PermissionPreset
        fields = [
            "name",
            "description",
            "organization",
            "system",
            "capabilities",
            "extra_capabilities",
        ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        capabilities_field = cast(forms.MultipleChoiceField, self.fields["capabilities"])
        capabilities_field.choices = capability_choices()
        if self.instance and self.instance.pk:
            existing = self.instance.capabilities.values_list("capability", flat=True)
            capabilities_field.initial = list(existing)

    def save(self, commit: bool = True) -> PermissionPreset:
        preset = super().save(commit=commit)
        extras_raw = self.cleaned_data.get("extra_capabilities", "") or ""
        extra_caps = {
            cap.strip() for cap in extras_raw.split(",") if cap.strip()
        }
        selected = set(self.cleaned_data.get("capabilities", [])) | extra_caps
        self._selected_capabilities = selected
        if commit:
            self.sync_capabilities(preset)
        return preset

    def sync_capabilities(self, preset: PermissionPreset) -> None:
        selected_attr = getattr(self, "_selected_capabilities", None)
        selected: set[str]
        if selected_attr is None:
            selected = set()
        else:
            selected = cast(set[str], selected_attr)
        current = set(preset.capabilities.values_list("capability", flat=True))
        for cap in current - selected:
            preset.capabilities.filter(capability=cap).delete()
        for cap in selected - current:
            PresetCapability.objects.create(preset=preset, capability=cap)
        # Refresh cached choices for dependent forms
        try:
            from apps.platform.authorization import capabilities as capabilities_module

            capabilities_module.CAPABILITY_CHOICES = capabilities_module.capability_choices()
        except Exception:
            pass

    def save_m2m(self) -> None:
        self.sync_capabilities(self.instance)


class RoleCapabilityForm(forms.ModelForm[RoleCapability]):
    capability = forms.ChoiceField(choices=(), label="Capability")

    class Meta:  # type: ignore[override]
        model = RoleCapability
        fields = ["capability"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        capability_field = cast(forms.ChoiceField, self.fields["capability"])
        capability_field.choices = capability_choices()


class RoleCapabilityInline(admin.TabularInline[RoleCapability, Role]):
    model = RoleCapability
    extra = 1
    form = RoleCapabilityForm


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin[Role]):
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
        role_rows: list[dict[str, Any]] = []
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

    def get_queryset(self, request: HttpRequest) -> QuerySet[Role]:
        qs = super().get_queryset(request)
        active_org_id = get_active_admin_org_id(request)
        if active_org_id:
            return qs.filter(Q(organization__isnull=True) | Q(organization_id=active_org_id))
        if _user_is_superuser(request.user):
            return qs
        org_ids = user_accessible_organizations(request.user).values_list("id", flat=True)
        return qs.filter(Q(organization__isnull=True) | Q(organization_id__in=org_ids))

    def formfield_for_foreignkey(
        self,
        db_field: ForeignKey[Any, Any],
        request: HttpRequest,
        **kwargs: Any,
    ) -> ModelChoiceField:
        if db_field.name == "organization" and not _user_is_superuser(request.user):
            kwargs["queryset"] = user_accessible_organizations(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(
        self,
        request: HttpRequest,
        obj: Role | None = None,
        change: bool = False,
        **kwargs: Any,
    ) -> type[ModelForm[Role]]:
        form_class = super().get_form(request, obj, change=change, **kwargs)
        active_org_id = get_active_admin_org_id(request)
        accessible_qs: QuerySet[Organization] = user_accessible_organizations(request.user)

        class WrappedForm(form_class):
            def __init__(self, *args: Any, **inner_kwargs: Any) -> None:
                initial: MutableMapping[str, Any] = dict(inner_kwargs.get("initial", {}))
                if active_org_id and obj is None:
                    initial.setdefault("organization", active_org_id)
                inner_kwargs["initial"] = initial
                super().__init__(*args, **inner_kwargs)
                if not _user_is_superuser(request.user) and "organization" in self.fields:
                    org_field = cast(ModelChoiceField, self.fields["organization"])
                    org_field.queryset = accessible_qs
                presets_field = cast(forms.ModelMultipleChoiceField, self.fields["presets"])
                presets_qs = presets_field.queryset
                if presets_qs is None:
                    return
                if active_org_id:
                    presets_qs = presets_qs.filter(
                        Q(organization__isnull=True) | Q(organization_id=active_org_id)
                    )
                elif not _user_is_superuser(request.user):
                    accessible_ids = list(accessible_qs.values_list("id", flat=True))
                    presets_qs = presets_qs.filter(
                        Q(organization__isnull=True) | Q(organization_id__in=accessible_ids)
                    )
                presets_field.queryset = presets_qs.order_by("name")

        return WrappedForm


@admin.register(PermissionPreset)
class PermissionPresetAdmin(admin.ModelAdmin[PermissionPreset]):
    form = PermissionPresetAdminForm
    list_display = ("name", "organization", "system", "created_at")
    search_fields = ("name", "organization__name")
    list_filter = ("system", "created_at", "organization")
    date_hierarchy = "created_at"

    def get_queryset(self, request: HttpRequest) -> QuerySet[PermissionPreset]:
        qs = super().get_queryset(request)
        active_org_id = get_active_admin_org_id(request)
        if active_org_id:
            return qs.filter(Q(organization__isnull=True) | Q(organization_id=active_org_id))
        if _user_is_superuser(request.user):
            return qs
        org_ids = user_accessible_organizations(request.user).values_list("id", flat=True)
        return qs.filter(Q(organization__isnull=True) | Q(organization_id__in=org_ids))

    def formfield_for_foreignkey(
        self,
        db_field: ForeignKey[Any, Any],
        request: HttpRequest,
        **kwargs: Any,
    ) -> ModelChoiceField:
        if db_field.name == "organization" and not _user_is_superuser(request.user):
            kwargs["queryset"] = user_accessible_organizations(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(
        self,
        request: HttpRequest,
        obj: PermissionPreset,
        form: forms.ModelForm[PermissionPreset],
        change: bool,
    ) -> None:
        super().save_model(request, obj, form, change)
        if isinstance(form, PermissionPresetAdminForm):
            form.sync_capabilities(obj)

    def get_form(
        self,
        request: HttpRequest,
        obj: PermissionPreset | None = None,
        change: bool = False,
        **kwargs: Any,
    ) -> type[ModelForm[PermissionPreset]]:
        form_class = super().get_form(request, obj, change=change, **kwargs)
        active_org_id = get_active_admin_org_id(request)
        accessible_qs: QuerySet[Organization] = user_accessible_organizations(request.user)

        class WrappedForm(form_class):
            def __init__(self, *args: Any, **inner_kwargs: Any) -> None:
                initial: MutableMapping[str, Any] = dict(inner_kwargs.get("initial", {}))
                if active_org_id and obj is None:
                    initial.setdefault("organization", active_org_id)
                inner_kwargs["initial"] = initial
                super().__init__(*args, **inner_kwargs)
                if not _user_is_superuser(request.user) and "organization" in self.fields:
                    org_field = cast(ModelChoiceField, self.fields["organization"])
                    org_field.queryset = accessible_qs

        return WrappedForm
