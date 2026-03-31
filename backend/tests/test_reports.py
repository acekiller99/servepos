"""Test report endpoints."""
import pytest

from tests.conftest import admin_headers, cashier_headers, waiter_headers


async def _populate_test_data(client):
    """Create some orders and payments for report testing."""
    item = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": "Report Item", "price": 10.0, "cost_price": 4.0,
    })
    item_id = item.json()["id"]

    # Create a few orders
    for i in range(3):
        order = await client.post("/api/v1/orders", headers=cashier_headers(), json={
            "order_type": "dine_in",
            "items": [{"menu_item_id": item_id, "item_name": "Report Item", "quantity": i + 1, "unit_price": 10.0}],
        })
        order_id = order.json()["id"]
        # Pay for each
        await client.post("/api/v1/payments", headers=cashier_headers(), json={
            "order_id": order_id,
            "payment_method": "cash" if i % 2 == 0 else "card",
            "amount": order.json()["total"],
        })
        # Mark completed
        await client.put(f"/api/v1/orders/{order_id}/status", headers=cashier_headers(), json={
            "status": "completed",
        })


@pytest.mark.asyncio
async def test_daily_sales(client, seed_staff):
    await _populate_test_data(client)
    resp = await client.get("/api/v1/reports/daily-sales", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert "date" in data[0]
    assert "order_count" in data[0]
    assert "total" in data[0]


@pytest.mark.asyncio
async def test_sales_by_item(client, seed_staff):
    await _populate_test_data(client)
    resp = await client.get("/api/v1/reports/sales-by-item", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert "item_name" in data[0]
    assert "total_qty" in data[0]
    assert "total_revenue" in data[0]


@pytest.mark.asyncio
async def test_sales_by_category(client, seed_staff):
    resp = await client.get("/api/v1/reports/sales-by-category", headers=admin_headers())
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sales_by_staff(client, seed_staff):
    await _populate_test_data(client)
    resp = await client.get("/api/v1/reports/sales-by-staff", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    if data:
        assert "staff_name" in data[0]
        assert "order_count" in data[0]


@pytest.mark.asyncio
async def test_hourly_sales(client, seed_staff):
    await _populate_test_data(client)
    resp = await client.get("/api/v1/reports/hourly-sales", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    if data:
        assert "hour" in data[0]
        assert "total_sales" in data[0]


@pytest.mark.asyncio
async def test_payment_methods_report(client, seed_staff):
    await _populate_test_data(client)
    resp = await client.get("/api/v1/reports/payment-methods", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    if data:
        assert "payment_method" in data[0]
        assert "count" in data[0]


@pytest.mark.asyncio
async def test_inventory_report(client, seed_staff):
    await client.post("/api/v1/inventory", headers=admin_headers(), json={
        "name": "Report Rice", "unit": "kg", "quantity": 50, "min_quantity": 10, "cost_per_unit": 3.0,
    })
    resp = await client.get("/api/v1/reports/inventory", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert "name" in data[0]
    assert "is_low_stock" in data[0]


@pytest.mark.asyncio
async def test_waste_report(client, seed_staff):
    resp = await client.get("/api/v1/reports/waste", headers=admin_headers())
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_profit_margin(client, seed_staff):
    await _populate_test_data(client)
    resp = await client.get("/api/v1/reports/profit-margin", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    if data:
        assert "margin" in data[0]
        assert "margin_pct" in data[0]


@pytest.mark.asyncio
async def test_peak_hours(client, seed_staff):
    await _populate_test_data(client)
    resp = await client.get("/api/v1/reports/peak-hours", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    if data:
        assert "day_of_week" in data[0]
        assert "hour" in data[0]


@pytest.mark.asyncio
async def test_export_csv(client, seed_staff):
    await _populate_test_data(client)
    resp = await client.get(
        "/api/v1/reports/export?type=daily_sales&format=csv",
        headers=admin_headers(),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reports_forbidden_for_waiter(client, seed_staff):
    resp = await client.get("/api/v1/reports/daily-sales", headers=waiter_headers())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_reports_forbidden_for_cashier(client, seed_staff):
    resp = await client.get("/api/v1/reports/daily-sales", headers=cashier_headers())
    assert resp.status_code == 403
