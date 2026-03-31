import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RegisterSession(Base):
    __tablename__ = "register_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outlet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("outlets.id", ondelete="CASCADE"))
    opened_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    closed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("staff.id"))
    opening_cash: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    closing_cash: Mapped[float | None] = mapped_column(Numeric(10, 2))
    expected_cash: Mapped[float | None] = mapped_column(Numeric(10, 2))
    cash_difference: Mapped[float | None] = mapped_column(Numeric(10, 2))
    total_sales: Mapped[float | None] = mapped_column(Numeric(10, 2))
    total_refunds: Mapped[float | None] = mapped_column(Numeric(10, 2))
    total_discounts: Mapped[float | None] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="open")
