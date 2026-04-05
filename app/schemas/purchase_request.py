import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import PurchaseRequestStatusEnum
from app.models.purchase_request import PurchaseRequest, PurchaseRequestItem

# ── Items ────────────────────────────────────────────────────────────────────


if TYPE_CHECKING:
    pass


class PurchaseRequestItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0)
    estimated_price: Decimal | None = None
    supplier_id: uuid.UUID | None = None
    warehouse_id: uuid.UUID | None = None


class PurchaseRequestItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    estimated_price: Decimal | None
    supplier_id: uuid.UUID | None
    warehouse_id: uuid.UUID | None
    product_name: str | None = None
    product_sku: str | None = None

    @model_validator(mode="before")
    @classmethod
    def populate_product_fields(cls, data: object) -> object:
        if not isinstance(data, PurchaseRequestItem):
            return data
        if data.product:
            object.__setattr__(data, "product_name", data.product.name)
            object.__setattr__(data, "product_sku", data.product.sku)
        return data


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


class PurchaseRequestReceiveItem(BaseModel):
    item_id: uuid.UUID
    warehouse_id: uuid.UUID


class PurchaseRequestReceive(BaseModel):
    items: list[PurchaseRequestReceiveItem] = Field(..., min_length=1)


class PurchaseRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    request_number: str
    status: PurchaseRequestStatusEnum
    created_by: uuid.UUID
    created_by_name: Optional[str] = None
    approved_by: Optional[uuid.UUID] = None
    approved_by_name: Optional[str] = None
    approved_at: datetime | None
    rejected_by: Optional[uuid.UUID] = None
    rejected_by_name: Optional[str] = None
    rejected_at: datetime | None
    rejection_reason: str | None
    notes: str | None
    received_by: Optional[uuid.UUID] = None
    received_by_name: Optional[str] = None
    received_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    items: list[PurchaseRequestItemOut]

    @model_validator(mode="before")
    @classmethod
    def populate_user_names(cls, data: object) -> object:
        if not isinstance(data, PurchaseRequest):
            return data
        if data.creator:
            object.__setattr__(data, "created_by_name", data.creator.full_name)
        if data.approver:
            object.__setattr__(data, "approved_by_name", data.approver.full_name)
        if data.rejector:
            object.__setattr__(data, "rejected_by_name", data.rejector.full_name)
        if data.receiver:  # ← add
            object.__setattr__(data, "received_by_name", data.receiver.full_name)
        return data


class PurchaseRequestListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    request_number: str
    status: PurchaseRequestStatusEnum
    created_by: uuid.UUID
    created_by_name: Optional[str] = None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_user_names(cls, data: object) -> object:
        if not isinstance(data, PurchaseRequest):
            return data
        if data.creator:
            object.__setattr__(data, "created_by_name", data.creator.full_name)
        return data
