from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DeliveryPlatformCreate(BaseModel):
    platform_name: str
    display_name: str
    store_id: str | None = None
    credentials_encrypted: dict
    integration_type: str = "webhook"
    webhook_secret: str | None = None
    polling_interval_seconds: int = 30
    auto_accept: bool = False
    auto_accept_delay_seconds: int = 0
    menu_sync_enabled: bool = False


class DeliveryPlatformUpdate(BaseModel):
    display_name: str | None = None
    store_id: str | None = None
    credentials_encrypted: dict | None = None
    integration_type: str | None = None
    webhook_secret: str | None = None
    polling_interval_seconds: int | None = None
    auto_accept: bool | None = None
    auto_accept_delay_seconds: int | None = None
    menu_sync_enabled: bool | None = None
    is_active: bool | None = None


class DeliveryPlatformResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    platform_name: str
    display_name: str
    store_id: str | None
    integration_type: str
    polling_interval_seconds: int
    auto_accept: bool
    auto_accept_delay_seconds: int
    menu_sync_enabled: bool
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeliveryOrderResponse(BaseModel):
    id: UUID
    order_id: UUID
    platform_id: UUID | None
    platform_order_id: str
    platform_order_number: str | None
    platform_status: str | None
    customer_name: str | None
    customer_phone: str | None
    customer_address: str | None
    delivery_notes: str | None
    rider_name: str | None
    rider_phone: str | None
    rider_vehicle: str | None
    estimated_pickup_time: datetime | None
    estimated_delivery_time: datetime | None
    actual_pickup_time: datetime | None
    platform_subtotal: float | None
    platform_commission: float | None
    platform_delivery_fee: float | None
    net_amount: float | None
    is_accepted: bool
    accepted_at: datetime | None
    rejected_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeliveryOrderReject(BaseModel):
    reason: str


class DeliveryOrderStatusUpdate(BaseModel):
    status: str  # preparing, ready_for_pickup, picked_up
