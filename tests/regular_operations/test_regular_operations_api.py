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
from rest_framework.test import APIClient
from scenarios.models import PaymentScenario

from tests.regular_operations.conftest import (
    DELETE_SENTINEL,
    MAIN_ACCOUNT_NAME,
    change_value_py_path,
)


pytestmark = pytest.mark.django_db


def test_create_income_operation_creates_scenario(api_client, user, list_url, create_account):
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
    }

    response = api_client.post(list_url, payload, format="json")
    assert response.status_code == 201
    operation = RegularOperation.objects.get()

    scenario_payload = {
        "operation_id": str(operation.id),
        "title": "План распределения зарплаты",
        "description": "Настраиваемый сценарий",
        "is_active": False,
    }
    scenario_response = api_client.post(reverse("scenario-list"), scenario_payload, format="json")
    assert scenario_response.status_code == status.HTTP_201_CREATED

    rules_payload = [
        {
            "scenario_id": scenario_response.data["id"],
            "target_account": str(savings_account.id),
            "amount": "700.00",
            "order": 1,
        },
        {
            "scenario_id": scenario_response.data["id"],
            "target_account": str(fun_account.id),
            "amount": "300.00",
            "order": 2,
        },
    ]
    for rule_payload in rules_payload:
        rule_response = api_client.post(reverse("scenario-rule-list"), rule_payload, format="json")
        assert rule_response.status_code == status.HTTP_201_CREATED

    detail_url = reverse("regular-operation-detail", args=[operation.id])
    detail_response = api_client.get(detail_url)
    assert detail_response.status_code == status.HTTP_200_OK
    scenario_data = detail_response.data["scenario"]
    assert scenario_data["title"] == scenario_payload["title"]
    assert scenario_data["description"] == scenario_payload["description"]
    assert scenario_data["is_active"] is scenario_payload["is_active"]
    assert [rule["target_account_id"] for rule in scenario_data["rules"]] == [
        str(savings_account.id),
        str(fun_account.id),
    ]
    assert [Decimal(rule["amount"]) for rule in scenario_data["rules"]] == [
        Decimal("700.00"),
        Decimal("300.00"),
    ]


def test_create_income_operation_without_scenario_uses_defaults(
    api_client, user, list_url, create_account
):
    main_account = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    now = timezone.now()

    payload = {
        "title": "Процент по вкладу",
        "description": "Ежемесячный доход",
        "amount": "500.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }

    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    operation = RegularOperation.objects.get()
    with pytest.raises(PaymentScenario.DoesNotExist):
        _ = operation.scenario
    assert PaymentScenario.objects.count() == 0


# ——— validation: EXPENSE ———
@pytest.mark.parametrize(
    "path,value,expected_field",
    [
        ("from_account", DELETE_SENTINEL, "from_account"),
        ("to_account", "__SPARE_ID__", "to_account"),
    ],
)
def test_expense_operation_validation_errors(
    path, value, expected_field, api_client, user, list_url, create_account
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

    # подготавливаем динамическое значение при необходимости
    if value == "__SPARE_ID__":
        value = str(spare_account.id)

    change_value_py_path(payload, path, value)

    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == 400
    assert expected_field in response.data


# ——— validation: INCOME ———
@pytest.mark.parametrize(
    "path,value,expected_field",
    [
        ("to_account", DELETE_SENTINEL, "to_account"),
        ("from_account", "__SECONDARY_ID__", "from_account"),
    ],
)
def test_income_operation_validation_errors(
    path, value, expected_field, api_client, user, list_url, create_account
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

    if value == "__SECONDARY_ID__":
        value = str(secondary_account.id)

    change_value_py_path(payload, path, value)

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
    payload = {
        "title": "Курс",
        "description": "Краткосрочная подработка",
        "amount": "300.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": (now + start_delta).isoformat(),
        "end_date": (now + end_delta).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }

    response = api_client.post(list_url, payload, format="json")

    assert response.status_code == 400
    assert "end_date" in response.data


@pytest.mark.parametrize(
    "path, value, expected_field",
    [
        pytest.param(
            "from_account", "__STRANGER_ID__", "from_account", id="expense: from stranger"
        ),
    ],
)
def test_expense_accounts_must_belong_to_user(
    path, value, expected_field, api_client, user, other_user, list_url, create_account
):
    own = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    stranger = create_account(other_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    now = timezone.now()

    payload = {
        "title": "Покупка",
        "description": "Чужой счёт расход",
        "amount": "50.00",
        "type": RegularOperationType.EXPENSE,
        "from_account": str(own.id),
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=7)).isoformat(),
        "period_type": RegularOperationPeriodType.WEEK,
        "period_interval": 1,
        "is_active": True,
    }

    if value == "__STRANGER_ID__":
        value = str(stranger.id)

    change_value_py_path(payload, path, value)

    response = api_client.post(list_url, payload, format="json")
    assert response.status_code == 400
    assert expected_field in response.data


@pytest.mark.parametrize(
    "path, value, expected_field",
    [
        pytest.param("to_account", "__STRANGER_ID__", "to_account", id="income: to stranger"),
    ],
)
def test_income_accounts_must_belong_to_user(
    path, value, expected_field, api_client, user, other_user, list_url, create_account
):
    own = create_account(user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    stranger = create_account(other_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    now = timezone.now()

    payload = {
        "title": "Доход",
        "description": "Проверка принадлежности счетов",
        "amount": "120.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(own.id),
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=30)).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }

    if value == "__STRANGER_ID__":
        value = str(stranger.id)

    change_value_py_path(payload, path, value)

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
    }
    create_response = api_client.post(list_url, create_payload, format="json")
    assert create_response.status_code == 201, create_response.data
    operation = RegularOperation.objects.get(user=user, title=create_payload["title"])

    scenario_payload = {
        "operation_id": str(operation.id),
        "title": "Сценарий",
        "description": "Отдельное описание",
        "is_active": False,
    }
    scenario_response = api_client.post(reverse("scenario-list"), scenario_payload, format="json")
    assert scenario_response.status_code == status.HTTP_201_CREATED
    rule_payload = {
        "scenario_id": scenario_response.data["id"],
        "target_account": str(savings_account.id),
        "amount": "1000.00",
        "order": 1,
    }
    rule_response = api_client.post(reverse("scenario-rule-list"), rule_payload, format="json")
    assert rule_response.status_code == status.HTTP_201_CREATED

    detail_url = reverse("regular-operation-detail", args=[operation.id])
    update_payload = {
        "title": "Изменённая операция",
        "is_active": False,
    }
    response = api_client.patch(detail_url, update_payload, format="json")

    assert response.status_code == 200
    scenario = PaymentScenario.objects.get(operation=operation)
    scenario.refresh_from_db()
    assert scenario.title == scenario_payload["title"]
    assert scenario.description == scenario_payload["description"]
    assert scenario.is_active is scenario_payload["is_active"]
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
    }
    create_response = api_client.post(list_url, create_payload, format="json")
    assert create_response.status_code == 201, create_response.data
    operation = RegularOperation.objects.get(user=user, title=create_payload["title"])
    scenario_response = api_client.post(
        reverse("scenario-list"),
        {
            "operation_id": str(operation.id),
            "title": "Правила",
            "description": "",
            "is_active": True,
        },
        format="json",
    )
    assert scenario_response.status_code == status.HTTP_201_CREATED
    scenario_id = scenario_response.data["id"]

    initial_rules = [
        {
            "scenario_id": scenario_id,
            "target_account": str(savings_account.id),
            "amount": "600.00",
            "order": 1,
        },
        {
            "scenario_id": scenario_id,
            "target_account": str(vacation_account.id),
            "amount": "300.00",
            "order": 2,
        },
    ]
    created_rules = []
    for rule_payload in initial_rules:
        rule_response = api_client.post(reverse("scenario-rule-list"), rule_payload, format="json")
        assert rule_response.status_code == status.HTTP_201_CREATED
        created_rules.append(rule_response.data)

    for rule in created_rules:
        delete_response = api_client.delete(reverse("scenario-rule-detail", args=[rule["id"]]))
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    new_rules = [
        {
            "scenario_id": scenario_id,
            "target_account": str(vacation_account.id),
            "amount": "900.00",
            "order": 1,
        }
    ]
    for rule_payload in new_rules:
        rule_response = api_client.post(reverse("scenario-rule-list"), rule_payload, format="json")
        assert rule_response.status_code == status.HTTP_201_CREATED

    scenario_detail = api_client.get(reverse("scenario-detail", args=[scenario_id]))
    assert scenario_detail.status_code == status.HTTP_200_OK
    assert [rule["target_account_id"] for rule in scenario_detail.data["rules"]] == [
        str(vacation_account.id)
    ]
    assert [Decimal(rule["amount"]) for rule in scenario_detail.data["rules"]] == [
        Decimal("900.00")
    ]


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
    scenario_response = api_client.post(
        reverse("scenario-list"),
        {
            "operation_id": str(operation.id),
            "title": "Сценарий",
            "description": "",
            "is_active": True,
        },
        format="json",
    )
    assert scenario_response.status_code == status.HTTP_201_CREATED
    detail_url = reverse("regular-operation-detail", args=[operation.id])
    response = api_client.delete(detail_url)

    assert response.status_code == 204
    assert RegularOperation.objects.count() == 0
    assert PaymentScenario.objects.count() == 0


def test_access_is_limited_to_authenticated_user(
    api_client, user, other_user, list_url, create_account
):
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
