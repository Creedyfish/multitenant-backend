import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Numeric

from app.db.database import Base

from .enums import PurchaseRequestStatusEnum

if TYPE_CHECKING:
    from app.models import Organization, Product, Supplier


class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default="gen_random_uuid()"
    )
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    request_number: Mapped[str]
    status: Mapped[PurchaseRequestStatusEnum] = mapped_column(
        SQLEnum(PurchaseRequestStatusEnum), default=PurchaseRequestStatusEnum.DRAFT
    )
    created_by: Mapped[uuid.UUID]
    approved_by: Mapped[uuid.UUID | None]
    approved_at: Mapped[datetime | None]
    rejected_by: Mapped[uuid.UUID | None]
    rejected_at: Mapped[datetime | None]
    rejection_reason: Mapped[str | None] = mapped_column(Text, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default="NOW()")
    updated_at: Mapped[datetime] = mapped_column(
        server_default="NOW()", onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(
        back_populates="purchase_requests"
    )
    items: Mapped[list["PurchaseRequestItem"]] = relationship(back_populates="request")

    __table_args__ = (
        Index(
            "idx_purchase_request_org_number", "org_id", "request_number", unique=True
        ),
        Index("idx_purchase_request_org_status", "org_id", "status"),
    )


class PurchaseRequestItem(Base):
    __tablename__ = "purchase_request_items"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default="gen_random_uuid()"
    )
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("purchase_requests.id"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]
    estimated_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), default=None
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("suppliers.id"), default=None
    )

    request: Mapped["PurchaseRequest"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
    supplier: Mapped["Supplier | None"] = relationship()

    __table_args__ = (Index("idx_purchase_request_item_request", "request_id"),)
