from django.contrib import admin
from regular_operations.models import RegularOperation


@admin.register(RegularOperation)
class RegularOperationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "type",
        "user",
        "amount",
        "start_date",
        "period_type",
        "period_interval",
        "is_active",
    )
    list_filter = ("type", "period_type", "is_active")
    search_fields = ("title", "description")
    ordering = ("-created_at",)
    autocomplete_fields = ("user", "from_account", "to_account")
