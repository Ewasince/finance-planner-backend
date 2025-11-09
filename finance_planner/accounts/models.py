from __future__ import annotations

import uuid

from django.db import models


class AccountType(models.TextChoices):
    MAIN = "main", "Главные"
    PURPOSE = "purpose", "Цель"
    ACCUMULATION = "accumulation", "Накопления"
    DEBT = "debt", "Долг"
    RESERVE = "reserve", "Резерв"


class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="accounts")
    name = models.CharField(max_length=255, verbose_name="Название счета")
    type = models.CharField(max_length=20, choices=AccountType.choices, verbose_name="Тип счета")
    current_balance = models.DecimalField(
        max_digits=19, decimal_places=2, default=0, verbose_name="Текущий баланс"
    )
    target_amount = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Целевая сумма",
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Счет"
        verbose_name_plural = "Счета"
        db_table = "accounts"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.user.email})"
