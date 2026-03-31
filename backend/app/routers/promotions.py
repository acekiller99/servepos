from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.promotion import Promotion
from app.models.staff import Staff
from app.schemas.promotion import (
    PromoValidateRequest,
    PromotionCreate,
    PromotionResponse,
    PromotionUpdate,
)

router = APIRouter()


@router.get("", response_model=list[PromotionResponse])
async def list_promotions(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Promotion).where(Promotion.outlet_id == current_user.outlet_id)
    )
    return result.scalars().all()


@router.post("", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED)
async def create_promotion(
    body: PromotionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    promo = Promotion(outlet_id=current_user.outlet_id, **body.model_dump())
    db.add(promo)
    await db.flush()
    await db.refresh(promo)
    return promo


@router.put("/{promo_id}", response_model=PromotionResponse)
async def update_promotion(
    promo_id: UUID,
    body: PromotionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(Promotion).where(
            Promotion.id == promo_id,
            Promotion.outlet_id == current_user.outlet_id,
        )
    )
    promo = result.scalar_one_or_none()
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(promo, field, value)
    await db.flush()
    await db.refresh(promo)
    return promo


@router.delete("/{promo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_promotion(
    promo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(Promotion).where(
            Promotion.id == promo_id,
            Promotion.outlet_id == current_user.outlet_id,
        )
    )
    promo = result.scalar_one_or_none()
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")
    await db.delete(promo)


@router.post("/validate")
async def validate_promo(
    body: PromoValidateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Promotion).where(
            Promotion.outlet_id == current_user.outlet_id,
            Promotion.promo_code == body.promo_code,
            Promotion.is_active == True,
        )
    )
    promo = result.scalar_one_or_none()
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid promo code")

    now = datetime.now(timezone.utc)

    # Check validity period
    if promo.valid_from:
        valid_from = promo.valid_from if promo.valid_from.tzinfo else promo.valid_from.replace(tzinfo=timezone.utc)
        if now < valid_from:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promo not yet active")
    if promo.valid_until:
        valid_until = promo.valid_until if promo.valid_until.tzinfo else promo.valid_until.replace(tzinfo=timezone.utc)
        if now > valid_until:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promo has expired")

    # Check usage limit
    if promo.usage_limit and promo.usage_count >= promo.usage_limit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promo usage limit reached")

    # Check minimum order
    if promo.min_order_amount and body.order_total < float(promo.min_order_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum order amount is {promo.min_order_amount}",
        )

    # Check valid days
    if now.weekday() not in (promo.valid_days or [0, 1, 2, 3, 4, 5, 6]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promo not valid today")

    # Calculate discount
    discount = 0.0
    if promo.type == "percentage":
        discount = body.order_total * float(promo.value) / 100
    elif promo.type == "fixed_amount":
        discount = float(promo.value)

    return {
        "valid": True,
        "promo_id": str(promo.id),
        "name": promo.name,
        "type": promo.type,
        "discount_amount": round(discount, 2),
    }
