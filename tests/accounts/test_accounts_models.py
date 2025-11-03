from accounts.models import Account, AccountType
from django.contrib.auth import get_user_model
import pytest


pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user(
        username="owner",
        email="owner@example.com",
        password="password123",
    )


def test_string_representation_includes_name_and_user_email(user):
    account = Account.objects.create(
        user=user,
        name="Основной счёт",
        type=AccountType.MAIN,
    )

    assert str(account) == "Основной счёт (owner@example.com)"


def test_current_balance_defaults_to_zero(user):
    account = Account.objects.create(
        user=user,
        name="Накопления",
        type=AccountType.ACCUMULATION,
    )

    assert account.current_balance == 0
