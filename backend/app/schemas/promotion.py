from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel


class PromotionCreate(BaseModel):
    name: str
    type: str  # percentage, fixed_amount, buy_x_get_y, happy_hour
    value: float
    min_order_amount: float | None = None
    applicable_items: list[str] = []
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    valid_days: list[int] = [0, 1, 2, 3, 4, 5, 6]
    valid_hours_start: time | None = None
    valid_hours_end: time | None = None
    promo_code: str | None = None
    is_active: bool = True
    usage_limit: int | None = None


class PromotionUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    value: float | None = None
    min_order_amount: float | None = None
    applicable_items: list[str] | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    valid_days: list[int] | None = None
    valid_hours_start: time | None = None
    valid_hours_end: time | None = None
    promo_code: str | None = None
    is_active: bool | None = None
    usage_limit: int | None = None


class PromotionResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    name: str
    type: str
    value: float
    min_order_amount: float | None
    applicable_items: list
    valid_from: datetime | None
    valid_until: datetime | None
    valid_days: list
    valid_hours_start: time | None
    valid_hours_end: time | None
    promo_code: str | None
    is_active: bool
    usage_limit: int | None
    usage_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PromoValidateRequest(BaseModel):
    promo_code: str
    order_total: float
