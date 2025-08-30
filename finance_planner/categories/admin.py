from django.contrib import admin
from categories.models import Category


class CategoryChildrenInline(admin.TabularInline):
    model = Category
    fk_name = 'parent'
    extra = 1
    fields = ['name', 'type', 'color', 'icon', 'budget_limit']
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'type', 'parent', 'budget_limit', 'is_system', 'created_at']
    list_filter = ['type', 'is_system', 'created_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CategoryChildrenInline]
    fieldsets = (
        (None, {
            'fields': ('user', 'name', 'type', 'parent')
        }),
        ('Внешний вид', {
            'fields': ('color', 'icon', 'description'),
            'classes': ('collapse',)
        }),
        ('Бюджет', {
            'fields': ('budget_limit', 'is_system'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'parent')
