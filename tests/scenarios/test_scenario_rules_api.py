from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from accounts.models import AccountType
from django.utils import timezone
import pytest
from regular_operations.models import (
    RegularOperation,
    RegularOperationPeriodType,
    RegularOperationType,
)
from rest_framework import status
from scenarios.models import Scenario


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


def test_add_rule_to_scenario(api_client, main_user, create_account):
    main_account = create_account(main_user, "Основной", AccountType.MAIN)
    target_account = create_account(main_user, "Цели", AccountType.PURPOSE)
    operation = _create_income_operation(main_user, main_account)
    scenario = Scenario.objects.create(
        user=main_user,
        operation=operation,
        title="Распределение",
        description="Сценарий по умолчанию",
        is_active=True,
    )

    payload = {
        "scenario": str(scenario.id),
        "target_account": str(target_account.id),
        "amount": "250.00",
        "order": 1,
    }

    response = api_client.post("/api/scenarios/rules/", payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    scenario.refresh_from_db()
    rules = list(scenario.rules.all())
    assert len(rules) == 1
    assert rules[0].target_account_id == target_account.id
    assert rules[0].amount == Decimal("250.00")
    assert response.data["scenario"] == scenario.id


def test_add_rule_to_foreign_scenario_not_allowed(
    api_client, main_user, other_user, create_account
):
    other_account = create_account(other_user, "Основной", AccountType.MAIN)
    other_income_operation = _create_income_operation(other_user, other_account)
    other_scenario = Scenario.objects.create(
        user=other_user,
        operation=other_income_operation,
        title="Сценарий другого пользователя",
        description="",
        is_active=True,
    )

    main_account = create_account(main_user, "Цели", AccountType.PURPOSE)
    payload = {
        "scenario": str(other_scenario.id),
        "target_account": str(main_account.id),
        "amount": "100.00",
        "order": 1,
    }

    response = api_client.post("/api/scenarios/rules/", payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "scenario" in response.data


def test_add_rule_to_foreign_account_not_allowed(api_client, main_user, other_user, create_account):
    main_account = create_account(main_user, "Основной", AccountType.MAIN)
    main_operation = _create_income_operation(main_user, main_account)
    main_scenario = Scenario.objects.create(
        user=main_user,
        operation=main_operation,
        title="Распределение",
        description="",  # noqa: PIE796
        is_active=True,
    )
    other_account = create_account(other_user, "Чужой счет", AccountType.RESERVE)

    payload = {
        "scenario_id": str(main_scenario.id),
        "target_account": str(other_account.id),
        "amount": "150.00",
        "order": 1,
    }

    response = api_client.post("/api/scenarios/rules/", payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "target_account" in response.data


def test_update_rule(api_client, main_user, create_account):
    main_account = create_account(main_user, "Основной", AccountType.MAIN)
    main_account = create_account(main_user, "Цели", AccountType.PURPOSE)
    main_operation = _create_income_operation(main_user, main_account)
    main_scenario = Scenario.objects.create(
        user=main_user,
        operation=main_operation,
        title="Распределение",
        description="Сценарий по умолчанию",
        is_active=True,
    )
    rule = main_scenario.rules.create(
        target_account=main_account, amount=Decimal("200.00"), order=1
    )

    response = api_client.patch(
        f"/api/scenarios/rules/{rule.id}/", {"amount": "350.00"}, format="json"
    )

    assert response.status_code == status.HTTP_200_OK
    rule.refresh_from_db()
    assert rule.amount == Decimal("350.00")


def test_delete_rule_removes_it(api_client, main_user, main_account, second_account):
    main_operation = _create_income_operation(main_user, main_account)
    main_scenario = Scenario.objects.create(
        user=main_user,
        operation=main_operation,
        title="Распределение",
        description="",
        is_active=True,
    )
    rule = main_scenario.rules.create(
        target_account=second_account, amount=Decimal("100.00"), order=1
    )

    response = api_client.delete(f"/api/scenarios/rules/{rule.id}/")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert main_scenario.rules.count() == 0
