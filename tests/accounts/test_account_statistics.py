from datetime import timedelta
from decimal import Decimal

from accounts.models import AccountType
from core.bootstrap import (
    DEFAULT_DATE,
    DEFAULT_TIME,
    MAIN_ACCOUNT_UUID,
    SECOND_ACCOUNT_UUID,
    THIRD_ACCOUNT_UUID,
)
from freezegun import freeze_time
import pytest
from regular_operations.models import RegularOperation, RegularOperationType
from rest_framework import status
from scenarios.models import Scenario


pytestmark = pytest.mark.django_db


@freeze_time(DEFAULT_TIME)
class TestAccountStatistics:
    @classmethod
    def setup_class(cls):
        cls.start_date = DEFAULT_DATE
        cls.end_date = DEFAULT_DATE + timedelta(days=2)

    def test_statistics_returns_daily_balances(self, main_user, api_client):
        income_operations = self._assert_2_incomes(main_user)
        self._assert_2_outcomes(main_user)
        self._assert_2_binded_scenarios(main_user, income_operations)

        self._calculate_for_period(api_client, self.start_date, self.end_date)

        statistics_payload = {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }
        statistics_response = api_client.post(
            "/api/accounts/statistics/", statistics_payload, format="json"
        )
        assert statistics_response.status_code == status.HTTP_200_OK, statistics_response.data

        data = statistics_response.data
        assert data == {
            "balances": {
                MAIN_ACCOUNT_UUID: {
                    "2025-11-01": "750.00",
                    "2025-11-02": "1500.00",
                    "2025-11-03": "2250.00",
                },
                SECOND_ACCOUNT_UUID: {
                    "2025-11-01": "300.00",
                    "2025-11-02": "600.00",
                    "2025-11-03": "900.00",
                },
                THIRD_ACCOUNT_UUID: {
                    "2025-11-01": "300.00",
                    "2025-11-02": "600.00",
                    "2025-11-03": "900.00",
                },
            }
        }

    @pytest.mark.parametrize(
        ["accounts", "expected_balance_response"],
        [
            pytest.param(
                [MAIN_ACCOUNT_UUID],
                {
                    MAIN_ACCOUNT_UUID: {
                        "2025-11-01": "750.00",
                        "2025-11-02": "1500.00",
                        "2025-11-03": "2250.00",
                    },
                },
                id="one account",
            ),
            pytest.param(
                [],
                {
                    MAIN_ACCOUNT_UUID: {
                        "2025-11-01": "750.00",
                        "2025-11-02": "1500.00",
                        "2025-11-03": "2250.00",
                    },
                    SECOND_ACCOUNT_UUID: {
                        "2025-11-01": "300.00",
                        "2025-11-02": "600.00",
                        "2025-11-03": "900.00",
                    },
                    THIRD_ACCOUNT_UUID: {
                        "2025-11-01": "300.00",
                        "2025-11-02": "600.00",
                        "2025-11-03": "900.00",
                    },
                },
                id="all accounts, no accounts passed",
            ),
            pytest.param(
                [MAIN_ACCOUNT_UUID, SECOND_ACCOUNT_UUID],
                {
                    MAIN_ACCOUNT_UUID: {
                        "2025-11-01": "750.00",
                        "2025-11-02": "1500.00",
                        "2025-11-03": "2250.00",
                    },
                    SECOND_ACCOUNT_UUID: {
                        "2025-11-01": "300.00",
                        "2025-11-02": "600.00",
                        "2025-11-03": "900.00",
                    },
                },
                id="part of accounts",
            ),
            pytest.param(
                [MAIN_ACCOUNT_UUID, SECOND_ACCOUNT_UUID, THIRD_ACCOUNT_UUID],
                {
                    MAIN_ACCOUNT_UUID: {
                        "2025-11-01": "750.00",
                        "2025-11-02": "1500.00",
                        "2025-11-03": "2250.00",
                    },
                    SECOND_ACCOUNT_UUID: {
                        "2025-11-01": "300.00",
                        "2025-11-02": "600.00",
                        "2025-11-03": "900.00",
                    },
                    THIRD_ACCOUNT_UUID: {
                        "2025-11-01": "300.00",
                        "2025-11-02": "600.00",
                        "2025-11-03": "900.00",
                    },
                },
                id="all accounts, all accounts passed",
            ),
        ],
    )
    def test_statistics_returns_daily_balances_for_one_account(
        self,
        api_client,
        main_user,
        accounts: list[str],
        expected_balance_response: dict,
    ):
        self._calculate_for_period(api_client, self.start_date, self.end_date)

        statistics_payload = {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "accounts": accounts,
        }
        statistics_response = api_client.post(
            "/api/accounts/statistics/", statistics_payload, format="json"
        )
        assert statistics_response.status_code == status.HTTP_200_OK, statistics_response.data

        data = statistics_response.data
        assert data == {"balances": expected_balance_response}

    def _calculate_for_period(self, client, start_date, end_date):
        calc_payload = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        calc_resp = client.post("/api/transactions/calculate/", calc_payload, format="json")
        assert calc_resp.status_code == status.HTTP_200_OK, calc_resp.data

    @pytest.mark.parametrize(
        ["start_date", "end_date", "expected_account_values"],
        [
            pytest.param(
                DEFAULT_DATE,
                DEFAULT_DATE,
                {
                    "2025-11-01": "4540.00"  # баланс на конец первого дня
                },
                id="PRESENT; 1 day  (today)",
            ),
            pytest.param(
                DEFAULT_DATE + timedelta(days=1),
                DEFAULT_DATE + timedelta(days=1),
                {
                    "2025-11-02": "4640.00"  # баланс на конец второго дня
                },
                id="FUTURE; 1 day  (tomorrow)",
            ),
            pytest.param(
                DEFAULT_DATE,
                DEFAULT_DATE + timedelta(days=1),
                {
                    "2025-11-01": "4540.00",
                    "2025-11-02": "4640.00",
                },
                id="PRESENT; 2 days (today + tomorrow)",
            ),
            pytest.param(
                DEFAULT_DATE,
                DEFAULT_DATE + timedelta(days=3),
                {
                    "2025-11-01": "4540.00",
                    "2025-11-02": "4640.00",
                    "2025-11-03": "3640.00",
                    "2025-11-04": "13640.00",
                },
                id="PRESENT; 4 days",
            ),
            pytest.param(
                DEFAULT_DATE - timedelta(days=1),
                DEFAULT_DATE - timedelta(days=1),
                {"2025-10-31": "4550.00"},
                id="PAST; 1 day (yesterday)",
            ),
            pytest.param(
                DEFAULT_DATE - timedelta(days=1),
                DEFAULT_DATE,
                {
                    "2025-10-31": "4550.00",
                    "2025-11-01": "4540.00",
                },
                id="PAST; 2 days (yesterday + today)",
            ),
            pytest.param(
                DEFAULT_DATE - timedelta(days=4),
                DEFAULT_DATE,
                {
                    "2025-10-28": "0.00",
                    "2025-10-29": "5000.00",
                    "2025-10-30": "4500.00",
                    "2025-10-31": "4550.00",
                    "2025-11-01": "4540.00",
                },
                id="PAST; 5 days",
            ),
            pytest.param(
                DEFAULT_DATE - timedelta(days=1),
                DEFAULT_DATE + timedelta(days=1),
                {
                    "2025-10-31": "4550.00",
                    "2025-11-01": "4540.00",
                    "2025-11-02": "4640.00",
                },
                id="PAST + FUTURE; 3 days (yesterday + today + tomorrow)",
            ),
            pytest.param(
                DEFAULT_DATE - timedelta(days=4),
                DEFAULT_DATE + timedelta(days=3),
                {
                    "2025-10-28": "0.00",
                    "2025-10-29": "5000.00",
                    "2025-10-30": "4500.00",
                    "2025-10-31": "4550.00",
                    "2025-11-01": "4540.00",
                    "2025-11-02": "4640.00",
                    "2025-11-03": "3640.00",
                    "2025-11-04": "13640.00",
                },
                id="PAST + FUTURE; 9 days",
            ),
        ],
    )
    def test_statistics_returns_daily_balances_from_manual_transactions(
        self,
        main_user,
        api_client,
        create_account,
        transactions_fabric,
        start_date,
        end_date,
        expected_account_values,
    ):
        account = create_account(main_user, "Test", AccountType.ACCUMULATION, Decimal("4550.00"))
        transactions_fabric(account)
        account_id = str(account.id)

        statistics_payload = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "accounts": [account_id],
        }
        response = api_client.post("/api/accounts/statistics/", statistics_payload, format="json")
        assert response.status_code == status.HTTP_200_OK, response.data

        assert response.data == {"balances": {account_id: expected_account_values}}

    def _assert_2_incomes(self, main_user):
        income_operations = RegularOperation.objects.filter(
            type=RegularOperationType.INCOME,
            user=main_user,
        ).order_by("title")
        assert income_operations.count() == 2
        return income_operations

    def _assert_2_outcomes(self, main_user):
        expense_operations = RegularOperation.objects.filter(
            type=RegularOperationType.EXPENSE,
            user=main_user,
        ).order_by("title")
        assert expense_operations.count() == 2

    def _assert_2_binded_scenarios(self, main_user, income_operations):
        scenarios = Scenario.objects.filter(operation__in=income_operations, user=main_user).order_by("title")
        assert scenarios.count() == 2
