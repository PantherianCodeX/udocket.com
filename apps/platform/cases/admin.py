from django.contrib import admin
from apps.platform.cases.models import Case, CaseMembership
from django.contrib import admin

class CaseMembershipInline(admin.TabularInline):
    model = CaseMembership
    extra = 1


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at", "updated_at")
    search_fields = ("id", "title")
    inlines = [CaseMembershipInline]
