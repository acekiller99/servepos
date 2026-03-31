from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReservationCreate(BaseModel):
    table_id: UUID | None = None
    customer_name: str
    customer_phone: str | None = None
    customer_email: str | None = None
    party_size: int
    reservation_time: datetime
    duration_minutes: int = 90
    notes: str | None = None


class ReservationUpdate(BaseModel):
    table_id: UUID | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    party_size: int | None = None
    reservation_time: datetime | None = None
    duration_minutes: int | None = None
    notes: str | None = None


class ReservationStatusUpdate(BaseModel):
    status: str  # confirmed, seated, completed, cancelled, no_show


class ReservationResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    table_id: UUID | None
    customer_name: str
    customer_phone: str | None
    customer_email: str | None
    party_size: int
    reservation_time: datetime
    duration_minutes: int
    status: str
    notes: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
