from datetime import timedelta
from typing import Any

from core.bootstrap import (
    DEFAULT_DATE,
    DEFAULT_TIME,
    MAIN_ACCOUNT_UUID,
    SECOND_ACCOUNT_UUID,
)
from freezegun import freeze_time
import pytest
from regular_operations.models import RegularOperation, RegularOperationType
from rest_framework import status
from scenarios.models import Scenario
from transactions.models import TransactionType


pytestmark = pytest.mark.django_db


def _extract_items(resp):
    # Поддержка обоих вариантов ответа: с пагинацией и без
    if isinstance(resp.data, dict) and "results" in resp.data:
        return resp.data["results"], resp.data["count"]
    return resp.data, len(resp.data)


@pytest.mark.parametrize(
    "querystring, expected_descriptions",
    [
        ("?type=income", ["Salary", "Bonus", "Cashback", "Freelance"]),
        ("?type=expense", ["Groceries", "Electronics", "Rent", "Fuel", "Кофе"]),
        ("?confirmed=false", ["Fuel", "Кофе"]),
        ("?date__gte=2025-11-05&date__lte=2025-11-07", ["Move to savings", "Cashback", "Кофе"]),
        ("?amount__gte=100", ["Salary", "Bonus", "Electronics", "Freelance", "Rent"]),
        (
            f"?from_account={MAIN_ACCOUNT_UUID}",
            ["Groceries", "Electronics", "Move to savings", "Rent", "Fuel"],
        ),
        (f"?to_account={MAIN_ACCOUNT_UUID}", ["Salary", "Bonus", "Freelance"]),
        ("?type__in=income,transfer&amount__lte=100", ["Salary", "Cashback", "Move to savings"]),
        ("?search=Коф", ["Кофе"]),
    ],
)
def test_transactions_filters_single_entrypoint(
    api_client, main_user, main_account, second_account, querystring, expected_descriptions
):
    fixtures = [
        ("2025-11-01", TransactionType.INCOME, "100.00", None, MAIN_ACCOUNT_UUID, "Salary", True),
        ("2025-11-03", TransactionType.INCOME, "250.00", None, MAIN_ACCOUNT_UUID, "Bonus", True),
        (
            "2025-11-02",
            TransactionType.EXPENSE,
            "50.00",
            MAIN_ACCOUNT_UUID,
            None,
            "Groceries",
            True,
        ),
        (
            "2025-11-04",
            TransactionType.EXPENSE,
            "120.00",
            MAIN_ACCOUNT_UUID,
            None,
            "Electronics",
            True,
        ),
        (
            "2025-11-05",
            TransactionType.TRANSFER,
            "75.00",
            MAIN_ACCOUNT_UUID,
            SECOND_ACCOUNT_UUID,
            "Move to savings",
            True,
        ),
        (
            "2025-11-06",
            TransactionType.INCOME,
            "30.00",
            None,
            SECOND_ACCOUNT_UUID,
            "Cashback",
            True,
        ),
        ("2025-11-07", TransactionType.EXPENSE, "20.00", SECOND_ACCOUNT_UUID, None, "Кофе", False),
        (
            "2025-11-08",
            TransactionType.INCOME,
            "500.00",
            None,
            MAIN_ACCOUNT_UUID,
            "Freelance",
            True,
        ),
        ("2025-11-09", TransactionType.EXPENSE, "200.00", MAIN_ACCOUNT_UUID, None, "Rent", True),
        ("2025-11-10", TransactionType.EXPENSE, "90.00", MAIN_ACCOUNT_UUID, None, "Fuel", False),
    ]

    for (
        date_value,
        type_value,
        amount_value,
        from_account_value,
        to_account_value,
        description_value,
        confirmed_value,
    ) in fixtures:
        payload = {
            "date": date_value,
            "type": type_value,
            "amount": amount_value,
            "description": description_value,
            "confirmed": confirmed_value,
        }
        if from_account_value is not None:
            payload["from_account"] = from_account_value
        if to_account_value is not None:
            payload["to_account"] = to_account_value

        create_response = api_client.post("/api/transactions/", payload, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.data

    list_response = api_client.get("/api/transactions/")
    assert list_response.status_code == status.HTTP_200_OK
    _, total_count = _extract_items(list_response)
    assert total_count == len(fixtures)

    response = api_client.get(f"/api/transactions/{querystring}")
    assert response.status_code == status.HTTP_200_OK, response.data
    items, _ = _extract_items(response)

    got_descriptions = sorted([item["description"] for item in items])
    expected_sorted = sorted(expected_descriptions)
    assert got_descriptions == expected_sorted, {
        "query": querystring,
        "expected": expected_sorted,
        "got": got_descriptions,
        "raw": items,
    }


@freeze_time(DEFAULT_TIME)
class TestCalculateCreatesTransactions:
    @classmethod
    def setup_class(cls):
        # Окно расчёта: 3 дня
        cls.start_date = DEFAULT_DATE
        cls.end_date = cls.start_date + timedelta(days=2)
        # Ожидаемое количество:
        cls.days = 3
        cls.incomes_per_day = 2
        cls.expenses_per_day = 2
        cls.transfers_per_day = 3  # (2 правила из income_1) + (1 правило из income_2)
        cls.expected_total = cls.days * (
            cls.incomes_per_day + cls.expenses_per_day + cls.transfers_per_day
        )

    def test_calculate_creates_transactions(self, main_user, api_client):
        """
        Создаём:
          - Основной счёт (MAIN), «Накопления» (ACCUMULATION), «Ипотека» (DEBT)
          - 2 регулярных ДОХОДА на основной счёт
          - 2 регулярных РАСХОДА с основного счёта
          - Сценарии/правила:
              * по первому доходу: 200 -> Накопления, 300 -> Ипотека
              * по второму доходу: 100 -> Накопления
        Затем вызываем /api/transactions/calculate/ на 3 дня и проверяем,
        что создано: 6 доходов, 6 расходов, 9 переводов (всего 21).
        """

        income_operations = self._assert_2_incomes()
        self._assert_2_expenses()
        self._assert_2_binded_scenarios(income_operations)
        income_1, income_2 = income_operations

        # --- Вызов калькуляции
        calc_payload = {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            # "dry_run": False  # по умолчанию False — транзакции должны создаться
        }

        calc_resp = api_client.post("/api/transactions/calculate/", calc_payload, format="json")
        assert calc_resp.status_code == status.HTTP_200_OK, calc_resp.data

        assert calc_resp.data["transactions_created"] == self.expected_total

        self._assert_filters_works(api_client, income_1)

        # --- Дополнительно: повторный вызов калькуляции не должен задвоить транзакции
        calculate_response_2 = api_client.post(
            "/api/transactions/calculate/", calc_payload, format="json"
        )
        assert calculate_response_2.status_code == status.HTTP_200_OK, calculate_response_2.data

        self._assert_filters_works(api_client, income_1)

    @pytest.mark.parametrize(
        ["updated_param", "updated_value"],
        [
            pytest.param("description", "updated", id="allow change transaction"),
            pytest.param(
                "date",
                (DEFAULT_DATE + timedelta(days=1)).isoformat(),
                id="allow change transaction date",
            ),
            pytest.param(
                "planned_date",
                (DEFAULT_DATE + timedelta(days=4)).isoformat(),
                id="planned date wont affect",
            ),
        ],
    )
    def test_when_calculate_transaction_wont_recreate(
        self,
        main_user,
        api_client,
        updated_param: str,
        updated_value: Any,
    ):
        income_operations = self._assert_2_incomes()
        self._assert_2_expenses()
        self._assert_2_binded_scenarios(income_operations)

        calc_payload = {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }

        # Первый расчёт
        first_resp = api_client.post("/api/transactions/calculate/", calc_payload, format="json")
        assert first_resp.status_code == status.HTTP_200_OK, first_resp.data
        assert first_resp.data["transactions_created"] == self.expected_total

        dates_query = (
            f"date__gte={self.start_date.isoformat()}&date__lte={self.end_date.isoformat()}"
        )

        # Получаем транзакции после первого расчёта (через API)
        list_resp_1 = api_client.get(f"/api/transactions/?{dates_query}")
        assert list_resp_1.status_code == status.HTTP_200_OK
        items_1, total_1 = _extract_items(list_resp_1)
        assert total_1 == self.expected_total

        # Берём одну транзакцию и обновляем её через API (симулируем ручное изменение)
        target = items_1[0]
        target_id = target["id"]

        patch_resp = api_client.patch(
            f"/api/transactions/{target_id}/",
            {updated_param: updated_value},
            format="json",
        )
        assert patch_resp.status_code == status.HTTP_200_OK, patch_resp.data

        # Второй расчёт на тот же диапазон
        second_resp = api_client.post("/api/transactions/calculate/", calc_payload, format="json")
        assert second_resp.status_code == status.HTTP_200_OK, second_resp.data
        # Новые транзакции создаваться не должны
        assert second_resp.data["transactions_created"] == 0

        # Получаем список транзакций снова
        list_resp_2 = api_client.get(f"/api/transactions/?{dates_query}")
        assert list_resp_2.status_code == status.HTTP_200_OK
        items_2, total_2 = _extract_items(list_resp_2)

        # Количество транзакций не изменилось
        assert total_2 == total_1

        # ID транзакций те же самые — ничего не задвоилось и не пропало
        ids_1 = {item["id"] for item in items_1}
        ids_2 = {item["id"] for item in items_2}
        assert ids_1 == ids_2

        # Обновлённая транзакция по-прежнему существует с тем же ID
        assert target_id in ids_2

    def _assert_2_incomes(self):
        income_operations = RegularOperation.objects.filter(
            type=RegularOperationType.INCOME
        ).order_by("title")
        assert income_operations.count() == 2
        income_1, income_2 = income_operations
        return income_operations

    def _assert_2_expenses(self):
        expense_operations = RegularOperation.objects.filter(
            type=RegularOperationType.EXPENSE
        ).order_by("title")
        assert expense_operations.count() == 2

    def _assert_2_binded_scenarios(self, income_operations):
        scenarios = Scenario.objects.filter(operation__in=income_operations).order_by("title")
        assert scenarios.count() == 2

    def _assert_filters_works(self, api_client, income_1):
        # --- Проверки через список транзакций и фильтры
        dates_query = (
            f"date__gte={self.start_date.isoformat()}&date__lte={self.end_date.isoformat()}"
        )

        # всего
        list_response_1 = api_client.get(f"/api/transactions/?{dates_query}")
        assert list_response_1.status_code == status.HTTP_200_OK
        _, total_count = _extract_items(list_response_1)
        assert total_count == self.expected_total

        # по типам
        income_response = api_client.get(f"/api/transactions/?type=income&{dates_query}")
        items_income, count_income = _extract_items(income_response)
        assert count_income == self.days * self.incomes_per_day

        expense_response = api_client.get(f"/api/transactions/?type=expense&{dates_query}")
        items_expense, count_expense = _extract_items(expense_response)
        assert count_expense == self.days * self.expenses_per_day

        transfer_response = api_client.get(f"/api/transactions/?type=transfer&{dates_query}")
        items_transfer, count_transfer = _extract_items(transfer_response)
        assert count_transfer == self.days * self.transfers_per_day

        # переводы по целевым счетам (проверяем «накопления» и «ипотеку»)
        savings_response = api_client.get(
            f"/api/transactions/?type=transfer&to_account={income_1.scenario.rules.get(order=1).target_account_id}&{dates_query}"
        )
        _, count_savings = _extract_items(savings_response)
        # в «Накопления» идут 2 перевода в день (200 из income_1 и 100 из income_2)
        assert count_savings == self.days * 2

        mortgage_response = api_client.get(
            f"/api/transactions/?type=transfer&to_account={income_1.scenario.rules.get(order=2).target_account_id}&{dates_query}"
        )
        _, count_mortgage = _extract_items(mortgage_response)
        # в «Ипотеку» идёт 1 перевод в день (300 из income_1)
        assert count_mortgage == self.days * 1

        # переводы должны уходить с основного счёта
        response_from_main_transfer = api_client.get(
            f"/api/transactions/?type=transfer&from_account={income_1.to_account_id}&{dates_query}"
        )
        _, count_from_main_transfer = _extract_items(response_from_main_transfer)
        assert count_from_main_transfer == count_transfer
