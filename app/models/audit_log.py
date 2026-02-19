from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.db.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=False)  # User ID
    action = Column(String, nullable=False)  # CREATE, UPDATE, DELETE, APPROVE, etc.
    entity = Column(String, nullable=False)  # Product, PurchaseRequest, etc.
    entity_id = Column(String, nullable=False)
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=False)
    timestamp = Column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index("idx_audit_log_org_entity", "org_id", "entity", "entity_id"),
        Index("idx_audit_log_timestamp", "timestamp"),
    )
