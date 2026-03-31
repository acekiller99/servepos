"""Test staff endpoints."""
import pytest

from tests.conftest import admin_headers, cashier_headers, waiter_headers, OUTLET_ID, ADMIN_ID, WAITER_ID


@pytest.mark.asyncio
async def test_list_staff(client, seed_staff):
    resp = await client.get("/api/v1/staff", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5


@pytest.mark.asyncio
async def test_list_staff_forbidden_for_waiter(client, seed_staff):
    resp = await client.get("/api/v1/staff", headers=waiter_headers())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_staff(client, seed_staff):
    resp = await client.post("/api/v1/staff", headers=admin_headers(), json={
        "outlet_id": str(OUTLET_ID),
        "email": "newstaff@test.com",
        "password": "pass123",
        "full_name": "New Staff",
        "role": "waiter",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["full_name"] == "New Staff"
    assert data["role"] == "waiter"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_create_staff_duplicate_email(client, seed_staff):
    resp = await client.post("/api/v1/staff", headers=admin_headers(), json={
        "outlet_id": str(OUTLET_ID),
        "email": "admin@test.com",
        "password": "pass123",
        "full_name": "Duplicate",
        "role": "waiter",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_staff(client, seed_staff):
    resp = await client.get(f"/api/v1/staff/{ADMIN_ID}", headers=admin_headers())
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Admin User"


@pytest.mark.asyncio
async def test_update_staff(client, seed_staff):
    resp = await client.put(f"/api/v1/staff/{WAITER_ID}", headers=admin_headers(), json={
        "full_name": "Updated Waiter",
    })
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Waiter"


@pytest.mark.asyncio
async def test_update_staff_password(client, seed_staff):
    resp = await client.put(f"/api/v1/staff/{WAITER_ID}", headers=admin_headers(), json={
        "password": "newpass456",
    })
    assert resp.status_code == 200

    # Verify new password works
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "waiter@test.com",
        "password": "newpass456",
    })
    assert login_resp.status_code == 200


@pytest.mark.asyncio
async def test_deactivate_staff(client, seed_staff):
    resp = await client.delete(f"/api/v1/staff/{WAITER_ID}", headers=admin_headers())
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_clock_in(client, seed_staff):
    resp = await client.post(f"/api/v1/staff/{WAITER_ID}/clock-in", headers=waiter_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["staff_id"] == str(WAITER_ID)
    assert data["clock_out"] is None


@pytest.mark.asyncio
async def test_clock_in_already_clocked_in(client, seed_staff):
    await client.post(f"/api/v1/staff/{WAITER_ID}/clock-in", headers=waiter_headers())
    resp = await client.post(f"/api/v1/staff/{WAITER_ID}/clock-in", headers=waiter_headers())
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_clock_out(client, seed_staff):
    await client.post(f"/api/v1/staff/{WAITER_ID}/clock-in", headers=waiter_headers())
    resp = await client.post(f"/api/v1/staff/{WAITER_ID}/clock-out", headers=waiter_headers())
    assert resp.status_code == 200
    assert resp.json()["clock_out"] is not None


@pytest.mark.asyncio
async def test_clock_out_no_active_shift(client, seed_staff):
    resp = await client.post(f"/api/v1/staff/{WAITER_ID}/clock-out", headers=waiter_headers())
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_shift_history(client, seed_staff):
    await client.post(f"/api/v1/staff/{WAITER_ID}/clock-in", headers=waiter_headers())
    await client.post(f"/api/v1/staff/{WAITER_ID}/clock-out", headers=waiter_headers())
    resp = await client.get(f"/api/v1/staff/{WAITER_ID}/shifts", headers=waiter_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
