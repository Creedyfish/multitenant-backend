import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base

if TYPE_CHECKING:
    from app.models import Organization, StockMovement


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default="gen_random_uuid()"
    )
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    sku: Mapped[str]
    name: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text, default=None)
    category: Mapped[str | None] = mapped_column(default=None)
    min_stock_level: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(server_default="NOW()")
    updated_at: Mapped[datetime] = mapped_column(
        server_default="NOW()", onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="products")
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="product"
    )

    __table_args__ = (
        Index("idx_product_org_sku", "org_id", "sku", unique=True),
        Index("idx_product_org_id", "org_id"),
    )
