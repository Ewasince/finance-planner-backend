from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Final

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import AccountType
from regular_operations.models import (
    RegularOperation,
    RegularOperationPeriodType,
    RegularOperationType,
)
from scenarios.models import PaymentScenario

from .conftest import (
    DEFAULT_SCENARIO_DATA,
    build_regular_operation_payload,
    build_scenario_data,
    build_scenario_rule_data,
)


pytestmark = pytest.mark.django_db

MAIN_ACCOUNT_NAME: Final[str] = "Основной счёт"


def _remove_from_account(payload: dict[str, object], accounts: dict[str, object]) -> None:
    payload.pop("from_account", None)


def _set_to_account(payload: dict[str, object], accounts: dict[str, object]) -> None:
    payload["to_account"] = str(accounts["to"].id)


def _set_scenario_rules(
    payload: dict[str, object], accounts: dict[str, object]
) -> None:
    payload["scenario_rules"] = [
        build_scenario_rule_data(
            target_account=str(accounts["to"].id),
            amount="50.00",
            order=1,
        )
    ]


def _set_invalid_scenario(payload: dict[str, object], accounts: dict[str, object]) -> None:
    payload["scenario"] = {"title": "Недопустимый сценарий"}


def _remove_to_account(payload: dict[str, object], accounts: dict[str, object]) -> None:
    payload.pop("to_account", None)


def _set_from_account(payload: dict[str, object], accounts: dict[str, object]) -> None:
    payload["from_account"] = str(accounts["from"].id)


def _foreign_expense_payload(accounts: dict[str, object], now: datetime) -> dict[str, object]:
    return build_regular_operation_payload(
        title="Покупка",
        description="Чужой счёт расход",
        amount="50.00",
        type=RegularOperationType.EXPENSE,
        from_account=str(accounts["stranger"].id),
        start_date=now,
        end_date=now + timedelta(days=7),
        period_type=RegularOperationPeriodType.WEEK,
        period_interval=1,
        scenario_rules=[],
    )


def _foreign_income_payload(accounts: dict[str, object], now: datetime) -> dict[str, object]:
    return build_regular_operation_payload(
        title="Чужие средства",
        description="Попытка зачисления",
        amount="120.00",
        type=RegularOperationType.INCOME,
        to_account=str(accounts["stranger"].id),
        start_date=now,
        end_date=now + timedelta(days=30),
        period_type=RegularOperationPeriodType.MONTH,
        period_interval=1,
        scenario_rules=[],
    )


def _foreign_rule_payload(accounts: dict[str, object], now: datetime) -> dict[str, object]:
    return build_regular_operation_payload(
        title="Проверка правил",
        description="Неверный целевой счёт",
        amount="500.00",
        type=RegularOperationType.INCOME,
        to_account=str(accounts["own"].id),
        start_date=now,
        end_date=now + timedelta(days=30),
        period_type=RegularOperationPeriodType.MONTH,
        period_interval=1,
        scenario_rules=[
            build_scenario_rule_data(
                target_account=str(accounts["stranger"].id),
                amount="500.00",
                order=1,
            )
        ],
    )


def test_create_income_operation_creates_scenario(
    api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    savings_account = create_account(user, "Накопления", AccountType.ACCUMULATION)
    fun_account = create_account(user, "Развлечения", AccountType.PURPOSE)
    now = timezone.now()

    first_rule_amount = Decimal("700.00")
    second_rule_amount = Decimal("300.00")
    payload = build_regular_operation_payload(
        to_account=str(main_account.id),
        start_date=now,
        end_date=now + timedelta(days=30),
        scenario_rules=[
            build_scenario_rule_data(
                target_account=str(savings_account.id),
                amount=str(first_rule_amount),
                order=1,
            ),
            build_scenario_rule_data(
                target_account=str(fun_account.id),
                amount=str(second_rule_amount),
                order=2,
            ),
        ],
    )

    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == 201
    operation = RegularOperation.objects.get()
    scenario = operation.scenario
    assert scenario is not None
    assert scenario.title == DEFAULT_SCENARIO_DATA["title"]
    assert scenario.description == DEFAULT_SCENARIO_DATA["description"]
    assert scenario.is_active is DEFAULT_SCENARIO_DATA["is_active"]
    assert scenario.title != operation.title

    rules = list(scenario.rules.order_by("order"))
    assert len(rules) == 2
    assert [rule.target_account_id for rule in rules] == [
        savings_account.id,
        fun_account.id,
    ]
    assert [rule.amount for rule in rules] == [first_rule_amount, second_rule_amount]


@pytest.mark.parametrize(
    "modifier,expected_field",
    [
        (_remove_from_account, "from_account"),
        (_set_to_account, "to_account"),
        (_set_scenario_rules, "scenario_rules"),
        (_set_invalid_scenario, "scenario"),
    ],
)
def test_expense_operation_validation_errors(
    modifier, expected_field, api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    spare_account = create_account(user, "Резерв", AccountType.RESERVE)
    now = timezone.now()
    payload = build_regular_operation_payload(
        title="Абонемент в спортзал",
        description="Фитнес",
        amount="150.00",
        type=RegularOperationType.EXPENSE,
        from_account=str(main_account.id),
        start_date=now,
        end_date=now + timedelta(days=30),
        period_type=RegularOperationPeriodType.MONTH,
        period_interval=1,
        scenario_rules=[],
    )

    modifier(payload, {"to": spare_account})

    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == 400
    assert expected_field in response.data


@pytest.mark.parametrize(
    "modifier,expected_field",
    [
        (_remove_to_account, "to_account"),
        (_set_from_account, "from_account"),
    ],
)
def test_income_operation_validation_errors(
    modifier, expected_field, api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    secondary_account = create_account(user, "Запасной", AccountType.RESERVE)
    now = timezone.now()
    payload = build_regular_operation_payload(
        title="Фриланс",
        description="Дополнительный доход",
        amount="200.00",
        type=RegularOperationType.INCOME,
        to_account=str(main_account.id),
        start_date=now,
        end_date=now + timedelta(days=30),
        period_type=RegularOperationPeriodType.MONTH,
        period_interval=1,
        scenario_rules=[],
    )

    modifier(payload, {"from": secondary_account})

    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == 400
    assert expected_field in response.data


@pytest.mark.parametrize(
    "start_delta,end_delta",
    [
        (timedelta(days=5), timedelta(days=0)),
        (timedelta(days=0), timedelta(days=0)),
    ],
)
def test_end_date_must_be_after_start_date(
    start_delta, end_delta, api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    now = timezone.now()
    payload = build_regular_operation_payload(
        title="Курс",
        description="Краткосрочная подработка",
        amount="300.00",
        type=RegularOperationType.INCOME,
        to_account=str(main_account.id),
        start_date=now + start_delta,
        end_date=now + end_delta,
        period_type=RegularOperationPeriodType.MONTH,
        period_interval=1,
        scenario_rules=[],
    )

    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == 400
    assert "end_date" in response.data


@pytest.mark.parametrize(
    "payload_factory,expected_field",
    [
        (_foreign_expense_payload, "from_account"),
        (_foreign_income_payload, "to_account"),
        (_foreign_rule_payload, "scenario_rules"),
    ],
)
def test_accounts_must_belong_to_user(
    payload_factory, expected_field, api_client, user, other_user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    stranger_account = create_account(other_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    now = timezone.now()

    payload = payload_factory({"own": main_account, "stranger": stranger_account}, now)
    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == 400
    assert expected_field in response.data


def test_update_without_scenario_rules_keeps_existing_scenario(
    api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    savings_account = create_account(user, "Накопления", AccountType.ACCUMULATION)
    now = timezone.now()
    scenario_data = build_scenario_data(
        title="Сценарий",
        description="Отдельное описание",
        is_active=False,
    )
    scenario_rule_amount = Decimal("1000.00")
    create_payload = build_regular_operation_payload(
        title="Зарплата",
        description="Основная",
        amount="1000.00",
        type=RegularOperationType.INCOME,
        to_account=str(main_account.id),
        start_date=now,
        end_date=now + timedelta(days=30),
        period_type=RegularOperationPeriodType.MONTH,
        period_interval=1,
        scenario=scenario_data,
        scenario_rules=[
            build_scenario_rule_data(
                target_account=str(savings_account.id),
                amount=str(scenario_rule_amount),
                order=1,
            )
        ],
    )
    create_response = api_client.post(list_url, create_payload, format="json")
    assert create_response.status_code == 201, create_response.data
    operation = RegularOperation.objects.get(user=user, title=create_payload["title"])
    detail_url = reverse("regular-operation-detail", args=[operation.id])
    update_payload = {
        "title": "Изменённая операция",
        "is_active": False,
    }
    response = api_client.patch(detail_url, update_payload, format="json")

    assert response.status_code == 200
    operation.refresh_from_db()
    scenario = operation.scenario
    scenario.refresh_from_db()

    assert scenario.title == scenario_data["title"]
    assert scenario.description == scenario_data["description"]
    assert scenario.is_active is scenario_data["is_active"]
    assert scenario.rules.count() == 1
    assert scenario.rules.first().amount == scenario_rule_amount


def test_update_with_new_scenario_rules_replaces_previous(
    api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    savings_account = create_account(user, "Сбережения", AccountType.ACCUMULATION)
    vacation_account = create_account(user, "Отпуск", AccountType.PURPOSE)
    now = timezone.now()
    first_rule_amount = Decimal("600.00")
    second_rule_amount = Decimal("300.00")
    create_payload = build_regular_operation_payload(
        title="Доход",
        description="Первоначальный",
        amount="900.00",
        type=RegularOperationType.INCOME,
        to_account=str(main_account.id),
        start_date=now,
        end_date=now + timedelta(days=30),
        period_type=RegularOperationPeriodType.MONTH,
        period_interval=1,
        scenario_rules=[
            build_scenario_rule_data(
                target_account=str(savings_account.id),
                amount=str(first_rule_amount),
                order=1,
            ),
            build_scenario_rule_data(
                target_account=str(vacation_account.id),
                amount=str(second_rule_amount),
                order=2,
            ),
        ],
    )
    create_response = api_client.post(list_url, create_payload, format="json")
    assert create_response.status_code == 201, create_response.data
    operation = RegularOperation.objects.get(user=user, title=create_payload["title"])
    detail_url = reverse("regular-operation-detail", args=[operation.id])
    update_rule_amount = Decimal("900.00")
    update_payload = {
        "scenario_rules": [
            build_scenario_rule_data(
                target_account=str(vacation_account.id),
                amount=str(update_rule_amount),
                order=1,
            )
        ],
    }
    response = api_client.patch(detail_url, update_payload, format="json")

    assert response.status_code == 200
    scenario = RegularOperation.objects.get(id=operation.id).scenario
    rules = list(scenario.rules.order_by("order"))
    assert len(rules) == 1
    assert rules[0].target_account_id == vacation_account.id
    assert rules[0].amount == update_rule_amount


def test_cannot_change_operation_type(api_client, user, list_url, create_account):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    now = timezone.now()
    create_payload = build_regular_operation_payload(
        title="Зарплата",
        description="",
        amount="800.00",
        type=RegularOperationType.INCOME,
        to_account=str(main_account.id),
        start_date=now,
        end_date=now + timedelta(days=30),
        period_type=RegularOperationPeriodType.MONTH,
        period_interval=1,
        scenario_rules=[],
    )
    create_response = api_client.post(list_url, create_payload, format="json")
    assert create_response.status_code == 201, create_response.data
    operation = RegularOperation.objects.get(user=user, title=create_payload["title"])
    detail_url = reverse("regular-operation-detail", args=[operation.id])
    response = api_client.patch(
        detail_url,
        {"type": RegularOperationType.EXPENSE},
        format="json",
    )

    assert response.status_code == 400
    assert "type" in response.data
    operation.refresh_from_db()
    assert operation.type == RegularOperationType.INCOME
    assert PaymentScenario.objects.filter(operation=operation).exists()


def test_delete_operation_removes_scenario(api_client, user, list_url, create_account):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    now = timezone.now()
    payload = build_regular_operation_payload(
        title="Повторяющийся доход",
        description="",
        amount="750.00",
        type=RegularOperationType.INCOME,
        to_account=str(main_account.id),
        start_date=now,
        end_date=now + timedelta(days=30),
        period_type=RegularOperationPeriodType.MONTH,
        period_interval=1,
        scenario_rules=[],
    )
    create_response = api_client.post(list_url, payload, format="json")
    assert create_response.status_code == 201, create_response.data
    operation = RegularOperation.objects.get(user=user, title=payload["title"])
    detail_url = reverse("regular-operation-detail", args=[operation.id])
    response = api_client.delete(detail_url)

    assert response.status_code == 204
    assert RegularOperation.objects.count() == 0
    assert PaymentScenario.objects.count() == 0


def test_access_is_limited_to_authenticated_user(api_client, user, other_user, list_url, create_account):
    unauthenticated_client = APIClient()
    response = unauthenticated_client.get(list_url)
    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    )

    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    other_account = create_account(other_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    now = timezone.now()

    RegularOperation.objects.create(
        user=user,
        title="Моя операция",
        description="",
        amount=Decimal("100.00"),
        type=RegularOperationType.EXPENSE,
        from_account=main_account,
        start_date=now,
        end_date=now + timedelta(days=10),
        period_type=RegularOperationPeriodType.WEEK,
        period_interval=1,
        is_active=True,
    )

    RegularOperation.objects.create(
        user=other_user,
        title="Чужая операция",
        description="",
        amount=Decimal("200.00"),
        type=RegularOperationType.EXPENSE,
        from_account=other_account,
        start_date=now,
        end_date=now + timedelta(days=5),
        period_type=RegularOperationPeriodType.WEEK,
        period_interval=1,
        is_active=True,
    )

    response = api_client.get(list_url)
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["title"] == "Моя операция"
