from accounts.models import AccountType
import pytest
from rest_framework import status
from rest_framework.test import APIClient


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ["account_type"],
    [
        (AccountType.MAIN,),
        (AccountType.PURPOSE,),
        (AccountType.ACCUMULATION,),
        (AccountType.DEBT,),
        (AccountType.RESERVE,),
    ],
)
def test_create_account(create_user, account_type):
    user = create_user("some_user")
    client = APIClient()
    client.force_authenticate(user=user)

    payload = {"name": "Счёт", "type": account_type, "description": "Описание"}
    response = client.post("/api/accounts/", payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.data
    assert response_data["name"] == "Счёт"
    assert response_data["type"] == account_type.value
    assert response_data["description"] == "Описание"
    assert response_data["current_balance"] == "0.00"
    assert response_data["target_amount"] is None


def test_cannot_create_two_main_accounts(create_user):
    user = create_user("some_user")
    client = APIClient()
    client.force_authenticate(user=user)

    payload = {"name": "Счёт", "type": AccountType.MAIN, "description": "Описание"}
    response = client.post("/api/accounts/", payload, format="json")

    assert response.status_code == 201
    payload = {"name": "Счёт 2", "type": AccountType.MAIN, "description": "Описание"}
    response = client.post("/api/accounts/", payload, format="json")

    assert response.status_code == 400
    assert "type" in response.data


def test_cannot_update_account_type(create_user):
    user = create_user("some_user")
    client = APIClient()
    client.force_authenticate(user=user)

    payload = {"name": "Счёт", "type": AccountType.MAIN, "description": "Описание"}
    response = client.post("/api/accounts/", payload, format="json")

    assert response.status_code == 201
    payload = {
        "type": AccountType.PURPOSE,
    }
    response = client.patch(f"/api/accounts/{response.data['id']}/", payload, format="json")

    assert response.status_code == 400
    assert "type" in response.data
