from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.order import Order
from app.models.payment import Payment
from app.models.register import RegisterSession
from app.models.staff import Staff
from app.schemas.payment import RegisterCloseRequest, RegisterOpenRequest, RegisterSessionResponse

router = APIRouter()


@router.post("/open", response_model=RegisterSessionResponse, status_code=status.HTTP_201_CREATED)
async def open_register(
    body: RegisterOpenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager", "cashier")),
):
    # Check if there's already an open session
    existing = await db.execute(
        select(RegisterSession).where(
            RegisterSession.outlet_id == current_user.outlet_id,
            RegisterSession.status == "open",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Register already open")

    session = RegisterSession(
        outlet_id=current_user.outlet_id,
        opened_by=current_user.id,
        opening_cash=body.opening_cash,
        notes=body.notes,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.post("/close", response_model=RegisterSessionResponse)
async def close_register(
    body: RegisterCloseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager", "cashier")),
):
    result = await db.execute(
        select(RegisterSession).where(
            RegisterSession.outlet_id == current_user.outlet_id,
            RegisterSession.status == "open",
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No open register session")

    # Calculate totals from orders during this session
    sales_result = await db.execute(
        select(func.coalesce(func.sum(Order.total), 0))
        .where(
            Order.outlet_id == current_user.outlet_id,
            Order.created_at >= session.opened_at,
            Order.is_void == False,
            Order.payment_status == "paid",
        )
    )
    total_sales = float(sales_result.scalar())

    # Calculate cash payments during session
    cash_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Order)
        .where(
            Order.outlet_id == current_user.outlet_id,
            Payment.payment_method == "cash",
            Payment.status == "completed",
            Payment.created_at >= session.opened_at,
        )
    )
    cash_payments = float(cash_result.scalar())

    # Calculate refunds
    refund_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Order)
        .where(
            Order.outlet_id == current_user.outlet_id,
            Payment.status == "refunded",
            Payment.created_at >= session.opened_at,
        )
    )
    total_refunds = float(refund_result.scalar())

    # Calculate discounts
    discount_result = await db.execute(
        select(func.coalesce(func.sum(Order.discount_amount), 0))
        .where(
            Order.outlet_id == current_user.outlet_id,
            Order.created_at >= session.opened_at,
        )
    )
    total_discounts = float(discount_result.scalar())

    expected_cash = float(session.opening_cash) + cash_payments - total_refunds
    cash_difference = body.closing_cash - expected_cash

    session.closed_by = current_user.id
    session.closing_cash = body.closing_cash
    session.expected_cash = expected_cash
    session.cash_difference = cash_difference
    session.total_sales = total_sales
    session.total_refunds = total_refunds
    session.total_discounts = total_discounts
    session.closed_at = datetime.now(timezone.utc)
    session.status = "closed"
    if body.notes:
        session.notes = (session.notes or "") + "\n" + body.notes

    await db.flush()
    await db.refresh(session)
    return session


@router.get("/current", response_model=RegisterSessionResponse)
async def current_register(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(RegisterSession).where(
            RegisterSession.outlet_id == current_user.outlet_id,
            RegisterSession.status == "open",
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No open register session")
    return session


@router.get("/history", response_model=list[RegisterSessionResponse])
async def register_history(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(RegisterSession)
        .where(RegisterSession.outlet_id == current_user.outlet_id)
        .order_by(RegisterSession.opened_at.desc())
    )
    return result.scalars().all()
