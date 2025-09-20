from django.contrib import admin
from django import forms
from django.urls import path
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from apps.platform.authorization.models import Role, RoleCapability
from apps.platform.authorization.capabilities import CAPABILITY_CHOICES


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
    list_display = ("slug", "name", "system", "created_at")
    list_filter = ("system", "created_at")
    date_hierarchy = "created_at"
    ordering = ("slug",)
    search_fields = ("slug", "name")
    inlines = [RoleCapabilityInline]

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path("capabilities/", self.admin_site.admin_view(self.capabilities_summary), name="authorization_capabilities_summary"),
        ]
        return extra + urls

    def capabilities_summary(self, request: HttpRequest) -> HttpResponse:
        from apps.platform.authorization.capabilities import role_capabilities, DEFAULT_CAPS
        roles = Role.objects.all().order_by("slug")
        role_rows = []
        seen = set()
        for slug, caps in DEFAULT_CAPS.items():
            role_rows.append({"slug": slug, "name": slug.title(), "system": True, "caps": sorted(caps)})
            seen.add(slug)
        for r in roles:
            role_rows.append({
                "slug": r.slug,
                "name": r.name,
                "system": r.system,
                "caps": sorted(role_capabilities(r.slug)),
            })
            seen.add(r.slug)
        ctx = {**self.admin_site.each_context(request), "title": "Effective Capabilities", "role_rows": role_rows}
        return TemplateResponse(request, "admin/authorization/capabilities_summary.html", ctx)
