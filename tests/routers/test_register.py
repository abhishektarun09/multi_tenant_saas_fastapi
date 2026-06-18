import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


# Patch audit_logs at the point of use, not where it is defined.
# Each router that imports audit_logs needs its own patch target.
@pytest.fixture(autouse=True)
def mock_audit_logs():
    with patch("api.v2.users.register.audit_logs", new=AsyncMock()):
        yield


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    payload = {
        "name": "Abhishek",
        "email": "test@example.com",
        "password": "Strongpassword#12345678",
    }

    response = await client.post("/v2/users/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Account created!"
    assert data["user"]["email"] == payload["email"]


@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: AsyncClient):
    payload = {
        "name": "Abhishek",
        "email": "duplicate@example.com",
        "password": "Strongpassword#12345678",
    }

    response1 = await client.post("/v2/users/register", json=payload)
    assert response1.status_code == 201

    response2 = await client.post("/v2/users/register", json=payload)
    assert response2.status_code == 400
    assert response2.json()["detail"] == "Email already registered"
