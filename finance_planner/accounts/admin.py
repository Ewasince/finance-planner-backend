from accounts.models import Account
from django.contrib import admin


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "type", "current_balance", "created_at"]
    list_filter = ["type", "created_at"]
    search_fields = ["name", "user__username"]
    readonly_fields = ["created_at", "updated_at"]
