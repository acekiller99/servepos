from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.inventory import InventoryItem, InventoryTransaction
from app.models.staff import Staff
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdate,
    InventoryTransactionResponse,
    RestockRequest,
    WasteRequest,
)

router = APIRouter()


@router.get("", response_model=list[InventoryItemResponse])
async def list_inventory(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(InventoryItem)
        .where(InventoryItem.outlet_id == current_user.outlet_id, InventoryItem.is_active == True)
        .order_by(InventoryItem.name)
    )
    return result.scalars().all()


@router.post("", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    body: InventoryItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    item = InventoryItem(outlet_id=current_user.outlet_id, **body.model_dump())
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.get("/low-stock", response_model=list[InventoryItemResponse])
async def low_stock(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.outlet_id == current_user.outlet_id,
            InventoryItem.is_active == True,
            InventoryItem.quantity <= InventoryItem.min_quantity,
        )
    )
    return result.scalars().all()


@router.put("/{item_id}", response_model=InventoryItemResponse)
async def update_inventory_item(
    item_id: UUID,
    body: InventoryItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == item_id,
            InventoryItem.outlet_id == current_user.outlet_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.flush()
    await db.refresh(item)
    return item


@router.post("/{item_id}/restock", response_model=InventoryItemResponse)
async def restock(
    item_id: UUID,
    body: RestockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == item_id,
            InventoryItem.outlet_id == current_user.outlet_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")

    item.quantity = float(item.quantity) + body.quantity
    item.last_restocked_at = datetime.now(timezone.utc)
    if body.cost_per_unit is not None:
        item.cost_per_unit = body.cost_per_unit

    txn = InventoryTransaction(
        inventory_item_id=item.id,
        transaction_type="restock",
        quantity_change=body.quantity,
        notes=body.notes,
        performed_by=current_user.id,
    )
    db.add(txn)
    await db.flush()
    await db.refresh(item)
    return item


@router.get("/{item_id}/transactions", response_model=list[InventoryTransactionResponse])
async def transaction_history(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(InventoryTransaction)
        .where(InventoryTransaction.inventory_item_id == item_id)
        .order_by(InventoryTransaction.created_at.desc())
    )
    return result.scalars().all()


@router.post("/waste")
async def record_waste(
    body: WasteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(InventoryItem).where(
            InventoryItem.id == body.inventory_item_id,
            InventoryItem.outlet_id == current_user.outlet_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")

    item.quantity = max(0, float(item.quantity) - body.quantity)

    txn = InventoryTransaction(
        inventory_item_id=item.id,
        transaction_type="waste",
        quantity_change=-body.quantity,
        notes=body.notes,
        performed_by=current_user.id,
    )
    db.add(txn)
    await db.flush()
    return {"status": "ok", "remaining_quantity": float(item.quantity)}
