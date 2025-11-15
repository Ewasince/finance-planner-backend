from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal

from accounts.models import Account
from core.bootstrap import DEFAULT_DATE
import pytest
from transactions.models import Transaction, TransactionType


@pytest.fixture
def transactions_fabric(main_user) -> Callable[[Account], None]:
    def _inner(account: Account):
        # создаём транзакции по спецификациям
        for amount, day_offset, incoming in [
            # баланс на конец дня — 0
            ("5000.00", -3, True),  # 5000
            ("500.00", -2, False),  # 4500
            ("50.00", -1, True),  # 4550 — стартовый баланс
            ("10.00", 0, False),  # 4540 – баланс на конец первого дня
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

    return _inner


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
