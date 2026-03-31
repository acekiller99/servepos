import base64
import io
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.order import Order
from app.models.payment import Payment
from app.models.staff import Staff
from app.schemas.payment import (
    PaymentCreate,
    PaymentRefund,
    PaymentResponse,
    QRGenerateRequest,
    QRGenerateResponse,
    QRScanRequest,
    QRStatusResponse,
)

router = APIRouter()


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def process_payment(
    body: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    order_result = await db.execute(select(Order).where(Order.id == body.order_id))
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    change_amount = 0.0
    pay_status = "completed"

    if body.payment_method == "cash":
        if body.amount > float(order.total):
            change_amount = body.amount - float(order.total)

    # For e-wallet, initial status is pending (QR flow)
    ewallet_methods = {"alipay", "touch_n_go", "grabpay", "boost", "wechat_pay", "shopeepay", "qr_generic"}
    if body.payment_method in ewallet_methods:
        pay_status = "pending"

    payment = Payment(
        order_id=body.order_id,
        payment_method=body.payment_method,
        amount=body.amount,
        tip_amount=body.tip_amount,
        reference_number=body.reference_number,
        change_amount=change_amount,
        status=pay_status,
        processed_by=current_user.id,
        notes=body.notes,
    )
    if pay_status == "completed":
        payment.completed_at = datetime.now(timezone.utc)

    db.add(payment)
    await db.flush()

    # Update order payment status
    await _update_order_payment_status(db, order)
    await db.refresh(payment)
    return payment


async def _update_order_payment_status(db: AsyncSession, order: Order):
    """Check all payments for an order and update payment_status."""
    payments_result = await db.execute(
        select(Payment).where(Payment.order_id == order.id, Payment.status == "completed")
    )
    payments = payments_result.scalars().all()
    total_paid = sum(float(p.amount) for p in payments)

    if total_paid >= float(order.total):
        order.payment_status = "paid"
    elif total_paid > 0:
        order.payment_status = "partial"
    else:
        order.payment_status = "unpaid"
    await db.flush()


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(
    payment_id: UUID,
    body: PaymentRefund,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment not completed")

    payment.status = "refunded"
    payment.notes = (payment.notes or "") + f"\nRefund: {body.reason or 'No reason'}"
    await db.flush()

    # Update order payment status
    order_result = await db.execute(select(Order).where(Order.id == payment.order_id))
    order = order_result.scalar_one()
    await _update_order_payment_status(db, order)

    await db.refresh(payment)
    return payment


@router.post("/qr/generate", response_model=QRGenerateResponse)
async def generate_qr(
    body: QRGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    order_result = await db.execute(select(Order).where(Order.id == body.order_id))
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    # Generate QR payload (in production, this would integrate with actual e-wallet APIs)
    qr_data = f"servepos://pay/{body.order_id}/{body.provider}/{body.amount}"

    # Generate QR image as base64
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    payment = Payment(
        order_id=body.order_id,
        payment_method=body.provider,
        amount=body.amount,
        status="pending",
        qr_code_data=qr_data,
        expires_at=expires_at,
        processed_by=current_user.id,
    )
    db.add(payment)
    await db.flush()
    await db.refresh(payment)

    return QRGenerateResponse(
        qr_code_base64=qr_base64,
        qr_url=None,
        payment_id=payment.id,
        expires_at=expires_at,
    )


@router.get("/qr/{payment_id}/status", response_model=QRStatusResponse)
async def qr_payment_status(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    # Check expiry
    if payment.expires_at and payment.status == "pending":
        expires = payment.expires_at if payment.expires_at.tzinfo else payment.expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            payment.status = "expired"
            await db.flush()

    return QRStatusResponse(
        status=payment.status,
        transaction_id=payment.ewallet_transaction_id,
    )


@router.post("/qr/callback")
async def qr_callback(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Webhook callback from e-wallet provider to confirm payment."""
    payment_id = payload.get("payment_id")
    transaction_id = payload.get("transaction_id")
    callback_status = payload.get("status")

    if not payment_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing payment_id")

    result = await db.execute(select(Payment).where(Payment.id == UUID(payment_id)))
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    if callback_status == "completed":
        payment.status = "completed"
        payment.ewallet_transaction_id = transaction_id
        payment.completed_at = datetime.now(timezone.utc)

        order_result = await db.execute(select(Order).where(Order.id == payment.order_id))
        order = order_result.scalar_one()
        await _update_order_payment_status(db, order)
    elif callback_status == "failed":
        payment.status = "failed"

    await db.flush()
    return {"status": "ok"}


@router.post("/qr/scan")
async def scan_customer_qr(
    body: QRScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Process a QR code scanned from customer's phone."""
    order_result = await db.execute(select(Order).where(Order.id == body.order_id))
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    payment = Payment(
        order_id=body.order_id,
        payment_method="qr_generic",
        amount=float(order.total),
        status="processing",
        qr_code_data=body.qr_data,
        processed_by=current_user.id,
    )
    db.add(payment)
    await db.flush()
    await db.refresh(payment)

    return {
        "payment_id": str(payment.id),
        "status": "processing",
        "message": "QR code submitted for processing",
    }
