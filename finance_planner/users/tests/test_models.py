from django.contrib.auth import get_user_model
from django.test import TestCase


class UserModelTests(TestCase):
    def test_string_representation_prefers_email(self):
        user = get_user_model().objects.create_user(
            username="testuser",
            email="user@example.com",
            password="password123",
        )

        self.assertEqual(str(user), "user@example.com")

    def test_string_representation_falls_back_to_username(self):
        user = get_user_model().objects.create_user(
            username="fallback",
            password="password123",
        )

        self.assertEqual(str(user), "fallback")
