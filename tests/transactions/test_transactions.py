from datetime import timedelta

from accounts.models import AccountType
from freezegun import freeze_time
import pytest
from regular_operations.models import RegularOperation, RegularOperationType
from rest_framework import status
from rest_framework.test import APIClient
from scenarios.models import Scenario
from transactions.models import TransactionType

from tests.constants import (
    DEFAULT_TIME,
    MAIN_ACCOUNT_UUID,
    SECOND_ACCOUNT_UUID,
)


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
def test_calculate_creates_transactions_with_scenarios(fresh_db, bootstrap_owner):
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

    # Окно расчёта: 3 дня
    start_date = DEFAULT_TIME.date()
    end_date = start_date + timedelta(days=2)

    income_operations = RegularOperation.objects.filter(
        type=RegularOperationType.INCOME
    ).order_by("title")
    assert income_operations.count() == 2
    income_1, income_2 = income_operations

    expense_operations = RegularOperation.objects.filter(
        type=RegularOperationType.EXPENSE
    ).order_by("title")
    assert expense_operations.count() == 2

    scenarios = Scenario.objects.filter(operation__in=income_operations).order_by("title")
    assert scenarios.count() == 2

    # --- Вызов калькуляции
    calc_payload = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        # "dry_run": False  # по умолчанию False — транзакции должны создаться
    }
    client = APIClient()
    client.force_authenticate(user=bootstrap_owner)

    calc_resp = client.post(
        "/api/transactions/calculate/", calc_payload, format="json"
    )
    assert calc_resp.status_code == status.HTTP_200_OK, calc_resp.data

    # Ожидаемое количество:
    days = 3
    incomes_per_day = 2
    expenses_per_day = 2
    transfers_per_day = 3  # (2 правила из income_1) + (1 правило из income_2)
    expected_total = days * (incomes_per_day + expenses_per_day + transfers_per_day)

    assert calc_resp.data["transactions_created"] == expected_total

    # --- Проверки через список транзакций и фильтры
    dates_query = f"date__gte={start_date.isoformat()}&date__lte={end_date.isoformat()}"

    # всего
    list_response_1 = client.get(f"/api/transactions/?{dates_query}")
    assert list_response_1.status_code == status.HTTP_200_OK
    _, total_count = _extract_items(list_response_1)
    assert total_count == expected_total

    # по типам
    income_response = client.get(
        f"/api/transactions/?type=income&{dates_query}"
    )
    items_income, count_income = _extract_items(income_response)
    assert count_income == days * incomes_per_day

    expense_response = client.get(
        f"/api/transactions/?type=expense&{dates_query}"
    )
    items_expense, count_expense = _extract_items(expense_response)
    assert count_expense == days * expenses_per_day

    transfer_response = client.get(
        f"/api/transactions/?type=transfer&{dates_query}"
    )
    items_transfer, count_transfer = _extract_items(transfer_response)
    assert count_transfer == days * transfers_per_day

    # переводы по целевым счетам (проверяем «накопления» и «ипотеку»)
    savings_response = client.get(
        f"/api/transactions/?type=transfer&to_account={income_1.scenario.rules.get(order=1).target_account_id}&{dates_query}"
    )
    _, count_savings = _extract_items(savings_response)
    # в «Накопления» идут 2 перевода в день (200 из income_1 и 100 из income_2)
    assert count_savings == days * 2

    mortgage_response = client.get(
        f"/api/transactions/?type=transfer&to_account={income_1.scenario.rules.get(order=2).target_account_id}&{dates_query}"
    )
    _, count_mortgage = _extract_items(mortgage_response)
    # в «Ипотеку» идёт 1 перевод в день (300 из income_1)
    assert count_mortgage == days * 1

    # переводы должны уходить с основного счёта
    response_from_main_transfer = client.get(
        f"/api/transactions/?type=transfer&from_account={income_1.to_account_id}&{dates_query}"
    )
    _, count_from_main_transfer = _extract_items(response_from_main_transfer)
    assert count_from_main_transfer == count_transfer

    # --- Дополнительно: повторный вызов калькуляции не должен задвоить транзакции
    calculate_response_2 = client.post(
        "/api/transactions/calculate/", calc_payload, format="json"
    )
    assert calculate_response_2.status_code == status.HTTP_200_OK, calculate_response_2.data

    list_response_2 = client.get(f"/api/transactions/?{dates_query}")
    _, total_count_after = _extract_items(list_response_2)
    assert total_count_after == expected_total
