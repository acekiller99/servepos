"""Test promotion endpoints."""
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import admin_headers, cashier_headers, waiter_headers


@pytest.mark.asyncio
async def test_create_promotion(client, seed_staff):
    resp = await client.post("/api/v1/promotions", headers=admin_headers(), json={
        "name": "Happy Hour",
        "type": "percentage",
        "value": 20.0,
        "promo_code": "HAPPY20",
        "is_active": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Happy Hour"
    assert data["type"] == "percentage"
    assert data["promo_code"] == "HAPPY20"


@pytest.mark.asyncio
async def test_list_promotions(client, seed_staff):
    await client.post("/api/v1/promotions", headers=admin_headers(), json={
        "name": "Promo1", "type": "fixed_amount", "value": 5.0,
    })
    resp = await client.get("/api/v1/promotions", headers=cashier_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_promotion(client, seed_staff):
    create = await client.post("/api/v1/promotions", headers=admin_headers(), json={
        "name": "Old Promo", "type": "percentage", "value": 10.0,
    })
    promo_id = create.json()["id"]
    resp = await client.put(f"/api/v1/promotions/{promo_id}", headers=admin_headers(), json={
        "name": "Updated Promo", "value": 15.0,
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Promo"
    assert resp.json()["value"] == 15.0


@pytest.mark.asyncio
async def test_delete_promotion(client, seed_staff):
    create = await client.post("/api/v1/promotions", headers=admin_headers(), json={
        "name": "Deletable", "type": "fixed_amount", "value": 3.0,
    })
    promo_id = create.json()["id"]
    resp = await client.delete(f"/api/v1/promotions/{promo_id}", headers=admin_headers())
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_validate_promo_code(client, seed_staff):
    await client.post("/api/v1/promotions", headers=admin_headers(), json={
        "name": "Validate Test",
        "type": "percentage",
        "value": 10.0,
        "promo_code": "SAVE10",
    })
    resp = await client.post("/api/v1/promotions/validate", headers=cashier_headers(), json={
        "promo_code": "SAVE10",
        "order_total": 50.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["discount_amount"] == 5.0  # 50 * 10%


@pytest.mark.asyncio
async def test_validate_promo_fixed_amount(client, seed_staff):
    await client.post("/api/v1/promotions", headers=admin_headers(), json={
        "name": "Fixed Discount",
        "type": "fixed_amount",
        "value": 7.0,
        "promo_code": "FLAT7",
    })
    resp = await client.post("/api/v1/promotions/validate", headers=cashier_headers(), json={
        "promo_code": "FLAT7",
        "order_total": 30.0,
    })
    assert resp.status_code == 200
    assert resp.json()["discount_amount"] == 7.0


@pytest.mark.asyncio
async def test_validate_invalid_promo(client, seed_staff):
    resp = await client.post("/api/v1/promotions/validate", headers=cashier_headers(), json={
        "promo_code": "NONEXISTENT",
        "order_total": 50.0,
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_validate_promo_min_order(client, seed_staff):
    await client.post("/api/v1/promotions", headers=admin_headers(), json={
        "name": "Min Order",
        "type": "percentage",
        "value": 10.0,
        "promo_code": "MIN50",
        "min_order_amount": 50.0,
    })
    resp = await client.post("/api/v1/promotions/validate", headers=cashier_headers(), json={
        "promo_code": "MIN50",
        "order_total": 30.0,
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_validate_expired_promo(client, seed_staff):
    past = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    await client.post("/api/v1/promotions", headers=admin_headers(), json={
        "name": "Expired",
        "type": "percentage",
        "value": 5.0,
        "promo_code": "EXPIRED",
        "valid_until": past,
    })
    resp = await client.post("/api/v1/promotions/validate", headers=cashier_headers(), json={
        "promo_code": "EXPIRED",
        "order_total": 50.0,
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_waiter_cannot_create_promotion(client, seed_staff):
    resp = await client.post("/api/v1/promotions", headers=waiter_headers(), json={
        "name": "Unauthorized", "type": "percentage", "value": 5.0,
    })
    assert resp.status_code == 403
