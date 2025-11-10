from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from accounts.models import Account


pytestmark = pytest.mark.django_db


def test_bootstrap_db_creates_superuser(bootstrap_db):
    assert get_user_model().objects.filter(is_superuser=True).count() == 1


def test_fresh_db_provides_accounts(fresh_db):
    assert Account.objects.count() == 3
    Account.objects.first().delete()


def test_fresh_db_resets_state_between_tests(fresh_db):
    assert Account.objects.count() == 3
