import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from database.db.session import get_db


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """Plain async client — no DB override."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def client_with_db(mock_db):
    """Async client with DB dependency overridden."""
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    """A mock AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    return session