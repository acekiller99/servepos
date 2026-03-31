"""Test authentication endpoints."""
import pytest

from tests.conftest import OUTLET_ID


@pytest.mark.asyncio
async def test_login_success(client, seed_staff):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "password123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, seed_staff):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client, seed_staff):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@test.com",
        "password": "password123",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_pin_login_success(client, seed_staff):
    resp = await client.post("/api/v1/auth/pin-login", json={
        "pin_code": "0000",
        "outlet_id": str(OUTLET_ID),
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_pin_login_wrong_pin(client, seed_staff):
    resp = await client.post("/api/v1/auth/pin-login", json={
        "pin_code": "9999",
        "outlet_id": str(OUTLET_ID),
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client, seed_staff):
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "password123",
    })
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client, seed_staff):
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "password123",
    })
    access_token = login_resp.json()["access_token"]

    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": access_token,
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(client, seed_staff):
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid.token.here",
    })
    assert resp.status_code == 401
