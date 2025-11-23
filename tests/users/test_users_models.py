from typing import Final

from django.contrib.auth import get_user_model
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from users.models import User


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


TEST_OLD_PASSWORD: Final[str] = "OldPass123!"
TEST_NEW_PASSWORD: Final[str] = "NewPass123!"


@pytest.mark.parametrize(
    "old_password, new_password, new_password2, expected_status, password_changed",
    [
        pytest.param(
            TEST_OLD_PASSWORD,
            "TEST_NEW_PASSWORD",
            "TEST_NEW_PASSWORD",
            status.HTTP_200_OK,
            True,
            id="success",
        ),
        pytest.param(
            TEST_OLD_PASSWORD + "break",
            TEST_NEW_PASSWORD,
            TEST_NEW_PASSWORD,
            status.HTTP_400_BAD_REQUEST,
            False,
            id="wrong old password",
        ),
        pytest.param(
            TEST_OLD_PASSWORD,
            TEST_NEW_PASSWORD,
            TEST_NEW_PASSWORD + "break",
            status.HTTP_400_BAD_REQUEST,
            False,
            id="wrong 2nd password",
        ),
    ],
)
def test_change_password(
    old_password,
    new_password,
    new_password2,
    expected_status,
    password_changed,
):
    client = APIClient()

    user = User.objects.create_user(
        username="testuser",
        password=TEST_OLD_PASSWORD,
        email="test@example.com",
    )

    client.force_authenticate(user=user)

    payload = {
        "old_password": old_password,
        "new_password": new_password,
        "new_password2": new_password2,
    }

    response = client.post("/api/users/change-password/", payload, format="json")
    assert response.status_code == expected_status, response.text

    user.refresh_from_db()

    if password_changed:
        assert user.check_password(new_password)
        assert not user.check_password(TEST_OLD_PASSWORD)
    else:
        assert not user.check_password(new_password)
        assert user.check_password(TEST_OLD_PASSWORD)
