import pytest
from sqlalchemy import text
from unittest.mock import AsyncMock


pytestmark = pytest.mark.asyncio


class TestHealthEndpoint:
    async def test_health_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_health_returns_ok_status(self, client):
        response = await client.get("/health")
        assert response.json() == {"status": "ok"}


class TestHealthDbEndpoint:
    async def test_db_ready_returns_200(self, client_with_db, mock_db):
        mock_db.execute = AsyncMock(return_value=None)  # SELECT 1 succeeds

        response = await client_with_db.get("/health/db")

        assert response.status_code == 200
        assert response.json() == {"status": "db ready"}
        mock_db.execute.assert_awaited_once()

    async def test_db_unavailable_returns_503(self, client_with_db, mock_db):
        mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))

        response = await client_with_db.get("/health/db")

        assert response.status_code == 503
        assert response.json()["detail"] == "DB not ready"