from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.shift import Shift
from app.models.staff import Staff
from app.schemas.staff import ShiftResponse, StaffCreate, StaffResponse, StaffUpdate
from app.utils.security import hash_password

router = APIRouter()


@router.get("", response_model=list[StaffResponse])
async def list_staff(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(Staff).where(Staff.outlet_id == current_user.outlet_id)
    )
    return result.scalars().all()


@router.post("", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    body: StaffCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    if body.email:
        existing = await db.execute(select(Staff).where(Staff.email == body.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

    staff_data = body.model_dump(exclude={"password"})
    staff_data["hashed_password"] = hash_password(body.password)
    staff = Staff(**staff_data)
    db.add(staff)
    await db.flush()
    await db.refresh(staff)
    return staff


@router.get("/{staff_id}", response_model=StaffResponse)
async def get_staff(
    staff_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")
    return staff


@router.put("/{staff_id}", response_model=StaffResponse)
async def update_staff(
    staff_id: UUID,
    body: StaffUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")

    update_data = body.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))
    for field, value in update_data.items():
        setattr(staff, field, value)

    await db.flush()
    await db.refresh(staff)
    return staff


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_staff(
    staff_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")
    staff.is_active = False
    await db.flush()


@router.post("/{staff_id}/clock-in", response_model=ShiftResponse)
async def clock_in(
    staff_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")

    # Check for already open shift
    open_shift = await db.execute(
        select(Shift).where(Shift.staff_id == staff_id, Shift.clock_out.is_(None))
    )
    if open_shift.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already clocked in")

    shift = Shift(
        staff_id=staff_id,
        outlet_id=staff.outlet_id,
        clock_in=datetime.now(timezone.utc),
    )
    db.add(shift)
    await db.flush()
    await db.refresh(shift)
    return shift


@router.post("/{staff_id}/clock-out", response_model=ShiftResponse)
async def clock_out(
    staff_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Shift).where(Shift.staff_id == staff_id, Shift.clock_out.is_(None))
    )
    shift = result.scalar_one_or_none()
    if shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active shift found")

    shift.clock_out = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(shift)
    return shift


@router.get("/{staff_id}/shifts", response_model=list[ShiftResponse])
async def list_shifts(
    staff_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Shift).where(Shift.staff_id == staff_id).order_by(Shift.clock_in.desc())
    )
    return result.scalars().all()
