from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OutletCreate(BaseModel):
    name: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    tax_id: str | None = None
    currency: str = "USD"
    tax_rate: float = 0
    service_charge_rate: float = 0
    receipt_header: str | None = None
    receipt_footer: str | None = None
    timezone: str = "UTC"


class OutletUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    tax_id: str | None = None
    currency: str | None = None
    tax_rate: float | None = None
    service_charge_rate: float | None = None
    receipt_header: str | None = None
    receipt_footer: str | None = None
    timezone: str | None = None
    is_active: bool | None = None


class OutletResponse(BaseModel):
    id: UUID
    name: str
    address: str | None
    phone: str | None
    email: str | None
    tax_id: str | None
    currency: str
    tax_rate: float
    service_charge_rate: float
    receipt_header: str | None
    receipt_footer: str | None
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
