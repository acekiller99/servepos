from uuid import UUID

from pydantic import BaseModel


# --- Floor Areas ---
class FloorAreaCreate(BaseModel):
    name: str
    sort_order: int = 0
    is_active: bool = True


class FloorAreaUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class FloorAreaResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    name: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


# --- Tables ---
class TableCreate(BaseModel):
    floor_area_id: UUID
    table_number: str
    capacity: int = 4
    shape: str = "rectangle"
    pos_x: float = 0
    pos_y: float = 0
    width: float = 100
    height: float = 60


class TableUpdate(BaseModel):
    floor_area_id: UUID | None = None
    table_number: str | None = None
    capacity: int | None = None
    shape: str | None = None
    pos_x: float | None = None
    pos_y: float | None = None
    width: float | None = None
    height: float | None = None
    is_active: bool | None = None


class TableStatusUpdate(BaseModel):
    status: str  # available, occupied, reserved, cleaning


class TableResponse(BaseModel):
    id: UUID
    floor_area_id: UUID
    outlet_id: UUID
    table_number: str
    capacity: int
    shape: str
    pos_x: float
    pos_y: float
    width: float
    height: float
    status: str
    current_order_id: UUID | None
    is_active: bool

    model_config = {"from_attributes": True}


class FloorPlanUpdate(BaseModel):
    tables: list[dict]  # [{"id": "...", "pos_x": 0, "pos_y": 0, "width": 100, "height": 60}]


class TableTransfer(BaseModel):
    target_table_id: UUID


class TableMerge(BaseModel):
    merge_table_ids: list[UUID]
