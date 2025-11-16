from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Final

from accounts.models import Account, AccountType
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction
from regular_operations.models import (
    RegularOperationPeriodType,
    RegularOperationType,
)
from rest_framework import status
from rest_framework.test import APIClient
from scenarios.models import RuleType


DEFAULT_TIME: Final[datetime] = datetime(2025, 11, 1, tzinfo=UTC)
DEFAULT_TIME_WITH_OFFSET: Final[datetime] = datetime(2025, 12, 1, tzinfo=UTC)

DEFAULT_DATE: Final[date] = DEFAULT_TIME.date()
DEFAULT_DATE_WITH_OFFSET: Final[date] = DEFAULT_TIME_WITH_OFFSET.date()

MAIN_ACCOUNT_UUID: Final[str] = "00000000-0000-0000-0000-000000000000"
SECOND_ACCOUNT_UUID: Final[str] = "00000000-0000-0000-0000-000000000001"
THIRD_ACCOUNT_UUID: Final[str] = "00000000-0000-0000-0000-000000000002"
OTHER_ACCOUNT_UUID: Final[str] = "00000000-0000-0000-0000-000000000003"


ACCOUNT_UUID_4: Final[str] = "00000000-0000-0000-0000-000000000004"
ACCOUNT_UUID_5: Final[str] = "00000000-0000-0000-0000-000000000005"
ACCOUNT_UUID_6: Final[str] = "00000000-0000-0000-0000-000000000006"


def _ensure_success(response, *, action: str) -> None:
    if response.status_code not in {status.HTTP_200_OK, status.HTTP_201_CREATED}:
        raise RuntimeError(
            f"Failed to {action}: status={response.status_code}, data={response.data}"
        )


def bootstrap_dev_data() -> None:
    call_command("migrate", interactive=False, verbosity=0)

    with transaction.atomic():
        call_command("flush", interactive=False, verbosity=0)

        user_model = get_user_model()
        user_model.objects.create_superuser(  # type: ignore[attr-defined]
            username="admin",
            email="admin@example.com",
            password="admin123",
        )

        owner = user_model.objects.create_user(  # type: ignore[attr-defined]
            username="owner",
            email="owner@example.com",
            password="password123",
        )

        stranger = user_model.objects.create_user(  # type: ignore[attr-defined]
            username="stranger",
            email="stranger@example.com",
            password="password123",
        )

        client = APIClient()
        client.force_authenticate(user=owner)

        other_client = APIClient()
        other_client.force_authenticate(user=stranger)
        payload: dict[str, Any]

        for payload, client_ in [
            (
                {
                    "id": MAIN_ACCOUNT_UUID,
                    "name": "Основной счёт",
                    "type": AccountType.MAIN.value,
                },
                client,
            ),
            (
                {
                    "id": SECOND_ACCOUNT_UUID,
                    "name": "Резерв",
                    "type": AccountType.RESERVE.value,
                },
                client,
            ),
            (
                {
                    "id": THIRD_ACCOUNT_UUID,
                    "name": "Накопление",
                    "type": AccountType.ACCUMULATION.value,
                },
                client,
            ),
            (
                {
                    "id": OTHER_ACCOUNT_UUID,
                    "name": "Накопление",
                    "type": AccountType.MAIN.value,
                },
                other_client,
            ),
            (
                {
                    "id": ACCOUNT_UUID_4,
                    "name": "Счёт 4",
                    "type": AccountType.ACCUMULATION.value,
                },
                other_client,
            ),
            (
                {
                    "id": ACCOUNT_UUID_5,
                    "name": "Счёт 5",
                    "type": AccountType.ACCUMULATION.value,
                },
                other_client,
            ),
            (
                {
                    "id": ACCOUNT_UUID_6,
                    "name": "Счёт 5",
                    "type": AccountType.ACCUMULATION.value,
                },
                other_client,
            ),
        ]:
            response = client_.post("/api/accounts/", payload, format="json")
            _ensure_success(response, action="create account")
            created_id = response.data.get("id")
            target_id = payload["id"]
            if created_id != target_id:
                # аккуратно с автоматическими присвоениями айди!
                Account.objects.filter(id=created_id).update(id=target_id)

        income_operations: dict[str, str] = {}
        for payload in [
            {
                "title": "Зарплата",
                "description": "Основной доход",
                "amount": "1000.00",
                "type": RegularOperationType.INCOME.value,
                "to_account": MAIN_ACCOUNT_UUID,
            },
            {
                "title": "Фриланс",
                "description": "Доп. доход",
                "amount": "500.00",
                "type": RegularOperationType.INCOME.value,
                "to_account": MAIN_ACCOUNT_UUID,
            },
        ]:
            payload = {
                **payload,
                "start_date": DEFAULT_TIME.isoformat(),
                "end_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                "period_type": RegularOperationPeriodType.DAY,
                "period_interval": 1,
                "active_before": date.max,
            }
            response = client.post("/api/regular-operations/", payload, format="json")
            _ensure_success(response, action="create income regular operation")
            scenario = response.data.get("scenario")
            if scenario is None:
                raise RuntimeError("Scenario is missing for the created regular operation")
            income_operations[payload["title"]] = scenario["id"]

        expenses_payload = [
            {
                "title": "Повседневные траты",
                "description": "",
                "amount": "100.00",
                "type": RegularOperationType.EXPENSE.value,
            },
            {
                "title": "Питание",
                "description": "",
                "amount": "50.00",
                "type": RegularOperationType.EXPENSE.value,
            },
        ]

        for payload in expenses_payload:
            payload = {
                **payload,
                "from_account": MAIN_ACCOUNT_UUID,
                "start_date": DEFAULT_TIME.isoformat(),
                "end_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                "period_type": RegularOperationPeriodType.DAY,
                "period_interval": 1,
                "active_before": date.max,
            }
            response = client.post("/api/regular-operations/", payload, format="json")
            _ensure_success(response, action="create expense regular operation")

        scenario_updates = {
            income_operations["Зарплата"]: {
                "title": "Распределение зарплаты",
                "description": "",
            },
            income_operations["Фриланс"]: {
                "title": "Распределение фриланса",
                "description": "",
            },
        }

        for scenario_id, payload in scenario_updates.items():
            response = client.patch(
                f"/api/scenarios/{scenario_id}/",
                payload,
                format="json",
            )
            _ensure_success(response, action="update scenario")

        scenario_rules_payloads = [
            {
                "scenario": income_operations["Зарплата"],
                "target_account": SECOND_ACCOUNT_UUID,
                "type": RuleType.FIXED.value,
                "amount": "200.00",
                "order": 1,
            },
            {
                "scenario": income_operations["Зарплата"],
                "target_account": THIRD_ACCOUNT_UUID,
                "type": RuleType.FIXED.value,
                "amount": "300.00",
                "order": 2,
            },
            {
                "scenario": income_operations["Фриланс"],
                "target_account": SECOND_ACCOUNT_UUID,
                "type": RuleType.FIXED.value,
                "amount": "100.00",
                "order": 1,
            },
        ]

        for payload in scenario_rules_payloads:
            response = client.post("/api/scenarios/rules/", payload, format="json")
            _ensure_success(response, action="create scenario rule")
