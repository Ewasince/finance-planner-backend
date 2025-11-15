from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
import os

from accounts.models import Account, AccountType
from core.bootstrap import (
    ACCOUNT_UUID_4,
    ACCOUNT_UUID_5,
    DEFAULT_TIME,
    MAIN_ACCOUNT_UUID,
    OTHER_ACCOUNT_UUID,
    SECOND_ACCOUNT_UUID,
    THIRD_ACCOUNT_UUID,
    bootstrap_dev_data,
)
import django
from django.contrib.auth import get_user_model
from django.core.management import call_command
from freezegun import freeze_time
import pytest
from regular_operations.models import RegularOperationPeriodType, RegularOperationType
from rest_framework.test import APIClient

from tests.constants import DEFAULT_EXPENSE_TITLE, DEFAULT_INCOME_TITLE


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()


@pytest.fixture
def default_income_payload() -> tuple[dict, dict]:
    return {
        "title": DEFAULT_INCOME_TITLE,
        "description": "Описание",
        "amount": "1000.00",
        "type": RegularOperationType.INCOME,
        "to_account": MAIN_ACCOUNT_UUID,
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "active_before": date.max,
        "start_date": DEFAULT_TIME.isoformat(),
        "end_date": (DEFAULT_TIME + timedelta(days=30)).isoformat(),
    }, {
        "title": DEFAULT_INCOME_TITLE,
        "description": "Описание",
        "amount": "1000.00",
        "type": RegularOperationType.INCOME.value,
        "from_account": None,
        "to_account": MAIN_ACCOUNT_UUID,
        "to_account_name": "Основной счёт",
        "period_type": RegularOperationPeriodType.MONTH.value,
        "period_interval": 1,
        "active_before": date.max.strftime("%Y-%m-%d"),
        "start_date": get_isoformat_with_z(DEFAULT_TIME),
        "end_date": get_isoformat_with_z(DEFAULT_TIME + timedelta(days=30)),
        "created_at": get_isoformat_with_z(DEFAULT_TIME),
        "updated_at": get_isoformat_with_z(DEFAULT_TIME),
    }


@pytest.fixture
def default_expense_payload() -> tuple[dict, dict]:
    return {
        "title": DEFAULT_EXPENSE_TITLE,
        "description": "Описание",
        "amount": "300.00",
        "type": RegularOperationType.EXPENSE,
        "from_account": MAIN_ACCOUNT_UUID,
        "start_date": DEFAULT_TIME.isoformat(),
        "end_date": (DEFAULT_TIME + timedelta(days=30)).isoformat(),
        "period_type": RegularOperationPeriodType.MONTH,
        "period_interval": 1,
        "active_before": date.max,
    }, {
        "title": DEFAULT_EXPENSE_TITLE,
        "description": "Описание",
        "amount": "300.00",
        "type": RegularOperationType.EXPENSE.value,
        "to_account": None,
        "from_account": MAIN_ACCOUNT_UUID,
        "from_account_name": "Основной счёт",
        "period_type": RegularOperationPeriodType.MONTH.value,
        "period_interval": 1,
        "active_before": date.max.strftime("%Y-%m-%d"),
        "start_date": get_isoformat_with_z(DEFAULT_TIME),
        "end_date": get_isoformat_with_z(DEFAULT_TIME + timedelta(days=30)),
        "created_at": get_isoformat_with_z(DEFAULT_TIME),
        "updated_at": get_isoformat_with_z(DEFAULT_TIME),
    }


@pytest.fixture
def main_user(bootstrap_db):
    return get_user_model().objects.get(username="owner")


@pytest.fixture
def other_user(bootstrap_db):
    return get_user_model().objects.get(username="stranger")


@pytest.fixture
def api_client(main_user):
    client = APIClient()
    client.force_authenticate(user=main_user)
    return client


@pytest.fixture
def other_api_client(other_user):
    client = APIClient()
    client.force_authenticate(user=other_user)
    return client


@pytest.fixture
def create_account():
    def _create_account(
        user, name: str, account_type: AccountType, current_balance: Decimal = Decimal("4540.00")
    ):
        return Account.objects.create(
            user=user, name=name, type=account_type, current_balance=current_balance
        )

    return _create_account


@pytest.fixture
def create_user():
    def _create_user(username: str):
        return get_user_model().objects.create_user(
            username="username",
            email=f"{username}@example.com",
            password="password123",
        )

    return _create_user


@pytest.fixture
def main_account(main_user):
    return Account.objects.get(id=MAIN_ACCOUNT_UUID)


@pytest.fixture
def second_account(main_user):
    return Account.objects.get(id=SECOND_ACCOUNT_UUID)


@pytest.fixture
def third_account(main_user):
    return Account.objects.get(id=THIRD_ACCOUNT_UUID)


@pytest.fixture
def account_4(other_user):
    return Account.objects.get(id=ACCOUNT_UUID_4)


@pytest.fixture
def account_5(other_user):
    return Account.objects.get(id=ACCOUNT_UUID_5)


@pytest.fixture
def other_account(main_user):
    return Account.objects.get(id=OTHER_ACCOUNT_UUID)


def get_isoformat_with_z(dt: datetime) -> str:
    """goyda! goyda! goyda!"""
    return dt.isoformat().replace("+00:00", "Z")


@pytest.fixture(scope="session", autouse=True)
def bootstrap_db(django_db_setup, django_db_blocker):
    with freeze_time(DEFAULT_TIME), django_db_blocker.unblock():
        bootstrap_dev_data()
    yield


@pytest.fixture(scope="function")
def fresh_db(django_db_setup, django_db_blocker):
    with freeze_time(DEFAULT_TIME), django_db_blocker.unblock():
        bootstrap_dev_data()
    yield


@pytest.fixture
def clear_db(django_db_setup, django_db_blocker):
    call_command("flush", interactive=False, verbosity=0)
    yield
