from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.db.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    # Relationships
    organization = relationship("Organization", back_populates="suppliers")

    # Indexes
    __table_args__ = (Index("idx_supplier_org_id", "org_id"),)
