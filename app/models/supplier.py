import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default="gen_random_uuid()"
    )
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str]
    contact_email: Mapped[str | None] = mapped_column(default=None)
    contact_phone: Mapped[str | None] = mapped_column(default=None)
    address: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="NOW()"
    )

    # Relationships
    organization = relationship("Organization", back_populates="suppliers")

    __table_args__ = (Index("idx_supplier_org_id", "org_id"),)
