from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.db.database import Base

from .enums import StockMovementTypeEnum


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False
    )
    type = Column(SQLEnum(StockMovementTypeEnum), nullable=False)
    quantity = Column(Integer, nullable=False)
    reference = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)  # User ID
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    # Relationships
    organization = relationship("Organization", back_populates="stock_movements")
    product = relationship("Product", back_populates="stock_movements")
    warehouse = relationship("Warehouse", back_populates="stock_movements")

    # Indexes
    __table_args__ = (
        Index(
            "idx_stock_movement_org_product_warehouse",
            "org_id",
            "product_id",
            "warehouse_id",
        ),
        Index("idx_stock_movement_created_at", "created_at"),
    )
