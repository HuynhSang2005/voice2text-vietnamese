import pytest
from httpx import AsyncClient
from main import app
from app.core.database import create_db_and_tables

@pytest.fixture(scope="function", autouse=True)
async def startup_event():
    await create_db_and_tables()
    yield


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Real-time STT API"}

@pytest.mark.asyncio
async def test_get_models():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/models")
    assert response.status_code == 200
    models = response.json()
    assert len(models) == 3
    assert models[0]["id"] == "zipformer"

@pytest.mark.asyncio
async def test_get_history():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
