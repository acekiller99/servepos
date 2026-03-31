from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, cast, select, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.reservation import Reservation
from app.models.staff import Staff
from app.schemas.reservation import (
    ReservationCreate,
    ReservationResponse,
    ReservationStatusUpdate,
    ReservationUpdate,
)

router = APIRouter()


@router.get("", response_model=list[ReservationResponse])
async def list_reservations(
    date_filter: date | None = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    query = select(Reservation).where(
        Reservation.outlet_id == current_user.outlet_id
    ).order_by(Reservation.reservation_time)

    if date_filter:
        query = query.where(cast(Reservation.reservation_time, Date) == date_filter)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    body: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    reservation = Reservation(
        outlet_id=current_user.outlet_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    db.add(reservation)
    await db.flush()
    await db.refresh(reservation)
    return reservation


@router.put("/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    reservation_id: UUID,
    body: ReservationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.outlet_id == current_user.outlet_id,
        )
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(reservation, field, value)
    await db.flush()
    await db.refresh(reservation)
    return reservation


@router.put("/{reservation_id}/status", response_model=ReservationResponse)
async def update_reservation_status(
    reservation_id: UUID,
    body: ReservationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.outlet_id == current_user.outlet_id,
        )
    )
    reservation = result.scalar_one_or_none()
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    reservation.status = body.status
    await db.flush()
    await db.refresh(reservation)
    return reservation


@router.get("/availability")
async def check_availability(
    date_check: date = Query(..., alias="date"),
    party_size: int = Query(1),
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    from app.models.table import Table

    # Get all tables that can fit the party
    tables_result = await db.execute(
        select(Table).where(
            Table.outlet_id == current_user.outlet_id,
            Table.is_active == True,
            Table.capacity >= party_size,
        )
    )
    tables = tables_result.scalars().all()

    # Get reservations for the date
    reservations_result = await db.execute(
        select(Reservation).where(
            Reservation.outlet_id == current_user.outlet_id,
            cast(Reservation.reservation_time, Date) == date_check,
            Reservation.status.in_(["confirmed", "seated"]),
        )
    )
    reservations = reservations_result.scalars().all()

    # Build time slots (every 30 min from 10:00 to 22:00)
    slots = []
    for hour in range(10, 22):
        for minute in (0, 30):
            slot_time = datetime(date_check.year, date_check.month, date_check.day, hour, minute)
            slot_end = slot_time + timedelta(minutes=90)

            available_tables = []
            for table in tables:
                is_reserved = any(
                    r.table_id == table.id
                    and r.reservation_time < slot_end
                    and r.reservation_time + timedelta(minutes=r.duration_minutes) > slot_time
                    for r in reservations
                )
                if not is_reserved:
                    available_tables.append({"id": str(table.id), "table_number": table.table_number, "capacity": table.capacity})

            slots.append({
                "time": slot_time.strftime("%H:%M"),
                "available_tables": available_tables,
                "available_count": len(available_tables),
            })

    return slots
