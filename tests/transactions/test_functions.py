from datetime import date

import pytest
from regular_operations.models import RegularOperationPeriodType
from transactions.views import _is_transaction_day


@pytest.mark.parametrize(
    ["created_date", "current_date", "period_interval", "period_type", "expected"],
    [
        # === DAY ===
        pytest.param(
            date(2025, 1, 1),
            date(2025, 1, 1),
            1,
            RegularOperationPeriodType.DAY,
            True,
            id="interval=every 1 DAY; same day; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            date(2025, 1, 2),
            1,
            RegularOperationPeriodType.DAY,
            True,
            id="interval=every 1 DAY; next day; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            date(2025, 1, 4),
            3,
            RegularOperationPeriodType.DAY,
            True,
            id="interval=every 3 DAY; exact multiple; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            date(2025, 1, 5),
            3,
            RegularOperationPeriodType.DAY,
            False,
            id="interval=every 3 DAY; not multiple; UNEXPECTED",
        ),
        # === WEEK ===
        pytest.param(
            date(2025, 1, 1),
            date(2025, 1, 15),  # если 01.01.2025 — среда, 15.01 — тоже среда (2 недели)
            2,
            RegularOperationPeriodType.WEEK,
            True,
            id="interval=every 2 WEEK; same weekday after 2 weeks; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            date(2025, 1, 8),  # неделя спустя
            2,
            RegularOperationPeriodType.WEEK,
            False,
            id="interval=every 2 WEEK; only 1 week passed; UNEXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            date(2025, 1, 16),  # четверг
            2,
            RegularOperationPeriodType.WEEK,
            False,
            id="interval=every 2 WEEK; wrong weekday; UNEXPECTED",
        ),
        # === MONTH ===
        pytest.param(
            date(2025, 1, 1),
            date(2025, 2, 1),
            1,
            RegularOperationPeriodType.MONTH,
            True,
            id="interval=every 1 MONTH; first day; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 5),
            date(2025, 2, 5),
            1,
            RegularOperationPeriodType.MONTH,
            True,
            id="interval=every 1 MONTH; fifth day; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            date(2025, 3, 1),
            2,
            RegularOperationPeriodType.MONTH,
            True,
            id="interval=every 2 MONTH; exact 2 months later; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            date(2025, 2, 1),
            2,
            RegularOperationPeriodType.MONTH,
            False,
            id="interval=every 2 MONTH; too early; UNEXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            date(2025, 2, 2),
            1,
            RegularOperationPeriodType.MONTH,
            False,
            id="interval=every 1 MONTH; wrong day of month; UNEXPECTED",
        ),
        pytest.param(
            date(2025, 1, 31),
            date(2025, 2, 28),
            1,
            RegularOperationPeriodType.MONTH,
            True,
            id="interval=every 1 MONTH; created 31st -> Feb last day (28); EXPECTED",
        ),
    ],
)
def test_is_transaction_day(current_date, period_type, period_interval, created_date, expected):
    result = _is_transaction_day(created_date, current_date, period_type, period_interval)
    assert result is expected
