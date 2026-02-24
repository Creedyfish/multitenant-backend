import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default="gen_random_uuid()"
    )
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    actor_id: Mapped[uuid.UUID]  # User ID
    action: Mapped[str] = mapped_column(String)  # CREATE, UPDATE, DELETE, APPROVE, etc.
    entity: Mapped[str] = mapped_column(String)  # Product, PurchaseRequest, etc.
    entity_id: Mapped[str] = mapped_column(String)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    after: Mapped[dict[str, Any]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="NOW()"
    )
    ip_address: Mapped[str | None] = mapped_column(String, default=None)
    user_agent: Mapped[str | None] = mapped_column(Text, default=None)

    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index("idx_audit_log_org_entity", "org_id", "entity", "entity_id"),
        Index("idx_audit_log_timestamp", "timestamp"),
    )
