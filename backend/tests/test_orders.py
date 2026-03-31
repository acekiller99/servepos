"""Test order endpoints."""
import uuid

import pytest

from tests.conftest import admin_headers, cashier_headers, waiter_headers, OUTLET_ID


async def _create_menu_item(client, name="Test Item", price=10.0):
    resp = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": name, "price": price,
    })
    return resp.json()["id"]


async def _create_order(client, items=None, order_type="dine_in"):
    if items is None:
        item_id = await _create_menu_item(client)
        items = [{"menu_item_id": item_id, "item_name": "Test Item", "quantity": 2, "unit_price": 10.0}]
    resp = await client.post("/api/v1/orders", headers=cashier_headers(), json={
        "order_type": order_type,
        "guest_count": 2,
        "items": items,
    })
    return resp


@pytest.mark.asyncio
async def test_create_order(client, seed_staff):
    resp = await _create_order(client)
    assert resp.status_code == 201
    data = resp.json()
    assert data["order_type"] == "dine_in"
    assert data["status"] == "pending"
    assert data["payment_status"] == "unpaid"
    assert len(data["items"]) == 1
    assert data["subtotal"] == 20.0
    assert data["order_number"].startswith("#")


@pytest.mark.asyncio
async def test_create_order_price_calculation(client, seed_staff):
    resp = await _create_order(client)
    data = resp.json()
    # outlet tax_rate=6%, service_charge=10%
    assert data["subtotal"] == 20.0
    assert abs(data["tax_amount"] - 1.2) < 0.01  # 20 * 6%
    assert abs(data["service_charge"] - 2.0) < 0.01  # 20 * 10%
    assert abs(data["total"] - 23.2) < 0.01  # 20 + 1.2 + 2.0


@pytest.mark.asyncio
async def test_list_orders(client, seed_staff):
    await _create_order(client)
    resp = await client.get("/api/v1/orders", headers=cashier_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_list_orders_filter_by_status(client, seed_staff):
    await _create_order(client)
    resp = await client.get("/api/v1/orders?status=pending", headers=cashier_headers())
    assert resp.status_code == 200
    for order in resp.json():
        assert order["status"] == "pending"


@pytest.mark.asyncio
async def test_get_order(client, seed_staff):
    create = await _create_order(client)
    order_id = create.json()["id"]
    resp = await client.get(f"/api/v1/orders/{order_id}", headers=cashier_headers())
    assert resp.status_code == 200
    assert resp.json()["id"] == order_id


@pytest.mark.asyncio
async def test_update_order(client, seed_staff):
    create = await _create_order(client)
    order_id = create.json()["id"]
    resp = await client.put(f"/api/v1/orders/{order_id}", headers=cashier_headers(), json={
        "customer_name": "John Doe",
    })
    assert resp.status_code == 200
    assert resp.json()["customer_name"] == "John Doe"


@pytest.mark.asyncio
async def test_add_items_to_order(client, seed_staff):
    create = await _create_order(client)
    order_id = create.json()["id"]
    item_id = await _create_menu_item(client, "Extra Item", 5.0)
    resp = await client.post(f"/api/v1/orders/{order_id}/items", headers=cashier_headers(), json=[
        {"menu_item_id": item_id, "item_name": "Extra Item", "quantity": 1, "unit_price": 5.0},
    ])
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2
    assert resp.json()["subtotal"] == 25.0  # 20 + 5


@pytest.mark.asyncio
async def test_update_order_item(client, seed_staff):
    create = await _create_order(client)
    order_id = create.json()["id"]
    item_id = create.json()["items"][0]["id"]
    resp = await client.put(f"/api/v1/orders/{order_id}/items/{item_id}", headers=cashier_headers(), json={
        "quantity": 3,
    })
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 3


@pytest.mark.asyncio
async def test_remove_order_item(client, seed_staff):
    create = await _create_order(client)
    order_id = create.json()["id"]
    item_id = create.json()["items"][0]["id"]
    resp = await client.delete(f"/api/v1/orders/{order_id}/items/{item_id}", headers=cashier_headers())
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_send_to_kitchen(client, seed_staff):
    create = await _create_order(client)
    order_id = create.json()["id"]
    resp = await client.post(f"/api/v1/orders/{order_id}/send-to-kitchen", headers=cashier_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "confirmed"
    for item in data["items"]:
        if not item["is_void"]:
            assert item["sent_to_kitchen"] is True
            assert item["status"] == "preparing"


@pytest.mark.asyncio
async def test_update_order_status(client, seed_staff):
    create = await _create_order(client)
    order_id = create.json()["id"]
    resp = await client.put(f"/api/v1/orders/{order_id}/status", headers=cashier_headers(), json={
        "status": "completed",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["completed_at"] is not None


@pytest.mark.asyncio
async def test_void_order(client, seed_staff):
    create = await _create_order(client)
    order_id = create.json()["id"]
    resp = await client.post(f"/api/v1/orders/{order_id}/void", headers=admin_headers(), json={
        "void_reason": "Customer left",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_void"] is True
    assert data["status"] == "cancelled"
    assert data["void_reason"] == "Customer left"


@pytest.mark.asyncio
async def test_void_order_forbidden_for_cashier(client, seed_staff):
    create = await _create_order(client)
    order_id = create.json()["id"]
    resp = await client.post(f"/api/v1/orders/{order_id}/void", headers=waiter_headers(), json={
        "void_reason": "test",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_apply_discount(client, seed_staff):
    create = await _create_order(client)
    order_id = create.json()["id"]
    resp = await client.post(f"/api/v1/orders/{order_id}/discount", headers=cashier_headers(), json={
        "discount_amount": 5.0,
        "discount_reason": "Happy hour",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["discount_amount"] == 5.0
    assert data["total"] < create.json()["total"]


@pytest.mark.asyncio
async def test_active_orders(client, seed_staff):
    await _create_order(client)
    resp = await client.get("/api/v1/orders/active", headers=cashier_headers())
    assert resp.status_code == 200
    for order in resp.json():
        assert order["status"] in ["pending", "confirmed", "preparing", "ready"]


@pytest.mark.asyncio
async def test_sync_offline_orders(client, seed_staff):
    item_id = await _create_menu_item(client)
    resp = await client.post("/api/v1/orders/sync", headers=cashier_headers(), json=[
        {
            "order_type": "takeaway",
            "items": [{"menu_item_id": item_id, "item_name": "Sync Item", "quantity": 1, "unit_price": 8.0}],
        },
        {
            "order_type": "takeaway",
            "items": [{"menu_item_id": item_id, "item_name": "Sync Item 2", "quantity": 2, "unit_price": 6.0}],
        },
    ])
    assert resp.status_code == 200
    assert len(resp.json()) == 2
