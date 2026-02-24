import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default="gen_random_uuid()"
    )
    name: Mapped[str]
    subdomain: Mapped[str] = mapped_column(unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="NOW()"
    )

    # Relationships
    users = relationship("User", back_populates="organization")
    products = relationship("Product", back_populates="organization")
    warehouses = relationship("Warehouse", back_populates="organization")
    stock_movements = relationship("StockMovement", back_populates="organization")
    purchase_requests = relationship("PurchaseRequest", back_populates="organization")
    suppliers = relationship("Supplier", back_populates="organization")
    audit_logs = relationship("AuditLog", back_populates="organization")
