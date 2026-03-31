from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.outlet import Outlet
from app.models.staff import Staff
from app.schemas.outlet import OutletCreate, OutletResponse, OutletUpdate

router = APIRouter()


@router.get("", response_model=list[OutletResponse])
async def list_outlets(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    if current_user.role == "admin":
        result = await db.execute(select(Outlet).where(Outlet.is_active == True))
    else:
        result = await db.execute(select(Outlet).where(Outlet.id == current_user.outlet_id))
    return result.scalars().all()


@router.post("", response_model=OutletResponse, status_code=status.HTTP_201_CREATED)
async def create_outlet(
    body: OutletCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner")),
):
    outlet = Outlet(**body.model_dump())
    db.add(outlet)
    await db.flush()
    await db.refresh(outlet)
    return outlet


@router.get("/{outlet_id}", response_model=OutletResponse)
async def get_outlet(
    outlet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(select(Outlet).where(Outlet.id == outlet_id))
    outlet = result.scalar_one_or_none()
    if outlet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlet not found")
    return outlet


@router.put("/{outlet_id}", response_model=OutletResponse)
async def update_outlet(
    outlet_id: UUID,
    body: OutletUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(select(Outlet).where(Outlet.id == outlet_id))
    outlet = result.scalar_one_or_none()
    if outlet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlet not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(outlet, field, value)

    await db.flush()
    await db.refresh(outlet)
    return outlet


@router.get("/{outlet_id}/settings", response_model=OutletResponse)
async def get_outlet_settings(
    outlet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(select(Outlet).where(Outlet.id == outlet_id))
    outlet = result.scalar_one_or_none()
    if outlet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlet not found")
    return outlet


@router.put("/{outlet_id}/settings", response_model=OutletResponse)
async def update_outlet_settings(
    outlet_id: UUID,
    body: OutletUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner")),
):
    return await update_outlet(outlet_id, body, db, current_user)
