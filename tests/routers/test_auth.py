import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def mock_audit_logs():
    with (
        patch("api.v2.users.register.audit_logs", new=AsyncMock()),
        patch("api.v2.auth.login.audit_logs", new=AsyncMock()),
    ):
        yield


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    password = "Strongpassword#12345678"
    email = "login-success@example.com"
    register_payload = {
        "name": "Login User",
        "email": email,
        "password": password,
    }

    register_response = await client.post("/v2/users/register", json=register_payload)
    assert register_response.status_code == 201

    login_response = await client.post(
        "/v2/auth/login",
        data={"username": email, "password": password},
    )

    assert login_response.status_code == 200
    data = login_response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert login_response.cookies.get("refresh_token") is not None


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    response = await client.post(
        "/v2/auth/login",
        data={"username": "wrong@example.com", "password": "badpassword"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Credentials"


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient):
    password = "Strongpassword#12345678"
    email = "refresh-success@example.com"
    register_payload = {
        "name": "Refresh User",
        "email": email,
        "password": password,
    }

    register_response = await client.post("/v2/users/register", json=register_payload)
    assert register_response.status_code == 201

    login_response = await client.post(
        "/v2/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    refresh_token = login_response.cookies.get("refresh_token")
    assert refresh_token is not None

    refresh_response = await client.post(
        "/v2/auth/refresh-token",
        cookies={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert refresh_response.cookies.get("refresh_token") is not None


@pytest.mark.asyncio
async def test_refresh_token_missing_cookie(client: AsyncClient):
    response = await client.post("/v2/auth/refresh-token")
    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh Token missing"
