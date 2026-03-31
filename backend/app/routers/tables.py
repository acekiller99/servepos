from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.order import Order
from app.models.staff import Staff
from app.models.table import FloorArea, Table
from app.schemas.table import (
    FloorAreaCreate,
    FloorAreaResponse,
    FloorAreaUpdate,
    FloorPlanUpdate,
    TableCreate,
    TableMerge,
    TableResponse,
    TableStatusUpdate,
    TableTransfer,
    TableUpdate,
)

router = APIRouter()


# ---- Tables ----

@router.get("", response_model=list[TableResponse])
async def list_tables(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Table)
        .where(Table.outlet_id == current_user.outlet_id, Table.is_active == True)
        .order_by(Table.table_number)
    )
    return result.scalars().all()


@router.post("", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
async def create_table(
    body: TableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    table = Table(outlet_id=current_user.outlet_id, **body.model_dump())
    db.add(table)
    await db.flush()
    await db.refresh(table)
    return table


@router.get("/floor-plan", response_model=list[TableResponse])
async def get_floor_plan(
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Table).where(Table.outlet_id == current_user.outlet_id, Table.is_active == True)
    )
    return result.scalars().all()


@router.put("/floor-plan")
async def update_floor_plan(
    body: FloorPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    for table_data in body.tables:
        table_id = table_data.get("id")
        if not table_id:
            continue
        result = await db.execute(
            select(Table).where(
                Table.id == UUID(table_id),
                Table.outlet_id == current_user.outlet_id,
            )
        )
        table = result.scalar_one_or_none()
        if table:
            if "pos_x" in table_data:
                table.pos_x = table_data["pos_x"]
            if "pos_y" in table_data:
                table.pos_y = table_data["pos_y"]
            if "width" in table_data:
                table.width = table_data["width"]
            if "height" in table_data:
                table.height = table_data["height"]
    await db.flush()
    return {"status": "ok"}


@router.get("/{table_id}", response_model=TableResponse)
async def get_table(
    table_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Table).where(Table.id == table_id, Table.outlet_id == current_user.outlet_id)
    )
    table = result.scalar_one_or_none()
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    return table


@router.put("/{table_id}", response_model=TableResponse)
async def update_table(
    table_id: UUID,
    body: TableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(require_roles("admin", "owner", "manager")),
):
    result = await db.execute(
        select(Table).where(Table.id == table_id, Table.outlet_id == current_user.outlet_id)
    )
    table = result.scalar_one_or_none()
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(table, field, value)
    await db.flush()
    await db.refresh(table)
    return table


@router.put("/{table_id}/status", response_model=TableResponse)
async def update_table_status(
    table_id: UUID,
    body: TableStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    result = await db.execute(
        select(Table).where(Table.id == table_id, Table.outlet_id == current_user.outlet_id)
    )
    table = result.scalar_one_or_none()
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    table.status = body.status
    if body.status == "available":
        table.current_order_id = None
    await db.flush()
    await db.refresh(table)
    return table


@router.post("/{table_id}/transfer", response_model=TableResponse)
async def transfer_table(
    table_id: UUID,
    body: TableTransfer,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    source_result = await db.execute(
        select(Table).where(Table.id == table_id, Table.outlet_id == current_user.outlet_id)
    )
    source = source_result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source table not found")

    target_result = await db.execute(
        select(Table).where(Table.id == body.target_table_id, Table.outlet_id == current_user.outlet_id)
    )
    target = target_result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target table not found")

    if target.status == "occupied":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Target table is occupied")

    # Transfer order
    target.current_order_id = source.current_order_id
    target.status = "occupied"
    source.current_order_id = None
    source.status = "available"

    # Update the order's table_id
    if target.current_order_id:
        order_result = await db.execute(select(Order).where(Order.id == target.current_order_id))
        order = order_result.scalar_one_or_none()
        if order:
            order.table_id = target.id

    await db.flush()
    await db.refresh(target)
    return target


@router.post("/{table_id}/merge")
async def merge_tables(
    table_id: UUID,
    body: TableMerge,
    db: AsyncSession = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    main_result = await db.execute(
        select(Table).where(Table.id == table_id, Table.outlet_id == current_user.outlet_id)
    )
    main_table = main_result.scalar_one_or_none()
    if main_table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Main table not found")

    merged_tables = []
    for merge_id in body.merge_table_ids:
        result = await db.execute(
            select(Table).where(Table.id == merge_id, Table.outlet_id == current_user.outlet_id)
        )
        table = result.scalar_one_or_none()
        if table is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Table {merge_id} not found")
        table.status = "occupied"
        table.current_order_id = main_table.current_order_id
        merged_tables.append(str(table.table_number))

    await db.flush()
    return {
        "main_table": str(main_table.table_number),
        "merged_with": merged_tables,
        "order_id": str(main_table.current_order_id) if main_table.current_order_id else None,
    }
