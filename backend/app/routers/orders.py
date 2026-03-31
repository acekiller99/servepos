from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, cast, func, select, Date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.order import Order, OrderItem
from app.models.outlet import Outlet
from app.models.staff import Staff
from app.models.table import Table
from app.schemas.order import (
    OrderCreate,
    OrderDiscount,
    OrderItemCreate,
    OrderItemResponse,
    OrderItemUpdate,
    OrderResponse,
    OrderStatusUpdate,
    OrderUpdate,
    OrderVoid,
)

router = APIRouter()


async def _calc_order_totals(order: Order, outlet: Outlet):
    """Recalculate order subtotal, tax, service charge, and total."""
    subtotal = Decimal("0")
    for item in order.items:
        if not item.is_void:
            subtotal += Decimal(str(item.subtotal))
    order.subtotal = float(subtotal)
    order.tax_amount = float(subtotal * Decimal(str(outlet.tax_rate)) / Decimal("100"))
    order.service_charge = float(subtotal * Decimal(str(outlet.service_charge_rate)) / Decimal("100"))
    order.total = float(
        subtotal
        + Decimal(str(order.tax_amount))
        + Decimal(str(order.service_charge))
        - Decimal(str(order.discount_amount))
    )


async def _next_order_number(db: AsyncSession, outlet_id: UUID) -> str:
    """Generate next sequential order number for today."""
    today = date.today()
    result = await db.execute(
        select(func.count())
        .select_from(Order)
        .where(
            Order.outlet_id == outlet_id,
            cast(Order.created_at, Date) == today,
        )
    )
    count = result.scalar() or 0
    return f"#{count + 1:03d}"


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    outlet_result = await db.execute(select(Outlet).where(Outlet.id == current_user.outlet_id))
    outlet = outlet_result.scalar_one()

    order_number = await _next_order_number(db, current_user.outlet_id)

    order = Order(
        outlet_id=current_user.outlet_id,
        order_number=order_number,
        order_type=body.order_type,
        table_id=body.table_id,
        staff_id=current_user.id,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        customer_notes=body.customer_notes,
        guest_count=body.guest_count,
    )
    db.add(order)
    await db.flush()

    for item_data in body.items:
        item_subtotal = float(Decimal(str(item_data.unit_price)) * item_data.quantity)
        # Add modifier price adjustments
        for mod in item_data.modifiers:
            item_subtotal += float(Decimal(str(mod.get("price_adjustment", 0))) * item_data.quantity)
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            item_name=item_data.item_name,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            modifiers=item_data.modifiers,
            subtotal=item_subtotal,
            notes=item_data.notes,
        )
        db.add(order_item)

    await db.flush()

    # Reload with items
    result = await db.execute(
        select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    )
    order = result.scalar_one()
    await _calc_order_totals(order, outlet)
    await db.flush()

    # Update table status if dine-in
    if body.table_id and body.order_type == "dine_in":
        table_result = await db.execute(select(Table).where(Table.id == body.table_id))
        table = table_result.scalar_one_or_none()
        if table:
            table.status = "occupied"
            table.current_order_id = order.id

    await db.flush()
    result = await db.execute(
        select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    )
    return result.scalar_one()


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    status_filter: str | None = Query(None, alias="status"),
    order_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    query = (
        select(Order)
        .where(Order.outlet_id == current_user.outlet_id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
    if status_filter:
        query = query.where(Order.status == status_filter)
    if order_type:
        query = query.where(Order.order_type == order_type)
    if date_from:
        query = query.where(cast(Order.created_at, Date) >= date_from)
    if date_to:
        query = query.where(cast(Order.created_at, Date) <= date_to)

    result = await db.execute(query)
    return result.scalars().unique().all()


@router.get("/active", response_model=list[OrderResponse])
async def active_orders(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Order)
        .where(
            Order.outlet_id == current_user.outlet_id,
            Order.status.in_(["pending", "confirmed", "preparing", "ready"]),
            Order.is_void == False,
        )
        .options(selectinload(Order.items))
        .order_by(Order.created_at)
    )
    return result.scalars().unique().all()


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.outlet_id == current_user.outlet_id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: UUID,
    body: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.outlet_id == current_user.outlet_id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    await db.flush()
    result = await db.execute(
        select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    )
    return result.scalar_one()


@router.post("/{order_id}/items", response_model=OrderResponse)
async def add_items(
    order_id: UUID,
    items: list[OrderItemCreate],
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.outlet_id == current_user.outlet_id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    outlet_result = await db.execute(select(Outlet).where(Outlet.id == current_user.outlet_id))
    outlet = outlet_result.scalar_one()

    for item_data in items:
        item_subtotal = float(Decimal(str(item_data.unit_price)) * item_data.quantity)
        for mod in item_data.modifiers:
            item_subtotal += float(Decimal(str(mod.get("price_adjustment", 0))) * item_data.quantity)
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            item_name=item_data.item_name,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            modifiers=item_data.modifiers,
            subtotal=item_subtotal,
            notes=item_data.notes,
        )
        order.items.append(order_item)

    await db.flush()
    await _calc_order_totals(order, outlet)
    await db.flush()
    # Re-fetch with all attributes loaded to avoid lazy-load issues in response serialization
    result2 = await db.execute(
        select(Order).where(Order.id == order.id).options(selectinload(Order.items))
        .execution_options(populate_existing=True)
    )
    return result2.scalar_one()


@router.put("/{order_id}/items/{item_id}", response_model=OrderItemResponse)
async def update_order_item(
    order_id: UUID,
    item_id: UUID,
    body: OrderItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    # Recalculate item subtotal
    if "quantity" in update_data or "modifiers" in update_data:
        item_subtotal = float(Decimal(str(item.unit_price)) * item.quantity)
        for mod in (item.modifiers or []):
            item_subtotal += float(Decimal(str(mod.get("price_adjustment", 0))) * item.quantity)
        item.subtotal = item_subtotal

    await db.flush()
    await db.refresh(item)

    # Recalculate order totals
    order_result = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    )
    order = order_result.scalar_one()
    outlet_result = await db.execute(select(Outlet).where(Outlet.id == order.outlet_id))
    outlet = outlet_result.scalar_one()
    await _calc_order_totals(order, outlet)
    await db.flush()

    return item


@router.delete("/{order_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_order_item(
    order_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
    item.is_void = True
    await db.flush()

    # Recalculate order totals
    order_result = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    )
    order = order_result.scalar_one()
    outlet_result = await db.execute(select(Outlet).where(Outlet.id == order.outlet_id))
    outlet = outlet_result.scalar_one()
    await _calc_order_totals(order, outlet)
    await db.flush()


@router.post("/{order_id}/send-to-kitchen", response_model=OrderResponse)
async def send_to_kitchen(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.outlet_id == current_user.outlet_id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    now = datetime.now(timezone.utc)
    for item in order.items:
        if not item.sent_to_kitchen and not item.is_void:
            item.sent_to_kitchen = True
            item.kitchen_sent_at = now
            item.status = "preparing"

    if order.status == "pending":
        order.status = "confirmed"

    await db.flush()
    result = await db.execute(
        select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    )
    return result.scalar_one()


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    body: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.outlet_id == current_user.outlet_id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order.status = body.status
    if body.status == "completed":
        order.completed_at = datetime.now(timezone.utc)
        # Free up the table
        if order.table_id:
            table_result = await db.execute(select(Table).where(Table.id == order.table_id))
            table = table_result.scalar_one_or_none()
            if table:
                table.status = "available"
                table.current_order_id = None

    await db.flush()
    result = await db.execute(
        select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    )
    return result.scalar_one()


@router.post("/{order_id}/void", response_model=OrderResponse)
async def void_order(
    order_id: UUID,
    body: OrderVoid,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.outlet_id == current_user.outlet_id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order.is_void = True
    order.void_reason = body.void_reason
    order.voided_by = current_user.id
    order.status = "cancelled"

    # Free up the table
    if order.table_id:
        table_result = await db.execute(select(Table).where(Table.id == order.table_id))
        table = table_result.scalar_one_or_none()
        if table and table.current_order_id == order.id:
            table.status = "available"
            table.current_order_id = None

    await db.flush()
    result = await db.execute(
        select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    )
    return result.scalar_one()


@router.post("/{order_id}/discount", response_model=OrderResponse)
async def apply_discount(
    order_id: UUID,
    body: OrderDiscount,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager", "cashier")),
):
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.outlet_id == current_user.outlet_id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    outlet_result = await db.execute(select(Outlet).where(Outlet.id == current_user.outlet_id))
    outlet = outlet_result.scalar_one()

    order.discount_amount = body.discount_amount
    order.discount_reason = body.discount_reason
    await _calc_order_totals(order, outlet)
    await db.flush()
    result = await db.execute(
        select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    )
    return result.scalar_one()


@router.post("/sync", response_model=list[OrderResponse])
async def sync_offline_orders(
    orders: list[OrderCreate],
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Bulk create orders synced from offline mode."""
    outlet_result = await db.execute(select(Outlet).where(Outlet.id == current_user.outlet_id))
    outlet = outlet_result.scalar_one()

    created_orders = []
    for order_data in orders:
        order_number = await _next_order_number(db, current_user.outlet_id)
        order = Order(
            outlet_id=current_user.outlet_id,
            order_number=order_number,
            order_type=order_data.order_type,
            table_id=order_data.table_id,
            staff_id=current_user.id,
            customer_name=order_data.customer_name,
            customer_phone=order_data.customer_phone,
            customer_notes=order_data.customer_notes,
            guest_count=order_data.guest_count,
        )
        db.add(order)
        await db.flush()

        for item_data in order_data.items:
            item_subtotal = float(Decimal(str(item_data.unit_price)) * item_data.quantity)
            for mod in item_data.modifiers:
                item_subtotal += float(Decimal(str(mod.get("price_adjustment", 0))) * item_data.quantity)
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item_data.menu_item_id,
                item_name=item_data.item_name,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                modifiers=item_data.modifiers,
                subtotal=item_subtotal,
                notes=item_data.notes,
            )
            db.add(order_item)

        await db.flush()
        result = await db.execute(
            select(Order).where(Order.id == order.id).options(selectinload(Order.items))
        )
        order = result.scalar_one()
        await _calc_order_totals(order, outlet)
        created_orders.append(order)

    await db.flush()
    # Re-fetch all orders with items to avoid lazy-load issues
    order_ids = [o.id for o in created_orders]
    result = await db.execute(
        select(Order).where(Order.id.in_(order_ids)).options(selectinload(Order.items))
        .execution_options(populate_existing=True)
    )
    return result.scalars().all()
