from django.contrib import admin
from scenarios.models import Scenario, ScenarioRule


class ScenarioRuleInline(admin.TabularInline):
    model = ScenarioRule
    extra = 1


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "active_before"]
    list_filter = ["active_before", "created_at"]
    search_fields = ["title", "user__username"]
    inlines = [ScenarioRuleInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ScenarioRule)
class ScenarioRuleAdmin(admin.ModelAdmin):
    list_display = ["scenario", "target_account", "type", "amount", "order"]
    list_filter = ["type"]
