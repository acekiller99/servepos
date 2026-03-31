from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# --- Order Items ---
class OrderItemCreate(BaseModel):
    menu_item_id: UUID | None = None
    item_name: str
    quantity: int = 1
    unit_price: float
    modifiers: list[dict] = []
    notes: str | None = None


class OrderItemUpdate(BaseModel):
    quantity: int | None = None
    modifiers: list[dict] | None = None
    notes: str | None = None


class OrderItemResponse(BaseModel):
    id: UUID
    order_id: UUID
    menu_item_id: UUID | None
    item_name: str
    quantity: int
    unit_price: float
    modifiers: list
    subtotal: float
    notes: str | None
    status: str
    is_void: bool
    sent_to_kitchen: bool
    kitchen_sent_at: datetime | None
    prepared_at: datetime | None
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Orders ---
class OrderCreate(BaseModel):
    order_type: str  # dine_in, takeaway, delivery
    table_id: UUID | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_notes: str | None = None
    guest_count: int = 1
    items: list[OrderItemCreate] = []


class OrderUpdate(BaseModel):
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_notes: str | None = None
    guest_count: int | None = None


class OrderStatusUpdate(BaseModel):
    status: str  # pending, confirmed, preparing, ready, served, completed, cancelled


class OrderVoid(BaseModel):
    void_reason: str


class OrderDiscount(BaseModel):
    discount_amount: float
    discount_reason: str | None = None


class OrderSplit(BaseModel):
    split_type: str  # 'equal', 'by_item'
    num_splits: int | None = None  # for equal splits
    item_groups: list[list[UUID]] | None = None  # for by_item splits


class OrderResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    order_number: str
    order_type: str
    table_id: UUID | None
    staff_id: UUID | None
    customer_name: str | None
    customer_phone: str | None
    customer_notes: str | None
    subtotal: float
    tax_amount: float
    service_charge: float
    discount_amount: float
    discount_reason: str | None
    total: float
    status: str
    payment_status: str
    guest_count: int
    is_void: bool
    void_reason: str | None = None
    voided_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}


# --- Offline Sync ---
class OfflineOrderSync(BaseModel):
    orders: list[OrderCreate]
