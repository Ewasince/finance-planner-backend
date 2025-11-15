from __future__ import annotations

from datetime import date

from django.core.validators import MinValueValidator
from django.db import models
from model_utils.models import UUIDModel
from models import TimeWatchingModel


class RegularOperationType(models.TextChoices):
    INCOME = "income", "Доход"
    EXPENSE = "expense", "Расход"


class RegularOperationPeriodType(models.TextChoices):
    DAY = "day", "Ежедневно"
    WEEK = "week", "Еженедельно"
    MONTH = "month", "Ежемесячно"


class RegularOperation(UUIDModel, TimeWatchingModel):
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="regular_operations"
    )
    title = models.CharField(max_length=255, verbose_name="Название операции")
    description = models.TextField(blank=True, verbose_name="Описание")
    amount = models.DecimalField(
        max_digits=19,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="Сумма",
    )
    type = models.CharField(
        max_length=20,
        choices=RegularOperationType.choices,
        verbose_name="Тип операции",
    )
    from_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="regular_operations_outgoing",
    )
    to_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="regular_operations_incoming",
    )
    start_date = models.DateTimeField(verbose_name="Дата начала")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата окончания")
    period_type = models.CharField(
        max_length=20,
        choices=RegularOperationPeriodType.choices,
        verbose_name="Периодичность",
    )
    period_interval = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Интервал",
    )
    active_before = models.DateField(default=date.max, verbose_name="Активна")

    class Meta:
        verbose_name = "Регулярная операция"
        verbose_name_plural = "Регулярные операции"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_type_display()})"
