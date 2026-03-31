"""Test reservation endpoints."""
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import admin_headers, cashier_headers, waiter_headers


async def _create_table_for_reservation(client):
    area = await client.post("/api/v1/floor-areas", headers=admin_headers(), json={
        "name": "Reservation Area",
    })
    table = await client.post("/api/v1/tables", headers=admin_headers(), json={
        "floor_area_id": area.json()["id"],
        "table_number": f"R{id(area)}",
        "capacity": 6,
    })
    return table.json()["id"]


@pytest.mark.asyncio
async def test_create_reservation(client, seed_staff):
    table_id = await _create_table_for_reservation(client)
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = await client.post("/api/v1/reservations", headers=cashier_headers(), json={
        "table_id": table_id,
        "customer_name": "Jane Doe",
        "customer_phone": "+60123456789",
        "party_size": 4,
        "reservation_time": future,
        "duration_minutes": 120,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["customer_name"] == "Jane Doe"
    assert data["party_size"] == 4
    assert data["status"] == "confirmed"


@pytest.mark.asyncio
async def test_list_reservations(client, seed_staff):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    await client.post("/api/v1/reservations", headers=cashier_headers(), json={
        "customer_name": "Test Guest",
        "party_size": 2,
        "reservation_time": future,
    })
    resp = await client.get("/api/v1/reservations", headers=cashier_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_reservation(client, seed_staff):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create = await client.post("/api/v1/reservations", headers=cashier_headers(), json={
        "customer_name": "Update Test",
        "party_size": 2,
        "reservation_time": future,
    })
    res_id = create.json()["id"]
    resp = await client.put(f"/api/v1/reservations/{res_id}", headers=cashier_headers(), json={
        "party_size": 6,
        "notes": "Birthday party",
    })
    assert resp.status_code == 200
    assert resp.json()["party_size"] == 6
    assert resp.json()["notes"] == "Birthday party"


@pytest.mark.asyncio
async def test_update_reservation_status(client, seed_staff):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create = await client.post("/api/v1/reservations", headers=cashier_headers(), json={
        "customer_name": "Status Test",
        "party_size": 3,
        "reservation_time": future,
    })
    res_id = create.json()["id"]
    resp = await client.put(f"/api/v1/reservations/{res_id}/status", headers=cashier_headers(), json={
        "status": "seated",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "seated"


@pytest.mark.asyncio
async def test_cancel_reservation(client, seed_staff):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create = await client.post("/api/v1/reservations", headers=cashier_headers(), json={
        "customer_name": "Cancel Test",
        "party_size": 2,
        "reservation_time": future,
    })
    res_id = create.json()["id"]
    resp = await client.put(f"/api/v1/reservations/{res_id}/status", headers=cashier_headers(), json={
        "status": "cancelled",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_no_show(client, seed_staff):
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create = await client.post("/api/v1/reservations", headers=cashier_headers(), json={
        "customer_name": "No Show",
        "party_size": 1,
        "reservation_time": future,
    })
    res_id = create.json()["id"]
    resp = await client.put(f"/api/v1/reservations/{res_id}/status", headers=cashier_headers(), json={
        "status": "no_show",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_show"


@pytest.mark.asyncio
async def test_check_availability(client, seed_staff):
    table_id = await _create_table_for_reservation(client)
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    resp = await client.get(
        f"/api/v1/reservations/availability?date={tomorrow}&party_size=2",
        headers=cashier_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert "time" in data[0]
    assert "available_tables" in data[0]
    assert "available_count" in data[0]
