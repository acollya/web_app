"""Basic smoke tests — verifies the app boots and health endpoint responds."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_ping(client: AsyncClient):
    response = await client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json() == {"message": "pong"}
