from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.db.database import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    capacity = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    # Relationships
    organization = relationship("Organization", back_populates="warehouses")
    stock_movements = relationship("StockMovement", back_populates="warehouse")

    # Indexes
    __table_args__ = (Index("idx_warehouse_org_id", "org_id"),)
