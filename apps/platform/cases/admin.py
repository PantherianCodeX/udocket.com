from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from apps.platform.cases.models import Case, CaseMembership
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

class CaseMembershipInline(admin.TabularInline):
    model = CaseMembership
    extra = 1
    autocomplete_fields = ["user"]


@admin.register(Case)
class CaseAdmin(SimpleHistoryAdmin):
    list_display = ("id", "title", "created_at", "updated_at")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    search_fields = ("id", "title")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = ((None, {"fields": ("id", "title", "created_at", "updated_at")}),)
    inlines = [CaseMembershipInline]
