"""Test table and floor area endpoints."""
import uuid

import pytest

from tests.conftest import admin_headers, waiter_headers, OUTLET_ID


async def _create_floor_area(client, name="Main Hall"):
    resp = await client.post("/api/v1/floor-areas", headers=admin_headers(), json={
        "name": name, "sort_order": 0,
    })
    return resp.json()["id"]


async def _create_table(client, floor_area_id, number="T1"):
    resp = await client.post("/api/v1/tables", headers=admin_headers(), json={
        "floor_area_id": floor_area_id,
        "table_number": number,
        "capacity": 4,
    })
    return resp.json()


# ---- Floor Areas ----

@pytest.mark.asyncio
async def test_create_floor_area(client, seed_staff):
    resp = await client.post("/api/v1/floor-areas", headers=admin_headers(), json={
        "name": "Patio", "sort_order": 1,
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "Patio"


@pytest.mark.asyncio
async def test_list_floor_areas(client, seed_staff):
    await _create_floor_area(client, "Hall A")
    resp = await client.get("/api/v1/floor-areas", headers=admin_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_floor_area(client, seed_staff):
    area_id = await _create_floor_area(client, "Old Name")
    resp = await client.put(f"/api/v1/floor-areas/{area_id}", headers=admin_headers(), json={
        "name": "New Name",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_floor_area(client, seed_staff):
    area_id = await _create_floor_area(client, "ToDelete")
    resp = await client.delete(f"/api/v1/floor-areas/{area_id}", headers=admin_headers())
    assert resp.status_code == 204


# ---- Tables ----

@pytest.mark.asyncio
async def test_create_table(client, seed_staff):
    area_id = await _create_floor_area(client)
    resp = await client.post("/api/v1/tables", headers=admin_headers(), json={
        "floor_area_id": area_id,
        "table_number": "T1",
        "capacity": 6,
        "shape": "circle",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["table_number"] == "T1"
    assert data["capacity"] == 6
    assert data["shape"] == "circle"
    assert data["status"] == "available"


@pytest.mark.asyncio
async def test_list_tables(client, seed_staff):
    area_id = await _create_floor_area(client)
    await _create_table(client, area_id, "T10")
    resp = await client.get("/api/v1/tables", headers=admin_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_table(client, seed_staff):
    area_id = await _create_floor_area(client)
    table = await _create_table(client, area_id, "T20")
    resp = await client.get(f"/api/v1/tables/{table['id']}", headers=admin_headers())
    assert resp.status_code == 200
    assert resp.json()["table_number"] == "T20"


@pytest.mark.asyncio
async def test_get_floor_plan(client, seed_staff):
    area_id = await _create_floor_area(client)
    await _create_table(client, area_id, "T30")
    resp = await client.get("/api/v1/tables/floor-plan", headers=admin_headers())
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_floor_plan_positions(client, seed_staff):
    area_id = await _create_floor_area(client)
    table = await _create_table(client, area_id, "T40")
    resp = await client.put("/api/v1/tables/floor-plan", headers=admin_headers(), json={
        "tables": [{"id": table["id"], "pos_x": 100, "pos_y": 200}],
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_table_status(client, seed_staff):
    area_id = await _create_floor_area(client)
    table = await _create_table(client, area_id, "T50")
    resp = await client.put(f"/api/v1/tables/{table['id']}/status", headers=waiter_headers(), json={
        "status": "cleaning",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "cleaning"


@pytest.mark.asyncio
async def test_transfer_table(client, seed_staff):
    area_id = await _create_floor_area(client)
    t1 = await _create_table(client, area_id, "T60")
    t2 = await _create_table(client, area_id, "T61")

    # Create an order on T1 to have something to transfer
    item_resp = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": "Transfer Item", "price": 10.0,
    })
    item_id = item_resp.json()["id"]
    order_resp = await client.post("/api/v1/orders", headers=waiter_headers(), json={
        "order_type": "dine_in",
        "table_id": t1["id"],
        "items": [{"menu_item_id": item_id, "item_name": "Transfer Item", "quantity": 1, "unit_price": 10.0}],
    })
    order_id = order_resp.json()["id"]

    resp = await client.post(f"/api/v1/tables/{t1['id']}/transfer", headers=waiter_headers(), json={
        "target_table_id": t2["id"],
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "occupied"


@pytest.mark.asyncio
async def test_merge_tables(client, seed_staff):
    area_id = await _create_floor_area(client)
    t1 = await _create_table(client, area_id, "T70")
    t2 = await _create_table(client, area_id, "T71")
    t3 = await _create_table(client, area_id, "T72")
    resp = await client.post(f"/api/v1/tables/{t1['id']}/merge", headers=waiter_headers(), json={
        "merge_table_ids": [t2["id"], t3["id"]],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["merged_with"]) == 2
