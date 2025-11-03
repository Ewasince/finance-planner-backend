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

# FIXME: заменить на автоматическое создание сценария при создании дохода
# def test_create_scenario_for_operation(api_client, main_user, create_account):
#     main_account = create_account(main_user, "Основной", AccountType.MAIN)
#     main_operation = _create_income_operation(main_user, main_account)
#
#     payload = {
#         "operation": str(main_operation.id),
#         "title": "План распределения",
#         "description": "Отдельный сценарий",
#         "is_active": False,
#     }
#
#     response = api_client.post("/api/scenarios/", payload, format="json")
#
#     assert response.status_code == status.HTTP_201_CREATED
#     scenario = Scenario.objects.get(operation=main_operation)
#     assert scenario.title == payload["title"]
#     assert response.data["operation"] == str(main_operation.id)
#     assert response.data["rules"] == []


def test_update_scenario(api_client, main_user, create_account):
    main_account = create_account(main_user, "Основной", AccountType.MAIN)
    main_operation = _create_income_operation(main_user, main_account)
    main_scenario = Scenario.objects.create(
        user=main_user,
        operation=main_operation,
        title="Старое название",
        description="",
        is_active=True,
    )

    payload = {"title": "Новое название", "description": "Обновлённое описание"}

    response = api_client.patch(f"/api/scenarios/{main_scenario.id}/", payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    main_scenario.refresh_from_db()
    assert main_scenario.title == payload["title"]
    assert main_scenario.description == payload["description"]
    assert response.data["title"] == payload["title"]


def test_retrieve_scenario_includes_rules(api_client, main_user, create_account):
    main_account = create_account(main_user, "Основной", AccountType.MAIN)
    target_account = create_account(main_user, "Цели", AccountType.PURPOSE)
    operation = _create_income_operation(main_user, main_account)
    scenario = Scenario.objects.create(
        user=main_user,
        operation=operation,
        title="Распределение",
        description="",
        is_active=True,
    )
    scenario.rules.create(target_account=target_account, amount=Decimal("150.00"), order=1)

    response = api_client.get(f"/api/scenarios/{scenario.id}/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["rules"]) == 1
    assert response.data["rules"][0]["target_account"] == target_account.id
