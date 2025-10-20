from django.contrib import admin

from .models import PaymentScenario, ScenarioRule


class ScenarioRuleInline(admin.TabularInline):
    model = ScenarioRule
    extra = 1


@admin.register(PaymentScenario)
class PaymentScenarioAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "is_active"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "user__username"]
    inlines = [ScenarioRuleInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ScenarioRule)
class ScenarioRuleAdmin(admin.ModelAdmin):
    list_display = ["scenario", "target_account", "type", "amount", "order"]
    list_filter = ["type"]
