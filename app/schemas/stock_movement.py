import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StockMovementTypeEnum

# ── Stock In ──────────────────────────────────────────────────────────────────


class StockInCreate(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int = Field(..., gt=0)
    reference: str | None = None
    notes: str | None = None


# ── Stock Out ─────────────────────────────────────────────────────────────────


class StockOutCreate(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int = Field(..., gt=0)
    reference: str | None = None
    notes: str | None = None


# ── Transfer ──────────────────────────────────────────────────────────────────


class StockTransferCreate(BaseModel):
    product_id: uuid.UUID
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    quantity: int = Field(..., gt=0)
    notes: str | None = None


# ── Adjustment ────────────────────────────────────────────────────────────────


class StockAdjustmentCreate(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int = Field(..., description="Positive to add stock, negative to remove")
    reference: str | None = None
    notes: str | None = None


# ── Output ────────────────────────────────────────────────────────────────────


class StockMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    type: StockMovementTypeEnum
    quantity: int
    reference: str | None
    notes: str | None
    created_by: uuid.UUID
    created_at: datetime


class StockLevelOut(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    current_stock: int
