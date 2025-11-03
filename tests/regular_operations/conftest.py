from __future__ import annotations

import os
from datetime import datetime
from typing import Final

import pytz

from accounts.models import Account, AccountType
import django
from django.contrib.auth import get_user_model
from pydash import set_ as pydash_set, unset as pydash_unset
import pytest
from rest_framework.test import APIClient


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()


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


MAIN_ACCOUNT_NAME: Final[str] = "Основной счёт"
DELETE_SENTINEL: Final[object] = object()


def change_value_py_path(obj: dict, path: str, value):
    if value is DELETE_SENTINEL:
        pydash_unset(obj, path)
    else:
        pydash_set(obj, path, value)

DEFAULT_TIME: Final[datetime] = datetime(2025, 11, 1, tzinfo=pytz.utc)

def get_isoformat_with_z(dt: datetime) -> str:
    """goyda! goyda! goyda!"""
    return dt.isoformat().replace("+00:00", "Z")
