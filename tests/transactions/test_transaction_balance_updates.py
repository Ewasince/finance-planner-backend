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


@pytest.mark.parametrize("confirmed", [True, False], ids=["confirmed", "not_confirmed"])
@pytest.mark.parametrize("case", TRANSACTION_CASES, ids=lambda case: f"update-{case.id}")
def test_transaction_update_recomputes_balances(transaction_env, case, confirmed):
    client, user, from_account, to_account = transaction_env()
    base_from_balance = from_account.current_balance
    base_to_balance = to_account.current_balance
    base_from_updated = from_account.current_balance_updated
    base_to_updated = to_account.current_balance_updated
    amount = Decimal("120.00")
    updated_amount = Decimal("70.00")

    with freeze_time(TRANSACTION_CREATED_AT):
        payload = _prepare_payload(case, amount, confirmed, from_account, to_account)
        create_response = client.post("/api/transactions/", payload, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.data
        transaction_id = Transaction.objects.filter(user=user).order_by("-created_at").first().id

    with freeze_time(TRANSACTION_UPDATED_AT):
        update_response = client.patch(
            f"/api/transactions/{transaction_id}/",
            {"amount": f"{updated_amount:.2f}"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK, update_response.data
        from_account.refresh_from_db()
        to_account.refresh_from_db()
        expected_timestamp = timezone.now()

    expected_from_balance = base_from_balance + (
        case.from_multiplier * (updated_amount if confirmed else Decimal("0"))
    )
    expected_to_balance = base_to_balance + (
        case.to_multiplier * (updated_amount if confirmed else Decimal("0"))
    )

    assert from_account.current_balance == expected_from_balance
    assert to_account.current_balance == expected_to_balance

    if confirmed and case.from_multiplier != Decimal("0"):
        assert from_account.current_balance_updated == expected_timestamp
    else:
        assert from_account.current_balance_updated == base_from_updated

    if confirmed and case.to_multiplier != Decimal("0"):
        assert to_account.current_balance_updated == expected_timestamp
    else:
        assert to_account.current_balance_updated == base_to_updated


def test_transaction_confirm_toggle_reverts_balances(transaction_env):
    client, user, from_account, to_account = transaction_env()
    base_from_balance = from_account.current_balance
    base_to_balance = to_account.current_balance
    amount = Decimal("80.00")

    with freeze_time(TRANSACTION_CREATED_AT):
        payload = _prepare_payload(TRANSACTION_CASES[2], amount, True, from_account, to_account)
        create_response = client.post("/api/transactions/", payload, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED
        transaction_id = Transaction.objects.filter(user=user).order_by("-created_at").first().id

    with freeze_time(TRANSACTION_UPDATED_AT):
        expected_timestamp = timezone.now()
        update_response = client.patch(
            f"/api/transactions/{transaction_id}/",
            {"confirmed": False},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        from_account.refresh_from_db()
        to_account.refresh_from_db()

    assert from_account.current_balance == base_from_balance
    assert to_account.current_balance == base_to_balance
    assert from_account.current_balance_updated == expected_timestamp
    assert to_account.current_balance_updated == expected_timestamp


def test_transaction_description_update_does_not_touch_balances(transaction_env):
    client, user, from_account, to_account = transaction_env()
    base_from_balance = from_account.current_balance
    base_to_balance = to_account.current_balance

    with freeze_time(TRANSACTION_CREATED_AT):
        payload = _prepare_payload(
            TRANSACTION_CASES[0], Decimal("60.00"), True, from_account, to_account
        )
        create_response = client.post("/api/transactions/", payload, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED
        transaction_id = Transaction.objects.filter(user=user).order_by("-created_at").first().id
        from_account.refresh_from_db()
        to_account.refresh_from_db()
        created_from_balance = from_account.current_balance
        created_to_balance = to_account.current_balance
        created_from_updated = from_account.current_balance_updated
        created_to_updated = to_account.current_balance_updated

    with freeze_time(TRANSACTION_UPDATED_AT):
        update_response = client.patch(
            f"/api/transactions/{transaction_id}/",
            {"description": "updated description"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        from_account.refresh_from_db()
        to_account.refresh_from_db()

    assert from_account.current_balance == created_from_balance
    assert to_account.current_balance == created_to_balance
    assert from_account.current_balance_updated == created_from_updated
    assert to_account.current_balance_updated == created_to_updated
    assert base_from_balance != created_from_balance
