from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from accounts.models import AccountType
from django.utils import timezone
from freezegun import freeze_time
import pytest
from regular_operations.models import (
    RegularOperation,
    RegularOperationPeriodType,
    RegularOperationType,
)
from rest_framework import status
from rest_framework.test import APIClient
from scenarios.models import Scenario

from tests.regular_operations.conftest import (
    DEFAULT_TIME,
    DELETE_SENTINEL,
    MAIN_ACCOUNT_NAME,
    change_value_py_path,
    get_isoformat_with_z,
)


pytestmark = pytest.mark.django_db


@freeze_time(DEFAULT_TIME)
def test_create_income_operation_creates_scenario(api_client, main_user, create_account):
    main_account = create_account(main_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    start_date = timezone.now()
    end_date = start_date + timedelta(days=30)

    payload = {
        "title": "Получение зарплаты",
        "description": "Основной доход",
        "amount": "1000.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }

    response = api_client.post("/api/regular-operations/", payload, format="json")
    assert response.status_code == 201
    # operation = RegularOperation.objects.get()

    response_data = response.json()
    regular_operation_id = response_data.pop("id")
    response_scenario = response_data.pop("scenario")

    assert response_data == {
        "title": "Получение зарплаты",
        "description": "Основной доход",
        "amount": "1000.00",
        "is_active": True,
        "from_account": None,
        "to_account": str(main_account.id),
        "to_account_name": main_account.name,
        "period_interval": 1,
        "period_type": RegularOperationPeriodType.MONTH.value,
        "type": RegularOperationType.INCOME.value,
        "start_date": get_isoformat_with_z(start_date),
        "end_date": get_isoformat_with_z(end_date),
        "created_at": get_isoformat_with_z(DEFAULT_TIME),
        "updated_at": get_isoformat_with_z(DEFAULT_TIME),
    }

    savings_account = create_account(main_user, "Накопления", AccountType.ACCUMULATION)
    fun_account = create_account(main_user, "Развлечения", AccountType.PURPOSE)
    rules_payload = [
        {
            "scenario": response_scenario["id"],
            "target_account": str(savings_account.id),
            "amount": "700.00",
            "order": 1,
        },
        {
            "scenario": response_scenario["id"],
            "target_account": str(fun_account.id),
            "amount": "300.00",
            "order": 2,
        },
    ]
    for rule_payload in rules_payload:
        # TODO: надо сделать урл вида /api/scenarios/<UUID>/rules/
        rule_response = api_client.post("/api/scenarios/rules/", rule_payload, format="json")
        assert rule_response.status_code == status.HTTP_201_CREATED

    detail_response = api_client.get(f"/api/regular-operations/{regular_operation_id}/")
    assert detail_response.status_code == status.HTTP_200_OK
    scenario_data = detail_response.data["scenario"]
    assert scenario_data["title"] == response_scenario["title"]
    assert scenario_data["description"] == response_scenario["description"]
    assert scenario_data["is_active"] is response_scenario["is_active"]
    assert [rule["target_account"] for rule in scenario_data["rules"]] == [
        savings_account.id,
        fun_account.id,
    ]
    assert [Decimal(rule["amount"]) for rule in scenario_data["rules"]] == [
        Decimal("700.00"),
        Decimal("300.00"),
    ]


@freeze_time(DEFAULT_TIME)
def test_create_expense_operation_desnt_creates_scenario(api_client, main_user, create_account):
    main_account = create_account(main_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    start_date = timezone.now()
    end_date = start_date + timedelta(days=30)

    payload = {
        "title": "Траты на кайф",
        "description": "",
        "amount": "1000.00",
        "type": RegularOperationType.EXPENSE,
        "from_account": str(main_account.id),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }

    response = api_client.post("/api/regular-operations/", payload, format="json")
    assert response.status_code == 201

    response_data = response.json()
    response_scenario = response_data.pop("scenario", None)

    assert response_scenario is None

    assert response_data == {
        "title": "Траты на кайф",
        "description": "",
        "amount": "1000.00",
        "is_active": True,
        "to_account": None,
        "from_account": str(main_account.id),
        "from_account_name": main_account.name,
        "period_interval": 1,
        "period_type": RegularOperationPeriodType.MONTH.value,
        "type": RegularOperationType.EXPENSE.value,
        "start_date": get_isoformat_with_z(start_date),
        "end_date": get_isoformat_with_z(end_date),
        "created_at": get_isoformat_with_z(DEFAULT_TIME),
        "updated_at": get_isoformat_with_z(DEFAULT_TIME),
    }


@pytest.mark.parametrize(
    "path,value,expected_field",
    [
        ("from_account", DELETE_SENTINEL, "from_account"),
        ("to_account", "__SPARE_ID__", "to_account"),
    ],
)
def test_expense_operation_validation_errors(
    path, value, expected_field, api_client, main_user, create_account
):
    main_account = create_account(main_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    spare_account = create_account(main_user, "Резерв", AccountType.RESERVE)
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

    response = api_client.post("/api/regular-operations/", payload, format="json")

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
    path, value, expected_field, api_client, main_user, create_account
):
    main_account = create_account(main_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    secondary_account = create_account(main_user, "Запасной", AccountType.RESERVE)
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

    response = api_client.post("/api/regular-operations/", payload, format="json")

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
    start_delta, end_delta, api_client, main_user, create_account
):
    main_account = create_account(main_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
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

    response = api_client.post("/api/regular-operations/", payload, format="json")

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
    path, value, expected_field, api_client, main_user, other_user, create_account
):
    own = create_account(main_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
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

    response = api_client.post("/api/regular-operations/", payload, format="json")
    assert response.status_code == 400
    assert expected_field in response.data


@pytest.mark.parametrize(
    "path, value, expected_field",
    [
        pytest.param("to_account", "__STRANGER_ID__", "to_account", id="income: to stranger"),
    ],
)
def test_income_accounts_must_belong_to_user(
    path, value, expected_field, api_client, main_user, other_user, create_account
):
    own = create_account(main_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
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

    response = api_client.post("/api/regular-operations/", payload, format="json")
    assert response.status_code == 400
    assert expected_field in response.data


@freeze_time(DEFAULT_TIME)
def test_update_without_scenario_rules_keeps_existing_scenario(
    api_client, main_user, create_account
):
    main_account = create_account(main_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    start_date = timezone.now()
    end_date = start_date + timedelta(days=30)

    payload = {
        "title": "Получение зарплаты",
        "description": "Основной доход",
        "amount": "1000.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }

    response = api_client.post("/api/regular-operations/", payload, format="json")
    assert response.status_code == 201

    response_data = response.json()
    regular_operation_id = response_data.pop("id")
    response_scenario = response_data.pop("scenario")

    savings_account = create_account(main_user, "Накопления", AccountType.ACCUMULATION)
    rule_payload = {
        "scenario": response_scenario["id"],
        "target_account": str(savings_account.id),
        "amount": "700.00",
        "order": 1,
    }

    rule_response = api_client.post("/api/scenarios/rules/", rule_payload, format="json")
    assert rule_response.status_code == status.HTTP_201_CREATED

    update_payload = {
        "title": "Изменённая операция",
        "is_active": False,
    }
    response = api_client.patch(
        f"/api/regular-operations/{regular_operation_id}/", update_payload, format="json"
    )

    assert response.status_code == status.HTTP_200_OK

    scenario = Scenario.objects.get(operation=regular_operation_id)
    scenario.refresh_from_db()
    assert scenario.title == response_scenario["title"]
    assert scenario.description == response_scenario["description"]
    assert scenario.is_active is response_scenario["is_active"]
    assert scenario.rules.count() == 1
    assert scenario.rules.first().amount == Decimal("700.00")


@freeze_time(DEFAULT_TIME)
def test_update_with_new_scenario_rules_replaces_previous(api_client, main_user, create_account):
    main_account = create_account(main_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    start_date = timezone.now()
    end_date = start_date + timedelta(days=30)

    payload = {
        "title": "Получение зарплаты",
        "description": "Основной доход",
        "amount": "1000.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }

    response = api_client.post("/api/regular-operations/", payload, format="json")
    assert response.status_code == 201

    response_data = response.json()
    regular_operation_id = response_data.pop("id")
    response_scenario = response_data.pop("scenario")

    savings_account = create_account(main_user, "Накопления", AccountType.ACCUMULATION)
    fun_account = create_account(main_user, "Развлечения", AccountType.PURPOSE)
    rules_payload = [
        {
            "scenario": response_scenario["id"],
            "target_account": str(savings_account.id),
            "amount": "700.00",
            "order": 1,
        },
        {
            "scenario": response_scenario["id"],
            "target_account": str(fun_account.id),
            "amount": "300.00",
            "order": 2,
        },
    ]
    created_rules = []
    for rule_payload in rules_payload:
        # TODO: надо сделать урл вида /api/scenarios/<UUID>/rules/
        rule_response = api_client.post("/api/scenarios/rules/", rule_payload, format="json")
        assert rule_response.status_code == status.HTTP_201_CREATED
        created_rules.append(rule_response.data)

    for rule in created_rules:
        delete_response = api_client.delete(f"/api/scenarios/rules/{rule['id']}/")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    vacation_account = create_account(main_user, "Отпуск", AccountType.PURPOSE)
    new_rules = [
        {
            "scenario": response_scenario["id"],
            "target_account": str(vacation_account.id),
            "amount": "100.00",
            "order": 1,
        },
    ]
    for rule_payload in new_rules:
        # TODO: надо сделать урл вида /api/scenarios/<UUID>/rules/
        rule_response = api_client.post("/api/scenarios/rules/", rule_payload, format="json")
        assert rule_response.status_code == status.HTTP_201_CREATED

    detail_response = api_client.get(f"/api/regular-operations/{regular_operation_id}/")
    assert detail_response.status_code == status.HTTP_200_OK
    assert [rule["target_account"] for rule in detail_response.data["scenario"]["rules"]] == [
        vacation_account.id
    ]
    assert [Decimal(rule["amount"]) for rule in detail_response.data["scenario"]["rules"]] == [
        Decimal("100.00")
    ]


@freeze_time(DEFAULT_TIME)
def test_cannot_change_operation_type(api_client, main_user, create_account):
    main_account = create_account(main_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    start_date = timezone.now()
    end_date = start_date + timedelta(days=30)

    payload = {
        "title": "Получение зарплаты",
        "description": "Основной доход",
        "amount": "1000.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }

    response = api_client.post("/api/regular-operations/", payload, format="json")
    assert response.status_code == 201

    response_data = response.json()
    regular_operation_id = response_data.pop("id")

    assert response.status_code == 201, response_data

    response = api_client.patch(
        f"/api/regular-operations/{regular_operation_id}/",
        {"type": RegularOperationType.EXPENSE},
        format="json",
    )

    assert response.status_code == 400
    assert "type" in response.data
    operation = RegularOperation.objects.get(id=regular_operation_id)
    operation.refresh_from_db()
    assert operation.type == RegularOperationType.INCOME


@freeze_time(DEFAULT_TIME)
def test_delete_operation_removes_scenario(api_client, main_user, create_account):
    main_account = create_account(main_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    start_date = timezone.now()
    end_date = start_date + timedelta(days=30)

    payload = {
        "title": "Получение зарплаты",
        "description": "Основной доход",
        "amount": "1000.00",
        "type": RegularOperationType.INCOME,
        "to_account": str(main_account.id),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }

    response = api_client.post("/api/regular-operations/", payload, format="json")
    assert response.status_code == 201

    response_data = response.json()
    regular_operation_id = response_data.pop("id")

    response = api_client.delete(f"/api/regular-operations/{regular_operation_id}/")

    assert response.status_code == 204
    assert RegularOperation.objects.count() == 0
    assert Scenario.objects.count() == 0


def test_access_is_limited_to_authenticated_user(api_client, main_user, other_user, create_account):
    unauthenticated_client = APIClient()
    response = unauthenticated_client.get("/api/regular-operations/")
    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    )

    main_account = create_account(main_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    other_account = create_account(other_user, MAIN_ACCOUNT_NAME, AccountType.MAIN)
    now = timezone.now()

    RegularOperation.objects.create(
        user=main_user,
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

    response = api_client.get("/api/regular-operations/")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["title"] == "Моя операция"
