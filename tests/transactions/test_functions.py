from datetime import date

import pytest
from regular_operations.models import RegularOperationPeriodType
from transactions.views import _is_transaction_day


@pytest.mark.parametrize(
    ["created_date", "deleted_date", "current_date", "period_interval", "period_type", "expected"],
    [
        # === DAY ===
        pytest.param(
            date(2025, 1, 1),
            None,
            date(2025, 1, 1),
            1,
            RegularOperationPeriodType.DAY,
            True,
            id="interval=every 1 DAY; same day; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            None,
            date(2025, 1, 2),
            1,
            RegularOperationPeriodType.DAY,
            True,
            id="interval=every 1 DAY; next day; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            None,
            date(2025, 1, 4),
            3,
            RegularOperationPeriodType.DAY,
            True,
            id="interval=every 3 DAY; exact multiple; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            None,
            date(2025, 1, 5),
            3,
            RegularOperationPeriodType.DAY,
            False,
            id="interval=every 3 DAY; not multiple; UNEXPECTED",
        ),
        # === WEEK ===
        pytest.param(
            date(2025, 1, 1),
            None,
            date(2025, 1, 15),  # если 01.01.2025 — среда, 15.01 — тоже среда (2 недели)
            2,
            RegularOperationPeriodType.WEEK,
            True,
            id="interval=every 2 WEEK; same weekday after 2 weeks; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            None,
            date(2025, 1, 8),  # неделя спустя
            2,
            RegularOperationPeriodType.WEEK,
            False,
            id="interval=every 2 WEEK; only 1 week passed; UNEXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            None,
            date(2025, 1, 16),  # четверг
            2,
            RegularOperationPeriodType.WEEK,
            False,
            id="interval=every 2 WEEK; wrong weekday; UNEXPECTED",
        ),
        # === MONTH ===
        pytest.param(
            date(2025, 1, 1),
            None,
            date(2025, 2, 1),
            1,
            RegularOperationPeriodType.MONTH,
            True,
            id="interval=every 1 MONTH; first day; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 5),
            None,
            date(2025, 2, 5),
            1,
            RegularOperationPeriodType.MONTH,
            True,
            id="interval=every 1 MONTH; fifth day; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            None,
            date(2025, 3, 1),
            2,
            RegularOperationPeriodType.MONTH,
            True,
            id="interval=every 2 MONTH; exact 2 months later; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            None,
            date(2025, 2, 1),
            2,
            RegularOperationPeriodType.MONTH,
            False,
            id="interval=every 2 MONTH; too early; UNEXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            None,
            date(2025, 2, 2),
            1,
            RegularOperationPeriodType.MONTH,
            False,
            id="interval=every 1 MONTH; wrong day of month; UNEXPECTED",
        ),
        pytest.param(
            date(2025, 1, 31),
            None,
            date(2025, 2, 28),
            1,
            RegularOperationPeriodType.MONTH,
            True,
            id="interval=every 1 MONTH; created 31st -> Feb last day (28); EXPECTED",
        ),
        # === DELETED BOUNDARY: DAY ===
        pytest.param(
            date(2025, 1, 1),
            date(2025, 1, 10),
            date(2025, 1, 9),
            1,
            RegularOperationPeriodType.DAY,
            True,
            id="deleted boundary; day before deleted_date; EXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            date(2025, 1, 10),
            date(2025, 1, 10),
            1,
            RegularOperationPeriodType.DAY,
            False,
            id="deleted boundary; current_date == deleted_date; UNEXPECTED",
        ),
        pytest.param(
            date(2025, 1, 1),
            date(2025, 1, 10),
            date(2025, 1, 13),  # кратно 3 дням, но после даты удаления
            3,
            RegularOperationPeriodType.DAY,
            False,
            id="deleted boundary; after deleted_date even if interval matches; UNEXPECTED",
        ),
    ],
)
def test_is_transaction_day(
    created_date: date,
    deleted_date: date | None,
    current_date: date,
    period_interval: int,
    period_type: str,
    expected: bool,
):
    assert (
        _is_transaction_day(
            created_date=created_date,
            deleted_date=deleted_date,
            current_date=current_date,
            period_type=period_type,
            period_interval=period_interval,
        )
        is expected
    )
