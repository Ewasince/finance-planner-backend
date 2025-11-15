from datetime import date, timedelta
from decimal import Decimal

from accounts.models import AccountType
from accounts.views import _calculate_account_start_delta
from core.bootstrap import DEFAULT_DATE
import pytest
from transactions.models import Transaction, TransactionType


pytestmark = pytest.mark.django_db


def _create_transaction(
    *, user, account, amount: str, tx_date: date, incoming: bool
) -> Transaction:
    if incoming:
        return Transaction.objects.create(
            user=user,
            date=tx_date,
            type=TransactionType.INCOME,
            amount=Decimal(amount),
            to_account=account,
        )
    return Transaction.objects.create(
        user=user,
        date=tx_date,
        type=TransactionType.EXPENSE,
        amount=Decimal(amount),
        from_account=account,
    )


@pytest.mark.parametrize(
    ["current_date", "start_date", "expected"],
    [
        # start_date == current_date
        pytest.param(
            DEFAULT_DATE,
            DEFAULT_DATE,
            Decimal("0.00"),
            id="dates_match",
        ),
        # start_date > current_date
        pytest.param(
            DEFAULT_DATE,
            DEFAULT_DATE + timedelta(days=1),
            Decimal("100.00"),
            id="start_after_current (1)",
        ),
        pytest.param(
            DEFAULT_DATE,
            DEFAULT_DATE + timedelta(days=2),
            Decimal("-900.00"),
            id="start_after_current (2)",
        ),
        # start_date < current_date
        pytest.param(
            DEFAULT_DATE,
            DEFAULT_DATE - timedelta(days=1),
            Decimal("10.00"),
            id="start_before_current (1)",
        ),
        pytest.param(
            DEFAULT_DATE,
            DEFAULT_DATE - timedelta(days=2),
            Decimal("-40.00"),
            id="start_before_current (2)",
        ),
    ],
)
def test_calculate_account_start_delta(
    main_user,
    create_account,
    start_date,
    current_date,
    expected,
):
    account = create_account(main_user, "Test", AccountType.MAIN)

    # создаём транзакции по спецификациям
    for amount, day_offset, incoming in [
        # баланс на конец дня — 0
        ("5000.00", -3, True),  # 5000
        ("500.00", -2, False),  # 4500
        ("50.00", -1, True),  # 4550
        ("10.00", 0, False),  # 4540 – стартовый баланс
        ("100.00", 1, True),  # 4640
        ("1000.00", 2, False),  # 3640
        ("10000.00", 3, True),  # 13640
    ]:
        _create_transaction(
            user=main_user,
            account=account,
            amount=amount,
            tx_date=DEFAULT_DATE + timedelta(days=day_offset),
            incoming=incoming,
        )

    delta = _calculate_account_start_delta(
        account=account,
        actual_transactions=Transaction.objects.filter(user=main_user).order_by("date"),
        start_date=start_date,
        current_date=current_date,
    )

    assert delta == expected
