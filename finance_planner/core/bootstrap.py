from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
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


class Bootstraper:
    def __init__(self) -> None:
        self.test_client: APIClient | None = None
        self.demo_client: APIClient | None = None

        self.test_salary_scenario_id: str | None = None
        self.demo_advance_scenario_id: str | None = None
        self.demo_salary_scenario_id: str | None = None
        self.demo_scholarship_scenario_id: str | None = None

    def bootstrap(self) -> None:
        call_command("migrate", interactive=False, verbosity=0)
        with transaction.atomic():
            call_command("flush", interactive=False, verbosity=0)

            self._create_users()
            self._create_accounts()
            self._create_regular_incomes()
            self._create_regular_expenses()
            self._create_scenario_rules()

            self._calculate_transactions()

    def _create_users(self):
        user_model = get_user_model()
        user_model.objects.create_superuser(  # type: ignore[attr-defined]
            username="admin",
            email="admin@example.com",
            password="admin123",
            first_name="Admin",
            last_name="Adminamatnetroj",
        )

        owner = user_model.objects.create_user(  # type: ignore[attr-defined]
            username="owner",
            email="owner@example.com",
            password="password123",
            first_name="Owner",
            last_name="Huewner",
        )

        owner_client = APIClient()
        owner_client.force_authenticate(user=owner)

        demo = user_model.objects.create_user(  # type: ignore[attr-defined]
            username="demo",
            email="demo@example.com",
            password="password123",
            first_name="Stranger",
            last_name="Huyanger",
        )

        other_client = APIClient()
        other_client.force_authenticate(user=demo)

        self.test_client = owner_client
        self.demo_client = other_client

    def _create_accounts(self):
        payload: dict[str, Any]
        for payload, client in [
            (
                {
                    "id": MAIN_ACCOUNT_UUID,
                    "name": "Основной счёт",
                    "type": AccountType.MAIN,
                },
                self.test_client,
            ),
            (
                {
                    "id": SECOND_ACCOUNT_UUID,
                    "name": "Резерв",
                    "type": AccountType.RESERVE,
                },
                self.test_client,
            ),
            (
                {
                    "id": THIRD_ACCOUNT_UUID,
                    "name": "Накопление",
                    "type": AccountType.ACCUMULATION,
                },
                self.test_client,
            ),
            (
                {
                    "id": OTHER_ACCOUNT_UUID,
                    "name": "Основной Счёт",
                    "type": AccountType.MAIN,
                },
                self.demo_client,
            ),
            (
                {
                    "id": ACCOUNT_UUID_4,
                    "name": "На отпуск",
                    "type": AccountType.PURPOSE,
                    "target_amount": "70000.0000",
                },
                self.demo_client,
            ),
            (
                {
                    "id": ACCOUNT_UUID_5,
                    "name": "Накопления",
                    "type": AccountType.RESERVE,
                },
                self.demo_client,
            ),
            (
                {
                    "id": ACCOUNT_UUID_6,
                    "name": "Ипотека",
                    "type": AccountType.DEBT,
                    "target_amount": "1000000.0000",
                    "current_balance": "120000.00"
                },
                self.demo_client,
            ),
        ]:
            if client is None:
                raise ValueError("No client")
            response = client.post("/api/accounts/", payload, format="json")
            _ensure_success(response, action="create account")
            created_id = response.data.get("id")
            target_id = payload["id"]
            if created_id != target_id:
                # аккуратно с автоматическими присвоениями айди!
                Account.objects.filter(id=created_id).update(id=target_id)

    def _create_regular_incomes(self):
        payload: dict[str, Any]
        for client, payload, attr_name in [
            (
                self.test_client,
                {
                    "title": "Зарплата",
                    "description": "Основной доход",
                    "amount": "1000.00",
                    "type": RegularOperationType.INCOME,
                    "start_date": DEFAULT_TIME.isoformat(),
                    "to_account": MAIN_ACCOUNT_UUID,
                    "period_type": RegularOperationPeriodType.DAY,
                    "end_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                },
                "test_salary_scenario_id",
            ),
            (
                self.test_client,
                {
                    "title": "Фриланс",
                    "description": "Доп. доход",
                    "amount": "500.00",
                    "type": RegularOperationType.INCOME,
                    "start_date": DEFAULT_TIME.isoformat(),
                    "to_account": MAIN_ACCOUNT_UUID,
                    "period_type": RegularOperationPeriodType.DAY,
                    "end_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                },
                None,
            ),
            (
                self.demo_client,
                {
                    "title": "Аванс",
                    "description": "К2",
                    "amount": "100000.00",
                    "type": RegularOperationType.INCOME,
                    "start_date": DEFAULT_TIME.isoformat(),
                    "to_account": OTHER_ACCOUNT_UUID,
                    "period_type": RegularOperationPeriodType.MONTH,
                },
                "demo_advance_scenario_id",
            ),
            (
                self.demo_client,
                {
                    "title": "Зарплата",
                    "description": "К2",
                    "amount": "120000.00",
                    "type": RegularOperationType.INCOME,
                    "start_date": (DEFAULT_TIME + timedelta(days=15)).isoformat(),
                    "to_account": OTHER_ACCOUNT_UUID,
                    "period_type": RegularOperationPeriodType.MONTH,
                },
                "demo_salary_scenario_id",
            ),
            (
                self.demo_client,
                {
                    "title": "Стипендия",
                    "description": "РТУ МИРЭА",
                    "amount": "5000.00",
                    "type": RegularOperationType.INCOME,
                    "start_date": (DEFAULT_TIME + timedelta(days=5)).isoformat(),
                    "to_account": OTHER_ACCOUNT_UUID,
                    "period_type": RegularOperationPeriodType.MONTH,
                },
                "demo_scholarship_scenario_id",
            ),
        ]:
            if client is None:
                raise ValueError("No client")
            payload = {
                **payload,
                "period_interval": 1,
            }
            response = client.post("/api/regular-operations/", payload, format="json")
            _ensure_success(response, action="create income regular operation")
            scenario = response.data.get("scenario")
            if scenario is None:
                raise RuntimeError("Scenario is missing for the created regular operation")
            if attr_name is not None:
                setattr(self, attr_name, scenario["id"])

    def _create_regular_expenses(self):
        payload: dict[str, Any]
        for client, payload in [
            (
                self.test_client,
                {
                    "title": "Повседневные траты",
                    "description": "",
                    "amount": "100.00",
                    "type": RegularOperationType.EXPENSE,
                    "from_account": MAIN_ACCOUNT_UUID,
                    "end_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                    "period_type": RegularOperationPeriodType.DAY,
                },
            ),
            (
                self.test_client,
                {
                    "title": "Питание",
                    "description": "",
                    "amount": "50.00",
                    "type": RegularOperationType.EXPENSE,
                    "from_account": MAIN_ACCOUNT_UUID,
                    "end_date": DEFAULT_TIME_WITH_OFFSET.isoformat(),
                    "period_type": RegularOperationPeriodType.DAY,
                },
            ),
            (
                self.demo_client,
                {
                    "title": "Питание",
                    "description": "",
                    "amount": "10000.00",
                    "type": RegularOperationType.EXPENSE,
                    "from_account": OTHER_ACCOUNT_UUID,
                    "period_type": RegularOperationPeriodType.MONTH,
                },
            ),
            (
                self.demo_client,
                {
                    "title": "Квартплата",
                    "description": "",
                    "amount": "50000.00",
                    "type": RegularOperationType.EXPENSE,
                    "from_account": OTHER_ACCOUNT_UUID,
                    "period_type": RegularOperationPeriodType.MONTH,
                },
            ),
        ]:
            if client is None:
                raise ValueError("No client")
            payload = {
                **payload,
                "start_date": DEFAULT_TIME.isoformat(),
                "period_interval": 1,
            }
            response = client.post("/api/regular-operations/", payload, format="json")
            _ensure_success(response, action="create expense regular operation")

    def _create_scenario_rules(self):
        scenario_rules_payloads = [
            (
                self.test_client,
                {
                    "scenario": self.test_salary_scenario_id,
                    "target_account": SECOND_ACCOUNT_UUID,
                    "type": RuleType.FIXED,
                    "amount": "200.00",
                    "order": 1,
                },
            ),
            (
                self.test_client,
                {
                    "scenario": self.test_salary_scenario_id,
                    "target_account": THIRD_ACCOUNT_UUID,
                    "type": RuleType.FIXED,
                    "amount": "300.00",
                    "order": 2,
                },
            ),
            (
                self.test_client,
                {
                    "scenario": self.test_salary_scenario_id,
                    "target_account": SECOND_ACCOUNT_UUID,
                    "type": RuleType.FIXED,
                    "amount": "100.00",
                    "order": 3,
                },
            ),
            (
                self.demo_client,
                {
                    "scenario": self.demo_advance_scenario_id,
                    "target_account": ACCOUNT_UUID_4,
                    "type": RuleType.FIXED,
                    "amount": "5000.00",
                    "order": 1,
                },
            ),
            (
                self.demo_client,
                {
                    "scenario": self.demo_salary_scenario_id,
                    "target_account": ACCOUNT_UUID_4,
                    "type": RuleType.FIXED,
                    "amount": "5000.00",
                    "order": 1,
                },
            ),
            (
                self.demo_client,
                {
                    "scenario": self.demo_advance_scenario_id,
                    "target_account": ACCOUNT_UUID_5,
                    "type": RuleType.FIXED,
                    "amount": "20000.00",
                    "order": 2,
                },
            ),
            (
                self.demo_client,
                {
                    "scenario": self.demo_salary_scenario_id,
                    "target_account": ACCOUNT_UUID_5,
                    "type": RuleType.FIXED,
                    "amount": "20000.00",
                    "order": 2,
                },
            ),
            (
                self.demo_client,
                {
                    "scenario": self.demo_advance_scenario_id,
                    "target_account": ACCOUNT_UUID_6,
                    "type": RuleType.FIXED,
                    "amount": "20000.00",
                    "order": 3,
                },
            ),
            (
                self.demo_client,
                {
                    "scenario": self.demo_salary_scenario_id,
                    "target_account": ACCOUNT_UUID_6,
                    "type": RuleType.FIXED,
                    "amount": "20000.00",
                    "order": 3,
                },
            ),
            (
                self.demo_client,
                {
                    "scenario": self.demo_scholarship_scenario_id,
                    "target_account": ACCOUNT_UUID_6,
                    "type": RuleType.FIXED,
                    "amount": "5000.00",
                    "order": 1,
                },
            ),
        ]

        for client, payload in scenario_rules_payloads:
            if client is None:
                raise ValueError("No client")
            response = client.post("/api/scenarios/rules/", payload, format="json")
            _ensure_success(response, action="create scenario rule")

    def _calculate_transactions(
        self,
    ):
        for client in [self.demo_client]:
            if client is None:
                raise ValueError("No client")
            client.post("/api/transactions/calculate/")


# def bootstrap_dev_data() -> None:
#
#
