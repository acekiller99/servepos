from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.menu import (
    ComboItem,
    ComboMeal,
    MenuCategory,
    MenuItem,
    MenuItemModifierGroup,
    ModifierGroup,
    ModifierOption,
)
from app.models.staff import Staff
from app.schemas.menu import (
    AvailabilityUpdate,
    ComboMealCreate,
    ComboMealResponse,
    ComboMealUpdate,
    MenuCategoryCreate,
    MenuCategoryResponse,
    MenuCategoryUpdate,
    MenuItemCreate,
    MenuItemResponse,
    MenuItemUpdate,
    ModifierGroupCreate,
    ModifierGroupResponse,
    ModifierGroupUpdate,
)

router = APIRouter()


# ---- Categories ----

@router.get("/categories", response_model=list[MenuCategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(MenuCategory)
        .where(MenuCategory.outlet_id == current_user.outlet_id)
        .order_by(MenuCategory.sort_order)
    )
    return result.scalars().all()


@router.post("/categories", response_model=MenuCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: MenuCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    category = MenuCategory(outlet_id=current_user.outlet_id, **body.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


@router.put("/categories/{category_id}", response_model=MenuCategoryResponse)
async def update_category(
    category_id: UUID,
    body: MenuCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(MenuCategory).where(
            MenuCategory.id == category_id,
            MenuCategory.outlet_id == current_user.outlet_id,
        )
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.flush()
    await db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(MenuCategory).where(
            MenuCategory.id == category_id,
            MenuCategory.outlet_id == current_user.outlet_id,
        )
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    await db.delete(category)


# ---- Menu Items ----

@router.get("/items", response_model=list[MenuItemResponse])
async def list_items(
    category_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    query = select(MenuItem).where(
        MenuItem.outlet_id == current_user.outlet_id,
        MenuItem.is_active == True,
    )
    if category_id:
        query = query.where(MenuItem.category_id == category_id)
    query = query.order_by(MenuItem.sort_order)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: MenuItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    item = MenuItem(outlet_id=current_user.outlet_id, **body.model_dump())
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.get("/items/{item_id}", response_model=MenuItemResponse)
async def get_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.outlet_id == current_user.outlet_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    return item


@router.put("/items/{item_id}", response_model=MenuItemResponse)
async def update_item(
    item_id: UUID,
    body: MenuItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.outlet_id == current_user.outlet_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.outlet_id == current_user.outlet_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    item.is_active = False
    await db.flush()


@router.put("/items/{item_id}/availability", response_model=MenuItemResponse)
async def toggle_availability(
    item_id: UUID,
    body: AvailabilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager", "cashier")),
):
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id == item_id,
            MenuItem.outlet_id == current_user.outlet_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    item.is_available = body.is_available
    await db.flush()
    await db.refresh(item)
    return item


# ---- Modifier Groups ----

@router.get("/modifiers", response_model=list[ModifierGroupResponse])
async def list_modifiers(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(ModifierGroup)
        .where(ModifierGroup.outlet_id == current_user.outlet_id)
        .options(selectinload(ModifierGroup.options))
        .order_by(ModifierGroup.sort_order)
    )
    return result.scalars().unique().all()


@router.post("/modifiers", response_model=ModifierGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_modifier(
    body: ModifierGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    group = ModifierGroup(
        outlet_id=current_user.outlet_id,
        name=body.name,
        selection_type=body.selection_type,
        min_selections=body.min_selections,
        max_selections=body.max_selections,
        is_required=body.is_required,
        sort_order=body.sort_order,
    )
    db.add(group)
    await db.flush()

    for opt in body.options:
        option = ModifierOption(group_id=group.id, **opt.model_dump())
        db.add(option)

    for item_id in body.menu_item_ids:
        link = MenuItemModifierGroup(menu_item_id=item_id, modifier_group_id=group.id)
        db.add(link)

    await db.flush()
    result = await db.execute(
        select(ModifierGroup)
        .where(ModifierGroup.id == group.id)
        .options(selectinload(ModifierGroup.options))
    )
    return result.scalar_one()


@router.put("/modifiers/{group_id}", response_model=ModifierGroupResponse)
async def update_modifier(
    group_id: UUID,
    body: ModifierGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(ModifierGroup)
        .where(
            ModifierGroup.id == group_id,
            ModifierGroup.outlet_id == current_user.outlet_id,
        )
        .options(selectinload(ModifierGroup.options))
    )
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modifier group not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    await db.flush()
    await db.refresh(group)
    return group


# ---- Combo Meals ----

@router.get("/combos", response_model=list[ComboMealResponse])
async def list_combos(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(ComboMeal)
        .where(ComboMeal.outlet_id == current_user.outlet_id, ComboMeal.is_active == True)
        .options(selectinload(ComboMeal.items))
    )
    return result.scalars().unique().all()


@router.post("/combos", response_model=ComboMealResponse, status_code=status.HTTP_201_CREATED)
async def create_combo(
    body: ComboMealCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    combo = ComboMeal(
        outlet_id=current_user.outlet_id,
        name=body.name,
        description=body.description,
        price=body.price,
        image_url=body.image_url,
    )
    db.add(combo)
    await db.flush()

    for ci in body.items:
        combo_item = ComboItem(combo_id=combo.id, **ci.model_dump())
        db.add(combo_item)

    await db.flush()
    result = await db.execute(
        select(ComboMeal)
        .where(ComboMeal.id == combo.id)
        .options(selectinload(ComboMeal.items))
    )
    return result.scalar_one()


@router.put("/combos/{combo_id}", response_model=ComboMealResponse)
async def update_combo(
    combo_id: UUID,
    body: ComboMealUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(ComboMeal)
        .where(
            ComboMeal.id == combo_id,
            ComboMeal.outlet_id == current_user.outlet_id,
        )
        .options(selectinload(ComboMeal.items))
    )
    combo = result.scalar_one_or_none()
    if combo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Combo not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(combo, field, value)
    await db.flush()
    await db.refresh(combo)
    return combo


# ---- Full Menu Tree ----

@router.get("/full")
async def full_menu(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    cat_result = await db.execute(
        select(MenuCategory)
        .where(MenuCategory.outlet_id == current_user.outlet_id, MenuCategory.is_active == True)
        .order_by(MenuCategory.sort_order)
    )
    categories = cat_result.scalars().all()

    items_result = await db.execute(
        select(MenuItem)
        .where(MenuItem.outlet_id == current_user.outlet_id, MenuItem.is_active == True)
        .options(selectinload(MenuItem.modifier_groups).selectinload(ModifierGroup.options))
        .order_by(MenuItem.sort_order)
    )
    items = items_result.scalars().unique().all()

    items_by_cat: dict[str | None, list] = {}
    for item in items:
        key = str(item.category_id) if item.category_id else None
        items_by_cat.setdefault(key, []).append(item)

    tree = []
    for cat in categories:
        cat_items = items_by_cat.get(str(cat.id), [])
        tree.append({
            "id": str(cat.id),
            "name": cat.name,
            "description": cat.description,
            "image_url": cat.image_url,
            "sort_order": cat.sort_order,
            "items": [
                {
                    "id": str(i.id),
                    "name": i.name,
                    "description": i.description,
                    "price": float(i.price),
                    "image_url": i.image_url,
                    "is_available": i.is_available,
                    "allergens": i.allergens,
                    "tags": i.tags,
                    "modifiers": [
                        {
                            "id": str(mg.id),
                            "name": mg.name,
                            "selection_type": mg.selection_type,
                            "min_selections": mg.min_selections,
                            "max_selections": mg.max_selections,
                            "is_required": mg.is_required,
                            "options": [
                                {
                                    "id": str(o.id),
                                    "name": o.name,
                                    "price_adjustment": float(o.price_adjustment),
                                }
                                for o in mg.options
                            ],
                        }
                        for mg in i.modifier_groups
                    ],
                }
                for i in cat_items
            ],
        })
    return tree
