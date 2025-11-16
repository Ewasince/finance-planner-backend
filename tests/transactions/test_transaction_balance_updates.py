from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Final

from core.bootstrap import ACCOUNT_UUID_4, ACCOUNT_UUID_5, DEFAULT_TIME, ACCOUNT_UUID_6
from freezegun import freeze_time
import pytest
from rest_framework import status
from transactions.models import TransactionType


pytestmark = pytest.mark.django_db


ACCOUNT_CREATED_AT = DEFAULT_TIME + timedelta(days=1)
TRANSACTION_CREATED_AT = DEFAULT_TIME + timedelta(days=5)
TRANSACTION_UPDATED_AT = DEFAULT_TIME + timedelta(days=6)


TRANSACTION_AMOUNT: Final[Decimal] = Decimal("200.00")
TRANSACTION_AMOUNT_NEGATIVE: Final[Decimal] = TRANSACTION_AMOUNT * Decimal("-1.00")
TRANSACTION_UPDATED_AMOUNT = Decimal("100.00")
TRANSACTION_UPDATED_AMOUNT_NEGATIVE = TRANSACTION_UPDATED_AMOUNT * Decimal("-1.00")


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
    other_user,
    other_api_client,
    payload,
    from_side: tuple[Decimal, datetime],
    to_side: tuple[Decimal, datetime],
):
    from_account = account_4
    to_account = account_5

    from_initial_balance = from_account.current_balance
    to_initial_balance = to_account.current_balance

    with freeze_time(TRANSACTION_CREATED_AT):
        response = other_api_client.post(
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
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.EXPENSE,
                "description": "expense_update_confirmed",
                "from_account": ACCOUNT_UUID_4,
                "confirmed": True,
            },
            (TRANSACTION_UPDATED_AMOUNT_NEGATIVE, TRANSACTION_UPDATED_AT),
            (Decimal("0"), DEFAULT_TIME),  # to: не участвует
            id="expense_confirmed",
        ),
        pytest.param(
            {
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.EXPENSE,
                "description": "expense_update_not_confirmed",
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
                "description": "income_update_confirmed",
                "to_account": ACCOUNT_UUID_5,
                "confirmed": True,
            },
            (Decimal("0"), DEFAULT_TIME),
            (TRANSACTION_UPDATED_AMOUNT, TRANSACTION_UPDATED_AT),
            id="income_confirmed",
        ),
        pytest.param(
            {
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.INCOME,
                "description": "income_update_not_confirmed",
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
                "description": "transfer_update_confirmed",
                "from_account": ACCOUNT_UUID_4,
                "to_account": ACCOUNT_UUID_5,
                "confirmed": True,
            },
            (TRANSACTION_UPDATED_AMOUNT_NEGATIVE, TRANSACTION_UPDATED_AT),
            (TRANSACTION_UPDATED_AMOUNT, TRANSACTION_UPDATED_AT),
            id="transfer_confirmed",
        ),
        pytest.param(
            {
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.TRANSFER,
                "description": "transfer_update_not_confirmed",
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
def test_transaction_update_recomputes_balances(
    other_api_client, other_user, account_4, account_5, payload, from_side, to_side
):
    from_account = account_4
    to_account = account_5

    base_from_balance = from_account.current_balance
    base_to_balance = to_account.current_balance

    # создаём транзакцию
    with freeze_time(TRANSACTION_CREATED_AT):
        create_response = other_api_client.post(
            "/api/transactions/",
            {
                **payload,
                "amount": TRANSACTION_AMOUNT,
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.data
        transaction_id = create_response.data["id"]

    from_delta, from_updated_expect = from_side
    to_delta, to_updated_expect = to_side

    # обновляем amount
    with freeze_time(TRANSACTION_UPDATED_AT):
        update_response = other_api_client.patch(
            f"/api/transactions/{transaction_id}/",
            {"amount": TRANSACTION_UPDATED_AMOUNT},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK, update_response.data
        from_account.refresh_from_db()
        to_account.refresh_from_db()

    assert from_account.current_balance == base_from_balance + from_delta
    assert to_account.current_balance == base_to_balance + to_delta

    assert from_account.current_balance_updated == from_updated_expect
    assert to_account.current_balance_updated == to_updated_expect


def test_transaction_confirm_toggle_return_400(other_api_client, other_user, account_4, account_5):
    with freeze_time(TRANSACTION_CREATED_AT):
        create_response = other_api_client.post(
            "/api/transactions/",
            {
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.TRANSFER,
                "description": "confirm_toggle_transfer",
                "from_account": ACCOUNT_UUID_4,
                "to_account": ACCOUNT_UUID_5,
                "confirmed": True,
                "amount": TRANSACTION_AMOUNT,
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.data
        transaction_id = create_response.data["id"]

    # снимаем галочку confirmed
    with freeze_time(TRANSACTION_UPDATED_AT):
        update_response = other_api_client.patch(
            f"/api/transactions/{transaction_id}/",
            {"confirmed": False},
            format="json",
        )
        assert update_response.status_code == status.HTTP_400_BAD_REQUEST


def test_transaction_description_update_does_not_touch_balances(
    other_api_client, other_user, account_4, account_5
):
    from_account = account_4
    to_account = account_5

    base_from_balance = from_account.current_balance
    base_to_balance = to_account.current_balance
    # создаём транзакцию
    with freeze_time(TRANSACTION_CREATED_AT):
        create_response = other_api_client.post(
            "/api/transactions/",
            {
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.TRANSFER,
                "description": "original description",
                "from_account": ACCOUNT_UUID_4,
                "to_account": ACCOUNT_UUID_5,
                "confirmed": True,
                "amount": TRANSACTION_AMOUNT,
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.data
        transaction_id = create_response.data["id"]
        from_account.refresh_from_db()
        to_account.refresh_from_db()
        created_from_balance = from_account.current_balance
        created_to_balance = to_account.current_balance

    # sanity-check: создание действительно изменило баланс
    assert created_from_balance == base_from_balance - TRANSACTION_AMOUNT
    assert created_to_balance == base_to_balance + TRANSACTION_AMOUNT

    # меняем только описание
    with freeze_time(TRANSACTION_UPDATED_AT):
        update_response = other_api_client.patch(
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
    assert from_account.current_balance_updated == TRANSACTION_CREATED_AT
    assert to_account.current_balance_updated == TRANSACTION_CREATED_AT


@pytest.mark.parametrize(
    ["update_payload", "side_4", "side_5", "side_6"],
    [
        pytest.param(
            {
                "amount": TRANSACTION_UPDATED_AMOUNT,
            },
            (TRANSACTION_UPDATED_AMOUNT_NEGATIVE, TRANSACTION_UPDATED_AT),
            (TRANSACTION_UPDATED_AMOUNT, TRANSACTION_UPDATED_AT),
            (Decimal("0"), DEFAULT_TIME),
            id="update_amount_only",
        ),
        pytest.param(
            {
                "from_account": ACCOUNT_UUID_6,
            },
            (Decimal("0"), TRANSACTION_UPDATED_AT),
            (TRANSACTION_AMOUNT, TRANSACTION_CREATED_AT),
            (TRANSACTION_AMOUNT_NEGATIVE, TRANSACTION_UPDATED_AT),
            id="update_from_only",
        ),
        pytest.param(
            {
                "to_account": ACCOUNT_UUID_6,
            },
            (TRANSACTION_AMOUNT_NEGATIVE, TRANSACTION_CREATED_AT),
            (Decimal("0"), TRANSACTION_UPDATED_AT),
            (TRANSACTION_AMOUNT, TRANSACTION_UPDATED_AT),
            id="update_to_only",
        ),
        pytest.param(
            {
                "from_account": ACCOUNT_UUID_5,
                "to_account": ACCOUNT_UUID_6,
            },
            (Decimal("0"), TRANSACTION_UPDATED_AT),
            (TRANSACTION_AMOUNT_NEGATIVE, TRANSACTION_UPDATED_AT),
            (TRANSACTION_AMOUNT, TRANSACTION_UPDATED_AT),
            id="update_from_and_to",
        ),
        pytest.param(
            {
                "from_account": ACCOUNT_UUID_6,
                "amount": TRANSACTION_UPDATED_AMOUNT,
            },
            (Decimal("0"), TRANSACTION_UPDATED_AT),
            (TRANSACTION_UPDATED_AMOUNT, TRANSACTION_UPDATED_AT),
            (TRANSACTION_UPDATED_AMOUNT_NEGATIVE, TRANSACTION_UPDATED_AT),
            id="update_from_and_amount",
        ),
        pytest.param(
            {
                "to_account": ACCOUNT_UUID_6,
                "amount": TRANSACTION_UPDATED_AMOUNT,
            },
            (TRANSACTION_UPDATED_AMOUNT_NEGATIVE, TRANSACTION_UPDATED_AT),
            (Decimal("0"), TRANSACTION_UPDATED_AT),
            (TRANSACTION_UPDATED_AMOUNT, TRANSACTION_UPDATED_AT),
            id="update_to_and_amount",
        ),
        pytest.param(
            {
                "from_account": ACCOUNT_UUID_5,
                "to_account": ACCOUNT_UUID_6,
                "amount": TRANSACTION_UPDATED_AMOUNT,
            },
            (Decimal("0"), TRANSACTION_UPDATED_AT),
            (TRANSACTION_UPDATED_AMOUNT_NEGATIVE, TRANSACTION_UPDATED_AT),
            (TRANSACTION_UPDATED_AMOUNT, TRANSACTION_UPDATED_AT),
            id="update_from_to_and_amount",
        ),
    ],
)
def test_transaction_update_accounts_and_amount_combinations(
    other_api_client,
    other_user,
    account_4,
    account_5,
    account_6,
    update_payload,
    side_4,
    side_5,
    side_6,
):
    base_4 = account_4.current_balance
    base_5 = account_5.current_balance
    base_6 = account_6.current_balance

    with freeze_time(TRANSACTION_CREATED_AT):
        create_response = other_api_client.post(
            "/api/transactions/",
            {
                "date": TRANSACTION_CREATED_AT.strftime("%Y-%m-%d"),
                "type": TransactionType.TRANSFER,
                "description": "update_accounts_and_amount",
                "from_account": ACCOUNT_UUID_4,
                "to_account": ACCOUNT_UUID_5,
                "confirmed": True,
                "amount": TRANSACTION_AMOUNT,
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.data
        transaction_id = create_response.data["id"]

    with freeze_time(TRANSACTION_UPDATED_AT):
        update_response = other_api_client.patch(
            f"/api/transactions/{transaction_id}/",
            update_payload,
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK, update_response.data
        account_4.refresh_from_db()
        account_5.refresh_from_db()
        account_6.refresh_from_db()

    side_4_delta, side_4_updated = side_4
    side_5_delta, side_5_updated = side_5
    side_6_delta, side_6_updated = side_6

    assert account_4.current_balance == base_4 + side_4_delta
    assert account_5.current_balance == base_5 + side_5_delta
    assert account_6.current_balance == base_6 + side_6_delta

    assert account_4.current_balance_updated == side_4_updated
    assert account_5.current_balance_updated == side_5_updated
    assert account_6.current_balance_updated == side_6_updated

