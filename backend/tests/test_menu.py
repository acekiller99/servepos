"""Test menu endpoints."""
import uuid

import pytest

from tests.conftest import admin_headers, waiter_headers, OUTLET_ID


@pytest.mark.asyncio
async def test_create_category(client, seed_staff):
    resp = await client.post("/api/v1/menu/categories", headers=admin_headers(), json={
        "name": "Drinks",
        "description": "Beverages",
        "sort_order": 1,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Drinks"
    assert data["outlet_id"] == str(OUTLET_ID)


@pytest.mark.asyncio
async def test_list_categories(client, seed_staff):
    await client.post("/api/v1/menu/categories", headers=admin_headers(), json={"name": "Cat1"})
    await client.post("/api/v1/menu/categories", headers=admin_headers(), json={"name": "Cat2"})
    resp = await client.get("/api/v1/menu/categories", headers=admin_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_update_category(client, seed_staff):
    create = await client.post("/api/v1/menu/categories", headers=admin_headers(), json={"name": "Old"})
    cat_id = create.json()["id"]
    resp = await client.put(f"/api/v1/menu/categories/{cat_id}", headers=admin_headers(), json={
        "name": "Updated",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_category(client, seed_staff):
    create = await client.post("/api/v1/menu/categories", headers=admin_headers(), json={"name": "ToDelete"})
    cat_id = create.json()["id"]
    resp = await client.delete(f"/api/v1/menu/categories/{cat_id}", headers=admin_headers())
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_create_menu_item(client, seed_staff):
    cat = await client.post("/api/v1/menu/categories", headers=admin_headers(), json={"name": "Food"})
    cat_id = cat.json()["id"]

    resp = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "category_id": cat_id,
        "name": "Chicken Rice",
        "price": 8.50,
        "cost_price": 3.00,
        "description": "Hainan style",
        "allergens": ["gluten"],
        "tags": ["bestseller"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Chicken Rice"
    assert data["price"] == 8.50


@pytest.mark.asyncio
async def test_list_menu_items(client, seed_staff):
    await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": "Item1", "price": 5.0,
    })
    resp = await client.get("/api/v1/menu/items", headers=admin_headers())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_menu_item(client, seed_staff):
    create = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": "TestItem", "price": 7.0,
    })
    item_id = create.json()["id"]
    resp = await client.get(f"/api/v1/menu/items/{item_id}", headers=admin_headers())
    assert resp.status_code == 200
    assert resp.json()["name"] == "TestItem"


@pytest.mark.asyncio
async def test_update_menu_item(client, seed_staff):
    create = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": "OldItem", "price": 5.0,
    })
    item_id = create.json()["id"]
    resp = await client.put(f"/api/v1/menu/items/{item_id}", headers=admin_headers(), json={
        "name": "NewItem", "price": 9.0,
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "NewItem"
    assert resp.json()["price"] == 9.0


@pytest.mark.asyncio
async def test_delete_menu_item(client, seed_staff):
    create = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": "Deletable", "price": 3.0,
    })
    item_id = create.json()["id"]
    resp = await client.delete(f"/api/v1/menu/items/{item_id}", headers=admin_headers())
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_toggle_availability(client, seed_staff):
    create = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": "Toggleable", "price": 4.0,
    })
    item_id = create.json()["id"]
    resp = await client.put(f"/api/v1/menu/items/{item_id}/availability", headers=admin_headers(), json={
        "is_available": False,
    })
    assert resp.status_code == 200
    assert resp.json()["is_available"] is False


@pytest.mark.asyncio
async def test_create_modifier_group(client, seed_staff):
    item = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": "Noodles", "price": 7.0,
    })
    item_id = item.json()["id"]

    resp = await client.post("/api/v1/menu/modifiers", headers=admin_headers(), json={
        "name": "Spice Level",
        "selection_type": "single",
        "min_selections": 1,
        "max_selections": 1,
        "is_required": True,
        "options": [
            {"name": "Mild", "price_adjustment": 0},
            {"name": "Spicy", "price_adjustment": 0.50},
            {"name": "Extra Spicy", "price_adjustment": 1.00},
        ],
        "menu_item_ids": [item_id],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Spice Level"
    assert len(data["options"]) == 3


@pytest.mark.asyncio
async def test_list_modifiers(client, seed_staff):
    resp = await client.get("/api/v1/menu/modifiers", headers=admin_headers())
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_create_combo(client, seed_staff):
    item1 = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": "Burger", "price": 10.0,
    })
    item2 = await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "name": "Fries", "price": 4.0,
    })

    resp = await client.post("/api/v1/menu/combos", headers=admin_headers(), json={
        "name": "Burger Combo",
        "price": 12.0,
        "items": [
            {"menu_item_id": item1.json()["id"], "quantity": 1},
            {"menu_item_id": item2.json()["id"], "quantity": 1},
        ],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Burger Combo"
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_combos(client, seed_staff):
    resp = await client.get("/api/v1/menu/combos", headers=admin_headers())
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_full_menu(client, seed_staff):
    cat = await client.post("/api/v1/menu/categories", headers=admin_headers(), json={"name": "Mains"})
    cat_id = cat.json()["id"]
    await client.post("/api/v1/menu/items", headers=admin_headers(), json={
        "category_id": cat_id, "name": "Steak", "price": 25.0,
    })
    resp = await client.get("/api/v1/menu/full", headers=admin_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(c["name"] == "Mains" for c in data)


@pytest.mark.asyncio
async def test_waiter_cannot_create_menu_item(client, seed_staff):
    resp = await client.post("/api/v1/menu/items", headers=waiter_headers(), json={
        "name": "Unauthorized", "price": 5.0,
    })
    assert resp.status_code == 403
