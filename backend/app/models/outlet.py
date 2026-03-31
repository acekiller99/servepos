import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Outlet(Base):
    __tablename__ = "outlets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    tax_id: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    service_charge_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    receipt_header: Mapped[str | None] = mapped_column(Text)
    receipt_footer: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    staff = relationship("Staff", back_populates="outlet", cascade="all, delete-orphan")
    floor_areas = relationship("FloorArea", back_populates="outlet", cascade="all, delete-orphan")
    tables = relationship("Table", back_populates="outlet", cascade="all, delete-orphan")
    menu_categories = relationship("MenuCategory", back_populates="outlet", cascade="all, delete-orphan")
    menu_items = relationship("MenuItem", back_populates="outlet", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="outlet", cascade="all, delete-orphan")
