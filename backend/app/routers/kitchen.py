from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.order import Order, OrderItem
from app.models.staff import Staff

router = APIRouter()


# ---- WebSocket connection manager for KDS ----
class KDSConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


kds_manager = KDSConnectionManager()


# ---- REST endpoints ----

@router.get("/orders")
async def kitchen_orders(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Order)
        .where(
            Order.outlet_id == current_user.outlet_id,
            Order.status.in_(["confirmed", "preparing"]),
            Order.is_void == False,
        )
        .options(selectinload(Order.items))
        .order_by(Order.created_at)
    )
    orders = result.scalars().unique().all()
    return [
        {
            "id": str(o.id),
            "order_number": o.order_number,
            "order_type": o.order_type,
            "table_id": str(o.table_id) if o.table_id else None,
            "status": o.status,
            "created_at": o.created_at.isoformat(),
            "items": [
                {
                    "id": str(item.id),
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "modifiers": item.modifiers,
                    "notes": item.notes,
                    "status": item.status,
                    "sent_to_kitchen": item.sent_to_kitchen,
                    "kitchen_sent_at": item.kitchen_sent_at.isoformat() if item.kitchen_sent_at else None,
                }
                for item in o.items
                if item.sent_to_kitchen and not item.is_void
            ],
        }
        for o in orders
    ]


@router.put("/items/{item_id}/status")
async def update_kitchen_item_status(
    item_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(select(OrderItem).where(OrderItem.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")

    new_status = body.get("status")
    if new_status not in ("preparing", "ready", "served"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    item.status = new_status
    if new_status == "ready":
        item.prepared_at = datetime.now(timezone.utc)

    await db.flush()

    await kds_manager.broadcast({
        "type": "item_status_update",
        "item_id": str(item.id),
        "order_id": str(item.order_id),
        "status": new_status,
    })

    return {"status": "ok", "item_id": str(item.id), "new_status": new_status}


@router.post("/items/{item_id}/bump")
async def bump_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(select(OrderItem).where(OrderItem.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")

    item.status = "ready"
    item.prepared_at = datetime.now(timezone.utc)
    await db.flush()

    # Check if all items in order are ready
    order_result = await db.execute(
        select(Order).where(Order.id == item.order_id).options(selectinload(Order.items))
    )
    order = order_result.scalar_one()
    all_ready = all(
        i.status in ("ready", "served") or i.is_void
        for i in order.items
        if i.sent_to_kitchen
    )
    if all_ready:
        order.status = "ready"

    await db.flush()

    await kds_manager.broadcast({
        "type": "item_bumped",
        "item_id": str(item.id),
        "order_id": str(item.order_id),
        "order_ready": all_ready,
    })

    return {"status": "ok", "item_id": str(item.id), "order_ready": all_ready}


@router.get("/stats")
async def kitchen_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    from sqlalchemy import func, extract

    # Pending items count
    pending_result = await db.execute(
        select(func.count())
        .select_from(OrderItem)
        .join(Order)
        .where(
            Order.outlet_id == current_user.outlet_id,
            OrderItem.sent_to_kitchen == True,
            OrderItem.status == "preparing",
            OrderItem.is_void == False,
        )
    )
    pending_count = pending_result.scalar() or 0

    # Average prep time (items completed today)
    from datetime import date
    from sqlalchemy import cast, Date

    avg_result = await db.execute(
        select(
            func.avg(
                extract("epoch", OrderItem.prepared_at) - extract("epoch", OrderItem.kitchen_sent_at)
            )
        )
        .join(Order)
        .where(
            Order.outlet_id == current_user.outlet_id,
            OrderItem.prepared_at.isnot(None),
            OrderItem.kitchen_sent_at.isnot(None),
            cast(OrderItem.prepared_at, Date) == date.today(),
        )
    )
    avg_prep_seconds = avg_result.scalar()

    return {
        "pending_items": pending_count,
        "avg_prep_time_seconds": round(avg_prep_seconds, 1) if avg_prep_seconds else None,
    }


# ---- WebSocket ----

@router.websocket("/ws")
async def kitchen_ws(websocket: WebSocket):
    await kds_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Clients can send pings or commands
    except WebSocketDisconnect:
        kds_manager.disconnect(websocket)
