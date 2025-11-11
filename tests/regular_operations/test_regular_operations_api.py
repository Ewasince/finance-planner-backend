from __future__ import annotations

from decimal import Decimal

from accounts.models import AccountType
from constants import DEFAULT_INCOME_TITLE
from core.bootstrap import (
    DEFAULT_TIME,
    DEFAULT_TIME_WITH_OFFSET,
    MAIN_ACCOUNT_UUID,
    OTHER_ACCOUNT_UUID,
    SECOND_ACCOUNT_UUID,
)
from freezegun import freeze_time
import pytest
from regular_operations.models import (
    RegularOperation,
    RegularOperationPeriodType,
    RegularOperationType,
)
from rest_framework import status
from rest_framework.test import APIClient
from scenarios.models import Scenario, ScenarioRule


pytestmark = pytest.mark.django_db


@freeze_time(DEFAULT_TIME)
def test_create_income_operation_creates_scenario(
    api_client, main_user, create_account, main_account, default_income_payload
):
    payload, expected_response_data = default_income_payload

    response = api_client.post("/api/regular-operations/", payload, format="json")
    assert response.status_code == 201

    response_data = response.json()
    regular_operation_id = response_data.pop("id")
    response_scenario = response_data.pop("scenario")

    assert response_data == expected_response_data

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
def test_create_expense_operation_doesnt_creates_scenario(
    api_client, main_user, create_account, main_account, default_expense_payload
):
    payload, expected_response_data = default_expense_payload

    response = api_client.post("/api/regular-operations/", payload, format="json")
    assert response.status_code == 201

    response_data = response.json()
    response_scenario = response_data.pop("scenario", None)
    response_data.pop("id", None)

    assert response_scenario is None
    assert response_data == expected_response_data


@freeze_time(DEFAULT_TIME)
def test_update_regular_operation_keeps_existing_scenario(
    api_client, main_user, create_account, main_account, default_income_payload
):
    payload, expected_response_data = default_income_payload

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
    update_response = api_client.patch(
        f"/api/regular-operations/{regular_operation_id}/", update_payload, format="json"
    )
    assert update_response.status_code == status.HTTP_200_OK

    detail_response = api_client.get(f"/api/regular-operations/{regular_operation_id}/")
    detail_response_scenario = detail_response.data["scenario"]

    assert detail_response_scenario["title"] == response_scenario["title"]
    assert detail_response_scenario["description"] == response_scenario["description"]
    assert detail_response_scenario["is_active"] is response_scenario["is_active"]
    assert len(detail_response_scenario["rules"]) == 1
    assert detail_response_scenario["rules"][0]["amount"] == "700.00"


@freeze_time(DEFAULT_TIME)
def test_update_with_new_scenario_rules_replaces_previous(
    api_client, main_user, create_account, main_account, default_income_payload
):
    payload, expected_response_data = default_income_payload

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


@pytest.mark.parametrize(
    ("field", "new_value"),
    (
        pytest.param(
            "type",
            RegularOperationType.EXPENSE,
            id="cannot_change_type",
        ),
        pytest.param(
            "period_type",
            RegularOperationPeriodType.DAY,
            id="cannot_change_period_type",
        ),
        pytest.param(
            "period_interval",
            2,
            id="cannot_change_period_interval",
        ),
    ),
)
@freeze_time(DEFAULT_TIME)
def test_cannot_change_operation_immutable_fields(
    field,
    new_value,
    api_client,
    main_user,
    create_account,
    main_account,
    default_income_payload,
):
    payload, expected_response_data = default_income_payload

    response = api_client.post("/api/regular-operations/", payload, format="json")
    assert response.status_code == 201

    response_data = response.json()
    regular_operation_id = response_data.pop("id")

    initial_value = payload[field]

    response = api_client.patch(
        f"/api/regular-operations/{regular_operation_id}/",
        {field: new_value},
        format="json",
    )

    assert response.status_code == 400
    assert field in response.data

    operation = RegularOperation.objects.get(id=regular_operation_id)
    operation.refresh_from_db()
    assert getattr(operation, field) == initial_value


@freeze_time(DEFAULT_TIME)
def test_delete_operation_removes_scenario_and_rules(
    api_client, default_income_payload, second_account
):
    payload, expected_response_data = default_income_payload

    response = api_client.post("/api/regular-operations/", payload, format="json")
    assert response.status_code == 201
    scenario_id = response.data["scenario"]["id"]
    assert RegularOperation.objects.filter(title=DEFAULT_INCOME_TITLE).count() == 1
    assert Scenario.objects.filter(id=scenario_id).count() == 1
    assert ScenarioRule.objects.filter(scenario=scenario_id).count() == 0

    payload = {
        "scenario": scenario_id,
        "target_account": str(second_account.id),
        "amount": "250.00",
        "order": 1,
    }
    rules_response = api_client.post("/api/scenarios/rules/", payload, format="json")
    assert rules_response.status_code == status.HTTP_201_CREATED
    assert ScenarioRule.objects.filter(scenario=scenario_id).count() == 1

    regular_operation_id = response.data.pop("id")

    operation_delete_response = api_client.delete(
        f"/api/regular-operations/{regular_operation_id}/"
    )

    assert operation_delete_response.status_code == 204
    assert RegularOperation.objects.filter(title=DEFAULT_INCOME_TITLE).count() == 0
    assert Scenario.objects.filter(id=scenario_id).count() == 0
    assert ScenarioRule.objects.filter(scenario=scenario_id).count() == 0


def test_access_is_limited_to_authenticated_user(
    api_client, main_user, other_user, create_account, main_account, other_account
):
    unauthenticated_client = APIClient()
    response = unauthenticated_client.get("/api/regular-operations/")
    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    )

    RegularOperation.objects.create(
        user=main_user,
        title="Моя операция",
        description="",
        amount=Decimal("100.00"),
        type=RegularOperationType.EXPENSE,
        from_account=main_account,
        start_date=DEFAULT_TIME,
        end_date=DEFAULT_TIME_WITH_OFFSET,
        period_type=RegularOperationPeriodType.WEEK,
        period_interval=1,
        is_active=True,
    )

    other_regular_operation = RegularOperation.objects.create(
        user=other_user,
        title="Чужая операция",
        description="",
        amount=Decimal("200.00"),
        type=RegularOperationType.EXPENSE,
        from_account=other_account,
        start_date=DEFAULT_TIME,
        end_date=DEFAULT_TIME_WITH_OFFSET,
        period_type=RegularOperationPeriodType.WEEK,
        period_interval=1,
        is_active=True,
    )

    response = api_client.get("/api/regular-operations/")
    assert response.status_code == 200
    assert response.data["count"] == 5
    assert len(response.data["results"]) == 5
    assert response.data["results"][0]["title"] == "Моя операция"

    response = api_client.get(f"/api/regular-operations/{other_regular_operation.id}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    ["payload", "expected_failed_field", "expected_message"],
    [
        pytest.param(
            {
                "title": "Ежемесячный перевод",
                "description": "Описание",
                "amount": "300.00",
                "type": RegularOperationType.EXPENSE,
                "start_date": DEFAULT_TIME.isoformat(),
                "end_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                "period_type": RegularOperationPeriodType.MONTH,
                "period_interval": 1,
                "is_active": True,
            },
            "from_account",
            None,
            id="EXPENSE; no account selected",
        ),
        pytest.param(
            {
                "title": "Ежемесячный перевод",
                "description": "Описание",
                "amount": "300.00",
                "type": RegularOperationType.EXPENSE,
                "from_account": MAIN_ACCOUNT_UUID,
                "to_account": SECOND_ACCOUNT_UUID,
                "start_date": DEFAULT_TIME.isoformat(),
                "end_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                "period_type": RegularOperationPeriodType.MONTH,
                "period_interval": 1,
                "is_active": True,
            },
            "to_account",
            None,
            id="EXPENSE; both accounts selected",
        ),
        pytest.param(
            {
                "title": "Ежемесячный перевод",
                "description": "Описание",
                "amount": "300.00",
                "type": RegularOperationType.EXPENSE,
                "from_account": MAIN_ACCOUNT_UUID,
                "start_date": DEFAULT_TIME.isoformat(),
                "end_date": DEFAULT_TIME.isoformat(),
                "period_type": RegularOperationPeriodType.MONTH,
                "period_interval": 1,
                "is_active": True,
            },
            "end_date",
            None,
            id="EXPENSE; start_date == end_date",
        ),
        pytest.param(
            {
                "title": "Ежемесячный перевод",
                "description": "Описание",
                "amount": "300.00",
                "type": RegularOperationType.EXPENSE,
                "from_account": MAIN_ACCOUNT_UUID,
                "start_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                "end_date": DEFAULT_TIME.isoformat(),
                "period_type": RegularOperationPeriodType.MONTH,
                "period_interval": 1,
                "is_active": True,
            },
            "end_date",
            None,
            id="EXPENSE; start_date < end_date",
        ),
        pytest.param(
            {
                "title": "Ежемесячный перевод",
                "description": "Описание",
                "amount": "300.00",
                "type": RegularOperationType.INCOME,
                "start_date": DEFAULT_TIME.isoformat(),
                "end_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                "period_type": RegularOperationPeriodType.MONTH,
                "period_interval": 1,
                "is_active": True,
            },
            "to_account",
            None,
            id="INCOME; no account selected",
        ),
        pytest.param(
            {
                "title": "Ежемесячный перевод",
                "description": "Описание",
                "amount": "300.00",
                "type": RegularOperationType.INCOME,
                "from_account": MAIN_ACCOUNT_UUID,
                "to_account": SECOND_ACCOUNT_UUID,
                "start_date": DEFAULT_TIME.isoformat(),
                "end_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                "period_type": RegularOperationPeriodType.MONTH,
                "period_interval": 1,
                "is_active": True,
            },
            "from_account",
            None,
            id="INCOME; both accounts selected",
        ),
        pytest.param(
            {
                "title": "Ежемесячный перевод",
                "description": "Описание",
                "amount": "300.00",
                "type": RegularOperationType.INCOME,
                "to_account": MAIN_ACCOUNT_UUID,
                "start_date": DEFAULT_TIME.isoformat(),
                "end_date": DEFAULT_TIME.isoformat(),
                "period_type": RegularOperationPeriodType.MONTH,
                "period_interval": 1,
                "is_active": True,
            },
            "end_date",
            None,
            id="INCOME; start_date == end_date",
        ),
        pytest.param(
            {
                "title": "Ежемесячный перевод",
                "description": "Описание",
                "amount": "300.00",
                "type": RegularOperationType.INCOME,
                "to_account": MAIN_ACCOUNT_UUID,
                "start_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                "end_date": DEFAULT_TIME.isoformat(),
                "period_type": RegularOperationPeriodType.MONTH,
                "period_interval": 1,
                "is_active": True,
            },
            "end_date",
            None,
            id="INCOME; start_date > end_date",
        ),
        pytest.param(
            {
                "title": "Ежемесячный перевод",
                "description": "Описание",
                "amount": "300.00",
                "type": RegularOperationType.EXPENSE,
                "from_account": OTHER_ACCOUNT_UUID,
                "start_date": DEFAULT_TIME.isoformat(),
                "end_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                "period_type": RegularOperationPeriodType.MONTH,
                "period_interval": 1,
                "is_active": True,
            },
            "from_account",
            "Счет списания должен принадлежать текущему пользователю",
            id="EXPESE; regular operation for now owned account",
        ),
        pytest.param(
            {
                "title": "Ежемесячный перевод",
                "description": "Описание",
                "amount": "300.00",
                "type": RegularOperationType.INCOME,
                "to_account": OTHER_ACCOUNT_UUID,
                "start_date": DEFAULT_TIME.isoformat(),
                "end_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                "period_type": RegularOperationPeriodType.MONTH,
                "period_interval": 1,
                "is_active": True,
            },
            "to_account",
            "Счет зачисления должен принадлежать текущему пользователю",
            id="INCOME; regular operation for now owned account",
        ),
    ],
)
@freeze_time(DEFAULT_TIME)
def test_expense_operation_validation_errors(
    payload,
    expected_failed_field,
    expected_message,
    api_client,
    main_user,
    main_account,
    second_account,
    other_account,
):
    response = api_client.post("/api/regular-operations/", payload, format="json")

    assert response.status_code == 400
    assert expected_failed_field in response.data
    if expected_message is not None:
        assert expected_message in str(response.data)
