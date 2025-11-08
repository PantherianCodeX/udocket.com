from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.platform.admin import TenantScopedAdminMixin
from apps.platform.cases.models import Case, CaseMembership
from apps.platform.tenancy import scope_cases


class CaseMembershipInline(admin.TabularInline):
    model = CaseMembership
    extra = 1
    autocomplete_fields = ["user"]


@admin.register(Case)
class CaseAdmin(TenantScopedAdminMixin, SimpleHistoryAdmin):
    list_display = ("id", "title", "organization", "created_at", "updated_at")
    list_filter = (
        "organization",
        "created_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    search_fields = ("id", "title")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = ((None, {"fields": ("id", "title", "organization", "created_at", "updated_at")}),)
    inlines = [CaseMembershipInline]

    def scope_queryset(self, request, queryset):  # type: ignore[override]
        return scope_cases(queryset, request.user)
