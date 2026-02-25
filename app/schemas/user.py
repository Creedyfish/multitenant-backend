from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import RoleEnum

# ── Base ──────────────────────────────────────────────────────────────────────


class UserBase(BaseModel):
    email: EmailStr
    role: RoleEnum = RoleEnum.STAFF


# ── Input schemas ─────────────────────────────────────────────────────────────


class UserCreate(UserBase):
    org_id: UUID
    password: str
    full_name: str


class UserUpdate(BaseModel):
    """Admin use only — can change role."""

    email: EmailStr | None = None
    full_name: str | None = None
    role: RoleEnum | None = None


class UserUpdateSelf(BaseModel):
    """Self-update — role intentionally excluded."""

    email: EmailStr | None = None
    full_name: str | None = None


class UserUpdatePassword(BaseModel):
    current_password: str
    new_password: str


class RegisterRequest(BaseModel):
    """Single payload to create an org + admin user in one step."""

    # Org fields
    org_name: str
    subdomain: str
    # User fields
    email: EmailStr
    password: str
    full_name: str


# ── Output schemas ────────────────────────────────────────────────────────────


class UserRead(UserBase):
    id: UUID
    org_id: UUID
    full_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class RegisterResponse(BaseModel):
    user: UserRead
    org_id: UUID
    subdomain: str
