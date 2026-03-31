"""Test delivery platform and delivery order endpoints."""
import uuid

import pytest

from tests.conftest import admin_headers, cashier_headers, waiter_headers, OUTLET_ID


# ---- Delivery Platforms ----

@pytest.mark.asyncio
async def test_add_delivery_platform(client, seed_staff):
    resp = await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "foodpanda",
        "display_name": "FoodPanda",
        "store_id": "FP-123",
        "credentials_encrypted": {"api_token": "test_token", "vendor_id": "V001"},
        "auto_accept": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["platform_name"] == "foodpanda"
    assert data["auto_accept"] is True


@pytest.mark.asyncio
async def test_list_delivery_platforms(client, seed_staff):
    await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "grabfood",
        "display_name": "GrabFood",
        "credentials_encrypted": {"key": "val"},
    })
    resp = await client.get("/api/v1/delivery/platforms", headers=cashier_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_delivery_platform(client, seed_staff):
    create = await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "shopeefood",
        "display_name": "ShopeeFood",
        "credentials_encrypted": {"key": "val"},
    })
    pid = create.json()["id"]
    resp = await client.put(f"/api/v1/delivery/platforms/{pid}", headers=admin_headers(), json={
        "auto_accept": True,
        "polling_interval_seconds": 15,
    })
    assert resp.status_code == 200
    assert resp.json()["auto_accept"] is True


@pytest.mark.asyncio
async def test_delete_delivery_platform(client, seed_staff):
    create = await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "grabfood",
        "display_name": "GrabFood",
        "credentials_encrypted": {"key": "val"},
    })
    pid = create.json()["id"]
    resp = await client.delete(f"/api/v1/delivery/platforms/{pid}", headers=admin_headers())
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_test_delivery_platform(client, seed_staff):
    create = await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "foodpanda",
        "display_name": "FoodPanda",
        "credentials_encrypted": {"token": "test"},
    })
    pid = create.json()["id"]
    resp = await client.post(f"/api/v1/delivery/platforms/{pid}/test", headers=admin_headers())
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---- Delivery Webhooks ----

@pytest.mark.asyncio
async def test_foodpanda_webhook(client, seed_staff):
    # Create platform first
    await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "foodpanda",
        "display_name": "FoodPanda",
        "credentials_encrypted": {"token": "test"},
        "auto_accept": False,
    })
    resp = await client.post("/api/v1/delivery/webhook/foodpanda", json={
        "order_id": "FP-ORDER-001",
        "order_number": "FP-A1B2",
        "customer_name": "Delivery Customer",
        "customer_phone": "+60111222333",
        "delivery_address": "123 Delivery St",
        "subtotal": 25.0,
        "total": 28.0,
        "commission": 3.0,
    })
    assert resp.status_code == 200
    assert "delivery_order_id" in resp.json()


@pytest.mark.asyncio
async def test_grabfood_webhook(client, seed_staff):
    await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "grabfood",
        "display_name": "GrabFood",
        "credentials_encrypted": {"token": "test"},
    })
    resp = await client.post("/api/v1/delivery/webhook/grabfood", json={
        "order_id": "GF-ORDER-001",
        "customer_name": "Grab Customer",
        "subtotal": 30.0,
        "total": 33.0,
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_shopeefood_webhook(client, seed_staff):
    await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "shopeefood",
        "display_name": "ShopeeFood",
        "credentials_encrypted": {"token": "test"},
    })
    resp = await client.post("/api/v1/delivery/webhook/shopeefood", json={
        "order_id": "SF-ORDER-001",
        "customer_name": "Shopee Customer",
        "subtotal": 20.0,
        "total": 22.0,
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_webhook_auto_accept(client, seed_staff):
    await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "foodpanda",
        "display_name": "FoodPanda",
        "credentials_encrypted": {"token": "test"},
        "auto_accept": True,
    })
    resp = await client.post("/api/v1/delivery/webhook/foodpanda", json={
        "order_id": "FP-AUTO-001",
        "customer_name": "Auto Customer",
        "subtotal": 15.0,
        "total": 18.0,
    })
    assert resp.status_code == 200
    # Verify auto-accepted
    delivery_id = resp.json()["delivery_order_id"]
    detail = await client.get(f"/api/v1/delivery/orders/{delivery_id}", headers=cashier_headers())
    assert detail.json()["is_accepted"] is True
    assert detail.json()["platform_status"] == "accepted"


# ---- Delivery Order Management ----

@pytest.mark.asyncio
async def test_list_delivery_orders(client, seed_staff):
    await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "foodpanda",
        "display_name": "FoodPanda",
        "credentials_encrypted": {"token": "test"},
    })
    await client.post("/api/v1/delivery/webhook/foodpanda", json={
        "order_id": "FP-LIST-001",
        "subtotal": 10.0,
        "total": 12.0,
    })
    resp = await client.get("/api/v1/delivery/orders", headers=cashier_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_pending_delivery_orders(client, seed_staff):
    await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "grabfood",
        "display_name": "GrabFood",
        "credentials_encrypted": {"token": "test"},
    })
    await client.post("/api/v1/delivery/webhook/grabfood", json={
        "order_id": "GF-PEND-001",
        "subtotal": 10.0,
        "total": 12.0,
    })
    resp = await client.get("/api/v1/delivery/orders/pending", headers=cashier_headers())
    assert resp.status_code == 200
    for order in resp.json():
        assert order["is_accepted"] is False


@pytest.mark.asyncio
async def test_accept_delivery_order(client, seed_staff):
    await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "foodpanda",
        "display_name": "FoodPanda",
        "credentials_encrypted": {"token": "test"},
    })
    webhook = await client.post("/api/v1/delivery/webhook/foodpanda", json={
        "order_id": "FP-ACCEPT-001",
        "subtotal": 20.0,
        "total": 23.0,
    })
    delivery_id = webhook.json()["delivery_order_id"]
    resp = await client.post(f"/api/v1/delivery/orders/{delivery_id}/accept", headers=cashier_headers())
    assert resp.status_code == 200
    assert resp.json()["is_accepted"] is True
    assert resp.json()["platform_status"] == "accepted"


@pytest.mark.asyncio
async def test_reject_delivery_order(client, seed_staff):
    await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "grabfood",
        "display_name": "GrabFood",
        "credentials_encrypted": {"token": "test"},
    })
    webhook = await client.post("/api/v1/delivery/webhook/grabfood", json={
        "order_id": "GF-REJECT-001",
        "subtotal": 10.0,
        "total": 12.0,
    })
    delivery_id = webhook.json()["delivery_order_id"]
    resp = await client.post(f"/api/v1/delivery/orders/{delivery_id}/reject", headers=cashier_headers(), json={
        "reason": "Kitchen closed",
    })
    assert resp.status_code == 200
    assert resp.json()["platform_status"] == "cancelled"
    assert resp.json()["rejected_reason"] == "Kitchen closed"


@pytest.mark.asyncio
async def test_mark_delivery_ready(client, seed_staff):
    await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "foodpanda",
        "display_name": "FoodPanda",
        "credentials_encrypted": {"token": "test"},
    })
    webhook = await client.post("/api/v1/delivery/webhook/foodpanda", json={
        "order_id": "FP-READY-001",
        "subtotal": 15.0,
        "total": 18.0,
    })
    delivery_id = webhook.json()["delivery_order_id"]
    await client.post(f"/api/v1/delivery/orders/{delivery_id}/accept", headers=cashier_headers())
    resp = await client.post(f"/api/v1/delivery/orders/{delivery_id}/ready", headers=cashier_headers())
    assert resp.status_code == 200
    assert resp.json()["platform_status"] == "ready_for_pickup"


@pytest.mark.asyncio
async def test_update_delivery_status(client, seed_staff):
    await client.post("/api/v1/delivery/platforms", headers=admin_headers(), json={
        "platform_name": "shopeefood",
        "display_name": "ShopeeFood",
        "credentials_encrypted": {"token": "test"},
    })
    webhook = await client.post("/api/v1/delivery/webhook/shopeefood", json={
        "order_id": "SF-STATUS-001",
        "subtotal": 12.0,
        "total": 15.0,
    })
    delivery_id = webhook.json()["delivery_order_id"]
    resp = await client.put(f"/api/v1/delivery/orders/{delivery_id}/status", headers=cashier_headers(), json={
        "status": "preparing",
    })
    assert resp.status_code == 200
    assert resp.json()["platform_status"] == "preparing"
