from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# --- Menu Categories ---
class MenuCategoryCreate(BaseModel):
    name: str
    description: str | None = None
    image_url: str | None = None
    sort_order: int = 0
    is_active: bool = True
    parent_id: UUID | None = None


class MenuCategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    image_url: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    parent_id: UUID | None = None


class MenuCategoryResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    name: str
    description: str | None
    image_url: str | None
    sort_order: int
    is_active: bool
    parent_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Menu Items ---
class MenuItemCreate(BaseModel):
    category_id: UUID | None = None
    name: str
    description: str | None = None
    price: float
    cost_price: float | None = None
    image_url: str | None = None
    sku: str | None = None
    barcode: str | None = None
    tax_rate_override: float | None = None
    is_taxable: bool = True
    preparation_time_minutes: int | None = None
    calories: int | None = None
    allergens: list[str] = []
    tags: list[str] = []
    is_available: bool = True
    sort_order: int = 0


class MenuItemUpdate(BaseModel):
    category_id: UUID | None = None
    name: str | None = None
    description: str | None = None
    price: float | None = None
    cost_price: float | None = None
    image_url: str | None = None
    sku: str | None = None
    barcode: str | None = None
    tax_rate_override: float | None = None
    is_taxable: bool | None = None
    preparation_time_minutes: int | None = None
    calories: int | None = None
    allergens: list[str] | None = None
    tags: list[str] | None = None
    is_available: bool | None = None
    sort_order: int | None = None


class MenuItemResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    category_id: UUID | None
    name: str
    description: str | None
    price: float
    cost_price: float | None
    image_url: str | None
    sku: str | None
    barcode: str | None
    tax_rate_override: float | None
    is_taxable: bool
    preparation_time_minutes: int | None
    calories: int | None
    allergens: list
    tags: list
    is_available: bool
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Modifier Groups ---
class ModifierOptionCreate(BaseModel):
    name: str
    price_adjustment: float = 0
    sort_order: int = 0
    is_active: bool = True


class ModifierOptionResponse(BaseModel):
    id: UUID
    group_id: UUID
    name: str
    price_adjustment: float
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class ModifierGroupCreate(BaseModel):
    name: str
    selection_type: str = "single"
    min_selections: int = 0
    max_selections: int = 1
    is_required: bool = False
    sort_order: int = 0
    options: list[ModifierOptionCreate] = []
    menu_item_ids: list[UUID] = []


class ModifierGroupUpdate(BaseModel):
    name: str | None = None
    selection_type: str | None = None
    min_selections: int | None = None
    max_selections: int | None = None
    is_required: bool | None = None
    sort_order: int | None = None


class ModifierGroupResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    name: str
    selection_type: str
    min_selections: int
    max_selections: int
    is_required: bool
    sort_order: int
    options: list[ModifierOptionResponse] = []

    model_config = {"from_attributes": True}


# --- Combo Meals ---
class ComboItemCreate(BaseModel):
    menu_item_id: UUID
    quantity: int = 1
    is_substitutable: bool = False


class ComboItemResponse(BaseModel):
    id: UUID
    combo_id: UUID
    menu_item_id: UUID
    quantity: int
    is_substitutable: bool

    model_config = {"from_attributes": True}


class ComboMealCreate(BaseModel):
    name: str
    description: str | None = None
    price: float
    image_url: str | None = None
    items: list[ComboItemCreate] = []


class ComboMealUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    image_url: str | None = None
    is_active: bool | None = None


class ComboMealResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    name: str
    description: str | None
    price: float
    image_url: str | None
    is_active: bool
    created_at: datetime
    items: list[ComboItemResponse] = []

    model_config = {"from_attributes": True}


# --- Availability ---
class AvailabilityUpdate(BaseModel):
    is_available: bool
