from django.conf import settings
import pytest
from users.models import User


pytestmark = pytest.mark.django_db


def test_svc_user_success(api_client):
    user = User.objects.create(
        username="ivan",
        email="example@mail.ru",
        first_name="Ivan",
        last_name="Ivanov",
    )

    url = f"/api/users/svc/{user.id}/"

    headers = {"HTTP_AUTHORIZATION": f"SVCBearer {settings.SERVICE_AUTH_TOKEN}"}

    response = api_client.get(url, **headers)

    assert response.status_code == 200
    data = response.json()

    assert data["email"] == "example@mail.ru"
    assert data["first_name"] == "Ivan"
    assert data["last_name"] == "Ivanov"


def test_svc_user_forbidden_no_token(api_client):
    user = User.objects.create(username="ivan")

    url = f"/api/users/svc/{user.id}/"

    response = api_client.get(url)

    assert response.status_code == 403


def test_svc_user_forbidden_invalid_token(api_client):
    user = User.objects.create(username="ivan")

    url = f"/api/users/svc/{user.id}/"

    headers = {"HTTP_AUTHORIZATION": "SVCBearer wrong-token"}

    response = api_client.get(url, **headers)

    assert response.status_code == 403


def test_svc_user_not_found(api_client):
    url = "/api/users/svc/999999/"

    headers = {"HTTP_AUTHORIZATION": f"SVCBearer {settings.SERVICE_AUTH_TOKEN}"}

    response = api_client.get(url, **headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "No User matches the given query."
