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
        patch("api.v2.organizations.list_users.redis", fake_redis),
        patch("api.v2.projects.list_projects.redis", fake_redis),
        patch("api.v2.projects.list_members.redis", fake_redis),
    ):
        yield


@pytest.fixture(autouse=True)
def mock_audit_logs():
    with (
        patch("api.v2.users.register.audit_logs", new=AsyncMock()),
        patch("api.v2.auth.login.audit_logs", new=AsyncMock()),
        patch("api.v2.organizations.register.audit_logs", new=AsyncMock()),
        patch("api.v2.organizations.add_user.audit_logs", new=AsyncMock()),
        patch("api.v2.organizations.remove_member.audit_logs", new=AsyncMock()),
        patch("api.v2.projects.create.audit_logs", new=AsyncMock()),
        patch("api.v2.projects.update.audit_logs", new=AsyncMock()),
        patch("api.v2.projects.delete.audit_logs", new=AsyncMock()),
        patch("api.v2.projects.add_user.audit_logs", new=AsyncMock()),
        patch("api.v2.projects.remove_user.audit_logs", new=AsyncMock()),
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
async def test_project_update_delete_list_routes(client: AsyncClient):
    email = "projectflow@example.com"
    password = "Strongpassword#12345678"

    await register_user(client, email, password)
    access_token = await login_user(client, email, password)
    headers = {"Authorization": f"Bearer {access_token}"}

    org_response = await client.post(
        "/v2/organizations/register",
        json={"name": "Project Route Org"},
        headers=headers,
    )
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]

    select_response = await client.post(
        f"/v2/organizations/select/{org_id}", headers=headers
    )
    assert select_response.status_code == 202
    selected_headers = {
        "Authorization": f"Bearer {select_response.json()['access_token']}"
    }

    create_response = await client.post(
        "/v2/projects/",
        json={"name": "Initial Project"},
        headers=selected_headers,
    )
    assert create_response.status_code == 201

    list_response = await client.get(
        "/v2/projects/?page=1&page_size=20", headers=selected_headers
    )
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["organization_id"] == org_id
    assert list_data["project_details"][0]["name"] == "Initial Project"
    project_id = list_data["project_details"][0]["project_id"]

    update_response = await client.put(
        f"/v2/projects/{project_id}",
        json={"new_name": "Updated Project"},
        headers=selected_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["response"] == "Project updated successfully"

    updated_list_response = await client.get(
        "/v2/projects/?page=1&page_size=20", headers=selected_headers
    )
    assert updated_list_response.status_code == 200
    updated_list_data = updated_list_response.json()
    assert updated_list_data["project_details"][0]["name"] == "Updated Project"

    delete_response = await client.delete(
        f"/v2/projects/{project_id}", headers=selected_headers
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["response"] == "Project deleted"

    after_delete_response = await client.get(
        "/v2/projects/?page=1&page_size=20", headers=selected_headers
    )
    assert after_delete_response.status_code == 404
    assert after_delete_response.json()["detail"] == "No projects in Organization"


@pytest.mark.asyncio
async def test_project_membership_flow(client: AsyncClient):
    primary_email = "projectmember1@example.com"
    secondary_email = "projectmember2@example.com"
    password = "Strongpassword#12345678"

    await register_user(client, primary_email, password)
    await register_user(client, secondary_email, password)

    access_token = await login_user(client, primary_email, password)
    headers = {"Authorization": f"Bearer {access_token}"}

    org_response = await client.post(
        "/v2/organizations/register",
        json={"name": "Membership Org"},
        headers=headers,
    )
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]

    select_response = await client.post(
        f"/v2/organizations/select/{org_id}", headers=headers
    )
    assert select_response.status_code == 202
    selected_headers = {
        "Authorization": f"Bearer {select_response.json()['access_token']}"
    }

    add_org_user_response = await client.post(
        "/v2/organizations/member",
        json={"email": secondary_email, "role": "member"},
        headers=selected_headers,
    )
    assert add_org_user_response.status_code == 201
    assert add_org_user_response.json()["message"] == "User added to organization"

    create_project_response = await client.post(
        "/v2/projects/",
        json={"name": "Membership Project"},
        headers=selected_headers,
    )
    assert create_project_response.status_code == 201

    list_project_response = await client.get(
        "/v2/projects/?page=1&page_size=20", headers=selected_headers
    )
    assert list_project_response.status_code == 200
    project_details = list_project_response.json()["project_details"]
    project_id = next(
        item["project_id"]
        for item in project_details
        if item["name"] == "Membership Project"
    )

    add_project_user_response = await client.post(
        f"/v2/projects/{project_id}/member",
        json={"email": secondary_email},
        headers=selected_headers,
    )
    assert add_project_user_response.status_code == 201
    added_project_member = add_project_user_response.json()
    assert added_project_member["user_id"] is not None
    assert added_project_member["project_id"] == project_id

    list_members_response = await client.get(
        f"/v2/projects/{project_id}/members",
        headers=selected_headers,
    )
    assert list_members_response.status_code == 200
    members = list_members_response.json()["member_details"]
    assert any(member["email"] == secondary_email for member in members)

    remove_project_user_response = await client.request(
        "DELETE",
        f"/v2/projects/{project_id}/member",
        json={"email": secondary_email},
        headers=selected_headers,
    )
    assert remove_project_user_response.status_code == 201
    assert (
        remove_project_user_response.json()["response"]
        == "Member removed from the project"
    )

    list_after_remove_response = await client.get(
        f"/v2/projects/{project_id}/members",
        headers=selected_headers,
    )
    assert list_after_remove_response.status_code == 404
    assert list_after_remove_response.json()["detail"] == "No member in the project"
