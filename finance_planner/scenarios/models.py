import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class PaymentScenario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='payment_scenarios')
    name = models.CharField(max_length=255, verbose_name="Название сценария")
    description = models.TextField(blank=True, verbose_name="Описание")
    source_account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='scenarios')
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    execution_order = models.IntegerField(default=0, verbose_name="Порядок выполнения")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Платежный сценарий"
        verbose_name_plural = "Платежные сценарии"
        ordering = ['execution_order']


class ScenarioRule(models.Model):
    class RuleType(models.TextChoices):
        FIXED = 'fixed', 'Фиксированная сумма'
        PERCENTAGE = 'percentage', 'Процент'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scenario = models.ForeignKey(PaymentScenario, on_delete=models.CASCADE, related_name='rules')
    target_account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=RuleType.choices, verbose_name="Тип правила")
    amount = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True,
                                 verbose_name="Фиксированная сумма")
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Процент"
    )
    order = models.IntegerField(default=0, verbose_name="Порядок применения")

    class Meta:
        verbose_name = "Правило сценария"
        verbose_name_plural = "Правила сценария"

        ordering = ['order']
