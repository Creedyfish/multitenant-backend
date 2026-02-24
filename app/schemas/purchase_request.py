import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PurchaseRequestStatusEnum

# ── Items ────────────────────────────────────────────────────────────────────


class PurchaseRequestItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0)
    estimated_price: Decimal | None = None
    supplier_id: uuid.UUID | None = None


class PurchaseRequestItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    estimated_price: Decimal | None
    supplier_id: uuid.UUID | None


# ── Purchase Requests ────────────────────────────────────────────────────────


class PurchaseRequestCreate(BaseModel):
    notes: str | None = None
    items: list[PurchaseRequestItemCreate] = Field(..., min_length=1)


class PurchaseRequestUpdate(BaseModel):
    """Only allowed while in DRAFT status."""

    notes: str | None = None
    items: list[PurchaseRequestItemCreate] | None = None


class PurchaseRequestReject(BaseModel):
    rejection_reason: str = Field(..., min_length=1)


class PurchaseRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    request_number: str
    status: PurchaseRequestStatusEnum
    created_by: uuid.UUID
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    rejected_by: uuid.UUID | None
    rejected_at: datetime | None
    rejection_reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[PurchaseRequestItemOut]


class PurchaseRequestListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    request_number: str
    status: PurchaseRequestStatusEnum
    created_by: uuid.UUID
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
