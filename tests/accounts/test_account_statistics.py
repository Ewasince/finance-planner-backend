from datetime import timedelta
from decimal import Decimal

from freezegun import freeze_time
import pytest
from regular_operations.models import (
    RegularOperation,
    RegularOperationPeriodType,
    RegularOperationType,
)
from rest_framework import status
from scenarios.models import Scenario

from tests.constants import (
    DEFAULT_TIME,
    DEFAULT_TIME_WITH_OFFSET,
    MAIN_ACCOUNT_UUID,
    SECOND_ACCOUNT_UUID,
    THIRD_ACCOUNT_UUID,
)


pytestmark = pytest.mark.django_db


@freeze_time(DEFAULT_TIME)
def test_statistics_returns_daily_balances_from_db_truth(
    api_client,
    main_user,
    create_account,
    main_account,
    second_account,
    third_account,
):
    """
    Готовим данные так же, как в тесте calculate:
      - Основной счёт + два целевых (Накопления, Ипотека)
      - 2 дохода / 2 расхода / правила сценариев (2 перевода из дохода_1 и 1 перевод из дохода_2)
    Затем:
      - вызываем /api/transactions/calculate/ на 3 дня, чтобы создать транзакции
      - считаем дневные балансы по БД
      - проверяем, что ответ /api/transactions/statistics/ совпадает с расчётом из БД
    """

    # Окно расчёта: 3 дня (включительно)
    start_date = DEFAULT_TIME.date()
    end_date = start_date + timedelta(days=2)

    # Делаем операции дневными
    period_type = RegularOperationPeriodType.DAY
    period_interval = 1

    # --- Регулярные операции: доходы
    income_1 = RegularOperation.objects.create(
        user=main_user,
        title="Зарплата",
        description="Основной доход",
        amount=Decimal("1000.00"),
        type=RegularOperationType.INCOME,
        to_account=main_account,
        start_date=DEFAULT_TIME,
        end_date=DEFAULT_TIME_WITH_OFFSET,
        period_type=period_type,
        period_interval=period_interval,
        is_active=True,
    )
    income_2 = RegularOperation.objects.create(
        user=main_user,
        title="Фриланс",
        description="Доп. доход",
        amount=Decimal("500.00"),
        type=RegularOperationType.INCOME,
        to_account=main_account,
        start_date=DEFAULT_TIME,
        end_date=DEFAULT_TIME_WITH_OFFSET,
        period_type=period_type,
        period_interval=period_interval,
        is_active=True,
    )

    # --- Регулярные операции: расходы
    RegularOperation.objects.create(
        user=main_user,
        title="Повседневные траты",
        description="",
        amount=Decimal("100.00"),
        type=RegularOperationType.EXPENSE,
        from_account=main_account,
        start_date=DEFAULT_TIME,
        end_date=DEFAULT_TIME_WITH_OFFSET,
        period_type=period_type,
        period_interval=period_interval,
        is_active=True,
    )
    RegularOperation.objects.create(
        user=main_user,
        title="Питание",
        description="",
        amount=Decimal("50.00"),
        type=RegularOperationType.EXPENSE,
        from_account=main_account,
        start_date=DEFAULT_TIME,
        end_date=DEFAULT_TIME_WITH_OFFSET,
        period_type=period_type,
        period_interval=period_interval,
        is_active=True,
    )

    # --- Сценарии и правила
    scenario_1 = Scenario.objects.create(
        user=main_user,
        operation=income_1,
        title="Распределение зарплаты",
        description="",
        is_active=True,
    )
    scenario_1.rules.create(target_account=second_account, amount=Decimal("200.00"), order=1)
    scenario_1.rules.create(target_account=third_account, amount=Decimal("300.00"), order=2)

    scenario_2 = Scenario.objects.create(
        user=main_user,
        operation=income_2,
        title="Распределение фриланса",
        description="",
        is_active=True,
    )
    scenario_2.rules.create(target_account=second_account, amount=Decimal("100.00"), order=1)

    calc_payload = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    calc_resp = api_client.post("/api/transactions/calculate/", calc_payload, format="json")
    assert calc_resp.status_code == status.HTTP_200_OK, calc_resp.data

    statistics_payload = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
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
