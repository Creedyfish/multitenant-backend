import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

from .enums import StockMovementTypeEnum

if TYPE_CHECKING:
    from app.models.organization import Organization, Product, Warehouse


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default="gen_random_uuid()"
    )
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("warehouses.id"))
    type: Mapped[StockMovementTypeEnum] = mapped_column(SQLEnum(StockMovementTypeEnum))
    quantity: Mapped[int]
    reference: Mapped[str | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_by: Mapped[uuid.UUID]
    created_at: Mapped[datetime] = mapped_column(server_default="NOW()")

    organization: Mapped["Organization"] = relationship(
        back_populates="stock_movements"
    )
    product: Mapped["Product"] = relationship(back_populates="stock_movements")
    warehouse: Mapped["Warehouse"] = relationship(back_populates="stock_movements")

    __table_args__ = (
        Index(
            "idx_stock_movement_org_product_warehouse",
            "org_id",
            "product_id",
            "warehouse_id",
        ),
        Index("idx_stock_movement_created_at", "created_at"),
    )
