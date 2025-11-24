import pytest
from httpx import AsyncClient
from main import app
from app.core.database import create_db_and_tables

@pytest.fixture(scope="function", autouse=True)
async def startup_event():
    await create_db_and_tables()
    yield

@pytest.mark.asyncio
async def test_404_not_found_rfc7807():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/non-existent-endpoint")
    
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["status"] == 404
    assert data["title"] == "Not Found"
    assert data["type"] == "about:blank"

@pytest.mark.asyncio
async def test_400_bad_request_rfc7807():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Trigger validation error (missing query param if any, or post invalid body)
        # Let's try the switch model endpoint with invalid method or missing param
        response = await ac.post("/models/switch") # Missing 'model' query param
    
    assert response.status_code == 422 # FastAPI returns 422 for validation errors
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["status"] == 422
    assert data["title"] == "Validation Error"

@pytest.mark.asyncio
async def test_custom_error_rfc7807():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Trigger the ValueError in switch_model
        response = await ac.post("/models/switch?model=invalid_model_name")
    
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    data = response.json()
    assert data["status"] == 400
    assert "Unknown model" in data["detail"]
