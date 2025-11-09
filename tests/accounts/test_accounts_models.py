from accounts.models import AccountType
import pytest


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
def test_create_account(api_client, main_user, account_type):
    payload = {"name": "Счёт", "type": account_type, "description": "Описание"}
    response = api_client.post("/api/accounts/", payload, format="json")

    assert response.status_code == 201
    response_data = response.data
    assert response_data["name"] == "Счёт"
    assert response_data["type"] == account_type.value
    assert response_data["description"] == "Описание"
    assert response_data["current_balance"] == "0.00"
    assert response_data["target_amount"] is None


def test_cannot_create_two_main_accounts(api_client, main_user):
    payload = {"name": "Счёт", "type": AccountType.MAIN, "description": "Описание"}
    response = api_client.post("/api/accounts/", payload, format="json")

    assert response.status_code == 201
    payload = {"name": "Счёт 2", "type": AccountType.MAIN, "description": "Описание"}
    response = api_client.post("/api/accounts/", payload, format="json")

    assert response.status_code == 400
    assert "type" in response.data


def test_cannot_update_account_type(api_client, main_user):
    payload = {"name": "Счёт", "type": AccountType.MAIN, "description": "Описание"}
    response = api_client.post("/api/accounts/", payload, format="json")

    assert response.status_code == 201
    payload = {
        "type": AccountType.PURPOSE,
    }
    response = api_client.patch(f"/api/accounts/{response.data['id']}/", payload, format="json")

    assert response.status_code == 400
    assert "type" in response.data
    pass
