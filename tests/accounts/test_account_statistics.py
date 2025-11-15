from datetime import timedelta

from django.db.models import QuerySet

from core.bootstrap import (
    DEFAULT_TIME,
    MAIN_ACCOUNT_UUID,
    SECOND_ACCOUNT_UUID,
    THIRD_ACCOUNT_UUID, DEFAULT_DATE,
)
from freezegun import freeze_time
import pytest
from regular_operations.models import RegularOperation, RegularOperationType
from rest_framework import status
from rest_framework.test import APIClient
from scenarios.models import Scenario


pytestmark = pytest.mark.django_db


@freeze_time(DEFAULT_TIME)
class TestAccountStatistics:
    @classmethod
    def setup_class(cls):
        cls.start_date = DEFAULT_DATE
        cls.end_date = DEFAULT_DATE + timedelta(days=2)


    def test_statistics_returns_daily_balances_from_db_truth(self, main_user):
        """
        Готовим данные так же, как в тесте calculate:
          - Основной счёт + два целевых (Накопления, Ипотека)
          - 2 дохода / 2 расхода / правила сценариев (2 перевода из дохода_1 и 1 перевод из дохода_2)
        Затем:
          - вызываем /api/transactions/calculate/ на 3 дня, чтобы создать транзакции
          - считаем дневные балансы по БД
          - проверяем, что ответ /api/transactions/statistics/ совпадает с расчётом из БД
        """

        income_operations = self._assert_2_incomes()
        self._assert_2_outcomes()
        self._assert_2_binded_scenarios(income_operations)

        calc_payload = {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }
        client = APIClient()
        client.force_authenticate(user=main_user)

        calc_resp = client.post("/api/transactions/calculate/", calc_payload, format="json")
        assert calc_resp.status_code == status.HTTP_200_OK, calc_resp.data

        statistics_payload = {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }
        statistics_response = client.post(
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

    def _assert_2_incomes(self):
        income_operations = RegularOperation.objects.filter(type=RegularOperationType.INCOME).order_by(
            "title"
        )
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
