from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["date", "type", "amount", "user", "confirmed"]
    list_filter = ["type", "confirmed", "date"]
    search_fields = ["description", "user__username"]
    readonly_fields = ["created_at", "updated_at"]
