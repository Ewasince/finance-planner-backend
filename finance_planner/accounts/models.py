import uuid
from django.db import models


class Account(models.Model):
    class AccountType(models.TextChoices):
        SAVINGS = 'savings', 'Накопления'
        CHECKING = 'checking', 'Расчетный'
        CREDIT = 'credit', 'Кредитный'
        INVESTMENT = 'investment', 'Инвестиционный'
        LOAN = 'loan', 'Долг'

    class GradientTheme(models.TextChoices):
        DEFAULT = 'default', 'По умолчанию'
        MOUNTAINS = 'mountains', 'Горы'
        FOREST = 'forest', 'Лес'
        TRAVEL = 'travel', 'Путешествия'
        TECHNOLOGY = 'technology', 'Технология'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=255, verbose_name="Название счета")
    type = models.CharField(max_length=20, choices=AccountType.choices, verbose_name="Тип счета")
    current_balance = models.DecimalField(max_digits=19, decimal_places=4, default=0, verbose_name="Текущий баланс")
    target_amount = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True,
                                        verbose_name="Целевая сумма")
    description = models.TextField(blank=True, verbose_name="Описание")
    accent_color = models.CharField(max_length=7, blank=True, verbose_name="Цвет акцента")
    gradient_theme = models.CharField(max_length=20, choices=GradientTheme.choices, default=GradientTheme.DEFAULT,
                                      verbose_name="Градиент")
    custom_image_url = models.URLField(blank=True, verbose_name="URL кастомного изображения")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Счет"
        verbose_name_plural = "Счета"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.name} ({self.user.email})"
