import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FloorArea(Base):
    __tablename__ = "floor_areas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outlet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("outlets.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    outlet = relationship("Outlet", back_populates="floor_areas")
    tables = relationship("Table", back_populates="floor_area", cascade="all, delete-orphan")


class Table(Base):
    __tablename__ = "tables"
    __table_args__ = (UniqueConstraint("outlet_id", "table_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    floor_area_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("floor_areas.id", ondelete="CASCADE"))
    outlet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("outlets.id", ondelete="CASCADE"))
    table_number: Mapped[str] = mapped_column(String(20), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=4)
    shape: Mapped[str] = mapped_column(String(20), default="rectangle")
    pos_x: Mapped[float] = mapped_column(Float, default=0)
    pos_y: Mapped[float] = mapped_column(Float, default=0)
    width: Mapped[float] = mapped_column(Float, default=100)
    height: Mapped[float] = mapped_column(Float, default=60)
    status: Mapped[str] = mapped_column(String(20), default="available")
    current_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    outlet = relationship("Outlet", back_populates="tables")
    floor_area = relationship("FloorArea", back_populates="tables")
