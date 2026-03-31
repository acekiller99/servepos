from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.delivery import DeliveryOrder, DeliveryPlatform
from app.models.staff import Staff
from app.schemas.delivery import (
    DeliveryOrderReject,
    DeliveryOrderResponse,
    DeliveryOrderStatusUpdate,
    DeliveryPlatformCreate,
    DeliveryPlatformResponse,
    DeliveryPlatformUpdate,
)

router = APIRouter()


# ---- Delivery Platforms ----

@router.get("/platforms", response_model=list[DeliveryPlatformResponse])
async def list_platforms(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryPlatform).where(DeliveryPlatform.outlet_id == current_user.outlet_id)
    )
    return result.scalars().all()


@router.post("/platforms", response_model=DeliveryPlatformResponse, status_code=status.HTTP_201_CREATED)
async def add_platform(
    body: DeliveryPlatformCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    platform = DeliveryPlatform(outlet_id=current_user.outlet_id, **body.model_dump())
    db.add(platform)
    await db.flush()
    await db.refresh(platform)
    return platform


@router.put("/platforms/{platform_id}", response_model=DeliveryPlatformResponse)
async def update_platform(
    platform_id: UUID,
    body: DeliveryPlatformUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(DeliveryPlatform).where(
            DeliveryPlatform.id == platform_id,
            DeliveryPlatform.outlet_id == current_user.outlet_id,
        )
    )
    platform = result.scalar_one_or_none()
    if platform is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(platform, field, value)
    await db.flush()
    await db.refresh(platform)
    return platform


@router.delete("/platforms/{platform_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_platform(
    platform_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(DeliveryPlatform).where(
            DeliveryPlatform.id == platform_id,
            DeliveryPlatform.outlet_id == current_user.outlet_id,
        )
    )
    platform = result.scalar_one_or_none()
    if platform is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform not found")
    await db.delete(platform)


@router.post("/platforms/{platform_id}/test")
async def test_platform(
    platform_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(DeliveryPlatform).where(
            DeliveryPlatform.id == platform_id,
            DeliveryPlatform.outlet_id == current_user.outlet_id,
        )
    )
    platform = result.scalar_one_or_none()
    if platform is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform not found")

    return {
        "platform": platform.platform_name,
        "status": "ok",
        "message": f"Connection test for {platform.display_name} successful (simulated)",
    }


# ---- Delivery Orders ----

@router.get("/orders", response_model=list[DeliveryOrderResponse])
async def list_delivery_orders(
    platform_name: str | None = None,
    order_status: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    query = (
        select(DeliveryOrder)
        .join(DeliveryPlatform, isouter=True)
        .where(DeliveryPlatform.outlet_id == current_user.outlet_id)
        .order_by(DeliveryOrder.created_at.desc())
    )
    if platform_name:
        query = query.where(DeliveryPlatform.platform_name == platform_name)
    if order_status:
        query = query.where(DeliveryOrder.platform_status == order_status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/orders/pending", response_model=list[DeliveryOrderResponse])
async def pending_delivery_orders(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryOrder)
        .join(DeliveryPlatform, isouter=True)
        .where(
            DeliveryPlatform.outlet_id == current_user.outlet_id,
            DeliveryOrder.is_accepted == False,
            DeliveryOrder.platform_status == "new",
        )
        .order_by(DeliveryOrder.created_at)
    )
    return result.scalars().all()


@router.get("/orders/active", response_model=list[DeliveryOrderResponse])
async def active_delivery_orders(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryOrder)
        .join(DeliveryPlatform, isouter=True)
        .where(
            DeliveryPlatform.outlet_id == current_user.outlet_id,
            DeliveryOrder.is_accepted == True,
            DeliveryOrder.platform_status.in_(["accepted", "preparing", "ready_for_pickup"]),
        )
        .order_by(DeliveryOrder.created_at)
    )
    return result.scalars().all()


@router.get("/orders/{delivery_order_id}", response_model=DeliveryOrderResponse)
async def get_delivery_order(
    delivery_order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryOrder).where(DeliveryOrder.id == delivery_order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery order not found")
    return order


@router.post("/orders/{delivery_order_id}/accept", response_model=DeliveryOrderResponse)
async def accept_delivery_order(
    delivery_order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryOrder).where(DeliveryOrder.id == delivery_order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery order not found")

    order.is_accepted = True
    order.accepted_at = datetime.now(timezone.utc)
    order.platform_status = "accepted"
    await db.flush()
    await db.refresh(order)
    return order


@router.post("/orders/{delivery_order_id}/reject", response_model=DeliveryOrderResponse)
async def reject_delivery_order(
    delivery_order_id: UUID,
    body: DeliveryOrderReject,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryOrder).where(DeliveryOrder.id == delivery_order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery order not found")

    order.platform_status = "cancelled"
    order.rejected_reason = body.reason
    await db.flush()
    await db.refresh(order)
    return order


@router.put("/orders/{delivery_order_id}/status", response_model=DeliveryOrderResponse)
async def update_delivery_status(
    delivery_order_id: UUID,
    body: DeliveryOrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryOrder).where(DeliveryOrder.id == delivery_order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery order not found")

    order.platform_status = body.status
    await db.flush()
    await db.refresh(order)
    return order


@router.post("/orders/{delivery_order_id}/ready", response_model=DeliveryOrderResponse)
async def mark_ready(
    delivery_order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(DeliveryOrder).where(DeliveryOrder.id == delivery_order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery order not found")

    order.platform_status = "ready_for_pickup"
    await db.flush()
    await db.refresh(order)
    return order


# ---- Webhook Receivers ----

@router.post("/webhook/foodpanda")
async def foodpanda_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    """Receive order webhook from FoodPanda."""
    # In production, verify webhook signature
    return await _process_delivery_webhook("foodpanda", payload, db)


@router.post("/webhook/grabfood")
async def grabfood_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    """Receive order webhook from GrabFood."""
    return await _process_delivery_webhook("grabfood", payload, db)


@router.post("/webhook/shopeefood")
async def shopeefood_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    """Receive order webhook from ShopeeFood."""
    return await _process_delivery_webhook("shopeefood", payload, db)


@router.post("/webhook/generic")
async def generic_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    """Receive order webhook from a generic delivery platform."""
    platform_name = payload.get("platform", "generic")
    return await _process_delivery_webhook(platform_name, payload, db)


async def _process_delivery_webhook(platform_name: str, payload: dict, db: AsyncSession):
    """Common logic for processing incoming delivery order webhooks."""
    from app.models.order import Order

    platform_order_id = payload.get("order_id", payload.get("id", ""))
    if not platform_order_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing order_id")

    # Find the platform config
    platform_result = await db.execute(
        select(DeliveryPlatform).where(DeliveryPlatform.platform_name == platform_name)
    )
    platform = platform_result.scalar_one_or_none()

    # Create internal order
    order = Order(
        outlet_id=platform.outlet_id if platform else None,
        order_number=f"D-{platform_order_id[:8]}",
        order_type="delivery",
        customer_name=payload.get("customer_name"),
        customer_phone=payload.get("customer_phone"),
        subtotal=payload.get("subtotal", 0),
        total=payload.get("total", 0),
        status="pending",
    )
    db.add(order)
    await db.flush()

    # Create delivery order record
    delivery_order = DeliveryOrder(
        order_id=order.id,
        platform_id=platform.id if platform else None,
        platform_order_id=str(platform_order_id),
        platform_order_number=payload.get("order_number"),
        platform_status="new",
        customer_name=payload.get("customer_name"),
        customer_phone=payload.get("customer_phone"),
        customer_address=payload.get("delivery_address"),
        delivery_notes=payload.get("notes"),
        rider_name=payload.get("rider_name"),
        rider_phone=payload.get("rider_phone"),
        platform_subtotal=payload.get("subtotal"),
        platform_commission=payload.get("commission"),
        platform_delivery_fee=payload.get("delivery_fee"),
        raw_payload=payload,
    )

    # Calculate net amount
    if delivery_order.platform_subtotal and delivery_order.platform_commission:
        delivery_order.net_amount = float(delivery_order.platform_subtotal) - float(delivery_order.platform_commission)

    # Auto-accept if configured
    if platform and platform.auto_accept:
        delivery_order.is_accepted = True
        delivery_order.accepted_at = datetime.now(timezone.utc)
        delivery_order.platform_status = "accepted"

    db.add(delivery_order)
    await db.flush()

    return {"status": "ok", "delivery_order_id": str(delivery_order.id)}
