from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from jwt.exceptions import InvalidTokenError

from app.core.config import settings
from app.core.security import oauth2_scheme
from app.db.database import DB
from app.models import User
from app.schemas import TokenData
from app.services.user import UserService


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DB):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email = payload.get("sub")
        subdomain = payload.get("subdomain")  # ✅ extract subdomain from token
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception
    if token_data.email is None:
        raise credentials_exception
    user = UserService(db).get_by_email(
        token_data.email, subdomain
    )  # ✅ pass subdomain
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user
