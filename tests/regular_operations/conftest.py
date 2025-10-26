from __future__ import annotations

from typing import Final

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AccountType, Account


@pytest.fixture
def user():
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
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def list_url():
    return reverse("regular-operation-list")


@pytest.fixture
def create_account():
    def _create_account(user, name: str, account_type: AccountType):
        return Account.objects.create(user=user, name=name, type=account_type)

    return _create_account


MAIN_ACCOUNT_NAME: Final[str] = "Основной счёт"
