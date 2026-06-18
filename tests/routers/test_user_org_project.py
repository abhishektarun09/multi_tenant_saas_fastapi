import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


class FakeAsyncRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    async def incr(self, key):
        value = int(self.store.get(key, 0) or 0) + 1
        self.store[key] = value
        return value


@pytest.fixture(autouse=True)
def mock_redis():
    fake_redis = FakeAsyncRedis()
    with (
        patch("core.oauth2.redis", fake_redis),
        patch("core.utils.redis", fake_redis),
        patch("api.v2.users.list_orgs.redis", fake_redis),
    ):
        yield


@pytest.fixture(autouse=True)
def mock_audit_logs():
    with (
        patch("api.v2.users.register.audit_logs", new=AsyncMock()),
        patch("api.v2.auth.login.audit_logs", new=AsyncMock()),
        patch("api.v2.organizations.register.audit_logs", new=AsyncMock()),
        patch("api.v2.projects.create.audit_logs", new=AsyncMock()),
    ):
        yield


async def register_user(client: AsyncClient, email: str, password: str):
    payload = {
        "name": "Org Project User",
        "email": email,
        "password": password,
    }
    response = await client.post("/v2/users/register", json=payload)
    assert response.status_code == 201
    return response.json()["user"]


async def login_user(client: AsyncClient, email: str, password: str):
    response = await client.post(
        "/v2/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_user_org_project_flow(client: AsyncClient):
    email = "orgflow@example.com"
    password = "Strongpassword#12345678"

    user = await register_user(client, email, password)
    access_token = await login_user(client, email, password)
    headers = {"Authorization": f"Bearer {access_token}"}

    org_payload = {"name": "Test Organization"}
    org_response = await client.post(
        "/v2/organizations/register", json=org_payload, headers=headers
    )
    assert org_response.status_code == 201
    org_data = org_response.json()
    assert org_data["slug"] == "test-organization"
    org_id = org_data["id"]

    select_response = await client.post(
        f"/v2/organizations/select/{org_id}", headers=headers
    )
    assert select_response.status_code == 202
    selected_access_token = select_response.json()["access_token"]
    selected_headers = {"Authorization": f"Bearer {selected_access_token}"}

    me_response = await client.get("/v2/users/me", headers=selected_headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == email
    assert me_data["org_id"] == org_id
    assert me_data["role"] == "owner"

    orgs_response = await client.get("/v2/users/orgs", headers=selected_headers)
    assert orgs_response.status_code == 200
    orgs_data = orgs_response.json()
    assert orgs_data["email"] == email
    assert orgs_data["org_ids"] == [org_id]

    project_payload = {"name": "Test Project"}
    project_response = await client.post(
        "/v2/projects/", json=project_payload, headers=selected_headers
    )
    assert project_response.status_code == 201
    project_data = project_response.json()
    assert project_data["name"] == "Test Project"
    assert project_data["organization_id"] == org_id
    assert project_data["created_by"] == user["id"]


@pytest.mark.asyncio
async def test_organization_duplicate_registration_fails(client: AsyncClient):
    email = "orgduplicate@example.com"
    password = "Strongpassword#12345678"

    await register_user(client, email, password)
    access_token = await login_user(client, email, password)
    headers = {"Authorization": f"Bearer {access_token}"}

    org_payload = {"name": "Duplicate Organization"}
    response1 = await client.post(
        "/v2/organizations/register", json=org_payload, headers=headers
    )
    assert response1.status_code == 201

    response2 = await client.post(
        "/v2/organizations/register", json=org_payload, headers=headers
    )
    assert response2.status_code == 400
    assert response2.json()["detail"] == "Organization already registered"
