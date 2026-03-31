"""Test health endpoint and app startup."""
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "servepos"


@pytest.mark.asyncio
async def test_openapi_schema(client):
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["info"]["title"] == "ServePOS"


@pytest.mark.asyncio
async def test_unauthenticated_request(client):
    resp = await client.get("/api/v1/staff")
    assert resp.status_code == 401
