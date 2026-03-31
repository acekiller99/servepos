"""Test payment, e-wallet, and register endpoints."""
import uuid

import pytest

from tests.conftest import admin_headers, cashier_headers, OUTLET_ID


async def _create_paid_order(client):
    """Create an order and return its ID."""
    item = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": "PayItem", "price": 15.0,
    })
    order = await client.post("/api/v1/orders", headers=cashier_headers(), json={
        "order_type": "takeaway",
        "items": [{"menu_item_id": item.json()["id"], "item_name": "PayItem", "quantity": 1, "unit_price": 15.0}],
    })
    return order.json()


# ---- Payments ----

@pytest.mark.asyncio
async def test_process_cash_payment(client, seed_staff):
    order = await _create_paid_order(client)
    resp = await client.post("/api/v1/payments", headers=cashier_headers(), json={
        "order_id": order["id"],
        "payment_method": "cash",
        "amount": 20.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["payment_method"] == "cash"
    assert data["status"] == "completed"
    assert data["change_amount"] > 0  # gave more than total


@pytest.mark.asyncio
async def test_process_card_payment(client, seed_staff):
    order = await _create_paid_order(client)
    resp = await client.post("/api/v1/payments", headers=cashier_headers(), json={
        "order_id": order["id"],
        "payment_method": "card",
        "amount": order["total"],
        "reference_number": "TXN-12345",
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_process_ewallet_payment_pending(client, seed_staff):
    order = await _create_paid_order(client)
    resp = await client.post("/api/v1/payments", headers=cashier_headers(), json={
        "order_id": order["id"],
        "payment_method": "grabpay",
        "amount": order["total"],
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_get_payment(client, seed_staff):
    order = await _create_paid_order(client)
    pay_resp = await client.post("/api/v1/payments", headers=cashier_headers(), json={
        "order_id": order["id"],
        "payment_method": "cash",
        "amount": order["total"],
    })
    payment_id = pay_resp.json()["id"]
    resp = await client.get(f"/api/v1/payments/{payment_id}", headers=cashier_headers())
    assert resp.status_code == 200
    assert resp.json()["id"] == payment_id


@pytest.mark.asyncio
async def test_refund_payment(client, seed_staff):
    order = await _create_paid_order(client)
    pay_resp = await client.post("/api/v1/payments", headers=cashier_headers(), json={
        "order_id": order["id"],
        "payment_method": "cash",
        "amount": order["total"],
    })
    payment_id = pay_resp.json()["id"]
    resp = await client.post(f"/api/v1/payments/{payment_id}/refund", headers=admin_headers(), json={
        "reason": "Customer complaint",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "refunded"


@pytest.mark.asyncio
async def test_refund_non_completed_payment(client, seed_staff):
    order = await _create_paid_order(client)
    pay_resp = await client.post("/api/v1/payments", headers=cashier_headers(), json={
        "order_id": order["id"],
        "payment_method": "alipay",
        "amount": order["total"],
    })
    payment_id = pay_resp.json()["id"]
    resp = await client.post(f"/api/v1/payments/{payment_id}/refund", headers=admin_headers(), json={
        "reason": "test",
    })
    assert resp.status_code == 400


# ---- QR Payments ----

@pytest.mark.asyncio
async def test_generate_qr(client, seed_staff):
    order = await _create_paid_order(client)
    resp = await client.post("/api/v1/payments/qr/generate", headers=cashier_headers(), json={
        "order_id": order["id"],
        "provider": "touch_n_go",
        "amount": order["total"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "qr_code_base64" in data
    assert "payment_id" in data
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_qr_payment_status(client, seed_staff):
    order = await _create_paid_order(client)
    qr = await client.post("/api/v1/payments/qr/generate", headers=cashier_headers(), json={
        "order_id": order["id"],
        "provider": "grabpay",
        "amount": 10.0,
    })
    payment_id = qr.json()["payment_id"]
    resp = await client.get(f"/api/v1/payments/qr/{payment_id}/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_qr_callback(client, seed_staff):
    order = await _create_paid_order(client)
    qr = await client.post("/api/v1/payments/qr/generate", headers=cashier_headers(), json={
        "order_id": order["id"],
        "provider": "alipay",
        "amount": order["total"],
    })
    payment_id = qr.json()["payment_id"]

    resp = await client.post("/api/v1/payments/qr/callback", json={
        "payment_id": payment_id,
        "transaction_id": "TXN-ALIPAY-123",
        "status": "completed",
    })
    assert resp.status_code == 200

    # Verify status updated
    status = await client.get(f"/api/v1/payments/qr/{payment_id}/status")
    assert status.json()["status"] == "completed"
    assert status.json()["transaction_id"] == "TXN-ALIPAY-123"


@pytest.mark.asyncio
async def test_qr_scan(client, seed_staff):
    order = await _create_paid_order(client)
    resp = await client.post("/api/v1/payments/qr/scan", headers=cashier_headers(), json={
        "order_id": order["id"],
        "qr_data": "SOME_QR_CODE_DATA_FROM_CUSTOMER",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"


# ---- E-Wallet Providers ----

@pytest.mark.asyncio
async def test_add_ewallet_provider(client, seed_staff):
    resp = await client.post("/api/v1/ewallet/providers", headers=admin_headers(), json={
        "provider_name": "grabpay",
        "display_name": "GrabPay",
        "merchant_id": "M123",
        "credentials_encrypted": {"partner_id": "test", "partner_secret": "test"},
    })
    assert resp.status_code == 201
    assert resp.json()["provider_name"] == "grabpay"


@pytest.mark.asyncio
async def test_list_ewallet_providers(client, seed_staff):
    await client.post("/api/v1/ewallet/providers", headers=admin_headers(), json={
        "provider_name": "boost",
        "display_name": "Boost",
        "credentials_encrypted": {"key": "value"},
    })
    resp = await client.get("/api/v1/ewallet/providers", headers=cashier_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_ewallet_provider(client, seed_staff):
    create = await client.post("/api/v1/ewallet/providers", headers=admin_headers(), json={
        "provider_name": "alipay",
        "display_name": "Alipay",
        "credentials_encrypted": {"app_id": "test"},
    })
    pid = create.json()["id"]
    resp = await client.put(f"/api/v1/ewallet/providers/{pid}", headers=admin_headers(), json={
        "display_name": "Alipay+",
    })
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Alipay+"


@pytest.mark.asyncio
async def test_delete_ewallet_provider(client, seed_staff):
    create = await client.post("/api/v1/ewallet/providers", headers=admin_headers(), json={
        "provider_name": "wechat_pay",
        "display_name": "WeChat Pay",
        "credentials_encrypted": {"key": "val"},
    })
    pid = create.json()["id"]
    resp = await client.delete(f"/api/v1/ewallet/providers/{pid}", headers=admin_headers())
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_test_ewallet_provider(client, seed_staff):
    create = await client.post("/api/v1/ewallet/providers", headers=admin_headers(), json={
        "provider_name": "touch_n_go",
        "display_name": "TnG",
        "credentials_encrypted": {"client_id": "test"},
    })
    pid = create.json()["id"]
    resp = await client.post(f"/api/v1/ewallet/providers/{pid}/test", headers=admin_headers())
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_available_providers(client, seed_staff):
    resp = await client.get("/api/v1/ewallet/providers/available", headers=cashier_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 7
    assert any(p["name"] == "alipay" for p in data)


# ---- Register Sessions ----

@pytest.mark.asyncio
async def test_open_register(client, seed_staff):
    resp = await client.post("/api/v1/register/open", headers=cashier_headers(), json={
        "opening_cash": 500.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["opening_cash"] == 500.0
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_open_register_already_open(client, seed_staff):
    await client.post("/api/v1/register/open", headers=cashier_headers(), json={
        "opening_cash": 500.0,
    })
    resp = await client.post("/api/v1/register/open", headers=cashier_headers(), json={
        "opening_cash": 300.0,
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_close_register(client, seed_staff):
    await client.post("/api/v1/register/open", headers=cashier_headers(), json={
        "opening_cash": 500.0,
    })
    resp = await client.post("/api/v1/register/close", headers=cashier_headers(), json={
        "closing_cash": 550.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "closed"
    assert data["closing_cash"] == 550.0
    assert data["expected_cash"] is not None


@pytest.mark.asyncio
async def test_current_register(client, seed_staff):
    await client.post("/api/v1/register/open", headers=cashier_headers(), json={
        "opening_cash": 200.0,
    })
    resp = await client.get("/api/v1/register/current", headers=cashier_headers())
    assert resp.status_code == 200
    assert resp.json()["status"] == "open"


@pytest.mark.asyncio
async def test_current_register_none_open(client, seed_staff):
    resp = await client.get("/api/v1/register/current", headers=cashier_headers())
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_register_history(client, seed_staff):
    resp = await client.get("/api/v1/register/history", headers=admin_headers())
    assert resp.status_code == 200
