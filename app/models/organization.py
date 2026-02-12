# app/models/organization.py
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.db.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name = Column(String, nullable=False)
    subdomain = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    # Relationships
    users = relationship("User", back_populates="organization")
    products = relationship("Product", back_populates="organization")
    warehouses = relationship("Warehouse", back_populates="organization")
    stock_movements = relationship("StockMovement", back_populates="organization")
    purchase_requests = relationship("PurchaseRequest", back_populates="organization")
    suppliers = relationship("Supplier", back_populates="organization")
    audit_logs = relationship("AuditLog", back_populates="organization")
