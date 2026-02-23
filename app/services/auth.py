from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import HTTPException, status

from app.core import create_access_token, create_refresh_token, verify_password
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.database import DB
from app.models import RefreshToken
from app.models.enums import RoleEnum
from app.schemas.auth import RegisterUser
from app.services.organization import create_organization
from app.services.refresh_token import get_refresh_token
from app.services.user import create_user, get_user


def add_refresh_token(user_id: UUID, token: str, delta: timedelta, db: DB):
    expires_at = datetime.now(timezone.utc) + delta
    data = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
    )
    db.add(data)
    db.commit()
    db.refresh(data)
    return data


def register_organization(payload: RegisterUser, db: DB):
    try:
        org = create_organization(
            name=payload.org_name, subdomain=payload.org_subdomain, db=db
        )
        password_hash = get_password_hash(payload.password)
        user = create_user(
            org_id=org.id,
            email=payload.email,
            password_hash=password_hash,
            role=RoleEnum.ADMIN,
            db=db,
        )
        db.commit()
        db.refresh(user)
        return user
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed")


def authenticate_user(db: DB, username: str, password: str, subdomain: str):
    user = get_user(db, username, subdomain)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user


def login(db: DB, username: str, password: str, subdomain: str):
    user = authenticate_user(db, username, password, subdomain)  # pass subdomain
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "org_id": str(user.org_id),
            "sub": user.email,
            "role": user.role.value,
            "org": user.organization.name,
            "subdomain": user.organization.subdomain,
        },
    )
    refresh_token_expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={
            "org_id": str(user.org_id),
            "sub": user.email,
            "role": user.role.value,
            "org": user.organization.name,
            "subdomain": user.organization.subdomain,
        },
        delta=refresh_token_expires_delta,
    )

    add_refresh_token(user.id, refresh_token, refresh_token_expires_delta, db=db)

    return access_token, refresh_token


def refresh(db: DB, refresh_token: str):
    try:
        payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_email = payload.get("sub")
    org_name = payload.get("org")
    org_subdomain = payload.get("subdomain")
    org_id = payload.get("org_id")
    role = payload.get("role")
    # 2. get user
    if not user_email or not isinstance(user_email, str):
        raise HTTPException(status_code=401, detail="Invalid token claims")
    user = get_user(db, user_email, org_subdomain)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # 3. check token exists in DB and is not expired
    token = get_refresh_token(db, user.id, refresh_token)
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    if token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # 4. issue new access token
    access_token = create_access_token(
        data={
            "sub": user_email,
            "org_id": org_id,
            "role": role,
            "org": org_name,
            "subdomain": org_subdomain,
        }
    )
    return access_token
