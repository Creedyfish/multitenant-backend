from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text

from app.db.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    sku = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    min_stock_level = Column(Integer, nullable=False, default=0)
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
    organization = relationship("Organization", back_populates="products")
    stock_movements = relationship("StockMovement", back_populates="product")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_product_org_sku", "org_id", "sku", unique=True),
        Index("idx_product_org_id", "org_id"),
    )
