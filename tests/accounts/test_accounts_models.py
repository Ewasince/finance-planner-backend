from django.contrib.auth import get_user_model
import pytest

from finance_planner.accounts.models import Account


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
        type=Account.AccountType.CHECKING,
    )

    assert str(account) == "Основной счёт (owner@example.com)"


def test_default_gradient_theme_used(user):
    account = Account.objects.create(
        user=user,
        name="Накопления",
        type=Account.AccountType.SAVINGS,
    )

    assert account.gradient_theme == Account.GradientTheme.DEFAULT
