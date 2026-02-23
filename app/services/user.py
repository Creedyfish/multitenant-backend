import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db import DB
from app.models import RoleEnum, User


def get_user(db: DB, email: str) -> User | None:
    return db.execute(
        select(User).options(joinedload(User.organization)).where(User.email == email)
    ).scalar_one_or_none()


def create_user(
    org_id: uuid.UUID, email: str, password_hash: str, role: RoleEnum, db: DB
):
    user = db.execute(
        select(User).where(User.email == email, User.org_id == org_id)
    ).scalar_one_or_none()

    if user:
        raise HTTPException(
            status_code=409,
            detail="User with this email already exists in this organization",
        )

    data = User(org_id=org_id, password_hash=password_hash, role=role, email=email)
    db.add(data)
    db.flush()
    db.refresh(data)
    return data
