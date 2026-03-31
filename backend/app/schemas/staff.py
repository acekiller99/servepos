from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StaffCreate(BaseModel):
    outlet_id: UUID
    email: str | None = None
    password: str
    full_name: str
    role: str  # owner, manager, cashier, waiter, kitchen, admin
    pin_code: str | None = None
    phone: str | None = None
    hourly_rate: float | None = None
    permissions: list[str] = []


class StaffUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    full_name: str | None = None
    role: str | None = None
    pin_code: str | None = None
    phone: str | None = None
    hourly_rate: float | None = None
    is_active: bool | None = None
    permissions: list[str] | None = None


class StaffResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    email: str | None
    full_name: str
    role: str
    phone: str | None
    hourly_rate: float | None
    is_active: bool
    permissions: list
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShiftResponse(BaseModel):
    id: UUID
    staff_id: UUID
    outlet_id: UUID
    clock_in: datetime
    clock_out: datetime | None
    break_minutes: int
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
