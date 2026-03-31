from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class InventoryItemCreate(BaseModel):
    name: str
    sku: str | None = None
    unit: str
    quantity: float = 0
    min_quantity: float = 0
    cost_per_unit: float | None = None
    supplier: str | None = None
    category: str | None = None


class InventoryItemUpdate(BaseModel):
    name: str | None = None
    sku: str | None = None
    unit: str | None = None
    min_quantity: float | None = None
    cost_per_unit: float | None = None
    supplier: str | None = None
    category: str | None = None
    is_active: bool | None = None


class InventoryItemResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    name: str
    sku: str | None
    unit: str
    quantity: float
    min_quantity: float
    cost_per_unit: float | None
    supplier: str | None
    category: str | None
    is_active: bool
    last_restocked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RestockRequest(BaseModel):
    quantity: float
    cost_per_unit: float | None = None
    notes: str | None = None


class WasteRequest(BaseModel):
    inventory_item_id: UUID
    quantity: float
    notes: str | None = None


class InventoryTransactionResponse(BaseModel):
    id: UUID
    inventory_item_id: UUID
    transaction_type: str
    quantity_change: float
    reference_id: UUID | None
    notes: str | None
    performed_by: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
