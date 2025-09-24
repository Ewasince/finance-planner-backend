from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Account


class AccountModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="owner",
            email="owner@example.com",
            password="password123",
        )

    def test_string_representation_includes_name_and_user_email(self):
        account = Account.objects.create(
            user=self.user,
            name="Основной счёт",
            type=Account.AccountType.CHECKING,
        )

        self.assertEqual(str(account), "Основной счёт (owner@example.com)")

    def test_default_gradient_theme_used(self):
        account = Account.objects.create(
            user=self.user,
            name="Накопления",
            type=Account.AccountType.SAVINGS,
        )

        self.assertEqual(account.gradient_theme, Account.GradientTheme.DEFAULT)
