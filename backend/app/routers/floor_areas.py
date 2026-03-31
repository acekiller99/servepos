from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.staff import Staff
from app.models.table import FloorArea
from app.schemas.table import FloorAreaCreate, FloorAreaResponse, FloorAreaUpdate

router = APIRouter()


@router.get("", response_model=list[FloorAreaResponse])
async def list_floor_areas(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(FloorArea)
        .where(FloorArea.outlet_id == current_user.outlet_id)
        .order_by(FloorArea.sort_order)
    )
    return result.scalars().all()


@router.post("", response_model=FloorAreaResponse, status_code=status.HTTP_201_CREATED)
async def create_floor_area(
    body: FloorAreaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    area = FloorArea(outlet_id=current_user.outlet_id, **body.model_dump())
    db.add(area)
    await db.flush()
    await db.refresh(area)
    return area


@router.put("/{area_id}", response_model=FloorAreaResponse)
async def update_floor_area(
    area_id: UUID,
    body: FloorAreaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(FloorArea).where(
            FloorArea.id == area_id,
            FloorArea.outlet_id == current_user.outlet_id,
        )
    )
    area = result.scalar_one_or_none()
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor area not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(area, field, value)
    await db.flush()
    await db.refresh(area)
    return area


@router.delete("/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_floor_area(
    area_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(FloorArea).where(
            FloorArea.id == area_id,
            FloorArea.outlet_id == current_user.outlet_id,
        )
    )
    area = result.scalar_one_or_none()
    if area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor area not found")
    await db.delete(area)
