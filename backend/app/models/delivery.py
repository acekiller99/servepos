import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DeliveryPlatform(Base):
    __tablename__ = "delivery_platforms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outlet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("outlets.id", ondelete="CASCADE"))
    platform_name: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    store_id: Mapped[str | None] = mapped_column(String(200))
    credentials_encrypted: Mapped[dict] = mapped_column(JSONB, nullable=False)
    integration_type: Mapped[str] = mapped_column(String(20), default="webhook")
    webhook_secret: Mapped[str | None] = mapped_column(String(200))
    polling_interval_seconds: Mapped[int] = mapped_column(Integer, default=30)
    auto_accept: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_accept_delay_seconds: Mapped[int] = mapped_column(Integer, default=0)
    menu_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DeliveryOrder(Base):
    __tablename__ = "delivery_orders"
    __table_args__ = (UniqueConstraint("platform_id", "platform_order_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"))
    platform_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("delivery_platforms.id", ondelete="SET NULL"))
    platform_order_id: Mapped[str] = mapped_column(String(200), nullable=False)
    platform_order_number: Mapped[str | None] = mapped_column(String(50))
    platform_status: Mapped[str | None] = mapped_column(String(30))
    customer_name: Mapped[str | None] = mapped_column(String(200))
    customer_phone: Mapped[str | None] = mapped_column(String(50))
    customer_address: Mapped[str | None] = mapped_column(Text)
    delivery_notes: Mapped[str | None] = mapped_column(Text)
    rider_name: Mapped[str | None] = mapped_column(String(200))
    rider_phone: Mapped[str | None] = mapped_column(String(50))
    rider_vehicle: Mapped[str | None] = mapped_column(String(50))
    estimated_pickup_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_delivery_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_pickup_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    platform_subtotal: Mapped[float | None] = mapped_column(Numeric(10, 2))
    platform_commission: Mapped[float | None] = mapped_column(Numeric(10, 2))
    platform_delivery_fee: Mapped[float | None] = mapped_column(Numeric(10, 2))
    net_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
