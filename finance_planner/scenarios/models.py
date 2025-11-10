from __future__ import annotations

from django.db import models
from model_utils.models import UUIDModel
from models import TimeWatchingModel
from users.models import User


class RuleType(models.TextChoices):
    FIXED = "fixed", "Фиксированная сумма"
    # TODO: PERCENTAGE = 'percentage', 'Процент'


class Scenario(UUIDModel, TimeWatchingModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scenarios")
    operation = models.OneToOneField(
        "regular_operations.RegularOperation",
        on_delete=models.CASCADE,
        related_name="scenario",
        verbose_name="Регулярная операция",
    )
    title = models.CharField(max_length=255, verbose_name="Название сценария")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Платежный сценарий"
        verbose_name_plural = "Платежные сценарии"


class ScenarioRule(UUIDModel, TimeWatchingModel):
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name="rules")
    target_account = models.ForeignKey("accounts.Account", on_delete=models.CASCADE)
    type = models.CharField(
        max_length=20,
        choices=RuleType.choices,
        verbose_name="Тип правила",
        default=RuleType.FIXED,
    )
    amount = models.DecimalField(
        max_digits=19,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Фиксированная сумма",
    )
    order = models.IntegerField(default=0, verbose_name="Порядок применения")

    class Meta:
        verbose_name = "Правило сценария"
        verbose_name_plural = "Правила сценария"

        ordering = ["order"]
