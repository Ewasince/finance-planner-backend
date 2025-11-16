from __future__ import annotations

from accounts.models import Account
from django.contrib.auth import get_user_model
import pytest


pytestmark = pytest.mark.django_db


def test_bootstrap_db_creates_superuser():
    assert get_user_model().objects.filter(is_superuser=True).count() == 1


def test_bootstrap_db_provides_accounts():
    assert Account.objects.count() == 7
    Account.objects.first().delete()
    assert Account.objects.count() != 7


def test_bootstrap_db_resets_state_between_tests():
    assert Account.objects.count() == 7
