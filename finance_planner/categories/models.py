import uuid
from django.db import models


class Category(models.Model):
    class CategoryType(models.TextChoices):
        INCOME = 'income', 'Доход'
        EXPENSE = 'expense', 'Расход'
        TRANSFER = 'transfer', 'Перевод'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255, verbose_name="Название категории")
    type = models.CharField(max_length=20, choices=CategoryType.choices, default=CategoryType.EXPENSE,
                            verbose_name="Тип категории")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    color = models.CharField(max_length=7, default='#3682f6', verbose_name="Цвет категории")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Иконка категории")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_system = models.BooleanField(default=False, verbose_name="Системная категория")
    budget_limit = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True,
                                       verbose_name="Лимит бюджета")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        unique_together = ['user', 'name']
        ordering = ['type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    @property
    def is_root(self):
        return self.parent is None

    @property
    def has_children(self):
        return self.children.exists()
