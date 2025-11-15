from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal

from accounts.models import Account, AccountType
from accounts.views import _calculate_account_start_delta
from core.bootstrap import DEFAULT_DATE
import pytest
from transactions.models import Transaction


pytestmark = pytest.mark.django_db


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
    transactions_fabric: Callable[[Account], None],
):
    account = create_account(main_user, "Test", AccountType.MAIN)

    transactions_fabric(account)

    delta = _calculate_account_start_delta(
        account=account,
        actual_transactions=Transaction.objects.filter(user=main_user).order_by("date"),
        start_date=start_date,
        current_date=current_date,
    )

    assert delta == expected
