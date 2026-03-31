from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PaymentCreate(BaseModel):
    order_id: UUID
    payment_method: str  # cash, card, alipay, touch_n_go, grabpay, boost, wechat_pay, shopeepay, qr_generic
    amount: float
    tip_amount: float = 0
    reference_number: str | None = None
    notes: str | None = None


class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    payment_method: str
    amount: float
    tip_amount: float
    reference_number: str | None
    change_amount: float
    qr_code_data: str | None
    qr_code_url: str | None
    ewallet_transaction_id: str | None
    status: str
    expires_at: datetime | None
    completed_at: datetime | None
    processed_by: UUID | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentRefund(BaseModel):
    reason: str | None = None


class QRGenerateRequest(BaseModel):
    order_id: UUID
    provider: str  # alipay, touch_n_go, grabpay, etc.
    amount: float


class QRGenerateResponse(BaseModel):
    qr_code_base64: str
    qr_url: str | None
    payment_id: UUID
    expires_at: datetime


class QRStatusResponse(BaseModel):
    status: str
    transaction_id: str | None = None


class QRScanRequest(BaseModel):
    order_id: UUID
    qr_data: str


# --- E-Wallet Providers ---
class EwalletProviderCreate(BaseModel):
    provider_name: str
    display_name: str
    merchant_id: str | None = None
    credentials_encrypted: dict
    qr_type: str = "dynamic"
    callback_url: str | None = None
    logo_url: str | None = None
    sort_order: int = 0


class EwalletProviderUpdate(BaseModel):
    display_name: str | None = None
    merchant_id: str | None = None
    credentials_encrypted: dict | None = None
    qr_type: str | None = None
    callback_url: str | None = None
    is_active: bool | None = None
    logo_url: str | None = None
    sort_order: int | None = None


class EwalletProviderResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    provider_name: str
    display_name: str
    merchant_id: str | None
    qr_type: str
    callback_url: str | None
    is_active: bool
    logo_url: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Register Sessions ---
class RegisterOpenRequest(BaseModel):
    opening_cash: float
    notes: str | None = None


class RegisterCloseRequest(BaseModel):
    closing_cash: float
    notes: str | None = None


class RegisterSessionResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    opened_by: UUID | None
    closed_by: UUID | None
    opening_cash: float
    closing_cash: float | None
    expected_cash: float | None
    cash_difference: float | None
    total_sales: float | None
    total_refunds: float | None
    total_discounts: float | None
    notes: str | None
    opened_at: datetime
    closed_at: datetime | None
    status: str

    model_config = {"from_attributes": True}
