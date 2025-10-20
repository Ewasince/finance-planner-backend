from django.contrib.auth import get_user_model
import pytest


pytestmark = pytest.mark.django_db


def test_string_representation_prefers_email():
    user = get_user_model().objects.create_user(
        username="testuser",
        email="user@example.com",
        password="password123",
    )

    assert str(user) == "user@example.com"


def test_string_representation_falls_back_to_username():
    user = get_user_model().objects.create_user(
        username="fallback",
        password="password123",
    )

    assert str(user) == "fallback"
