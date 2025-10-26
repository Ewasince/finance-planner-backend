from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from accounts.models import AccountType
from django.urls import reverse
from django.utils import timezone
import pytest
from regular_operations.models import (
    RegularOperation,
    RegularOperationPeriodType,
    RegularOperationType,
)
from rest_framework import status
from scenarios.models import PaymentScenario


pytestmark = pytest.mark.django_db


def _create_income_operation(user, to_account):
    now = timezone.now()
    return RegularOperation.objects.create(
        user=user,
        title="Зарплата",
        description="Основной доход",
        amount=Decimal("1000.00"),
        type=RegularOperationType.INCOME,
        to_account=to_account,
        start_date=now,
        end_date=now + timedelta(days=30),
        period_type=RegularOperationPeriodType.MONTH,
        period_interval=1,
        is_active=True,
    )


def test_add_rule_to_scenario(api_client, user, create_account):
    main_account = create_account(user, "Основной", AccountType.MAIN)
    target_account = create_account(user, "Цели", AccountType.PURPOSE)
    operation = _create_income_operation(user, main_account)
    scenario = PaymentScenario.objects.create(
        user=user,
        operation=operation,
        title="Распределение",
        description="Сценарий по умолчанию",
        is_active=True,
    )

    url = reverse("scenario-rule-create", kwargs={"scenario_id": scenario.id})
    payload = {
        "target_account": str(target_account.id),
        "amount": "250.00",
        "order": 1,
    }

    response = api_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    scenario.refresh_from_db()
    rules = list(scenario.rules.all())
    assert len(rules) == 1
    assert rules[0].target_account_id == target_account.id
    assert rules[0].amount == Decimal("250.00")
    assert response.data["scenario_id"] == str(scenario.id)


def test_add_rule_to_foreign_scenario_not_allowed(api_client, user, other_user, create_account):
    other_main = create_account(other_user, "Основной", AccountType.MAIN)
    operation = _create_income_operation(other_user, other_main)
    scenario = PaymentScenario.objects.create(
        user=other_user,
        operation=operation,
        title="Их сценарий",
        description="",  # noqa: PIE796
        is_active=True,
    )

    url = reverse("scenario-rule-create", kwargs={"scenario_id": scenario.id})
    target_account = create_account(user, "Цели", AccountType.PURPOSE)
    payload = {
        "target_account": str(target_account.id),
        "amount": "100.00",
        "order": 1,
    }

    response = api_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_add_rule_with_foreign_account_validation_error(
    api_client, user, other_user, create_account
):
    main_account = create_account(user, "Основной", AccountType.MAIN)
    operation = _create_income_operation(user, main_account)
    scenario = PaymentScenario.objects.create(
        user=user,
        operation=operation,
        title="Распределение",
        description="",  # noqa: PIE796
        is_active=True,
    )
    foreign_account = create_account(other_user, "Чужой счет", AccountType.RESERVE)

    url = reverse("scenario-rule-create", kwargs={"scenario_id": scenario.id})
    payload = {
        "target_account": str(foreign_account.id),
        "amount": "150.00",
        "order": 1,
    }

    response = api_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "target_account" in response.data
