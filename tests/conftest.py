from __future__ import annotations

from datetime import datetime, timedelta
import os

from accounts.models import Account, AccountType
import django
from django.contrib.auth import get_user_model
import pytest
from regular_operations.models import RegularOperationPeriodType, RegularOperationType
from rest_framework.test import APIClient

from tests.constants import (
    DEFAULT_TIME,
    MAIN_ACCOUNT_UUID,
    OTHER_ACCOUNT_UUID,
    SECOND_ACCOUNT_UUID,
    THIRD_ACCOUNT_UUID,
)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()


@pytest.fixture
def default_income_payload() -> tuple[dict, dict]:
    return {
        "title": "Зарплата",
        "description": "Описание",
        "amount": "1000.00",
        "type": RegularOperationType.INCOME,
        "to_account": MAIN_ACCOUNT_UUID,
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
        "start_date": DEFAULT_TIME.isoformat(),
        "end_date": (DEFAULT_TIME + timedelta(days=30)).isoformat(),
    }, {
        "title": "Зарплата",
        "description": "Описание",
        "amount": "1000.00",
        "type": RegularOperationType.INCOME.value,
        "from_account": None,
        "to_account": MAIN_ACCOUNT_UUID,
        "to_account_name": "Основной счёт",
        "period_type": RegularOperationPeriodType.MONTH.value,
        "period_interval": 1,
        "is_active": True,
        "start_date": get_isoformat_with_z(DEFAULT_TIME),
        "end_date": get_isoformat_with_z(DEFAULT_TIME + timedelta(days=30)),
        "created_at": get_isoformat_with_z(DEFAULT_TIME),
        "updated_at": get_isoformat_with_z(DEFAULT_TIME),
    }


@pytest.fixture
def default_expense_payload() -> tuple[dict, dict]:
    return {
        "title": "Ежемесячный перевод",
        "description": "Описание",
        "amount": "300.00",
        "type": RegularOperationType.EXPENSE,
        "from_account": MAIN_ACCOUNT_UUID,
        "start_date": DEFAULT_TIME.isoformat(),
        "end_date": (DEFAULT_TIME + timedelta(days=30)).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "is_active": True,
    }, {
        "title": "Ежемесячный перевод",
        "description": "Описание",
        "amount": "300.00",
        "type": RegularOperationType.EXPENSE.value,
        "to_account": None,
        "from_account": MAIN_ACCOUNT_UUID,
        "from_account_name": "Основной счёт",
        "period_type": RegularOperationPeriodType.MONTH.value,
        "period_interval": 1,
        "is_active": True,
        "start_date": get_isoformat_with_z(DEFAULT_TIME),
        "end_date": get_isoformat_with_z(DEFAULT_TIME + timedelta(days=30)),
        "created_at": get_isoformat_with_z(DEFAULT_TIME),
        "updated_at": get_isoformat_with_z(DEFAULT_TIME),
    }


@pytest.fixture
def main_user():
    return get_user_model().objects.create_user(
        username="owner",
        email="owner@example.com",
        password="password123",
    )


@pytest.fixture
def other_user():
    return get_user_model().objects.create_user(
        username="stranger",
        email="stranger@example.com",
        password="password123",
    )


@pytest.fixture
def api_client(main_user):
    client = APIClient()
    client.force_authenticate(user=main_user)
    return client


@pytest.fixture
def create_account():
    def _create_account(user, name: str, account_type: AccountType):
        return Account.objects.create(user=user, name=name, type=account_type)

    return _create_account


@pytest.fixture
def main_account(main_user):
    return Account.objects.create(
        id=MAIN_ACCOUNT_UUID, user=main_user, name="Основной счёт", type=AccountType.MAIN
    )


@pytest.fixture
def second_account(main_user):
    return Account.objects.create(
        id=SECOND_ACCOUNT_UUID, user=main_user, name="Резерв", type=AccountType.RESERVE
    )


@pytest.fixture
def third_account(main_user):
    return Account.objects.create(
        id=THIRD_ACCOUNT_UUID, user=main_user, name="Накопление", type=AccountType.ACCUMULATION
    )


@pytest.fixture
def bootstrap_owner(bootstrap_db):
    return get_user_model().objects.get(username="owner")




@pytest.fixture
def other_account(other_user):
    return Account.objects.create(
        id=OTHER_ACCOUNT_UUID, user=other_user, name="Резерв", type=AccountType.RESERVE
    )


def get_isoformat_with_z(dt: datetime) -> str:
    """goyda! goyda! goyda!"""
    return dt.isoformat().replace("+00:00", "Z")
