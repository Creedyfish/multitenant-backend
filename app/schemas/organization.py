from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OrganizationCreate(BaseModel):
    name: str
    subdomain: str


class OrganizationUpdate(BaseModel):
    name: str | None = None


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    subdomain: str
    created_at: datetime

    class Config:
        from_attributes = True
