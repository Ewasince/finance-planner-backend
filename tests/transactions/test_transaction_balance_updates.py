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


@pytest.mark.parametrize(
    ["payload", "from_side", "to_side"],
    [
        # EXPENSE
        pytest.param(
            {
                "type": TransactionType.EXPENSE,
                "confirmed": True,
                "description": "expense_update_confirmed",
            },
            (Decimal("-1"), True),
            (Decimal("0"), False),
            id="expense_confirmed",
        ),
        pytest.param(
            {
                "type": TransactionType.EXPENSE,
                "confirmed": False,
                "description": "expense_update_not_confirmed",
            },
            (Decimal("-1"), False),
            (Decimal("0"), False),
            id="expense_not_confirmed",
        ),
        # INCOME
        pytest.param(
            {
                "type": TransactionType.INCOME,
                "confirmed": True,
                "description": "income_update_confirmed",
            },
            (Decimal("0"), False),
            (Decimal("1"), True),
            id="income_confirmed",
        ),
        pytest.param(
            {
                "type": TransactionType.INCOME,
                "confirmed": False,
                "description": "income_update_not_confirmed",
            },
            (Decimal("0"), False),
            (Decimal("1"), False),
            id="income_not_confirmed",
        ),
        # TRANSFER
        pytest.param(
            {
                "type": TransactionType.TRANSFER,
                "confirmed": True,
                "description": "transfer_update_confirmed",
            },
            (Decimal("-1"), True),
            (Decimal("1"), True),
            id="transfer_confirmed",
        ),
        pytest.param(
            {
                "type": TransactionType.TRANSFER,
                "confirmed": False,
                "description": "transfer_update_not_confirmed",
            },
            (Decimal("-1"), False),
            (Decimal("1"), False),
            id="transfer_not_confirmed",
        ),
    ],
)
def test_transaction_update_recomputes_balances(
    transaction_env, payload, from_side, to_side
):
    client, user, from_account, to_account = transaction_env()
    base_from_balance = from_account.current_balance
    base_to_balance = to_account.current_balance
    base_from_updated = from_account.current_balance_updated
    base_to_updated = to_account.current_balance_updated

    create_amount = Decimal("120.00")
    updated_amount = Decimal("70.00")

    create_body = {
        "date": _date_from_timestamp(TRANSACTION_CREATED_AT),
        "type": payload["type"],
        "amount": f"{create_amount:.2f}",
        "confirmed": payload["confirmed"],
        "description": payload["description"],
    }
    if payload["type"] in (TransactionType.EXPENSE, TransactionType.TRANSFER):
        create_body["from_account"] = str(from_account.id)
    if payload["type"] in (TransactionType.INCOME, TransactionType.TRANSFER):
        create_body["to_account"] = str(to_account.id)

    with freeze_time(TRANSACTION_CREATED_AT):
        create_response = client.post("/api/transactions/", create_body, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.data
        transaction_id = (
            Transaction.objects.filter(user=user).order_by("-created_at").first().id
        )

    from_multiplier, from_touches_balance = from_side
    to_multiplier, to_touches_balance = to_side

    with freeze_time(TRANSACTION_UPDATED_AT):
        expected_timestamp = timezone.now()
        update_response = client.patch(
            f"/api/transactions/{transaction_id}/",
            {"amount": f"{updated_amount:.2f}"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK, update_response.data
        from_account.refresh_from_db()
        to_account.refresh_from_db()

    effective_amount = updated_amount if payload["confirmed"] else Decimal("0")

    expected_from_balance = base_from_balance + from_multiplier * effective_amount
    expected_to_balance = base_to_balance + to_multiplier * effective_amount

    assert from_account.current_balance == expected_from_balance
    assert to_account.current_balance == expected_to_balance

    if payload["confirmed"] and from_touches_balance:
        assert from_account.current_balance_updated == expected_timestamp
    else:
        assert from_account.current_balance_updated == base_from_updated

    if payload["confirmed"] and to_touches_balance:
        assert to_account.current_balance_updated == expected_timestamp
    else:
        assert to_account.current_balance_updated == base_to_updated


@pytest.mark.parametrize(
    ["payload", "from_side", "to_side"],
    [
        pytest.param(
            {
                "type": TransactionType.TRANSFER,
                "description": "confirm_toggle_transfer",
            },
            (Decimal("0"), True),   # from: вернулись к базе, но timestamp обновился
            (Decimal("0"), True),   # to: то же самое
            id="transfer_confirm_true_to_false",
        ),
    ],
)
def test_transaction_confirm_toggle_reverts_balances(
    transaction_env, payload, from_side, to_side
):
    client, user, from_account, to_account = transaction_env()
    base_from_balance = from_account.current_balance
    base_to_balance = to_account.current_balance

    amount = Decimal("80.00")

    create_body = {
        "date": _date_from_timestamp(TRANSACTION_CREATED_AT),
        "type": payload["type"],
        "amount": f"{amount:.2f}",
        "confirmed": True,
        "description": payload["description"],
        "from_account": str(from_account.id),
        "to_account": str(to_account.id),
    }

    with freeze_time(TRANSACTION_CREATED_AT):
        create_response = client.post("/api/transactions/", create_body, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.data
        transaction_id = (
            Transaction.objects.filter(user=user).order_by("-created_at").first().id
        )

    from_delta, from_updates_timestamp = from_side
    to_delta, to_updates_timestamp = to_side

    with freeze_time(TRANSACTION_UPDATED_AT):
        expected_timestamp = timezone.now()
        update_response = client.patch(
            f"/api/transactions/{transaction_id}/",
            {"confirmed": False},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK, update_response.data
        from_account.refresh_from_db()
        to_account.refresh_from_db()

    assert from_account.current_balance == base_from_balance + from_delta
    assert to_account.current_balance == base_to_balance + to_delta

    if from_updates_timestamp:
        assert from_account.current_balance_updated == expected_timestamp
    if to_updates_timestamp:
        assert to_account.current_balance_updated == expected_timestamp


@pytest.mark.parametrize(
    ["payload", "from_side", "to_side"],
    [
        pytest.param(
            {
                "type": TransactionType.EXPENSE,
                "description": "original description",
            },
            (Decimal("-1"), True),
            (Decimal("0"), False),
            id="expense_description_update",
        ),
    ],
)
def test_transaction_description_update_does_not_touch_balances(
    transaction_env, payload, from_side, to_side
):
    client, user, from_account, to_account = transaction_env()
    base_from_balance = from_account.current_balance
    base_to_balance = to_account.current_balance

    amount = Decimal("60.00")

    create_body = {
        "date": _date_from_timestamp(TRANSACTION_CREATED_AT),
        "type": payload["type"],
        "amount": f"{amount:.2f}",
        "confirmed": True,
        "description": payload["description"],
        "from_account": str(from_account.id),
    }

    from_multiplier, _ = from_side
    to_multiplier, _ = to_side

    with freeze_time(TRANSACTION_CREATED_AT):
        create_response = client.post("/api/transactions/", create_body, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.data
        transaction_id = (
            Transaction.objects.filter(user=user).order_by("-created_at").first().id
        )
        from_account.refresh_from_db()
        to_account.refresh_from_db()
        created_from_balance = from_account.current_balance
        created_to_balance = to_account.current_balance
        created_from_updated = from_account.current_balance_updated
        created_to_updated = to_account.current_balance_updated

    # sanity-check: создание действительно изменило баланс
    effective_amount = amount  # confirmed=True
    assert created_from_balance == base_from_balance + from_multiplier * effective_amount
    assert created_to_balance == base_to_balance + to_multiplier * effective_amount

    with freeze_time(TRANSACTION_UPDATED_AT):
        update_response = client.patch(
            f"/api/transactions/{transaction_id}/",
            {"description": "updated description"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK, update_response.data
        from_account.refresh_from_db()
        to_account.refresh_from_db()

    # после обновления описания ничего не должно поменяться
    assert from_account.current_balance == created_from_balance
    assert to_account.current_balance == created_to_balance
    assert from_account.current_balance_updated == created_from_updated
    assert to_account.current_balance_updated == created_to_updated