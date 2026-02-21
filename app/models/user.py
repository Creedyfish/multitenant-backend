import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

from .enums import RoleEnum

if TYPE_CHECKING:
    from app.models import Organization


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default="gen_random_uuid()"
    )
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    email: Mapped[str]
    password_hash: Mapped[str]
    role: Mapped[RoleEnum] = mapped_column(SQLEnum(RoleEnum), default=RoleEnum.STAFF)
    created_at: Mapped[datetime] = mapped_column(server_default="NOW()")

    organization: Mapped["Organization"] = relationship(back_populates="users")

    __table_args__ = (
        Index("idx_user_org_email", "org_id", "email", unique=True),
        Index("idx_user_org_id", "org_id"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default="gen_random_uuid()"
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(unique=True, index=True)
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(server_default="NOW()")

    __table_args__ = (Index("idx_refresh_token_user", "user_id"),)
