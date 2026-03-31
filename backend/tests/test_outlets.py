"""Test outlet endpoints."""
import pytest

from tests.conftest import admin_headers, cashier_headers, OUTLET_ID


@pytest.mark.asyncio
async def test_list_outlets(client, seed_staff):
    resp = await client.get("/api/v1/outlets", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Test Restaurant"


@pytest.mark.asyncio
async def test_create_outlet(client, seed_staff):
    resp = await client.post("/api/v1/outlets", headers=admin_headers(), json={
        "name": "Branch 2",
        "address": "456 New St",
        "currency": "USD",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Branch 2"
    assert data["currency"] == "USD"


@pytest.mark.asyncio
async def test_create_outlet_forbidden_for_cashier(client, seed_staff):
    resp = await client.post("/api/v1/outlets", headers=cashier_headers(), json={
        "name": "Branch 3",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_outlet(client, seed_staff):
    resp = await client.get(f"/api/v1/outlets/{OUTLET_ID}", headers=admin_headers())
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Restaurant"


@pytest.mark.asyncio
async def test_get_outlet_not_found(client, seed_staff):
    import uuid
    resp = await client.get(f"/api/v1/outlets/{uuid.uuid4()}", headers=admin_headers())
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_outlet(client, seed_staff):
    resp = await client.put(f"/api/v1/outlets/{OUTLET_ID}", headers=admin_headers(), json={
        "name": "Updated Restaurant",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Restaurant"


@pytest.mark.asyncio
async def test_get_outlet_settings(client, seed_staff):
    resp = await client.get(f"/api/v1/outlets/{OUTLET_ID}/settings", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["tax_rate"] == 6.0
    assert data["service_charge_rate"] == 10.0


@pytest.mark.asyncio
async def test_update_outlet_settings(client, seed_staff):
    resp = await client.put(f"/api/v1/outlets/{OUTLET_ID}/settings", headers=admin_headers(), json={
        "tax_rate": 8.0,
    })
    assert resp.status_code == 200
    assert resp.json()["tax_rate"] == 8.0
