from datetime import timedelta

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
        income_operations = self._assert_2_incomes()
        self._assert_2_outcomes()
        self._assert_2_binded_scenarios(income_operations)

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

    def _assert_2_incomes(self):
        income_operations = RegularOperation.objects.filter(
            type=RegularOperationType.INCOME
        ).order_by("title")
        assert income_operations.count() == 2
        return income_operations

    def _assert_2_outcomes(self):
        expense_operations = RegularOperation.objects.filter(
            type=RegularOperationType.EXPENSE
        ).order_by("title")
        assert expense_operations.count() == 2

    def _assert_2_binded_scenarios(self, income_operations):
        scenarios = Scenario.objects.filter(operation__in=income_operations).order_by("title")
        assert scenarios.count() == 2
