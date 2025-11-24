import pytest
from httpx import AsyncClient
from main import app
from app.core.database import create_db_and_tables

@pytest.fixture(scope="function", autouse=True)
async def startup_event():
    await create_db_and_tables()
    yield

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
