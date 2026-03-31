from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.ewallet import EwalletProvider
from app.models.staff import Staff
from app.schemas.payment import (
    EwalletProviderCreate,
    EwalletProviderResponse,
    EwalletProviderUpdate,
)

router = APIRouter()

SUPPORTED_PROVIDERS = [
    {"name": "alipay", "display_name": "Alipay"},
    {"name": "touch_n_go", "display_name": "Touch 'n Go eWallet"},
    {"name": "grabpay", "display_name": "GrabPay"},
    {"name": "boost", "display_name": "Boost"},
    {"name": "wechat_pay", "display_name": "WeChat Pay"},
    {"name": "shopeepay", "display_name": "ShopeePay"},
    {"name": "qr_generic", "display_name": "Generic QR Code"},
]


@router.get("/providers", response_model=list[EwalletProviderResponse])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(EwalletProvider)
        .where(EwalletProvider.outlet_id == current_user.outlet_id)
        .order_by(EwalletProvider.sort_order)
    )
    return result.scalars().all()


@router.post("/providers", response_model=EwalletProviderResponse, status_code=status.HTTP_201_CREATED)
async def add_provider(
    body: EwalletProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    provider = EwalletProvider(
        outlet_id=current_user.outlet_id,
        **body.model_dump(),
    )
    db.add(provider)
    await db.flush()
    await db.refresh(provider)
    return provider


@router.put("/providers/{provider_id}", response_model=EwalletProviderResponse)
async def update_provider(
    provider_id: UUID,
    body: EwalletProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(EwalletProvider).where(
            EwalletProvider.id == provider_id,
            EwalletProvider.outlet_id == current_user.outlet_id,
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)
    await db.flush()
    await db.refresh(provider)
    return provider


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(EwalletProvider).where(
            EwalletProvider.id == provider_id,
            EwalletProvider.outlet_id == current_user.outlet_id,
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    await db.delete(provider)


@router.post("/providers/{provider_id}/test")
async def test_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(EwalletProvider).where(
            EwalletProvider.id == provider_id,
            EwalletProvider.outlet_id == current_user.outlet_id,
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    # Placeholder: in production, this would test actual API connectivity
    return {
        "provider": provider.provider_name,
        "status": "ok",
        "message": f"Connection test for {provider.display_name} successful (simulated)",
    }


@router.get("/providers/available")
async def available_providers(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    configured_result = await db.execute(
        select(EwalletProvider.provider_name)
        .where(EwalletProvider.outlet_id == current_user.outlet_id)
    )
    configured = {row[0] for row in configured_result.all()}

    return [
        {
            **p,
            "is_configured": p["name"] in configured,
        }
        for p in SUPPORTED_PROVIDERS
    ]
