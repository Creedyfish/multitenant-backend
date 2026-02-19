from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.db.database import Base

from .enums import RoleEnum


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    email = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(SQLEnum(RoleEnum), nullable=False, default=RoleEnum.STAFF)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    # Relationships
    organization = relationship("Organization", back_populates="users")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_user_org_email", "org_id", "email", unique=True),
        Index("idx_user_org_id", "org_id"),
    )


class RefreshToken(Base):
    """Store refresh tokens for JWT authentication"""

    __tablename__ = "refresh_tokens"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    __table_args__ = (Index("idx_refresh_token_user", "user_id"),)
