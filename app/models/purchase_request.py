from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text

from app.db.database import Base

from .enums import PurchaseRequestStatusEnum


class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    request_number = Column(String, nullable=False)
    status = Column(
        SQLEnum(PurchaseRequestStatusEnum),
        nullable=False,
        default=PurchaseRequestStatusEnum.DRAFT,
    )
    created_by = Column(UUID(as_uuid=True), nullable=False)  # User ID
    approved_by = Column(UUID(as_uuid=True), nullable=True)  # User ID
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(UUID(as_uuid=True), nullable=True)  # User ID
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        onupdate=func.now(),
    )

    # Relationships
    organization = relationship("Organization", back_populates="purchase_requests")
    items = relationship("PurchaseRequestItem", back_populates="request")

    # Indexes and constraints
    __table_args__ = (
        Index(
            "idx_purchase_request_org_number", "org_id", "request_number", unique=True
        ),
        Index("idx_purchase_request_org_status", "org_id", "status"),
    )


class PurchaseRequestItem(Base):
    __tablename__ = "purchase_request_items"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    request_id = Column(
        UUID(as_uuid=True), ForeignKey("purchase_requests.id"), nullable=False
    )
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    estimated_price = Column(Numeric(10, 2), nullable=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)

    # Relationships
    request = relationship("PurchaseRequest", back_populates="items")

    # Indexes
    __table_args__ = (Index("idx_purchase_request_item_request", "request_id"),)
