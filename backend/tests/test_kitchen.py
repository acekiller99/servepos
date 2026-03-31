"""Test kitchen display system endpoints."""
import pytest

from tests.conftest import admin_headers, cashier_headers, kitchen_headers


async def _create_order_and_send_to_kitchen(client):
    """Helper: create order, send to kitchen, return order and item IDs."""
    item = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": "KDS Item", "price": 10.0,
    })
    order = await client.post("/api/v1/orders", headers=cashier_headers(), json={
        "order_type": "dine_in",
        "items": [{"menu_item_id": item.json()["id"], "item_name": "KDS Item", "quantity": 2, "unit_price": 10.0}],
    })
    order_id = order.json()["id"]
    await client.post(f"/api/v1/orders/{order_id}/send-to-kitchen", headers=cashier_headers())

    # Re-fetch to get updated status
    updated = await client.get(f"/api/v1/orders/{order_id}", headers=cashier_headers())
    order_item_id = updated.json()["items"][0]["id"]
    return order_id, order_item_id


@pytest.mark.asyncio
async def test_kitchen_orders(client, seed_staff):
    await _create_order_and_send_to_kitchen(client)
    resp = await client.get("/api/v1/kitchen/orders", headers=kitchen_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["items"][0]["sent_to_kitchen"] is True


@pytest.mark.asyncio
async def test_update_kitchen_item_status(client, seed_staff):
    _, item_id = await _create_order_and_send_to_kitchen(client)
    resp = await client.put(f"/api/v1/kitchen/items/{item_id}/status", headers=kitchen_headers(), json={
        "status": "ready",
    })
    assert resp.status_code == 200
    assert resp.json()["new_status"] == "ready"


@pytest.mark.asyncio
async def test_update_kitchen_item_invalid_status(client, seed_staff):
    _, item_id = await _create_order_and_send_to_kitchen(client)
    resp = await client.put(f"/api/v1/kitchen/items/{item_id}/status", headers=kitchen_headers(), json={
        "status": "invalid",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_bump_item(client, seed_staff):
    _, item_id = await _create_order_and_send_to_kitchen(client)
    resp = await client.post(f"/api/v1/kitchen/items/{item_id}/bump", headers=kitchen_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "order_ready" in data


@pytest.mark.asyncio
async def test_kitchen_stats(client, seed_staff):
    resp = await client.get("/api/v1/kitchen/stats", headers=kitchen_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "pending_items" in data
    assert "avg_prep_time_seconds" in data
