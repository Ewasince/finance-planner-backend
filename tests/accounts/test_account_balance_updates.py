from datetime import timedelta
from decimal import Decimal

from accounts.models import Account, AccountType
from core.bootstrap import DEFAULT_TIME
from django.utils import timezone
from freezegun import freeze_time
import pytest
from rest_framework import status


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ["payload", "expected_balance"],
    [
        (
            {
                "name": "Накопления",
                "type": AccountType.ACCUMULATION,
                "description": "with balance",
                "current_balance": "150.00",
            },
            Decimal("150.00"),
        ),
        (
            {
                "name": "Накопления",
                "type": AccountType.ACCUMULATION,
                "description": "no balance",
            },
            Decimal("0.00"),
        ),
    ],
)
@freeze_time(DEFAULT_TIME)
def test_create_account_with_balance_sets_current_balance_updated(
    main_user,
    api_client,
    payload,
    expected_balance,
):
    response = api_client.post("/api/accounts/", payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    created_account = Account.objects.get(id=response.data["id"], user=main_user)
    assert created_account.current_balance == expected_balance
    assert created_account.current_balance_updated == timezone.now()


def test_update_account_balance_updates_timestamp(main_user, api_client):
    with freeze_time(DEFAULT_TIME + timedelta(days=2)):
        create_response = api_client.post(
            "/api/accounts/",
            {
                "name": "Основной",
                "type": AccountType.ACCUMULATION,
                "current_balance": "10.00",
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        account_id = create_response.data["id"]

    account = Account.objects.get(id=account_id, user=main_user)
    initial_updated_at = account.current_balance_updated

    tomorrow_datetime = DEFAULT_TIME + timedelta(days=3)
    with freeze_time(tomorrow_datetime):
        update_response = api_client.patch(
            f"/api/accounts/{account_id}/",
            {"current_balance": "25.00"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        account.refresh_from_db()
        assert account.current_balance == Decimal("25.00")
        assert account.current_balance_updated == tomorrow_datetime

    assert account.current_balance_updated != initial_updated_at
    assert account.current_balance_updated == tomorrow_datetime


def test_update_account_without_balance_keeps_timestamp(main_user, api_client):
    with freeze_time(DEFAULT_TIME + timedelta(days=1)):
        create_response = api_client.post(
            "/api/accounts/",
            {"name": "Инвестиции", "type": AccountType.ACCUMULATION},
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        account_id = create_response.data["id"]

    account = Account.objects.get(id=account_id, user=main_user)
    initial_updated_at = account.current_balance_updated

    tomorrow_datetime = DEFAULT_TIME + timedelta(days=2)
    with freeze_time(tomorrow_datetime):
        update_response = api_client.patch(
            f"/api/accounts/{account_id}/",
            {"description": "new description"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        account.refresh_from_db()

    assert account.current_balance_updated == initial_updated_at
    assert account.current_balance == Decimal("0")
