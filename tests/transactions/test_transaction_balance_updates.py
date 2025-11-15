from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Final

from accounts.models import Account
from core.bootstrap import ACCOUNT_UUID_4, ACCOUNT_UUID_5, DEFAULT_TIME
from freezegun import freeze_time
import pytest
from rest_framework import status
from transactions.models import TransactionType


pytestmark = pytest.mark.django_db


ACCOUNT_CREATED_AT = DEFAULT_TIME + timedelta(days=1)
TRANSACTION_CREATED_AT = DEFAULT_TIME + timedelta(days=5)
TRANSACTION_UPDATED_AT = DEFAULT_TIME + timedelta(days=6)


@dataclass
class TransactionCase:
    id: str
    type: str
    include_from: bool
    include_to: bool
    from_multiplier: Decimal
    to_multiplier: Decimal


TRANSACTION_CASES: list[TransactionCase] = [
    TransactionCase(
        id="from_account_only",
        type=TransactionType.EXPENSE,
        include_from=True,
        include_to=False,
        from_multiplier=Decimal("-1"),
        to_multiplier=Decimal("0"),
    ),
    TransactionCase(
        id="to_account_only",
        type=TransactionType.INCOME,
        include_from=False,
        include_to=True,
        from_multiplier=Decimal("0"),
        to_multiplier=Decimal("1"),
    ),
    TransactionCase(
        id="transfer",
        type=TransactionType.TRANSFER,
        include_from=True,
        include_to=True,
        from_multiplier=Decimal("-1"),
        to_multiplier=Decimal("1"),
    ),
]


def _prepare_payload(
    case: TransactionCase,
    amount: Decimal,
    confirmed: bool,
    from_account: Account,
    to_account: Account,
) -> dict:
    payload = {
        "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d").split("T")[0],
        "type": case.type,
        "amount": f"{amount:.2f}",
        "confirmed": confirmed,
        "description": f"case-{case.id}",
    }
    if case.include_from:
        payload["from_account"] = str(from_account.id)
    if case.include_to:
        payload["to_account"] = str(to_account.id)
    return payload


TRANSACTION_AMOUNT: Final[Decimal] = Decimal("150.00")
TRANSACTION_AMOUNT_NEGATIVE: Final[Decimal] = TRANSACTION_AMOUNT * Decimal("-1.00")


@pytest.mark.parametrize(
    ["payload", "from_side", "to_side"],
    [
        # EXPENSE
        pytest.param(
            {
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.EXPENSE,
                "description": "desc",
                "from_account": ACCOUNT_UUID_4,
                "confirmed": True,
            },
            (TRANSACTION_AMOUNT_NEGATIVE, TRANSACTION_CREATED_AT),
            (Decimal("0"), DEFAULT_TIME),
            id="expense_confirmed",
        ),
        pytest.param(
            {
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.EXPENSE,
                "description": "desc",
                "from_account": ACCOUNT_UUID_4,
                "confirmed": False,
            },
            (Decimal("0"), DEFAULT_TIME),
            (Decimal("0"), DEFAULT_TIME),
            id="expense_not_confirmed",
        ),
        # INCOME
        pytest.param(
            {
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.INCOME,
                "description": "desc",
                "to_account": ACCOUNT_UUID_5,
                "confirmed": True,
            },
            (Decimal("0"), DEFAULT_TIME),
            (TRANSACTION_AMOUNT, TRANSACTION_CREATED_AT),
            id="income_confirmed",
        ),
        pytest.param(
            {
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.INCOME,
                "description": "desc",
                "to_account": ACCOUNT_UUID_5,
                "confirmed": False,
            },
            (Decimal("0"), DEFAULT_TIME),
            (Decimal("0"), DEFAULT_TIME),
            id="income_not_confirmed",
        ),
        # TRANSFER
        pytest.param(
            {
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.TRANSFER,
                "description": "desc",
                "from_account": ACCOUNT_UUID_4,
                "to_account": ACCOUNT_UUID_5,
                "confirmed": True,
            },
            (TRANSACTION_AMOUNT_NEGATIVE, TRANSACTION_CREATED_AT),
            (TRANSACTION_AMOUNT, TRANSACTION_CREATED_AT),
            id="transfer_confirmed",
        ),
        pytest.param(
            {
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.TRANSFER,
                "description": "desc",
                "from_account": ACCOUNT_UUID_4,
                "to_account": ACCOUNT_UUID_5,
                "confirmed": False,
            },
            (Decimal("0"), DEFAULT_TIME),
            (Decimal("0"), DEFAULT_TIME),
            id="transfer_not_confirmed",
        ),
    ],
)
def test_transaction_creation_updates_balances(
    account_4,
    account_5,
    account_6,
    main_user,
    api_client,
    payload,
    from_side: tuple[Decimal, datetime],
    to_side: tuple[Decimal, datetime],
):
    from_account = account_4
    to_account = account_5

    from_initial_balance = from_account.current_balance
    to_initial_balance = to_account.current_balance

    with freeze_time(TRANSACTION_CREATED_AT):
        response = api_client.post(
            "/api/transactions/",
            {
                **payload,
                "amount": TRANSACTION_AMOUNT,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        from_account.refresh_from_db()
        to_account.refresh_from_db()

        from_delta, from_updated_expect = from_side
        to_delta, to_updated_expect = to_side

        assert from_account.current_balance == from_initial_balance + from_delta
        assert to_account.current_balance == to_initial_balance + to_delta

        assert from_account.current_balance_updated == from_updated_expect
        assert to_account.current_balance_updated == to_updated_expect
