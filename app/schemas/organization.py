from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Organization(BaseModel):
    name: str
    subdomain: str


class OrganizationCreate(Organization):
    pass


class OrganizationRead(Organization):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
