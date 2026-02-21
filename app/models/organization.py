import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models import (
        AuditLog,
        Product,
        PurchaseRequest,
        StockMovement,
        Supplier,
        User,
        Warehouse,
    )


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default="gen_random_uuid()"
    )
    name: Mapped[str]
    subdomain: Mapped[str] = mapped_column(unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default="NOW()")

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    products: Mapped[list["Product"]] = relationship(back_populates="organization")
    warehouses: Mapped[list["Warehouse"]] = relationship(back_populates="organization")
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="organization"
    )
    purchase_requests: Mapped[list["PurchaseRequest"]] = relationship(
        back_populates="organization"
    )
    suppliers: Mapped[list["Supplier"]] = relationship(back_populates="organization")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="organization")
