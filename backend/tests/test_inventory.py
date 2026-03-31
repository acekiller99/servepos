"""Test inventory endpoints."""
import uuid

import pytest

from tests.conftest import admin_headers, cashier_headers, OUTLET_ID


@pytest.mark.asyncio
async def test_create_inventory_item(client, seed_staff):
    resp = await client.post("/api/v1/inventory", headers=admin_headers(), json={
        "name": "Chicken Breast",
        "unit": "kg",
        "quantity": 50.0,
        "min_quantity": 10.0,
        "cost_per_unit": 8.50,
        "supplier": "Farm Fresh",
        "category": "Meat",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Chicken Breast"
    assert data["quantity"] == 50.0


@pytest.mark.asyncio
async def test_list_inventory(client, seed_staff):
    await client.post("/api/v1/inventory", headers=admin_headers(), json={
        "name": "Rice", "unit": "kg", "quantity": 100,
    })
    resp = await client.get("/api/v1/inventory", headers=cashier_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_inventory_item(client, seed_staff):
    create = await client.post("/api/v1/inventory", headers=admin_headers(), json={
        "name": "Flour", "unit": "kg", "quantity": 20,
    })
    item_id = create.json()["id"]
    resp = await client.put(f"/api/v1/inventory/{item_id}", headers=admin_headers(), json={
        "min_quantity": 5.0,
        "cost_per_unit": 2.50,
    })
    assert resp.status_code == 200
    assert resp.json()["min_quantity"] == 5.0


@pytest.mark.asyncio
async def test_restock(client, seed_staff):
    create = await client.post("/api/v1/inventory", headers=admin_headers(), json={
        "name": "Oil", "unit": "liter", "quantity": 10,
    })
    item_id = create.json()["id"]
    resp = await client.post(f"/api/v1/inventory/{item_id}/restock", headers=admin_headers(), json={
        "quantity": 20.0,
        "notes": "Monthly restock",
    })
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 30.0  # 10 + 20


@pytest.mark.asyncio
async def test_low_stock(client, seed_staff):
    await client.post("/api/v1/inventory", headers=admin_headers(), json={
        "name": "Salt", "unit": "kg", "quantity": 1, "min_quantity": 5,
    })
    resp = await client.get("/api/v1/inventory/low-stock", headers=cashier_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    for item in resp.json():
        assert item["quantity"] <= item["min_quantity"]


@pytest.mark.asyncio
async def test_transaction_history(client, seed_staff):
    create = await client.post("/api/v1/inventory", headers=admin_headers(), json={
        "name": "Sugar", "unit": "kg", "quantity": 5,
    })
    item_id = create.json()["id"]
    await client.post(f"/api/v1/inventory/{item_id}/restock", headers=admin_headers(), json={
        "quantity": 10.0,
    })
    resp = await client.get(f"/api/v1/inventory/{item_id}/transactions", headers=cashier_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    assert resp.json()[0]["transaction_type"] == "restock"


@pytest.mark.asyncio
async def test_record_waste(client, seed_staff):
    create = await client.post("/api/v1/inventory", headers=admin_headers(), json={
        "name": "Tomato", "unit": "kg", "quantity": 20,
    })
    item_id = create.json()["id"]
    resp = await client.post("/api/v1/inventory/waste", headers=admin_headers(), json={
        "inventory_item_id": item_id,
        "quantity": 3.0,
        "notes": "Spoiled",
    })
    assert resp.status_code == 200
    assert resp.json()["remaining_quantity"] == 17.0  # 20 - 3
