from __future__ import annotations

from typing import Any, Iterable, Final

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Account, AccountType
from regular_operations.models import (
    RegularOperationPeriodType,
    RegularOperationType,
)


DEFAULT_SCENARIO_DATA: Final[dict[str, Any]] = {
    "title": "План распределения зарплаты",
    "description": "Настраиваемый сценарий",
    "is_active": False,
}

DEFAULT_SCENARIO_RULE_DATA: Final[dict[str, Any]] = {
    "target_account": "00000000-0000-0000-0000-000000000000",
    "amount": "100.00",
    "order": 1,
}

DEFAULT_REGULAR_OPERATION_DATA: Final[dict[str, Any]] = {
    "title": "Получение зарплаты",
    "description": "Основной доход",
    "amount": "1000.00",
    "type": RegularOperationType.INCOME,
    "start_date": "2024-01-01T00:00:00+00:00",
    "end_date": "2024-01-31T00:00:00+00:00",
    "period_type": RegularOperationPeriodType.MONTH,
    "period_interval": 1,
    "is_active": True,
}


def build_scenario_data(**overrides: Any) -> dict[str, Any]:
    return {**DEFAULT_SCENARIO_DATA, **overrides}


def build_scenario_rule_data(**overrides: Any) -> dict[str, Any]:
    return {**DEFAULT_SCENARIO_RULE_DATA, **overrides}


def build_regular_operation_payload(
    *,
    scenario: dict[str, Any] | None = None,
    scenario_rules: Iterable[dict[str, Any]] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    payload = {**DEFAULT_REGULAR_OPERATION_DATA, **overrides}
    payload["scenario"] = (
        build_scenario_data() if scenario is None else scenario
    )
    payload["scenario_rules"] = (
        [build_scenario_rule_data()]
        if scenario_rules is None
        else scenario_rules
    )
    return payload


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
