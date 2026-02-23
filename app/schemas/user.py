from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import RoleEnum


# Shared fields
class UserBase(BaseModel):
    email: EmailStr
    role: RoleEnum = RoleEnum.STAFF


# Input schema for creating a user
class UserCreate(UserBase):
    org_id: UUID
    password: str  # plain password; hash it in service layer


# Output schema for returning user data
class UserRead(UserBase):
    id: UUID
    org_id: UUID
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",  # 👈 reject any fields not declared in schema
    )
