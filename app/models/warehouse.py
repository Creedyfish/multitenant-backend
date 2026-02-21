import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models import Organization, StockMovement


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default="gen_random_uuid()"
    )
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str]
    location: Mapped[str]
    capacity: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default="NOW()")

    organization: Mapped["Organization"] = relationship(back_populates="warehouses")
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="warehouse"
    )

    __table_args__ = (Index("idx_warehouse_org_id", "org_id"),)
