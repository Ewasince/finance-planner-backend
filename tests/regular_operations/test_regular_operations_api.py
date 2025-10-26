from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Final

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Account, AccountType
from regular_operations.models import (
    RegularOperation,
    RegularOperationPeriodType,
    RegularOperationType,
)
from scenarios.models import PaymentScenario


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user(
        username="owner",
        email="owner@example.com",
        password="password123",
    )


@pytest.fixture
def other_user():
    return get_user_model().objects.create_user(
        username="stranger",
        email="stranger@example.com",
        password="password123",
    )


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def list_url():
    return reverse("regular-operation-list")


@pytest.fixture
def create_account():
    def _create_account(user, name: str, account_type: AccountType):
        return Account.objects.create(user=user, name=name, type=account_type)

    return _create_account

MAIN_ACCOUNT_NAME: Final[str] = "Основной счёт"


def test_create_income_operation_creates_scenario(
    api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    savings_account = create_account(user, "Накопления", AccountType.ACCUMULATION)
    fun_account = create_account(user, "Развлечения", AccountType.PURPOSE)
    now = timezone.now()

    payload = {
        "title": "Получение зарплаты",
        "description": "Основной доход",
        "amount": "1000.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
        "scenario": {
            "title": "План распределения зарплаты",
            "description": "Настраиваемый сценарий",
            "is_active": False,
        },
        "scenario_rules": [
            {
                "target_account": str(savings_account.id),
                "amount": "700.00",
                "order": 1,
            },
            {
                "target_account": str(fun_account.id),
                "amount": "300.00",
                "order": 2,
            },
        ],
    }

    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == 201
    operation = RegularOperation.objects.get()
    scenario = operation.scenario
    assert scenario is not None
    assert scenario.title == payload["scenario"]["title"]
    assert scenario.description == payload["scenario"]["description"]
    assert scenario.is_active is False
    assert scenario.title != operation.title

    rules = list(scenario.rules.order_by("order"))
    assert len(rules) == 2
    assert [rule.target_account_id for rule in rules] == [
        savings_account.id,
        fun_account.id,
    ]
    assert [rule.amount for rule in rules] == [Decimal("700.00"), Decimal("300.00")]


@pytest.mark.parametrize(
    "modifier,expected_field",
    [
        (lambda data, accounts: data.pop("from_account"), "from_account"),
        (
            lambda data, accounts: data.update({
                "to_account": str(accounts["to"].id),
            }),
            "to_account",
        ),
        (
            lambda data, accounts: data.update({
                "scenario_rules": [
                    {
                        "target_account": str(accounts["to"].id),
                        "amount": "50.00",
                        "order": 1,
                    }
                ],
            }),
            "scenario_rules",
        ),
        (
            lambda data, accounts: data.update({
                "scenario": {"title": "Недопустимый сценарий"},
            }),
            "scenario",
        ),
    ],
)
def test_expense_operation_validation_errors(
    modifier, expected_field, api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    spare_account = create_account(user, "Резерв", AccountType.RESERVE)
    now = timezone.now()
    payload = {
        "title": "Абонемент в спортзал",
        "description": "Фитнес",
        "amount": "150.00",
        "type": RegularOperationType.EXPENSE,
        "from_account": str(main_account.id),
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }

    modifier(payload, {"to": spare_account})

    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == 400
    assert expected_field in response.data


@pytest.mark.parametrize(
    "modifier,expected_field",
    [
        (lambda data, accounts: data.pop("to_account"), "to_account"),
        (
            lambda data, accounts: data.update({
                "from_account": str(accounts["from"].id),
            }),
            "from_account",
        ),
    ],
)
def test_income_operation_validation_errors(
    modifier, expected_field, api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    secondary_account = create_account(user, "Запасной", AccountType.RESERVE)
    now = timezone.now()
    payload = {
        "title": "Фриланс",
        "description": "Дополнительный доход",
        "amount": "200.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }

    modifier(payload, {"from": secondary_account})

    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == 400
    assert expected_field in response.data


@pytest.mark.parametrize(
    "start_shift,end_shift",
    [
        (timedelta(days=3), timedelta(days=2)),
        (timedelta(days=5), timedelta(days=4)),
    ],
)
def test_end_date_must_be_after_start_date(
    start_shift, end_shift, api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    now = timezone.now()
    payload = {
        "title": "Курс",
        "description": "Краткосрочная подработка",
        "amount": "300.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": (now + start_shift).isoformat(),
        "end_date": (now + end_shift).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }

    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == 400
    assert "end_date" in response.data


@pytest.mark.parametrize(
    "payload_factory,expected_field",
    [
        (
            lambda accounts, now: {
                "title": "Покупка",
                "description": "Чужой счёт расход",
                "amount": "50.00",
                "type": RegularOperationType.EXPENSE,
                "from_account": str(accounts["stranger"].id),
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=7)).isoformat(),
                "period_type": RegularOperationPeriodType.WEEK,
                "period_interval": 1,
                "is_active": True,
            },
            "from_account",
        ),
        (
            lambda accounts, now: {
                "title": "Чужие средства",
                "description": "Попытка зачисления",
                "amount": "120.00",
                "type": RegularOperationType.INCOME,
                "to_account": str(accounts["stranger"].id),
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=30)).isoformat(),
                "period_type": RegularOperationPeriodType.MONTH,
                "period_interval": 1,
                "is_active": True,
            },
            "to_account",
        ),
        (
            lambda accounts, now: {
                "title": "Проверка правил",
                "description": "Неверный целевой счёт",
                "amount": "500.00",
                "type": RegularOperationType.INCOME,
                "to_account": str(accounts["own_main"].id),
                "start_date": now.isoformat(),
                "end_date": (now + timedelta(days=30)).isoformat(),
                "period_type": RegularOperationPeriodType.MONTH,
                "period_interval": 1,
                "is_active": True,
                "scenario_rules": [
                    {
                        "target_account": str(accounts["stranger"].id),
                        "amount": "500.00",
                        "order": 1,
                    }
                ],
            },
            "scenario_rules",
        ),
    ],
)
def test_accounts_must_belong_to_user(
    payload_factory, expected_field, api_client, user, other_user, list_url, create_account
):
    accounts = {
        "own_main": create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN),
        "stranger": create_account(other_user, MAIN_ACCOUNT_NAME, AccountType.MAIN),
    }
    now = timezone.now()

    payload = payload_factory(accounts, now)
    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == 400
    assert expected_field in response.data


def test_update_without_scenario_rules_keeps_existing_scenario(
    api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    savings_account = create_account(user, "Накопления", AccountType.ACCUMULATION)
    now = timezone.now()
    create_payload = {
        "title": "Зарплата",
        "description": "Основная",
        "amount": "1000.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
        "scenario": {
            "title": "Сценарий",
            "description": "Отдельное описание",
            "is_active": False,
        },
        "scenario_rules": [
            {
                "target_account": str(savings_account.id),
                "amount": "1000.00",
                "order": 1,
            }
        ],
    }
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

    assert scenario.title == create_payload["scenario"]["title"]
    assert scenario.description == create_payload["scenario"]["description"]
    assert scenario.is_active is create_payload["scenario"]["is_active"]
    assert scenario.rules.count() == 1
    assert scenario.rules.first().amount == Decimal("1000.00")


def test_update_with_new_scenario_rules_replaces_previous(
    api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    savings_account = create_account(user, "Сбережения", AccountType.ACCUMULATION)
    vacation_account = create_account(user, "Отпуск", AccountType.PURPOSE)
    now = timezone.now()
    create_payload = {
        "title": "Доход",
        "description": "Первоначальный",
        "amount": "900.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
        "scenario_rules": [
            {
                "target_account": str(savings_account.id),
                "amount": "600.00",
                "order": 1,
            },
            {
                "target_account": str(vacation_account.id),
                "amount": "300.00",
                "order": 2,
            },
        ],
    }
    create_response = api_client.post(list_url, create_payload, format="json")
    assert create_response.status_code == 201, create_response.data
    operation = RegularOperation.objects.get(user=user, title=create_payload["title"])
    detail_url = reverse("regular-operation-detail", args=[operation.id])
    update_payload = {
        "scenario_rules": [
            {
                "target_account": str(vacation_account.id),
                "amount": "900.00",
                "order": 1,
            }
        ],
    }
    response = api_client.patch(detail_url, update_payload, format="json")

    assert response.status_code == 200
    scenario = RegularOperation.objects.get(id=operation.id).scenario
    rules = list(scenario.rules.order_by("order"))
    assert len(rules) == 1
    assert rules[0].target_account_id == vacation_account.id
    assert rules[0].amount == Decimal("900.00")


def test_cannot_change_operation_type(api_client, user, list_url, create_account):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    now = timezone.now()
    create_payload = {
        "title": "Зарплата",
        "description": "",
        "amount": "800.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }
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
    payload = {
        "title": "Повторяющийся доход",
        "description": "",
        "amount": "750.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }
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
