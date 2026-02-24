from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WarehouseBase(BaseModel):
    name: str
    location: str
    capacity: int | None = None


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    capacity: int | None = None


class WarehouseRead(WarehouseBase):
    id: UUID
    org_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
