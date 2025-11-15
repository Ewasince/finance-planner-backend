from __future__ import annotations

from django.core.validators import MinValueValidator
from django.db import models
from model_utils.models import UUIDModel


class TransactionType(models.TextChoices):
    INCOME = "income", "Пополнение"
    EXPENSE = "expense", "Списание"
    TRANSFER = "transfer", "Перевод"


class Transaction(UUIDModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="transactions")
    date = models.DateField(verbose_name="Дата операции")
    # поле только для запланированных транзакций, чтобы регулярные операция/сценариии видели что в
    # конкретную дату они уже ставили транзакцию
    planned_date = models.DateField(
        verbose_name="Дата запланированной операции", null=True, blank=True
    )
    type = models.CharField(
        max_length=20, choices=TransactionType.choices, verbose_name="Тип операции"
    )
    amount = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        validators=[MinValueValidator(0.01)],
        verbose_name="Сумма",
    )
    from_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outgoing_transactions",
    )
    to_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_transactions",
    )
    confirmed = models.BooleanField(default=True, verbose_name="Подтверждено")
    description = models.TextField(blank=True, verbose_name="Комментарий")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    operation = models.ForeignKey(
        "regular_operations.RegularOperation",
        on_delete=models.SET_NULL,  # TODO: я хз чё сюда ставить
        null=True,
        blank=True,
    )
    scenario_rule = models.ForeignKey(
        "scenarios.ScenarioRule",
        on_delete=models.SET_NULL,  # TODO: я хз чё сюда ставить
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Операция"
        verbose_name_plural = "Операции"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.date} {self.type} {self.amount}"
