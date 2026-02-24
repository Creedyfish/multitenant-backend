from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SupplierBase(BaseModel):
    name: str
    contact_email: str | None = None
    contact_phone: str | None = None
    address: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    address: str | None = None


class SupplierRead(SupplierBase):
    id: UUID
    org_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
